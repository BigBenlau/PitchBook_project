#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_DIR.parent

DEFAULT_RUNS_DIR = PART5_DIR / "agent_runs" / "crypto_company_parallel"
DEFAULT_FINAL_DIR = PART5_DIR / "agent_runs" / "crypto_company"

RESULT_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "normalized_domain",
    "company_type",
    "crypto_project_likelihood",
    "project_search_required",
    "project_search_reason",
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

CLASSIFIER_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "normalized_domain",
    "company_type",
    "crypto_project_likelihood",
    "search_tier",
    "project_search_required",
    "risk_flags",
    "classifier_reason",
]

LIST_COLUMNS = [
    "project_name",
    "project_url",
    "token_ticker",
    "token_name",
    "token_url",
]

ALLOWED_COMPANY_TYPES = {
    "protocol_or_network",
    "dapp_or_product",
    "exchange_or_broker",
    "wallet_or_custody",
    "mining_or_validator",
    "infrastructure_or_data",
    "security_or_compliance",
    "service_provider",
    "investment_or_holdings",
    "media_or_education",
    "gaming_or_nft",
    "traditional_business",
    "unclear",
}

ALLOWED_LIKELIHOODS = {"high", "medium", "low", "none", "unclear"}
ALLOWED_YES_NO = {"yes", "no"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_SEARCH_TIERS = {"full", "light", "skip_candidate"}

VERIFICATION_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "worker_token_ticker",
    "verifier_token_ticker",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_urls",
    "recommended_action",
]

ALLOWED_VERDICTS = {
    "pass",
    "suspected_missing_token",
    "suspected_extra_token",
    "wrong_project_mapping",
    "non_fungible_or_stock_ticker",
    "search_should_not_have_been_skipped",
    "insufficient_evidence",
}

ALLOWED_VERIFICATION_ACTIONS = {
    "accept_worker_row",
    "edit_row",
    "mark_manual_review",
    "rerun_company",
    "rerun_batch",
    "update_prompt_or_process",
}

BLOCKING_VERIFICATION_ACTIONS = {
    "edit_row",
    "rerun_company",
    "rerun_batch",
    "update_prompt_or_process",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect v2 part5 worker result CSVs, enforce verifier gates, and update final outputs.",
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
        help="Final merged results CSV. Defaults to part5_analyse_company_to_token/agent_runs/crypto_company/results.csv.",
    )
    parser.add_argument(
        "--classifier-results-csv",
        type=Path,
        default=None,
        help="Final classifier/router CSV. Defaults to part5_analyse_company_to_token/agent_runs/crypto_company/classifier_results.csv.",
    )
    parser.add_argument(
        "--manual-review-csv",
        type=Path,
        default=None,
        help="Manual review CSV. Defaults to part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv.",
    )
    parser.add_argument(
        "--verification-findings-csv",
        type=Path,
        default=None,
        help="Merged verifier report CSV. Defaults to part5_analyse_company_to_token/agent_runs/crypto_company/verification_findings.csv.",
    )
    parser.add_argument(
        "--checkpoint-json",
        type=Path,
        default=None,
        help="Checkpoint JSON. Defaults to part5_analyse_company_to_token/agent_runs/crypto_company/checkpoint.json.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write outputs even when scheduled worker rows are missing or validation errors exist.",
    )
    parser.add_argument(
        "--allow-unresolved-verification",
        action="store_true",
        help="Allow merge when verifier recommends edit/rerun/process updates. Intended only for debug.",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip mandatory verifier checks. Intended only for legacy/debug runs.",
    )
    parser.add_argument(
        "--replace-output",
        action="store_true",
        help="Replace existing final results instead of appending to a v2 final CSV.",
    )
    return parser.parse_args()


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows = [repair_extra_columns(row, fieldnames) for row in reader]
        return fieldnames, rows


def repair_extra_columns(row: dict, fieldnames: list[str]) -> dict[str, str]:
    """Repair rows where unquoted commas split has_token_evidence."""
    if None not in row:
        return {field: row.get(field, "") for field in fieldnames}

    values = [row.get(field, "") for field in fieldnames] + list(row.get(None) or [])
    if len(values) <= len(fieldnames):
        return {field: values[index] if index < len(values) else "" for index, field in enumerate(fieldnames)}

    if "has_token_evidence" not in fieldnames:
        return {field: row.get(field, "") for field in fieldnames}

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


def load_schedule(path: Path) -> list[dict[str, str]]:
    header, rows = load_csv(path)
    if not header:
        raise SystemExit(f"Schedule CSV has no header: {path}")
    return rows


