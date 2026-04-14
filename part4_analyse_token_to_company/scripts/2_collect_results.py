#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent

DEFAULT_RUNS_DIR = PART4_DIR / "agent_runs" / "token_company_parallel"
DEFAULT_FINAL_DIR = PART4_DIR / "agent_runs" / "token_company"

EXTRACTED_CSV_COLUMNS = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "confidence",
    "evidence_spans",
    "notes",
    "status",
    "error",
]

VALIDATED_CSV_COLUMNS = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "confidence",
    "evidence_spans",
    "notes",
    "status",
    "error",
    "source_labels",
    "cmc_match_methods",
    "sentence_risk_flags",
    "validation_issues",
    "suggested_confidence_cap",
    "needs_manual_review",
]

REVIEW_QUEUE_COLUMNS = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "confidence",
    "review_priority",
    "review_reason",
    "source_labels",
    "cmc_match_methods",
    "sentence_risk_flags",
    "validation_issues",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "evidence_spans",
    "notes",
]

VERIFICATION_CSV_COLUMNS = [
    "row_index",
    "token_name",
    "worker_founder_people",
    "worker_related_companies",
    "worker_foundation_or_orgs",
    "verifier_founder_people",
    "verifier_related_companies",
    "verifier_foundation_or_orgs",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_notes",
    "recommended_action",
]

ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_STATUS = {"completed", "pending_agent"}
ALLOWED_MANUAL_REVIEW = {"0", "1"}
ALLOWED_VERDICTS = {
    "pass",
    "suspected_missing_entity",
    "suspected_extra_entity",
    "wrong_entity_type",
    "insufficient_evidence",
    "search_should_escalate",
    "formatting_error",
}
ALLOWED_ACTIONS = {
    "accept_worker_row",
    "edit_row",
    "mark_manual_review",
    "rerun_row",
    "rerun_batch",
    "update_prompt_or_process",
}
BLOCKING_ACTIONS = {
    "edit_row",
    "rerun_row",
    "rerun_batch",
    "update_prompt_or_process",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Part4 harness batch outputs, enforce verifier gates, and write consolidated results.",
    )
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--schedule-csv", type=Path, default=None)
    parser.add_argument("--extracted-results-csv", type=Path, default=None)
    parser.add_argument("--validated-results-csv", type=Path, default=None)
    parser.add_argument("--review-queue-csv", type=Path, default=None)
    parser.add_argument("--verification-findings-csv", type=Path, default=None)
    parser.add_argument("--checkpoint-json", type=Path, default=None)
    parser.add_argument("--allow-partial", action="store_true")
    parser.add_argument("--allow-unresolved-verification", action="store_true")
    parser.add_argument("--skip-verification", action="store_true")
    parser.add_argument("--replace-output", action="store_true")
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
        return list(reader.fieldnames or []), list(reader)


