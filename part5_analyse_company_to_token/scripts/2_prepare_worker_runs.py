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
    "company_type",
    "crypto_project_likelihood",
    "project_search_required",
    "project_search_reason",
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

CLASSIFIER_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "normalized_domain",
    "company_type",
    "crypto_project_likelihood",
    "search_tier",
    "project_search_required",
    "risk_flags",
    "classifier_reason",
]

VERIFICATION_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "worker_token_ticker",
    "verifier_token_ticker",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_urls",
    "recommended_action",
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
    "classifier_results_csv",
    "results_csv",
    "instructions_file",
    "verifier_dir",
    "verification_report_csv",
    "verification_summary_md",
    "verifier_instructions_file",
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


def write_classifier_header(path: Path, force: bool) -> None:
    if path.exists() and results_has_data(path) and not force:
        return
    if path.exists() and not force:
        return
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(CLASSIFIER_CSV_COLUMNS)


def write_verification_header(path: Path, force: bool) -> None:
    if path.exists() and results_has_data(path) and not force:
        return
    if path.exists() and not force:
        return
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(VERIFICATION_CSV_COLUMNS)


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
- {PART5_DIR / "Plan.md"}
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
- For every company, first classify company type, crypto project likelihood, search tier, project_search_required, risk flags, and classifier reason.
- Write one classifier/router row per company to `classifier_results.csv`.
- Use `search_tier = full`, `light`, or `skip_candidate` according to `Plan.md`.
- Use `project_search_required = yes` for `full` and `light`; use `no` only for `skip_candidate`.
- If `search_tier = skip_candidate`, write one completed result row with `token_ticker = []` and a clear `project_search_reason` derived from `classifier_reason`.
- If `search_tier = light`, run a bounded token-existence check.
- If `search_tier = full`, search freely to identify company -> project -> fungible token ticker mapping.
- Prefer official and primary sources, but do not limit research to official website, CoinGecko, or CoinMarketCap.
- Return exactly one CSV row per company.
- If no supported token is found, set `token_ticker` to `[]`.
- If multiple tokens are found, keep one row and put all symbols in `token_ticker` as a JSON list, e.g. `["ABC","XYZ"]`.
- Also use JSON-list strings for `project_name`, `project_url`, `token_name`, and `token_url`.
- Do not use stock ticker, NFT-only symbol, chain name, or product code as a fungible token ticker unless the evidence clearly supports it.

Write:
- {run_dir / "classifier_results.csv"}
- {run_dir / "results.csv"}

Classifier CSV header:
{",".join(CLASSIFIER_CSV_COLUMNS)}

CSV header:
{",".join(RESULT_CSV_COLUMNS)}

Final response should report:
- classifier rows written
- total data rows written
- rows with non-empty `token_ticker`
- rows with `token_ticker = []`
- rows by `search_tier`
- `needs_manual_review = yes` count
- classifier file path
- results file path
"""


def build_verifier_instructions(
    round_index: int,
    round_rows: list[dict[str, str]],
    verifier_dir: Path,
) -> str:
    result_paths = "\n".join(f"- {row['results_csv']}" for row in round_rows)
    task_paths = "\n".join(f"- {row['tasks_file']}" for row in round_rows)
    task_ranges = "\n".join(
        f"- {row['batch_file']}: task_index {row['first_task_index']} to {row['last_task_index']}"
        for row in round_rows
    )
    return f"""# Part5 Round-End Verifier

You are a fresh verifier subagent for part5 round {round_index}.

You are not the worker that produced these rows. Re-check independently.

Exclusive write scope:
- {verifier_dir}

Read first:
- {PART5_DIR / "Plan.md"}
- {PART5_DIR / "agent_prompt_template.md"}

Round task ranges:
{task_ranges}

Input task files:
{task_paths}

Worker result files:
{result_paths}

Task:
- Independently check whether each company's `token_ticker` JSON list is correct.
- Check that classifier/router tiering did not skip rows that should have been searched.
- Detect missing fungible token tickers.
- Detect extra or unrelated token tickers.
- Detect wrong company-to-project mapping.
- Detect stock tickers, NFT-only symbols, chain names, or product codes incorrectly reported as fungible token tickers.
- Detect `project_search_required = no` rows that should have been searched.
- Focus on token-positive rows, skipped-search rows, ambiguous brands, low/medium confidence rows, and multiple-token signals.

Search policy:
- Search freely.
- Use independent queries, not only worker evidence URLs.
- Prefer official and primary sources when available.
- Use secondary sources only for corroboration or disambiguation.

Write:
- {verifier_dir / "verification_report.csv"}
- {verifier_dir / "verification_summary.md"}

CSV header:
{",".join(VERIFICATION_CSV_COLUMNS)}

Every row in the round should appear in `verification_report.csv`. Use `verdict = pass` when the worker row is acceptable.

Allowed verdict values:
- pass
- suspected_missing_token
- suspected_extra_token
- wrong_project_mapping
- non_fungible_or_stock_ticker
- search_should_not_have_been_skipped
- insufficient_evidence

