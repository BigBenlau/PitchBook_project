#!/usr/bin/env python3
"""
Build Part4 token_master.csv from the union of CoinGecko and CoinMarketCap token lists,
assign a stable token_id, route token_type, and split deterministic batch inputs.

Example:
python3 part4_analyse_token_to_company/scripts/0_prepare_input_batches.py \
  --coingecko-csv part3_find_token_list_at_cg_and_cmc/output/coingecko_about.csv \
  --cmc-csv part3_find_token_list_at_cg_and_cmc/output/cmc_about_qa.csv \
  --batch-size 500 \
  --overwrite
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent
PART3_OUTPUT_DIR = REPO_ROOT / "part3_find_token_list_at_cg_and_cmc" / "output"
INPUT_DIR = PART4_DIR / "input"
OUTPUT_DIR = PART4_DIR / "output"

DEFAULT_COINGECKO_CSV = PART3_OUTPUT_DIR / "coingecko_about.csv"
DEFAULT_CMC_CSV = PART3_OUTPUT_DIR / "cmc_about_qa.csv"
DEFAULT_TOKEN_MASTER_CSV = OUTPUT_DIR / "token_master.csv"
DEFAULT_BATCH_DIR = INPUT_DIR / "batches"
DEFAULT_MANIFEST = INPUT_DIR / "batch_manifest.csv"
DEFAULT_BATCH_SIZE = 500

TOKEN_MASTER_COLUMNS = [
    "token_id",
    "token_name",
    "token_symbol",
    "coingecko_slug",
    "cmc_slug",
    "token_href",
    "official_website",
    "token_type",
    "source_presence",
    "cmc_match_method",
    "categories",
    "coingecko_about_text",
    "cmc_about_text",
]

MANIFEST_FIELDNAMES = [
    "batch_id",
    "batch_path",
    "row_count",
    "start_row",
    "end_row",
    "start_token_id",
    "end_token_id",
    "status",
]

SOCIAL_HOST_KEYWORDS = (
    "twitter",
    "x.com",
    "facebook",
    "instagram",
    "youtube",
    "linkedin",
    "discord",
    "telegram",
    "reddit",
    "medium.com",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build token_master.csv from the CG+CMC union and split deterministic batches."
    )
    parser.add_argument("--coingecko-csv", type=Path, default=DEFAULT_COINGECKO_CSV)
    parser.add_argument("--cmc-csv", type=Path, default=DEFAULT_CMC_CSV)
    parser.add_argument("--token-master-csv", type=Path, default=DEFAULT_TOKEN_MASTER_CSV)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove existing batch_*.csv files before writing new batches.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")
    if not args.coingecko_csv.is_file():
        raise SystemExit(f"CoinGecko CSV does not exist: {args.coingecko_csv}")
    if not args.cmc_csv.is_file():
        raise SystemExit(f"CoinMarketCap CSV does not exist: {args.cmc_csv}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def normalize_name(value: str) -> str:
    text = normalize_text(value).lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_symbol(value: str) -> str:
    return normalize_text(value).upper()


def slug_from_href(token_href: str) -> str:
    path = urlparse((token_href or "").strip()).path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1].strip().lower()


def parse_json_object(value: str) -> dict[str, str]:
    text = (value or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        normalize_text(str(key)): normalize_text(str(item))
        for key, item in data.items()
        if normalize_text(str(key)) and normalize_text(str(item))
    }


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
    return [normalize_text(str(item)) for item in data if normalize_text(str(item))]


def choose_official_website(websites_json: str) -> str:
    websites = parse_json_object(websites_json)
    for url in websites.values():
        lowered = url.lower()
        if lowered.startswith(("http://", "https://")) and not any(
            keyword in lowered for keyword in SOCIAL_HOST_KEYWORDS
        ):
            return url
    return ""


def build_token_id(*, coingecko_slug: str, cmc_slug: str, token_symbol: str, token_name: str) -> str:
    if coingecko_slug:
        return f"cg:{coingecko_slug}"
    if cmc_slug:
        return f"cmc:{cmc_slug}"
    normalized_name = normalize_name(token_name).replace(" ", "-")
    normalized_symbol = normalize_symbol(token_symbol).lower()
    suffix = "-".join(part for part in [normalized_name, normalized_symbol] if part) or "unknown"
    return f"token:{suffix}"


def route_token_type(
    *,
    token_name: str,
    token_symbol: str,
    categories: list[str],
    coingecko_about_text: str,
    cmc_about_text: str,
) -> str:
    name = normalize_text(token_name).lower()
    symbol = normalize_symbol(token_symbol).lower()
    category_text = " ".join(categories).lower()
    summary_text = " ".join(
        part[:600]
        for part in [coingecko_about_text.lower(), cmc_about_text.lower()]
        if part
    )
    identity_text = " ".join(part for part in [name, symbol, category_text] if part)

    if any(term in identity_text for term in ("wrapped", "bridged", "wrapped-", "tokenized bitcoin", "bridged usdt")):
        return "wrapped_or_bridged"
    if any(term in identity_text for term in ("staked", "liquid staking", "restaked", "receipt token", "yield-bearing")):
        return "liquid_staking_or_receipt"
    if any(term in identity_text for term in ("stablecoin", "usd₮", "usdt", "usdc", "usde", "susds", "usds", "tether")):
        return "fiat_stablecoin"
    if (
        "stablecoin" in summary_text
        or "digital dollar" in summary_text
        or "pegged 1:1" in summary_text
        or "pegged 1 1" in summary_text
    ):
        return "fiat_stablecoin"
    if any(term in identity_text for term in ("exchange token", "exchange-based token", "exchange-based")):
        return "exchange_token"
    if any(term in identity_text for term in ("synthetic", "etf", "vault share", "leveraged")):
        return "synthetic_or_fund"
    if any(term in identity_text for term in ("meme", "dog-themed", "community token", "community-driven")):
        return "meme_or_community"
    if any(term in category_text for term in ("layer 1", "layer 2", "proof of work", "proof of stake")):
        return "base_asset"
    if any(term in identity_text for term in ("protocol", "defi", "governance token", "smart contract platform", "dapp")):
        return "protocol_token"
    return "unknown"


def build_cmc_indexes(
    rows: list[dict[str, str]],
) -> tuple[dict[str, dict[str, str]], dict[tuple[str, str], dict[str, str]], dict[str, dict[str, str]]]:
    by_slug: dict[str, dict[str, str]] = {}
    by_symbol_name: dict[tuple[str, str], dict[str, str]] = {}
    by_name: dict[str, dict[str, str]] = {}
    for row in rows:
        slug = normalize_text(str(row.get("slug") or "")).lower()
        symbol = normalize_symbol(str(row.get("symbol") or ""))
        name = normalize_name(str(row.get("token_name") or ""))
        if slug and slug not in by_slug:
            by_slug[slug] = row
        if symbol and name and (symbol, name) not in by_symbol_name:
            by_symbol_name[(symbol, name)] = row
        if name and name not in by_name:
            by_name[name] = row
    return by_slug, by_symbol_name, by_name


def remove_existing_batches(batch_dir: Path) -> None:
    if not batch_dir.is_dir():
        return
    for path in batch_dir.glob("batch_*.csv"):
        path.unlink()


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def build_token_master_rows(coingecko_rows: list[dict[str, str]], cmc_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_slug, by_symbol_name, by_name = build_cmc_indexes(cmc_rows)
    used_cmc_keys: set[tuple[str, str, str]] = set()
    token_rows: list[dict[str, str]] = []

    for cg_row in coingecko_rows:
        token_name = normalize_text(str(cg_row.get("token_name") or ""))
        token_symbol = normalize_symbol(str(cg_row.get("token_symbol") or ""))
        token_href = normalize_text(str(cg_row.get("token_href") or ""))
        coingecko_slug = slug_from_href(token_href)
        categories = parse_json_list(str(cg_row.get("categories") or ""))
        websites_json = str(cg_row.get("websites") or "")
        matched_cmc = None
        match_method = "unmatched"

        if coingecko_slug and coingecko_slug in by_slug:
            matched_cmc = by_slug[coingecko_slug]
            match_method = "slug"
        else:
            key = (token_symbol, normalize_name(token_name))
            if key in by_symbol_name:
                matched_cmc = by_symbol_name[key]
                match_method = "symbol+name"
            else:
                normalized = normalize_name(token_name)
                if normalized in by_name:
                    matched_cmc = by_name[normalized]
                    match_method = "name_exact"

        cmc_slug = normalize_text(str((matched_cmc or {}).get("slug") or "")).lower()
        cmc_about_text = normalize_text(str((matched_cmc or {}).get("about_text") or ""))
        if matched_cmc:
            used_cmc_keys.add((normalize_name(str(matched_cmc.get("token_name") or "")), token_symbol, cmc_slug))

        token_rows.append(
            {
                "token_id": build_token_id(
                    coingecko_slug=coingecko_slug,
                    cmc_slug=cmc_slug,
                    token_symbol=token_symbol,
                    token_name=token_name,
                ),
                "token_name": token_name,
                "token_symbol": token_symbol,
                "coingecko_slug": coingecko_slug,
                "cmc_slug": cmc_slug,
                "token_href": token_href,
                "official_website": choose_official_website(websites_json),
                "token_type": route_token_type(
                    token_name=token_name,
                    token_symbol=token_symbol,
                    categories=categories,
                    coingecko_about_text=normalize_text(str(cg_row.get("about_text") or "")),
                    cmc_about_text=cmc_about_text,
                ),
                "source_presence": "cg+cmc" if matched_cmc else "cg_only",
                "cmc_match_method": match_method,
                "categories": json.dumps(categories, ensure_ascii=False),
                "coingecko_about_text": normalize_text(str(cg_row.get("about_text") or "")),
                "cmc_about_text": cmc_about_text,
            }
        )

    extra_cmc_rows: list[dict[str, str]] = []
    for cmc_row in cmc_rows:
        token_name = normalize_text(str(cmc_row.get("token_name") or ""))
        token_symbol = normalize_symbol(str(cmc_row.get("symbol") or ""))
        cmc_slug = normalize_text(str(cmc_row.get("slug") or "")).lower()
        key = (normalize_name(token_name), token_symbol, cmc_slug)
        if key in used_cmc_keys:
            continue
        extra_cmc_rows.append(
            {
                "token_id": build_token_id(
                    coingecko_slug="",
                    cmc_slug=cmc_slug,
                    token_symbol=token_symbol,
                    token_name=token_name,
                ),
                "token_name": token_name,
                "token_symbol": token_symbol,
                "coingecko_slug": "",
                "cmc_slug": cmc_slug,
                "token_href": "",
                "official_website": "",
                "token_type": route_token_type(
                    token_name=token_name,
                    token_symbol=token_symbol,
                    categories=[],
                    coingecko_about_text="",
                    cmc_about_text=normalize_text(str(cmc_row.get("about_text") or "")),
                ),
                "source_presence": "cmc_only",
                "cmc_match_method": "cmc_only",
                "categories": "[]",
                "coingecko_about_text": "",
                "cmc_about_text": normalize_text(str(cmc_row.get("about_text") or "")),
            }
        )

    all_rows = token_rows + sorted(extra_cmc_rows, key=lambda row: (row["token_name"].lower(), row["token_symbol"]))
    seen_token_ids: set[str] = set()
    deduped_rows: list[dict[str, str]] = []
    for row in all_rows:
        token_id = row["token_id"]
        if token_id in seen_token_ids:
            continue
        seen_token_ids.add(token_id)
        deduped_rows.append(row)
    return deduped_rows


def main() -> None:
    args = parse_args()
    validate_args(args)

    batch_dir = args.batch_dir.resolve()
    manifest_path = args.manifest.resolve()
    token_master_csv = args.token_master_csv.resolve()
    batch_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        remove_existing_batches(batch_dir)

    coingecko_rows = read_csv(args.coingecko_csv.resolve())
    cmc_rows = read_csv(args.cmc_csv.resolve())
    token_master_rows = build_token_master_rows(coingecko_rows, cmc_rows)
    write_csv(token_master_csv, TOKEN_MASTER_COLUMNS, token_master_rows)

    manifest_rows: list[dict[str, str]] = []
    total_rows = 0
    for batch_number, start in enumerate(range(0, len(token_master_rows), args.batch_size), start=1):
        subset = token_master_rows[start : start + args.batch_size]
        total_rows += len(subset)
        batch_path = batch_dir / f"batch_{batch_number:04d}.csv"
        write_csv(batch_path, TOKEN_MASTER_COLUMNS, subset)
        manifest_rows.append(
            {
                "batch_id": f"batch_{batch_number:04d}",
                "batch_path": relative_path(batch_path),
                "row_count": str(len(subset)),
                "start_row": str(start + 1),
                "end_row": str(start + len(subset)),
                "start_token_id": subset[0]["token_id"],
                "end_token_id": subset[-1]["token_id"],
                "status": "pending",
            }
        )

    write_csv(manifest_path, MANIFEST_FIELDNAMES, manifest_rows)
    print(f"Wrote token master with {len(token_master_rows)} rows.", flush=True)
    print(f"Token master CSV: {token_master_csv}", flush=True)
    print(f"Wrote {len(manifest_rows)} batches for {total_rows} rows.", flush=True)
    print(f"Batch directory: {batch_dir}", flush=True)
    print(f"Manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
