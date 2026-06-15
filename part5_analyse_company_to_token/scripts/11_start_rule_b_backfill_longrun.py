#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_DIR.parent
DEFAULT_BATCH_DIR = PART5_DIR / "agent_task_batches" / "crypto_company_rule_b_backfill"
DEFAULT_RUNS_PARENT_DIR = PART5_DIR / "agent_runs"
DEFAULT_LATEST_JSON = PART5_DIR / "agent_runs" / "crypto_company_rule_b_longrun_latest.json"
DEFAULT_ACTIVE_RUN_JSON = PART5_DIR / "agent_runs" / "crypto_company_rule_b_active_run.json"
DEFAULT_CODEX_BIN = shutil.which("codex") or "/home/benl66/bin/codex"
DEFAULT_SYSTEMD_RUN_BIN = "systemd-run"
DEFAULT_WORKERS = 8
DEFAULT_DETACHED_STARTUP_WAIT_SECONDS = 15
DEFAULT_ACTIVE_HEARTBEAT_SECONDS = 300
SYSTEMD_RUNNING_STATES = {"active", "activating", "reloading"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start the Part5 Rule B-only backfill supervisor as a detached longrun.")
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--runs-parent-dir", type=Path, default=DEFAULT_RUNS_PARENT_DIR)
    parser.add_argument("--latest-json", type=Path, default=DEFAULT_LATEST_JSON)
    parser.add_argument("--active-run-json", type=Path, default=DEFAULT_ACTIVE_RUN_JSON)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--max-batch-restarts", type=int, default=3)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--startup-no-row-timeout-seconds", type=int, default=900)
    parser.add_argument("--partial-stall-timeout-seconds", type=int, default=1800)
    parser.add_argument("--batch-timeout-seconds", type=int, default=10800)
    parser.add_argument("--codex-bin", default=DEFAULT_CODEX_BIN)
    parser.add_argument("--model", default="gpt-5.5")
    parser.add_argument("--reasoning-effort", default="xhigh")
    parser.add_argument(
        "--launcher-mode",
        choices=["auto", "systemd", "tmux", "screen", "foreground"],
        default="auto",
        help="Longrun launcher. auto tries systemd, then tmux, then screen.",
    )
    parser.add_argument("--force-restart", action="store_true", help="Override a recent active heartbeat and supersede the prior active run.")
    return parser.parse_args()


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def read_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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


def systemd_unit_bootstrapped(unit_name: str, *, timeout_seconds: int = DEFAULT_DETACHED_STARTUP_WAIT_SECONDS) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        state = read_systemd_unit_state(unit_name)
        active_state = str((state or {}).get("ActiveState") or "").strip()
        if active_state in SYSTEMD_RUNNING_STATES:
            return True
        time.sleep(0.5)
    return False


def wait_for_supervisor_bootstrap(runs_dir: Path, *, timeout_seconds: int = DEFAULT_DETACHED_STARTUP_WAIT_SECONDS) -> bool:
    state_path = runs_dir / "rule_b_supervisor_state.json"
    events_path = runs_dir / "rule_b_supervisor_events.log"
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if state_path.exists() or events_path.exists():
            return True
        time.sleep(0.5)
    return False


def ensure_no_active_job(latest_path: Path, active_run_path: Path, *, force_restart: bool) -> None:
    if force_restart:
        return
    active_run = read_json(active_run_path)
    if active_run:
        runs_dir = Path(str(active_run.get("runs_dir") or ""))
        if recent_run_heartbeat(runs_dir, active_run):
            raise SystemExit(f"Rule B backfill already active by active-run heartbeat: runs_dir={runs_dir}")
    latest = read_json(latest_path)
    if not latest:
        return
    pid = latest.get("pid")
    if isinstance(pid, int) and is_pid_running(pid):
        raise SystemExit(f"Rule B backfill already active: pid={pid} runs_dir={latest.get('runs_dir')}")
    unit_name = str(latest.get("unit_name") or "").strip()
    unit_state = read_systemd_unit_state(unit_name)
    if unit_state and str(unit_state.get("ActiveState") or "").strip() in SYSTEMD_RUNNING_STATES:
        raise SystemExit(f"Rule B backfill already active: unit={unit_name} runs_dir={latest.get('runs_dir')}")
    runs_dir = Path(str(latest.get("runs_dir") or ""))
    if latest.get("status") == "running" and recent_run_heartbeat(runs_dir, latest):
        raise SystemExit(f"Rule B backfill appears active by recent heartbeat: runs_dir={runs_dir}")


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


