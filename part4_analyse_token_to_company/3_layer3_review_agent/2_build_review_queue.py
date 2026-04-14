#!/usr/bin/env python3
"""
Build a review queue from validated founder/company extraction results.

Harness batch example:
python3 part4_analyse_token_to_company/3_layer3_review_agent/2_build_review_queue.py \
  --input-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/founder_company_validated.csv \
  --output-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/founder_company_review_queue.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_INPUT_CSV = OUTPUT_DIR / "founder_company_validated.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "founder_company_review_queue.csv"
OUTPUT_FIELDNAMES = [
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build review queue.")
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


def determine_priority(confidence: str, issues: list[str], token_name: str) -> str:
    lowered = token_name.lower()
    if "variant_token_requires_review" in issues or any(
        term in lowered for term in ("wrapped", "bridged", "staked")
    ):
        return "high"
    if "no_slug_match_support" in issues:
        return "high"
    if "candidate_sentence_risk_flags_present" in issues:
        return "high"
    if "high_confidence_without_official_support" in issues or "company_looks_like_org" in issues:
        return "high"
    if confidence == "low":
        return "medium"
    return "low"


def build_reason(issues: list[str], founders: list[str], companies: list[str], orgs: list[str]) -> str:
    if issues:
        return "; ".join(issues)
    if not founders and not companies and not orgs:
        return "no_founder_company_org_extracted"
    return "manual_review_requested"


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
                needs_manual_review = str(row.get("needs_manual_review") or "").strip() == "1"
                founders = parse_json_list(str(row.get("founder_people") or ""))
                companies = parse_json_list(str(row.get("related_companies") or ""))
                orgs = parse_json_list(str(row.get("foundation_or_orgs") or ""))
                issues = parse_json_list(str(row.get("validation_issues") or ""))
                confidence = str(row.get("confidence") or "").strip().lower()
                token_name = str(row.get("token_name") or "").strip()

                if not needs_manual_review and (founders or companies or orgs) and confidence != "low":
                    continue

                reason = build_reason(issues, founders, companies, orgs)
                priority = determine_priority(confidence, issues, token_name)

                writer.writerow(
                    {
                        "row_index": str(row.get("row_index") or ""),
                        "token_name": token_name,
                        "token_symbol": str(row.get("token_symbol") or ""),
                        "token_href": str(row.get("token_href") or ""),
                        "slug": str(row.get("slug") or ""),
                        "confidence": str(row.get("confidence") or ""),
                        "review_priority": priority,
                        "review_reason": reason,
                        "source_labels": str(row.get("source_labels") or ""),
                        "cmc_match_methods": str(row.get("cmc_match_methods") or ""),
                        "sentence_risk_flags": str(row.get("sentence_risk_flags") or ""),
                        "validation_issues": str(row.get("validation_issues") or ""),
                        "founder_people": str(row.get("founder_people") or ""),
                        "related_companies": str(row.get("related_companies") or ""),
                        "foundation_or_orgs": str(row.get("foundation_or_orgs") or ""),
                        "evidence_spans": str(row.get("evidence_spans") or ""),
                        "notes": str(row.get("notes") or ""),
                    }
                )


if __name__ == "__main__":
    main()
