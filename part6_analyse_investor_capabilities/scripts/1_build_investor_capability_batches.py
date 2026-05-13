#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent

DEFAULT_INPUT_CSV = REPO_ROOT / "part2_build_crypto_candidate" / "output" / "crypto_investor.csv"
DEFAULT_OUTPUT_DIR = PART6_DIR / "agent_task_batches" / "crypto_investor"
DEFAULT_BATCH_SIZE = 30
DEFAULT_SEARCH_POLICY = "local_first_then_web_search_with_primary_source_priority"
DEFAULT_TASK_SCOPE = "investor_router|capability_classification"

INPUT_COLUMNS = [
    "task_index",
    "InvestorID",
    "InvestorName",
    "InvestorAlsoKnownAs",
    "InvestorFormerName",
    "InvestorLegalName",
    "Website",
    "normalized_domain",
    "ParentCompany",
    "Exchange",
    "Ticker",
    "HQLocation",
    "HQCountry",
    "PrimaryInvestorType",
    "OtherInvestorTypes",
    "PreferredInvestmentTypes",
    "PreferredVerticals",
    "OtherInvestmentPreferences",
    "LastClosedFundName",
    "LastClosedFundType",
    "Description",
    "MatchedKeywords",
    "MatchedColumns",
    "InvestorCapabilityContext",
    "SearchPolicy",
    "AgentTaskScope",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build investor capability task batches from crypto_investor.csv.",
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--investor-id",
        action="append",
        default=[],
        help="Filter to specific InvestorID values. Repeat or pass comma-separated values.",
    )
    parser.add_argument("--description-max-chars", type=int, default=700)
    parser.add_argument("--context-max-chars", type=int, default=400)
    return parser.parse_args()


def normalize_text(value: str) -> str:
    return " ".join((value or "").split())


def limit_text(value: str, max_chars: int) -> str:
    normalized = normalize_text(value)
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()


def derive_normalized_domain(website: str, normalized_domain: str = "") -> str:
    explicit = normalize_text(normalized_domain)
    if explicit:
        return explicit.lower()

    raw = normalize_text(website)
    if not raw:
        return ""

    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).strip().lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def flatten_ids(raw_values: Iterable[str]) -> set[str]:
    investor_ids: set[str] = set()
    for raw in raw_values:
        for value in raw.split(","):
            cleaned = value.strip()
            if cleaned:
                investor_ids.add(cleaned)
    return investor_ids


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def filter_rows(rows: list[dict[str, str]], investor_ids: set[str]) -> list[dict[str, str]]:
    if not investor_ids:
        return rows
    return [row for row in rows if (row.get("InvestorID") or "").strip() in investor_ids]


def slice_rows(rows: list[dict[str, str]], offset: int, limit: int) -> list[dict[str, str]]:
    selected = rows[offset:] if offset > 0 else rows
    if limit > 0:
        selected = selected[:limit]
    return selected


def build_context(source_row: dict[str, str], max_chars: int) -> str:
    parts: list[str] = []
    for label, column in [
        ("PrimaryInvestorType", "PrimaryInvestorType"),
        ("OtherInvestorTypes", "OtherInvestorTypes"),
        ("PreferredVerticals", "PreferredVerticals"),
        ("PreferredInvestmentTypes", "PreferredInvestmentTypes"),
        ("OtherInvestmentPreferences", "OtherInvestmentPreferences"),
        ("LastClosedFundName", "LastClosedFundName"),
        ("LastClosedFundType", "LastClosedFundType"),
        ("MatchedKeywords", "MatchedKeywords"),
        ("MatchedColumns", "MatchedColumns"),
    ]:
        value = normalize_text(source_row.get(column, ""))
        if value:
            parts.append(f"{label}: {value}")
    return limit_text(" | ".join(parts), max_chars)


