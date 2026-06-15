#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_DIR.parent
DEFAULT_BATCH_DIR = PART5_DIR / "agent_task_batches" / "crypto_company_rule_b_backfill"
DEFAULT_RUNS_DIR = PART5_DIR / "agent_runs" / "crypto_company_rule_b_backfill_current"
DEFAULT_CODEX_BIN = shutil.which("codex") or "/home/benl66/bin/codex"
DEFAULT_WORKERS = 8
DEFAULT_MAX_RESTARTS = 3
DEFAULT_POLL_SECONDS = 20
DEFAULT_STARTUP_TIMEOUT_SECONDS = 900
DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS = 1800
DEFAULT_BATCH_TIMEOUT_SECONDS = 10800
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_REASONING_EFFORT = "xhigh"
USAGE_LIMIT_MARKERS = [
    "you've hit your usage limit",
    "you have hit your usage limit",
    "usage limit",
]

RULE_B_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "include_rule_B",
    "rule_B_token_results",
    "rule_B_decision_reason",
    "rule_B_needs_manual_review",
]
SCHEDULE_COLUMNS = [
    "batch_file",
    "batch_number",
    "task_count",
    "first_task_index",
    "last_task_index",
    "first_company",
    "last_company",
    "status",
    "attempt_index",
    "respawn_count",
    "last_failure_type",
    "run_dir",
    "tasks_file",
    "active_attempt",
    "rule_b_results_csv",
    "instructions_file",
    "final_message_md",
    "worker_log",
    "pid",
    "started_at",
    "completed_at",
    "collected_at",
    "last_row_count",
    "last_progress_at",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a queue-mode Part5 Rule B-only backfill supervisor.")
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--max-batch-restarts", type=int, default=DEFAULT_MAX_RESTARTS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--startup-no-row-timeout-seconds", type=int, default=DEFAULT_STARTUP_TIMEOUT_SECONDS)
    parser.add_argument("--partial-stall-timeout-seconds", type=int, default=DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS)
    parser.add_argument("--batch-timeout-seconds", type=int, default=DEFAULT_BATCH_TIMEOUT_SECONDS)
    parser.add_argument("--codex-bin", default=DEFAULT_CODEX_BIN)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning-effort", default=DEFAULT_REASONING_EFFORT)
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def pid_alive(pid_value: str) -> bool:
    try:
        pid = int(pid_value)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    stat_path = Path("/proc") / str(pid) / "stat"
    if stat_path.exists():
        try:
            parts = stat_path.read_text(encoding="utf-8", errors="replace").split()
            if len(parts) > 2 and parts[2] == "Z":
                return False
        except OSError:
            pass
    return True


def process_alive(pid_value: str, active_processes: dict[str, subprocess.Popen]) -> bool:
    process = active_processes.get(str(pid_value or ""))
    if process is None:
        return pid_alive(pid_value)
    if process.poll() is None:
        return True
    try:
        process.wait(timeout=0)
    except subprocess.TimeoutExpired:
        return True
    active_processes.pop(str(pid_value or ""), None)
    return False


def bootstrap_codex_home(target_home: Path) -> Path:
    source_home = Path.home() / ".codex"
    target_home.mkdir(parents=True, exist_ok=True)
    for name in ["auth.json", "config.toml", "installation_id", "version.json"]:
        source = source_home / name
        target = target_home / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
    return target_home


def terminate_pid(pid_value: str) -> None:
    try:
        pid = int(pid_value)
    except (TypeError, ValueError):
        return
    if pid <= 0:
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except OSError:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass


