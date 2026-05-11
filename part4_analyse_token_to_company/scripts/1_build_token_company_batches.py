#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent

DEFAULT_INPUT_CSV = (
    REPO_ROOT
    / "part3_find_token_list_at_cg_and_cmc"
    / "output"
    / "coingecko_coinmarketcap_union.csv"
)
DEFAULT_TEMPLATE = PART4_DIR / "agent_prompt_template.md"
DEFAULT_OUTPUT_DIR = PART4_DIR / "agent_task_batches" / "token_company"
DEFAULT_BATCH_SIZE = 30
DEFAULT_SEARCH_POLICY = "free_search_with_primary_source_priority"
DEFAULT_TASK_SCOPE = "token_identity_classification|project_company_mapping"

INPUT_COLUMNS = [
    "task_index",
    "canonical_slug",
    "token_name",
    "token_symbol",
    "cg_name",
    "cg_symbol",
    "cg_slug",
    "cg_url",
    "cmc_name",
    "cmc_symbol",
    "cmc_slug",
    "cmc_url",
    "cmc_rank",
    "from_cg",
    "from_cmc",
    "match_method",
    "source_presence",
    "SearchPolicy",
    "AgentTaskScope",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build part4 token-to-company JSONL batches from a normalized token CSV.",
    )
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--canonical-slug",
        action="append",
        default=[],
        help="Filter to specific canonical_slug values. Repeat or pass comma-separated values.",
    )
    parser.add_argument(
        "--token-symbol",
        action="append",
        default=[],
        help="Filter to specific token symbols. Repeat or pass comma-separated values.",
    )
    return parser.parse_args()


def flatten_values(raw_values: list[str]) -> set[str]:
    values: set[str] = set()
    for raw_value in raw_values:
        for value in raw_value.split(","):
            item = value.strip()
            if item:
                values.add(item.lower())
    return values


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def normalize_text(value: object) -> str:
    return " ".join(str(value or "").split())


def build_cg_url(slug: str) -> str:
    slug = normalize_text(slug)
    return f"https://www.coingecko.com/en/coins/{slug}" if slug else ""


def build_cmc_url(slug: str) -> str:
    slug = normalize_text(slug)
    return f"https://coinmarketcap.com/currencies/{slug}/" if slug else ""


def load_rows(input_csv: Path) -> list[dict[str, str]]:
    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def normalize_input_row(source_row: dict[str, str], task_index: int) -> dict[str, str]:
    canonical_slug = normalize_text(source_row.get("canonical_slug", "")).lower()
    token_name = normalize_text(source_row.get("token_name", ""))
    token_symbol = normalize_text(source_row.get("token_symbol", "")).upper()
    cg_slug = normalize_text(source_row.get("cg_slug", "")).lower()
    cmc_slug = normalize_text(source_row.get("cmc_slug", "")).lower()
    from_cg = normalize_text(source_row.get("from_cg", ""))
    from_cmc = normalize_text(source_row.get("from_cmc", ""))

    source_presence_parts: list[str] = []
    if from_cg in {"1", "true", "yes"}:
        source_presence_parts.append("coingecko")
    if from_cmc in {"1", "true", "yes"}:
        source_presence_parts.append("coinmarketcap")

    output = {
        "task_index": str(task_index),
        "canonical_slug": canonical_slug,
        "token_name": token_name,
        "token_symbol": token_symbol,
        "cg_name": normalize_text(source_row.get("cg_name", "")),
        "cg_symbol": normalize_text(source_row.get("cg_symbol", "")).upper(),
        "cg_slug": cg_slug,
        "cg_url": build_cg_url(cg_slug),
        "cmc_name": normalize_text(source_row.get("cmc_name", "")),
        "cmc_symbol": normalize_text(source_row.get("cmc_symbol", "")).upper(),
        "cmc_slug": cmc_slug,
        "cmc_url": build_cmc_url(cmc_slug),
        "cmc_rank": normalize_text(source_row.get("cmc_rank", "")),
        "from_cg": from_cg,
        "from_cmc": from_cmc,
        "match_method": normalize_text(source_row.get("match_method", "")),
        "source_presence": "|".join(source_presence_parts),
        "SearchPolicy": DEFAULT_SEARCH_POLICY,
        "AgentTaskScope": DEFAULT_TASK_SCOPE,
    }
    return {column: output.get(column, "") for column in INPUT_COLUMNS}


