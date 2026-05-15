#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent

DEFAULT_BATCH_DIR = PART6_DIR / "agent_task_batches" / "crypto_investor"
DEFAULT_RUNS_PARENT_DIR = PART6_DIR / "agent_runs"
DEFAULT_FINAL_RESULTS_CSV = PART6_DIR / "agent_runs" / "crypto_investor" / "results.csv"
DEFAULT_RUN_PREFIX = "crypto_investor_parallel_eval"
DEFAULT_LIVE_LOG_NAME = "supervisor_live.log"
DEFAULT_LATEST_JOB_JSON = PART6_DIR / "agent_runs" / "crypto_investor_longrun_latest.json"
DEFAULT_SPLIT_BATCH_RESPAWN_THRESHOLD = 3
DEFAULT_SPLIT_BATCH_FAILURE_THRESHOLD = 2
DEFAULT_STARTUP_TIMEOUT_SECONDS = 480
DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS = 240
DEFAULT_POLL_SECONDS = 30
DEFAULT_BATCH_TIMEOUT_SECONDS = 7200
DEFAULT_NOHUP_BIN = "nohup"
DEFAULT_SYSTEMD_RUN_BIN = "systemd-run"
DEFAULT_CODEX_BIN = shutil.which("codex") or "codex"
DEFAULT_DETACHED_STARTUP_WAIT_SECONDS = 15
SYSTEMD_RUNNING_STATES = {"active", "activating", "reloading"}

BATCH_FILE_RE = re.compile(r"batch_(\d+)\.jsonl$")


