from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
COINGECKO_PATH = OUTPUT_DIR / "coingecko_all_crypto_list.csv"
COINMARKETCAP_PATH = OUTPUT_DIR / "coinmarketcap_list.csv"
MERGED_OUTPUT_PATH = OUTPUT_DIR / "coingecko_coinmarketcap_union.csv"

OUTPUT_FIELDNAMES = [
    "index",
    "canonical_slug",
    "token_name",
    "token_symbol",
    "from_cmc",
    "from_cg",
    "match_method",
    "cg_name",
    "cg_symbol",
    "cg_slug",
    "cg_page",
    "cmc_name",
    "cmc_symbol",
    "cmc_slug",
    "cmc_rank",
]

GENERIC_NAME_SUFFIXES = {
    "chain",
    "coin",
    "dao",
    "defi",
    "ecosystem",
    "finance",
    "foundation",
    "governance",
    "network",
    "protocol",
    "token",
}

# Manual overrides are intended for agent-reviewed or otherwise high-confidence
# rebrands / legacy slug differences that are not captured by deterministic rules.
MANUAL_OVERRIDES: dict[str, str] = {
    "aada-finance": "lenfi",
    "derace": "zkrace",
    "breederdao": "sovrun",
    "forj": "bondly",
    "stader": "strx",
}


@dataclass(frozen=True)
class CoinGeckoRow:
    row_index: int
    page: str
    name: str
    symbol: str
    slug: str


@dataclass(frozen=True)
class CoinMarketCapRow:
    row_index: int
    rank: str
    name: str
    symbol: str
    slug: str


