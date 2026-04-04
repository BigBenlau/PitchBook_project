from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DEFAULT_OUTPUT = SCRIPT_DIR / "crypto_blockchain_keyword_hits.csv"
DEFAULT_KEYWORDS = ("crypto", "blockchain")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scan all CSV files in data/ and output rows where any cell contains "
            "crypto/blockchain-related keywords."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directory containing CSV files. Defaults to ./data",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output CSV path. Defaults to ./crypto_blockchain_keyword_hits.csv",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=list(DEFAULT_KEYWORDS),
        help="Case-insensitive keywords to search for. Defaults to: crypto blockchain",
    )
    parser.add_argument(
        "--include-samples",
        action="store_true",
        help="Include files ending with _10.csv. By default they are skipped.",
    )
    return parser.parse_args()


def iter_csv_files(data_dir: Path, include_samples: bool) -> Iterable[Path]:
    for path in sorted(data_dir.glob("*.csv")):
        if not include_samples and path.name.endswith("_10.csv"):
            continue
        yield path


def normalize_keywords(keywords: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        value = keyword.strip().lower()
        if not value or value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return normalized


def matching_keywords(value: str, keywords: list[str]) -> list[str]:
    lowered = value.lower()
    return [keyword for keyword in keywords if keyword in lowered]


def first_id_value(row: dict[str, str]) -> tuple[str, str]:
    for column, value in row.items():
        if column.endswith("ID") and value.strip():
            return column, value.strip()
    return "", ""


def scan_file(path: Path, keywords: list[str], writer: csv.DictWriter) -> int:
    hit_count = 0
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        if reader.fieldnames is None:
            return 0

        for row_number, row in enumerate(reader, start=2):
            id_column, id_value = first_id_value(row)
            for column_name, raw_value in row.items():
                value = (raw_value or "").strip()
                if not value:
                    continue

                matched = matching_keywords(value, keywords)
                if not matched:
                    continue

                writer.writerow(
                    {
                        "file": path.name,
                        "row_number": row_number,
                        "id_column": id_column,
                        "id_value": id_value,
                        "column": column_name,
                        "matched_keywords": "|".join(matched),
                        "value": value,
                    }
                )
                hit_count += 1

    return hit_count


def main() -> None:
    args = parse_args()
    data_dir = args.data_dir.resolve()
    output_path = args.output.resolve()
    keywords = normalize_keywords(args.keywords)

    if not data_dir.is_dir():
        raise SystemExit(f"Data directory does not exist: {data_dir}")
    if not keywords:
        raise SystemExit("No valid keywords were provided.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    csv_files = list(iter_csv_files(data_dir, args.include_samples))
    total_files = len(csv_files)
    total_hits = 0
    scanned_files = 0
    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=[
                "file",
                "row_number",
                "id_column",
                "id_value",
                "column",
                "matched_keywords",
                "value",
            ],
        )
        writer.writeheader()

        for csv_file in csv_files:
            scanned_files += 1
            file_hits = scan_file(csv_file, keywords, writer)
            total_hits += file_hits
            print(
                f"[{scanned_files}/{total_files}] {csv_file.name}: "
                f"{file_hits} matches (total {total_hits})"
            )

    print(
        f"Scanned {scanned_files} files, found {total_hits} matches, "
        f"output written to {output_path}"
    )


if __name__ == "__main__":
    main()