def recent_run_heartbeat(runs_dir: Path, latest: dict[str, object]) -> bool:
    if not runs_dir.exists():
        return False
    threshold = max(DEFAULT_ACTIVE_HEARTBEAT_SECONDS, command_poll_seconds(latest) * 4)
    now = time.time()
    for name in ["rule_b_supervisor_state.json", "schedule.csv", "rule_b_supervisor_events.log"]:
        path = runs_dir / name
        if path.exists() and now - path.stat().st_mtime <= threshold:
            return True
    return False


def active_run_payload(latest: dict[str, object]) -> dict[str, object]:
    return {
        "kind": "part5_rule_b_active_run",
        "status": latest.get("status"),
        "launched_at": latest.get("launched_at"),
        "runs_dir": latest.get("runs_dir"),
        "batch_dir": latest.get("batch_dir"),
        "workers": latest.get("workers"),
        "max_batch_restarts": latest.get("max_batch_restarts"),
        "model": latest.get("model"),
        "reasoning_effort": latest.get("reasoning_effort"),
        "latest_json": latest.get("latest_json"),
    }


def write_active_run(path: Path, latest: dict[str, object]) -> None:
    write_json(path, active_run_payload(latest))


def update_active_run_status(path: Path, runs_dir: Path, status: str) -> None:
    active = read_json(path)
    if not active:
        return
    if Path(str(active.get("runs_dir") or "")).resolve() != runs_dir.resolve():
        return
    active["status"] = status
    active["updated_at"] = datetime.now(timezone.utc).isoformat()
    write_json(path, active)


def build_systemd_unit_name(*, ts: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.@-]+", "-", ts).lower()
    return f"crypto-company-rule-b-backfill-{normalized}"


def build_session_name(*, ts: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_.@-]+", "-", ts).lower()
    return f"part5_rule_b_{normalized}"


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def run_in_tmux(session_name: str, command: list[str], stdout_log: Path) -> subprocess.CompletedProcess[str]:
    tmux_bin = shutil.which("tmux")
    if not tmux_bin:
        return subprocess.CompletedProcess(["tmux"], 127, "", "tmux is not available")
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


def run_in_screen(session_name: str, command: list[str], stdout_log: Path) -> subprocess.CompletedProcess[str]:
    screen_bin = shutil.which("screen")
    if not screen_bin:
        return subprocess.CompletedProcess(["screen"], 127, "", "screen is not available")
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


