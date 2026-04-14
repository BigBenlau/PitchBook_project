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

RESULT_COLUMNS = [
    "token_id",
    "token_name",
    "token_symbol",
    "coingecko_slug",
    "cmc_slug",
    "token_href",
    "official_website",
    "token_type",
    "founder_people",
    "founder_status",
    "founder_evidence_spans",
    "related_companies",
    "related_company_status",
    "related_company_evidence_spans",
    "foundation_or_orgs",
    "foundation_status",
    "foundation_evidence_spans",
    "source_urls",
    "source_labels",
    "confidence",
    "needs_manual_review",
    "notes",
    "status",
]

VERIFICATION_COLUMNS = [
    "token_id",
    "token_name",
    "worker_founder_status",
    "worker_related_company_status",
    "worker_foundation_status",
    "verifier_founder_status",
    "verifier_related_company_status",
    "verifier_foundation_status",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_notes",
    "recommended_action",
    "corrected_result_row_json",
]

ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_STATUS = {"completed", "pending_layer3"}
ALLOWED_MANUAL_REVIEW = {"0", "1"}
ALLOWED_FIELD_STATUS = {"supported", "unresolved", "not_applicable"}
ALLOWED_ACTIONS = {
    "accept_worker_row",
    "edit_row",
    "mark_manual_review",
    "rerun_token",
    "rerun_batch",
    "update_prompt_or_process",
}
BLOCKING_ACTIONS = {"rerun_token", "rerun_batch", "update_prompt_or_process"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Part4 harness batch outputs, enforce verifier gates, and write consolidated results."
    )
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--schedule-csv", type=Path, default=None)
    parser.add_argument("--token-master-csv", type=Path, default=None)
    parser.add_argument("--token-entity-results-csv", type=Path, default=None)
    parser.add_argument("--review-queue-csv", type=Path, default=None)
    parser.add_argument("--verification-findings-csv", type=Path, default=None)
    parser.add_argument("--checkpoint-json", type=Path, default=None)
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


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def is_json_list(value: str) -> bool:
    try:
        parsed = json.loads((value or "").strip())
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def validate_result_row(row: dict[str, str], source: Path) -> list[str]:
    token_id = str(row.get("token_id") or "").strip()
    errors: list[str] = []
    if not token_id:
        errors.append("token_id is blank")
    for column in [
        "founder_people",
        "founder_evidence_spans",
        "related_companies",
        "related_company_evidence_spans",
        "foundation_or_orgs",
        "foundation_evidence_spans",
        "source_urls",
        "source_labels",
    ]:
        value = str(row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
        elif not is_json_list(value):
            errors.append(f"{column} is not a valid JSON list")

    for column in ["founder_status", "related_company_status", "foundation_status"]:
        if str(row.get(column) or "").strip() not in ALLOWED_FIELD_STATUS:
            errors.append(f"{column} must be one of {sorted(ALLOWED_FIELD_STATUS)}")

    if str(row.get("confidence") or "").strip() not in ALLOWED_CONFIDENCE:
        errors.append("confidence must be high, medium, or low")
    if str(row.get("needs_manual_review") or "").strip() not in ALLOWED_MANUAL_REVIEW:
        errors.append("needs_manual_review must be 0 or 1")
    if str(row.get("status") or "").strip() not in ALLOWED_STATUS:
        errors.append("status must be completed or pending_layer3")

    if (
        str(row.get("founder_status") or "").strip() == ""
        or str(row.get("related_company_status") or "").strip() == ""
        or str(row.get("foundation_status") or "").strip() == ""
    ):
        errors.append("field-level statuses are incomplete")

    if all(
        str(row.get(column) or "").strip() == "[]"
        for column in ["founder_people", "related_companies", "foundation_or_orgs"]
    ) and not any(
        str(row.get(column) or "").strip() == "unresolved"
        for column in ["founder_status", "related_company_status", "foundation_status"]
    ):
        errors.append("all targets are empty but no field is unresolved")

    if errors:
        return [f"{source}: token_id={token_id or '-'}: {error}" for error in errors]
    return []


def validate_verification_row(row: dict[str, str], source: Path) -> list[str]:
    token_id = str(row.get("token_id") or "").strip()
    errors: list[str] = []
    if not token_id:
        errors.append("token_id is blank")
    action = str(row.get("recommended_action") or "").strip()
    if action not in ALLOWED_ACTIONS:
        errors.append(f"invalid recommended_action {action!r}")
    corrected = str(row.get("corrected_result_row_json") or "").strip()
    if action == "edit_row" and not corrected:
        errors.append("edit_row requires corrected_result_row_json")
    if corrected:
        try:
            parsed = json.loads(corrected)
        except json.JSONDecodeError:
            errors.append("corrected_result_row_json is not valid JSON")
        else:
            if not isinstance(parsed, dict):
                errors.append("corrected_result_row_json must be an object")
            else:
                parsed_token_id = str(parsed.get("token_id") or "").strip()
                if parsed_token_id != token_id:
                    errors.append("corrected_result_row_json token_id mismatch")
    if errors:
        return [f"{source}: token_id={token_id or '-'}: {error}" for error in errors]
    return []


def load_schedule_rows(schedule_csv: Path) -> list[dict[str, str]]:
    _, rows = load_csv(schedule_csv)
    if not rows:
        raise SystemExit(f"Schedule has no rows: {schedule_csv}")
    return rows


def collect_worker_rows(schedule_rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], list[str]]:
    rows_by_token: dict[str, dict[str, str]] = {}
    errors: list[str] = []
    for schedule_row in schedule_rows:
        result_csv = ensure_file(resolve_path(schedule_row["token_entity_results_csv"]), "Token entity results CSV")
        header, rows = load_csv(result_csv)
        if header != RESULT_COLUMNS:
            errors.append(f"{result_csv}: header mismatch")
        for row in rows:
            token_id = str(row.get("token_id") or "").strip()
            if token_id in rows_by_token:
                errors.append(f"{result_csv}: duplicate token_id across batches: {token_id}")
            errors.extend(validate_result_row(row, result_csv))
            rows_by_token[token_id] = {column: row.get(column, "") for column in RESULT_COLUMNS}
    return rows_by_token, errors


