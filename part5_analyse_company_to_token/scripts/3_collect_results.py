#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
DEFAULT_RUNS_DIR = PART5_DIR / "agent_runs" / "crypto_company_parallel"

RESULT_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "normalized_domain",
    "project_name",
    "project_url",
    "status",
    "completed_at",
    "token_ticker",
    "token_name",
    "token_url",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
]

LIST_COLUMNS = [
    "project_name",
    "project_url",
    "token_ticker",
    "token_name",
    "token_url",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect part5 worker result CSVs and export manual-review rows.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Worker runs directory containing schedule.csv and per-batch results.csv files.",
    )
    parser.add_argument(
        "--schedule-csv",
        type=Path,
        default=None,
        help="Schedule CSV. Defaults to <runs-dir>/schedule.csv.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Merged results CSV. Defaults to <runs-dir>/results.csv.",
    )
    parser.add_argument(
        "--manual-review-csv",
        type=Path,
        default=None,
        help="Manual review CSV. Defaults to <runs-dir>/needs_manual_review.csv.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write outputs even when some scheduled result rows are missing.",
    )
    return parser.parse_args()


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def load_schedule(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        return list(reader)


def load_result_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows = [repair_extra_columns(row, fieldnames) for row in reader]
        return fieldnames, rows


def repair_extra_columns(row: dict, fieldnames: list[str]) -> dict[str, str]:
    """Repair rows where unquoted commas split has_token_evidence.

    Worker outputs are CSV, but short evidence sometimes contains a comma without
    quoting. In that case csv.DictReader stores trailing cells under None. The
    stable fields after evidence are the final four result columns, so merge the
    overflow back into has_token_evidence.
    """
    if None not in row:
        return {field: row.get(field, "") for field in fieldnames}

    values = [row.get(field, "") for field in fieldnames] + list(row.get(None) or [])
    if len(values) <= len(fieldnames):
        return {field: values[index] if index < len(values) else "" for index, field in enumerate(fieldnames)}

    evidence_index = fieldnames.index("has_token_evidence")
    tail_count = 4
    fixed_values = (
        values[:evidence_index]
        + [",".join(values[evidence_index : len(values) - tail_count])]
        + values[len(values) - tail_count :]
    )
    return {
        field: fixed_values[index] if index < len(fixed_values) else ""
        for index, field in enumerate(fieldnames)
    }


def parse_task_index(row: dict[str, str], source: Path) -> int:
    raw = (row.get("task_index") or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Invalid task_index in {source}: {raw!r}") from None


def validate_result_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    for column in LIST_COLUMNS:
        value = (row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
            continue
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            errors.append(f"{column} is not valid JSON: {value!r}")
            continue
        if not isinstance(parsed, list):
            errors.append(f"{column} is not a JSON list: {value!r}")
    if row.get("needs_manual_review") not in {"yes", "no"}:
        errors.append("needs_manual_review must be yes or no")
    if row.get("confidence") not in {"high", "medium", "low"}:
        errors.append("confidence must be high, medium, or low")
    if row.get("status") != "completed":
        errors.append("status must be completed")
    if errors:
        task_index = row.get("task_index", "")
        company_name = row.get("company_name", "")
        return [f"{source}: task_index={task_index} company={company_name}: {error}" for error in errors]
    return []


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=RESULT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    runs_dir = args.runs_dir.resolve()
    schedule_csv = ensure_file(
        args.schedule_csv.resolve() if args.schedule_csv else runs_dir / "schedule.csv",
        "Schedule CSV",
    )
    output_csv = args.output_csv.resolve() if args.output_csv else runs_dir / "results.csv"
    manual_review_csv = (
        args.manual_review_csv.resolve()
        if args.manual_review_csv
        else runs_dir / "needs_manual_review.csv"
    )

    schedule_rows = load_schedule(schedule_csv)
    if not schedule_rows:
        raise SystemExit("Schedule has no rows.")

    merged_rows: list[dict[str, str]] = []
    validation_errors: list[str] = []
    expected_total = 0
    duplicate_task_indexes: set[int] = set()
    seen_task_indexes: set[int] = set()

    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        expected_total += task_count
        results_csv = ensure_file(Path(schedule_row["results_csv"]), "Worker results CSV")
        header, rows = load_result_rows(results_csv)
        if header != RESULT_CSV_COLUMNS:
            validation_errors.append(f"{results_csv}: header mismatch")
        if len(rows) != task_count:
            validation_errors.append(
                f"{results_csv}: expected {task_count} rows, found {len(rows)}"
            )
        for row in rows:
            task_index = parse_task_index(row, results_csv)
            if task_index in seen_task_indexes:
                duplicate_task_indexes.add(task_index)
            seen_task_indexes.add(task_index)
            validation_errors.extend(validate_result_row(row, results_csv))
            merged_rows.append({column: row.get(column, "") for column in RESULT_CSV_COLUMNS})

    if duplicate_task_indexes:
        validation_errors.append(
            "Duplicate task_index values: "
            + ",".join(str(value) for value in sorted(duplicate_task_indexes))
        )

    merged_rows.sort(key=lambda row: int(row["task_index"]))
    manual_rows = [
        row for row in merged_rows if (row.get("needs_manual_review") or "").strip() == "yes"
    ]

    if validation_errors and not args.allow_partial:
        print("Validation errors:")
        for error in validation_errors[:50]:
            print(f"- {error}")
        if len(validation_errors) > 50:
            print(f"- ... {len(validation_errors) - 50} more")
        raise SystemExit("Refusing to write outputs. Pass --allow-partial to write anyway.")

    write_csv(output_csv, merged_rows)
    write_csv(manual_review_csv, manual_rows)

    print(f"Schedule CSV: {schedule_csv}")
    print(f"Expected rows: {expected_total}")
    print(f"Merged rows: {len(merged_rows)}")
    print(f"Manual review rows: {len(manual_rows)}")
    print(f"Validation errors: {len(validation_errors)}")
    print(f"Merged output CSV: {output_csv}")
    print(f"Manual review CSV: {manual_review_csv}")


if __name__ == "__main__":
    main()
