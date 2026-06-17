#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_TO_PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_TO_PART6_DIR.parent

DEFAULT_PART5_RESULTS = (
    REPO_ROOT
    / "part5_analyse_company_to_token"
    / "agent_runs"
    / "crypto_company"
    / "results.csv"
)
DEFAULT_BRIDGE_OUTPUT_DIR = PART5_TO_PART6_DIR / "output"
DEFAULT_BATCH_SIZE = 30


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify formal Part5-to-Part6 bridge outputs.",
    )
    parser.add_argument("--part5-results-csv", type=Path, default=DEFAULT_PART5_RESULTS)
    parser.add_argument("--bridge-output-dir", type=Path, default=DEFAULT_BRIDGE_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--part6-reference-results-csv",
        type=Path,
        default=None,
        help="Optional read-only Part6 reference results CSV to compare investor ID set/order.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Defaults to <bridge-output-dir>/verification_report.json.",
    )
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise SystemExit(f"{label} does not exist or is not a file: {resolved}")
    return resolved


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        return reader.fieldnames or [], list(reader)


def parse_token_results(value: str | None) -> list[dict[str, Any]]:
    raw = normalize_text(value)
    if not raw or raw == "[]":
        return []
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("token_results is not a JSON list")
    return [item for item in parsed if isinstance(item, dict)]


