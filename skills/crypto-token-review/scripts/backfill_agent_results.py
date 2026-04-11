#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
DEFAULT_INPUT_CSV = REPO_ROOT / "part2_build_crypto_candidate" / "output" / "crypto_company.csv"
DEFAULT_RUNS_DIR = REPO_ROOT / "part4" / "agent_runs"
OUTPUT_COLUMNS = [
    "has_token",
    "token_ticker",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
    "agent_task_status",
    "agent_result_source",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill Codex agent results into a CSV.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help="CSV to update by CompanyID.",
    )
    parser.add_argument(
        "--results-jsonl",
        type=Path,
        default=None,
        help="results.jsonl written during the Codex run.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Run directory containing results.jsonl.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Output CSV path. Defaults to <input>_backfilled.csv.",
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input CSV instead of writing a sibling output file.",
    )
    return parser.parse_args()


def resolve_results_path(args: argparse.Namespace) -> Path:
    if args.results_jsonl:
        return args.results_jsonl.resolve()
    if args.run_dir:
        return args.run_dir.resolve() / "results.jsonl"
    latest = sorted(DEFAULT_RUNS_DIR.glob("*/results.jsonl"))
    if not latest:
        raise SystemExit("No results.jsonl found. Pass --results-jsonl or --run-dir.")
    return latest[-1]


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def normalize_list(value: object) -> str:
    if not value:
        return ""
    if isinstance(value, list):
        return "|".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def build_company_results(rows: list[dict], result_source: str) -> dict[str, dict]:
    results: dict[str, dict] = {}
    for row in rows:
        company_id = str(row.get("company_id") or "")
        parsed = row.get("parsed_output")
        status = str(row.get("status") or "")
        if not company_id or not isinstance(parsed, dict) or status != "completed":
            continue
        results[company_id] = {
            "has_token": str(parsed.get("has_token") or ""),
            "token_ticker": str(parsed.get("token_ticker") or ""),
            "has_token_evidence": str(parsed.get("has_token_evidence") or ""),
            "evidence_urls": normalize_list(parsed.get("evidence_urls")),
            "evidence_source_types": normalize_list(parsed.get("evidence_source_types")),
            "confidence": str(parsed.get("confidence") or ""),
            "needs_manual_review": str(parsed.get("needs_manual_review") or ""),
            "agent_task_status": status,
            "agent_result_source": result_source,
        }
    return results


def main() -> None:
    args = parse_args()

    input_csv = args.input_csv.resolve()
    if not input_csv.exists():
        raise SystemExit(f"Input CSV does not exist: {input_csv}")

    results_path = resolve_results_path(args)
    if not results_path.exists():
        raise SystemExit(f"results.jsonl does not exist: {results_path}")

    rows = load_jsonl(results_path)
    company_results = build_company_results(rows, str(results_path))
    if not company_results:
        raise SystemExit("No completed parsed outputs found in results.jsonl.")

    output_csv = input_csv if args.in_place else (
        args.output_csv.resolve()
        if args.output_csv
        else input_csv.with_name(f"{input_csv.stem}_backfilled.csv")
    )

    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        for column in OUTPUT_COLUMNS:
            if column not in fieldnames:
                fieldnames.append(column)
        output_rows: list[dict[str, str]] = []
        updated = 0
        for row in reader:
            company_id = (row.get("CompanyID") or "").strip()
            if company_id in company_results:
                row.update(company_results[company_id])
                updated += 1
            output_rows.append(row)

    with output_csv.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"Input CSV: {input_csv}")
    print(f"Results log: {results_path}")
    print(f"Rows updated: {updated}")
    print(f"Output CSV: {output_csv}")


if __name__ == "__main__":
    main()
