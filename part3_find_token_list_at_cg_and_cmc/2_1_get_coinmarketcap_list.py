from __future__ import annotations

"""
整體用途：
1. 分頁抓取 CoinMarketCap listing API。
2. 每頁抓取 1000 個 token，從 start=1 開始。
3. 當返回 0 個 token 時停止。
4. 將結果寫入 CSV，欄位為 no, cmc_rank, name, symbol, slug, tags, platform_symbol。
"""

import csv
import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "coinmarketcap_list.csv"
BASE_URL = "https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing"
PAGE_SIZE = 1000
START_PAGE_INDEX = 1
REQUEST_DELAY_SECONDS = 0.5
RETRY_LIMIT = 20
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
OUTPUT_FIELDNAMES = [
    "no",
    "cmc_rank",
    "name",
    "symbol",
    "slug",
    "tags",
    "platform_symbol",
]
EXCLUDED_NAMES = {"CoinMarketCap 20 Index DTF"}


def build_request(start: int) -> Request:
    """建立 CoinMarketCap listing API 請求。"""
    query = urlencode(
        {
            "start": start,
            "limit": PAGE_SIZE,
            "sortBy": "rank",
            "sortType": "desc",
            "cryptoType": "all",
            "tagType": "all",
            "audited": "false",
        }
    )
    return Request(
        f"{BASE_URL}?{query}",
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        },
    )


def fetch_json(start: int) -> dict[str, Any]:
    """抓取單頁 JSON，失敗時重試。"""
    request = build_request(start)
    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            with urlopen(request, timeout=30) as response:
                status = getattr(response, "status", None)
                body = response.read().decode("utf-8", errors="replace")
                if status != 200:
                    print(
                        f"[start {start}] attempt {attempt}/{RETRY_LIMIT} non-200 status: {status}",
                        flush=True,
                    )
                    if attempt == RETRY_LIMIT:
                        raise SystemExit(
                            f"Failed to fetch start={start} after {RETRY_LIMIT} attempts: "
                            f"status={status} {request.full_url}"
                        )
                    continue
                try:
                    return json.loads(body)
                except json.JSONDecodeError as exc:
                    raise SystemExit(f"Invalid JSON returned for start={start}") from exc
        except HTTPError as exc:
            print(
                f"[start {start}] attempt {attempt}/{RETRY_LIMIT} HTTPError: {exc.code} {request.full_url}",
                flush=True,
            )
            if attempt == RETRY_LIMIT:
                raise SystemExit(
                    f"Failed to fetch start={start} after {RETRY_LIMIT} attempts: "
                    f"HTTPError {exc.code} {request.full_url}"
                ) from exc
        except URLError as exc:
            print(
                f"[start {start}] attempt {attempt}/{RETRY_LIMIT} URLError: {request.full_url} ({exc})",
                flush=True,
            )
            if attempt == RETRY_LIMIT:
                raise SystemExit(
                    f"Failed to fetch start={start} after {RETRY_LIMIT} attempts: "
                    f"URLError {request.full_url} ({exc})"
                ) from exc
        finally:
            time.sleep(REQUEST_DELAY_SECONDS)

    raise SystemExit(f"Failed to fetch start={start}: {request.full_url}")


def extract_tokens(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """從 API 響應中提取 token 列表。"""
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("cryptoCurrencyList")
    if not isinstance(items, list):
        return []
    return items


def normalize_tags(value: Any) -> str:
    """將 tags 統一轉成 JSON list 字串。"""
    if not isinstance(value, list):
        return "[]"
    tags = [str(item).strip() for item in value if str(item).strip()]
    return json.dumps(tags, ensure_ascii=False)


def normalize_platform_symbol(value: Any) -> str:
    """提取 platform.symbol。"""
    if not isinstance(value, dict):
        return ""
    return str(value.get("symbol") or "").strip()


def append_output(rows: list[dict[str, str]]) -> None:
    """逐頁追加寫入輸出 CSV。"""
    if not rows:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    file_exists = OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0
    with OUTPUT_PATH.open("a", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=OUTPUT_FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    """主流程：從 start=1 開始抓取，直到返回 0 個 token。"""
    if OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()

    global_index = 1
    start = START_PAGE_INDEX
    page_number = 1
    total_rows = 0

    while True:
        payload = fetch_json(start)
        items = extract_tokens(payload)
        if not items:
            print(f"Stopped at start={start}: found 0 tokens", flush=True)
            break

        page_rows: list[dict[str, str]] = []
        for item in items:
            name = str(item.get("name") or "").strip()
            if name in EXCLUDED_NAMES:
                continue

            page_rows.append(
                {
                    "no": str(global_index),
                    "cmc_rank": str(item.get("cmcRank") or ""),
                    "name": name,
                    "symbol": str(item.get("symbol") or "").strip(),
                    "slug": str(item.get("slug") or "").strip(),
                    "tags": normalize_tags(item.get("tags")),
                    "platform_symbol": normalize_platform_symbol(item.get("platform")),
                }
            )
            global_index += 1

        append_output(page_rows)
        total_rows += len(page_rows)
        print(
            f"[page {page_number}] start={start} parsed {len(page_rows)} tokens, total={total_rows}",
            flush=True,
        )

        page_rows.clear()
        items.clear()
        start += PAGE_SIZE
        page_number += 1

    print(f"Wrote {total_rows} rows to {OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