def parse_task_index(row: dict[str, str], source: Path) -> int:
    raw = (row.get("task_index") or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Invalid task_index in {source}: {raw!r}") from None


def parse_batch_number(batch_file: str) -> int:
    stem = Path(batch_file).stem
    try:
        return int(stem.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def validate_json_list(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def json_list_length(value: str) -> int:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return -1
    return len(parsed) if isinstance(parsed, list) else -1


def validate_result_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    for column in LIST_COLUMNS:
        value = (row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
        elif not validate_json_list(value):
            errors.append(f"{column} is not a valid JSON list: {value!r}")

    if row.get("status") != "completed":
        errors.append("status must be completed")
    if row.get("company_type") not in ALLOWED_COMPANY_TYPES:
        errors.append("company_type uses an invalid value")
    if row.get("crypto_project_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("crypto_project_likelihood uses an invalid value")
    if row.get("project_search_required") not in ALLOWED_YES_NO:
        errors.append("project_search_required must be yes or no")
    if row.get("needs_manual_review") not in ALLOWED_YES_NO:
        errors.append("needs_manual_review must be yes or no")
    if row.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append("confidence must be high, medium, or low")
    if row.get("project_search_required") == "no" and not (row.get("project_search_reason") or "").strip():
        errors.append("project_search_required=no requires project_search_reason")

    token_count = json_list_length(row.get("token_ticker", ""))
    if token_count > 0 and not ((row.get("token_url") or "").strip() or (row.get("evidence_urls") or "").strip()):
        errors.append("token_ticker is non-empty but token_url/evidence_urls are empty")

    if errors:
        task_index = row.get("task_index", "")
        company_name = row.get("company_name", "")
        return [f"{source}: task_index={task_index} company={company_name}: {error}" for error in errors]
    return []


def validate_classifier_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    if row.get("company_type") not in ALLOWED_COMPANY_TYPES:
        errors.append("company_type uses an invalid value")
    if row.get("crypto_project_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("crypto_project_likelihood uses an invalid value")
    search_tier = row.get("search_tier")
    project_search_required = row.get("project_search_required")
    if search_tier not in ALLOWED_SEARCH_TIERS:
        errors.append("search_tier uses an invalid value")
    if project_search_required not in ALLOWED_YES_NO:
        errors.append("project_search_required must be yes or no")
    if search_tier in {"full", "light"} and project_search_required != "yes":
        errors.append("full/light search_tier requires project_search_required=yes")
    if search_tier == "skip_candidate" and project_search_required != "no":
        errors.append("skip_candidate requires project_search_required=no")
    if search_tier == "skip_candidate" and row.get("crypto_project_likelihood") in {"high", "medium", "unclear"}:
        errors.append("skip_candidate cannot have high, medium, or unclear likelihood")
    risk_flags = (row.get("risk_flags") or "").strip()
    if not risk_flags:
        errors.append("risk_flags is blank")
    elif not validate_json_list(risk_flags):
        errors.append(f"risk_flags is not a valid JSON list: {risk_flags!r}")
    if not (row.get("classifier_reason") or "").strip():
        errors.append("classifier_reason is blank")

    if errors:
        task_index = row.get("task_index", "")
        company_name = row.get("company_name", "")
        return [f"{source}: task_index={task_index} company={company_name}: {error}" for error in errors]
    return []


def collect_classifier_rows(schedule_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str], dict[int, dict[str, str]]]:
    classifier_rows: list[dict[str, str]] = []
    validation_errors: list[str] = []
    seen_task_indexes: set[int] = set()
    duplicate_task_indexes: set[int] = set()

    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        classifier_raw = (schedule_row.get("classifier_results_csv") or "").strip()
        if not classifier_raw:
            validation_errors.append(f"{schedule_row.get('batch_file')}: missing classifier_results_csv in schedule")
            continue
        classifier_csv = ensure_file(resolve_path(classifier_raw), "Classifier results CSV")
        header, rows = load_csv(classifier_csv)
        if header != CLASSIFIER_CSV_COLUMNS:
            validation_errors.append(f"{classifier_csv}: header mismatch")
        if len(rows) != task_count:
            validation_errors.append(f"{classifier_csv}: expected {task_count} rows, found {len(rows)}")
        for row in rows:
            task_index = parse_task_index(row, classifier_csv)
            if task_index in seen_task_indexes:
                duplicate_task_indexes.add(task_index)
            seen_task_indexes.add(task_index)
            validation_errors.extend(validate_classifier_row(row, classifier_csv))
            classifier_rows.append({column: row.get(column, "") for column in CLASSIFIER_CSV_COLUMNS})

    if duplicate_task_indexes:
        validation_errors.append(
            "Duplicate classifier task_index values: "
            + ",".join(str(value) for value in sorted(duplicate_task_indexes))
        )

    classifier_rows.sort(key=lambda row: int(row["task_index"]))
    return classifier_rows, validation_errors, {int(row["task_index"]): row for row in classifier_rows}


def collect_worker_rows(
    schedule_rows: list[dict[str, str]],
    classifier_rows_by_task: dict[int, dict[str, str]],
) -> tuple[list[dict[str, str]], list[str], int]:
    merged_rows: list[dict[str, str]] = []
    validation_errors: list[str] = []
    expected_total = 0
    duplicate_task_indexes: set[int] = set()
    seen_task_indexes: set[int] = set()

    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        expected_total += task_count
        results_csv = ensure_file(resolve_path(schedule_row["results_csv"]), "Worker results CSV")
        header, rows = load_csv(results_csv)
        if header != RESULT_CSV_COLUMNS:
            validation_errors.append(f"{results_csv}: header mismatch")
        if len(rows) != task_count:
            validation_errors.append(f"{results_csv}: expected {task_count} rows, found {len(rows)}")
        for row in rows:
            task_index = parse_task_index(row, results_csv)
            if task_index in seen_task_indexes:
                duplicate_task_indexes.add(task_index)
            seen_task_indexes.add(task_index)
            validation_errors.extend(validate_result_row(row, results_csv))
            classifier_row = classifier_rows_by_task.get(task_index)
            if not classifier_row:
                validation_errors.append(f"{results_csv}: task_index={task_index}: missing classifier row")
            else:
                for column in ["company_type", "crypto_project_likelihood", "project_search_required"]:
                    if row.get(column) != classifier_row.get(column):
                        validation_errors.append(
                            f"{results_csv}: task_index={task_index}: {column} does not match classifier_results.csv"
                        )
            merged_rows.append({column: row.get(column, "") for column in RESULT_CSV_COLUMNS})

    if duplicate_task_indexes:
        validation_errors.append(
            "Duplicate task_index values: "
            + ",".join(str(value) for value in sorted(duplicate_task_indexes))
        )

    merged_rows.sort(key=lambda row: int(row["task_index"]))
    return merged_rows, validation_errors, expected_total


def collect_verification_rows(
    schedule_rows: list[dict[str, str]],
    worker_rows_by_task: dict[int, dict[str, str]],
    skip_verification: bool,
    allow_unresolved_verification: bool,
) -> tuple[list[dict[str, str]], list[str]]:
    if skip_verification:
        return [], []

    validation_errors: list[str] = []
    report_to_expected_tasks: dict[Path, set[int]] = {}
    report_to_summary: dict[Path, Path] = {}

    for schedule_row in schedule_rows:
        report_raw = (schedule_row.get("verification_report_csv") or "").strip()
        summary_raw = (schedule_row.get("verification_summary_md") or "").strip()
        if not report_raw:
            validation_errors.append(f"{schedule_row.get('batch_file')}: missing verification_report_csv in schedule")
            continue
        report_path = resolve_path(report_raw)
        report_to_expected_tasks.setdefault(report_path, set())
        report_to_summary[report_path] = resolve_path(summary_raw) if summary_raw else Path()
        first = int(schedule_row.get("first_task_index") or 0)
        last = int(schedule_row.get("last_task_index") or 0)
        if first and last:
            report_to_expected_tasks[report_path].update(range(first, last + 1))

    all_verifier_rows: list[dict[str, str]] = []
    for report_path, expected_tasks in sorted(report_to_expected_tasks.items()):
        report = ensure_file(report_path, "Verification report CSV")
        summary = report_to_summary.get(report_path)
        if summary and not summary.exists():
            validation_errors.append(f"{summary}: missing verification_summary.md")

        header, rows = load_csv(report)
        if header != VERIFICATION_CSV_COLUMNS:
            validation_errors.append(f"{report}: header mismatch")
        if len(rows) != len(expected_tasks):
            validation_errors.append(f"{report}: expected {len(expected_tasks)} verifier rows, found {len(rows)}")

        seen_report_tasks: set[int] = set()
        for row in rows:
            task_index = parse_task_index(row, report)
            seen_report_tasks.add(task_index)
            verdict = (row.get("verdict") or "").strip()
            action = (row.get("recommended_action") or "").strip()
            if verdict not in ALLOWED_VERDICTS:
                validation_errors.append(f"{report}: task_index={task_index}: invalid verdict {verdict!r}")
            if action not in ALLOWED_VERIFICATION_ACTIONS:
                validation_errors.append(f"{report}: task_index={task_index}: invalid recommended_action {action!r}")
            if verdict == "pass" and action != "accept_worker_row":
                validation_errors.append(f"{report}: task_index={task_index}: pass verdict must use accept_worker_row")
            if verdict != "pass" and not (row.get("error_reason") or "").strip():
                validation_errors.append(f"{report}: task_index={task_index}: non-pass verdict requires error_reason")
            if not allow_unresolved_verification and action in BLOCKING_VERIFICATION_ACTIONS:
                worker_row = worker_rows_by_task.get(task_index)
                edit_resolved = (
                    action == "edit_row"
                    and worker_row is not None
                    and (worker_row.get("token_ticker") or "").strip()
                    == (row.get("verifier_token_ticker") or "").strip()
                )
                if not edit_resolved:
                    validation_errors.append(
                        f"{report}: task_index={task_index}: verifier action {action} blocks merge until resolved"
                    )
            if action == "mark_manual_review":
                worker_row = worker_rows_by_task.get(task_index)
                if worker_row and worker_row.get("needs_manual_review") != "yes":
                    validation_errors.append(
                        f"{report}: task_index={task_index}: verifier requests manual review but worker row is not marked yes"
                    )
            all_verifier_rows.append({column: row.get(column, "") for column in VERIFICATION_CSV_COLUMNS})

        missing = expected_tasks - seen_report_tasks
        if missing:
            validation_errors.append(
                f"{report}: missing verifier rows for task_index "
                + ",".join(str(value) for value in sorted(missing)[:20])
            )

    all_verifier_rows.sort(key=lambda row: int(row["task_index"]))
    return all_verifier_rows, validation_errors


def load_existing_results(path: Path, replace_output: bool) -> list[dict[str, str]]:
    if replace_output or not path.exists():
        return []
    header, rows = load_csv(path)
    if header != RESULT_CSV_COLUMNS:
        raise SystemExit(
            f"Existing output CSV is not v2 schema: {path}. "
            "Use --replace-output or write to a different --output-csv."
        )
    return [{column: row.get(column, "") for column in RESULT_CSV_COLUMNS} for row in rows]


def load_existing_classifier_results(path: Path, replace_output: bool) -> list[dict[str, str]]:
    if replace_output or not path.exists():
        return []
    header, rows = load_csv(path)
    if header != CLASSIFIER_CSV_COLUMNS:
        raise SystemExit(
            f"Existing classifier CSV is not current schema: {path}. "
            "Use --replace-output or write to a different --classifier-results-csv."
        )
    return [{column: row.get(column, "") for column in CLASSIFIER_CSV_COLUMNS} for row in rows]


def merge_existing_and_new(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    rows_by_task: dict[int, dict[str, str]] = {}
    for row in existing_rows:
        rows_by_task[parse_task_index(row, Path("<existing-output>"))] = row
    for row in new_rows:
        task_index = parse_task_index(row, Path("<new-output>"))
        if task_index in rows_by_task:
            errors.append(f"New rows duplicate existing task_index={task_index}")
        rows_by_task[task_index] = row
    return [rows_by_task[index] for index in sorted(rows_by_task)], errors


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_checkpoint(
    path: Path,
    final_rows: list[dict[str, str]],
    schedule_rows: list[dict[str, str]],
    output_csv: Path,
    classifier_results_csv: Path,
    manual_review_csv: Path,
    verification_findings_csv: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    max_task_index = max((int(row["task_index"]) for row in final_rows), default=0)
    max_batch = max((parse_batch_number(row.get("batch_file", "")) for row in schedule_rows), default=0)
    total_batches = max_batch
    batch_dir_values = [row.get("batch_file", "") for row in schedule_rows]
    if batch_dir_values:
        first_batch_path = resolve_path(batch_dir_values[0])
        if first_batch_path.parent.exists():
            total_batches = max((parse_batch_number(path.name) for path in first_batch_path.parent.glob("batch_*.jsonl")), default=max_batch)

    checkpoint = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v2",
        "completed_rows_in_final_results": len(final_rows),
        "completed_through_task_index": max_task_index,
        "completed_through_batch": max_batch,
        "next_batch_to_process": max_batch + 1 if max_batch else 1,
        "next_task_index_to_process": max_task_index + 1,
        "batch_size": 30,
        "workers": 5,
        "total_batches": total_batches,
        "classifier_results_csv": str(classifier_results_csv),
        "final_results_csv": str(output_csv),
        "manual_review_csv": str(manual_review_csv),
        "verification_findings_csv": str(verification_findings_csv),
        "status": f"ready_for_batch_{max_batch + 1:04d}" if max_batch else "ready",
    }
    path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    runs_dir = args.runs_dir.resolve()
    schedule_csv = ensure_file(
        args.schedule_csv.resolve() if args.schedule_csv else runs_dir / "schedule.csv",
        "Schedule CSV",
    )
    output_csv = (
        args.output_csv.resolve()
        if args.output_csv
        else (DEFAULT_FINAL_DIR / "results.csv").resolve()
    )
    classifier_results_csv = (
        args.classifier_results_csv.resolve()
        if args.classifier_results_csv
        else (DEFAULT_FINAL_DIR / "classifier_results.csv").resolve()
    )
    manual_review_csv = (
        args.manual_review_csv.resolve()
        if args.manual_review_csv
        else (DEFAULT_FINAL_DIR / "needs_manual_review.csv").resolve()
    )
    verification_findings_csv = (
        args.verification_findings_csv.resolve()
        if args.verification_findings_csv
        else (DEFAULT_FINAL_DIR / "verification_findings.csv").resolve()
    )
    checkpoint_json = (
        args.checkpoint_json.resolve()
        if args.checkpoint_json
        else (DEFAULT_FINAL_DIR / "checkpoint.json").resolve()
    )

    schedule_rows = load_schedule(schedule_csv)
    if not schedule_rows:
        raise SystemExit("Schedule has no rows.")

    classifier_rows, validation_errors, classifier_rows_by_task = collect_classifier_rows(schedule_rows)
    new_rows, worker_errors, expected_total = collect_worker_rows(schedule_rows, classifier_rows_by_task)
    validation_errors.extend(worker_errors)
    worker_rows_by_task = {int(row["task_index"]): row for row in new_rows}
    verifier_rows, verifier_errors = collect_verification_rows(
        schedule_rows=schedule_rows,
        worker_rows_by_task=worker_rows_by_task,
        skip_verification=args.skip_verification,
        allow_unresolved_verification=args.allow_unresolved_verification,
    )
    validation_errors.extend(verifier_errors)

    existing_rows = load_existing_results(output_csv, replace_output=args.replace_output)
    final_rows, merge_errors = merge_existing_and_new(existing_rows, new_rows)
    validation_errors.extend(merge_errors)

    existing_classifier_rows = load_existing_classifier_results(
        classifier_results_csv,
        replace_output=args.replace_output,
    )
    final_classifier_rows, classifier_merge_errors = merge_existing_and_new(
        existing_classifier_rows,
        classifier_rows,
    )
    validation_errors.extend(classifier_merge_errors)

    manual_rows = [
        row for row in final_rows if (row.get("needs_manual_review") or "").strip() == "yes"
    ]

    if validation_errors and not args.allow_partial:
        print("Validation errors:")
        for error in validation_errors[:80]:
            print(f"- {error}")
        if len(validation_errors) > 80:
            print(f"- ... {len(validation_errors) - 80} more")
        raise SystemExit("Refusing to write outputs. Fix errors or pass --allow-partial for debug output.")

    write_csv(output_csv, RESULT_CSV_COLUMNS, final_rows)
    write_csv(classifier_results_csv, CLASSIFIER_CSV_COLUMNS, final_classifier_rows)
    write_csv(manual_review_csv, RESULT_CSV_COLUMNS, manual_rows)
    if verifier_rows:
        write_csv(verification_findings_csv, VERIFICATION_CSV_COLUMNS, verifier_rows)
    write_checkpoint(
        path=checkpoint_json,
        final_rows=final_rows,
        schedule_rows=schedule_rows,
        output_csv=output_csv,
        classifier_results_csv=classifier_results_csv,
        manual_review_csv=manual_review_csv,
        verification_findings_csv=verification_findings_csv,
    )

    print(f"Schedule CSV: {schedule_csv}")
    print(f"Expected new rows: {expected_total}")
    print(f"Classifier rows: {len(classifier_rows)}")
    print(f"New rows: {len(new_rows)}")
    print(f"Final rows: {len(final_rows)}")
    print(f"Manual review rows: {len(manual_rows)}")
    print(f"Verifier rows: {len(verifier_rows)}")
    print(f"Validation errors: {len(validation_errors)}")
    print(f"Final output CSV: {output_csv}")
    print(f"Classifier results CSV: {classifier_results_csv}")
    print(f"Manual review CSV: {manual_review_csv}")
    print(f"Verification findings CSV: {verification_findings_csv}")
    print(f"Checkpoint JSON: {checkpoint_json}")


if __name__ == "__main__":
    main()
