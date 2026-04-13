#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_DIR.parent

DEFAULT_INPUT_CSV = REPO_ROOT / "part2_build_crypto_candidate" / "output" / "crypto_company.csv"
DEFAULT_TEMPLATE = PART5_DIR / "agent_prompt_template.md"
DEFAULT_OUTPUT_DIR = PART5_DIR / "agent_task_batches" / "crypto_company"
DEFAULT_BATCH_SIZE = 30
DEFAULT_SEARCH_POLICY = "free_search_with_primary_source_priority"
DEFAULT_TASK_SCOPE = "company_relevance_classification|project_token_mapping|fungible_token_ticker"

INPUT_COLUMNS = [
    "task_index",
    "CompanyID",
    "CompanyName",
    "CompanyAlsoKnownAs",
    "CompanyFormerName",
    "CompanyLegalName",
    "Website",
    "normalized_domain",
    "ParentCompany",
    "Exchange",
    "Ticker",
    "HQLocation",
    "HQCountry",
    "Verticals",
    "EmergingSpaces",
    "Description",
    "Keywords",
    "MatchedKeywords",
    "MatchedColumns",
    "CryptoRelevanceContext",
    "SearchPolicy",
    "AgentTaskScope",
]

PROMPT_PLACEHOLDERS = [
    "skill_path",
    "task_index",
    "CompanyID",
    "CompanyName",
    "CompanyAlsoKnownAs",
    "CompanyFormerName",
    "CompanyLegalName",
    "Website",
    "normalized_domain",
    "ParentCompany",
    "Exchange",
    "Ticker",
    "HQLocation",
    "HQCountry",
    "Verticals",
    "EmergingSpaces",
    "Description",
    "Keywords",
    "MatchedKeywords",
    "MatchedColumns",
    "CryptoRelevanceContext",
    "SearchPolicy",
    "AgentTaskScope",
    "completed_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Extract part5 token-review inputs from crypto_company.csv and build "
            "agent-ready JSONL batches."
        )
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help="Source crypto_company.csv. Defaults to part2_build_crypto_candidate/output/crypto_company.csv.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Prompt template. Defaults to part5_analyse_company_to_token/agent_prompt_template.md.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for input_companies.csv, manifest.csv, and batch_XXXX.jsonl files.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of companies per batch JSONL file.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N selected rows.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of selected rows to write. 0 means no limit.",
    )
    parser.add_argument(
        "--company-id",
        action="append",
        default=[],
        help="Filter to specific CompanyID values. Repeat or pass comma-separated values.",
    )
    parser.add_argument(
        "--description-max-chars",
        type=int,
        default=700,
        help="Maximum characters retained from Description.",
    )
    parser.add_argument(
        "--keywords-max-chars",
        type=int,
        default=300,
        help="Maximum characters retained from Keywords.",
    )
    parser.add_argument(
        "--context-max-chars",
        type=int,
        default=300,
        help="Maximum characters retained from crypto relevance context.",
    )
    return parser.parse_args()


def flatten_company_ids(raw_values: Iterable[str]) -> set[str]:
    company_ids: set[str] = set()
    for raw_value in raw_values:
        for value in raw_value.split(","):
            item = value.strip()
            if item:
                company_ids.add(item)
    return company_ids


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


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


def build_crypto_relevance_context(source_row: dict[str, str], max_chars: int) -> str:
    parts: list[str] = []
    for label, column in [
        ("Relation_Verticals", "Relation_Verticals"),
        ("Relation_SimilarVerticals", "Relation_SimilarVerticals"),
        ("Relation_CompetitorVerticals", "Relation_CompetitorVerticals"),
        ("MatchedKeywords", "MatchedKeywords"),
        ("MatchedColumns", "MatchedColumns"),
    ]:
        value = normalize_text(source_row.get(column, ""))
        if value:
            parts.append(f"{label}: {value}")
    return limit_text(" | ".join(parts), max_chars)


def load_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        return list(reader)


def filter_rows(rows: list[dict[str, str]], company_ids: set[str]) -> list[dict[str, str]]:
    if not company_ids:
        return rows
    return [row for row in rows if (row.get("CompanyID") or "").strip() in company_ids]


def slice_rows(rows: list[dict[str, str]], offset: int, limit: int) -> list[dict[str, str]]:
    selected = rows[offset:] if offset > 0 else rows
    if limit > 0:
        selected = selected[:limit]
    return selected


