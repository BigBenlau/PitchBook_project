#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from part6_schema import (
    ALLOWED_CONFIDENCE,
    ALLOWED_INVESTOR_ARCHETYPES,
    ALLOWED_LIKELIHOODS,
    ALLOWED_SEARCH_TIERS,
    ALLOWED_YES_NO,
    CAPABILITY_FLAG_COLUMNS,
    CLASSIFIER_CSV_COLUMNS,
    RESULT_CSV_COLUMNS,
    capability_labels_from_row,
    ensure_capability_labels,
    parse_json_list,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Atomically append one validated classifier/result row pair for a part6 investor attempt. "
            "This is the only supported append path for authoritative attempt CSVs."
        )
    )
    parser.add_argument("--tasks-file", type=Path, required=True)
    parser.add_argument("--classifier-csv", type=Path, required=True)
    parser.add_argument("--results-csv", type=Path, required=True)
    parser.add_argument(
        "--bundle-json",
        type=Path,
        required=True,
        help='JSON file with {"classifier_row": {...}, "result_row": {...}}',
    )
    return parser.parse_args()


def parse_optional_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def load_tasks(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            raw = line.strip()
            if raw:
                tasks.append(json.loads(raw))
    return tasks


def load_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows = [{field: str(row.get(field, "") or "") for field in fieldnames} for row in reader]
    return fieldnames, rows


def atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_raw = tempfile.mkstemp(prefix=f".{path.name}.tmp.", suffix=".csv", dir=path.parent)
    temp_path = Path(temp_raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            outfile.flush()
            os.fsync(outfile.fileno())
        os.replace(temp_path, path)
        try:
            dir_fd = os.open(path.parent, os.O_DIRECTORY)
        except OSError:
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def lock_path_for_csv(path: Path) -> Path:
    return path.parent / f".{path.name}.lock"


@contextmanager
def locked_csv_pair(paths: list[Path]) -> Iterator[None]:
    opened: list[Any] = []
    try:
        for lock_path in sorted(lock_path_for_csv(path) for path in paths):
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = lock_path.open("a+", encoding="utf-8")
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            opened.append(handle)
        yield
    finally:
        while opened:
            handle = opened.pop()
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()


def normalize_row(row: dict[str, Any], columns: list[str]) -> dict[str, str]:
    return {column: str(row.get(column, "") or "") for column in columns}


def validate_json_list(raw: str) -> bool:
    return isinstance(parse_json_list(raw), list)


def split_pipe_list(value: str) -> list[str]:
    raw = str(value or "").strip()
    if not raw or raw == "[]":
        return []
    return [item.strip() for item in raw.split("|") if item.strip()]


def validate_classifier_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if row.get("investor_archetype") not in ALLOWED_INVESTOR_ARCHETYPES:
        errors.append("invalid investor_archetype")
    if row.get("crypto_native_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("invalid crypto_native_likelihood")
    if row.get("operating_capability_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("invalid operating_capability_likelihood")
    search_tier = row.get("search_tier", "")
    capability_search_required = row.get("capability_search_required", "")
    if search_tier not in ALLOWED_SEARCH_TIERS:
        errors.append("invalid search_tier")
    if capability_search_required not in ALLOWED_YES_NO:
        errors.append("invalid capability_search_required")
    if search_tier in {"full", "light"} and capability_search_required != "yes":
        errors.append("full/light search_tier requires capability_search_required=yes")
    if search_tier == "skip_candidate" and capability_search_required != "no":
        errors.append("skip_candidate requires capability_search_required=no")
    if search_tier == "skip_candidate" and row.get("crypto_native_likelihood") not in {"low", "none"}:
        errors.append("skip_candidate requires crypto_native_likelihood low/none")
    if search_tier == "skip_candidate" and row.get("operating_capability_likelihood") not in {"low", "none"}:
        errors.append("skip_candidate requires operating_capability_likelihood low/none")
    if not validate_json_list(row.get("risk_flags", "")):
        errors.append("risk_flags must be a JSON list string")
    if not row.get("classifier_reason", "").strip():
        errors.append("classifier_reason is required")
    return errors


def validate_result_row(row: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if row.get("investor_archetype") not in ALLOWED_INVESTOR_ARCHETYPES:
        errors.append("invalid investor_archetype")
    if row.get("crypto_native_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("invalid crypto_native_likelihood")
    if row.get("operating_capability_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("invalid operating_capability_likelihood")
    if row.get("search_tier") not in ALLOWED_SEARCH_TIERS:
        errors.append("invalid search_tier")
    if row.get("capability_search_required") not in ALLOWED_YES_NO:
        errors.append("invalid capability_search_required")
    if row.get("status") != "completed":
        errors.append("status must be completed")
    if row.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append("confidence must be high/medium/low")
    if row.get("needs_manual_review") not in ALLOWED_YES_NO:
        errors.append("needs_manual_review must be yes/no")
    if row.get("search_tier") in {"full", "light"} and row.get("capability_search_required") != "yes":
        errors.append("full/light search_tier requires capability_search_required=yes")
    if row.get("search_tier") == "skip_candidate" and row.get("capability_search_required") != "no":
        errors.append("skip_candidate requires capability_search_required=no")
    if row.get("search_tier") == "skip_candidate" and row.get("crypto_native_likelihood") not in {"low", "none"}:
        errors.append("skip_candidate requires crypto_native_likelihood low/none")
    if row.get("search_tier") == "skip_candidate" and row.get("operating_capability_likelihood") not in {"low", "none"}:
        errors.append("skip_candidate requires operating_capability_likelihood low/none")
    if not row.get("completed_at", "").strip():
        errors.append("completed_at is required")
    if not row.get("capability_search_reason", "").strip():
        errors.append("capability_search_reason is required")
    if not validate_json_list(row.get("capability_labels", "")):
        errors.append("capability_labels must be a JSON list string")
    if not validate_json_list(row.get("other_flags", "")):
        errors.append("other_flags must be a JSON list string")
    for column in CAPABILITY_FLAG_COLUMNS:
        if row.get(column) not in ALLOWED_YES_NO:
            errors.append(f"{column} must be yes or no")
    expected_labels = capability_labels_from_row(row)
    actual_labels = [str(value).strip() for value in parse_json_list(row.get("capability_labels", "")) if str(value).strip()]
    if actual_labels != expected_labels:
        errors.append("capability_labels must match yes-valued capability flags")
    searched_row = row.get("capability_search_required") == "yes"
    evidence_urls = split_pipe_list(row.get("evidence_urls", ""))
    evidence_types = split_pipe_list(row.get("evidence_source_types", ""))
    if searched_row:
        if not evidence_urls:
            errors.append("searched rows require non-empty evidence_urls")
        if not evidence_types:
            errors.append("searched rows require non-empty evidence_source_types")
    for url in evidence_urls:
        if not url.startswith(("http://", "https://")):
            errors.append("evidence_urls must contain only absolute http(s) URLs")
            break
    if any(value == "yes" for value in (row.get(column, "") for column in CAPABILITY_FLAG_COLUMNS)) and not evidence_urls:
        errors.append("capability-positive rows require evidence_urls")
    return errors


def validate_pair(classifier_row: dict[str, str], result_row: dict[str, str], expected_task: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["task_index", "investor_id", "investor_name", "normalized_domain"]:
        classifier_value = classifier_row.get(key, "")
        result_value = result_row.get(key, "")
        expected_value = str(expected_task.get(key, ""))
        if classifier_value != expected_value:
            errors.append(f"classifier {key} must match tasks.jsonl ({expected_value!r})")
        if result_value != expected_value:
            errors.append(f"result {key} must match tasks.jsonl ({expected_value!r})")
        if classifier_value != result_value:
            errors.append(f"classifier/result {key} mismatch")
    for key in [
        "primary_investor_type",
        "investor_archetype",
        "crypto_native_likelihood",
        "operating_capability_likelihood",
        "search_tier",
        "capability_search_required",
    ]:
        if classifier_row.get(key, "") != result_row.get(key, ""):
            errors.append(f"classifier/result {key} mismatch")
    return errors


def load_bundle(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Bundle must be a JSON object: {path}")
    classifier_row = payload.get("classifier_row")
    result_row = payload.get("result_row")
    if not isinstance(classifier_row, dict) or not isinstance(result_row, dict):
        raise SystemExit(f"Bundle must contain classifier_row/result_row objects: {path}")
    return classifier_row, result_row


def main() -> None:
    args = parse_args()
    tasks_file = args.tasks_file.resolve()
    classifier_csv = args.classifier_csv.resolve()
    results_csv = args.results_csv.resolve()
    bundle_json = args.bundle_json.resolve()

    tasks = load_tasks(tasks_file)
    raw_classifier_row, raw_result_row = load_bundle(bundle_json)
    classifier_row = normalize_row(raw_classifier_row, CLASSIFIER_CSV_COLUMNS)
    result_row = normalize_row(raw_result_row, RESULT_CSV_COLUMNS)
    result_row = normalize_row(ensure_capability_labels(result_row), RESULT_CSV_COLUMNS)

    classifier_errors = validate_classifier_row(classifier_row)
    result_errors = validate_result_row(result_row)
    if classifier_errors or result_errors:
        joined = classifier_errors + result_errors
        raise SystemExit("Row validation failed: " + " | ".join(joined))

    with locked_csv_pair([classifier_csv, results_csv]):
        classifier_fields, classifier_rows = load_csv_rows(classifier_csv)
        result_fields, result_rows = load_csv_rows(results_csv)
        if classifier_fields and classifier_fields != CLASSIFIER_CSV_COLUMNS:
            raise SystemExit(f"Classifier CSV header mismatch: {classifier_csv}")
        if result_fields and result_fields != RESULT_CSV_COLUMNS:
            raise SystemExit(f"Results CSV header mismatch: {results_csv}")
        if len(classifier_rows) != len(result_rows):
            raise SystemExit(
                f"Authoritative CSVs are out of sync before append: classifier={len(classifier_rows)} results={len(result_rows)}"
            )

        next_index = len(classifier_rows)
        if next_index >= len(tasks):
            raise SystemExit(f"Append would exceed task_count for {tasks_file}")
        expected_task = tasks[next_index]
        pair_errors = validate_pair(classifier_row, result_row, expected_task)
        if pair_errors:
            raise SystemExit("Pair validation failed: " + " | ".join(pair_errors))

        if parse_optional_int(classifier_row.get("task_index")) != parse_optional_int(expected_task.get("task_index")):
            raise SystemExit(
                f"Classifier task_index {classifier_row.get('task_index')} is not the next expected task_index {expected_task.get('task_index')}"
            )
        if parse_optional_int(result_row.get("task_index")) != parse_optional_int(expected_task.get("task_index")):
            raise SystemExit(
                f"Result task_index {result_row.get('task_index')} is not the next expected task_index {expected_task.get('task_index')}"
            )

        classifier_rows.append(classifier_row)
        result_rows.append(result_row)
        atomic_write_csv(classifier_csv, CLASSIFIER_CSV_COLUMNS, classifier_rows)
        atomic_write_csv(results_csv, RESULT_CSV_COLUMNS, result_rows)

    print(
        json.dumps(
            {
                "appended_task_index": result_row.get("task_index", ""),
                "classifier_rows": len(classifier_rows),
                "result_rows": len(result_rows),
                "classifier_csv": str(classifier_csv),
                "results_csv": str(results_csv),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