def is_json_list(value: str) -> bool:
    try:
        parsed = json.loads((value or "").strip())
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def parse_row_index(row: dict[str, str], source: Path) -> int:
    raw = str(row.get("row_index") or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Invalid row_index in {source}: {raw!r}") from None


def parse_batch_number(batch_id: str) -> int:
    try:
        return int(batch_id.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def validate_extracted_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    for column in ["founder_people", "related_companies", "foundation_or_orgs", "evidence_spans"]:
        value = (row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
        elif not is_json_list(value):
            errors.append(f"{column} is not a valid JSON list: {value!r}")
    if row.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append("confidence must be high, medium, or low")
    if row.get("status") not in ALLOWED_STATUS:
        errors.append("status must be completed or pending_agent")
    if errors:
        return [f"{source}: row_index={row.get('row_index')}: {error}" for error in errors]
    return []


def validate_validated_row(row: dict[str, str], source: Path) -> list[str]:
    errors = validate_extracted_row(row, source)
    for column in ["source_labels", "cmc_match_methods", "sentence_risk_flags", "validation_issues"]:
        value = (row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
        elif not is_json_list(value):
            errors.append(f"{column} is not a valid JSON list: {value!r}")
    if row.get("needs_manual_review") not in ALLOWED_MANUAL_REVIEW:
        errors.append("needs_manual_review must be 0 or 1")
    confidence_cap = (row.get("suggested_confidence_cap") or "").strip()
    if confidence_cap and confidence_cap not in ALLOWED_CONFIDENCE:
        errors.append("suggested_confidence_cap must be blank or a valid confidence value")
    if errors:
        return [f"{source}: row_index={row.get('row_index')}: {error}" for error in errors]
    return []


def collect_extracted_rows(schedule_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[str], dict[int, dict[str, str]]]:
    rows_out: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[int] = set()
    duplicates: set[int] = set()
    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        extracted_csv = ensure_file(resolve_path(schedule_row["extracted_results_csv"]), "Extracted results CSV")
        header, rows = load_csv(extracted_csv)
        if header != EXTRACTED_CSV_COLUMNS:
            errors.append(f"{extracted_csv}: header mismatch")
        if len(rows) != task_count:
            errors.append(f"{extracted_csv}: expected {task_count} rows, found {len(rows)}")
        for row in rows:
            row_index = parse_row_index(row, extracted_csv)
            if row_index in seen:
                duplicates.add(row_index)
            seen.add(row_index)
            errors.extend(validate_extracted_row(row, extracted_csv))
            rows_out.append({column: row.get(column, "") for column in EXTRACTED_CSV_COLUMNS})
    if duplicates:
        errors.append("Duplicate extracted row_index values: " + ",".join(str(v) for v in sorted(duplicates)))
    rows_out.sort(key=lambda row: int(row["row_index"]))
    return rows_out, errors, {int(row["row_index"]): row for row in rows_out}


def collect_validated_rows(
    schedule_rows: list[dict[str, str]],
    extracted_rows_by_index: dict[int, dict[str, str]],
) -> tuple[list[dict[str, str]], list[str]]:
    rows_out: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[int] = set()
    duplicates: set[int] = set()
    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        validated_csv = ensure_file(resolve_path(schedule_row["validated_results_csv"]), "Validated results CSV")
        header, rows = load_csv(validated_csv)
        if header != VALIDATED_CSV_COLUMNS:
            errors.append(f"{validated_csv}: header mismatch")
        if len(rows) != task_count:
            errors.append(f"{validated_csv}: expected {task_count} rows, found {len(rows)}")
        for row in rows:
            row_index = parse_row_index(row, validated_csv)
            if row_index in seen:
                duplicates.add(row_index)
            seen.add(row_index)
            errors.extend(validate_validated_row(row, validated_csv))
            extracted_row = extracted_rows_by_index.get(row_index)
            if not extracted_row:
                errors.append(f"{validated_csv}: row_index={row_index}: missing extracted row")
            else:
                for column in [
                    "token_name",
                    "token_symbol",
                    "token_href",
                    "slug",
                    "founder_people",
                    "related_companies",
                    "foundation_or_orgs",
                    "confidence",
                    "evidence_spans",
                    "notes",
                    "status",
                    "error",
                ]:
                    if row.get(column) != extracted_row.get(column):
                        errors.append(
                            f"{validated_csv}: row_index={row_index}: {column} does not match extracted results"
                        )
            rows_out.append({column: row.get(column, "") for column in VALIDATED_CSV_COLUMNS})
        review_queue_csv = ensure_file(resolve_path(schedule_row["review_queue_csv"]), "Review queue CSV")
        review_header, _ = load_csv(review_queue_csv)
        if review_header != REVIEW_QUEUE_COLUMNS:
            errors.append(f"{review_queue_csv}: header mismatch")
    if duplicates:
        errors.append("Duplicate validated row_index values: " + ",".join(str(v) for v in sorted(duplicates)))
    rows_out.sort(key=lambda row: int(row["row_index"]))
    return rows_out, errors


def edit_resolved(worker_row: dict[str, str] | None, verifier_row: dict[str, str]) -> bool:
    if worker_row is None:
        return False
    return (
        (worker_row.get("founder_people") or "").strip()
        == (verifier_row.get("verifier_founder_people") or "").strip()
        and (worker_row.get("related_companies") or "").strip()
        == (verifier_row.get("verifier_related_companies") or "").strip()
        and (worker_row.get("foundation_or_orgs") or "").strip()
        == (verifier_row.get("verifier_foundation_or_orgs") or "").strip()
    )


def collect_verification_rows(
    schedule_rows: list[dict[str, str]],
    worker_rows_by_index: dict[int, dict[str, str]],
    skip_verification: bool,
    allow_unresolved_verification: bool,
) -> tuple[list[dict[str, str]], list[str]]:
    if skip_verification:
        return [], []

    rows_out: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[int] = set()
    duplicates: set[int] = set()
    for schedule_row in schedule_rows:
        report_csv = ensure_file(resolve_path(schedule_row["verification_report_csv"]), "Verification report CSV")
        summary_md = resolve_path(schedule_row["verification_summary_md"])
        if not summary_md.exists():
            errors.append(f"{summary_md}: missing verification_summary.md")
        header, rows = load_csv(report_csv)
        task_count = int(schedule_row.get("task_count") or 0)
        if header != VERIFICATION_CSV_COLUMNS:
            errors.append(f"{report_csv}: header mismatch")
        if len(rows) != task_count:
            errors.append(f"{report_csv}: expected {task_count} rows, found {len(rows)}")
        for row in rows:
            row_index = parse_row_index(row, report_csv)
            if row_index in seen:
                duplicates.add(row_index)
            seen.add(row_index)
            verdict = (row.get("verdict") or "").strip()
            action = (row.get("recommended_action") or "").strip()
            if verdict not in ALLOWED_VERDICTS:
                errors.append(f"{report_csv}: row_index={row_index}: invalid verdict {verdict!r}")
            if action not in ALLOWED_ACTIONS:
                errors.append(f"{report_csv}: row_index={row_index}: invalid recommended_action {action!r}")
            if verdict == "pass" and action != "accept_worker_row":
                errors.append(f"{report_csv}: row_index={row_index}: pass verdict must use accept_worker_row")
            if verdict != "pass" and not (row.get("error_reason") or "").strip():
                errors.append(f"{report_csv}: row_index={row_index}: non-pass verdict requires error_reason")
            if not allow_unresolved_verification and action in BLOCKING_ACTIONS:
                if not (action == "edit_row" and edit_resolved(worker_rows_by_index.get(row_index), row)):
                    errors.append(
                        f"{report_csv}: row_index={row_index}: verifier action {action} blocks merge until resolved"
                    )
            rows_out.append({column: row.get(column, "") for column in VERIFICATION_CSV_COLUMNS})
    if duplicates:
        errors.append("Duplicate verifier row_index values: " + ",".join(str(v) for v in sorted(duplicates)))
    rows_out.sort(key=lambda row: int(row["row_index"]))
    return rows_out, errors


def apply_verifier_manual_review(validated_rows: list[dict[str, str]], verifier_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    verifier_by_index = {int(row["row_index"]): row for row in verifier_rows}
    updated_rows: list[dict[str, str]] = []
    for row in validated_rows:
        updated_row = dict(row)
        verifier_row = verifier_by_index.get(int(row["row_index"]))
        if verifier_row and (verifier_row.get("recommended_action") or "").strip() == "mark_manual_review":
            updated_row["needs_manual_review"] = "1"
        updated_rows.append(updated_row)
    return updated_rows


def load_existing_rows(path: Path, fieldnames: list[str], replace_output: bool) -> list[dict[str, str]]:
    if replace_output or not path.exists():
        return []
    header, rows = load_csv(path)
    if header != fieldnames:
        raise SystemExit(f"Existing CSV is not current schema: {path}")
    return [{column: row.get(column, "") for column in fieldnames} for row in rows]


def merge_existing_and_new(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str]]:
    errors: list[str] = []
    rows_by_index: dict[int, dict[str, str]] = {}
    for row in existing_rows:
        rows_by_index[int(row["row_index"])] = row
    for row in new_rows:
        row_index = int(row["row_index"])
        if row_index in rows_by_index:
            errors.append(f"New rows duplicate existing row_index={row_index}")
        rows_by_index[row_index] = row
    return [rows_by_index[index] for index in sorted(rows_by_index)], errors


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_checkpoint(
    path: Path,
    validated_rows: list[dict[str, str]],
    schedule_rows: list[dict[str, str]],
    extracted_results_csv: Path,
    validated_results_csv: Path,
    review_queue_csv: Path,
    verification_findings_csv: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    max_row_index = max((int(row["row_index"]) for row in validated_rows), default=0)
    max_batch = max((parse_batch_number(str(row.get("batch_id") or "")) for row in schedule_rows), default=0)
    checkpoint = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v2_harness",
        "completed_rows_in_final_results": len(validated_rows),
        "completed_through_row_index": max_row_index,
        "completed_through_batch": max_batch,
        "next_batch_to_process": max_batch + 1 if max_batch else 1,
        "extracted_results_csv": str(extracted_results_csv),
        "validated_results_csv": str(validated_results_csv),
        "review_queue_csv": str(review_queue_csv),
        "verification_findings_csv": str(verification_findings_csv),
        "status": f"ready_for_batch_{max_batch + 1:04d}" if max_batch else "ready",
    }
    path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def rebuild_review_queue(validated_results_csv: Path, review_queue_csv: Path) -> None:
    subprocess.run(
        [
            "python3",
            str(PART4_DIR / "3_layer3_review_agent" / "2_build_review_queue.py"),
            "--input-csv",
            str(validated_results_csv),
            "--output-csv",
            str(review_queue_csv),
        ],
        check=True,
        cwd=REPO_ROOT,
    )


def main() -> None:
    args = parse_args()
    runs_dir = args.runs_dir.resolve()
    schedule_csv = ensure_file(
        args.schedule_csv.resolve() if args.schedule_csv else runs_dir / "schedule.csv",
        "Schedule CSV",
    )
    extracted_results_csv = (
        args.extracted_results_csv.resolve()
        if args.extracted_results_csv
        else (DEFAULT_FINAL_DIR / "founder_company_extracted.csv").resolve()
    )
    validated_results_csv = (
        args.validated_results_csv.resolve()
        if args.validated_results_csv
        else (DEFAULT_FINAL_DIR / "founder_company_validated.csv").resolve()
    )
    review_queue_csv = (
        args.review_queue_csv.resolve()
        if args.review_queue_csv
        else (DEFAULT_FINAL_DIR / "founder_company_review_queue.csv").resolve()
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

    _, schedule_rows = load_csv(schedule_csv)
    if not schedule_rows:
        raise SystemExit("Schedule has no rows.")

    new_extracted_rows, validation_errors, extracted_rows_by_index = collect_extracted_rows(schedule_rows)
    new_validated_rows, worker_errors = collect_validated_rows(schedule_rows, extracted_rows_by_index)
    validation_errors.extend(worker_errors)
    worker_rows_by_index = {int(row["row_index"]): row for row in new_validated_rows}
    verifier_rows, verifier_errors = collect_verification_rows(
        schedule_rows=schedule_rows,
        worker_rows_by_index=worker_rows_by_index,
        skip_verification=args.skip_verification,
        allow_unresolved_verification=args.allow_unresolved_verification,
    )
    validation_errors.extend(verifier_errors)
    new_validated_rows = apply_verifier_manual_review(new_validated_rows, verifier_rows)

    existing_extracted_rows = load_existing_rows(
        extracted_results_csv,
        EXTRACTED_CSV_COLUMNS,
        replace_output=args.replace_output,
    )
    final_extracted_rows, merge_errors = merge_existing_and_new(existing_extracted_rows, new_extracted_rows)
    validation_errors.extend(merge_errors)

    existing_validated_rows = load_existing_rows(
        validated_results_csv,
        VALIDATED_CSV_COLUMNS,
        replace_output=args.replace_output,
    )
    final_validated_rows, validated_merge_errors = merge_existing_and_new(existing_validated_rows, new_validated_rows)
    validation_errors.extend(validated_merge_errors)

    existing_verifier_rows = load_existing_rows(
        verification_findings_csv,
        VERIFICATION_CSV_COLUMNS,
        replace_output=args.replace_output,
    )
    final_verifier_rows, verifier_merge_errors = merge_existing_and_new(existing_verifier_rows, verifier_rows)
    validation_errors.extend(verifier_merge_errors)

    if validation_errors and not args.allow_partial:
        print("Validation errors:")
        for error in validation_errors[:80]:
            print(f"- {error}")
        if len(validation_errors) > 80:
            print(f"- ... {len(validation_errors) - 80} more")
        raise SystemExit("Refusing to write outputs. Fix errors or pass --allow-partial for debug output.")

    write_csv(extracted_results_csv, EXTRACTED_CSV_COLUMNS, final_extracted_rows)
    write_csv(validated_results_csv, VALIDATED_CSV_COLUMNS, final_validated_rows)
    if verifier_rows or verification_findings_csv.exists():
        write_csv(verification_findings_csv, VERIFICATION_CSV_COLUMNS, final_verifier_rows)
    rebuild_review_queue(validated_results_csv, review_queue_csv)
    write_checkpoint(
        path=checkpoint_json,
        validated_rows=final_validated_rows,
        schedule_rows=schedule_rows,
        extracted_results_csv=extracted_results_csv,
        validated_results_csv=validated_results_csv,
        review_queue_csv=review_queue_csv,
        verification_findings_csv=verification_findings_csv,
    )

    print(f"Schedule CSV: {schedule_csv}")
    print(f"Extracted rows: {len(new_extracted_rows)}")
    print(f"Validated rows: {len(new_validated_rows)}")
    print(f"Final validated rows: {len(final_validated_rows)}")
    print(f"Verifier rows: {len(verifier_rows)}")
    print(f"Validation errors: {len(validation_errors)}")
    print(f"Extracted output CSV: {extracted_results_csv}")
    print(f"Validated output CSV: {validated_results_csv}")
    print(f"Review queue CSV: {review_queue_csv}")
    print(f"Verification findings CSV: {verification_findings_csv}")
    print(f"Checkpoint JSON: {checkpoint_json}")


if __name__ == "__main__":
    main()