def build_input_row(
    source_row: dict[str, str],
    task_index: int,
    description_max_chars: int,
    keywords_max_chars: int,
    context_max_chars: int,
) -> dict[str, str]:
    output = {
        "task_index": str(task_index),
        "CompanyID": normalize_text(source_row.get("CompanyID", "")),
        "CompanyName": normalize_text(source_row.get("CompanyName", "")),
        "CompanyAlsoKnownAs": normalize_text(source_row.get("CompanyAlsoKnownAs", "")),
        "CompanyFormerName": normalize_text(source_row.get("CompanyFormerName", "")),
        "CompanyLegalName": normalize_text(source_row.get("CompanyLegalName", "")),
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
        "Verticals": normalize_text(source_row.get("Verticals", "")),
        "EmergingSpaces": normalize_text(source_row.get("EmergingSpaces", "")),
        "Description": limit_text(source_row.get("Description", ""), description_max_chars),
        "Keywords": limit_text(source_row.get("Keywords", ""), keywords_max_chars),
        "MatchedKeywords": normalize_text(source_row.get("MatchedKeywords", "")),
        "MatchedColumns": normalize_text(source_row.get("MatchedColumns", "")),
        "CryptoRelevanceContext": build_crypto_relevance_context(source_row, context_max_chars),
        "SearchPolicy": DEFAULT_SEARCH_POLICY,
        "AgentTaskScope": DEFAULT_TASK_SCOPE,
    }
    return {column: output.get(column, "") for column in INPUT_COLUMNS}


def render_prompt(template: str, values: dict[str, str]) -> str:
    rendered = template
    prompt_values = {
        **values,
        "skill_path": str((REPO_ROOT / "skills" / "crypto-token-review").resolve()),
        "completed_at": "",
    }
    for field in PROMPT_PLACEHOLDERS:
        value = prompt_values.get(field, "")
        rendered = rendered.replace(f"{{{{{field}}}}}", value)
        rendered = rendered.replace(f"{{{field}}}", value)
    return rendered


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
        "CompanyID",
        "CompanyName",
        "normalized_domain",
        "SearchPolicy",
        "AgentTaskScope",
    ]
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for index, row in enumerate(rows):
            batch_index = index // batch_size + 1
            writer.writerow(
                {
                    "task_index": row["task_index"],
                    "batch_index": str(batch_index),
                    "batch_file": f"batch_{batch_index:04d}.jsonl",
                    "CompanyID": row["CompanyID"],
                    "CompanyName": row["CompanyName"],
                    "normalized_domain": row["normalized_domain"],
                    "SearchPolicy": row["SearchPolicy"],
                    "AgentTaskScope": row["AgentTaskScope"],
                }
            )


def write_batches(
    output_dir: Path,
    rows: list[dict[str, str]],
    template: str,
    template_path: Path,
    batch_size: int,
) -> int:
    batch_count = 0
    for start in range(0, len(rows), batch_size):
        batch_count += 1
        batch_rows = rows[start : start + batch_size]
        batch_file = output_dir / f"batch_{batch_count:04d}.jsonl"
        with batch_file.open("w", encoding="utf-8") as outfile:
            for row in batch_rows:
                payload = {
                    "task_index": int(row["task_index"]),
                    "batch_index": batch_count,
                    "company_id": row["CompanyID"],
                    "company_name": row["CompanyName"],
                    "normalized_domain": row["normalized_domain"],
                    "search_policy": row["SearchPolicy"],
                    "agent_task_scope": row["AgentTaskScope"],
                    "plan": relative_path(PART5_DIR / "Plan.md"),
                    "prompt_template": relative_path(template_path),
                    "input_row": row,
                    "prompt": render_prompt(template, row),
                }
                outfile.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return batch_count


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be greater than 0.")
    if args.offset < 0:
        raise SystemExit("--offset must be 0 or greater.")
    if args.limit < 0:
        raise SystemExit("--limit must be 0 or greater.")

    input_csv = ensure_file(args.input_csv, "Input CSV")
    template_path = ensure_file(args.template, "Template")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    template = template_path.read_text(encoding="utf-8")
    source_rows = load_rows(input_csv)
    filtered_rows = filter_rows(source_rows, flatten_company_ids(args.company_id))
    selected_rows = slice_rows(filtered_rows, args.offset, args.limit)
    if not selected_rows:
        raise SystemExit("No rows selected for batch generation.")

    input_rows = [
        build_input_row(
            row,
            task_index=index,
            description_max_chars=args.description_max_chars,
            keywords_max_chars=args.keywords_max_chars,
            context_max_chars=args.context_max_chars,
        )
        for index, row in enumerate(selected_rows, start=1)
    ]

    write_input_csv(output_dir / "input_companies.csv", input_rows)
    write_manifest(output_dir / "manifest.csv", input_rows, args.batch_size)
    batch_count = write_batches(output_dir, input_rows, template, template_path, args.batch_size)

    print(f"Input CSV: {input_csv}")
    print(f"Source rows: {len(source_rows)}")
    print(f"Selected rows: {len(input_rows)}")
    print(f"Output directory: {output_dir}")
    print(f"Extracted input CSV: {output_dir / 'input_companies.csv'}")
    print(f"Manifest: {output_dir / 'manifest.csv'}")
    print(f"Batches written: {batch_count}")


if __name__ == "__main__":
    main()