@dataclass(frozen=True)
class BatchMeta:
    number: int
    path: Path
    first_task_index: int
    last_task_index: int
    first_company: str
    last_company: str
    task_indices: tuple[int, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prepare the next missing crypto-company batch window and launch the round "
            "supervisor as a detached long-running process. Detached mode prefers "
            "systemd-run --user and falls back to nohup plus a new session."
        )
    )
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--runs-parent-dir", type=Path, default=DEFAULT_RUNS_PARENT_DIR)
    parser.add_argument("--final-results-csv", type=Path, default=DEFAULT_FINAL_RESULTS_CSV)
    parser.add_argument("--latest-job-json", type=Path, default=DEFAULT_LATEST_JOB_JSON)
    parser.add_argument("--run-prefix", default=DEFAULT_RUN_PREFIX)
    parser.add_argument("--round-count", type=int, default=10)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument(
        "--scheduler-mode",
        choices=["round", "queue"],
        default="round",
        help="Execution scheduler. `round` preserves the old round barrier; `queue` keeps slots full and collects completed batches independently.",
    )
    parser.add_argument("--start-batch", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--allow-parallel", action="store_true")
    parser.add_argument("--foreground", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument(
        "--batch-timeout-seconds",
        type=int,
        default=DEFAULT_BATCH_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--startup-no-row-timeout-seconds",
        type=int,
        default=DEFAULT_STARTUP_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--partial-stall-timeout-seconds",
        type=int,
        default=DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--split-batch-respawn-threshold",
        type=int,
        default=DEFAULT_SPLIT_BATCH_RESPAWN_THRESHOLD,
    )
    parser.add_argument(
        "--split-batch-failure-threshold",
        type=int,
        default=DEFAULT_SPLIT_BATCH_FAILURE_THRESHOLD,
    )
    return parser.parse_args()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def read_final_task_indices(path: Path) -> set[int]:
    task_indices: set[int] = set()
    if not path.exists():
        return task_indices
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            task_index = (row.get("task_index") or "").strip()
            if task_index:
                task_indices.add(int(task_index))
    return task_indices


def load_batch_meta(path: Path) -> BatchMeta:
    task_indices: list[int] = []
    first_company = ""
    last_company = ""
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            task_index = int(record["task_index"])
            investor_name = str(record.get("investor_name") or "")
            task_indices.append(task_index)
            if not first_company:
                first_company = investor_name
            last_company = investor_name
    if not task_indices:
        raise SystemExit(f"Batch file is empty: {path}")
    match = BATCH_FILE_RE.search(path.name)
    if not match:
        raise SystemExit(f"Unrecognized batch filename: {path.name}")
    return BatchMeta(
        number=int(match.group(1)),
        path=path,
        first_task_index=min(task_indices),
        last_task_index=max(task_indices),
        first_company=first_company,
        last_company=last_company,
        task_indices=tuple(task_indices),
    )


def load_all_batches(batch_dir: Path) -> list[BatchMeta]:
    metas: list[BatchMeta] = []
    for path in sorted(batch_dir.glob("batch_*.jsonl")):
        metas.append(load_batch_meta(path))
    if not metas:
        raise SystemExit(f"No batch_*.jsonl files found in {batch_dir}")
    return metas


def first_missing_batch_number(batch_metas: list[BatchMeta], completed_task_indices: set[int]) -> int | None:
    for meta in batch_metas:
        if any(task_index not in completed_task_indices for task_index in meta.task_indices):
            return meta.number
    return None


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def resolve_codex_bin(binary: str) -> str:
    candidate = str(binary or "").strip()
    if not candidate:
        raise SystemExit("codex binary path is empty.")
    expanded = Path(candidate).expanduser()
    if expanded.is_absolute():
        if expanded.exists():
            return str(expanded.resolve())
        raise SystemExit(f"codex binary not found: {candidate}")
    resolved = shutil.which(candidate)
    if resolved:
        return str(Path(resolved).resolve())
    raise SystemExit(f"codex binary not found: {candidate}")


def systemd_run_available() -> bool:
    return shutil.which(DEFAULT_SYSTEMD_RUN_BIN) is not None


def read_systemd_unit_state(unit_name: str) -> dict[str, str] | None:
    if not unit_name:
        return None
    cmd = [
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


def wait_for_supervisor_bootstrap(runs_dir: Path, *, timeout_seconds: int = DEFAULT_DETACHED_STARTUP_WAIT_SECONDS) -> bool:
    state_path = runs_dir / "supervisor_state.json"
    events_path = runs_dir / "supervisor_events.log"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if state_path.exists() or events_path.exists():
            return True
        time.sleep(0.5)
    return False


def systemd_unit_bootstrapped(unit_name: str, *, timeout_seconds: int = DEFAULT_DETACHED_STARTUP_WAIT_SECONDS) -> bool:
    if not unit_name:
        return False
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = read_systemd_unit_state(unit_name)
        active_state = str((state or {}).get("ActiveState") or "").strip()
        if active_state in SYSTEMD_RUNNING_STATES:
            return True
        time.sleep(0.5)
    return False


def read_latest_job(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def ensure_no_active_job(path: Path, *, allow_parallel: bool) -> None:
    latest = read_latest_job(path)
    if not latest or allow_parallel:
        return
    pid = latest.get("pid")
    if isinstance(pid, int) and is_pid_running(pid):
        raise SystemExit(
            "A detached long-running job is still active. "
            f"pid={pid} run_dir={latest.get('runs_dir')} "
            "Use --allow-parallel only if you intentionally want another concurrent job."
        )
    unit_name = str(latest.get("unit_name") or "").strip()
    unit_state = read_systemd_unit_state(unit_name)
    if unit_state and str(unit_state.get("ActiveState") or "").strip() in SYSTEMD_RUNNING_STATES:
        raise SystemExit(
            "A detached long-running systemd unit is still active. "
            f"unit={unit_name} run_dir={latest.get('runs_dir')} "
            "Use --allow-parallel only if you intentionally want another concurrent job."
        )


def run_prepare(
    *,
    batch_dir: Path,
    runs_dir: Path,
    workers: int,
    start_batch: int,
    limit_batches: int,
    force: bool,
) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "2_prepare_worker_runs.py"),
        "--batch-dir",
        str(batch_dir),
        "--runs-dir",
        str(runs_dir),
        "--workers",
        str(workers),
        "--start-batch",
        str(start_batch),
        "--limit-batches",
        str(limit_batches),
    ]
    if force:
        cmd.append("--force")
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def build_supervisor_command(
    *,
    runs_dir: Path,
    round_count: int,
    workers: int,
    scheduler_mode: str,
    poll_seconds: int,
    batch_timeout_seconds: int,
    startup_timeout_seconds: int,
    partial_stall_timeout_seconds: int,
    split_batch_respawn_threshold: int,
    split_batch_failure_threshold: int,
    codex_bin: str,
) -> list[str]:
    supervisor_script = "5_run_queue_supervisor.py" if scheduler_mode == "queue" else "5_run_round_supervisor.py"
    return [
        sys.executable,
        str(SCRIPT_DIR / supervisor_script),
        "--runs-dir",
        str(runs_dir),
        "--start-round-index",
        "1",
        "--round-count",
        str(round_count),
        *(
            ["--max-workers", str(workers)]
            if scheduler_mode == "queue"
            else []
        ),
        "--poll-seconds",
        str(poll_seconds),
        "--batch-timeout-seconds",
        str(batch_timeout_seconds),
        "--startup-no-row-timeout-seconds",
        str(startup_timeout_seconds),
        "--partial-stall-timeout-seconds",
        str(partial_stall_timeout_seconds),
        "--codex-bin",
        codex_bin,
        "--split-batch-respawn-threshold",
        str(split_batch_respawn_threshold),
        "--split-batch-failure-threshold",
        str(split_batch_failure_threshold),
    ]


def build_systemd_unit_name(*, timestamp: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.@-]+", "-", timestamp).lower()
    return f"crypto-company-longrun-{normalized}"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.round_count <= 0:
        raise SystemExit("--round-count must be greater than 0.")
    if args.workers <= 0:
        raise SystemExit("--workers must be greater than 0.")
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be greater than 0.")

    batch_dir = args.batch_dir.resolve()
    runs_parent_dir = args.runs_parent_dir.resolve()
    final_results_csv = args.final_results_csv.resolve()
    latest_job_json = args.latest_job_json.resolve()
    codex_bin = resolve_codex_bin(DEFAULT_CODEX_BIN)
    runs_parent_dir.mkdir(parents=True, exist_ok=True)
    latest_job_json.parent.mkdir(parents=True, exist_ok=True)

    ensure_no_active_job(latest_job_json, allow_parallel=args.allow_parallel)

    batch_metas = load_all_batches(batch_dir)
    completed_task_indices = read_final_task_indices(final_results_csv)
    start_batch = args.start_batch or first_missing_batch_number(batch_metas, completed_task_indices)
    if start_batch is None:
        print("No remaining missing batches detected from final results.csv; nothing to launch.")
        return

    batch_count = args.round_count * args.workers
    selected = [meta for meta in batch_metas if meta.number >= start_batch][:batch_count]
    if not selected:
        raise SystemExit(f"No batches available at or after batch_{start_batch:04d}.")

    actual_batch_count = len(selected)
    actual_round_count = math.ceil(actual_batch_count / args.workers)
    first_meta = selected[0]
    last_meta = selected[-1]

    timestamp = utc_timestamp()
    runs_dir = runs_parent_dir / f"{args.run_prefix}_{actual_round_count}rounds_{timestamp}"
    run_prepare(
        batch_dir=batch_dir,
        runs_dir=runs_dir,
        workers=args.workers,
        start_batch=first_meta.number,
        limit_batches=actual_batch_count,
        force=args.force,
    )

    supervisor_cmd = build_supervisor_command(
        runs_dir=runs_dir,
        round_count=actual_round_count,
        workers=args.workers,
        scheduler_mode=args.scheduler_mode,
        poll_seconds=args.poll_seconds,
        batch_timeout_seconds=args.batch_timeout_seconds,
        startup_timeout_seconds=args.startup_no_row_timeout_seconds,
        partial_stall_timeout_seconds=args.partial_stall_timeout_seconds,
        split_batch_respawn_threshold=args.split_batch_respawn_threshold,
        split_batch_failure_threshold=args.split_batch_failure_threshold,
        codex_bin=codex_bin,
    )

    log_path = runs_dir / DEFAULT_LIVE_LOG_NAME
    log_handle = log_path.open("a", encoding="utf-8")
    log_handle.write(
        f"{utc_now().isoformat()} launching detached supervisor for batches "
        f"{first_meta.number:04d}-{last_meta.number:04d}\n"
    )
    log_handle.flush()

    launcher_state = {
        "launched_at": utc_now().isoformat(),
        "runs_dir": str(runs_dir),
        "schedule_csv": str((runs_dir / "schedule.csv").resolve()),
        "events_log": str((runs_dir / "supervisor_events.log").resolve()),
        "state_json": str((runs_dir / "supervisor_state.json").resolve()),
        "registry_json": str((runs_dir / "supervisor_registry.json").resolve()),
        "live_log": str(log_path.resolve()),
        "start_batch": first_meta.number,
        "end_batch": last_meta.number,
        "first_task_index": first_meta.first_task_index,
        "last_task_index": last_meta.last_task_index,
        "batch_count": actual_batch_count,
        "workers": args.workers,
        "scheduler_mode": args.scheduler_mode,
        "round_count_requested": args.round_count,
        "round_count_actual": actual_round_count,
        "batch_timeout_seconds": args.batch_timeout_seconds,
        "split_batch_respawn_threshold": args.split_batch_respawn_threshold,
        "split_batch_failure_threshold": args.split_batch_failure_threshold,
        "codex_bin": codex_bin,
        "command": supervisor_cmd,
        "mode": "foreground" if args.foreground else "detached",
    }

    if args.foreground:
        write_json(runs_dir / "launcher_state.json", launcher_state)
        write_json(latest_job_json, launcher_state)
        try:
            completed = subprocess.run(supervisor_cmd, cwd=REPO_ROOT, check=False)
        finally:
            log_handle.close()
        if completed.returncode != 0:
            raise SystemExit(completed.returncode)
        return

    unit_name = build_systemd_unit_name(timestamp=timestamp)
    launcher_state["unit_name"] = unit_name

    systemd_cmd = [
        DEFAULT_SYSTEMD_RUN_BIN,
        "--user",
        "--unit",
        unit_name,
        "--same-dir",
        "--collect",
        "-p",
        f"WorkingDirectory={REPO_ROOT}",
        "-p",
        "Restart=on-failure",
        "-p",
        "RestartSec=15s",
        *supervisor_cmd,
    ]
    launcher_state["systemd_command"] = systemd_cmd

    if systemd_run_available():
        completed = subprocess.run(
            systemd_cmd,
            cwd=REPO_ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode == 0 and systemd_unit_bootstrapped(unit_name):
            launcher_state["pid"] = 0
            launcher_state["status"] = "running"
            launcher_state["mode"] = "detached_systemd"
            write_json(runs_dir / "launcher_state.json", launcher_state)
            write_json(latest_job_json, launcher_state)
            log_handle.write(completed.stdout)
            if completed.stderr:
                log_handle.write(completed.stderr)
            log_handle.flush()
            log_handle.close()

            if not wait_for_supervisor_bootstrap(runs_dir):
                print(f"Detached supervisor launched via systemd-run: unit={unit_name}")
                print(f"Runs dir: {runs_dir}")
                print(f"Batch window: batch_{first_meta.number:04d} -> batch_{last_meta.number:04d}")
                print(f"Task window: {first_meta.first_task_index} -> {last_meta.last_task_index}")
                print(f"Schedule CSV: {runs_dir / 'schedule.csv'}")
                print(f"Supervisor state: {runs_dir / 'supervisor_state.json'}")
                print(f"Supervisor events: {runs_dir / 'supervisor_events.log'}")
                print(f"Live log: {log_path}")
                print(f"Latest job JSON: {latest_job_json}")
                return

            print(f"Detached supervisor launched via systemd-run: unit={unit_name}")
            print(f"Runs dir: {runs_dir}")
            print(f"Batch window: batch_{first_meta.number:04d} -> batch_{last_meta.number:04d}")
            print(f"Task window: {first_meta.first_task_index} -> {last_meta.last_task_index}")
            print(f"Schedule CSV: {runs_dir / 'schedule.csv'}")
            print(f"Supervisor state: {runs_dir / 'supervisor_state.json'}")
            print(f"Supervisor events: {runs_dir / 'supervisor_events.log'}")
            print(f"Live log: {log_path}")
            print(f"Latest job JSON: {latest_job_json}")
            return

        log_handle.write("systemd-run launch failed or unit did not bootstrap; falling back to nohup\n")
        log_handle.write(completed.stdout)
        log_handle.write(completed.stderr)
        log_handle.flush()

    detached_cmd = [DEFAULT_NOHUP_BIN, *supervisor_cmd]
    shell_cmd = (
        "nohup "
        + " ".join(shlex.quote(part) for part in supervisor_cmd)
        + f" >> {shlex.quote(str(log_path))} 2>&1 < /dev/null & echo $!"
    )
    launcher_state["detached_command"] = detached_cmd
    launcher_state["detached_shell_command"] = shell_cmd
    launcher_state["mode"] = "detached_nohup"

    completed = subprocess.run(
        ["/bin/bash", "-lc", shell_cmd],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        log_handle.write(completed.stdout)
        log_handle.write(completed.stderr)
        log_handle.flush()
        log_handle.close()
        raise SystemExit(f"Failed to launch detached supervisor with nohup: returncode={completed.returncode}")

    pid_text = (completed.stdout or "").strip().splitlines()[-1].strip() if (completed.stdout or "").strip() else ""
    launcher_state["pid"] = int(pid_text) if pid_text.isdigit() else 0
    launcher_state["status"] = "running" if launcher_state["pid"] else "launched_pid_unknown"
    write_json(runs_dir / "launcher_state.json", launcher_state)
    write_json(latest_job_json, launcher_state)
    log_handle.flush()
    log_handle.close()

    if not wait_for_supervisor_bootstrap(runs_dir):
        launcher_state["status"] = "launch_failed_no_supervisor_state"
        write_json(runs_dir / "launcher_state.json", launcher_state)
        write_json(latest_job_json, launcher_state)
        raise SystemExit(
            "Detached supervisor launch did not create supervisor_state.json or supervisor_events.log "
            "within the startup wait window."
        )

    print(f"Detached supervisor started: pid={launcher_state['pid']}")
    print(f"Runs dir: {runs_dir}")
    print(f"Batch window: batch_{first_meta.number:04d} -> batch_{last_meta.number:04d}")
    print(f"Task window: {first_meta.first_task_index} -> {last_meta.last_task_index}")
    print(f"Schedule CSV: {runs_dir / 'schedule.csv'}")
    print(f"Supervisor state: {runs_dir / 'supervisor_state.json'}")
    print(f"Supervisor events: {runs_dir / 'supervisor_events.log'}")
    print(f"Live log: {log_path}")
    print(f"Latest job JSON: {latest_job_json}")


if __name__ == "__main__":
    main()
