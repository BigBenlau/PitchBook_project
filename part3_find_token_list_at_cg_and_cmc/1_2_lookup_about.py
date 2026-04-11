from __future__ import annotations

"""
整體用途：
1. 讀取 output/coingecko_all_crypto_list.csv 中的 token 清單。
2. 逐行訪問 https://www.coingecko.com{token_href}。
3. 提取頁面中 class 包含 coin-page-editorial-content 的區塊文字。
4. 將純文字按段落寫入輸出 CSV，忽略所有 HTML 標記。
"""

import csv
import json
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
DEFAULT_INPUT_CSV = OUTPUT_DIR / "coingecko_all_crypto_list.csv"
DEFAULT_OUTPUT_CSV = OUTPUT_DIR / "coingecko_about.csv"
BASE_URL = "https://www.coingecko.com"
REQUEST_DELAY_SECONDS = 0.5
RETRY_LIMIT = 100
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
OUTPUT_FIELDNAMES = [
    "token_name",
    "token_symbol",
    "token_href",
    "status",
    "error",
    "categories",
    "websites",
    "about_text",
]
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "li"}


def normalize_whitespace(value: str) -> str:
    """清理多餘空白與 HTML entity。"""
    text = unescape(value or "")
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


class CoinGeckoAboutParser(HTMLParser):
    """提取 coin-page-editorial-content 區塊中的純文字段落。"""

    def __init__(self) -> None:
        super().__init__()
        self.container_depth = 0
        self.current_block_tag = ""
        self.current_text_parts: list[str] = []
        self.paragraphs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if key}
        classes = (attr_map.get("class") or "").split()

        if "coin-page-editorial-content" in classes:
            self.container_depth += 1
            return

        if self.container_depth <= 0:
            return

        if tag == "div":
            self.container_depth += 1
            return

        if tag in BLOCK_TAGS:
            self.flush_current_block()
            self.current_block_tag = tag
            self.current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if self.container_depth <= 0:
            return

        if tag in BLOCK_TAGS and self.current_block_tag == tag:
            self.flush_current_block()
            self.current_block_tag = ""
            self.current_text_parts = []
            return

        if tag == "div":
            self.flush_current_block()
            self.container_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.container_depth > 0:
            self.current_text_parts.append(data)

    def flush_current_block(self) -> None:
        text = normalize_whitespace(" ".join(self.current_text_parts))
        if text:
            self.paragraphs.append(text)
        self.current_text_parts = []


class CoinGeckoCategoriesParser(HTMLParser):
    """只提取左側標籤為 Categories 的 info row 中的分類文字。"""

    def __init__(self) -> None:
        super().__init__()
        self.div_depth = 0
        self.current_row_depth: int | None = None
        self.current_row_is_categories = False
        self.current_label_depth: int | None = None
        self.current_label_parts: list[str] = []
        self.in_category_link = False
        self.current_text_parts: list[str] = []
        self.categories: list[str] = []
        self.seen: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if key}

        if tag == "div":
            self.div_depth += 1
            classes = set((attr_map.get("class") or "").split())

            if (
                self.current_row_depth is None
                and {"tw-flex", "tw-justify-between", "tw-py-3"}.issubset(classes)
            ):
                self.current_row_depth = self.div_depth
                self.current_row_is_categories = False
                self.current_label_depth = None
                self.current_label_parts = []
                return

            if (
                self.current_row_depth is not None
                and self.current_label_depth is None
                and self.div_depth == self.current_row_depth + 1
                and "tw-text-left" in classes
            ):
                self.current_label_depth = self.div_depth
                self.current_label_parts = []
            return

        if tag != "a" or not self.current_row_is_categories:
            return

        href = (attr_map.get("href") or "").strip()
        if not href.startswith("/en/categories/"):
            return

        self.in_category_link = True
        self.current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.in_category_link:
            text = normalize_whitespace(" ".join(self.current_text_parts))
            self.in_category_link = False
            self.current_text_parts = []
            if not text or text in self.seen:
                return

            self.seen.add(text)
            self.categories.append(text)
            return

        if tag != "div" or self.div_depth <= 0:
            return

        if self.current_label_depth is not None and self.div_depth == self.current_label_depth:
            label = normalize_whitespace(" ".join(self.current_label_parts))
            self.current_row_is_categories = label == "Categories"
            self.current_label_depth = None
            self.current_label_parts = []

        if self.current_row_depth is not None and self.div_depth == self.current_row_depth:
            self.current_row_depth = None
            self.current_row_is_categories = False
            self.current_label_depth = None
            self.current_label_parts = []
            self.in_category_link = False
            self.current_text_parts = []

        self.div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.current_label_depth is not None:
            self.current_label_parts.append(data)
        if self.in_category_link:
            self.current_text_parts.append(data)


