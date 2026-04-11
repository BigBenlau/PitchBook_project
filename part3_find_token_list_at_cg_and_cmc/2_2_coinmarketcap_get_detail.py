from __future__ import annotations

"""
整體用途：
1. 讀取 output/coinmarketcap_list.csv 中的 token 清單。
2. 逐行訪問 https://coinmarketcap.com/currencies/{slug}/
3. 提取每個頁面 #section-coin-about 區塊中的整段文字內容。
4. 僅從頁面 DOM 提取內容，不使用頁面內嵌 JSON 回退。
5. 將結果寫入 output/cmc_about_qa.csv
"""

import csv
import re
import sys
import time
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
INPUT_PATH = OUTPUT_DIR / "coinmarketcap_list.csv"
OUTPUT_PATH = OUTPUT_DIR / "cmc_about_qa.csv"
DEBUG_HTML_DIR = OUTPUT_DIR / "cmc_about_debug_html"
URL_TEMPLATE = "https://coinmarketcap.com/currencies/{slug}/"
REQUEST_DELAY_SECONDS = 0.5
RETRY_LIMIT = 20
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
OUTPUT_FIELDNAMES = ["token_name", "symbol", "slug", "about_text"]
BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li"}
SKIP_TAGS = {"script", "style", "svg", "noscript"}


def normalize_text(value: str) -> str:
    """清理 HTML entity 與多餘空白。"""
    text = unescape(value or "")
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def fetch_html(url: str) -> str:
    """抓取頁面 HTML。"""
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
            with urlopen(request, timeout=30) as response:
                status = getattr(response, "status", None)
                body = response.read().decode("utf-8", errors="replace")
                if status != 200:
                    print(
                        f"[HTTP] attempt {attempt}/{RETRY_LIMIT} non-200 status {status}: {url}",
                        flush=True,
                    )
                    if attempt == RETRY_LIMIT:
                        raise SystemExit(
                            f"Failed to fetch page after {RETRY_LIMIT} attempts: {url}"
                        )
                    continue
                return body
        except HTTPError as exc:
            print(
                f"[HTTP] attempt {attempt}/{RETRY_LIMIT} HTTPError {exc.code}: {url}",
                flush=True,
            )
            if attempt == RETRY_LIMIT:
                raise SystemExit(
                    f"Failed to fetch page after {RETRY_LIMIT} attempts: HTTPError {exc.code} {url}"
                ) from exc
        except URLError as exc:
            print(
                f"[HTTP] attempt {attempt}/{RETRY_LIMIT} URLError: {url} ({exc})",
                flush=True,
            )
            if attempt == RETRY_LIMIT:
                raise SystemExit(
                    f"Failed to fetch page after {RETRY_LIMIT} attempts: URLError {url} ({exc})"
                ) from exc
        finally:
            time.sleep(REQUEST_DELAY_SECONDS)

    raise SystemExit(f"Failed to fetch page: {url}")


class AboutSectionParser(HTMLParser):
    """從頁面 DOM 中提取 #section-coin-about 區塊的純文字。"""

    def __init__(self) -> None:
        super().__init__()
        self.section_depth = 0
        self.skip_depth = 0
        self.current_block_parts: list[str] = []
        self.text_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip_depth > 0:
            self.skip_depth += 1
            return

        attrs_dict = dict(attrs)
        if self.section_depth == 0:
            if attrs_dict.get("id") == "section-coin-about":
                self.section_depth = 1
            return

        self.section_depth += 1
        if tag in SKIP_TAGS:
            self.skip_depth = 1
            return
        if tag in BLOCK_TAGS:
            self.flush_current_block()

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth > 0:
            self.skip_depth -= 1
            if self.section_depth > 0:
                self.section_depth -= 1
                if self.section_depth == 0:
                    self.flush_current_block()
            return

        if self.section_depth == 0:
            return

        if tag in BLOCK_TAGS:
            self.flush_current_block()
        self.section_depth -= 1
        if self.section_depth == 0:
            self.flush_current_block()

    def handle_data(self, data: str) -> None:
        if self.section_depth > 0 and self.skip_depth == 0:
            self.current_block_parts.append(data)

    def flush_current_block(self) -> None:
        text = normalize_text(" ".join(self.current_block_parts))
        self.current_block_parts = []
        if text:
            self.text_blocks.append(text)


def extract_about_text(html: str) -> str:
    """僅從頁面 DOM 提取 #section-coin-about 的整段純文字。"""
    parser = AboutSectionParser()
    parser.feed(html)
    parser.flush_current_block()
    return "  ".join(parser.text_blocks)


def diagnose_missing_about_text(html: str) -> str:
    """輸出 about 提取失敗的簡單診斷。"""
    if 'id="section-coin-about"' not in html:
        return "section-coin-about not found in fetched HTML"
    return "section-coin-about exists but no visible text was extracted"


def validate_input_csv() -> None:
    """檢查輸入 CSV 是否存在且欄位完整。"""
    if not INPUT_PATH.is_file():
        raise SystemExit(f"Input CSV does not exist: {INPUT_PATH}")

    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        required = {"name", "symbol", "slug"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_columns = ", ".join(sorted(missing))
            raise SystemExit(f"Missing required columns in input CSV: {missing_columns}")


def iter_input_rows():
    """逐行讀取輸入 token。"""
    with INPUT_PATH.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            yield row


def append_output(token_name: str, symbol: str, slug: str, about_text: str) -> None:
    """將單個 token 的 about 文字聚合為單行輸出。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0
    with OUTPUT_PATH.open("a", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(
            {
                "token_name": token_name,
                "symbol": symbol,
                "slug": slug,
                "about_text": about_text,
            }
        )


def write_debug_html(slug: str, html: str) -> Path:
    """將當次 response 的完整 HTML 寫入調試文件。"""
    DEBUG_HTML_DIR.mkdir(parents=True, exist_ok=True)
    safe_slug = re.sub(r"[^a-zA-Z0-9._-]+", "_", slug or "unknown").strip("_") or "unknown"
    output_path = DEBUG_HTML_DIR / f"{safe_slug}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path


def main() -> None:
    """主流程：逐行讀取 token 清單，抓頁面並提取 About 文字。"""
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()
    DEBUG_HTML_DIR.mkdir(parents=True, exist_ok=True)

    validate_input_csv()
    processed = 0
    for index, row in enumerate(iter_input_rows(), start=1):
        token_name = str(row.get("name") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        slug = str(row.get("slug") or "").strip()
        if not slug:
            append_output(token_name, symbol, "", "")
            continue

        url = URL_TEMPLATE.format(slug=slug)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{now}] [token {index}] fetch about text: {token_name or '-'} ({symbol or '-'}) {url}",
            flush=True,
        )
        html = fetch_html(url)
        about_text = extract_about_text(html)
        append_output(token_name, symbol, slug, about_text)
        processed += 1
        if not about_text:
            debug_path = write_debug_html(slug, html)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(
                f"[{now}] [token {index}] missing about text; saved response html to {debug_path}",
                flush=True,
            )
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(
            f"[{now}] [token {index}] extracted about_text length={len(about_text)} for slug={slug}",
            flush=True,
        )
        if not about_text:
            reason = diagnose_missing_about_text(html)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now}] [token {index}] diagnosis: {reason}", flush=True)

    print(f"Finished {processed} tokens. Output: {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Interrupted by user")
