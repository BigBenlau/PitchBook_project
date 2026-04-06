from __future__ import annotations

"""
整體用途：
1. 讀取第一步生成的 company_new.csv 與 investor_new.csv。
2. 在指定欄位中搜尋固定關鍵詞。
3. 輸出所有命中的 company 與 investor 結果表。

本腳本只負責「關鍵詞篩選」，不再重新掃描 relation 表。
"""

import argparse
import csv
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR / "output"
KEYWORDS = ["crypto", "blockchain", "web3"]

COMPANY_SEARCH_COLUMNS = [
    "Verticals",
    "Description",
    "Keywords",
    "Relation_Verticals",
    "Relation_SimilarVerticals",
    "Relation_SimilarDescriptions",
    "Relation_CompetitorVerticals",
    "Relation_CompetitorDescriptions",
]

INVESTOR_SEARCH_COLUMNS = [
    "PreferredVerticals",
    "Description",
]


def parse_args() -> argparse.Namespace:
    """解析命令列參數，決定要從哪個輸出目錄讀取 _new.csv。"""
    parser = argparse.ArgumentParser(
        description=(
            "Filter company_new.csv and investor_new.csv using constant crypto "
            "keywords and write matched result CSV files."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory containing company_new.csv and investor_new.csv.",
    )
    return parser.parse_args()


def normalize_keywords(keywords: Iterable[str]) -> list[str]:
    """清理並標準化關鍵詞，去空白、轉小寫、去重。"""
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        value = keyword.strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def ensure_csv_columns(path: Path, required_columns: Iterable[str]) -> list[str]:
    """檢查輸入 CSV 是否存在必要欄位，並回傳 header。"""
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.reader(infile)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise SystemExit(f"CSV file is empty: {path}") from exc

    missing = [column for column in required_columns if column not in header]
    if missing:
        raise SystemExit(f"Missing columns in {path}: {', '.join(missing)}")
    return header


def find_matches(value: str, keywords: list[str]) -> list[str]:
    """對單一欄位值做忽略大小寫的子字串匹配。"""
    lowered = value.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def write_filtered_output(
    input_path: Path,
    output_path: Path,
    search_columns: list[str],
    keywords: list[str],
) -> None:
    """
    讀取 _new.csv，對指定欄位做關鍵詞搜尋，並輸出命中的完整列。

    額外附加：
    - MatchedKeywords
    - MatchedColumns
    """
    header = ensure_csv_columns(input_path, search_columns)
    fieldnames = header + ["MatchedKeywords", "MatchedColumns"]
    row_count = 0

    print(
        f"Searching keywords in {input_path.name} columns: "
        f"{', '.join(search_columns)}",
        flush=True,
    )

    with input_path.open("r", encoding="utf-8-sig", newline="") as infile, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            matched_keywords: list[str] = []
            matched_columns: list[str] = []
            seen_keywords: set[str] = set()
            seen_columns: set[str] = set()

            for column in search_columns:
                value = (row.get(column) or "").strip()
                if not value:
                    continue
                hits = find_matches(value, keywords)
                if not hits:
                    continue
                if column not in seen_columns:
                    matched_columns.append(column)
                    seen_columns.add(column)
                for hit in hits:
                    if hit not in seen_keywords:
                        matched_keywords.append(hit)
                        seen_keywords.add(hit)

            if not matched_keywords:
                continue

            output_row = dict(row)
            output_row["MatchedKeywords"] = "|".join(matched_keywords)
            output_row["MatchedColumns"] = "|".join(matched_columns)
            writer.writerow(output_row)
            row_count += 1

    print(f"Wrote {row_count} matched rows to {output_path}", flush=True)


def main() -> None:
    """主流程：檢查輸入、執行 company/investor 篩選、輸出結果表。"""

    # Section 1: 解析參數與關鍵詞
    args = parse_args()
    output_dir = args.output_dir.resolve()
    keywords = normalize_keywords(KEYWORDS)

    # Section 2: 檢查輸入目錄與必要檔案
    if not output_dir.is_dir():
        raise SystemExit(f"Output directory does not exist: {output_dir}")
    if not keywords:
        raise SystemExit("KEYWORDS must contain at least one non-empty keyword.")

    company_new_path = output_dir / "company_new.csv"
    investor_new_path = output_dir / "investor_new.csv"
    crypto_company_path = output_dir / "crypto_company.csv"
    crypto_investor_path = output_dir / "crypto_investor.csv"

    for path in [company_new_path, investor_new_path]:
        if not path.is_file():
            raise SystemExit(f"Required merged CSV file does not exist: {path}")

    # Section 3: 執行 company 與 investor 關鍵詞篩選
    print(f"Using keywords: {', '.join(keywords)}", flush=True)
    write_filtered_output(company_new_path, crypto_company_path, COMPANY_SEARCH_COLUMNS, keywords)
    write_filtered_output(
        investor_new_path, crypto_investor_path, INVESTOR_SEARCH_COLUMNS, keywords
    )

    # Section 4: 輸出完成
    print(f"Filtered outputs written under {output_dir}", flush=True)


if __name__ == "__main__":
    main()