class CoinGeckoWebsitesParser(HTMLParser):
    """只提取左側標籤為 Website 的 info row 中的網站鍵值。"""

    def __init__(self) -> None:
        super().__init__()
        self.div_depth = 0
        self.current_row_depth: int | None = None
        self.current_row_is_website = False
        self.current_label_depth: int | None = None
        self.current_label_parts: list[str] = []
        self.in_website_link = False
        self.current_href = ""
        self.current_text_parts: list[str] = []
        self.websites: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key.lower(): value for key, value in attrs if key}

        if tag == "div":
            self.div_depth += 1
            classes = set((attr_map.get("class") or "").split())

            if (
                self.current_row_depth is None
                and {"tw-flex", "tw-justify-between", "tw-py-3"}.issubset(classes)
            ):
                self.current_row_depth = self.div_depth
                self.current_row_is_website = False
                self.current_label_depth = None
                self.current_label_parts = []
                return

            if (
                self.current_row_depth is not None
                and self.current_label_depth is None
                and self.div_depth == self.current_row_depth + 1
                and "tw-text-left" in classes
            ):
                self.current_label_depth = self.div_depth
                self.current_label_parts = []
            return

        if tag != "a" or not self.current_row_is_website:
            return

        href = (attr_map.get("href") or "").strip()
        if not href:
            return

        self.in_website_link = True
        self.current_href = href
        self.current_text_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.in_website_link:
            key = normalize_whitespace(" ".join(self.current_text_parts))
            href = self.current_href
            self.in_website_link = False
            self.current_href = ""
            self.current_text_parts = []
            if key and href and key not in self.websites:
                self.websites[key] = href
            return

        if tag != "div" or self.div_depth <= 0:
            return

        if self.current_label_depth is not None and self.div_depth == self.current_label_depth:
            label = normalize_whitespace(" ".join(self.current_label_parts))
            self.current_row_is_website = label == "Website"
            self.current_label_depth = None
            self.current_label_parts = []

        if self.current_row_depth is not None and self.div_depth == self.current_row_depth:
            self.current_row_depth = None
            self.current_row_is_website = False
            self.current_label_depth = None
            self.current_label_parts = []
            self.in_website_link = False
            self.current_href = ""
            self.current_text_parts = []

        self.div_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.current_label_depth is not None:
            self.current_label_parts.append(data)
        if self.in_website_link:
            self.current_text_parts.append(data)


def fetch_page_html(url: str) -> str:
    """抓取單個 coin 頁，失敗時重試 100 次。"""
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


def extract_about_text(html: str) -> str:
    """從頁面 HTML 提取 about 段落文字。"""
    parser = CoinGeckoAboutParser()
    parser.feed(html)
    parser.flush_current_block()
    return "  ".join(parser.paragraphs)


def extract_categories(html: str) -> str:
    """從頁面 HTML 提取 categories，並輸出為 list 字串。"""
    parser = CoinGeckoCategoriesParser()
    parser.feed(html)
    return json.dumps(parser.categories, ensure_ascii=False)


def extract_websites(html: str) -> str:
    """從頁面 HTML 提取 Website 區塊中的鍵值對。"""
    parser = CoinGeckoWebsitesParser()
    parser.feed(html)
    return json.dumps(parser.websites, ensure_ascii=False)


def validate_input_csv(input_csv: Path) -> None:
    """檢查輸入 CSV 是否存在且欄位完整。"""
    if not input_csv.is_file():
        raise SystemExit(f"Input CSV does not exist: {input_csv}")

    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        required = {"page", "token_name", "token_symbol", "token_href"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            missing_columns = ", ".join(sorted(missing))
            raise SystemExit(f"Missing required columns in input CSV: {missing_columns}")


def iter_input_rows(input_csv: Path):
    """以流式方式逐行讀取輸入 CSV。"""
    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            yield row


def append_output(row: dict[str, str]) -> None:
    """逐筆追加寫入輸出 CSV。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = DEFAULT_OUTPUT_CSV.exists() and DEFAULT_OUTPUT_CSV.stat().st_size > 0
    with DEFAULT_OUTPUT_CSV.open("a", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main() -> None:
    """主流程：逐行讀取 token，抓取 about 文字並逐筆寫出。"""
    input_csv = DEFAULT_INPUT_CSV
    output_csv = DEFAULT_OUTPUT_CSV

    if output_csv.exists():
        output_csv.unlink()

    validate_input_csv(input_csv)
    for index, row in enumerate(iter_input_rows(input_csv), start=1):
        token_href = (row.get("token_href") or "").strip()
        source_url = f"{BASE_URL}{token_href}"
        print(
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [row {index}] fetch about: {row.get('token_name', '').strip() or '-'} {source_url}",
            flush=True,
        )

        if not token_href:
            append_output(
                {
                    "token_name": (row.get("token_name") or "").strip(),
                    "token_symbol": (row.get("token_symbol") or "").strip(),
                    "token_href": "",
                    "status": "error",
                    "error": "Missing token_href",
                    "categories": "[]",
                    "websites": "{}",
                    "about_text": "",
                }
            )
            continue

        try:
            html = fetch_page_html(source_url)
            categories = extract_categories(html)
            websites = extract_websites(html)
            about_text = extract_about_text(html)
            append_output(
                {
                    "token_name": (row.get("token_name") or "").strip(),
                    "token_symbol": (row.get("token_symbol") or "").strip(),
                    "token_href": token_href,
                    "status": "ok" if about_text else "empty",
                    "error": "",
                    "categories": categories,
                    "websites": websites,
                    "about_text": about_text,
                }
            )
            html = ""
            categories = ""
            websites = ""
            about_text = ""
        except SystemExit as exc:
            append_output(
                {
                    "token_name": (row.get("token_name") or "").strip(),
                    "token_symbol": (row.get("token_symbol") or "").strip(),
                    "token_href": token_href,
                    "status": "error",
                    "error": str(exc),
                    "categories": "[]",
                    "websites": "{}",
                    "about_text": "",
                }
            )

    print(f"Finished. Output: {output_csv}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("Interrupted by user")
