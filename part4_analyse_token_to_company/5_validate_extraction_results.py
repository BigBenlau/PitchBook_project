#!/usr/bin/env python3
"""
Validate founder/company extraction results and attach review signals.

Example:
python3 part4/5_validate_extraction_results.py --results-csv part4/output/founder_company_extracted.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
DEFAULT_RESULTS_CSV = OUTPUT_DIR / "founder_company_extracted.csv"
DEFAULT_SENTENCES_CSV = OUTPUT_DIR / "token_evidence_sentences.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "founder_company_validated.csv"
ORG_TERMS = ("foundation", "dao", "association", "labs", "protocol", "network")
COMPANY_TERMS = ("inc", "corp", "corporation", "limited", "ltd", "llc", "company", "group")
INVESTOR_TERMS = ("capital", "ventures", "partners")
EXCHANGE_TERMS = ("binance", "coinbase", "kraken", "okx", "bybit")
VARIANT_TERMS = ("wrapped", "bridged", "staked", "liquid staking")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate extraction results.")
    parser.add_argument("--results-csv", type=Path, default=DEFAULT_RESULTS_CSV)
    parser.add_argument("--sentences-csv", type=Path, default=DEFAULT_SENTENCES_CSV)
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


def load_source_labels(path: Path) -> dict[int, set[str]]:
    labels: dict[int, set[str]] = {}
    if not path.is_file():
        return labels
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                row_index = int(str(row.get("row_index") or "").strip())
            except ValueError:
                continue
            source_type = str(row.get("source_type") or "").strip()
            if source_type:
                labels.setdefault(row_index, set()).add(source_type)
    return labels


def looks_like_person(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if any(term in text.lower() for term in ORG_TERMS + COMPANY_TERMS):
        return False
    return bool(re.search(r"[A-Za-z]", text))


def main() -> None:
    args = parse_args()
    source_labels = load_source_labels(args.sentences_csv.resolve())
    input_csv = args.results_csv.resolve()
    output_csv = args.output_csv.resolve()

    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        extra_fields = [
            "source_labels",
            "validation_issues",
            "suggested_confidence_cap",
            "needs_manual_review",
        ]
        with output_csv.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames + extra_fields)
            writer.writeheader()

            for row in reader:
                try:
                    row_index = int(str(row.get("row_index") or "").strip())
                except ValueError:
                    row_index = 0

                token_name = str(row.get("token_name") or "").strip()
                confidence = str(row.get("confidence") or "").strip().lower()
                founders = parse_json_list(str(row.get("founder_people") or ""))
                companies = parse_json_list(str(row.get("related_companies") or ""))
                orgs = parse_json_list(str(row.get("foundation_or_orgs") or ""))
                evidence_spans = parse_json_list(str(row.get("evidence_spans") or ""))
                labels = sorted(source_labels.get(row_index, set()))
                issues: list[str] = []
                confidence_cap = ""

                if (founders or companies or orgs) and not evidence_spans:
                    issues.append("missing_evidence_spans")

                if confidence == "high" and not labels:
                    issues.append("high_confidence_without_source_labels")

                if confidence == "high" and "official_site" not in labels:
                    issues.append("high_confidence_without_official_support")
                    confidence_cap = "medium"

                for founder in founders:
                    if not looks_like_person(founder):
                        issues.append("founder_looks_non_person")
                        break

                for company in companies:
                    lowered = company.lower()
                    if any(term in lowered for term in ORG_TERMS):
                        issues.append("company_looks_like_org")
                        break
                    if any(term in lowered for term in INVESTOR_TERMS):
                        issues.append("company_looks_like_investor")
                        break
                    if any(term in lowered for term in EXCHANGE_TERMS):
                        issues.append("company_looks_like_exchange_or_platform")
                        break

                for org in orgs:
                    lowered = org.lower()
                    if any(term in lowered for term in COMPANY_TERMS):
                        issues.append("org_looks_like_company")
                        break

                if token_name and any(term in token_name.lower() for term in VARIANT_TERMS):
                    issues.append("variant_token_requires_review")

                if confidence == "low":
                    issues.append("low_confidence")

                needs_manual_review = "1" if issues else "0"

                writer.writerow(
                    {
                        **row,
                        "source_labels": json.dumps(labels, ensure_ascii=False),
                        "validation_issues": json.dumps(sorted(set(issues)), ensure_ascii=False),
                        "suggested_confidence_cap": confidence_cap,
                        "needs_manual_review": needs_manual_review,
                    }
                )


if __name__ == "__main__":
    main()
