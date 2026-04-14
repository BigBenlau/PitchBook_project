#!/usr/bin/env python3
"""
Build a field-level review queue from consolidated Part4 token_entity_results.csv.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_INPUT_CSV = OUTPUT_DIR / "token_entity_results.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "token_entity_review_queue.csv"

OUTPUT_FIELDNAMES = [
    "token_id",
    "token_name",
    "token_symbol",
    "token_type",
    "confidence",
    "review_priority",
    "review_reason",
    "unresolved_targets",
    "needs_manual_review",
    "founder_status",
    "related_company_status",
    "foundation_status",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "source_urls",
    "source_labels",
    "notes",
]

HIGH_RISK_TOKEN_TYPES = {
    "wrapped_or_bridged",
    "liquid_staking_or_receipt",
    "synthetic_or_fund",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Part4 field-level review queue.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    return parser.parse_args()


def parse_json_list(value: str) -> list[str]:
    text = (value or "").strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [str(item).strip() for item in data if str(item).strip()]


def unresolved_targets(row: dict[str, str]) -> list[str]:
    targets: list[str] = []
    if str(row.get("founder_status") or "").strip() == "unresolved":
        targets.append("founder")
    if str(row.get("related_company_status") or "").strip() == "unresolved":
        targets.append("related_company")
    if str(row.get("foundation_status") or "").strip() == "unresolved":
        targets.append("foundation")
    return targets


def determine_priority(row: dict[str, str], unresolved: list[str]) -> str:
    token_type = str(row.get("token_type") or "").strip()
    confidence = str(row.get("confidence") or "").strip().lower()
    manual_review = str(row.get("needs_manual_review") or "").strip() == "1"
    if unresolved:
        if token_type in HIGH_RISK_TOKEN_TYPES or len(unresolved) >= 2:
            return "high"
        return "medium"
    if manual_review:
        return "high" if token_type in HIGH_RISK_TOKEN_TYPES or confidence == "low" else "medium"
    return "low"


def build_reason(row: dict[str, str], unresolved: list[str]) -> str:
    reasons: list[str] = []
    if unresolved:
        reasons.append("unresolved_targets=" + ",".join(unresolved))
    if str(row.get("status") or "").strip() == "pending_layer3":
        reasons.append("pending_layer3")
    if str(row.get("needs_manual_review") or "").strip() == "1":
        reasons.append("manual_review_requested")
    token_type = str(row.get("token_type") or "").strip()
    if token_type in HIGH_RISK_TOKEN_TYPES:
        reasons.append(f"high_risk_token_type={token_type}")
    return "; ".join(reasons) if reasons else "manual_review_requested"


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.resolve()
    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        with output_csv.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
            writer.writeheader()

            for row in reader:
                unresolved = unresolved_targets(row)
                manual_review = str(row.get("needs_manual_review") or "").strip() == "1"
                if not unresolved and not manual_review:
                    continue

                writer.writerow(
                    {
                        "token_id": str(row.get("token_id") or ""),
                        "token_name": str(row.get("token_name") or ""),
                        "token_symbol": str(row.get("token_symbol") or ""),
                        "token_type": str(row.get("token_type") or ""),
                        "confidence": str(row.get("confidence") or ""),
                        "review_priority": determine_priority(row, unresolved),
                        "review_reason": build_reason(row, unresolved),
                        "unresolved_targets": json.dumps(unresolved, ensure_ascii=False),
                        "needs_manual_review": str(row.get("needs_manual_review") or "0"),
                        "founder_status": str(row.get("founder_status") or ""),
                        "related_company_status": str(row.get("related_company_status") or ""),
                        "foundation_status": str(row.get("foundation_status") or ""),
                        "founder_people": json.dumps(parse_json_list(str(row.get("founder_people") or "")), ensure_ascii=False),
                        "related_companies": json.dumps(
                            parse_json_list(str(row.get("related_companies") or "")), ensure_ascii=False
                        ),
                        "foundation_or_orgs": json.dumps(
                            parse_json_list(str(row.get("foundation_or_orgs") or "")), ensure_ascii=False
                        ),
                        "source_urls": str(row.get("source_urls") or "[]"),
                        "source_labels": str(row.get("source_labels") or "[]"),
                        "notes": str(row.get("notes") or ""),
                    }
                )


if __name__ == "__main__":
    main()
