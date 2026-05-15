#!/usr/bin/env python3
from __future__ import annotations

import ast
import argparse
import csv
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent
DEFAULT_FINAL_DIR = PART4_DIR / "agent_runs" / "token_company"
DEFAULT_OPS_DIR = PART4_DIR / "agent_runs" / "token_company_ops"
LATEST_JOB_JSON = PART4_DIR / "agent_runs" / "token_company_longrun_latest.json"

RESULT_CSV_COLUMNS = [
    "task_index",
    "canonical_slug",
    "token_symbol",
    "token_name",
    "token_origin_type",
    "entity_link_likelihood",
    "entity_search_required",
    "entity_search_reason",
    "project_name",
    "project_url",
    "mapped_entity_name",
    "mapped_entity_legal_name",
    "mapped_entity_type",
    "mapped_entity_url",
    "mapped_entity_country",
    "entity_relation_type",
    "status",
    "completed_at",
    "has_entity_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
]

CLASSIFIER_CSV_COLUMNS = [
    "task_index",
    "canonical_slug",
    "token_symbol",
    "token_name",
    "token_origin_type",
    "entity_link_likelihood",
    "search_tier",
    "entity_search_required",
    "risk_flags",
    "classifier_reason",
]

LIST_COLUMNS = [
    "project_name",
    "project_url",
    "mapped_entity_name",
    "mapped_entity_legal_name",
    "mapped_entity_type",
    "mapped_entity_url",
    "mapped_entity_country",
    "entity_relation_type",
]

ALLOWED_TOKEN_ORIGIN_TYPES = {
    "layer1_or_l2",
    "protocol_or_app",
    "exchange_token",
    "stablecoin",
    "wrapped_or_bridged_asset",
    "liquid_staking_or_restaking",
    "asset_backed_or_rwa",
    "meme_or_community",
    "governance_or_utility",
    "unclear",
}
ALLOWED_LIKELIHOODS = {"high", "medium", "low", "none", "unclear"}
ALLOWED_YES_NO = {"yes", "no"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_SEARCH_TIERS = {"full", "light", "skip_candidate"}
ALLOWED_ENTITY_TYPES = {
    "company",
    "foundation",
    "issuer",
    "association",
    "trust",
    "dao_legal_wrapper",
    "nonprofit",
    "government_entity",
    "other_legal_entity",
    "unclear",
}

BACKLOG_FILENAMES = [
    "retry_pending_batches.csv",
    "schema_error_batches.csv",
    "collect_blocked_batches.csv",
]

CLEANUP_FILE_PATTERNS = [
    "*.lint_failed.*.bak",
    "*.manual_repair_*.bak",
    "*.schema_normalize_*.bak",
    "*.router_align_*.bak",
    "*.manual_collect_metadata_*.bak",
    "*.auto_check_metadata_*.bak",
    "task_*_classifier.json",
    "task_*_result.json",
    "*_classifier_row.json",
    "*_result_row.json",
]

CLEANUP_RUN_ROOT_FILENAMES = [
    "lint_rerun_batches.csv",
    "lint_rerun_batches.md",
    "startup_respawn_batches.csv",
    "startup_respawn_batches.md",
    "header_only_rerun_batches.csv",
    "header_only_rerun_batches.md",
]

CLEANUP_DIR_NAMES = {
    ".codex_home",
}


@dataclass
class CheckReport:
    runs_dir: str
    final_dir: str
    checked_batches: list[str] = field(default_factory=list)
    artifact_errors: list[str] = field(default_factory=list)
    final_errors: list[str] = field(default_factory=list)
    metadata_errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    batch_summaries: list[dict[str, Any]] = field(default_factory=list)
    final_summary: dict[str, Any] = field(default_factory=dict)
    backlog_summary: dict[str, Any] = field(default_factory=dict)

    @property
    def errors(self) -> list[str]:
        return self.artifact_errors + self.final_errors + self.metadata_errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "runs_dir": self.runs_dir,
            "final_dir": self.final_dir,
            "checked_batches": self.checked_batches,
            "artifact_errors": self.artifact_errors,
            "final_errors": self.final_errors,
            "metadata_errors": self.metadata_errors,
            "warnings": self.warnings,
            "batch_summaries": self.batch_summaries,
            "final_summary": self.final_summary,
            "backlog_summary": self.backlog_summary,
        }


def ensure_ops_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ops_report_path(ops_dir: Path, runs_dir: Path, stem: str, *, suffix: str = ".json") -> Path:
    safe_run_name = runs_dir.name or "latest"
    return ensure_ops_dir(ops_dir) / f"{safe_run_name}.{stem}{suffix}"