Allowed recommended_action values:
- accept_worker_row
- edit_row
- mark_manual_review
- rerun_company
- rerun_batch
- update_prompt_or_process

`verification_summary.md` must include:
- checked row count
- pass count
- non-pass count
- suspected missing token count
- suspected extra token count
- wrong mapping count
- skipped-search concern count
- systematic causes found
- recommended process updates
"""


def build_worker_spawn_prompt(row: dict[str, str]) -> str:
    return f"""Use a worker subagent for this part5 batch. Recommended model: gpt-5.4-mini, reasoning medium.

Read the worker instructions:
{row["instructions_file"]}

Then execute the batch and write results only to:
{row["classifier_results_csv"]}
{row["results_csv"]}
"""


def build_verifier_spawn_prompt(row: dict[str, str]) -> str:
    return f"""Use a fresh verifier subagent for this part5 round. Recommended model: gpt-5.4-mini, reasoning high.

Read the verifier instructions:
{row["verifier_instructions_file"]}

Then write:
{row["verification_report_csv"]}
{row["verification_summary_md"]}

The round is not complete until every non-pass verifier row has a recorded recommended action.
"""


def write_rounds_markdown(path: Path, schedule_rows: list[dict[str, str]], workers: int) -> None:
    lines = [
        "# Part5 Worker Schedule",
        "",
        f"- workers_per_round: {workers}",
        f"- total_batches: {len(schedule_rows)}",
        f"- total_rounds: {((len(schedule_rows) - 1) // workers + 1) if schedule_rows else 0}",
        "",
        "Use one round at a time. Start the listed workers in parallel, wait for all to finish, then start the fresh verifier for that same round.",
        "",
        "Do not collect, merge, update checkpoint, or delete temporary run directories until the round verifier has written `verification_report.csv` and `verification_summary.md` and every non-pass row has a recorded action.",
        "",
        "After worker results are complete, collect merged results and manual-review rows:",
        "",
        "```bash",
        f"python part5_analyse_company_to_token/scripts/3_collect_results.py --runs-dir {path.parent}",
        "```",
        "",
    ]
    current_round = ""
    last_round_row: dict[str, str] | None = None
    for row in schedule_rows:
        if row["round_index"] != current_round:
            if last_round_row is not None:
                lines.extend(
                    [
                        f"### Round {current_round} Verifier",
                        "",
                        "```text",
                        build_verifier_spawn_prompt(last_round_row),
                        "```",
                        "",
                    ]
                )
            current_round = row["round_index"]
            lines.extend([f"## Round {current_round}", ""])
        lines.extend(
            [
                f"### Worker {row['worker_slot']} - {row['batch_file']}",
                "",
                "```text",
                build_worker_spawn_prompt(row),
                "```",
                "",
            ]
        )
        last_round_row = row
    if last_round_row is not None:
        lines.extend(
            [
                f"### Round {current_round} Verifier",
                "",
                "```text",
                build_verifier_spawn_prompt(last_round_row),
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


def prepare_round_verification(
    runs_dir: Path,
    round_index: int,
    round_rows: list[dict[str, str]],
    force: bool,
) -> dict[str, str]:
    verifier_dir = runs_dir / f"round_{round_index:04d}_verification"
    verifier_dir.mkdir(parents=True, exist_ok=True)

    verification_report = verifier_dir / "verification_report.csv"
    verification_summary = verifier_dir / "verification_summary.md"
    verifier_instructions = verifier_dir / "verifier_instructions.md"

    write_verification_header(verification_report, force=force)

    if force or not verification_summary.exists():
        verification_summary.write_text(
            "\n".join(
                [
                    f"# Round {round_index} Verification Summary",
                    "",
                    "- status: pending",
                    "- checked row count:",
                    "- pass count:",
                    "- non-pass count:",
                    "- suspected missing token count:",
                    "- suspected extra token count:",
                    "- wrong mapping count:",
                    "- skipped-search concern count:",
                    "- systematic causes found:",
                    "- recommended process updates:",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if force or not verifier_instructions.exists():
        verifier_instructions.write_text(
            build_verifier_instructions(round_index, round_rows, verifier_dir),
            encoding="utf-8",
        )

    return {
        "verifier_dir": relative_path(verifier_dir),
        "verification_report_csv": relative_path(verification_report),
        "verification_summary_md": relative_path(verification_summary),
        "verifier_instructions_file": relative_path(verifier_instructions),
    }


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

    classifier_results_csv = run_dir / "classifier_results.csv"
    write_classifier_header(classifier_results_csv, force=force)

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
        "classifier_results_csv": relative_path(classifier_results_csv),
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

    rows_by_round: dict[int, list[dict[str, str]]] = {}
    for row in schedule_rows:
        rows_by_round.setdefault(int(row["round_index"]), []).append(row)

    for round_index, round_rows in rows_by_round.items():
        verifier_paths = prepare_round_verification(
            runs_dir=runs_dir,
            round_index=round_index,
            round_rows=round_rows,
            force=args.force,
        )
        for row in round_rows:
            row.update(verifier_paths)

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
