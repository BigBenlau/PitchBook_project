#!/usr/bin/env python3
"""
Split the full Part4 token input CSV into deterministic batch CSV files.

Example:
python3 part4_analyse_token_to_company/0_prepare_input_batches.py \
  --input-csv part4_analyse_token_to_company/tmp/full/coingecko_about_with_cmc_about.csv \
  --batch-size 500
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_DIR = SCRIPT_DIR / "input"
DEFAULT_INPUT_CSV = SCRIPT_DIR / "tmp" / "full" / "coingecko_about_with_cmc_about.csv"
DEFAULT_BATCH_DIR = INPUT_DIR / "batches"
DEFAULT_MANIFEST = INPUT_DIR / "batch_manifest.csv"
DEFAULT_BATCH_SIZE = 500
MANIFEST_FIELDNAMES = [
    "batch_id",
    "batch_path",
    "row_count",
    "start_row",
    "end_row",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Split full token input into batch CSV files.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove existing batch_*.csv files before writing new batches.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")
    if not args.input_csv.is_file():
        raise SystemExit(f"Input CSV does not exist: {args.input_csv}")


def remove_existing_batches(batch_dir: Path) -> None:
    if not batch_dir.is_dir():
        return
    for path in batch_dir.glob("batch_*.csv"):
        path.unlink()


def write_manifest(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=MANIFEST_FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    input_csv = args.input_csv.resolve()
    batch_dir = args.batch_dir.resolve()
    manifest_path = args.manifest.resolve()
    validate_args(args)

    batch_dir.mkdir(parents=True, exist_ok=True)
    if args.overwrite:
        remove_existing_batches(batch_dir)

    manifest_rows: list[dict[str, str]] = []
    total_rows = 0
    batch_rows: list[dict[str, str]] = []
    batch_number = 0
    fieldnames: list[str] = []

    with input_csv.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        if not fieldnames:
            raise SystemExit(f"No header found in input CSV: {input_csv}")

        for row in reader:
            total_rows += 1
            batch_rows.append(row)
            if len(batch_rows) >= args.batch_size:
                batch_number += 1
                start_row = total_rows - len(batch_rows) + 1
                end_row = total_rows
                batch_path = batch_dir / f"batch_{batch_number:04d}.csv"
                with batch_path.open("w", encoding="utf-8", newline="") as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(batch_rows)
                manifest_rows.append(
                    {
                        "batch_id": f"batch_{batch_number:04d}",
                        "batch_path": str(batch_path),
                        "row_count": str(len(batch_rows)),
                        "start_row": str(start_row),
                        "end_row": str(end_row),
                        "status": "pending",
                    }
                )
                batch_rows = []

    if batch_rows:
        batch_number += 1
        start_row = total_rows - len(batch_rows) + 1
        end_row = total_rows
        batch_path = batch_dir / f"batch_{batch_number:04d}.csv"
        with batch_path.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(batch_rows)
        manifest_rows.append(
            {
                "batch_id": f"batch_{batch_number:04d}",
                "batch_path": str(batch_path),
                "row_count": str(len(batch_rows)),
                "start_row": str(start_row),
                "end_row": str(end_row),
                "status": "pending",
            }
        )

    write_manifest(manifest_path, manifest_rows)
    print(f"Wrote {len(manifest_rows)} batches for {total_rows} rows.", flush=True)
    print(f"Batch directory: {batch_dir}", flush=True)
    print(f"Manifest: {manifest_path}", flush=True)


if __name__ == "__main__":
    main()