def filter_rows(
    rows: list[dict[str, str]],
    canonical_slugs: set[str],
    token_symbols: set[str],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for row in rows:
        slug = normalize_text(row.get("canonical_slug", "")).lower()
        symbol = normalize_text(row.get("token_symbol", "")).lower()
        if canonical_slugs and slug not in canonical_slugs:
            continue
        if token_symbols and symbol not in token_symbols:
            continue
        output.append(row)
    return output


def slice_rows(rows: list[dict[str, str]], offset: int, limit: int) -> list[dict[str, str]]:
    selected = rows[offset:] if offset > 0 else rows
    if limit > 0:
        selected = selected[:limit]
    return selected


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, rows: list[dict[str, str]], batch_size: int) -> None:
    manifest_rows: list[dict[str, str]] = []
    for batch_index, start in enumerate(range(0, len(rows), batch_size), start=1):
        chunk = rows[start : start + batch_size]
        manifest_rows.append(
            {
                "batch_index": str(batch_index),
                "batch_file": f"batch_{batch_index:04d}.jsonl",
                "task_count": str(len(chunk)),
                "first_task_index": chunk[0]["task_index"],
                "last_task_index": chunk[-1]["task_index"],
                "first_token": chunk[0]["token_name"],
                "last_token": chunk[-1]["token_name"],
            }
        )
    write_csv(
        path,
        [
            "batch_index",
            "batch_file",
            "task_count",
            "first_task_index",
            "last_task_index",
            "first_token",
            "last_token",
        ],
        manifest_rows,
    )


def write_batches(output_dir: Path, rows: list[dict[str, str]], batch_size: int) -> None:
    if batch_size <= 0:
        raise SystemExit("--batch-size must be greater than 0")

    for batch_index, start in enumerate(range(0, len(rows), batch_size), start=1):
        chunk = rows[start : start + batch_size]
        batch_path = output_dir / f"batch_{batch_index:04d}.jsonl"
        with batch_path.open("w", encoding="utf-8") as outfile:
            for row in chunk:
                payload = {
                    "task_index": int(row["task_index"]),
                    "batch_index": batch_index,
                    "canonical_slug": row["canonical_slug"],
                    "token_name": row["token_name"],
                    "token_symbol": row["token_symbol"],
                    "cg_url": row["cg_url"],
                    "cmc_url": row["cmc_url"],
                    "from_cg": row["from_cg"],
                    "from_cmc": row["from_cmc"],
                    "company_id": row["canonical_slug"],
                    "company_name": row["token_name"],
                    "normalized_domain": row["canonical_slug"],
                    "search_policy": row["SearchPolicy"],
                    "agent_task_scope": row["AgentTaskScope"],
                    "plan": relative_path(PART4_DIR / "Plan.md"),
                    "prompt_template": relative_path(PART4_DIR / "agent_prompt_template.md"),
                    "input_row": row,
                }
                outfile.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> None:
    args = parse_args()
    input_csv = ensure_file(args.input_csv, "Input CSV")
    ensure_file(args.template, "Prompt template")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    source_rows = load_rows(input_csv)
    selected_source_rows = slice_rows(
        filter_rows(
            source_rows,
            canonical_slugs=flatten_values(args.canonical_slug),
            token_symbols=flatten_values(args.token_symbol),
        ),
        offset=args.offset,
        limit=args.limit,
    )
    if not selected_source_rows:
        raise SystemExit("No rows selected.")

    normalized_rows = [
        normalize_input_row(source_row, task_index=index)
        for index, source_row in enumerate(selected_source_rows, start=1)
    ]

    write_csv(output_dir / "input_tokens.csv", INPUT_COLUMNS, normalized_rows)
    write_manifest(output_dir / "manifest.csv", normalized_rows, args.batch_size)
    write_batches(output_dir, normalized_rows, args.batch_size)

    print(f"Input CSV: {input_csv.resolve()}")
    print(f"Output dir: {output_dir}")
    print(f"Selected rows: {len(normalized_rows)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Manifest: {output_dir / 'manifest.csv'}")


if __name__ == "__main__":
    main()
