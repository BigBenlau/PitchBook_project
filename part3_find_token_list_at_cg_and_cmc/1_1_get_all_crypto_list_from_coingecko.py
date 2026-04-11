from __future__ import annotations

"""
整體用途：
1. 逐頁抓取 CoinGecko 的 all cryptocurrencies 頁面。
2. 從每頁中提取 token 全名、簡稱與 coin 詳情頁 href。
3. 將結果寫入 CSV，供後續 token 名稱匹配使用。

頁面範圍固定為 1-400。
"""

import csv
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "coingecko_all_crypto_list.csv"
BASE_URL = "https://www.coingecko.com/en/all-cryptocurrencies/show_more_coins?page={page}"
START_PAGE = 1
END_PAGE = 400
REQUEST_DELAY_SECONDS = 0.5
RETRY_LIMIT = 10
RETRY_DELAY_SECONDS = 2.0
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
NAME_SYMBOL_TEXT_RE = re.compile(r"^\s*(.+?)\s+([A-Z0-9.\-]+)\s*$")


class CoinGeckoNameParser(HTMLParser):
    """從頁面 HTML 中提取 coin 詳情頁的錨點文字。"""

    def __init__(self) -> None:
        super().__init__()
        self.in_coin_link = False
        self.current_href = ""
        self.current_text_parts: list[str] = []
        self.items: list[tuple[str, str, str]] = []
        self.seen: set[tuple[str, str, str]] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        attrs_dict = dict(attrs)
        href = attrs_dict.get("href") or ""
        if "/en/coins/" not in href:
            return
        self.in_coin_link = True
        self.current_href = href
        self.current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_coin_link:
            self.current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "a" or not self.in_coin_link:
            return

        raw_text = " ".join(part.strip() for part in self.current_text_parts if part.strip())
        raw_text = re.sub(r"\s+", " ", raw_text).strip()
        href = self.current_href.strip()
        self.in_coin_link = False
        self.current_href = ""

        if not raw_text or not href:
            return

        parsed = parse_name_and_symbol(raw_text)
        if not parsed:
            return

        item = (parsed[0], parsed[1], href)
        if item in self.seen:
            return

        self.seen.add(item)
        self.items.append(item)


def parse_name_and_symbol(text: str) -> tuple[str, str] | None:
    """將類似 `Bitcoin BTC` 的文字拆成名稱與簡稱。"""
    match = NAME_SYMBOL_TEXT_RE.match(text)
    if not match:
        return None

    token_name = match.group(1).strip()
    token_symbol = match.group(2).strip()
    if not token_name or not token_symbol:
        return None
    return token_name, token_symbol


def fetch_page_html(page: int) -> str:
    """抓取指定頁碼的 HTML 內容，非 200 或異常時自動重試。"""
    url = BASE_URL.format(page=page)
    for attempt in range(1, RETRY_LIMIT + 1):
        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-US,en;q=0.9",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                status = getattr(response, "status", None)
                if status != 200:
                    print(
                        f"[page {page}] attempt {attempt}/{RETRY_LIMIT} "
                        f"non-200 status: {status}",
                        flush=True,
                    )
                    if attempt == RETRY_LIMIT:
                        raise SystemExit(
                            f"Failed to fetch page {page} after {RETRY_LIMIT} attempts: "
                            f"status={status} {url}"
                        )
                    time.sleep(RETRY_DELAY_SECONDS)
                    continue

                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            print(
                f"[page {page}] attempt {attempt}/{RETRY_LIMIT} "
                f"HTTPError: {exc.code} {url}",
                flush=True,
            )
            if attempt == RETRY_LIMIT:
                raise SystemExit(
                    f"Failed to fetch page {page} after {RETRY_LIMIT} attempts: "
                    f"HTTPError {exc.code} {url}"
                ) from exc
            time.sleep(RETRY_DELAY_SECONDS)
        except URLError as exc:
            print(
                f"[page {page}] attempt {attempt}/{RETRY_LIMIT} "
                f"URLError: {url} ({exc})",
                flush=True,
            )
            if attempt == RETRY_LIMIT:
                raise SystemExit(
                    f"Failed to fetch page {page} after {RETRY_LIMIT} attempts: "
                    f"URLError {url} ({exc})"
                ) from exc
            time.sleep(RETRY_DELAY_SECONDS)

    raise SystemExit(f"Failed to fetch page {page}: {url}")


def extract_tokens_from_html(html: str) -> list[tuple[str, str, str]]:
    """從單頁 HTML 中提取 token 名稱、簡稱與 coin 頁 href。"""
    parser = CoinGeckoNameParser()
    parser.feed(html)
    return parser.items


def append_output(rows: list[dict[str, str]]) -> None:
    """將單頁抓取結果追加寫入 CSV。"""
    if not rows:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0
    with OUTPUT_PATH.open("a", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=["page", "token_name", "token_symbol", "token_href"],
        )
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """主流程：抓取 1-400 頁並逐頁輸出 CSV。"""

    # Section 1: 初始化輸出檔
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    # Section 2: 逐頁抓取、解析並立即落盤
    total_rows = 0
    end_page = END_PAGE
    for page in range(START_PAGE, END_PAGE + 1):
        html = fetch_page_html(page)
        items = extract_tokens_from_html(html)
        if not items:
            end_page = page
            print(f"Stopped at page {page}: parsed 0 tokens", flush=True)
            break

        print(f"[{page}/{END_PAGE}] parsed {len(items)} tokens", flush=True)

        page_rows: list[dict[str, str]] = []
        for token_name, token_symbol, token_href in items:
            page_rows.append(
                {
                    "page": str(page),
                    "token_name": token_name,
                    "token_symbol": token_symbol,
                    "token_href": token_href,
                }
            )

        append_output(page_rows)
        total_rows += len(page_rows)
        page_rows.clear()
        items.clear()
        html = ""

        time.sleep(REQUEST_DELAY_SECONDS)

    # Section 3: 輸出結果摘要
    print(f"Wrote {total_rows} rows to {OUTPUT_PATH}", flush=True)
    print(f"End page: {end_page}", flush=True)


if __name__ == "__main__":
    main()
