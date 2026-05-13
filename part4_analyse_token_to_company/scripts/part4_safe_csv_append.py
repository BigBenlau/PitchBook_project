#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import tempfile
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent

IMMUTABLE_IDENTITY_FIELDS = [
    "task_index",
    "canonical_slug",
    "token_symbol",
    "token_name",
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

SCHEMA_TO_COLUMNS = {
    "classifier": CLASSIFIER_CSV_COLUMNS,
    "result": RESULT_CSV_COLUMNS,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely append or upsert a structured part4 classifier/result row into a CSV.",
    )
    parser.add_argument(
        "--schema",
        choices=sorted(SCHEMA_TO_COLUMNS),
        required=True,
        help="Target row schema: classifier or result.",
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        required=True,
        help="Target CSV path to update.",
    )
    parser.add_argument(
        "--row-json",
        default="",
        help="Inline JSON object payload for the row.",
    )
    parser.add_argument(
        "--row-json-file",
        type=Path,
        default=None,
        help="Path to a JSON file containing the row object.",
    )
    parser.add_argument(
        "--tasks-file",
        type=Path,
        default=None,
        help="Optional tasks.jsonl path. When provided, immutable identity fields are enforced from the task row.",
    )
    parser.add_argument(
        "--upsert-key",
        default="task_index",
        help="Primary key column used to replace an existing row. Defaults to task_index.",
    )
    parser.add_argument(
        "--attempt-metadata",
        type=Path,
        default=None,
        help=(
            "Optional attempt_metadata.json path. When provided with --tasks-file, preserved "
            "recovery-prefix rows cannot be rewritten."
        ),
    )
    return parser.parse_args()


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def load_row_payload(args: argparse.Namespace) -> dict[str, object]:
    if args.row_json_file is not None:
        payload = json.loads(resolve_path(args.row_json_file).read_text(encoding="utf-8"))
    elif args.row_json:
        payload = json.loads(args.row_json)
    else:
        raise SystemExit("Provide either --row-json or --row-json-file.")
    if not isinstance(payload, dict):
        raise SystemExit("Row payload must be a JSON object.")
    return payload


def parse_task_index(value: object) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def load_tasks(path: Path) -> list[dict[str, object]]:
    tasks: list[dict[str, object]] = []
    with resolve_path(path).open("r", encoding="utf-8") as infile:
        for line in infile:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                continue
            tasks.append(payload)
    return tasks


def load_tasks_by_index(tasks: list[dict[str, object]]) -> dict[int, dict[str, object]]:
    indexed: dict[int, dict[str, object]] = {}
    for payload in tasks:
        task_index = parse_task_index(payload.get("task_index"))
        if task_index is None:
            continue
        indexed[task_index] = payload
    return indexed


def load_attempt_metadata(path: Path) -> dict[str, object]:
    payload = json.loads(resolve_path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Attempt metadata payload must be a JSON object.")
    return payload


def normalize_row(
    payload: dict[str, object],
    *,
    schema: str,
    tasks_by_index: dict[int, dict[str, object]] | None,
) -> dict[str, str]:
    columns = SCHEMA_TO_COLUMNS[schema]
    unexpected = sorted(set(payload) - set(columns))
    if unexpected:
        raise SystemExit(f"Unexpected columns for {schema} row: {', '.join(unexpected)}")

    task_index = parse_task_index(payload.get("task_index"))
    if task_index is None:
        raise SystemExit("Row payload must include task_index.")

    row = {column: "" for column in columns}
    for column in columns:
        value = payload.get(column, "")
        row[column] = "" if value is None else str(value)

    if tasks_by_index is not None:
        task = tasks_by_index.get(task_index)
        if task is None:
            raise SystemExit(f"task_index={task_index} not found in tasks file.")
        for field in IMMUTABLE_IDENTITY_FIELDS:
            row[field] = str(task.get(field, row.get(field, "")))

    return row


def validate_preserved_prefix_guard(
    *,
    task_index: int,
    tasks: list[dict[str, object]] | None,
    attempt_metadata: dict[str, object] | None,
) -> None:
    if not tasks or not attempt_metadata:
        return
    prefix_rows = parse_task_index(attempt_metadata.get("attempt_start_prefix_rows")) or 0
    if prefix_rows <= 0:
        return
    preserved_task_indexes: set[int] = set()
    for task in tasks[:prefix_rows]:
        preserved_task_index = parse_task_index(task.get("task_index"))
        if preserved_task_index is not None:
            preserved_task_indexes.add(preserved_task_index)
    if task_index in preserved_task_indexes:
        attempt_mode = str(attempt_metadata.get("attempt_mode") or "recovery")
        raise SystemExit(
            f"task_index={task_index} belongs to the preserved prefix for attempt_mode={attempt_mode} "
            "and cannot be rewritten in this attempt."
        )


def read_existing_rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        header = list(reader.fieldnames or [])
        if header != columns:
            raise SystemExit(f"{path}: header mismatch")
        return [{column: row.get(column, "") for column in columns} for row in reader]


def write_rows(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=str(path.parent),
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as outfile:
            temp_path = Path(outfile.name)
            writer = csv.DictWriter(outfile, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
            outfile.flush()
            os.fsync(outfile.fileno())
        temp_path.replace(path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def main() -> None:
    args = parse_args()
    if args.attempt_metadata is not None and args.tasks_file is None:
        raise SystemExit("--attempt-metadata requires --tasks-file.")
    columns = SCHEMA_TO_COLUMNS[args.schema]
    csv_path = resolve_path(args.csv_path)
    tasks = load_tasks(args.tasks_file) if args.tasks_file is not None else None
    tasks_by_index = load_tasks_by_index(tasks) if tasks is not None else None
    attempt_metadata = load_attempt_metadata(args.attempt_metadata) if args.attempt_metadata is not None else None
    payload = load_row_payload(args)
    row = normalize_row(payload, schema=args.schema, tasks_by_index=tasks_by_index)
    task_index = parse_task_index(row.get("task_index"))
    if task_index is None:
        raise SystemExit("Normalized row is missing a valid task_index.")
    validate_preserved_prefix_guard(
        task_index=task_index,
        tasks=tasks,
        attempt_metadata=attempt_metadata,
    )

    existing_rows = read_existing_rows(csv_path, columns)
    upsert_key = args.upsert_key
    if upsert_key not in columns:
        raise SystemExit(f"--upsert-key must be one of: {', '.join(columns)}")
    row_key = row.get(upsert_key, "")
    if not row_key:
        raise SystemExit(f"Row payload must provide non-empty {upsert_key}.")

    updated_rows: list[dict[str, str]] = []
    replaced = False
    for existing in existing_rows:
        if existing.get(upsert_key, "") == row_key:
            updated_rows.append(row)
            replaced = True
        else:
            updated_rows.append(existing)
    if not replaced:
        updated_rows.append(row)

    write_rows(csv_path, columns, updated_rows)
    action = "replaced" if replaced else "appended"
    print(
        json.dumps(
            {
                "status": "ok",
                "schema": args.schema,
                "csv_path": str(csv_path),
                "task_index": row.get("task_index", ""),
                "action": action,
                "row_count": len(updated_rows),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