def normalize_symbol(value: str) -> str:
    return value.strip().upper()


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def loose_name_key(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    while tokens and tokens[-1] in GENERIC_NAME_SUFFIXES:
        tokens.pop()
    return "".join(tokens)


def cmc_rank_key(value: str) -> tuple[int, int]:
    if value.isdigit():
        return (0, int(value))
    return (1, 0)


def choose_display_name(cg: CoinGeckoRow | None, cmc: CoinMarketCapRow | None) -> str:
    if cg and not cmc:
        return cg.name
    if cmc and not cg:
        return cmc.name
    assert cg and cmc
    candidates = [cg.name.strip(), cmc.name.strip()]
    if normalize_name(candidates[0]) == normalize_name(candidates[1]):
        return min(candidates, key=lambda item: (len(item), item.lower()))
    if loose_name_key(candidates[0]) == loose_name_key(candidates[1]):
        return min(candidates, key=lambda item: (len(item), item.lower()))
    normalized = [normalize_name(item) for item in candidates]
    if normalized[0] and normalized[1]:
        shorter, longer = sorted(candidates, key=len)
        short_norm, long_norm = sorted(normalized, key=len)
        if short_norm and short_norm in long_norm:
            return shorter
    return cmc.name


def choose_display_symbol(cg: CoinGeckoRow | None, cmc: CoinMarketCapRow | None) -> str:
    if cg and not cmc:
        return cg.symbol
    if cmc and not cg:
        return cmc.symbol
    assert cg and cmc
    if normalize_symbol(cg.symbol) == normalize_symbol(cmc.symbol):
        return cmc.symbol
    return cmc.symbol or cg.symbol


def choose_canonical_id(cg: CoinGeckoRow | None, cmc: CoinMarketCapRow | None) -> str:
    if cmc and cmc.slug:
        return cmc.slug
    if cg and cg.slug:
        return cg.slug
    raise ValueError("Expected at least one source slug")


def load_coingecko_rows() -> list[CoinGeckoRow]:
    deduped_rows: dict[str, CoinGeckoRow] = {}
    with COINGECKO_PATH.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        for row_index, row in enumerate(reader, start=1):
            token_href = (row.get("token_href") or "").strip()
            slug = token_href.rstrip("/").split("/")[-1].strip()
            if not slug:
                continue
            candidate = CoinGeckoRow(
                row_index=row_index,
                page=(row.get("page") or "").strip(),
                name=(row.get("token_name") or "").strip(),
                symbol=(row.get("token_symbol") or "").strip(),
                slug=slug,
            )
            existing = deduped_rows.get(slug)
            if existing is None or candidate.row_index < existing.row_index:
                deduped_rows[slug] = candidate
    return list(deduped_rows.values())


def load_coinmarketcap_rows() -> list[CoinMarketCapRow]:
    rows: list[CoinMarketCapRow] = []
    with COINMARKETCAP_PATH.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        for row_index, row in enumerate(reader, start=1):
            slug = (row.get("slug") or "").strip()
            if not slug:
                continue
            rows.append(
                CoinMarketCapRow(
                    row_index=row_index,
                    rank=(row.get("cmc_rank") or "").strip(),
                    name=(row.get("name") or "").strip(),
                    symbol=(row.get("symbol") or "").strip(),
                    slug=slug,
                )
            )
    return rows


def build_output_row(
    cg: CoinGeckoRow | None,
    cmc: CoinMarketCapRow | None,
    match_method: str,
) -> dict[str, str]:
    return {
        "index": "",
        "canonical_slug": choose_canonical_id(cg, cmc),
        "token_name": choose_display_name(cg, cmc),
        "token_symbol": choose_display_symbol(cg, cmc),
        "from_cmc": "1" if cmc else "0",
        "from_cg": "1" if cg else "0",
        "match_method": match_method,
        "cg_name": cg.name if cg else "",
        "cg_symbol": cg.symbol if cg else "",
        "cg_slug": cg.slug if cg else "",
        "cg_page": cg.page if cg else "",
        "cmc_name": cmc.name if cmc else "",
        "cmc_symbol": cmc.symbol if cmc else "",
        "cmc_slug": cmc.slug if cmc else "",
        "cmc_rank": cmc.rank if cmc else "",
    }


def try_pair_unique_symbol_rows(
    cg_rows: list[CoinGeckoRow],
    cmc_rows: list[CoinMarketCapRow],
) -> list[tuple[CoinGeckoRow, CoinMarketCapRow, str]]:
    matches: list[tuple[CoinGeckoRow, CoinMarketCapRow, str]] = []

    cg_by_symbol: dict[str, list[CoinGeckoRow]] = defaultdict(list)
    cmc_by_symbol: dict[str, list[CoinMarketCapRow]] = defaultdict(list)

    for row in cg_rows:
        cg_by_symbol[normalize_symbol(row.symbol)].append(row)
    for row in cmc_rows:
        cmc_by_symbol[normalize_symbol(row.symbol)].append(row)

    for symbol in sorted(set(cg_by_symbol) & set(cmc_by_symbol)):
        left = cg_by_symbol[symbol]
        right = cmc_by_symbol[symbol]
        strict_pairs: list[tuple[CoinGeckoRow, CoinMarketCapRow]] = []
        loose_pairs: list[tuple[CoinGeckoRow, CoinMarketCapRow]] = []

        cg_by_strict_name: dict[str, list[CoinGeckoRow]] = defaultdict(list)
        cmc_by_strict_name: dict[str, list[CoinMarketCapRow]] = defaultdict(list)
        cg_by_loose_name: dict[str, list[CoinGeckoRow]] = defaultdict(list)
        cmc_by_loose_name: dict[str, list[CoinMarketCapRow]] = defaultdict(list)

        for row in left:
            cg_by_strict_name[normalize_name(row.name)].append(row)
            cg_by_loose_name[loose_name_key(row.name)].append(row)
        for row in right:
            cmc_by_strict_name[normalize_name(row.name)].append(row)
            cmc_by_loose_name[loose_name_key(row.name)].append(row)

        for name_key in sorted(set(cg_by_strict_name) & set(cmc_by_strict_name)):
            if not name_key:
                continue
            if len(cg_by_strict_name[name_key]) == 1 and len(cmc_by_strict_name[name_key]) == 1:
                strict_pairs.append((cg_by_strict_name[name_key][0], cmc_by_strict_name[name_key][0]))

        matched_cg_slugs = {cg.slug for cg, _ in strict_pairs}
        matched_cmc_slugs = {cmc.slug for _, cmc in strict_pairs}

        for name_key in sorted(set(cg_by_loose_name) & set(cmc_by_loose_name)):
            if not name_key:
                continue
            cg_name_rows = [row for row in cg_by_loose_name[name_key] if row.slug not in matched_cg_slugs]
            cmc_name_rows = [row for row in cmc_by_loose_name[name_key] if row.slug not in matched_cmc_slugs]
            if len(cg_name_rows) == 1 and len(cmc_name_rows) == 1:
                loose_pairs.append((cg_name_rows[0], cmc_name_rows[0]))
                matched_cg_slugs.add(cg_name_rows[0].slug)
                matched_cmc_slugs.add(cmc_name_rows[0].slug)

        for cg, cmc in strict_pairs:
            matches.append((cg, cmc, "same_symbol_same_name"))

        for cg, cmc in loose_pairs:
            matches.append((cg, cmc, "same_symbol_loose_name"))

        if len(left) == 1 and len(right) == 1:
            cg = left[0]
            cmc = right[0]
            if cg.slug in matched_cg_slugs or cmc.slug in matched_cmc_slugs:
                continue
    return matches


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cg_rows = load_coingecko_rows()
    cmc_rows = load_coinmarketcap_rows()

    cg_by_slug = {row.slug: row for row in cg_rows}
    cmc_by_slug = {row.slug: row for row in cmc_rows}

    used_cg_slugs: set[str] = set()
    used_cmc_slugs: set[str] = set()
    merged_rows: list[dict[str, str]] = []

    exact_slug_pairs = sorted(set(cg_by_slug) & set(cmc_by_slug))
    for slug in exact_slug_pairs:
        cg = cg_by_slug[slug]
        cmc = cmc_by_slug[slug]
        merged_rows.append(build_output_row(cg, cmc, "exact_slug"))
        used_cg_slugs.add(slug)
        used_cmc_slugs.add(slug)

    remaining_cg = [row for row in cg_rows if row.slug not in used_cg_slugs]
    remaining_cmc = [row for row in cmc_rows if row.slug not in used_cmc_slugs]

    auto_pairs = try_pair_unique_symbol_rows(remaining_cg, remaining_cmc)
    for cg, cmc, method in auto_pairs:
        if cg.slug in used_cg_slugs or cmc.slug in used_cmc_slugs:
            continue
        merged_rows.append(build_output_row(cg, cmc, method))
        used_cg_slugs.add(cg.slug)
        used_cmc_slugs.add(cmc.slug)

    for cg_slug, cmc_slug in MANUAL_OVERRIDES.items():
        if cg_slug in used_cg_slugs or cmc_slug in used_cmc_slugs:
            continue
        cg = cg_by_slug.get(cg_slug)
        cmc = cmc_by_slug.get(cmc_slug)
        if not cg or not cmc:
            continue
        merged_rows.append(build_output_row(cg, cmc, "manual_override"))
        used_cg_slugs.add(cg.slug)
        used_cmc_slugs.add(cmc.slug)

    for row in cg_rows:
        if row.slug in used_cg_slugs:
            continue
        merged_rows.append(build_output_row(row, None, "cg_only"))

    for row in cmc_rows:
        if row.slug in used_cmc_slugs:
            continue
        merged_rows.append(build_output_row(None, row, "cmc_only"))

    merged_rows.sort(
        key=lambda row: (
            cmc_rank_key(row["cmc_rank"]),
            row["canonical_slug"].lower(),
        )
    )

    for index, row in enumerate(merged_rows, start=1):
        row["index"] = str(index)

    with MERGED_OUTPUT_PATH.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        writer.writerows(merged_rows)

    method_counter = Counter(row["match_method"] for row in merged_rows)
    print(f"Wrote {len(merged_rows)} merged rows to {MERGED_OUTPUT_PATH}")
    for method, count in sorted(method_counter.items()):
        print(f"{method}: {count}")


if __name__ == "__main__":
    main()
