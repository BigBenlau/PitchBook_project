#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import fcntl
import json
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent

DEFAULT_RUNS_DIR = PART6_DIR / "agent_runs" / "crypto_investor"
DEFAULT_LATEST_JOB_JSON = PART6_DIR / "agent_runs" / "crypto_investor_longrun_latest.json"
DEFAULT_BATCH_DIR = REPO_ROOT / "part5_to_part6" / "output" / "part6_batches"
DEFAULT_EXPECTED_ROW_COUNT = 10353
DEFAULT_HEARTBEAT_GRACE_SECONDS = 1800
DEFAULT_MAX_WORKERS = 8
DEFAULT_POLL_SECONDS = 30
DEFAULT_BATCH_TIMEOUT_SECONDS = 7200
DEFAULT_STARTUP_NO_ROW_TIMEOUT_SECONDS = 480
DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS = 480
DEFAULT_LOG = PART6_DIR / "agent_runs" / "crypto_investor_watchdog.log"
DEFAULT_RESTART_STDOUT_LOG = PART6_DIR / "agent_runs" / "crypto_investor_watchdog_restarts.log"
DEFAULT_LOCK = PART6_DIR / "agent_runs" / "crypto_investor_watchdog.lock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Part6 queue longrun watchdog. Intended for cron: if final outputs "
            "are incomplete and the longrun is stopped or stale, restart it in screen."
        )
    )
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--latest-job-json", type=Path, default=DEFAULT_LATEST_JOB_JSON)
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--expected-row-count", type=int, default=DEFAULT_EXPECTED_ROW_COUNT)
    parser.add_argument("--heartbeat-grace-seconds", type=int, default=DEFAULT_HEARTBEAT_GRACE_SECONDS)
    parser.add_argument("--max-workers", type=int, default=DEFAULT_MAX_WORKERS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--batch-timeout-seconds", type=int, default=DEFAULT_BATCH_TIMEOUT_SECONDS)
    parser.add_argument("--startup-no-row-timeout-seconds", type=int, default=DEFAULT_STARTUP_NO_ROW_TIMEOUT_SECONDS)
    parser.add_argument("--partial-stall-timeout-seconds", type=int, default=DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS)
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG)
    parser.add_argument("--restart-stdout-log", type=Path, default=DEFAULT_RESTART_STDOUT_LOG)
    parser.add_argument("--lock-file", type=Path, default=DEFAULT_LOCK)
    parser.add_argument(
        "--restart-mode",
        choices=["foreground", "tmux", "screen", "systemd"],
        default="tmux",
    )
    parser.add_argument(
        "--complete-exit-code",
        type=int,
        default=0,
        help="Exit with this code when final outputs are complete; useful for a loop wrapper that should stop itself.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def log_line(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{iso_now()} {message}\n")


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def acquire_watchdog_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("w", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        raise SystemExit("another watchdog invocation is already running")
    handle.write(json.dumps({"pid": subprocess.os.getpid(), "started_at": iso_now()}) + "\n")
    handle.flush()
    return handle


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def task_indexes_are_complete(path: Path, expected_count: int) -> tuple[bool, int, str]:
    rows = read_csv_rows(path)
    if len(rows) != expected_count:
        return False, len(rows), f"row_count={len(rows)} expected={expected_count}"
    indexes: list[int] = []
    for row_number, row in enumerate(rows, start=2):
        raw = str(row.get("task_index") or "").strip()
        try:
            indexes.append(int(raw))
        except ValueError:
            return False, len(rows), f"invalid_task_index={raw!r} csv_row={row_number}"
    expected = list(range(1, expected_count + 1))
    if indexes != expected:
        for offset, (actual, want) in enumerate(zip(indexes, expected), start=1):
            if actual != want:
                return False, len(rows), f"task_index_mismatch_at_data_row={offset} actual={actual} expected={want}"
        return False, len(rows), "task_index_sequence_mismatch"
    return True, len(rows), "complete"


def final_outputs_complete(runs_dir: Path, expected_count: int) -> tuple[bool, str]:
    results_ok, results_count, results_reason = task_indexes_are_complete(runs_dir / "results.csv", expected_count)
    classifier_ok, classifier_count, classifier_reason = task_indexes_are_complete(
        runs_dir / "classifier_results.csv",
        expected_count,
    )
    if results_ok and classifier_ok:
        return True, f"results={results_count} classifier={classifier_count}"
    return False, f"results:{results_reason}; classifier:{classifier_reason}"


def run_status(latest_job_json: Path, heartbeat_grace_seconds: int) -> tuple[dict[str, Any] | None, str]:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "7_check_longrun_status.py"),
        "--latest-job-json",
        str(latest_job_json),
        "--heartbeat-grace-seconds",
        str(heartbeat_grace_seconds),
        "--json",
    ]
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=90,
    )
    if completed.returncode != 0:
        return None, f"status_command_failed returncode={completed.returncode} stderr={completed.stderr.strip()!r}"
    try:
        return json.loads(completed.stdout), ""
    except json.JSONDecodeError as exc:
        return None, f"status_json_decode_failed error={exc}"


