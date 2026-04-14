#!/usr/bin/env python3
"""
Prepare token-to-entity extraction tasks.

This task builder is token_id-based and always emits one task per token in the batch,
even when the sentence file has no evidence rows for that token.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DEFAULT_BATCH_CSV = PROJECT_DIR / "output" / "token_master.csv"
DEFAULT_SENTENCES_CSV = PROJECT_DIR / "output" / "entity_sentences.csv"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "output"
DEFAULT_TASKS_JSONL = DEFAULT_OUTPUT_DIR / "token_entity_tasks.jsonl"
DEFAULT_BATCH_DIR = DEFAULT_OUTPUT_DIR / "codex_batches"
DEFAULT_RESULT_TEMPLATE = DEFAULT_OUTPUT_DIR / "token_entity_results.csv"
DEFAULT_PROMPT_PATH = PROJECT_DIR / "scripts" / "4_founder_company_prompt.txt"
DEFAULT_BATCH_SIZE = 10

RESULT_FIELDNAMES = [
    "token_id",
    "token_name",
    "token_symbol",
    "coingecko_slug",
    "cmc_slug",
    "token_href",
    "official_website",
    "token_type",
    "founder_people",
    "founder_status",
    "founder_evidence_spans",
    "related_companies",
    "related_company_status",
    "related_company_evidence_spans",
    "foundation_or_orgs",
    "foundation_status",
    "foundation_evidence_spans",
    "source_urls",
    "source_labels",
    "confidence",
    "needs_manual_review",
    "notes",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare token-level extraction tasks.")
    parser.add_argument("--batch-csv", type=Path, default=DEFAULT_BATCH_CSV)
    parser.add_argument("--sentences-csv", type=Path, default=DEFAULT_SENTENCES_CSV)
    parser.add_argument("--prompt-path", type=Path, default=DEFAULT_PROMPT_PATH)
    parser.add_argument("--tasks-jsonl", type=Path, default=DEFAULT_TASKS_JSONL)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--result-template", type=Path, default=DEFAULT_RESULT_TEMPLATE)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    return parser.parse_args()


def load_prompt_template(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"Prompt template does not exist: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise SystemExit(f"Input CSV does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def group_sentences_by_token(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in load_rows(path):
        token_id = str(row.get("token_id") or "").strip()
        if token_id:
            grouped.setdefault(token_id, []).append(row)
    return grouped


def build_evidence_block(sentence_rows: list[dict[str, str]]) -> str:
    if not sentence_rows:
        return "[NO HIGH-SIGNAL SENTENCE MATCHES]"
    lines: list[str] = []
    for index, row in enumerate(sentence_rows, start=1):
        lines.extend(
            [
                f"[{index}] source_type: {str(row.get('source_type') or '-').strip()}",
                f"[{index}] source_label: {str(row.get('source_label') or '-').strip()}",
                f"[{index}] source_url: {str(row.get('source_url') or '-').strip()}",
                f"[{index}] target_group: {str(row.get('target_group') or '-').strip()}",
                f"[{index}] trigger_keyword: {str(row.get('trigger_keyword') or '-').strip()}",
                f"[{index}] risk_flags: {str(row.get('risk_flags') or '[]').strip()}",
                f"[{index}] sentence: {str(row.get('sentence') or '[EMPTY]').strip()}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_task(prompt_template: str, token_row: dict[str, str], sentence_rows: list[dict[str, str]]) -> dict[str, object]:
    prompt = (
        f"{prompt_template}\n\n"
        f"Return exactly one JSON object for this token.\n"
        f"Use only the evidence below and the token metadata.\n\n"
        f"token_id: {str(token_row.get('token_id') or '').strip()}\n"
        f"token_name: {str(token_row.get('token_name') or '').strip()}\n"
        f"token_symbol: {str(token_row.get('token_symbol') or '').strip()}\n"
        f"coingecko_slug: {str(token_row.get('coingecko_slug') or '').strip()}\n"
        f"cmc_slug: {str(token_row.get('cmc_slug') or '').strip()}\n"
        f"token_href: {str(token_row.get('token_href') or '').strip()}\n"
        f"official_website: {str(token_row.get('official_website') or '').strip()}\n"
        f"token_type: {str(token_row.get('token_type') or '').strip()}\n\n"
        f"Candidate evidence sentences:\n{build_evidence_block(sentence_rows)}\n"
    )
    return {
        "token_id": str(token_row.get("token_id") or "").strip(),
        "token_name": str(token_row.get("token_name") or "").strip(),
        "token_symbol": str(token_row.get("token_symbol") or "").strip(),
        "coingecko_slug": str(token_row.get("coingecko_slug") or "").strip(),
        "cmc_slug": str(token_row.get("cmc_slug") or "").strip(),
        "token_href": str(token_row.get("token_href") or "").strip(),
        "official_website": str(token_row.get("official_website") or "").strip(),
        "token_type": str(token_row.get("token_type") or "").strip(),
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
            "# Token Entity Extraction Batch",
            "",
            "Use only the evidence embedded below.",
            "Return one JSON object per task using the full result schema.",
            "No markdown fences.",
            "",
        ]
        for task in subset:
            lines.extend([f"## {task['token_id']}", "", str(task["prompt"]), ""])
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

    batch_rows = load_rows(args.batch_csv.resolve())
    sentence_rows_by_token = group_sentences_by_token(args.sentences_csv.resolve())
    prompt_template = load_prompt_template(args.prompt_path.resolve())

    tasks: list[dict[str, object]] = []
    for index, token_row in enumerate(batch_rows, start=1):
        if index <= args.offset:
            continue
        if args.limit > 0 and len(tasks) >= args.limit:
            break
        token_id = str(token_row.get("token_id") or "").strip()
        tasks.append(build_task(prompt_template, token_row, sentence_rows_by_token.get(token_id, [])))

    if not tasks:
        raise SystemExit("No rows selected.")

    write_jsonl(args.tasks_jsonl.resolve(), tasks)
    batch_count = write_batch_files(args.batch_dir.resolve(), tasks, args.batch_size)
    write_result_template(args.result_template.resolve())

    print(f"Prepared {len(tasks)} tasks.", flush=True)
    print(f"Tasks JSONL: {args.tasks_jsonl.resolve()}", flush=True)
    print(f"Batch files: {args.batch_dir.resolve()} ({batch_count} files)", flush=True)
    print(f"Result template: {args.result_template.resolve()}", flush=True)


if __name__ == "__main__":
    main()