def ops_backup_path(ops_dir: Path, source_path: Path, stamp: str) -> Path:
    safe_source = str(source_path).replace("/", "__")
    return ensure_ops_dir(ops_dir) / f"{safe_source}.auto_check_metadata_{stamp}.bak"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one-shot part4 artifact checks, optional batch-scope collect, "
            "and optional schedule/backlog metadata reconciliation."
        )
    )
    parser.add_argument("--runs-dir", type=Path, help="Run directory containing schedule.csv.")
    parser.add_argument("--final-dir", type=Path, default=DEFAULT_FINAL_DIR)
    parser.add_argument("--ops-dir", type=Path, default=DEFAULT_OPS_DIR)
    parser.add_argument(
        "--batch-file",
        action="append",
        default=[],
        help="Optional scoped batch. Repeatable. Accepts basename or schedule batch_file.",
    )
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run 3_collect_results.py for the scoped batches after artifact checks pass.",
    )
    parser.add_argument(
        "--require-verification",
        action="store_true",
        help="Do not pass --skip-verification to 3_collect_results.py.",
    )
    parser.add_argument(
        "--require-final-coverage",
        action="store_true",
        help="Fail if final results/classifier CSVs do not cover every scoped task.",
    )
    parser.add_argument(
        "--fix-metadata",
        action="store_true",
        help="Mark scoped schedule rows completed/done and remove scoped backlog rows after checks pass.",
    )
    parser.add_argument(
        "--strict-metadata",
        action="store_true",
        help="Fail on non-completed scoped schedule rows or scoped backlog entries.",
    )
    parser.add_argument(
        "--cleanup-intermediates",
        action="store_true",
        help=(
            "Delete allowlisted temporary repair/quarantine backups, per-row JSON shards, "
            "stale leases, and worker sandbox folders for the scoped batches."
        ),
    )
    parser.add_argument(
        "--cleanup-dry-run",
        action="store_true",
        help="Preview intermediate cleanup without deleting files or folders.",
    )
    parser.add_argument(
        "--delete-runs-dir",
        action="store_true",
        help=(
            "After all checks pass, delete the current parallel runs_dir. "
            "This preserves final-dir outputs and writes a deletion report there."
        ),
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Report path. Defaults to token_company_ops/<runs_dir>.auto_check_collect_report.json.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)
    return data if isinstance(data, dict) else {}