def parse_batch_number(path: Path) -> int:
    try:
        return int(path.stem.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def event(runs_dir: Path, event_type: str, **payload: Any) -> None:
    path = runs_dir / "rule_b_supervisor_events.log"
    record = {"at": iso_now(), "event": event_type, **payload}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_state(runs_dir: Path, rows: list[dict[str, str]], phase: str) -> None:
    counts: dict[str, int] = {}
    for row in rows:
        status = row.get("status", "")
        counts[status] = counts.get(status, 0) + 1
    payload = {
        "updated_at": iso_now(),
        "phase": phase,
        "status_counts": counts,
        "total_batches": len(rows),
        "completed_batches": counts.get("completed", 0),
        "retry_capped_batches": counts.get("retry_capped", 0),
        "quota_blocked_batches": counts.get("quota_blocked", 0),
        "active_batches": counts.get("running", 0),
    }
    (runs_dir / "rule_b_supervisor_state.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def runs_dir_from_argv() -> Path:
    for index, value in enumerate(sys.argv):
        if value == "--runs-dir" and index + 1 < len(sys.argv):
            return Path(sys.argv[index + 1])
    return DEFAULT_RUNS_DIR


def render_instructions(tasks_file: Path, output_csv: Path, attempt_dir: Path) -> str:
    return f"""# Part5 Rule B-Only Backfill Worker

You are updating only Rule B outputs for one Part5 batch. Use model `gpt-5.5` with `xhigh` reasoning.

Read:
- {PART5_DIR / "Plan.md"}
- {PART5_DIR / "agent_prompt_template.md"}
- {tasks_file}

Write scope:
- {attempt_dir}

Authoritative output CSV:
- {output_csv}

CSV header:
{",".join(RULE_B_COLUMNS)}

Task:
- Process every task in `{tasks_file}` in order.
- Do not edit the original Part5 `results.csv`.
- Do not rewrite original `token_results`.
- Do not evaluate Rule A.
- Only decide Rule B from the company outward.

Rule B positive:
- `include_rule_B = yes`.
- Include a token only when evidence shows the company is an officially recognized founding entity, co-founding entity, or original founding organization of the blockchain/protocol ecosystem.
- `rule_B_token_results` must be a JSON object-list string.
- Each token object must include `token_symbol`, `token_name`, `token_url`, `reason`, `evidence_urls`, and `evidence_source_types`.
- `evidence_urls` must contain absolute HTTP(S) URLs supporting the founding/original-organization role.

Rule B negative:
- `include_rule_B = no`.
- `rule_B_token_results = []`.
- `rule_B_decision_reason` must explain why the company does not satisfy Rule B.

Exclusions:
- Do not include later venture arms, later ecosystem funds, portfolio companies, dApps, wallets, DEXs, staking providers, incubators, investors, market makers, or ordinary ecosystem participants.
- Do not include a company just because it held, invested in, promoted, listed, partnered with, or used a token.

Manual review flag:
- `rule_B_needs_manual_review = yes` only when Rule B inclusion/exclusion remains unresolved after reasonable search.
- Otherwise write `no`.

Operational requirements:
- Keep exactly one CSV row per task.
- Append rows incrementally as each task is completed.
- Keep task identity fields exactly as provided.
- Use valid CSV quoting and valid JSON for `rule_B_token_results`.
- Use `python3` for any local validation commands; do not call `python`.
- Do not read the global final `results.csv` or sibling batch outputs for routine processing. `{tasks_file}` is the authoritative input for this worker.
"""


def prepare_attempt(row: dict[str, str], *, runs_dir: Path, attempt_index: int) -> dict[str, str]:
    batch_file = Path(row["batch_file"])
    run_dir = Path(row["run_dir"])
    attempt_dir = run_dir / "attempts" / f"attempt_{attempt_index:04d}"
    attempt_dir.mkdir(parents=True, exist_ok=True)
    tasks_file = run_dir / "tasks.jsonl"
    if not tasks_file.exists():
        shutil.copyfile(batch_file, tasks_file)
    output_csv = attempt_dir / "rule_b_results.csv"
    write_csv(output_csv, RULE_B_COLUMNS, [])
    instructions_file = attempt_dir / "worker_instructions.md"
    instructions_file.write_text(render_instructions(tasks_file, output_csv, attempt_dir), encoding="utf-8")
    row.update(
        {
            "attempt_index": str(attempt_index),
            "active_attempt": str(attempt_dir),
            "tasks_file": str(tasks_file),
            "rule_b_results_csv": str(output_csv),
            "instructions_file": str(instructions_file),
            "final_message_md": str(attempt_dir / "final_message.md"),
            "worker_log": str(attempt_dir / "worker.log"),
            "pid": "",
            "started_at": "",
            "completed_at": "",
            "collected_at": "",
            "last_row_count": "0",
            "last_progress_at": "",
        }
    )
    return row


def initialize_schedule(batch_dir: Path, runs_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for order, batch_file in enumerate(sorted(batch_dir.glob("batch_*.jsonl")), start=1):
        tasks = read_jsonl(batch_file)
        if not tasks:
            continue
        batch_number = parse_batch_number(batch_file)
        run_dir = runs_dir / f"batch_{batch_number:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        row = {
            "batch_file": str(batch_file.resolve()),
            "batch_number": str(batch_number or order),
            "task_count": str(len(tasks)),
            "first_task_index": str(tasks[0].get("task_index", "")),
            "last_task_index": str(tasks[-1].get("task_index", "")),
            "first_company": str(tasks[0].get("company_name", "")),
            "last_company": str(tasks[-1].get("company_name", "")),
            "status": "prepared",
            "attempt_index": "0",
            "respawn_count": "0",
            "last_failure_type": "",
            "run_dir": str(run_dir),
            "tasks_file": "",
            "active_attempt": "",
            "rule_b_results_csv": "",
            "instructions_file": "",
            "final_message_md": "",
            "worker_log": "",
            "pid": "",
            "started_at": "",
            "completed_at": "",
            "collected_at": "",
            "last_row_count": "0",
            "last_progress_at": "",
        }
        rows.append(row)
    if not rows:
        raise SystemExit(f"No Rule B batch files found in {batch_dir}")
    return rows


def spawn_worker(
    row: dict[str, str],
    *,
    codex_bin: str,
    model: str,
    reasoning: str,
    runs_dir: Path,
    active_processes: dict[str, subprocess.Popen],
) -> dict[str, str]:
    instructions = Path(row["instructions_file"])
    prompt = f"Read {instructions} and execute it fully. Obey its write scope and output paths exactly."
    cmd = [
        codex_bin,
        "-a",
        "never",
        "--search",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "-m",
        model,
        "-c",
        f"model_reasoning_effort=\"{reasoning}\"",
        "-s",
        "danger-full-access",
        "--json",
        "-o",
        row["final_message_md"],
        prompt,
    ]
    codex_home = bootstrap_codex_home(Path(row["active_attempt"]) / ".codex_home")
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    log_path = Path(row["worker_log"])
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    now = iso_now()
    row["status"] = "running"
    row["pid"] = str(process.pid)
    active_processes[str(process.pid)] = process
    row["started_at"] = now
    row["last_progress_at"] = now
    row["last_row_count"] = "0"
    event(runs_dir, "worker_spawn", batch=row["batch_file"], attempt=row["attempt_index"], pid=process.pid)
    return row


def run_collector(runs_dir: Path, batch_file: str, *, lint_only: bool) -> bool:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "9_collect_rule_b_overlay.py"),
        "--runs-dir",
        str(runs_dir),
        "--batch-file",
        Path(batch_file).name,
    ]
    if lint_only:
        cmd.append("--lint-only")
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    event(
        runs_dir,
        "collector",
        batch=batch_file,
        lint_only=lint_only,
        returncode=completed.returncode,
        stdout_tail=completed.stdout[-1000:],
        stderr_tail=completed.stderr[-1000:],
    )
    return completed.returncode == 0