def collect_verification_rows(
    schedule_rows: list[dict[str, str]],
    skip_verification: bool,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]], list[str]]:
    if skip_verification:
        return {}, [], []

    verifier_by_token: dict[str, dict[str, str]] = {}
    all_rows: list[dict[str, str]] = []
    errors: list[str] = []
    for schedule_row in schedule_rows:
        report_path = resolve_path(schedule_row["verification_report_csv"])
        if not report_path.exists():
            continue
        report_csv = ensure_file(report_path, "Verification report CSV")
        header, rows = load_csv(report_csv)
        if header != VERIFICATION_COLUMNS:
            errors.append(f"{report_csv}: header mismatch")
        for row in rows:
            token_id = str(row.get("token_id") or "").strip()
            if token_id in verifier_by_token:
                errors.append(f"{report_csv}: duplicate verifier token_id {token_id}")
            errors.extend(validate_verification_row(row, report_csv))
            trimmed = {column: row.get(column, "") for column in VERIFICATION_COLUMNS}
            verifier_by_token[token_id] = trimmed
            all_rows.append(trimmed)
    return verifier_by_token, all_rows, errors


def apply_verifier_actions(
    worker_rows_by_token: dict[str, dict[str, str]],
    verifier_by_token: dict[str, dict[str, str]],
    allow_unresolved_verification: bool,
) -> tuple[list[dict[str, str]], list[str]]:
    merged_rows: list[dict[str, str]] = []
    errors: list[str] = []

    for token_id, worker_row in sorted(worker_rows_by_token.items()):
        verifier_row = verifier_by_token.get(token_id)
        if not verifier_row:
            merged_rows.append(worker_row)
            continue

        action = str(verifier_row.get("recommended_action") or "").strip()
        if action in BLOCKING_ACTIONS and not allow_unresolved_verification:
            errors.append(
                f"verification blocks merge for token_id={token_id}: recommended_action={action}"
            )
            continue
        if action == "edit_row":
            corrected = json.loads(str(verifier_row.get("corrected_result_row_json") or "{}"))
            corrected_row = {column: str(corrected.get(column, "")) for column in RESULT_COLUMNS}
            errors.extend(validate_result_row(corrected_row, Path("<corrected_result_row_json>")))
            merged_rows.append(corrected_row)
            continue
        if action == "mark_manual_review":
            updated = dict(worker_row)
            updated["needs_manual_review"] = "1"
            merged_rows.append(updated)
            continue
        merged_rows.append(worker_row)

    return merged_rows, errors


def read_token_master_rows(path: Path) -> dict[str, dict[str, str]]:
    _, rows = load_csv(path)
    return {str(row.get("token_id") or "").strip(): row for row in rows if str(row.get("token_id") or "").strip()}