def duplicate_values(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def count_jsonl_rows(batch_files: list[Path]) -> tuple[int, list[str]]:
    total = 0
    errors: list[str] = []
    for path in batch_files:
        with path.open("r", encoding="utf-8") as infile:
            for line_number, line in enumerate(infile, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    payload = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    errors.append(f"{path.name}:{line_number}: invalid JSON: {exc}")
                    continue
                if not payload.get("investor_id"):
                    errors.append(f"{path.name}:{line_number}: missing investor_id")
                if not isinstance(payload.get("input_row"), dict):
                    errors.append(f"{path.name}:{line_number}: missing input_row object")
                total += 1
    return total, errors


def main() -> None:
    args = parse_args()
    part5_results_csv = ensure_file(args.part5_results_csv, "part5_results_csv")
    bridge_output_dir = args.bridge_output_dir.resolve()
    report_json = (args.report_json or (bridge_output_dir / "verification_report.json")).resolve()

    token_company_csv = ensure_file(bridge_output_dir / "token_company_universe.csv", "token_company_universe_csv")
    part6_input_csv = ensure_file(bridge_output_dir / "part6_investor_input.csv", "part6_investor_input_csv")
    audit_csv = ensure_file(bridge_output_dir / "investor_candidate_audit.csv", "investor_candidate_audit_csv")
    summary_json = ensure_file(bridge_output_dir / "summary.json", "summary_json")
    batches_dir = bridge_output_dir / "part6_batches"
    if not batches_dir.is_dir():
        raise SystemExit(f"part6_batches directory does not exist: {batches_dir}")
    batch_manifest_csv = ensure_file(batches_dir / "manifest.csv", "batch_manifest_csv")
    batch_input_csv = ensure_file(batches_dir / "input_investors.csv", "batch_input_csv")

    errors: list[str] = []

    part5_header, part5_rows = read_csv(part5_results_csv)
    if "token_results" not in part5_header:
        errors.append("Part5 results are missing token_results")
    part5_positive_ids: list[str] = []
    for row in part5_rows:
        company_id = normalize_text(row.get("company_id"))
        try:
            token_objects = parse_token_results(row.get("token_results"))
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Invalid Part5 token_results for company_id={company_id}: {exc}")
            continue
        if company_id and token_objects:
            part5_positive_ids.append(company_id)

    token_company_header, token_company_rows = read_csv(token_company_csv)
    token_company_ids = [normalize_text(row.get("company_id")) for row in token_company_rows]
    token_company_ids = [value for value in token_company_ids if value]

    part6_input_header, part6_input_rows = read_csv(part6_input_csv)
    investor_ids = [normalize_text(row.get("InvestorID")) for row in part6_input_rows]
    investor_ids = [value for value in investor_ids if value]

    audit_header, audit_rows = read_csv(audit_csv)
    audit_ids = [normalize_text(row.get("InvestorID")) for row in audit_rows]
    audit_ids = [value for value in audit_ids if value]

    manifest_header, manifest_rows = read_csv(batch_manifest_csv)
    batch_input_header, batch_input_rows = read_csv(batch_input_csv)
    batch_files = sorted(batches_dir.glob("batch_*.jsonl"))
    batch_jsonl_rows, batch_json_errors = count_jsonl_rows(batch_files)
    errors.extend(batch_json_errors)

    expected_batch_count = (len(part6_input_rows) + args.batch_size - 1) // args.batch_size
    if set(token_company_ids) != set(part5_positive_ids):
        errors.append(
            "token_company_universe company_id set does not match Part5 non-empty token_results company set"
        )
    if len(token_company_ids) != len(set(token_company_ids)):
        errors.append("token_company_universe contains duplicate company_id values")
    if len(investor_ids) != len(set(investor_ids)):
        errors.append("part6_investor_input contains duplicate InvestorID values")
    if len(manifest_rows) != len(part6_input_rows):
        errors.append("batch manifest row count does not match part6_investor_input row count")
    if len(batch_input_rows) != len(part6_input_rows):
        errors.append("batch input_investors row count does not match part6_investor_input row count")
    if batch_jsonl_rows != len(part6_input_rows):
        errors.append("total JSONL batch rows do not match part6_investor_input row count")
    if len(batch_files) != expected_batch_count:
        errors.append("batch file count does not match expected batch count")

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    if summary.get("part5_token_company_count") != len(token_company_rows):
        errors.append("summary part5_token_company_count does not match token_company_universe rows")
    if summary.get("part6_input_rows") != len(part6_input_rows):
        errors.append("summary part6_input_rows does not match part6_investor_input rows")

    reference_payload: dict[str, Any] = {"enabled": False}
    if args.part6_reference_results_csv:
        reference_results_csv = ensure_file(args.part6_reference_results_csv, "part6_reference_results_csv")
        reference_header, reference_rows = read_csv(reference_results_csv)
        if "investor_id" not in reference_header:
            errors.append("Part6 reference results are missing investor_id")
            reference_ids: list[str] = []
        else:
            reference_ids = [normalize_text(row.get("investor_id")) for row in reference_rows]
            reference_ids = [value for value in reference_ids if value]
        set_match = set(reference_ids) == set(investor_ids)
        order_match = reference_ids == investor_ids
        if not set_match:
            errors.append("Part6 reference investor_id set does not match bridge InvestorID set")
        if not order_match:
            errors.append("Part6 reference investor_id order does not match bridge InvestorID order")
        reference_payload = {
            "enabled": True,
            "rows": len(reference_rows),
            "unique_investor_ids": len(set(reference_ids)),
            "id_set_match": set_match,
            "id_order_match": order_match,
        }

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "part5_results_rows": len(part5_rows),
        "formal_token_company_rows_from_part5": len(part5_positive_ids),
        "token_company_universe_rows": len(token_company_rows),
        "part6_input_rows": len(part6_input_rows),
        "investor_candidate_audit_rows": len(audit_rows),
        "unique_investor_ids": len(set(investor_ids)),
        "batch_size": args.batch_size,
        "batch_count": len(batch_files),
        "expected_batch_count": expected_batch_count,
        "batch_manifest_rows": len(manifest_rows),
        "batch_input_rows": len(batch_input_rows),
        "batch_jsonl_rows": batch_jsonl_rows,
        "part6_reference": reference_payload,
        "duplicate_company_ids": duplicate_values(token_company_ids)[:50],
        "duplicate_investor_ids": duplicate_values(investor_ids)[:50],
        "summary_keys": sorted(summary),
        "errors": errors,
    }
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
