#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_DIR.parent

DEFAULT_BATCH_DIR = PART5_DIR / "agent_task_batches" / "crypto_company"
DEFAULT_RUNS_DIR = PART5_DIR / "agent_runs" / "crypto_company_parallel"
DEFAULT_WORKERS = 5

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

SCHEDULE_COLUMNS = [
    "round_index",
    "worker_slot",
    "batch_file",
    "task_count",
    "first_task_index",
    "last_task_index",
    "first_company",
    "last_company",
    "run_dir",
    "tasks_file",
    "results_csv",
    "instructions_file",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare 5-worker Codex run directories from part5 batch JSONL files.",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=DEFAULT_BATCH_DIR,
        help="Directory containing batch_XXXX.jsonl files.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Directory where per-batch worker run folders will be created.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of parallel workers per round. Defaults to 5.",
    )
    parser.add_argument(
        "--start-batch",
        type=int,
        default=1,
        help="First batch number to include, e.g. 1 for batch_0001.jsonl.",
    )
    parser.add_argument(
        "--limit-batches",
        type=int,
        default=0,
        help="Maximum number of batches to prepare. 0 means all selected batches.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite tasks.jsonl, instructions.md, and empty results.csv files.",
    )
    return parser.parse_args()


def ensure_dir(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_dir():
        raise SystemExit(f"{label} is not a directory: {resolved}")
    return resolved


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def batch_number(path: Path) -> int:
    stem = path.stem
    try:
        return int(stem.split("_", 1)[1])
    except (IndexError, ValueError):
        raise SystemExit(f"Unexpected batch file name: {path.name}") from None


def load_tasks(path: Path) -> list[dict]:
    tasks: list[dict] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def count_result_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        return sum(1 for _ in reader)


def results_has_data(path: Path) -> bool:
    return count_result_rows(path) > 0


def write_results_header(path: Path, force: bool) -> None:
    if path.exists() and results_has_data(path) and not force:
        return
    if path.exists() and not force:
        return
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(RESULT_CSV_COLUMNS)


def build_worker_instructions(
    batch_file: Path,
    run_dir: Path,
    tasks: list[dict],
    round_index: int,
    worker_slot: int,
) -> str:
    first = tasks[0]
    last = tasks[-1]
    return f"""# Part5 Worker Run

You are Worker {worker_slot} in round {round_index} for the part5 company-to-token review.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Exclusive write scope:
- {run_dir}

Read:
- {batch_file}
- {run_dir / "tasks.jsonl"}
- {PART5_DIR / "agent_prompt_template.md"}

Task range:
- batch_file: {batch_file.name}
- task_count: {len(tasks)}
- first_task_index: {first.get("task_index")}
- first_company: {first.get("company_name")}
- last_task_index: {last.get("task_index")}
- last_company: {last.get("company_name")}

Method:
- Follow the rendered prompt in each JSONL task.
- Use only official website under the official domain, CoinGecko, and CoinMarketCap.
- Return exactly one CSV row per company.
- If no supported token is found, set `token_ticker` to `[]`.
- If multiple tokens are found, keep one row and put all symbols in `token_ticker` as a JSON list, e.g. `["ABC","XYZ"]`.
- Also use JSON-list strings for `project_name`, `project_url`, `token_name`, and `token_url`.

Write:
- {run_dir / "results.csv"}

CSV header:
{",".join(RESULT_CSV_COLUMNS)}

Final response should report:
- total data rows written
- rows with non-empty `token_ticker`
- rows with `token_ticker = []`
- `needs_manual_review = yes` count
- output file path
"""


def build_spawn_prompt(row: dict[str, str]) -> str:
    return f"""Use a worker subagent for this part5 batch.

Read the worker instructions:
{row["instructions_file"]}

Then execute the batch and write results only to:
{row["results_csv"]}
"""


def write_rounds_markdown(path: Path, schedule_rows: list[dict[str, str]], workers: int) -> None:
    lines = [
        "# Part5 Worker Schedule",
        "",
        f"- workers_per_round: {workers}",
        f"- total_batches: {len(schedule_rows)}",
        f"- total_rounds: {((len(schedule_rows) - 1) // workers + 1) if schedule_rows else 0}",
        "",
        "Use one round at a time. Start the listed workers in parallel, wait for all to finish, then move to the next round.",
        "",
        "After worker results are complete, collect merged results and manual-review rows:",
        "",
        "```bash",
        f"python part5_analyse_company_to_token/scripts/3_collect_results.py --runs-dir {path.parent}",
        "```",
        "",
    ]
    current_round = ""
    for row in schedule_rows:
        if row["round_index"] != current_round:
            current_round = row["round_index"]
            lines.extend([f"## Round {current_round}", ""])
        lines.extend(
            [
                f"### Worker {row['worker_slot']} - {row['batch_file']}",
                "",
                "```text",
                build_spawn_prompt(row),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_schedule_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=SCHEDULE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def prepare_run(
    batch_file: Path,
    tasks: list[dict],
    runs_dir: Path,
    round_index: int,
    worker_slot: int,
    force: bool,
) -> dict[str, str]:
    run_dir = runs_dir / batch_file.stem
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks_path = run_dir / "tasks.jsonl"
    if force or not tasks_path.exists():
        shutil.copyfile(batch_file, tasks_path)

    results_csv = run_dir / "results.csv"
    write_results_header(results_csv, force=force)

    instructions_file = run_dir / "instructions.md"
    if force or not instructions_file.exists():
        instructions_file.write_text(
            build_worker_instructions(batch_file, run_dir, tasks, round_index, worker_slot),
            encoding="utf-8",
        )

    first = tasks[0]
    last = tasks[-1]
    result_rows = count_result_rows(results_csv)
    status = "completed" if result_rows >= len(tasks) else "pending"
    if 0 < result_rows < len(tasks):
        status = "partial"

    return {
        "round_index": str(round_index),
        "worker_slot": str(worker_slot),
        "batch_file": batch_file.name,
        "task_count": str(len(tasks)),
        "first_task_index": str(first.get("task_index", "")),
        "last_task_index": str(last.get("task_index", "")),
        "first_company": str(first.get("company_name", "")),
        "last_company": str(last.get("company_name", "")),
        "run_dir": relative_path(run_dir),
        "tasks_file": relative_path(tasks_path),
        "results_csv": relative_path(results_csv),
        "instructions_file": relative_path(instructions_file),
        "status": status,
    }


def main() -> None:
    args = parse_args()
    if args.workers <= 0:
        raise SystemExit("--workers must be greater than 0.")
    if args.start_batch <= 0:
        raise SystemExit("--start-batch must be greater than 0.")
    if args.limit_batches < 0:
        raise SystemExit("--limit-batches must be 0 or greater.")

    batch_dir = ensure_dir(args.batch_dir, "Batch directory")
    runs_dir = args.runs_dir.resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)

    batch_files = [
        path
        for path in sorted(batch_dir.glob("batch_*.jsonl"), key=batch_number)
        if batch_number(path) >= args.start_batch
    ]
    if args.limit_batches:
        batch_files = batch_files[: args.limit_batches]
    if not batch_files:
        raise SystemExit("No batch files selected.")

    schedule_rows: list[dict[str, str]] = []
    for index, batch_file in enumerate(batch_files):
        tasks = load_tasks(batch_file)
        if not tasks:
            raise SystemExit(f"Batch file has no tasks: {batch_file}")
        round_index = index // args.workers + 1
        worker_slot = index % args.workers + 1
        schedule_rows.append(
            prepare_run(
                batch_file=batch_file.resolve(),
                tasks=tasks,
                runs_dir=runs_dir,
                round_index=round_index,
                worker_slot=worker_slot,
                force=args.force,
            )
        )

    schedule_csv = runs_dir / "schedule.csv"
    rounds_md = runs_dir / "schedule_rounds.md"
    write_schedule_csv(schedule_csv, schedule_rows)
    write_rounds_markdown(rounds_md, schedule_rows, args.workers)

    print(f"Batch directory: {batch_dir}")
    print(f"Runs directory: {runs_dir}")
    print(f"Workers per round: {args.workers}")
    print(f"Batches scheduled: {len(schedule_rows)}")
    print(f"Rounds: {(len(schedule_rows) - 1) // args.workers + 1}")
    print(f"Schedule CSV: {schedule_csv}")
    print(f"Schedule markdown: {rounds_md}")


if __name__ == "__main__":
    main()