def batch_count_for_metadata(schedule_csv: Path, batch_dir: Path) -> int:
    rows = read_csv_rows(schedule_csv)
    if rows:
        return len(rows)
    return len(sorted(batch_dir.glob("batch_*.jsonl"))) if batch_dir.exists() else 0


def max_round_index(schedule_csv: Path, *, max_workers: int, batch_count: int) -> int:
    rows = read_csv_rows(schedule_csv)
    values: list[int] = []
    for row in rows:
        try:
            values.append(int(str(row.get("round_index") or "0")))
        except ValueError:
            pass
    if values:
        return max(values)
    if batch_count > 0 and max_workers > 0:
        return math.ceil(batch_count / max_workers)
    return 1


def build_supervisor_command(
    *,
    runs_dir: Path,
    round_count: int,
    max_workers: int,
    poll_seconds: int,
    batch_timeout_seconds: int,
    startup_no_row_timeout_seconds: int,
    partial_stall_timeout_seconds: int,
) -> list[str]:
    return [
        sys.executable,
        str(SCRIPT_DIR / "5_run_queue_supervisor.py"),
        "--runs-dir",
        str(runs_dir),
        "--final-dir",
        str(runs_dir),
        "--start-round-index",
        "1",
        "--round-count",
        str(round_count),
        "--max-workers",
        str(max_workers),
        "--poll-seconds",
        str(poll_seconds),
        "--batch-timeout-seconds",
        str(batch_timeout_seconds),
        "--startup-no-row-timeout-seconds",
        str(startup_no_row_timeout_seconds),
        "--partial-stall-timeout-seconds",
        str(partial_stall_timeout_seconds),
    ]


def should_restart(status_payload: dict[str, Any] | None, heartbeat_grace_seconds: int) -> tuple[bool, str]:
    if status_payload is None:
        return True, "status_unavailable"
    status = str(status_payload.get("status") or "").strip()
    phase = str(status_payload.get("phase") or "").strip()
    heartbeat_age = status_payload.get("heartbeat_age_seconds")
    stale_heartbeat = not isinstance(heartbeat_age, int) or heartbeat_age > heartbeat_grace_seconds
    stopped_statuses = {
        "missing",
        "failed",
        "stopped_or_stale",
        "launched_no_state",
    }
    failed_phases = {
        "failed",
        "error",
        "final_lint_failed",
    }
    if status in stopped_statuses:
        return True, f"status={status}"
    if phase in failed_phases:
        return True, f"phase={phase}"
    if stale_heartbeat:
        return True, f"heartbeat_age={heartbeat_age} grace={heartbeat_grace_seconds}"
    return False, f"status={status} phase={phase} heartbeat_age={heartbeat_age}"


def start_in_screen(session_name: str, command: list[str], stdout_log: Path) -> subprocess.CompletedProcess[str]:
    screen_bin = shutil.which("screen")
    if not screen_bin:
        raise SystemExit("screen is not available")
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    shell_command = (
        f"cd {sh_quote(str(REPO_ROOT))} && "
        f"exec {' '.join(sh_quote(part) for part in command)} "
        f">> {sh_quote(str(stdout_log))} 2>&1"
    )
    return subprocess.run(
        [screen_bin, "-dmS", session_name, "bash", "-lc", shell_command],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )


def start_in_tmux(session_name: str, command: list[str], stdout_log: Path) -> subprocess.CompletedProcess[str]:
    tmux_bin = shutil.which("tmux")
    if not tmux_bin:
        raise SystemExit("tmux is not available")
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    shell_command = (
        f"cd {sh_quote(str(REPO_ROOT))} && "
        f"exec {' '.join(sh_quote(part) for part in command)} "
        f">> {sh_quote(str(stdout_log))} 2>&1"
    )
    return subprocess.run(
        [tmux_bin, "new-session", "-d", "-s", session_name, "bash", "-lc", shell_command],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )


def start_in_systemd(session_name: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    systemd_run_bin = shutil.which("systemd-run")
    if not systemd_run_bin:
        raise SystemExit("systemd-run is not available")
    return subprocess.run(
        [
            systemd_run_bin,
            "--user",
            "--unit",
            session_name,
            "--same-dir",
            "--collect",
            "-p",
            f"WorkingDirectory={REPO_ROOT}",
            *command,
        ],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=60,
    )


def start_in_foreground(command: list[str], stdout_log: Path) -> subprocess.CompletedProcess[str]:
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    with stdout_log.open("a", encoding="utf-8") as handle:
        return subprocess.run(
            command,
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def update_latest_job(
    latest_job_json: Path,
    *,
    runs_dir: Path,
    command: list[str],
    session_name: str,
    mode: str,
    expected_count: int,
    max_workers: int,
    round_count: int,
    batch_count: int,
) -> None:
    payload = load_json(latest_job_json) or {}
    payload.update(
        {
            "launched_at": iso_now(),
            "runs_dir": str(runs_dir.resolve()),
            "schedule_csv": str((runs_dir / "schedule.csv").resolve()),
            "events_log": str((runs_dir / "supervisor_events.log").resolve()),
            "state_json": str((runs_dir / "supervisor_state.json").resolve()),
            "registry_json": str((runs_dir / "supervisor_registry.json").resolve()),
            "final_dir": str(runs_dir.resolve()),
            "final_results_csv": str((runs_dir / "results.csv").resolve()),
            "start_batch": 1,
            "end_batch": batch_count,
            "first_task_index": 1,
            "last_task_index": expected_count,
            "batch_count": batch_count,
            "workers": max_workers,
            "scheduler_mode": "queue",
            "round_count_actual": round_count,
            "mode": mode,
            "screen_session": session_name if mode == "screen_watchdog" else None,
            "tmux_session": session_name if mode == "tmux_watchdog" else None,
            "unit_name": session_name if mode == "systemd_watchdog" else None,
            "command": command,
        }
    )
    write_json(latest_job_json, payload)


def main() -> None:
    args = parse_args()
    runs_dir = args.runs_dir.resolve()
    latest_job_json = args.latest_job_json.resolve()
    batch_dir = args.batch_dir.resolve()
    log_path = args.log.resolve()
    restart_stdout_log = args.restart_stdout_log.resolve()

    lock_handle = acquire_watchdog_lock(args.lock_file.resolve())
    try:
        complete, complete_reason = final_outputs_complete(runs_dir, args.expected_row_count)
        if complete:
            log_line(log_path, f"complete=true {complete_reason}; watchdog exits")
            raise SystemExit(args.complete_exit_code)

        status_payload, status_error = run_status(latest_job_json, args.heartbeat_grace_seconds)
        restart, reason = should_restart(status_payload, args.heartbeat_grace_seconds)
        if not restart:
            log_line(log_path, f"complete=false {complete_reason}; healthy {reason}; no_restart")
            return

        batch_count = batch_count_for_metadata(runs_dir / "schedule.csv", batch_dir)
        round_count = max_round_index(
            runs_dir / "schedule.csv",
            max_workers=args.max_workers,
            batch_count=batch_count,
        )
        command = build_supervisor_command(
            runs_dir=runs_dir,
            round_count=round_count,
            max_workers=args.max_workers,
            poll_seconds=args.poll_seconds,
            batch_timeout_seconds=args.batch_timeout_seconds,
            startup_no_row_timeout_seconds=args.startup_no_row_timeout_seconds,
            partial_stall_timeout_seconds=args.partial_stall_timeout_seconds,
        )
        session_name = f"part6_crypto_longrun_{utc_now().strftime('%Y%m%dT%H%M%SZ')}"
        log_line(
            log_path,
            (
                f"complete=false {complete_reason}; restart_required reason={reason} "
                f"status_error={status_error!r} mode={args.restart_mode} session={session_name}"
            ),
        )
        if args.dry_run:
            log_line(log_path, f"dry_run=true command={' '.join(command)}")
            return

        if args.restart_mode == "foreground":
            completed = start_in_foreground(command, restart_stdout_log)
            mode = "foreground_watchdog"
        elif args.restart_mode == "tmux":
            completed = start_in_tmux(session_name, command, restart_stdout_log)
            mode = "tmux_watchdog"
        elif args.restart_mode == "screen":
            completed = start_in_screen(session_name, command, restart_stdout_log)
            mode = "screen_watchdog"
        else:
            completed = start_in_systemd(session_name, command)
            mode = "systemd_watchdog"
        log_line(
            log_path,
            (
                f"restart_command returncode={completed.returncode} "
                f"stdout={completed.stdout.strip()!r} stderr={completed.stderr.strip()!r}"
            ),
        )
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
        update_latest_job(
            latest_job_json,
            runs_dir=runs_dir,
            command=command,
            session_name=session_name,
            mode=mode,
            expected_count=args.expected_row_count,
            max_workers=args.max_workers,
            round_count=round_count,
            batch_count=batch_count,
        )
    finally:
        lock_handle.close()


if __name__ == "__main__":
    main()
