from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = SCRIPT_DIR / "crypto_blockchain_keyword_hits.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "crypto_keyword_hit_rankings"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize repeated values from crypto_blockchain_keyword_hits.csv "
            "and output rankings by file, by column, and by (file, column)."
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Input hit CSV. Defaults to ./crypto_blockchain_keyword_hits.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for output ranking CSVs.",
    )
    return parser.parse_args()


def write_counter_csv(
    path: Path,
    header: list[str],
    rows: list[tuple[str, ...]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(header)
        writer.writerows(rows)


def build_rankings(
    input_path: Path,
) -> tuple[list[tuple[str, ...]], list[tuple[str, ...]], list[tuple[str, ...]]]:
    by_file: Counter[str] = Counter()
    by_column: Counter[str] = Counter()
    by_file_column: Counter[tuple[str, str]] = Counter()

    with input_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        required_columns = {"file", "column"}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise SystemExit(
                "Input CSV must contain at least these columns: file, column"
            )

        for row in reader:
            file_name = (row.get("file") or "").strip()
            column_name = (row.get("column") or "").strip()
            if not file_name or not column_name:
                continue

            by_file[file_name] += 1
            by_column[column_name] += 1
            by_file_column[(file_name, column_name)] += 1

    file_rows = [
        (file_name, str(count))
        for file_name, count in sorted(
            by_file.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    column_rows = [
        (column_name, str(count))
        for column_name, count in sorted(
            by_column.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    file_column_rows = [
        (file_name, column_name, str(count))
        for (file_name, column_name), count in sorted(
            by_file_column.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1]),
        )
    ]

    return file_rows, column_rows, file_column_rows


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()

    if not input_path.is_file():
        raise SystemExit(f"Input file does not exist: {input_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    file_rows, column_rows, file_column_rows = build_rankings(input_path=input_path)

    file_output = output_dir / "ranking_by_file.csv"
    column_output = output_dir / "ranking_by_column.csv"
    file_column_output = output_dir / "ranking_by_file_column.csv"

    write_counter_csv(
        file_output,
        ["file", "repeat_count"],
        file_rows,
    )
    write_counter_csv(
        column_output,
        ["column", "repeat_count"],
        column_rows,
    )
    write_counter_csv(
        file_column_output,
        ["file", "column", "repeat_count"],
        file_column_rows,
    )

    print(f"Wrote {len(file_rows)} rows to {file_output}")
    print(f"Wrote {len(column_rows)} rows to {column_output}")
    print(f"Wrote {len(file_column_rows)} rows to {file_column_output}")


if __name__ == "__main__":
    main()
