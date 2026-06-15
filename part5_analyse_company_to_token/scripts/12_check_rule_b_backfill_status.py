#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
DEFAULT_LATEST_JSON = PART5_DIR / "agent_runs" / "crypto_company_rule_b_longrun_latest.json"
DEFAULT_ACTIVE_RUN_JSON = PART5_DIR / "agent_runs" / "crypto_company_rule_b_active_run.json"
DEFAULT_FINAL_RESULTS = PART5_DIR / "agent_runs" / "crypto_company" / "results.csv"
DEFAULT_ACTIVE_HEARTBEAT_SECONDS = 300


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check Part5 Rule B-only backfill longrun status.")
    parser.add_argument("--latest-json", type=Path, default=DEFAULT_LATEST_JSON)
    parser.add_argument("--active-run-json", type=Path, default=DEFAULT_ACTIVE_RUN_JSON)
    parser.add_argument("--runs-dir", type=Path, default=None)
    return parser.parse_args()


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_systemd_unit_state(unit_name: str) -> dict[str, str] | None:
    if not unit_name:
        return None
    completed = subprocess.run(
        [
            "systemctl",
            "--user",
            "show",
            unit_name,
            "--property=Id",
            "--property=LoadState",
            "--property=ActiveState",
            "--property=SubState",
            "--property=MainPID",
            "--property=Result",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        return None
    payload: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key] = value
    return payload


def tmux_session_alive(session_name: str) -> bool:
    tmux_bin = shutil.which("tmux")
    if not tmux_bin or not session_name:
        return False
    completed = subprocess.run(
        [tmux_bin, "has-session", "-t", session_name],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def screen_session_alive(session_name: str) -> bool:
    screen_bin = shutil.which("screen")
    if not screen_bin or not session_name:
        return False
    completed = subprocess.run(
        [screen_bin, "-ls", session_name],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return session_name in completed.stdout


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def count_csv_rows(path_value: str) -> int:
    if not path_value:
        return 0
    path = Path(path_value)
    if not path.exists():
        return 0
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def mtime_age_seconds(path: Path) -> int | None:
    if not path.exists():
        return None
    return int(time.time() - path.stat().st_mtime)


def command_poll_seconds(latest: dict[str, object]) -> int:
    command = latest.get("command")
    if not isinstance(command, list):
        return 0
    try:
        index = command.index("--poll-seconds")
    except ValueError:
        return 0
    if index + 1 >= len(command):
        return 0
    try:
        return int(str(command[index + 1]))
    except ValueError:
        return 0


def recent_file_heartbeat(runs_dir: Path, latest: dict[str, object]) -> tuple[bool, int | None]:
    ages = [
        age
        for age in [
            mtime_age_seconds(runs_dir / "rule_b_supervisor_state.json"),
            mtime_age_seconds(runs_dir / "schedule.csv"),
            mtime_age_seconds(runs_dir / "rule_b_supervisor_events.log"),
        ]
        if age is not None
    ]
    if not ages:
        return False, None
    threshold = max(DEFAULT_ACTIVE_HEARTBEAT_SECONDS, command_poll_seconds(latest) * 4)
    newest_age = min(ages)
    return newest_age <= threshold, newest_age


def main() -> None:
    args = parse_args()
    latest = {}
    if args.latest_json.exists():
        latest = json.loads(args.latest_json.read_text(encoding="utf-8"))
    active_run = {}
    if args.active_run_json.exists():
        active_run = json.loads(args.active_run_json.read_text(encoding="utf-8"))
    runs_dir = args.runs_dir or Path(str(latest.get("runs_dir") or ""))
    print(f"latest_json={args.latest_json}")
    print(f"active_run_json={args.active_run_json}")
    print(f"active_run_dir={active_run.get('runs_dir') or ''}")
    print(f"active_run_status={active_run.get('status') or ''}")
    print(f"runs_dir={runs_dir if str(runs_dir) else ''}")
    pid = int(latest.get("pid") or 0)
    unit_name = str(latest.get("unit_name") or "")
    tmux_session = str(latest.get("tmux_session") or "")
    screen_session = str(latest.get("screen_session") or "")
    print(f"mode={latest.get('mode')}")
    print(f"supervisor_pid={pid}")
    print(f"supervisor_alive={pid_alive(pid)}")
    print(f"unit_name={unit_name}")
    unit_state = read_systemd_unit_state(unit_name)
    if unit_state:
        print(f"unit_active={unit_state.get('ActiveState')} unit_sub={unit_state.get('SubState')} unit_main_pid={unit_state.get('MainPID')} unit_result={unit_state.get('Result')}")
    print(f"tmux_session={tmux_session}")
    print(f"tmux_alive={tmux_session_alive(tmux_session)}")
    print(f"screen_session={screen_session}")
    print(f"screen_alive={screen_session_alive(screen_session)}")
    heartbeat_recent = False
    heartbeat_age = None
    if str(runs_dir):
        heartbeat_recent, heartbeat_age = recent_file_heartbeat(runs_dir, latest)
    effective_active = (
        pid_alive(pid)
        or (unit_state and unit_state.get("ActiveState") in {"active", "activating", "reloading"})
        or tmux_session_alive(tmux_session)
        or screen_session_alive(screen_session)
        or heartbeat_recent
    )
    print(f"file_heartbeat_recent={heartbeat_recent}")
    print(f"file_heartbeat_age_seconds={heartbeat_age if heartbeat_age is not None else ''}")
    print(f"effective_active={bool(effective_active)}")

    state_path = runs_dir / "rule_b_supervisor_state.json" if str(runs_dir) else Path("")
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        print(f"phase={state.get('phase')}")
        print(f"status_counts={state.get('status_counts')}")
        print(f"updated_at={state.get('updated_at')}")
    schedule_rows = read_csv(runs_dir / "schedule.csv") if str(runs_dir) else []
    if schedule_rows:
        counts: dict[str, int] = {}
        schedule_result_rows = 0
        live_result_rows = 0
        latest_worker_log_age: int | None = None
        latest_result_age: int | None = None
        running_full_rows = 0
        quota_blocked_rows = 0
        for row in schedule_rows:
            counts[row.get("status", "")] = counts.get(row.get("status", ""), 0) + 1
            if row.get("status") == "quota_blocked":
                quota_blocked_rows += 1
            schedule_result_rows += int(row.get("last_row_count") or "0")
            live_rows_for_batch = count_csv_rows(row.get("rule_b_results_csv", ""))
            live_result_rows += live_rows_for_batch
            if row.get("status") == "running" and live_rows_for_batch >= int(row.get("task_count") or "0"):
                running_full_rows += 1
            worker_log_age = mtime_age_seconds(Path(row.get("worker_log", ""))) if row.get("worker_log") else None
            result_age = mtime_age_seconds(Path(row.get("rule_b_results_csv", ""))) if row.get("rule_b_results_csv") else None
            if worker_log_age is not None:
                latest_worker_log_age = worker_log_age if latest_worker_log_age is None else min(latest_worker_log_age, worker_log_age)
            if result_age is not None:
                latest_result_age = result_age if latest_result_age is None else min(latest_result_age, result_age)
        print(f"total_batches={len(schedule_rows)}")
        print(f"schedule_status_counts={counts}")
        print(f"run_local_rule_b_rows={schedule_result_rows}")
        print(f"run_local_rule_b_live_rows={live_result_rows}")
        print(f"quota_blocked_batches={quota_blocked_rows}")
        print(f"running_batches_with_full_live_rows={running_full_rows}")
        print(f"latest_worker_log_age_seconds={latest_worker_log_age if latest_worker_log_age is not None else ''}")
        print(f"latest_result_age_seconds={latest_result_age if latest_result_age is not None else ''}")
        possible_liveness_stall = (
            running_full_rows > 0
            and counts.get("running", 0) == running_full_rows
            and latest_worker_log_age is not None
            and latest_worker_log_age > 120
        )
        print(f"possible_completed_worker_liveness_stall={possible_liveness_stall}")
        for row in schedule_rows[:10]:
            if row.get("status") in {"running", "retry_capped", "quota_blocked"}:
                live_rows = count_csv_rows(row.get("rule_b_results_csv", ""))
                print(
                    f"batch={Path(row.get('batch_file','')).name} status={row.get('status')} "
                    f"attempt={row.get('attempt_index')} rows={row.get('last_row_count')}/{row.get('task_count')} "
                    f"live_rows={live_rows}/{row.get('task_count')} "
                    f"failure={row.get('last_failure_type')}"
                )

    final_rows = read_csv(DEFAULT_FINAL_RESULTS)
    completed = sum(1 for row in final_rows if (row.get("include_rule_B") or "").strip() in {"yes", "no"})
    pending = sum(1 for row in final_rows if (row.get("include_rule_B") or "").strip() == "pending")
    print(f"final_rule_b_completed={completed}")
    print(f"final_rule_b_pending={pending}")


if __name__ == "__main__":
    main()
