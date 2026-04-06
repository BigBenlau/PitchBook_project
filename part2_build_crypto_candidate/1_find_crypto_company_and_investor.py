from __future__ import annotations

"""
整體用途：
1. 讀取 Company 與 Investor 主表。
2. 將指定的 Company relation 表欄位聚合回 Company 主表。
3. 生成後續可直接做關鍵詞搜尋的 company_new.csv 與 investor_new.csv。

本腳本只負責「合併主表」，不負責關鍵詞篩選。
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = SCRIPT_DIR / "output"
DELIMITER = " | "

COMPANY_RELATION_SPECS = [
    {
        "path": DATA_DIR / "CompanyVerticalRelation.csv",
        "key": "CompanyID",
        "source": "Vertical",
        "target": "Relation_Verticals",
    },
    {
        "path": DATA_DIR / "CompanySimilarRelation.csv",
        "key": "CompanyID",
        "source": "SimilarVerticals",
        "target": "Relation_SimilarVerticals",
    },
    {
        "path": DATA_DIR / "CompanySimilarRelation.csv",
        "key": "CompanyID",
        "source": "SimilarDescription",
        "target": "Relation_SimilarDescriptions",
    },
    {
        "path": DATA_DIR / "CompanyCompetitorRelation.csv",
        "key": "CompanyID",
        "source": "CompetitorVerticals",
        "target": "Relation_CompetitorVerticals",
    },
    {
        "path": DATA_DIR / "CompanyCompetitorRelation.csv",
        "key": "CompanyID",
        "source": "CompetitorDescription",
        "target": "Relation_CompetitorDescriptions",
    },
]

def parse_args() -> argparse.Namespace:
    """解析命令列參數，決定資料來源目錄與輸出目錄。"""
    parser = argparse.ArgumentParser(
        description=(
            "Build merged company_new.csv and investor_new.csv from main tables "
            "and selected relation tables."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing source CSV files. Defaults to ./data",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directory for generated CSV files.",
    )
    return parser.parse_args()


def ensure_csv_columns(path: Path, required_columns: Iterable[str]) -> list[str]:
    """檢查 CSV 是否存在必要欄位，並回傳 header。"""
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


def collect_relation_values_by_file(
    specs: list[dict[str, str | Path]],
) -> dict[str, dict[str, list[str]]]:
    """
    針對同一個 relation 檔案一次讀取，並同時聚合多個來源欄位。

    回傳格式：
    {
        "target_column_name": {
            "entity_id": ["value1", "value2", ...]
        }
    }
    """
    if not specs:
        return {}

    path = Path(specs[0]["path"])
    key_column = str(specs[0]["key"])
    source_columns = [str(spec["source"]) for spec in specs]
    ensure_csv_columns(path, [key_column, *source_columns])

    values_by_target: dict[str, dict[str, list[str]]] = {
        str(spec["target"]): defaultdict(list) for spec in specs
    }
    seen_by_target: dict[str, dict[str, set[str]]] = {
        str(spec["target"]): defaultdict(set) for spec in specs
    }
    impacted_by_target: dict[str, set[str]] = {
        str(spec["target"]): set() for spec in specs
    }

    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            entity_id = (row.get(key_column) or "").strip()
            if not entity_id:
                continue

            for spec in specs:
                source_column = str(spec["source"])
                target_column = str(spec["target"])
                value = (row.get(source_column) or "").strip()
                if not value:
                    continue
                if value in seen_by_target[target_column][entity_id]:
                    continue
                seen_by_target[target_column][entity_id].add(value)
                values_by_target[target_column][entity_id].append(value)
                impacted_by_target[target_column].add(entity_id)

    for spec in specs:
        source_column = str(spec["source"])
        target_column = str(spec["target"])
        print(
            f"Aggregated {path.name}.{source_column} -> {target_column} "
            f"for {len(impacted_by_target[target_column])} entities",
            flush=True,
        )

    return values_by_target


def write_company_new(
    company_path: Path,
    output_path: Path,
    relation_specs: list[dict[str, str | Path]],
) -> None:
    """將指定 relation 欄位聚合回 Company 主表，生成 company_new.csv。"""
    print(f"Reading main table: {company_path.name}")
    company_header = ensure_csv_columns(company_path, ["CompanyID"])
    relation_values: dict[str, dict[str, list[str]]] = {}
    specs_by_path: dict[Path, list[dict[str, str | Path]]] = defaultdict(list)
    for spec in relation_specs:
        specs_by_path[Path(spec["path"])].append(spec)

    for specs_for_path in specs_by_path.values():
        relation_values.update(collect_relation_values_by_file(specs_for_path))
    new_columns = [str(spec["target"]) for spec in relation_specs]

    row_count = 0
    with company_path.open("r", encoding="utf-8-sig", newline="") as infile, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=company_header + new_columns)
        writer.writeheader()

        for row in reader:
            company_id = (row.get("CompanyID") or "").strip()
            for new_column in new_columns:
                row[new_column] = DELIMITER.join(relation_values[new_column].get(company_id, []))
            writer.writerow(row)
            row_count += 1

    print(f"Wrote {row_count} rows to {output_path}", flush=True)


def write_investor_new(investor_path: Path, output_path: Path) -> None:
    """直接複寫 Investor 主表為 investor_new.csv，作為第二步篩選輸入。"""
    print(f"Reading main table: {investor_path.name}", flush=True)
    investor_header = ensure_csv_columns(investor_path, ["InvestorID"])

    row_count = 0
    with investor_path.open("r", encoding="utf-8-sig", newline="") as infile, output_path.open(
        "w", encoding="utf-8", newline=""
    ) as outfile:
        reader = csv.DictReader(infile)
        writer = csv.DictWriter(outfile, fieldnames=investor_header)
        writer.writeheader()

        for row in reader:
            writer.writerow(row)
            row_count += 1

    print(f"Wrote {row_count} rows to {output_path}", flush=True)


def main() -> None:
    """主流程：校驗輸入、生成合併後的 company_new.csv 與 investor_new.csv。"""

    # Section 1: 解析參數與基本路徑
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()

    # Section 2: 檢查必要輸入檔是否存在
    if not data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist: {data_dir}")

    company_path = data_dir / "Company.csv"
    investor_path = data_dir / "Investor.csv"
    relation_paths = [Path(spec["path"]) for spec in COMPANY_RELATION_SPECS]
    required_paths = [company_path, investor_path, *relation_paths]
    for path in required_paths:
        if not path.is_file():
            raise SystemExit(f"Required CSV file does not exist: {path}")

    # Section 3: 準備輸出路徑
    output_dir.mkdir(parents=True, exist_ok=True)

    company_new_path = output_dir / "company_new.csv"
    investor_new_path = output_dir / "investor_new.csv"

    # Section 4: 生成合併後的主表
    write_company_new(company_path, company_new_path, COMPANY_RELATION_SPECS)
    write_investor_new(investor_path, investor_new_path)
    print(f"Merged outputs written under {output_dir}", flush=True)


if __name__ == "__main__":
    main()
