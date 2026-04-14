#!/usr/bin/env python3
"""
Prepare founder/company extraction tasks for a batch-local evidence CSV.

Harness batch example:
python3 part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/3_extract_founder_companies.py \
  --input-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_evidence_sentences.csv \
  --tasks-jsonl part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/founder_company_tasks.jsonl \
  --batch-dir part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/codex_batches \
  --result-template part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/founder_company_extracted.csv \
  --batch-size 10
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_INPUT_CSV = PROJECT_DIR / "output" / "token_evidence_sentences.csv"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_TASKS_JSONL = DEFAULT_OUTPUT_DIR / "founder_company_tasks.jsonl"
DEFAULT_BATCH_DIR = DEFAULT_OUTPUT_DIR / "codex_batches"
DEFAULT_RESULT_TEMPLATE = DEFAULT_OUTPUT_DIR / "founder_company_extracted.csv"
DEFAULT_PROMPT_PATH = PROJECT_DIR / "4_founder_company_prompt.txt"
DEFAULT_BATCH_SIZE = 10
RESULT_FIELDNAMES = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "confidence",
    "evidence_spans",
    "notes",
    "status",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare founder/company extraction tasks for the current Codex chat. "
            "This script does not call the OpenAI API."
        )
    )
    parser.add_argument(
        "--input-csv",
        type=Path,
        default=DEFAULT_INPUT_CSV,
        help="Candidate sentence CSV produced by 2_filter_candidate_sentences.py.",
    )
    parser.add_argument(
        "--prompt-path",
        type=Path,
        default=DEFAULT_PROMPT_PATH,
        help="Prompt template shared by all Codex extraction tasks.",
    )
    parser.add_argument(
        "--tasks-jsonl",
        type=Path,
        default=DEFAULT_TASKS_JSONL,
        help="JSONL file containing one Codex task per token.",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=DEFAULT_BATCH_DIR,
        help="Directory to write Markdown batch files for the current Codex chat.",
    )
    parser.add_argument(
        "--result-template",
        type=Path,
        default=DEFAULT_RESULT_TEMPLATE,
        help="CSV template for extracted results.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="How many tokens to place in each Markdown batch file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of rows to package. 0 means no limit.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N rows from the input CSV.",
    )
    return parser.parse_args()


def load_prompt_template(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Prompt template does not exist: {path}")
    return path.read_text(encoding="utf-8").strip()


def validate_input_csv(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"Input CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        required = {"row_index", "token_name", "token_symbol", "token_href", "sentence"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise SystemExit(
                f"Missing required columns in {path}: {', '.join(sorted(missing))}"
            )


def derive_slug(token_href: str) -> str:
    path = urlparse((token_href or "").strip()).path.strip("/")
    if not path:
        return ""
    return path.split("/")[-1].strip().lower()


def iter_input_rows(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for index, row in enumerate(reader, start=1):
            yield index, row


def group_sentence_rows(path: Path) -> list[tuple[int, dict[str, str], list[dict[str, str]]]]:
    grouped: dict[int, tuple[dict[str, str], list[dict[str, str]]]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            try:
                row_index = int(str(row.get("row_index") or "").strip())
            except ValueError:
                continue
            if row_index not in grouped:
                grouped[row_index] = (row, [])
            grouped[row_index][1].append(row)
    return [(row_index, header, rows) for row_index, (header, rows) in sorted(grouped.items())]


def build_evidence_block(sentence_rows: list[dict[str, str]]) -> str:
    lines: list[str] = []
    for index, row in enumerate(sentence_rows, start=1):
        source_type = str(row.get("source_type") or "").strip()
        source_label = str(row.get("source_label") or "").strip()
        source_url = str(row.get("source_url") or "").strip()
        cmc_match_method = str(row.get("cmc_match_method") or "").strip()
        trigger = str(row.get("trigger_keyword") or "").strip()
        risk_flags = str(row.get("risk_flags") or "[]").strip()
        sentence = str(row.get("sentence") or "").strip()
        lines.extend(
            [
                f"[{index}] source_type: {source_type or '-'}",
                f"[{index}] source_label: {source_label or '-'}",
                f"[{index}] source_url: {source_url or '-'}",
                f"[{index}] cmc_match_method: {cmc_match_method or '-'}",
                f"[{index}] trigger_keyword: {trigger or '-'}",
                f"[{index}] risk_flags: {risk_flags or '[]'}",
                f"[{index}] sentence: {sentence or '[EMPTY]'}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_task(
    prompt_template: str,
    row_index: int,
    header_row: dict[str, str],
    sentence_rows: list[dict[str, str]],
) -> dict[str, object]:
    token_name = str(header_row.get("token_name") or "").strip()
    token_symbol = str(header_row.get("token_symbol") or "").strip()
    token_href = str(header_row.get("token_href") or "").strip()
    slug = str(header_row.get("slug") or "").strip() or derive_slug(token_href)
    evidence_block = build_evidence_block(sentence_rows)
    prompt = (
        f"{prompt_template}\n\n"
        f"Return exactly one JSON object for this token.\n"
        f"Use only the evidence sentences below. Do not infer from token name alone.\n\n"
        f"row_index: {row_index}\n"
        f"token_name: {token_name}\n"
        f"token_symbol: {token_symbol}\n"
        f"token_href: {token_href}\n"
        f"slug: {slug}\n\n"
        f"Candidate evidence sentences:\n{evidence_block or '[EMPTY]'}\n"
    )
    return {
        "row_index": row_index,
        "token_name": token_name,
        "token_symbol": token_symbol,
        "token_href": token_href,
        "slug": slug,
        "evidence_sentences": sentence_rows,
        "prompt": prompt,
    }


def write_jsonl(path: Path, tasks: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as outfile:
        for task in tasks:
            outfile.write(json.dumps(task, ensure_ascii=False) + "\n")


def write_batch_files(batch_dir: Path, tasks: list[dict[str, object]], batch_size: int) -> int:
    batch_dir.mkdir(parents=True, exist_ok=True)

    for path in batch_dir.glob("batch_*.md"):
        path.unlink()

    batch_count = 0
    for start in range(0, len(tasks), batch_size):
        batch_count += 1
        subset = tasks[start : start + batch_size]
        batch_path = batch_dir / f"batch_{batch_count:04d}.md"
        lines = [
            "# Founder / Company Extraction Batch",
            "",
            "Use the source text already embedded below. Do not use outside knowledge.",
            "For each task, return exactly one JSON object with these keys:",
            "`row_index`, `token_name`, `token_symbol`, `token_href`, `slug`, "
            "`founder_people`, `related_companies`, `foundation_or_orgs`, "
            "`confidence`, `evidence_spans`, `notes`",
            "",
            "Rules:",
            "- `founder_people`, `related_companies`, `foundation_or_orgs`, `evidence_spans` must be JSON arrays.",
            "- `confidence` must be one of `high`, `medium`, `low`.",
            "- Use only explicit evidence from the provided token text.",
            "- If unsupported, return empty arrays.",
            "- Do not add markdown fences around the JSON objects.",
            "",
        ]
        for task in subset:
            lines.extend(
                [
                    f"## Task {task['row_index']}",
                    "",
                    str(task["prompt"]),
                    "",
                ]
            )
        batch_path.write_text("\n".join(lines), encoding="utf-8")
    return batch_count


def write_result_template(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=RESULT_FIELDNAMES)
        writer.writeheader()


def main() -> None:
    args = parse_args()
    if args.limit < 0:
        raise SystemExit("--limit must be 0 or greater.")
    if args.offset < 0:
        raise SystemExit("--offset must be 0 or greater.")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")

    input_csv = args.input_csv.resolve()
    prompt_path = args.prompt_path.resolve()
    tasks_jsonl = args.tasks_jsonl.resolve()
    batch_dir = args.batch_dir.resolve()
    result_template = args.result_template.resolve()

    validate_input_csv(input_csv)
    prompt_template = load_prompt_template(prompt_path)

    tasks: list[dict[str, object]] = []
    for row_index, header_row, sentence_rows in group_sentence_rows(input_csv):
        if row_index <= args.offset:
            continue
        if args.limit > 0 and len(tasks) >= args.limit:
            break
        if not sentence_rows:
            continue
        tasks.append(build_task(prompt_template, row_index, header_row, sentence_rows))

    if not tasks:
        raise SystemExit("No rows selected.")

    write_jsonl(tasks_jsonl, tasks)
    batch_count = write_batch_files(batch_dir, tasks, args.batch_size)
    write_result_template(result_template)

    print(f"Prepared {len(tasks)} tasks.", flush=True)
    print(f"Tasks JSONL: {tasks_jsonl}", flush=True)
    print(f"Batch files: {batch_dir} ({batch_count} files)", flush=True)
    print(f"Result template: {result_template}", flush=True)


if __name__ == "__main__":
    main()