def build_input_row(
    source_row: dict[str, str],
    task_index: int,
    description_max_chars: int,
    context_max_chars: int,
) -> dict[str, str]:
    output = {
        "task_index": str(task_index),
        "InvestorID": normalize_text(source_row.get("InvestorID", "")),
        "InvestorName": normalize_text(source_row.get("InvestorName", "")),
        "InvestorAlsoKnownAs": normalize_text(source_row.get("InvestorAlsoKnownAs", "")),
        "InvestorFormerName": normalize_text(source_row.get("InvestorFormerName", "")),
        "InvestorLegalName": normalize_text(source_row.get("InvestorLegalName", "")),
        "Website": normalize_text(source_row.get("Website", "")),
        "normalized_domain": derive_normalized_domain(
            source_row.get("Website", ""),
            source_row.get("normalized_domain", ""),
        ),
        "ParentCompany": normalize_text(source_row.get("ParentCompany", "")),
        "Exchange": normalize_text(source_row.get("Exchange", "")),
        "Ticker": normalize_text(source_row.get("Ticker", "")),
        "HQLocation": normalize_text(source_row.get("HQLocation", "")),
        "HQCountry": normalize_text(source_row.get("HQCountry", "")),
        "PrimaryInvestorType": normalize_text(source_row.get("PrimaryInvestorType", "")),
        "OtherInvestorTypes": normalize_text(source_row.get("OtherInvestorTypes", "")),
        "PreferredInvestmentTypes": normalize_text(source_row.get("PreferredInvestmentTypes", "")),
        "PreferredVerticals": normalize_text(source_row.get("PreferredVerticals", "")),
        "OtherInvestmentPreferences": normalize_text(source_row.get("OtherInvestmentPreferences", "")),
        "LastClosedFundName": normalize_text(source_row.get("LastClosedFundName", "")),
        "LastClosedFundType": normalize_text(source_row.get("LastClosedFundType", "")),
        "Description": limit_text(source_row.get("Description", ""), description_max_chars),
        "MatchedKeywords": normalize_text(source_row.get("MatchedKeywords", "")),
        "MatchedColumns": normalize_text(source_row.get("MatchedColumns", "")),
        "InvestorCapabilityContext": build_context(source_row, context_max_chars),
        "SearchPolicy": DEFAULT_SEARCH_POLICY,
        "AgentTaskScope": DEFAULT_TASK_SCOPE,
    }
    return {column: output.get(column, "") for column in INPUT_COLUMNS}


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def write_input_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=INPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, rows: list[dict[str, str]], batch_size: int) -> None:
    fieldnames = [
        "task_index",
        "batch_index",
        "batch_file",
        "InvestorID",
        "InvestorName",
        "normalized_domain",
        "PrimaryInvestorType",
        "SearchPolicy",
        "AgentTaskScope",
    ]
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            task_index = int(row["task_index"])
            batch_index = ((task_index - 1) // batch_size) + 1
            writer.writerow(
                {
                    "task_index": row["task_index"],
                    "batch_index": str(batch_index),
                    "batch_file": f"batch_{batch_index:04d}.jsonl",
                    "InvestorID": row["InvestorID"],
                    "InvestorName": row["InvestorName"],
                    "normalized_domain": row["normalized_domain"],
                    "PrimaryInvestorType": row["PrimaryInvestorType"],
                    "SearchPolicy": row["SearchPolicy"],
                    "AgentTaskScope": row["AgentTaskScope"],
                }
            )


def write_batches(output_dir: Path, rows: list[dict[str, str]], batch_size: int) -> None:
    for batch_start in range(0, len(rows), batch_size):
        batch_rows = rows[batch_start : batch_start + batch_size]
        batch_index = (batch_start // batch_size) + 1
        batch_path = output_dir / f"batch_{batch_index:04d}.jsonl"
        with batch_path.open("w", encoding="utf-8") as outfile:
            for row in batch_rows:
                payload = {
                    "task_index": row["task_index"],
                    "investor_id": row["InvestorID"],
                    "investor_name": row["InvestorName"],
                    "normalized_domain": row["normalized_domain"],
                    "primary_investor_type": row["PrimaryInvestorType"],
                    "input_row": row,
                }
                outfile.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    input_csv = ensure_file(args.input_csv, "input_csv")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rows = load_rows(input_csv)
    filtered_rows = filter_rows(source_rows, flatten_ids(args.investor_id))
    selected_rows = slice_rows(filtered_rows, args.offset, args.limit)

    if not selected_rows:
        raise SystemExit("No investor rows selected.")

    input_rows = [
        build_input_row(
            row,
            task_index=index,
            description_max_chars=args.description_max_chars,
            context_max_chars=args.context_max_chars,
        )
        for index, row in enumerate(selected_rows, start=1)
    ]

    input_csv_path = output_dir / "input_investors.csv"
    manifest_path = output_dir / "manifest.csv"

    write_input_csv(input_csv_path, input_rows)
    write_manifest(manifest_path, input_rows, args.batch_size)
    write_batches(output_dir, input_rows, args.batch_size)

    print(f"Input CSV: {relative_path(input_csv)}")
    print(f"Selected investors: {len(input_rows)}")
    print(f"Output dir: {relative_path(output_dir)}")
    print(f"Input rows CSV: {relative_path(input_csv_path)}")
    print(f"Manifest CSV: {relative_path(manifest_path)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Batch count: {(len(input_rows) + args.batch_size - 1) // args.batch_size}")


if __name__ == "__main__":
    main()