def validate_final_coverage(token_master: dict[str, dict[str, str]], merged_rows: list[dict[str, str]]) -> list[str]:
    merged_token_ids = {str(row.get("token_id") or "").strip() for row in merged_rows}
    missing = sorted(token_id for token_id in token_master if token_id not in merged_token_ids)
    if not missing:
        return []
    return ["Tokens present in token_master.csv but missing from final results: " + ",".join(missing[:50])]


def rebuild_review_queue(results_csv: Path, review_queue_csv: Path) -> None:
    subprocess.run(
        [
            "python3",
            str(PART4_DIR / "3_layer3_review_agent" / "2_build_review_queue.py"),
            "--input-csv",
            str(results_csv),
            "--output-csv",
            str(review_queue_csv),
        ],
        check=True,
    )


def write_checkpoint(
    checkpoint_json: Path,
    *,
    token_master_csv: Path,
    token_entity_results_csv: Path,
    review_queue_csv: Path,
    verification_findings_csv: Path,
    schedule_rows: list[dict[str, str]],
    merged_rows: list[dict[str, str]],
) -> None:
    completed_tokens = [
        str(row.get("token_id") or "").strip()
        for row in merged_rows
        if str(row.get("status") or "").strip() == "completed"
    ]
    last_batch = schedule_rows[-1]["batch_id"] if schedule_rows else ""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "completed_tokens_in_final_results": len(completed_tokens),
        "completed_through_token_id": completed_tokens[-1] if completed_tokens else "",
        "completed_through_batch": last_batch,
        "next_batch_to_process": "",
        "token_master_csv": str(token_master_csv),
        "token_entity_results_csv": str(token_entity_results_csv),
        "token_entity_review_queue_csv": str(review_queue_csv),
        "verification_findings_csv": str(verification_findings_csv),
    }
    checkpoint_json.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    runs_dir = args.runs_dir.resolve()
    schedule_csv = args.schedule_csv.resolve() if args.schedule_csv else (runs_dir / "schedule.csv").resolve()
    token_entity_results_csv = (
        args.token_entity_results_csv.resolve()
        if args.token_entity_results_csv
        else (DEFAULT_FINAL_DIR / "token_entity_results.csv").resolve()
    )
    review_queue_csv = (
        args.review_queue_csv.resolve()
        if args.review_queue_csv
        else (DEFAULT_FINAL_DIR / "token_entity_review_queue.csv").resolve()
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

    schedule_rows = load_schedule_rows(ensure_file(schedule_csv, "Schedule CSV"))
    token_master_csv = (
        args.token_master_csv.resolve()
        if args.token_master_csv
        else resolve_path(schedule_rows[0]["token_master_csv"])
    )
    token_master = read_token_master_rows(ensure_file(token_master_csv, "Token master CSV"))

    worker_rows_by_token, errors = collect_worker_rows(schedule_rows)
    verifier_by_token, verifier_rows, verifier_errors = collect_verification_rows(
        schedule_rows, skip_verification=args.skip_verification
    )
    errors.extend(verifier_errors)
    merged_rows, merge_errors = apply_verifier_actions(
        worker_rows_by_token,
        verifier_by_token,
        allow_unresolved_verification=args.allow_unresolved_verification,
    )
    errors.extend(merge_errors)
    errors.extend(validate_final_coverage(token_master, merged_rows))

    if errors:
        raise SystemExit("\n".join(errors))

    merged_rows.sort(key=lambda row: str(row.get("token_id") or ""))
    if token_entity_results_csv.exists() and not args.replace_output:
        raise SystemExit(
            f"Output already exists. Use --replace-output to overwrite: {token_entity_results_csv}"
        )

    write_csv(token_entity_results_csv, RESULT_COLUMNS, merged_rows)
    if verifier_rows or verification_findings_csv.exists():
        write_csv(verification_findings_csv, VERIFICATION_COLUMNS, verifier_rows)
    rebuild_review_queue(token_entity_results_csv, review_queue_csv)
    write_checkpoint(
        checkpoint_json,
        token_master_csv=token_master_csv,
        token_entity_results_csv=token_entity_results_csv,
        review_queue_csv=review_queue_csv,
        verification_findings_csv=verification_findings_csv,
        schedule_rows=schedule_rows,
        merged_rows=merged_rows,
    )

    print(f"Merged rows: {len(merged_rows)}", flush=True)
    print(f"Token entity results CSV: {token_entity_results_csv}", flush=True)
    print(f"Review queue CSV: {review_queue_csv}", flush=True)
    print(f"Verification findings CSV: {verification_findings_csv}", flush=True)
    print(f"Checkpoint JSON: {checkpoint_json}", flush=True)


if __name__ == "__main__":
    main()
