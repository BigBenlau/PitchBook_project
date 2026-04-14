from __future__ import annotations

"""
整體用途：
1. 讀取 part3_find_token_list_at_cg_and_cmc/output/coingecko_about.csv
   與 part3_find_token_list_at_cg_and_cmc/output/cmc_about_qa.csv。
2. 按 coingecko_about.csv 的 token 順序輸出。
3. 將 CoinMarketCap 的 about_text 欄位按 slug 合併到 CoinGecko 資料中。
4. 將 merged CSV 寫到 part4_analyse_token_to_company/output/。
"""

import csv
import re
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
PART3_OUTPUT_DIR = PROJECT_DIR.parent / "part3_find_token_list_at_cg_and_cmc" / "output"
OUTPUT_DIR = PROJECT_DIR / "output"
COINGECKO_PATH = PART3_OUTPUT_DIR / "coingecko_about.csv"
CMC_PATH = PART3_OUTPUT_DIR / "cmc_about_qa.csv"
OUTPUT_PATH = OUTPUT_DIR / "coingecko_about_with_cmc_about.csv"


def normalize_slug_from_href(token_href: str) -> str:
    """從 CoinGecko token_href 提取 slug。"""
    value = (token_href or "").strip()
    if not value:
        return ""
    path = urlparse(value).path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1].strip().lower()


def normalize_symbol(value: str) -> str:
    """標準化 symbol。"""
    return (value or "").strip().upper()


def normalize_name(value: str) -> str:
    """標準化 token 名稱，供模糊匹配使用。"""
    text = (value or "").strip().lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def load_cmc_rows() -> list[dict[str, str]]:
    """讀取 CoinMarketCap about_text 原始行。"""
    if not CMC_PATH.is_file():
        raise SystemExit(f"Missing input CSV: {CMC_PATH}")

    rows: list[dict[str, str]] = []
    with CMC_PATH.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        required = {"token_name", "symbol", "slug", "about_text"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"Missing required columns in {CMC_PATH}: {', '.join(sorted(missing))}")

        for row in reader:
            rows.append(
                {
                    "token_name": str(row.get("token_name") or "").strip(),
                    "symbol": normalize_symbol(str(row.get("symbol") or "")),
                    "slug": str(row.get("slug") or "").strip().lower(),
                    "about_text": str(row.get("about_text") or "").strip(),
                }
            )
    return rows


def build_index(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    """按指定字段建立一對多索引。"""
    indexed: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value:
            continue
        indexed.setdefault(value, []).append(row)
    return indexed


def choose_unique_name_match(
    candidates: list[dict[str, str]],
    normalized_source_name: str,
) -> dict[str, str] | None:
    """在候選集中按名稱做精確唯一匹配。"""
    if not normalized_source_name:
        return None

    exact_matches = [
        row for row in candidates if normalize_name(str(row.get("token_name") or "")) == normalized_source_name
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]

    return None


def match_cmc_row(
    *,
    slug: str,
    symbol: str,
    token_name: str,
    by_slug: dict[str, list[dict[str, str]]],
    by_symbol: dict[str, list[dict[str, str]]],
    by_name: dict[str, list[dict[str, str]]],
    cmc_rows: list[dict[str, str]],
) -> tuple[dict[str, str] | None, str]:
    """依序用 slug、symbol、name 匹配 CMC 行。"""
    if slug:
        slug_candidates = by_slug.get(slug, [])
        if len(slug_candidates) == 1:
            return slug_candidates[0], "slug"
        if len(slug_candidates) > 1:
            normalized_source_name = normalize_name(token_name)
            chosen = choose_unique_name_match(slug_candidates, normalized_source_name)
            if chosen:
                return chosen, "slug"

    normalized_source_name = normalize_name(token_name)
    if symbol:
        symbol_candidates = by_symbol.get(symbol, [])
        if len(symbol_candidates) == 1:
            return symbol_candidates[0], "symbol"
        if len(symbol_candidates) > 1:
            chosen = choose_unique_name_match(symbol_candidates, normalized_source_name)
            if chosen:
                return chosen, "symbol"

    if normalized_source_name:
        name_candidates = by_name.get(normalized_source_name, [])
        if len(name_candidates) == 1:
            return name_candidates[0], "name_exact"

    return None, "unmatched"


def main() -> None:
    """主流程：按 CoinGecko 順序合併 CoinMarketCap about_text 欄位。"""
    if not COINGECKO_PATH.is_file():
        raise SystemExit(f"Missing input CSV: {COINGECKO_PATH}")

    cmc_rows = load_cmc_rows()
    by_slug = build_index(cmc_rows, "slug")
    by_symbol = build_index(cmc_rows, "symbol")
    by_name = build_index(
        [
            {**row, "normalized_name": normalize_name(str(row.get("token_name") or ""))}
            for row in cmc_rows
        ],
        "normalized_name",
    )

    with COINGECKO_PATH.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise SystemExit(f"No headers found in {COINGECKO_PATH}")
        if "token_href" not in fieldnames:
            raise SystemExit(f"Missing required columns in {COINGECKO_PATH}: token_href")

        output_fieldnames = fieldnames + ["cmc_about_text", "cmc_match_method"]
        rows_written = 0
        matched_by_slug = 0
        matched_by_symbol = 0
        matched_by_name = 0
        unmatched_rows = 0

        with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()

            for row in reader:
                token_name = str(row.get("token_name") or "").strip()
                token_symbol = normalize_symbol(str(row.get("token_symbol") or ""))
                slug = normalize_slug_from_href(str(row.get("token_href") or ""))
                matched_row, match_method = match_cmc_row(
                    slug=slug,
                    symbol=token_symbol,
                    token_name=token_name,
                    by_slug=by_slug,
                    by_symbol=by_symbol,
                    by_name=by_name,
                    cmc_rows=cmc_rows,
                )
                cmc_about_text = str((matched_row or {}).get("about_text") or "")

                if match_method == "slug":
                    matched_by_slug += 1
                elif match_method == "symbol":
                    matched_by_symbol += 1
                    print(
                        f"[fallback:symbol] slug not matched for token_name={token_name} "
                        f"symbol={token_symbol} slug={slug or '-'} -> "
                        f"cmc_name={matched_row['token_name']} cmc_slug={matched_row['slug']}",
                        flush=True,
                    )
                elif match_method == "name_exact":
                    matched_by_name += 1
                    print(
                        f"[fallback:name] slug not matched for token_name={token_name} "
                        f"symbol={token_symbol} slug={slug or '-'} -> "
                        f"cmc_name={matched_row['token_name']} cmc_slug={matched_row['slug']}",
                        flush=True,
                    )
                else:
                    unmatched_rows += 1
                    print(
                        f"[unmatched] slug not matched for token_name={token_name} "
                        f"symbol={token_symbol} slug={slug or '-'}",
                        flush=True,
                    )

                writer.writerow(
                    {
                        **row,
                        "cmc_about_text": cmc_about_text,
                        "cmc_match_method": match_method,
                    }
                )
                rows_written += 1

    print(
        f"Wrote {rows_written} rows to {OUTPUT_PATH} "
        f"(slug={matched_by_slug}, symbol={matched_by_symbol}, "
        f"name={matched_by_name}, unmatched={unmatched_rows})",
        flush=True,
    )


if __name__ == "__main__":
    main()
