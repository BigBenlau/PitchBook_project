#!/usr/bin/env python3
"""
Extract high-signal candidate sentences from CG/CMC text and official evidence.

Harness batch example:
python3 part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/2_filter_candidate_sentences.py \
  --merged-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/merged_input.csv \
  --official-evidence-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/official_evidence.csv \
  --output-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_evidence_sentences.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_MERGED_CSV = OUTPUT_DIR / "coingecko_about_with_cmc_about.csv"
DEFAULT_OFFICIAL_EVIDENCE_CSV = OUTPUT_DIR / "official_evidence.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "token_evidence_sentences.csv"
TRIGGER_PATTERNS = [
    "founder",
    "co-founder",
    "founded by",
    "created by",
    "invented by",
    "launched by",
    "issued by",
    "developed by",
    "operated by",
    "maintained by",
    "foundation",
    "labs",
    "dao",
    "association",
    "issuer",
    "parent company",
    "built by",
    "managed by",
    "governed by",
    "stewarded by",
    "core contributor",
    "operator",
    "team behind",
    "company behind",
    "entity behind",
]
NEGATIVE_PATTERNS = [
    "listed on",
    "traded on",
    "available on",
    "partnered with",
    "partnership with",
    "backed by",
    "invested by",
    "portfolio",
    "custody",
    "custodian",
]
VARIANT_PATTERNS = ["wrapped", "bridged", "staked", "liquid staking", "synthetic"]
OUTPUT_FIELDNAMES = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "source_type",
    "source_label",
    "source_url",
    "cmc_match_method",
    "trigger_keyword",
    "risk_flags",
    "sentence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter high-signal evidence sentences.")
    parser.add_argument("--merged-csv", type=Path, default=DEFAULT_MERGED_CSV)
    parser.add_argument("--official-evidence-csv", type=Path, default=DEFAULT_OFFICIAL_EVIDENCE_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--min-length", type=int, default=25)
    return parser.parse_args()


def derive_slug(token_href: str) -> str:
    path = urlparse((token_href or "").strip()).path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1].strip().lower()


def normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_sentence(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+|(?<=\")\s+(?=[A-Z])|(?<=\))\s+(?=[A-Z])", normalized)
    results: list[str] = []
    for part in parts:
        sentence = normalize_sentence(part)
        if sentence:
            results.append(sentence)
    return results


def detect_trigger(sentence: str) -> str:
    lowered = sentence.lower()
    for pattern in TRIGGER_PATTERNS:
        if pattern in lowered:
            return pattern
    return ""


def detect_risk_flags(sentence: str, token_name: str) -> list[str]:
    lowered = sentence.lower()
    token_lowered = token_name.lower()
    flags: list[str] = []
    if any(pattern in lowered for pattern in NEGATIVE_PATTERNS):
        flags.append("negative_relation_context")
    if "etf" in lowered and "issuer" in lowered:
        flags.append("etf_issuer_not_token_issuer")
    if "foundation" in lowered and any(
        pattern in lowered
        for pattern in (
            "technical foundation",
            "foundation for future",
            "foundation for the future",
            "laying out the technical foundation",
            "foundation of the protocol",
        )
    ):
        flags.append("non_org_foundation_context")
    if lowered.startswith(("who are the founder", "who were the founder")):
        flags.append("heading_without_entity")
    if any(pattern in token_lowered for pattern in VARIANT_PATTERNS):
        flags.append("variant_token")
    if "contributor" in lowered and "founder" not in lowered and "co-founder" not in lowered:
        flags.append("contributor_not_founder")
    if "ecosystem" in lowered and not any(term in lowered for term in ("issuer", "operator", "developer")):
        flags.append("ecosystem_context")
    return sorted(set(flags))


def iter_csv_rows(path: Path):
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            yield row


def load_official_rows(path: Path) -> dict[int, list[dict[str, str]]]:
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in iter_csv_rows(path) or []:
        try:
            row_index = int(str(row.get("row_index") or "").strip())
        except ValueError:
            continue
        grouped.setdefault(row_index, []).append(row)
    return grouped


def write_sentence(
    writer: csv.DictWriter,
    *,
    row_index: int,
    token_name: str,
    token_symbol: str,
    token_href: str,
    source_type: str,
    source_label: str,
    source_url: str,
    cmc_match_method: str,
    text: str,
    min_length: int,
    seen: set[tuple[int, str, str]],
) -> None:
    slug = derive_slug(token_href)
    for sentence in split_sentences(text):
        if len(sentence) < min_length:
            continue
        trigger = detect_trigger(sentence)
        if not trigger:
            continue
        risk_flags = detect_risk_flags(sentence, token_name)
        dedupe_key = (row_index, source_type, sentence.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        writer.writerow(
            {
                "row_index": row_index,
                "token_name": token_name,
                "token_symbol": token_symbol,
                "token_href": token_href,
                "slug": slug,
                "source_type": source_type,
                "source_label": source_label,
                "source_url": source_url,
                "cmc_match_method": cmc_match_method,
                "trigger_keyword": trigger,
                "risk_flags": json.dumps(risk_flags, ensure_ascii=False),
                "sentence": sentence,
            }
        )


def main() -> None:
    args = parse_args()
    official_rows = load_official_rows(args.official_evidence_csv.resolve())
    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()
        seen: set[tuple[int, str, str]] = set()

        for row_index, row in enumerate(iter_csv_rows(args.merged_csv.resolve()) or [], start=1):
            token_name = str(row.get("token_name") or "").strip()
            token_symbol = str(row.get("token_symbol") or "").strip()
            token_href = str(row.get("token_href") or "").strip()

            write_sentence(
                writer,
                row_index=row_index,
                token_name=token_name,
                token_symbol=token_symbol,
                token_href=token_href,
                source_type="coingecko_about",
                source_label="CoinGecko about_text",
                source_url="",
                cmc_match_method=str(row.get("cmc_match_method") or ""),
                text=str(row.get("about_text") or ""),
                min_length=args.min_length,
                seen=seen,
            )
            write_sentence(
                writer,
                row_index=row_index,
                token_name=token_name,
                token_symbol=token_symbol,
                token_href=token_href,
                source_type="cmc_about",
                source_label="CoinMarketCap about_text",
                source_url="",
                cmc_match_method=str(row.get("cmc_match_method") or ""),
                text=str(row.get("cmc_about_text") or ""),
                min_length=args.min_length,
                seen=seen,
            )

            for official_row in official_rows.get(row_index, []):
                if str(official_row.get("status") or "").strip() != "ok":
                    continue
                write_sentence(
                    writer,
                    row_index=row_index,
                    token_name=token_name,
                    token_symbol=token_symbol,
                    token_href=token_href,
                    source_type="official_site",
                    source_label=str(official_row.get("page_type") or "official"),
                    source_url=str(official_row.get("source_url") or ""),
                    cmc_match_method=str(row.get("cmc_match_method") or ""),
                    text=str(official_row.get("paragraph_text") or ""),
                    min_length=args.min_length,
                    seen=seen,
                )


if __name__ == "__main__":
    main()
