#!/usr/bin/env python3
"""
Collect high-signal company/foundation/operator paragraphs from official token websites.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_INPUT_CSV = OUTPUT_DIR / "token_master.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "official_evidence.csv"
DEFAULT_MAX_PAGES = 6
DEFAULT_MAX_PARAGRAPHS = 6
REQUEST_DELAY_SECONDS = 0.5
RETRY_LIMIT = 3

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)

PAGE_SUFFIXES = [
    "",
    "/about",
    "/company",
    "/foundation",
    "/governance",
    "/legal",
    "/team",
    "/docs",
    "/whitepaper",
    "/litepaper",
]

SIGNAL_PATTERNS = [
    "issuer",
    "issuing entity",
    "developed by",
    "operated by",
    "maintained by",
    "managed by",
    "governed by",
    "parent company",
    "trust company",
    "foundation",
    "association",
    "dao",
    "labs",
    "founded by",
    "created by",
    "co-founder",
    "founder",
]

OUTPUT_FIELDNAMES = [
    "token_id",
    "token_name",
    "token_symbol",
    "token_type",
    "official_website",
    "source_url",
    "page_type",
    "paragraph_rank",
    "keyword_hits",
    "paragraph_text",
    "status",
    "error",
]

SKIP_TAGS = {"script", "style", "svg", "noscript"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "div"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect official-site company/foundation evidence.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-paragraphs", type=int, default=DEFAULT_MAX_PARAGRAPHS)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "").replace("\xa0", " ")).strip()


def canonicalize_root_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def build_candidate_urls(root_url: str, max_pages: int) -> list[tuple[str, str]]:
    seen: set[str] = set()
    candidates: list[tuple[str, str]] = []
    for suffix in PAGE_SUFFIXES:
        if len(candidates) >= max_pages:
            break
        url = root_url if not suffix else urljoin(root_url.rstrip("/") + "/", suffix.lstrip("/"))
        normalized = url.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append((url, suffix.strip("/") or "home"))
    return candidates


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            with urlopen(request, timeout=20) as response:
                status = getattr(response, "status", None)
                body = response.read().decode("utf-8", errors="replace")
                if status == 200:
                    return body
                if attempt == RETRY_LIMIT:
                    raise SystemExit(f"Failed to fetch {url}: status={status}")
        except (HTTPError, URLError):
            if attempt == RETRY_LIMIT:
                raise
        time.sleep(REQUEST_DELAY_SECONDS)
    return ""


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.skip_depth = 0
        self.block_depth = 0
        self.current_parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip_depth > 0:
            self.skip_depth += 1
            return
        if tag in SKIP_TAGS:
            self.skip_depth = 1
            return
        if tag in BLOCK_TAGS:
            self.flush()
            self.block_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth > 0:
            self.skip_depth -= 1
            return
        if tag in BLOCK_TAGS:
            self.flush()
            if self.block_depth > 0:
                self.block_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth == 0:
            self.current_parts.append(data)

    def flush(self) -> None:
        text = normalize_whitespace(" ".join(self.current_parts))
        self.current_parts = []
        if len(text) >= 40:
            self.paragraphs.append(text)


def extract_paragraphs(html: str) -> list[str]:
    parser = VisibleTextParser()
    parser.feed(html)
    parser.flush()
    return parser.paragraphs


def paragraph_keyword_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in SIGNAL_PATTERNS if pattern in lowered]


def select_top_paragraphs(paragraphs: Iterable[str], max_paragraphs: int) -> list[tuple[str, list[str]]]:
    scored: list[tuple[int, int, str, list[str]]] = []
    for paragraph in paragraphs:
        hits = paragraph_keyword_hits(paragraph)
        if not hits:
            continue
        score = len(hits)
        scored.append((score, len(paragraph), paragraph, hits))
    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))

    selected: list[tuple[str, list[str]]] = []
    seen_texts: set[str] = set()
    for _, _, paragraph, hits in scored:
        key = paragraph.lower()
        if key in seen_texts:
            continue
        seen_texts.add(key)
        selected.append((paragraph, hits))
        if len(selected) >= max_paragraphs:
            break
    return selected


def iter_input_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        for row in csv.DictReader(infile):
            yield row


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.resolve()
    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()

        for row_number, row in enumerate(iter_input_rows(input_csv), start=1):
            if row_number <= args.offset:
                continue
            if args.limit > 0 and row_number > args.offset + args.limit:
                break

            token_id = str(row.get("token_id") or "").strip()
            token_name = str(row.get("token_name") or "").strip()
            token_symbol = str(row.get("token_symbol") or "").strip()
            token_type = str(row.get("token_type") or "").strip()
            official_website = canonicalize_root_url(str(row.get("official_website") or ""))

            if not official_website:
                writer.writerow(
                    {
                        "token_id": token_id,
                        "token_name": token_name,
                        "token_symbol": token_symbol,
                        "token_type": token_type,
                        "official_website": "",
                        "source_url": "",
                        "page_type": "",
                        "paragraph_rank": "",
                        "keyword_hits": "[]",
                        "paragraph_text": "",
                        "status": "no_website",
                        "error": "",
                    }
                )
                continue

            wrote_signal = False
            last_error = ""
            for source_url, page_type in build_candidate_urls(official_website, args.max_pages):
                try:
                    html = fetch_html(source_url)
                    paragraphs = extract_paragraphs(html)
                    selected = select_top_paragraphs(paragraphs, args.max_paragraphs)
                except (HTTPError, URLError) as exc:
                    last_error = str(exc)
                    continue

                for rank, (paragraph, hits) in enumerate(selected, start=1):
                    writer.writerow(
                        {
                            "token_id": token_id,
                            "token_name": token_name,
                            "token_symbol": token_symbol,
                            "token_type": token_type,
                            "official_website": official_website,
                            "source_url": source_url,
                            "page_type": page_type,
                            "paragraph_rank": rank,
                            "keyword_hits": json.dumps(hits, ensure_ascii=False),
                            "paragraph_text": paragraph,
                            "status": "ok",
                            "error": "",
                        }
                    )
                    wrote_signal = True

            if not wrote_signal:
                writer.writerow(
                    {
                        "token_id": token_id,
                        "token_name": token_name,
                        "token_symbol": token_symbol,
                        "token_type": token_type,
                        "official_website": official_website,
                        "source_url": "",
                        "page_type": "",
                        "paragraph_rank": "",
                        "keyword_hits": "[]",
                        "paragraph_text": "",
                        "status": "no_signal",
                        "error": last_error,
                    }
                )


if __name__ == "__main__":
    main()