def mark_retry(row: dict[str, str], reason: str, *, max_restarts: int, runs_dir: Path) -> dict[str, str]:
    restarts = int(row.get("respawn_count") or "0")
    if restarts >= max_restarts:
        row["status"] = "retry_capped"
        row["last_failure_type"] = reason
        row["pid"] = ""
        event(runs_dir, "retry_capped", batch=row["batch_file"], reason=reason, respawn_count=restarts)
        return row
    restarts += 1
    next_attempt = int(row.get("attempt_index") or "1") + 1
    row["respawn_count"] = str(restarts)
    row["last_failure_type"] = reason
    row["status"] = "prepared"
    row = prepare_attempt(row, runs_dir=runs_dir, attempt_index=next_attempt)
    event(runs_dir, "retry_prepared", batch=row["batch_file"], reason=reason, attempt=row["attempt_index"])
    return row


def log_contains_usage_limit(path_value: str) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    if not path.exists():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except OSError:
        return False
    return any(marker in text for marker in USAGE_LIMIT_MARKERS)


def mark_quota_blocked(row: dict[str, str], *, runs_dir: Path) -> dict[str, str]:
    row["status"] = "quota_blocked"
    row["last_failure_type"] = "usage_limit"
    row["pid"] = ""
    row["completed_at"] = iso_now()
    event(
        runs_dir,
        "quota_blocked",
        batch=row["batch_file"],
        attempt=row.get("attempt_index", ""),
        worker_log=row.get("worker_log", ""),
    )
    return row


def seconds_since(value: str) -> float:
    if not value:
        return 0.0
    try:
        return (utc_now() - datetime.fromisoformat(value)).total_seconds()
    except ValueError:
        return 0.0


