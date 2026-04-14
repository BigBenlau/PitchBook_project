#!/usr/bin/env python3
"""
Extract target-aware evidence sentences from official evidence first, then CG/CMC text.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_BATCH_CSV = OUTPUT_DIR / "token_master.csv"
DEFAULT_OFFICIAL_EVIDENCE_CSV = OUTPUT_DIR / "official_evidence.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "entity_sentences.csv"

FOUNDER_TRIGGERS = ["founder", "co-founder", "founded by", "created by", "invented by"]
COMPANY_TRIGGERS = [
    "issuer",
    "issuing entity",
    "operated by",
    "developed by",
    "maintained by",
    "managed by",
    "parent company",
    "trust company",
    "company behind",
    "entity behind",
]
FOUNDATION_TRIGGERS = ["foundation", "dao", "association", "labs", "governed by", "stewarded by"]
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
]
VARIANT_PATTERNS = ["wrapped", "bridged", "staked", "liquid staking", "synthetic"]

OUTPUT_FIELDNAMES = [
    "token_id",
    "token_name",
    "token_symbol",
    "token_type",
    "source_type",
    "source_label",
    "source_url",
    "target_group",
    "trigger_keyword",
    "risk_flags",
    "sentence",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter target-aware evidence sentences.")
    parser.add_argument("--batch-csv", type=Path, default=DEFAULT_BATCH_CSV)
    parser.add_argument("--official-evidence-csv", type=Path, default=DEFAULT_OFFICIAL_EVIDENCE_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--min-length", type=int, default=25)
    return parser.parse_args()


def normalize_sentence(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_sentences(text: str) -> list[str]:
    normalized = normalize_sentence(text)
    if not normalized:
        return []
    return [part for part in re.split(r"(?<=[.!?])\s+|(?<=\))\s+(?=[A-Z])", normalized) if part]


def detect_trigger(sentence: str) -> tuple[str, str]:
    lowered = sentence.lower()
    for pattern in COMPANY_TRIGGERS:
        if pattern in lowered:
            return "related_company", pattern
    for pattern in FOUNDATION_TRIGGERS:
        if pattern in lowered:
            return "foundation", pattern
    for pattern in FOUNDER_TRIGGERS:
        if pattern in lowered:
            return "founder", pattern
    return "", ""


def detect_risk_flags(sentence: str, token_name: str, token_type: str) -> list[str]:
    lowered = sentence.lower()
    token_lowered = token_name.lower()
    flags: list[str] = []
    if any(pattern in lowered for pattern in NEGATIVE_PATTERNS):
        flags.append("negative_relation_context")
    if any(pattern in token_lowered for pattern in VARIANT_PATTERNS):
        flags.append("variant_token")
    if token_type in {"wrapped_or_bridged", "liquid_staking_or_receipt", "synthetic_or_fund"}:
        flags.append("high_risk_token_type")
    if "contributor" in lowered and "founder" not in lowered and "co-founder" not in lowered:
        flags.append("contributor_not_founder")
    return sorted(set(flags))


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


def iter_csv_rows(path: Path):
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        for row in csv.DictReader(infile):
            yield row


def load_official_rows(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in iter_csv_rows(path) or []:
        token_id = str(row.get("token_id") or "").strip()
        if not token_id:
            continue
        grouped.setdefault(token_id, []).append(row)
    return grouped


def write_sentences(
    writer: csv.DictWriter,
    *,
    token_id: str,
    token_name: str,
    token_symbol: str,
    token_type: str,
    source_type: str,
    source_label: str,
    source_url: str,
    text: str,
    min_length: int,
    seen: set[tuple[str, str, str, str]],
) -> None:
    for sentence in split_sentences(text):
        if len(sentence) < min_length:
            continue
        target_group, trigger = detect_trigger(sentence)
        if not target_group:
            continue
        risk_flags = detect_risk_flags(sentence, token_name, token_type)
        dedupe_key = (token_id, source_type, target_group, sentence.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        writer.writerow(
            {
                "token_id": token_id,
                "token_name": token_name,
                "token_symbol": token_symbol,
                "token_type": token_type,
                "source_type": source_type,
                "source_label": source_label,
                "source_url": source_url,
                "target_group": target_group,
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
        seen: set[tuple[str, str, str, str]] = set()

        for row in iter_csv_rows(args.batch_csv.resolve()) or []:
            token_id = str(row.get("token_id") or "").strip()
            token_name = str(row.get("token_name") or "").strip()
            token_symbol = str(row.get("token_symbol") or "").strip()
            token_type = str(row.get("token_type") or "").strip()

            for official_row in official_rows.get(token_id, []):
                if str(official_row.get("status") or "").strip() != "ok":
                    continue
                write_sentences(
                    writer,
                    token_id=token_id,
                    token_name=token_name,
                    token_symbol=token_symbol,
                    token_type=token_type,
                    source_type="official_site",
                    source_label=str(official_row.get("page_type") or "official"),
                    source_url=str(official_row.get("source_url") or ""),
                    text=str(official_row.get("paragraph_text") or ""),
                    min_length=args.min_length,
                    seen=seen,
                )

            write_sentences(
                writer,
                token_id=token_id,
                token_name=token_name,
                token_symbol=token_symbol,
                token_type=token_type,
                source_type="coingecko_about",
                source_label="CoinGecko about_text",
                source_url="",
                text=str(row.get("coingecko_about_text") or ""),
                min_length=args.min_length,
                seen=seen,
            )
            write_sentences(
                writer,
                token_id=token_id,
                token_name=token_name,
                token_symbol=token_symbol,
                token_type=token_type,
                source_type="cmc_about",
                source_label="CoinMarketCap about_text",
                source_url="",
                text=str(row.get("cmc_about_text") or ""),
                min_length=args.min_length,
                seen=seen,
            )


if __name__ == "__main__":
    main()
