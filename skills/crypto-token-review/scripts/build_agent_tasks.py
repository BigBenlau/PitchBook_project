#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
DEFAULT_INPUT_CSV = REPO_ROOT / "part4" / "project_review_queue.csv"
DEFAULT_TEMPLATE = SKILL_DIR / "references" / "agent_task_prompt.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "part4" / "agent_task_batches"
DEFAULT_BATCH_SIZE = 200
DEFAULT_ALLOWED_SOURCES = "official_site|coingecko|coinmarketcap"
DEFAULT_TASK_SCOPE = "project_token_mapping|token_ticker"

PLACEHOLDERS = [
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
    "allowed_sources",
    "agent_task_scope",
]

UNRESOLVED_FIELDS = [
    "has_token",
    "token_ticker",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build agent-ready batch prompts for crypto token review.",
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help="Queue CSV to read. Defaults to part4/project_review_queue.csv.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Prompt template file with {{placeholders}}.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where manifest.csv and batch_XXXX.jsonl files are written.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of tasks per JSONL batch file.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N selected rows before writing tasks.",
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
        "--only-unresolved",
        action="store_true",
        help="Only include rows whose token output fields are still blank.",
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


def ensure_path(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    return resolved


def normalize_text(value: str) -> str:
    return " ".join((value or "").split())


def limit_text(value: str, max_chars: int) -> str:
    normalized = normalize_text(value)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip()


def derive_normalized_domain(website: str, normalized_domain: str) -> str:
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


def is_unresolved(row: dict[str, str]) -> bool:
    return all(not (row.get(field) or "").strip() for field in UNRESOLVED_FIELDS)


def render_template(template: str, values: dict[str, str]) -> str:
    rendered = template
    for field in PLACEHOLDERS:
        rendered = rendered.replace(f"{{{{{field}}}}}", values.get(field, ""))
    return rendered


def load_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        return list(reader)


def filter_rows(
    rows: list[dict[str, str]],
    company_ids: set[str],
    only_unresolved: bool,
) -> list[dict[str, str]]:
    filtered: list[dict[str, str]] = []
    for row in rows:
        company_id = (row.get("CompanyID") or "").strip()
        if company_ids and company_id not in company_ids:
            continue
        if only_unresolved and not is_unresolved(row):
            continue
        filtered.append(row)
    return filtered


def slice_rows(rows: list[dict[str, str]], offset: int, limit: int) -> list[dict[str, str]]:
    selected = rows[offset:] if offset > 0 else rows
    if limit > 0:
        selected = selected[:limit]
    return selected


def build_prompt_values(row: dict[str, str]) -> dict[str, str]:
    normalized_domain = derive_normalized_domain(
        row.get("Website", ""),
        row.get("normalized_domain", ""),
    )
    values: dict[str, str] = {
        "skill_path": str(SKILL_DIR.resolve()),
        "allowed_sources": (row.get("allowed_sources") or DEFAULT_ALLOWED_SOURCES).strip(),
        "agent_task_scope": (row.get("agent_task_scope") or DEFAULT_TASK_SCOPE).strip(),
        "normalized_domain": normalized_domain,
    }
    for field in PLACEHOLDERS:
        if field in values:
            continue
        if field == "Description":
            values[field] = limit_text(row.get(field, ""), 700)
        elif field == "Keywords":
            values[field] = limit_text(row.get(field, ""), 300)
        else:
            values[field] = normalize_text(row.get(field, ""))
    return values


def write_manifest(
    manifest_path: Path,
    manifest_rows: list[dict[str, str]],
) -> None:
    fieldnames = [
        "task_index",
        "batch_index",
        "batch_file",
        "CompanyID",
        "CompanyName",
        "normalized_domain",
        "allowed_sources",
        "agent_task_scope",
    ]
    with manifest_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)


def write_batches(
    rows: list[dict[str, str]],
    template: str,
    template_path: Path,
    output_dir: Path,
    batch_size: int,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, str]] = []

    batch_number = 0
    for start in range(0, len(rows), batch_size):
        batch_number += 1
        batch_rows = rows[start : start + batch_size]
        batch_file = output_dir / f"batch_{batch_number:04d}.jsonl"

        with batch_file.open("w", encoding="utf-8") as outfile:
            for index_within_batch, row in enumerate(batch_rows, start=1):
                task_index = start + index_within_batch
                values = build_prompt_values(row)
                values["task_index"] = str(task_index)
                prompt = render_template(template, values)
                payload = {
                    "task_index": task_index,
                    "batch_index": batch_number,
                    "company_id": row.get("CompanyID", ""),
                    "company_name": row.get("CompanyName", ""),
                    "normalized_domain": values["normalized_domain"],
                    "allowed_sources": values["allowed_sources"],
                    "agent_task_scope": values["agent_task_scope"],
                    "prompt_template": (
                        str(template_path.resolve().relative_to(REPO_ROOT))
                        if template_path.resolve().is_relative_to(REPO_ROOT)
                        else str(template_path.resolve())
                    ),
                    "prompt": prompt,
                }
                outfile.write(json.dumps(payload, ensure_ascii=True) + "\n")

                manifest_rows.append(
                    {
                        "task_index": str(task_index),
                        "batch_index": str(batch_number),
                        "batch_file": batch_file.name,
                        "CompanyID": row.get("CompanyID", ""),
                        "CompanyName": row.get("CompanyName", ""),
                        "normalized_domain": values["normalized_domain"],
                        "allowed_sources": values["allowed_sources"],
                        "agent_task_scope": values["agent_task_scope"],
                    }
                )

    write_manifest(output_dir / "manifest.csv", manifest_rows)


def main() -> None:
    args = parse_args()

    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be greater than 0.")
    if args.offset < 0:
        raise SystemExit("--offset must be 0 or greater.")
    if args.limit < 0:
        raise SystemExit("--limit must be 0 or greater.")

    input_csv = ensure_path(args.input_csv, "Input CSV")
    template_path = ensure_path(args.template, "Template")
    output_dir = args.output_dir.resolve()
    company_ids = flatten_company_ids(args.company_id)

    template = template_path.read_text(encoding="utf-8")
    rows = load_rows(input_csv)
    filtered_rows = filter_rows(rows, company_ids, args.only_unresolved)
    selected_rows = slice_rows(filtered_rows, args.offset, args.limit)

    if not selected_rows:
        raise SystemExit("No rows selected for task generation.")

    write_batches(selected_rows, template, template_path, output_dir, args.batch_size)

    print(f"Input rows: {len(rows)}")
    print(f"Selected rows: {len(selected_rows)}")
    print(f"Output directory: {output_dir}")
    print(f"Batches written: {(len(selected_rows) - 1) // args.batch_size + 1}")
    print(f"Manifest: {output_dir / 'manifest.csv'}")


if __name__ == "__main__":
    main()
