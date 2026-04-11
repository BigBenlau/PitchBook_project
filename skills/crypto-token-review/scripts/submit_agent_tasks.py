#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REPO_ROOT = SKILL_DIR.parent.parent
DEFAULT_BATCH = REPO_ROOT / "part4" / "agent_task_batches" / "crypto_company_first30" / "batch_0001.jsonl"
DEFAULT_RUNS_DIR = REPO_ROOT / "part4" / "agent_runs"
RESULT_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "normalized_domain",
    "project_name",
    "project_url",
    "status",
    "completed_at",
    "token_ticker",
    "token_name",
    "token_url",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare a Codex-native run directory from a batch JSONL task file.",
    )
    parser.add_argument(
        "--batch-jsonl",
        type=Path,
        default=DEFAULT_BATCH,
        help="Batch JSONL produced by build_agent_tasks.py.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Directory to write the prepared Codex run. Defaults to part4/agent_runs/<timestamp>.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of tasks to include. 0 means no limit.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Skip the first N tasks in the batch file.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip tasks already present in results.jsonl under the run directory.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_tasks(path: Path) -> list[dict]:
    tasks: list[dict] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            tasks.append(json.loads(line))
    return tasks


def slice_tasks(tasks: list[dict], offset: int, limit: int) -> list[dict]:
    selected = tasks[offset:] if offset > 0 else tasks
    if limit > 0:
        selected = selected[:limit]
    return selected


def derive_run_dir(batch_jsonl: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return DEFAULT_RUNS_DIR / f"{batch_jsonl.stem}_{stamp}"


def load_existing_task_indexes(path: Path) -> set[int]:
    if not path.exists():
        return set()
    existing: set[int] = set()
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            task_index = row.get("task_index")
            if isinstance(task_index, int):
                existing.add(task_index)
    return existing


def append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as outfile:
        outfile.write(json.dumps(payload, ensure_ascii=True) + "\n")


def write_manifest(path: Path, tasks: list[dict]) -> None:
    fieldnames = [
        "task_index",
        "company_id",
        "company_name",
        "normalized_domain",
        "allowed_sources",
        "agent_task_scope",
    ]
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for task in tasks:
            writer.writerow(
                {
                    "task_index": task.get("task_index", ""),
                    "company_id": task.get("company_id", ""),
                    "company_name": task.get("company_name", ""),
                    "normalized_domain": task.get("normalized_domain", ""),
                    "allowed_sources": task.get("allowed_sources", ""),
                    "agent_task_scope": task.get("agent_task_scope", ""),
                }
            )


def build_instructions(run_dir: Path, selected_count: int) -> str:
    return f"""# Codex Run Instructions

This run directory is prepared for execution inside the current Codex conversation.

Run metadata:
- prepared_at: {utc_now()}
- run_dir: {run_dir}
- selected_tasks: {selected_count}
- skill_path: {SKILL_DIR}

Files:
- tasks.jsonl: the task list to execute in Codex
- manifest.csv: task summary
- results.csv: append one CSV row per completed company
- results.jsonl: optional audit log if the coordinator wants to preserve raw worker output

How to use in Codex:
1. Read `tasks.jsonl`.
2. For each task, spawn a worker agent in the current conversation.
3. Give the worker the task's `prompt` exactly as written.
4. Require the worker to return CSV rows matching the header in `results.csv`.
5. Append returned data rows to `results.csv`; do not duplicate the header.
6. If a company maps to multiple tokens, keep one row and put the tickers in a JSON list in `token_ticker`.
7. If no token is found, append one row with `token_ticker` as `[]`.

CSV header:

{",".join(RESULT_CSV_COLUMNS)}

Result rules:
- Do not include `CompanyID`, `CompanyName`, `has_token`, or `raw_output` columns.
- `token_ticker = []` means no supported token ticker was found.
- `project_name`, `project_url`, `token_ticker`, `token_name`, and `token_url` are JSON-list string columns.
- `completed_at` should be an ISO timestamp; leave blank only if the coordinator fills it later.
"""


def main() -> None:
    args = parse_args()

    batch_jsonl = args.batch_jsonl.resolve()
    if not batch_jsonl.exists():
        raise SystemExit(f"Batch JSONL does not exist: {batch_jsonl}")
    if args.offset < 0:
        raise SystemExit("--offset must be 0 or greater.")
    if args.limit < 0:
        raise SystemExit("--limit must be 0 or greater.")

    run_dir = args.run_dir.resolve() if args.run_dir else derive_run_dir(batch_jsonl)
    run_dir.mkdir(parents=True, exist_ok=True)
    selected_tasks = slice_tasks(load_tasks(batch_jsonl), args.offset, args.limit)
    if not selected_tasks:
        raise SystemExit("No tasks selected for run preparation.")

    results_path = run_dir / "results.jsonl"
    results_csv_path = run_dir / "results.csv"
    existing_indexes = load_existing_task_indexes(results_path) if args.skip_existing else set()
    prepared_tasks = [
        task for task in selected_tasks if int(task.get("task_index", 0)) not in existing_indexes
    ]
    if not prepared_tasks:
        raise SystemExit("No tasks remain after applying --skip-existing.")

    tasks_path = run_dir / "tasks.jsonl"
    with tasks_path.open("w", encoding="utf-8") as outfile:
        for task in prepared_tasks:
            outfile.write(json.dumps(task, ensure_ascii=True) + "\n")

    write_manifest(run_dir / "manifest.csv", prepared_tasks)
    (run_dir / "instructions.md").write_text(
        build_instructions(run_dir, len(prepared_tasks)),
        encoding="utf-8",
    )
    if not results_path.exists():
        results_path.write_text("", encoding="utf-8")
    if not results_csv_path.exists():
        results_csv_path.write_text(",".join(RESULT_CSV_COLUMNS) + "\n", encoding="utf-8")

    append_jsonl(
        run_dir / "prepared_runs.jsonl",
        {
            "prepared_at": utc_now(),
            "source_batch": str(batch_jsonl),
            "run_dir": str(run_dir),
            "selected_tasks": len(prepared_tasks),
        },
    )

    print(f"Run directory: {run_dir}")
    print(f"Tasks selected: {len(selected_tasks)}")
    print(f"Tasks prepared: {len(prepared_tasks)}")
    print(f"Tasks file: {tasks_path}")
    print(f"Manifest: {run_dir / 'manifest.csv'}")
    print(f"Instructions: {run_dir / 'instructions.md'}")
    print(f"Results file: {results_path}")
    print(f"Results CSV: {results_csv_path}")


if __name__ == "__main__":
    main()
