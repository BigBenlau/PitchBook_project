#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from result_schema import RESULT_CSV_COLUMNS, parse_json_list


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
DEFAULT_FINAL_DIR = PART5_DIR / "agent_runs" / "crypto_company"
DEFAULT_RESULTS_CSV = DEFAULT_FINAL_DIR / "results.csv"
DEFAULT_WITH_TICKER_CSV = DEFAULT_FINAL_DIR / "results_with_ticker.csv"
DEFAULT_WITHOUT_TICKER_CSV = DEFAULT_FINAL_DIR / "results_without_ticker.csv"
DEFAULT_RULE_B_REVIEW_CSV = DEFAULT_FINAL_DIR / "rule_b_needs_manual_review.csv"
DEFAULT_CHECKPOINT_JSON = DEFAULT_FINAL_DIR / "rule_b_backfill_checkpoint.json"
DEFAULT_LATEST_JSON = PART5_DIR / "agent_runs" / "crypto_company_rule_b_longrun_latest.json"
DEFAULT_ACTIVE_RUN_JSON = PART5_DIR / "agent_runs" / "crypto_company_rule_b_active_run.json"
SCHEDULE_CSV_NAME = "schedule.csv"

RULE_B_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "include_rule_B",
    "rule_B_token_results",
    "rule_B_decision_reason",
    "rule_B_needs_manual_review",
]
ALLOWED_INCLUDE = {"yes", "no"}
ALLOWED_YES_NO = {"yes", "no"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate and overlay Part5 Rule B-only worker outputs into final results.csv.")
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--batch-file", action="append", default=[], help="Optional batch basename or schedule batch_file to collect.")
    parser.add_argument("--results-csv", type=Path, default=DEFAULT_RESULTS_CSV)
    parser.add_argument("--with-ticker-csv", type=Path, default=DEFAULT_WITH_TICKER_CSV)
    parser.add_argument("--without-ticker-csv", type=Path, default=DEFAULT_WITHOUT_TICKER_CSV)
    parser.add_argument("--rule-b-review-csv", type=Path, default=DEFAULT_RULE_B_REVIEW_CSV)
    parser.add_argument("--checkpoint-json", type=Path, default=DEFAULT_CHECKPOINT_JSON)
    parser.add_argument("--latest-json", type=Path, default=DEFAULT_LATEST_JSON)
    parser.add_argument("--active-run-json", type=Path, default=DEFAULT_ACTIVE_RUN_JSON)
    parser.add_argument("--allow-stale-run", action="store_true", help="Allow overlay from a non-active run. Use only for manual repair.")
    parser.add_argument("--allow-overwrite-completed", action="store_true", help="Allow replacing rows whose Rule B fields are already completed.")
    parser.add_argument("--lint-only", action="store_true")
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc


def guard_active_run(args: argparse.Namespace) -> None:
    if args.allow_stale_run:
        return
    current_runs_dir = args.runs_dir.resolve()
    for metadata_path in [args.active_run_json, args.latest_json]:
        metadata = read_json(metadata_path)
        if not metadata:
            continue
        expected_raw = str(metadata.get("runs_dir") or "").strip()
        if not expected_raw:
            continue
        expected_runs_dir = Path(expected_raw).resolve()
        if current_runs_dir != expected_runs_dir:
            raise SystemExit(
                "Refusing to overlay Rule B output from a non-active run: "
                f"runs_dir={current_runs_dir} active_runs_dir={expected_runs_dir} metadata={metadata_path}"
            )
        return


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def schedule_rows(runs_dir: Path, batch_filters: set[str]) -> list[dict[str, str]]:
    _, rows = read_csv(runs_dir / SCHEDULE_CSV_NAME)
    if not batch_filters:
        return rows
    selected = []
    for row in rows:
        batch_value = row.get("batch_file", "")
        if batch_value in batch_filters or Path(batch_value).name in batch_filters:
            selected.append(row)
    return selected


def is_http_url(value: Any) -> bool:
    raw = str(value or "").strip()
    return raw.startswith("http://") or raw.startswith("https://")


def validate_token_objects(value: str, *, context: str) -> list[str]:
    errors: list[str] = []
    parsed = parse_json_list(value)
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            errors.append(f"{context}: token object {index} is not an object")
            continue
        for key in ["token_symbol", "token_name", "token_url", "reason", "evidence_urls", "evidence_source_types"]:
            if key not in item:
                errors.append(f"{context}: token object {index} missing {key}")
        evidence_urls = item.get("evidence_urls")
        if not isinstance(evidence_urls, list) or not evidence_urls or not all(is_http_url(url) for url in evidence_urls):
            errors.append(f"{context}: token object {index} evidence_urls must be non-empty HTTP(S) URLs")
        source_types = item.get("evidence_source_types")
        if not isinstance(source_types, list) or not source_types:
            errors.append(f"{context}: token object {index} evidence_source_types must be a non-empty list")
        if isinstance(evidence_urls, list) and isinstance(source_types, list) and len(evidence_urls) != len(source_types):
            errors.append(f"{context}: token object {index} evidence_urls/evidence_source_types length mismatch")
    return errors


def validate_overlay_rows(schedule_row: dict[str, str]) -> tuple[list[dict[str, str]], list[str]]:
    results_path = Path(schedule_row["rule_b_results_csv"])
    tasks_path = Path(schedule_row["tasks_file"])
    header, rows = read_csv(results_path)
    tasks = load_jsonl(tasks_path)
    errors: list[str] = []
    if header != RULE_B_COLUMNS:
        errors.append(f"{results_path}: header mismatch")
    if len(rows) != len(tasks):
        errors.append(f"{results_path}: expected {len(tasks)} rows, found {len(rows)}")
    tasks_by_index = {str(task.get("task_index", "")): task for task in tasks}
    seen: set[str] = set()
    for row in rows:
        task_index = str(row.get("task_index", "")).strip()
        context = f"{results_path}: task_index={task_index}"
        task = tasks_by_index.get(task_index)
        if not task:
            errors.append(f"{context}: task not found in tasks file")
            continue
        seen.add(task_index)
        if row.get("company_id") != str(task.get("company_id", "")):
            errors.append(f"{context}: company_id mismatch")
        if row.get("company_name") != str(task.get("company_name", "")):
            errors.append(f"{context}: company_name mismatch")
        include = (row.get("include_rule_B") or "").strip()
        if include not in ALLOWED_INCLUDE:
            errors.append(f"{context}: include_rule_B must be yes or no")
        needs_review = (row.get("rule_B_needs_manual_review") or "").strip()
        if needs_review not in ALLOWED_YES_NO:
            errors.append(f"{context}: rule_B_needs_manual_review must be yes or no")
        token_results = parse_json_list(row.get("rule_B_token_results", ""))
        if include == "yes" and not token_results:
            errors.append(f"{context}: include_rule_B=yes requires non-empty rule_B_token_results")
        if include == "no" and token_results:
            errors.append(f"{context}: include_rule_B=no requires [] rule_B_token_results")
        if not (row.get("rule_B_decision_reason") or "").strip():
            errors.append(f"{context}: rule_B_decision_reason is required")
        errors.extend(validate_token_objects(row.get("rule_B_token_results", ""), context=context))
    missing = set(tasks_by_index) - seen
    if missing:
        errors.append(f"{results_path}: missing task indexes {sorted(missing)[:10]}")
    return rows, errors


def has_token(row: dict[str, str]) -> bool:
    return bool(parse_json_list(row.get("token_results", "")))


def main() -> None:
    args = parse_args()
    guard_active_run(args)
    filters = {Path(value).name for value in args.batch_file}
    selected_schedule_rows = schedule_rows(args.runs_dir, filters)
    if not selected_schedule_rows:
        raise SystemExit("No schedule rows selected.")

    all_overlay_rows: list[dict[str, str]] = []
    errors: list[str] = []
    for schedule_row in selected_schedule_rows:
        rows, row_errors = validate_overlay_rows(schedule_row)
        errors.extend(row_errors)
        all_overlay_rows.extend(rows)
    if errors:
        print("lint: FAIL")
        for error in errors[:200]:
            print(f"- {error}")
        raise SystemExit(1)
    print(f"lint: PASS batches={len(selected_schedule_rows)} overlay_rows={len(all_overlay_rows)}")
    if args.lint_only:
        return

    header, final_rows = read_csv(args.results_csv)
    if header != RESULT_CSV_COLUMNS:
        raise SystemExit(f"{args.results_csv}: unsupported header")
    overlay_by_task = {row["task_index"]: row for row in all_overlay_rows}
    updated = 0
    review_rows: list[dict[str, str]] = []
    for row in final_rows:
        overlay = overlay_by_task.get(row.get("task_index", ""))
        if not overlay:
            continue
        existing_include = (row.get("include_rule_B") or "").strip()
        if existing_include in {"yes", "no"} and not args.allow_overwrite_completed:
            continue
        row["include_rule_B"] = overlay["include_rule_B"]
        row["rule_B_token_results"] = overlay["rule_B_token_results"]
        row["rule_B_decision_reason"] = overlay["rule_B_decision_reason"]
        updated += 1
        if overlay.get("rule_B_needs_manual_review") == "yes":
            review_rows.append({**row, "rule_B_needs_manual_review": "yes"})

    write_csv(args.results_csv, RESULT_CSV_COLUMNS, final_rows)
    write_csv(args.with_ticker_csv, RESULT_CSV_COLUMNS, [row for row in final_rows if has_token(row)])
    write_csv(args.without_ticker_csv, RESULT_CSV_COLUMNS, [row for row in final_rows if not has_token(row)])

    review_fields = RESULT_CSV_COLUMNS + ["rule_B_needs_manual_review"]
    existing_review_rows: list[dict[str, str]] = []
    if args.rule_b_review_csv.exists():
        _, existing_review_rows = read_csv(args.rule_b_review_csv)
    by_task = {row.get("task_index", ""): row for row in existing_review_rows}
    for row in review_rows:
        by_task[row.get("task_index", "")] = row
    write_csv(args.rule_b_review_csv, review_fields, list(by_task.values()))

    completed_rule_b = sum(1 for row in final_rows if (row.get("include_rule_B") or "").strip() in {"yes", "no"})
    checkpoint = {
        "updated_at": utc_now(),
        "updated_rows_this_collect": updated,
        "completed_rule_b_rows": completed_rule_b,
        "total_final_rows": len(final_rows),
        "pending_rule_b_rows": len(final_rows) - completed_rule_b,
        "runs_dir": str(args.runs_dir),
    }
    args.checkpoint_json.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"overlay: PASS updated_rows={updated}")
    print(f"completed_rule_b_rows={completed_rule_b}")
    print(f"pending_rule_b_rows={len(final_rows) - completed_rule_b}")


if __name__ == "__main__":
    main()
