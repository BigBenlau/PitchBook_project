#!/usr/bin/env python3
"""
Collect high-signal founder/company paragraphs from official token websites.

Example:
python3 part4/2_collect_official_evidence.py --input-csv part4/output/coingecko_about_with_cmc_about.csv
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
OUTPUT_DIR = SCRIPT_DIR / "output"
DEFAULT_INPUT_CSV = OUTPUT_DIR / "coingecko_about_with_cmc_about.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "official_evidence.csv"
DEFAULT_MAX_PAGES = 5
DEFAULT_MAX_PARAGRAPHS = 5
REQUEST_DELAY_SECONDS = 0.5
RETRY_LIMIT = 3
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
PAGE_SUFFIXES = ["", "/about", "/team", "/foundation", "/docs", "/whitepaper", "/litepaper"]
SIGNAL_PATTERNS = [
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
]
OUTPUT_FIELDNAMES = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
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
NON_OFFICIAL_KEYWORDS = (
    "twitter",
    "x.com",
    "facebook",
    "instagram",
    "youtube",
    "linkedin",
    "discord",
    "telegram",
    "reddit",
    "github",
    "gitbook",
    "medium.com",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect official-site founder/company evidence.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-csv", type=Path, default=DEFAULT_OUTPUT_CSV)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    parser.add_argument("--max-paragraphs", type=int, default=DEFAULT_MAX_PARAGRAPHS)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(value or "").replace("\xa0", " ")).strip()


def derive_slug(token_href: str) -> str:
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
    result: dict[str, str] = {}
    for key, item in data.items():
        item_text = str(item or "").strip()
        if item_text:
            result[str(key or "").strip()] = item_text
    return result


def choose_official_website(row: dict[str, str]) -> str:
    explicit = str(row.get("official_website") or "").strip()
    if explicit:
        return explicit

    websites = parse_json_object(str(row.get("websites") or ""))
    for _, url in websites.items():
        lowered = url.lower()
        if lowered.startswith(("http://", "https://")) and not any(
            keyword in lowered for keyword in NON_OFFICIAL_KEYWORDS
        ):
            return url
    return ""


def canonicalize_root_url(url: str) -> str:
    parsed = urlparse(url.strip())
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
        page_type = suffix.strip("/") or "home"
        candidates.append((url, page_type))
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
        reader = csv.DictReader(infile)
        for index, row in enumerate(reader, start=1):
            yield index, row


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.resolve()
    output_csv = args.output_csv.resolve()
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with output_csv.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        writer.writeheader()

        for row_index, row in iter_input_rows(input_csv):
            if row_index <= args.offset:
                continue
            if args.limit > 0 and row_index > args.offset + args.limit:
                break

            token_name = str(row.get("token_name") or "").strip()
            token_symbol = str(row.get("token_symbol") or "").strip()
            token_href = str(row.get("token_href") or "").strip()
            slug = derive_slug(token_href)
            official_website = canonicalize_root_url(choose_official_website(row))

            if not official_website:
                writer.writerow(
                    {
                        "row_index": row_index,
                        "token_name": token_name,
                        "token_symbol": token_symbol,
                        "token_href": token_href,
                        "slug": slug,
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

                if not selected:
                    continue

                for rank, (paragraph, hits) in enumerate(selected, start=1):
                    writer.writerow(
                        {
                            "row_index": row_index,
                            "token_name": token_name,
                            "token_symbol": token_symbol,
                            "token_href": token_href,
                            "slug": slug,
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
                        "row_index": row_index,
                        "token_name": token_name,
                        "token_symbol": token_symbol,
                        "token_href": token_href,
                        "slug": slug,
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