def main() -> None:
    args = parse_args()
    if not args.batch_dir.exists():
        raise SystemExit(f"Rule B batch directory does not exist: {args.batch_dir}")
    ensure_no_active_job(args.latest_json, args.active_run_json, force_restart=args.force_restart)
    runs_dir = args.runs_parent_dir / f"crypto_company_rule_b_backfill_{timestamp()}"
    runs_dir.mkdir(parents=True, exist_ok=True)
    live_log = runs_dir / "supervisor_live.log"
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "10_run_rule_b_backfill_supervisor.py"),
        "--batch-dir",
        str(args.batch_dir),
        "--runs-dir",
        str(runs_dir),
        "--workers",
        str(args.workers),
        "--max-batch-restarts",
        str(args.max_batch_restarts),
        "--poll-seconds",
        str(args.poll_seconds),
        "--startup-no-row-timeout-seconds",
        str(args.startup_no_row_timeout_seconds),
        "--partial-stall-timeout-seconds",
        str(args.partial_stall_timeout_seconds),
        "--batch-timeout-seconds",
        str(args.batch_timeout_seconds),
        "--codex-bin",
        str(args.codex_bin),
        "--model",
        args.model,
        "--reasoning-effort",
        args.reasoning_effort,
    ]
    ts = runs_dir.name.rsplit("_", 1)[-1]
    unit_name = build_systemd_unit_name(ts=ts)
    session_name = build_session_name(ts=ts)
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
        *cmd,
    ]
    latest = {
        "kind": "part5_rule_b_backfill",
        "status": "running",
        "launched_at": datetime.now(timezone.utc).isoformat(),
        "pid": 0,
        "unit_name": unit_name,
        "runs_dir": str(runs_dir),
        "batch_dir": str(args.batch_dir),
        "workers": args.workers,
        "max_batch_restarts": args.max_batch_restarts,
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "live_log": str(live_log),
        "command": cmd,
        "systemd_command": systemd_cmd,
        "latest_json": str(args.latest_json),
        "active_run_json": str(args.active_run_json),
        "force_restart": args.force_restart,
        "mode": "detached_pending",
    }

    completed: subprocess.CompletedProcess[str] | None = None
    mode = ""
    errors: list[str] = []
    if args.launcher_mode in {"auto", "systemd"} and systemd_run_available():
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
        with live_log.open("a", encoding="utf-8") as log:
            log.write(completed.stdout)
            log.write(completed.stderr)
        if completed.returncode == 0 and systemd_unit_bootstrapped(unit_name):
            mode = "detached_systemd"
        else:
            errors.append(f"systemd returncode={completed.returncode} stderr={completed.stderr.strip()!r}")
            if args.launcher_mode == "systemd":
                latest["status"] = "launch_failed"
                latest["systemd_stdout"] = completed.stdout
                latest["systemd_stderr"] = completed.stderr
                write_json(runs_dir / "launcher_state.json", latest)
                write_json(args.latest_json, latest)
                raise SystemExit(f"systemd-run failed or did not bootstrap: unit={unit_name}")

    if not mode and args.launcher_mode in {"auto", "tmux"}:
        completed = run_in_tmux(session_name, cmd, live_log)
        if completed.returncode == 0:
            mode = "tmux_watchdog"
        else:
            errors.append(f"tmux returncode={completed.returncode} stderr={completed.stderr.strip()!r}")
            if args.launcher_mode == "tmux":
                raise SystemExit(completed.returncode)

    if not mode and args.launcher_mode in {"auto", "screen"}:
        completed = run_in_screen(session_name, cmd, live_log)
        if completed.returncode == 0:
            mode = "screen_watchdog"
        else:
            errors.append(f"screen returncode={completed.returncode} stderr={completed.stderr.strip()!r}")
            if args.launcher_mode == "screen":
                raise SystemExit(completed.returncode)

    if not mode and args.launcher_mode == "foreground":
        latest["status"] = "running"
        latest["mode"] = "foreground"
        latest["tmux_session"] = None
        latest["screen_session"] = None
        latest["unit_name"] = None
        latest["launch_errors"] = errors
        write_json(runs_dir / "launcher_state.json", latest)
        write_json(args.latest_json, latest)
        write_active_run(args.active_run_json, latest)
        print("mode=foreground")
        print("unit=")
        print("session=")
        print(f"runs_dir={runs_dir}")
        print(f"live_log={live_log}")
        print(f"latest_json={args.latest_json}")
        sys.stdout.flush()
        with live_log.open("a", encoding="utf-8") as log:
            process = subprocess.Popen(cmd, cwd=REPO_ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
            latest["pid"] = process.pid
            write_json(runs_dir / "launcher_state.json", latest)
            write_json(args.latest_json, latest)
            returncode = process.wait()
        mode = "foreground"
        latest["status"] = "completed" if returncode == 0 else "failed"
        latest["returncode"] = returncode
        write_json(runs_dir / "launcher_state.json", latest)
        write_json(args.latest_json, latest)
        update_active_run_status(args.active_run_json, runs_dir, str(latest["status"]))
        if returncode != 0:
            raise SystemExit(returncode)
        return

    if not mode:
        latest["status"] = "launch_failed"
        latest["launch_errors"] = errors
        write_json(runs_dir / "launcher_state.json", latest)
        write_json(args.latest_json, latest)
        raise SystemExit("Unable to launch Rule B longrun with systemd, tmux, or screen.")

    latest["status"] = "running"
    latest["mode"] = mode
    latest["tmux_session"] = session_name if mode == "tmux_watchdog" else None
    latest["screen_session"] = session_name if mode == "screen_watchdog" else None
    latest["unit_name"] = unit_name if mode == "detached_systemd" else None
    latest["launch_errors"] = errors
    write_json(runs_dir / "launcher_state.json", latest)
    write_json(args.latest_json, latest)
    write_active_run(args.active_run_json, latest)
    wait_for_supervisor_bootstrap(runs_dir)
    print(f"mode={mode}")
    print(f"unit={latest.get('unit_name') or ''}")
    print(f"session={session_name if mode in {'tmux_watchdog', 'screen_watchdog'} else ''}")
    print(f"runs_dir={runs_dir}")
    print(f"live_log={live_log}")
    print(f"latest_json={args.latest_json}")


if __name__ == "__main__":
    main()
