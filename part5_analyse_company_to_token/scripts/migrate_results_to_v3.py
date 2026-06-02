#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from result_schema import (
    LEGACY_RESULT_CSV_COLUMNS_NO_RULES,
    LEGACY_RESULT_CSV_COLUMNS_WITH_RULES,
    RESULT_CSV_COLUMNS,
    migrate_legacy_result_row,
    parse_json_list,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
DEFAULT_FINAL_DIR = PART5_DIR / "agent_runs" / "crypto_company"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate part5 result CSVs from split token columns to v3 token result object lists.",
    )
    parser.add_argument(
        "csv_paths",
        nargs="*",
        type=Path,
        default=[
            DEFAULT_FINAL_DIR / "results.csv",
            DEFAULT_FINAL_DIR / "needs_manual_review.csv",
        ],
    )
    return parser.parse_args()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=RESULT_CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{column: row.get(column, "") for column in RESULT_CSV_COLUMNS} for row in rows])


def legacy_projection(row: dict[str, Any]) -> list[dict[str, str]]:
    symbols = [str(item) for item in parse_json_list(row.get("token_ticker", ""))]
    names = [str(item) for item in parse_json_list(row.get("token_name", ""))]
    urls = [str(item) for item in parse_json_list(row.get("token_url", ""))]
    return [
        {
            "token_symbol": symbol,
            "token_name": names[index] if index < len(names) else "",
            "token_url": urls[index] if index < len(urls) else "",
        }
        for index, symbol in enumerate(symbols)
    ]


def v3_projection(row: dict[str, Any]) -> list[dict[str, str]]:
    projection: list[dict[str, str]] = []
    for item in parse_json_list(row.get("token_results", "")):
        if not isinstance(item, dict):
            continue
        projection.append(
            {
                "token_symbol": str(item.get("token_symbol", "") or ""),
                "token_name": str(item.get("token_name", "") or ""),
                "token_url": str(item.get("token_url", "") or ""),
            }
        )
    return projection


def migrate_file(path: Path) -> tuple[int, int]:
    header, rows = read_csv(path)
    if header == RESULT_CSV_COLUMNS:
        mismatches = [
            row.get("task_index", "")
            for row in rows
            if not isinstance(parse_json_list(row.get("token_results", "")), list)
        ]
        if mismatches:
            raise SystemExit(f"{path}: invalid token_results JSON for task_index {mismatches[:10]}")
        write_csv(path, rows)
        return len(rows), 0

    if tuple(header) not in {
        tuple(LEGACY_RESULT_CSV_COLUMNS_WITH_RULES),
        tuple(LEGACY_RESULT_CSV_COLUMNS_NO_RULES),
    }:
        raise SystemExit(f"{path}: unsupported header")

    before = {row.get("task_index", ""): legacy_projection(row) for row in rows}
    migrated = [migrate_legacy_result_row(row) for row in rows]
    write_csv(path, migrated)

    _, after_rows = read_csv(path)
    after = {row.get("task_index", ""): v3_projection(row) for row in after_rows}
    mismatches = [
        task_index
        for task_index, before_projection in before.items()
        if before_projection != after.get(task_index)
    ]
    if mismatches:
        sample = mismatches[:10]
        raise SystemExit(
            f"{path}: original token projection mismatch after migration for task_index {sample}"
        )
    return len(rows), len(mismatches)


def main() -> None:
    args = parse_args()
    for path in args.csv_paths:
        if not path.exists():
            print(f"{path}: missing, skipped")
            continue
        row_count, mismatch_count = migrate_file(path)
        print(f"{path}: rows={row_count}, original_token_mismatches={mismatch_count}")


if __name__ == "__main__":
    main()
