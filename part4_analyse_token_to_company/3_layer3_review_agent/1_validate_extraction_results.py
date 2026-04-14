#!/usr/bin/env python3
"""
Validate consolidated token_entity_results.csv and attach light review signals.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_RESULTS_CSV = OUTPUT_DIR / "token_entity_results.csv"
DEFAULT_SENTENCES_CSV = OUTPUT_DIR / "entity_sentences.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "token_entity_results_validated.csv"

HIGH_RISK_TOKEN_TYPES = {
    "wrapped_or_bridged",
    "liquid_staking_or_receipt",
    "synthetic_or_fund",
    "unknown",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Part4 token_entity_results.csv.")
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


def load_sentence_metadata(path: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    labels: dict[str, set[str]] = {}
    risk_flags: dict[str, set[str]] = {}
    if not path.is_file():
        return labels, risk_flags
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            token_id = str(row.get("token_id") or "").strip()
            if not token_id:
                continue
            source_type = str(row.get("source_type") or "").strip()
            if source_type:
                labels.setdefault(token_id, set()).add(source_type)
            for flag in parse_json_list(str(row.get("risk_flags") or "")):
                risk_flags.setdefault(token_id, set()).add(flag)
    return labels, risk_flags


def unresolved_targets(row: dict[str, str]) -> list[str]:
    targets: list[str] = []
    if str(row.get("founder_status") or "").strip() == "unresolved":
        targets.append("founder")
    if str(row.get("related_company_status") or "").strip() == "unresolved":
        targets.append("related_company")
    if str(row.get("foundation_status") or "").strip() == "unresolved":
        targets.append("foundation")
    return targets


def main() -> None:
    args = parse_args()
    source_labels, sentence_risk_flags = load_sentence_metadata(args.sentences_csv.resolve())
    input_csv = args.results_csv.resolve()
    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        extra_fields = ["validation_issues"]
        with output_csv.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames + extra_fields)
            writer.writeheader()

            for row in reader:
                token_id = str(row.get("token_id") or "").strip()
                token_type = str(row.get("token_type") or "").strip()
                confidence = str(row.get("confidence") or "").strip().lower()
                issues: list[str] = []
                labels = source_labels.get(token_id, set())
                flags = sentence_risk_flags.get(token_id, set())
                unresolved = unresolved_targets(row)

                if unresolved:
                    issues.append("unresolved_targets=" + ",".join(unresolved))
                if token_type in HIGH_RISK_TOKEN_TYPES:
                    issues.append(f"high_risk_token_type={token_type}")
                if confidence == "low":
                    issues.append("low_confidence")
                if "official_site" not in labels and (
                    str(row.get("related_company_status") or "").strip() == "supported"
                    or str(row.get("foundation_status") or "").strip() == "supported"
                ):
                    issues.append("supported_company_or_foundation_without_official_site_sentence")
                if flags:
                    issues.append("sentence_risk_flags=" + ",".join(sorted(flags)))

                updated = dict(row)
                if issues:
                    updated["needs_manual_review"] = "1"
                updated["validation_issues"] = json.dumps(sorted(set(issues)), ensure_ascii=False)
                writer.writerow(updated)


if __name__ == "__main__":
    main()