def update_running_row(
    row: dict[str, str],
    *,
    args: argparse.Namespace,
    runs_dir: Path,
    active_processes: dict[str, subprocess.Popen],
) -> dict[str, str]:
    current_rows = count_rows(Path(row["rule_b_results_csv"]))
    previous_rows = int(row.get("last_row_count") or "0")
    if current_rows > previous_rows:
        row["last_row_count"] = str(current_rows)
        row["last_progress_at"] = iso_now()

    alive = process_alive(row.get("pid", ""), active_processes)
    if alive:
        if current_rows == 0 and seconds_since(row.get("started_at", "")) > args.startup_no_row_timeout_seconds:
            terminate_pid(row.get("pid", ""))
            return mark_retry(row, "startup_no_row", max_restarts=args.max_batch_restarts, runs_dir=runs_dir)
        if 0 < current_rows < int(row["task_count"]) and seconds_since(row.get("last_progress_at", "")) > args.partial_stall_timeout_seconds:
            terminate_pid(row.get("pid", ""))
            return mark_retry(row, "partial_stall", max_restarts=args.max_batch_restarts, runs_dir=runs_dir)
        if seconds_since(row.get("started_at", "")) > args.batch_timeout_seconds:
            terminate_pid(row.get("pid", ""))
            return mark_retry(row, "batch_timeout", max_restarts=args.max_batch_restarts, runs_dir=runs_dir)
        return row

    row["pid"] = ""
    row["completed_at"] = iso_now()
    if log_contains_usage_limit(row.get("worker_log", "")):
        return mark_quota_blocked(row, runs_dir=runs_dir)
    if current_rows != int(row["task_count"]):
        return mark_retry(row, "row_count_mismatch", max_restarts=args.max_batch_restarts, runs_dir=runs_dir)
    if not run_collector(runs_dir, row["batch_file"], lint_only=True):
        return mark_retry(row, "schema_error", max_restarts=args.max_batch_restarts, runs_dir=runs_dir)
    if not run_collector(runs_dir, row["batch_file"], lint_only=False):
        return mark_retry(row, "collect_failed", max_restarts=args.max_batch_restarts, runs_dir=runs_dir)
    row["status"] = "completed"
    row["collected_at"] = iso_now()
    event(runs_dir, "batch_completed", batch=row["batch_file"], attempt=row["attempt_index"])
    return row


def main() -> None:
    args = parse_args()
    args.runs_dir.mkdir(parents=True, exist_ok=True)
    schedule_csv = args.runs_dir / "schedule.csv"
    active_processes: dict[str, subprocess.Popen] = {}
    if schedule_csv.exists():
        rows = read_csv(schedule_csv)
    else:
        rows = initialize_schedule(args.batch_dir, args.runs_dir)
        write_csv(schedule_csv, SCHEDULE_COLUMNS, rows)
        event(args.runs_dir, "supervisor_start", batch_dir=str(args.batch_dir), total_batches=len(rows))

    phase = "watch"
    while True:
        rows = [
            update_running_row(row, args=args, runs_dir=args.runs_dir, active_processes=active_processes)
            if row.get("status") == "running"
            else row
            for row in rows
        ]
        active = sum(1 for row in rows if row.get("status") == "running")
        quota_blocked = any(row.get("status") == "quota_blocked" for row in rows)
        for row in rows:
            if active >= args.workers:
                break
            if quota_blocked:
                break
            if row.get("status") == "prepared":
                if not row.get("active_attempt"):
                    row = prepare_attempt(row, runs_dir=args.runs_dir, attempt_index=int(row.get("attempt_index") or "0") + 1)
                row = spawn_worker(
                    row,
                    codex_bin=args.codex_bin,
                    model=args.model,
                    reasoning=args.reasoning_effort,
                    runs_dir=args.runs_dir,
                    active_processes=active_processes,
                )
                active += 1
                write_csv(schedule_csv, SCHEDULE_COLUMNS, rows)
                write_state(args.runs_dir, rows, phase)
        write_csv(schedule_csv, SCHEDULE_COLUMNS, rows)
        write_state(args.runs_dir, rows, phase)
        if quota_blocked and active == 0:
            phase = "quota_blocked"
            write_state(args.runs_dir, rows, phase)
            event(args.runs_dir, "supervisor_quota_blocked")
            break
        unresolved = [row for row in rows if row.get("status") not in {"completed", "retry_capped", "quota_blocked"}]
        if not unresolved:
            phase = "completed"
            write_state(args.runs_dir, rows, phase)
            event(args.runs_dir, "supervisor_complete")
            break
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        runs_dir = runs_dir_from_argv()
        runs_dir.mkdir(parents=True, exist_ok=True)
        event(
            runs_dir,
            "supervisor_error",
            error_type=type(exc).__name__,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        (runs_dir / "rule_b_supervisor_state.json").write_text(
            json.dumps(
                {
                    "updated_at": iso_now(),
                    "phase": "failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        raise