def resolve_path(value: str | Path) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def find_latest_runs_dir() -> Path:
    if LATEST_JOB_JSON.exists():
        data = read_json(LATEST_JOB_JSON)
        for key in ["runs_dir", "run_dir", "path"]:
            raw = data.get(key)
            if raw:
                candidate = resolve_path(str(raw))
                if (candidate / "schedule.csv").exists():
                    return candidate
        nested = data.get("job")
        if isinstance(nested, dict):
            raw = nested.get("runs_dir") or nested.get("run_dir") or nested.get("path")
            if raw:
                candidate = resolve_path(str(raw))
                if (candidate / "schedule.csv").exists():
                    return candidate

    agent_runs = PART4_DIR / "agent_runs"
    candidates = [
        path
        for path in agent_runs.glob("token_company_parallel_eval_*")
        if (path / "schedule.csv").exists()
    ]
    if not candidates:
        raise SystemExit("Cannot resolve runs_dir: pass --runs-dir explicitly.")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows: list[dict[str, str]] = []
        for row in reader:
            clean = {key: (value or "") for key, value in row.items() if key is not None}
            if None in row:
                clean["_extra_columns"] = json.dumps(row[None], ensure_ascii=False)
            rows.append(clean)
        return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_optional_int(value: str | None, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def parse_failure_counts_json(value: str | None) -> dict[str, int]:
    raw = (value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    counts: dict[str, int] = {}
    for key, item in parsed.items():
        try:
            counts[str(key)] = int(item)
        except (TypeError, ValueError):
            counts[str(key)] = 0
    return counts


def validate_json_list(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def parse_json_list(value: str) -> list[Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def split_pipe_list(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw or raw == "[]":
        return []
    if raw.startswith("["):
        parsed = parse_json_list(raw)
        if parsed:
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [part.strip() for part in raw.split("|") if part.strip()]


def normalize_risk_flags_value(value: object) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw or raw.lower() == "none":
        return "[]"
    if validate_json_list(raw):
        return raw
    if "|" in raw:
        flags = [part.strip() for part in raw.split("|") if part.strip()]
    else:
        flags = [raw]
    return json.dumps(flags, ensure_ascii=False)


def normalize_json_list_string(value: object) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return ""
    if validate_json_list(raw):
        return json.dumps(json.loads(raw), ensure_ascii=False, separators=(",", ":"))
    try:
        parsed_literal = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        parsed_literal = None
    if isinstance(parsed_literal, (list, tuple)):
        return json.dumps(list(parsed_literal), ensure_ascii=False, separators=(",", ":"))
    if raw.lower() in {"none", "null"}:
        return "[]"
    if "|" in raw:
        parts = [part.strip() for part in raw.split("|") if part.strip()]
        return json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
    return json.dumps([raw], ensure_ascii=False, separators=(",", ":"))


def normalize_has_entity_evidence_value(row: dict[str, str]) -> str:
    raw = (row.get("has_entity_evidence") or "").strip()
    if raw.lower() not in {"yes", "no"}:
        return raw
    if (row.get("entity_search_required") or "").strip() != "yes":
        return raw

    mapped_raw = normalize_json_list_string(row.get("mapped_entity_name", ""))
    try:
        mapped_count = len(json.loads(mapped_raw)) if mapped_raw else 0
    except json.JSONDecodeError:
        mapped_count = 0
    source_types = split_pipe_list(row.get("evidence_source_types", ""))
    source_summary = ", ".join(source_types[:3]) if source_types else "official project sources"
    if mapped_count > 0:
        return (
            "Reviewed canonical token pages and cited "
            f"{source_summary}; the cited materials support the mapped entity."
        )
    return (
        "Reviewed canonical token pages and cited "
        f"{source_summary}; no reliable legal-entity mapping surfaced from those sources."
    )


def canonicalize_classifier_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {column: row.get(column, "") for column in CLASSIFIER_CSV_COLUMNS}
    normalized["risk_flags"] = normalize_risk_flags_value(normalized.get("risk_flags", ""))
    return normalized


def canonicalize_result_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {column: row.get(column, "") for column in RESULT_CSV_COLUMNS}
    for column in LIST_COLUMNS:
        normalized[column] = normalize_json_list_string(normalized.get(column, ""))
    if normalized.get("status") == "complete":
        normalized["status"] = "completed"
    normalized["has_entity_evidence"] = normalize_has_entity_evidence_value(normalized)
    return normalized


def align_result_router_fields(
    row: dict[str, str],
    classifier_row: dict[str, str] | None,
) -> dict[str, str]:
    if not classifier_row:
        return row
    aligned = dict(row)
    for column in ["token_origin_type", "entity_link_likelihood", "entity_search_required"]:
        aligned[column] = classifier_row.get(column, "")
    return aligned


def batch_key(value: str) -> str:
    return Path(value).name


def load_schedule(runs_dir: Path) -> tuple[list[str], list[dict[str, str]]]:
    schedule_csv = runs_dir / "schedule.csv"
    if not schedule_csv.exists():
        raise SystemExit(f"Missing schedule.csv: {schedule_csv}")
    return load_csv(schedule_csv)


def resolve_batch_scope(
    schedule_rows: list[dict[str, str]],
    requested: list[str],
) -> list[dict[str, str]]:
    if not requested:
        return schedule_rows
    requested_values = {value.strip() for value in requested if value.strip()}
    requested_basenames = {Path(value).name for value in requested_values}
    matched: list[dict[str, str]] = []
    for row in schedule_rows:
        batch_file = str(row.get("batch_file") or "").strip()
        if batch_file in requested_values or Path(batch_file).name in requested_basenames:
            matched.append(row)
    missing = requested_basenames - {Path(str(row.get("batch_file") or "")).name for row in matched}
    if missing:
        raise SystemExit("Requested batches not found in schedule.csv: " + ", ".join(sorted(missing)))
    return matched


def load_tasks(schedule_row: dict[str, str]) -> list[dict[str, Any]]:
    raw = schedule_row.get("tasks_file") or ""
    if not raw:
        return []
    path = resolve_path(raw)
    if not path.exists():
        return []
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def expected_task_indexes(schedule_row: dict[str, str]) -> list[int]:
    tasks = load_tasks(schedule_row)
    indexes = [parse_optional_int(str(task.get("task_index") or ""), default=0) for task in tasks]
    indexes = [index for index in indexes if index > 0]
    if indexes:
        return indexes
    first = parse_optional_int(schedule_row.get("first_task_index"), default=0)
    last = parse_optional_int(schedule_row.get("last_task_index"), default=0)
    if first > 0 and last >= first:
        return list(range(first, last + 1))
    return []


def validate_classifier_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    task_index = row.get("task_index", "")
    token_name = row.get("token_name", "")
    if row.get("token_origin_type") not in ALLOWED_TOKEN_ORIGIN_TYPES:
        errors.append("token_origin_type uses an invalid value")
    if row.get("entity_link_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("entity_link_likelihood uses an invalid value")
    if row.get("search_tier") not in ALLOWED_SEARCH_TIERS:
        errors.append("search_tier uses an invalid value")
    if row.get("entity_search_required") not in ALLOWED_YES_NO:
        errors.append("entity_search_required must be yes or no")
    if not validate_json_list(normalize_risk_flags_value(row.get("risk_flags") or "")):
        errors.append("risk_flags is not a valid JSON list")
    if not (row.get("classifier_reason") or "").strip():
        errors.append("classifier_reason is blank")
    return [f"{source}: task_index={task_index} token={token_name}: {error}" for error in errors]


def validate_result_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    task_index = row.get("task_index", "")
    token_name = row.get("token_name", "")
    for column in LIST_COLUMNS:
        value = (row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
        elif not validate_json_list(value):
            errors.append(f"{column} is not a valid JSON list")
    if row.get("status") != "completed":
        errors.append("status must be completed")
    if row.get("token_origin_type") not in ALLOWED_TOKEN_ORIGIN_TYPES:
        errors.append("token_origin_type uses an invalid value")
    if row.get("entity_link_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("entity_link_likelihood uses an invalid value")
    if row.get("entity_search_required") not in ALLOWED_YES_NO:
        errors.append("entity_search_required must be yes or no")
    if row.get("needs_manual_review") not in ALLOWED_YES_NO:
        errors.append("needs_manual_review must be yes or no")
    if row.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append("confidence must be high, medium, or low")

    has_entity_evidence = (row.get("has_entity_evidence") or "").strip()
    evidence_urls = split_pipe_list(row.get("evidence_urls", ""))
    evidence_source_types = split_pipe_list(row.get("evidence_source_types", ""))
    if not has_entity_evidence:
        errors.append("has_entity_evidence is blank")
    if row.get("entity_search_required") == "yes":
        if not evidence_urls:
            errors.append("searched rows require non-empty evidence_urls")
        if not evidence_source_types:
            errors.append("searched rows require non-empty evidence_source_types")
        if has_entity_evidence.lower() in {"yes", "no"}:
            errors.append("searched rows must summarize evidence in has_entity_evidence, not bare yes/no")
    for entity_type in parse_json_list(row.get("mapped_entity_type", "")):
        if str(entity_type) not in ALLOWED_ENTITY_TYPES:
            errors.append(f"mapped_entity_type contains invalid value: {entity_type!r}")
    return [f"{source}: task_index={task_index} token={token_name}: {error}" for error in errors]


def rows_by_task(rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    by_task: dict[int, dict[str, str]] = {}
    for row in rows:
        task_index = parse_optional_int(row.get("task_index"), default=0)
        if task_index > 0:
            by_task[task_index] = row
    return by_task


def resolve_check_csv_path(
    schedule_row: dict[str, str],
    *,
    primary_key: str,
    fallback_key: str,
    expected_header: list[str],
    expected_rows: int,
) -> Path:
    candidates: list[tuple[str, Path, bool, int]] = []
    for key, source_name in [(primary_key, "primary"), (fallback_key, "best_valid")]:
        raw = str(schedule_row.get(key) or "").strip()
        if not raw:
            continue
        path = resolve_path(raw)
        if not path.exists() or not path.is_file():
            continue
        header, rows = load_csv(path)
        candidates.append((source_name, path, header == expected_header, len(rows)))
    if not candidates:
        raw = str(schedule_row.get(primary_key) or "").strip() or str(schedule_row.get(fallback_key) or "").strip()
        return resolve_path(raw)
    for source_name, path, header_ok, row_count in candidates:
        if source_name == "primary" and header_ok and row_count == expected_rows:
            return path
    for source_name, path, header_ok, row_count in candidates:
        if source_name == "best_valid" and header_ok and row_count == expected_rows:
            return path
    return candidates[0][1]


def check_batch_artifacts(schedule_row: dict[str, str]) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    batch_name = batch_key(str(schedule_row.get("batch_file") or ""))
    task_count = parse_optional_int(schedule_row.get("task_count"), default=0)
    expected_indexes = expected_task_indexes(schedule_row)
    if not task_count and expected_indexes:
        task_count = len(expected_indexes)

    classifier_path = resolve_check_csv_path(
        schedule_row,
        primary_key="classifier_results_csv",
        fallback_key="best_valid_classifier_results_csv",
        expected_header=CLASSIFIER_CSV_COLUMNS,
        expected_rows=task_count,
    )
    results_path = resolve_check_csv_path(
        schedule_row,
        primary_key="results_csv",
        fallback_key="best_valid_results_csv",
        expected_header=RESULT_CSV_COLUMNS,
        expected_rows=task_count,
    )
    run_dir = resolve_path(schedule_row.get("run_dir") or "")
    active_attempt = resolve_path(schedule_row.get("active_attempt") or run_dir)
    classifier_header, classifier_rows = load_csv(classifier_path)
    results_header, result_rows = load_csv(results_path)

    if classifier_header != CLASSIFIER_CSV_COLUMNS:
        errors.append(f"{classifier_path}: header mismatch")
    if results_header != RESULT_CSV_COLUMNS:
        errors.append(f"{results_path}: header mismatch")
    if task_count and len(classifier_rows) != task_count:
        errors.append(f"{classifier_path}: expected {task_count} rows, found {len(classifier_rows)}")
    if task_count and len(result_rows) != task_count:
        errors.append(f"{results_path}: expected {task_count} rows, found {len(result_rows)}")

    classifier_rows = [canonicalize_classifier_row(row) for row in classifier_rows]
    classifier_by_task = rows_by_task(classifier_rows)
    normalized_result_rows: list[dict[str, str]] = []
    for row in result_rows:
        task_index = parse_optional_int(row.get("task_index"), default=0)
        classifier_row = classifier_by_task.get(task_index)
        normalized_result_rows.append(
            align_result_router_fields(canonicalize_result_row(row), classifier_row)
        )
    result_rows = normalized_result_rows
    result_by_task = rows_by_task(result_rows)
    if expected_indexes:
        missing_classifier = sorted(set(expected_indexes) - set(classifier_by_task))
        missing_results = sorted(set(expected_indexes) - set(result_by_task))
        if missing_classifier:
            errors.append(f"{classifier_path}: missing task_index {missing_classifier[:20]}")
        if missing_results:
            errors.append(f"{results_path}: missing task_index {missing_results[:20]}")

    for row in classifier_rows:
        errors.extend(validate_classifier_row(row, classifier_path))
    for row in result_rows:
        errors.extend(validate_result_row(row, results_path))
        task_index = parse_optional_int(row.get("task_index"), default=0)
        classifier_row = classifier_by_task.get(task_index)
        if not classifier_row:
            continue
        for column in ["token_origin_type", "entity_link_likelihood", "entity_search_required"]:
            if row.get(column) != classifier_row.get(column):
                errors.append(f"{results_path}: task_index={task_index}: {column} does not match classifier_results.csv")

    backup_patterns = [
        "*.lint_failed.*.bak",
        "*.manual_repair_*.bak",
        "*.schema_normalize_*.bak",
        "*.router_align_*.bak",
        "*.auto_check_metadata_*.bak",
    ]
    backup_count = 0
    if active_attempt.exists():
        for pattern in backup_patterns:
            backup_count += len(list(active_attempt.glob(pattern)))
    reconciled_dir = run_dir / "reconciled"
    if reconciled_dir.exists():
        for pattern in backup_patterns:
            backup_count += len(list(reconciled_dir.glob(pattern)))

    failure_counts = parse_failure_counts_json(schedule_row.get("failure_counts_json"))
    nonzero_failure_counts = {
        key: value for key, value in sorted(failure_counts.items()) if value > 0
    }

    summary = {
        "batch_file": str(schedule_row.get("batch_file") or ""),
        "batch_name": batch_name,
        "status": str(schedule_row.get("status") or ""),
        "queue_state": str(schedule_row.get("queue_state") or ""),
        "collect_state": str(schedule_row.get("collect_state") or ""),
        "collected_at": str(schedule_row.get("collected_at") or ""),
        "attempt_index": parse_optional_int(schedule_row.get("attempt_index"), default=0),
        "respawn_count": parse_optional_int(schedule_row.get("respawn_count"), default=0),
        "last_failure_type": str(schedule_row.get("last_failure_type") or ""),
        "last_rerun_reason": str(schedule_row.get("last_rerun_reason") or ""),
        "collect_failure_reason": str(schedule_row.get("collect_failure_reason") or ""),
        "consecutive_no_progress_attempts": parse_optional_int(
            schedule_row.get("consecutive_no_progress_attempts"),
            default=0,
        ),
        "nonzero_failure_counts": nonzero_failure_counts,
        "best_valid_classifier_rows": parse_optional_int(
            schedule_row.get("best_valid_classifier_rows"),
            default=0,
        ),
        "best_valid_result_rows": parse_optional_int(
            schedule_row.get("best_valid_result_rows"),
            default=0,
        ),
        "last_seen_classifier_rows": parse_optional_int(
            schedule_row.get("last_seen_classifier_rows"),
            default=0,
        ),
        "last_seen_result_rows": parse_optional_int(
            schedule_row.get("last_seen_result_rows"),
            default=0,
        ),
        "repair_backup_count": backup_count,
        "task_count": task_count,
        "classifier_rows": len(classifier_rows),
        "result_rows": len(result_rows),
        "first_task_index": min(expected_indexes) if expected_indexes else None,
        "last_task_index": max(expected_indexes) if expected_indexes else None,
    }
    return summary, errors


def load_final_indexes(final_dir: Path) -> tuple[dict[str, Any], set[int], set[int], list[str]]:
    errors: list[str] = []
    results_csv = final_dir / "results.csv"
    classifier_csv = final_dir / "classifier_results.csv"
    result_header, result_rows = load_csv(results_csv)
    classifier_header, classifier_rows = load_csv(classifier_csv)
    if result_header and result_header != RESULT_CSV_COLUMNS:
        errors.append(f"{results_csv}: header mismatch")
    if classifier_header and classifier_header != CLASSIFIER_CSV_COLUMNS:
        errors.append(f"{classifier_csv}: header mismatch")
    result_indexes = set(rows_by_task(result_rows))
    classifier_indexes = set(rows_by_task(classifier_rows))
    manual_review_csv = final_dir / "needs_manual_review.csv"
    _, manual_rows = load_csv(manual_review_csv)
    return (
        {
            "results_csv": str(results_csv),
            "classifier_results_csv": str(classifier_csv),
            "manual_review_csv": str(manual_review_csv),
            "results_rows": len(result_rows),
            "classifier_rows": len(classifier_rows),
            "manual_review_rows": len(manual_rows),
            "first_result_task_index": min(result_indexes) if result_indexes else None,
            "last_result_task_index": max(result_indexes) if result_indexes else None,
        },
        result_indexes,
        classifier_indexes,
        errors,
    )


def inspect_backlogs(ops_dir: Path, scoped_batch_files: set[str]) -> tuple[dict[str, Any], list[str]]:
    scoped_entries: list[str] = []
    summary: dict[str, Any] = {}
    for filename in BACKLOG_FILENAMES:
        path = ops_dir / filename
        header, rows = load_csv(path)
        scoped = [
            row for row in rows
            if str(row.get("batch_file") or "") in scoped_batch_files
            or batch_key(str(row.get("batch_file") or "")) in {batch_key(value) for value in scoped_batch_files}
        ]
        summary[filename] = {
            "exists": path.exists(),
            "rows": len(rows),
            "scoped_rows": len(scoped),
            "scoped_batches": [batch_key(str(row.get("batch_file") or "")) for row in scoped],
        }
        scoped_entries.extend(f"{filename}:{batch_key(str(row.get('batch_file') or ''))}" for row in scoped)
    return summary, scoped_entries


def run_checks(
    runs_dir: Path,
    final_dir: Path,
    ops_dir: Path,
    batch_files: list[str],
    require_final_coverage: bool,
    strict_metadata: bool,
) -> CheckReport:
    _, schedule_rows = load_schedule(runs_dir)
    scoped_rows = resolve_batch_scope(schedule_rows, batch_files)
    scoped_batch_files = {str(row.get("batch_file") or "") for row in scoped_rows}
    report = CheckReport(runs_dir=str(runs_dir), final_dir=str(final_dir))
    report.checked_batches = [batch_key(str(row.get("batch_file") or "")) for row in scoped_rows]

    expected_indexes: set[int] = set()
    for row in scoped_rows:
        summary, errors = check_batch_artifacts(row)
        report.batch_summaries.append(summary)
        report.artifact_errors.extend(errors)
        expected_indexes.update(expected_task_indexes(row))
        if summary["respawn_count"] > 0:
            report.warnings.append(
                f"{summary['batch_name']}: historical respawn_count={summary['respawn_count']}"
            )
        if summary["consecutive_no_progress_attempts"] > 0:
            report.warnings.append(
                f"{summary['batch_name']}: historical consecutive_no_progress_attempts="
                f"{summary['consecutive_no_progress_attempts']}"
            )
        if summary["nonzero_failure_counts"]:
            report.warnings.append(
                f"{summary['batch_name']}: historical failure_counts="
                + json.dumps(summary["nonzero_failure_counts"], ensure_ascii=False, sort_keys=True)
            )
        if summary["repair_backup_count"] > 0:
            report.warnings.append(
                f"{summary['batch_name']}: repair/quarantine backup files={summary['repair_backup_count']}"
            )
        if summary["status"] == "completed" and (
            summary["last_failure_type"] or summary["collect_failure_reason"]
        ):
            report.warnings.append(
                f"{summary['batch_name']}: completed but stale failure fields remain "
                f"(last_failure_type={summary['last_failure_type']!r}, "
                f"collect_failure_reason={summary['collect_failure_reason']!r})"
            )
        if strict_metadata:
            if row.get("status") != "completed":
                report.metadata_errors.append(f"{summary['batch_name']}: status is {row.get('status')!r}, expected completed")
            if row.get("queue_state") != "completed":
                report.metadata_errors.append(f"{summary['batch_name']}: queue_state is {row.get('queue_state')!r}, expected completed")
            if row.get("collect_state") != "done":
                report.metadata_errors.append(f"{summary['batch_name']}: collect_state is {row.get('collect_state')!r}, expected done")
        elif row.get("status") != "completed" or row.get("collect_state") != "done":
            report.warnings.append(
                f"{summary['batch_name']}: metadata not completed yet "
                f"(status={row.get('status')}, collect_state={row.get('collect_state')})"
            )

    final_summary, final_result_indexes, final_classifier_indexes, final_header_errors = load_final_indexes(final_dir)
    report.final_summary = final_summary
    report.final_errors.extend(final_header_errors)
    if require_final_coverage:
        missing_results = sorted(expected_indexes - final_result_indexes)
        missing_classifier = sorted(expected_indexes - final_classifier_indexes)
        if missing_results:
            report.final_errors.append(f"Final results.csv missing task_index {missing_results[:30]}")
        if missing_classifier:
            report.final_errors.append(f"Final classifier_results.csv missing task_index {missing_classifier[:30]}")

    backlog_summary, scoped_backlogs = inspect_backlogs(ops_dir, scoped_batch_files)
    report.backlog_summary = backlog_summary
    if strict_metadata and scoped_backlogs:
        report.metadata_errors.append("Scoped batches still appear in backlog files: " + ", ".join(scoped_backlogs))
    elif scoped_backlogs:
        report.warnings.append("Scoped batches still appear in backlog files: " + ", ".join(scoped_backlogs))
    return report


def write_report(report_path: Path, report: CheckReport, extra: dict[str, Any] | None = None) -> None:
    payload = report.to_dict()
    if extra:
        payload.update(extra)
    payload["updated_at"] = utc_now()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def print_report(label: str, report: CheckReport) -> None:
    status = "PASS" if not report.errors else "FAIL"
    print(f"{label}: {status}")
    print(f"runs_dir: {report.runs_dir}")
    print(f"checked_batches: {', '.join(report.checked_batches) if report.checked_batches else 'none'}")
    print(
        "final_rows: "
        f"results={report.final_summary.get('results_rows', 0)} "
        f"classifier={report.final_summary.get('classifier_rows', 0)} "
        f"manual_review={report.final_summary.get('manual_review_rows', 0)}"
    )
    print(
        f"errors: artifacts={len(report.artifact_errors)} "
        f"final={len(report.final_errors)} metadata={len(report.metadata_errors)}"
    )
    if report.errors:
        for error in report.errors[:50]:
            print(f"- {error}")
        if len(report.errors) > 50:
            print(f"- ... {len(report.errors) - 50} more")
    if report.warnings:
        print(f"warnings: {len(report.warnings)}")
        for warning in report.warnings[:20]:
            print(f"- {warning}")
        if len(report.warnings) > 20:
            print(f"- ... {len(report.warnings) - 20} more")


def run_collect(runs_dir: Path, batch_files: list[str], require_verification: bool) -> int:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "3_collect_results.py"),
        "--runs-dir",
        str(runs_dir),
        "--repair-identity-drift-in-place",
        "--fail-on-identity-drift",
    ]
    for batch_file in batch_files:
        command.extend(["--batch-file", batch_key(batch_file)])
    if not require_verification:
        command.append("--skip-verification")
    print("collect_command: " + " ".join(command))
    completed = subprocess.run(command, cwd=str(REPO_ROOT), check=False)
    return completed.returncode


def fix_metadata(runs_dir: Path, final_dir: Path, ops_dir: Path, batch_files: list[str]) -> dict[str, Any]:
    schedule_csv = runs_dir / "schedule.csv"
    schedule_header, schedule_rows = load_schedule(runs_dir)
    scoped_rows = resolve_batch_scope(schedule_rows, batch_files)
    scoped_batch_files = {str(row.get("batch_file") or "") for row in scoped_rows}
    scoped_basenames = {batch_key(value) for value in scoped_batch_files}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    shutil.copy2(schedule_csv, ops_backup_path(ops_dir, schedule_csv, stamp))
    collected_at = utc_now()

    updated_batches: list[str] = []
    for row in schedule_rows:
        batch_file = str(row.get("batch_file") or "")
        if batch_file not in scoped_batch_files and batch_key(batch_file) not in scoped_basenames:
            continue
        row["status"] = "completed"
        row["queue_state"] = "completed"
        row["collect_state"] = "done"
        row["collected_at"] = collected_at
        row["last_collected_attempt_index"] = row.get("attempt_index") or row.get("best_valid_attempt_index") or "1"
        row["collect_failure_reason"] = ""
        row["prepared_mode"] = ""
        row["prepared_reason"] = ""
        row["last_failure_type"] = ""
        row["last_rerun_reason"] = ""
        row["health_state"] = "completed"
        row["completion_mode"] = ""
        row["tail_retry_pending"] = ""
        row["next_eligible_retry_at"] = ""
        row["last_seen_classifier_rows"] = row.get("best_valid_classifier_rows") or row.get("task_count") or ""
        row["last_seen_result_rows"] = row.get("best_valid_result_rows") or row.get("task_count") or ""
        if not row.get("ready_to_collect_at"):
            row["ready_to_collect_at"] = row.get("best_valid_updated_at") or collected_at
        updated_batches.append(batch_key(batch_file))
    write_csv(schedule_csv, schedule_header, schedule_rows)

    backlog_removed: dict[str, int] = {}
    for filename in BACKLOG_FILENAMES:
        path = ops_dir / filename
        header, rows = load_csv(path)
        if not rows:
            continue
        shutil.copy2(path, ops_backup_path(ops_dir, path, stamp))
        kept = [
            row for row in rows
            if str(row.get("batch_file") or "") not in scoped_batch_files
            and batch_key(str(row.get("batch_file") or "")) not in scoped_basenames
        ]
        removed = len(rows) - len(kept)
        backlog_removed[filename] = removed
        if kept:
            write_csv(path, header, kept)
        else:
            path.unlink()

    return {
        "updated_batches": sorted(set(updated_batches)),
        "collected_at": collected_at,
        "backlog_removed": backlog_removed,
    }


def cleanup_intermediates(
    runs_dir: Path,
    ops_dir: Path,
    batch_files: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    _, schedule_rows = load_schedule(runs_dir)
    scoped_rows = resolve_batch_scope(schedule_rows, batch_files)
    delete_files: set[Path] = set()
    delete_dirs: set[Path] = set()

    for row in scoped_rows:
        run_dir = resolve_path(row.get("run_dir") or "")
        active_attempt = resolve_path(row.get("active_attempt") or run_dir)
        candidate_dirs = [run_dir, active_attempt, run_dir / "reconciled"]

        lease_path = run_dir / "active_attempt_lease.json"
        if lease_path.exists():
            delete_files.add(lease_path)

        for candidate_dir in candidate_dirs:
            if not candidate_dir.exists() or not candidate_dir.is_dir():
                continue
            for pattern in CLEANUP_FILE_PATTERNS:
                for path in candidate_dir.glob(pattern):
                    if path.is_file():
                        delete_files.add(path)
            for dir_name in CLEANUP_DIR_NAMES:
                path = candidate_dir / dir_name
                if path.exists() and path.is_dir():
                    delete_dirs.add(path)

    for filename in CLEANUP_RUN_ROOT_FILENAMES:
        path = runs_dir / filename
        if path.exists() and path.is_file():
            delete_files.add(path)

    for pattern in ["*.manual_collect_metadata_*.bak", "*.auto_check_metadata_*.bak"]:
        for path in runs_dir.glob(pattern):
            if path.is_file():
                delete_files.add(path)
        for path in ops_dir.glob(pattern):
            if path.is_file():
                delete_files.add(path)

    files = sorted(delete_files)
    dirs = sorted(delete_dirs, reverse=True)
    removed_files: list[str] = []
    removed_dirs: list[str] = []

    if not dry_run:
        for path in files:
            if path.exists() and path.is_file():
                path.unlink()
                removed_files.append(str(path))
        for path in dirs:
            if path.exists() and path.is_dir():
                shutil.rmtree(path)
                removed_dirs.append(str(path))

    return {
        "dry_run": dry_run,
        "candidate_file_count": len(files),
        "candidate_dir_count": len(dirs),
        "removed_file_count": len(removed_files),
        "removed_dir_count": len(removed_dirs),
        "candidate_files": [str(path) for path in files[:200]],
        "candidate_dirs": [str(path) for path in dirs[:50]],
        "removed_files": removed_files[:200],
        "removed_dirs": removed_dirs[:50],
    }


def update_latest_after_runs_dir_delete(runs_dir: Path, final_dir: Path, ops_dir: Path) -> dict[str, Any]:
    if not LATEST_JOB_JSON.exists():
        return {"latest_job_exists": False, "updated": False}
    try:
        data = read_json(LATEST_JOB_JSON)
    except (OSError, json.JSONDecodeError):
        data = {}
    raw_runs_dir = str(data.get("runs_dir") or data.get("run_dir") or "")
    if raw_runs_dir and resolve_path(raw_runs_dir).resolve() != runs_dir.resolve():
        return {
            "latest_job_exists": True,
            "updated": False,
            "reason": "latest_job_points_elsewhere",
            "latest_runs_dir": raw_runs_dir,
        }
    backup = ensure_ops_dir(ops_dir) / (
        LATEST_JOB_JSON.name
        + ".parallel_deleted_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        + ".bak"
    )
    shutil.copy2(LATEST_JOB_JSON, backup)
    updated = {
        "status": "final_outputs_only",
        "phase": "parallel_run_artifacts_deleted",
        "updated_at": utc_now(),
        "deleted_runs_dir": str(runs_dir),
        "final_dir": str(final_dir),
        "final_results_csv": str(final_dir / "results.csv"),
        "classifier_results_csv": str(final_dir / "classifier_results.csv"),
        "manual_review_csv": str(final_dir / "needs_manual_review.csv"),
        "checkpoint_json": str(final_dir / "checkpoint.json"),
        "previous_latest_job_backup": str(backup),
    }
    LATEST_JOB_JSON.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"latest_job_exists": True, "updated": True, "backup": str(backup)}


def delete_runs_dir_after_checks(
    runs_dir: Path,
    final_dir: Path,
    ops_dir: Path,
    report_payload: dict[str, Any],
) -> dict[str, Any]:
    if not runs_dir.exists():
        return {"deleted": False, "reason": "runs_dir_missing", "runs_dir": str(runs_dir)}
    try:
        runs_dir.relative_to(PART4_DIR / "agent_runs")
    except ValueError as exc:
        raise SystemExit(f"Refusing to delete runs_dir outside part4 agent_runs: {runs_dir}") from exc
    if runs_dir.name == "token_company":
        raise SystemExit(f"Refusing to delete final output directory: {runs_dir}")
    if not (runs_dir / "schedule.csv").exists():
        raise SystemExit(f"Refusing to delete runs_dir without schedule.csv marker: {runs_dir}")

    deletion_report = ensure_ops_dir(ops_dir) / (
        "parallel_run_deleted_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        + ".json"
    )
    deletion_report.parent.mkdir(parents=True, exist_ok=True)
    deletion_payload = {
        "deleted_at": utc_now(),
        "deleted_runs_dir": str(runs_dir),
        "final_dir": str(final_dir),
        "pre_delete_report": report_payload,
    }
    deletion_report.write_text(
        json.dumps(deletion_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    latest_update = update_latest_after_runs_dir_delete(runs_dir, final_dir, ops_dir)
    shutil.rmtree(runs_dir)
    return {
        "deleted": True,
        "deleted_runs_dir": str(runs_dir),
        "deletion_report": str(deletion_report),
        "latest_update": latest_update,
    }


def main() -> None:
    args = parse_args()
    runs_dir = (args.runs_dir or find_latest_runs_dir()).resolve()
    final_dir = args.final_dir.resolve()
    ops_dir = ensure_ops_dir(args.ops_dir.resolve())
    if args.report_json:
        report_path = args.report_json.resolve()
    elif args.delete_runs_dir:
        report_path = ops_report_path(
            ops_dir,
            runs_dir,
            "auto_check_collect_before_delete_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"),
        ).resolve()
    else:
        report_path = ops_report_path(ops_dir, runs_dir, "auto_check_collect_report").resolve()

    _, schedule_rows = load_schedule(runs_dir)
    scoped_rows = resolve_batch_scope(schedule_rows, args.batch_file)
    batch_files = [str(row.get("batch_file") or "") for row in scoped_rows]

    pre_report = run_checks(
        runs_dir=runs_dir,
        final_dir=final_dir,
        ops_dir=ops_dir,
        batch_files=batch_files,
        require_final_coverage=False,
        strict_metadata=False,
    )
    print_report("precheck", pre_report)
    if pre_report.artifact_errors:
        write_report(report_path, pre_report, {"phase": "precheck_failed"})
        raise SystemExit(1)

    collect_returncode: int | None = None
    if args.collect:
        collect_returncode = run_collect(
            runs_dir=runs_dir,
            batch_files=batch_files,
            require_verification=args.require_verification,
        )
        if collect_returncode != 0:
            write_report(
                report_path,
                pre_report,
                {"phase": "collect_failed", "collect_returncode": collect_returncode},
            )
            raise SystemExit(collect_returncode)

    require_final_coverage = args.require_final_coverage or args.collect or args.fix_metadata
    post_report = run_checks(
        runs_dir=runs_dir,
        final_dir=final_dir,
        ops_dir=ops_dir,
        batch_files=batch_files,
        require_final_coverage=require_final_coverage,
        strict_metadata=False,
    )
    print_report("postcheck", post_report)
    if post_report.artifact_errors or post_report.final_errors:
        write_report(
            report_path,
            post_report,
            {"phase": "postcheck_failed", "collect_returncode": collect_returncode},
        )
        raise SystemExit(1)

    metadata_fix_summary: dict[str, Any] | None = None
    if args.fix_metadata:
        metadata_fix_summary = fix_metadata(runs_dir, final_dir, ops_dir, batch_files)
        print("metadata_fix: applied")
        print(json.dumps(metadata_fix_summary, ensure_ascii=False, indent=2))

    cleanup_summary: dict[str, Any] | None = None
    if args.cleanup_intermediates or args.cleanup_dry_run:
        cleanup_summary = cleanup_intermediates(
            runs_dir=runs_dir,
            ops_dir=ops_dir,
            batch_files=batch_files,
            dry_run=args.cleanup_dry_run and not args.cleanup_intermediates,
        )
        print("cleanup_intermediates:")
        print(json.dumps(cleanup_summary, ensure_ascii=False, indent=2))

    final_report = run_checks(
        runs_dir=runs_dir,
        final_dir=final_dir,
        ops_dir=ops_dir,
        batch_files=batch_files,
        require_final_coverage=require_final_coverage,
        strict_metadata=args.strict_metadata or args.fix_metadata,
    )
    print_report("finalcheck", final_report)
    delete_summary: dict[str, Any] | None = None
    if args.delete_runs_dir:
        if final_report.errors:
            print("delete_runs_dir: skipped because finalcheck failed")
        else:
            delete_summary = delete_runs_dir_after_checks(
                runs_dir=runs_dir,
                final_dir=final_dir,
                ops_dir=ops_dir,
                report_payload=final_report.to_dict(),
            )
            print("delete_runs_dir:")
            print(json.dumps(delete_summary, ensure_ascii=False, indent=2))
    write_report(
        report_path,
        final_report,
        {
            "phase": "completed" if not final_report.errors else "failed",
            "collect_returncode": collect_returncode,
            "metadata_fix": metadata_fix_summary,
            "cleanup_intermediates": cleanup_summary,
            "delete_runs_dir": delete_summary,
        },
    )
    if final_report.errors:
        raise SystemExit(1)
    print(f"report_json: {report_path}")


if __name__ == "__main__":
    main()
