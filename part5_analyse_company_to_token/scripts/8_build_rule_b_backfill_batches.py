#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT_CSV = PART5_DIR / "agent_runs" / "crypto_company" / "results.csv"
DEFAULT_OUTPUT_DIR = PART5_DIR / "agent_task_batches" / "crypto_company_rule_b_backfill"
DEFAULT_BATCH_SIZE = 10

TASK_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "normalized_domain",
    "company_type",
    "crypto_project_likelihood",
    "project_search_required",
    "project_search_reason",
    "project_name",
    "project_url",
    "token_results",
    "token_decision_reason",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
    "include_rule_B",
    "rule_B_token_results",
    "rule_B_decision_reason",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Part5 Rule B-only backfill JSONL batches from final results.csv.")
    parser.add_argument("--input-csv", type=Path, default=DEFAULT_INPUT_CSV)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--include-completed", action="store_true", help="Include rows whose include_rule_B is already yes/no.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory.")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_jsonl(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            payload = {column: row.get(column, "") for column in TASK_COLUMNS}
            handle.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> None:
    args = parse_args()
    if args.batch_size <= 0:
        raise SystemExit("--batch-size must be positive")
    if args.output_dir.exists():
        if not args.force:
            raise SystemExit(f"Output directory already exists: {args.output_dir}")
        shutil.rmtree(args.output_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = read_rows(args.input_csv)
    selected = [
        row
        for row in rows
        if args.include_completed or (row.get("include_rule_B") or "").strip() in {"", "pending"}
    ]
    if not selected:
        raise SystemExit("No Rule B rows selected for backfill.")

    manifest_path = args.output_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8") as manifest_file:
        writer = csv.DictWriter(
            manifest_file,
            fieldnames=["batch_file", "row_count", "first_task_index", "last_task_index", "first_company", "last_company"],
        )
        writer.writeheader()
        for batch_index, start in enumerate(range(0, len(selected), args.batch_size), start=1):
            chunk = selected[start : start + args.batch_size]
            batch_file = args.output_dir / f"batch_{batch_index:04d}.jsonl"
            write_jsonl(batch_file, chunk)
            writer.writerow(
                {
                    "batch_file": batch_file.name,
                    "row_count": len(chunk),
                    "first_task_index": chunk[0].get("task_index", ""),
                    "last_task_index": chunk[-1].get("task_index", ""),
                    "first_company": chunk[0].get("company_name", ""),
                    "last_company": chunk[-1].get("company_name", ""),
                }
            )

    print(f"input_rows={len(rows)}")
    print(f"selected_rows={len(selected)}")
    print(f"batch_size={args.batch_size}")
    print(f"batch_count={(len(selected) + args.batch_size - 1) // args.batch_size}")
    print(f"output_dir={args.output_dir}")
    print(f"manifest={manifest_path}")


if __name__ == "__main__":
    main()
