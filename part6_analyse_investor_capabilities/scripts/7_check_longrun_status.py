#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
DEFAULT_LATEST_JOB_JSON = PART6_DIR / "agent_runs" / "crypto_investor_longrun_latest.json"
DEFAULT_EVENTS_TAIL = 20
DEFAULT_RUNNING_GRACE_SECONDS = 180
DEFAULT_HEARTBEAT_GRACE_SECONDS = 900
DEFAULT_HOST_STATE_JSON = "supervisor_host_state.json"
DEFAULT_HOST_EVENTS_LOG = "supervisor_host_events.log"
SYSTEMD_RUNNING_STATES = {"active", "activating", "reloading"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read the latest long-running crypto-investor supervisor metadata and report "
            "whether the job is still running, heartbeat freshness, backlog counts, "
            "active workers, and current running batch progress."
        )
    )
    parser.add_argument("--latest-job-json", type=Path, default=DEFAULT_LATEST_JOB_JSON)
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--events-tail", type=int, default=DEFAULT_EVENTS_TAIL)
    parser.add_argument("--heartbeat-grace-seconds", type=int, default=DEFAULT_HEARTBEAT_GRACE_SECONDS)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_pid_running(pid: object) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def path_mtime_utc(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def read_schedule_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_events_tail(path: Path, tail: int) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-tail:]


def parse_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except (TypeError, ValueError):
        return default


def parse_batch_number(batch_file: str) -> int:
    stem = Path(batch_file).stem
    try:
        return int(stem.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def collect_host_process_lines(runs_dir: Path | None) -> dict[str, object]:
    try:
        completed = subprocess.run(
            ["ps", "-ef"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return {
            "available": False,
            "scope": "unavailable",
            "lines": [],
        }

    current_pid = os.getpid()
    current_pid_text = f" {current_pid} "
    lines = []
    for line in completed.stdout.splitlines():
        if "part6_analyse_investor_capabilities" not in line and "crypto_investor" not in line:
            continue
        if "grep part6" in line:
            continue
        if current_pid_text in line:
            continue
        if "7_check_longrun_status.py" in line:
            continue
        lines.append(line)
    if not lines:
        return {
            "available": True,
            "scope": "part6",
            "lines": [],
        }

    if runs_dir is None:
        return {
            "available": True,
            "scope": "part6",
            "lines": lines,
        }

    run_name = runs_dir.name
    runs_dir_text = str(runs_dir)
    narrowed = [
        line
        for line in lines
        if run_name in line
        or runs_dir_text in line
    ]
    return {
        "available": True,
        "scope": "current_run",
        "lines": narrowed,
    }


def read_systemd_unit_status(unit_name: str) -> dict[str, object]:
    if not unit_name:
        return {
            "available": False,
            "queried": False,
            "unit_name": "",
            "error": "missing_unit_name",
        }
    try:
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
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return {
            "available": False,
            "queried": False,
            "unit_name": unit_name,
            "error": str(exc),
        }

    payload: dict[str, object] = {
        "available": True,
        "queried": completed.returncode == 0,
        "unit_name": unit_name,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    if completed.returncode != 0:
        return payload

    for line in completed.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key] = value
    return payload


def row_is_deferred_long_tail(row: dict[str, str]) -> bool:
    status = (row.get("status") or "").strip()
    completion_mode = (row.get("completion_mode") or "").strip()
    if status == "deferred_long_tail":
        return True
    if status == "completed":
        return False
    return completion_mode == "deferred_long_tail"


def effective_row_status(row: dict[str, str]) -> str:
    if row_is_deferred_long_tail(row):
        return "deferred_long_tail"
    return (row.get("status") or "").strip() or "unknown"


def row_is_resolved(row: dict[str, str]) -> bool:
    return effective_row_status(row) in {"completed", "deferred_long_tail"}


def row_has_open_queue_work(row: dict[str, str]) -> bool:
    status = effective_row_status(row)
    if status == "deferred_long_tail":
        return False
    if status == "completed" and str(row.get("collect_state") or "").strip() == "done":
        return False
    return True


def build_backlog_summary(schedule_rows: list[dict[str, str]]) -> dict[str, object]:
    waiting_rows: list[dict[str, str]] = []
    tail_retry_rows: list[dict[str, str]] = []
    collect_rows: list[dict[str, str]] = []
    deferred_rows: list[dict[str, str]] = []
    open_rounds: set[int] = set()

    for row in schedule_rows:
        round_index = parse_int(row.get("round_index"))
        if round_index <= 0:
            continue
        status = effective_row_status(row)
        queue_state = str(row.get("queue_state") or "").strip()
        collect_state = str(row.get("collect_state") or "").strip()
        if row_has_open_queue_work(row):
            open_rounds.add(round_index)
        if status in {"prepared", "needs_rerun"} and queue_state == "tail_retry_pending":
            tail_retry_rows.append(row)
        elif status in {"prepared", "needs_rerun"}:
            waiting_rows.append(row)
        if status == "completed" and collect_state != "done":
            collect_rows.append(row)
        if status == "deferred_long_tail":
            deferred_rows.append(row)

    def earliest_round(rows: list[dict[str, str]]) -> int | None:
        indexes = [parse_int(row.get("round_index")) for row in rows if parse_int(row.get("round_index")) > 0]
        return min(indexes) if indexes else None

    return {
        "earliest_open_round_index": min(open_rounds) if open_rounds else None,
        "waiting_count": len(waiting_rows),
        "waiting_earliest_round_index": earliest_round(waiting_rows),
        "tail_retry_count": len(tail_retry_rows),
        "tail_retry_earliest_round_index": earliest_round(tail_retry_rows),
        "collect_count": len(collect_rows),
        "collect_earliest_round_index": earliest_round(collect_rows),
        "deferred_count": len(deferred_rows),
        "deferred_earliest_round_index": earliest_round(deferred_rows),
    }


def active_slots_from_state(state: dict[str, object] | None) -> list[dict[str, object]]:
    if not isinstance(state, dict) or not isinstance(state.get("slots"), list):
        return []
    return [
        item
        for item in state["slots"]
        if isinstance(item, dict) and item.get("state") == "running" and item.get("batch_file")
    ]


def build_active_progress(
    *,
    state: dict[str, object] | None,
    schedule_rows: list[dict[str, str]],
) -> dict[str, object]:
    active_slots = active_slots_from_state(state)
    if active_slots:
        active_rounds = sorted({parse_int(item.get("round_index")) for item in active_slots if parse_int(item.get("round_index")) > 0})
        active_batch_numbers = sorted(
            {
                parse_batch_number(str(item.get("batch_file") or ""))
                for item in active_slots
                if parse_batch_number(str(item.get("batch_file") or "")) > 0
            }
        )
        return {
            "source": "supervisor_state.slots",
            "active_round_indexes": active_rounds,
            "active_round_min": active_rounds[0] if active_rounds else None,
            "active_round_max": active_rounds[-1] if active_rounds else None,
            "active_batch_min": active_batch_numbers[0] if active_batch_numbers else None,
            "active_batch_max": active_batch_numbers[-1] if active_batch_numbers else None,
            "active_batch_count": len(active_slots),
            "frontier_round_index": active_rounds[-1] if active_rounds else None,
            "frontier_batch_number": active_batch_numbers[-1] if active_batch_numbers else None,
        }

    running_rows = [row for row in schedule_rows if effective_row_status(row) == "running"]
    active_rounds = sorted({parse_int(row.get("round_index")) for row in running_rows if parse_int(row.get("round_index")) > 0})
    active_batch_numbers = sorted(
        {
            parse_batch_number(str(row.get("batch_file") or ""))
            for row in running_rows
            if parse_batch_number(str(row.get("batch_file") or "")) > 0
        }
    )
    return {
        "source": "schedule.running_rows",
        "active_round_indexes": active_rounds,
        "active_round_min": active_rounds[0] if active_rounds else None,
        "active_round_max": active_rounds[-1] if active_rounds else None,
        "active_batch_min": active_batch_numbers[0] if active_batch_numbers else None,
        "active_batch_max": active_batch_numbers[-1] if active_batch_numbers else None,
        "active_batch_count": len(running_rows),
        "frontier_round_index": active_rounds[-1] if active_rounds else None,
        "frontier_batch_number": active_batch_numbers[-1] if active_batch_numbers else None,
    }


def build_active_batches(
    *,
    state: dict[str, object] | None,
    schedule_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    row_by_batch = {str(row.get("batch_file") or ""): row for row in schedule_rows}
    output: list[dict[str, object]] = []
    active_slots = active_slots_from_state(state)
    if active_slots:
        for item in sorted(active_slots, key=lambda slot: parse_int(slot.get("slot_id"))):
            batch_file = str(item.get("batch_file") or "")
            row = row_by_batch.get(batch_file, {})
            output.append(
                {
                    "slot_id": parse_int(item.get("slot_id")),
                    "batch_file": batch_file,
                    "batch_number": parse_batch_number(batch_file),
                    "round_index": parse_int(item.get("round_index")),
                    "attempt_index": parse_int(item.get("attempt_index")),
                    "status": effective_row_status(row) if row else "running",
                    "queue_state": row.get("queue_state") or item.get("queue_state") or "",
                    "active_attempt": row.get("active_attempt") or "",
                    "classifier_rows": parse_int(row.get("last_seen_classifier_rows")),
                    "result_rows": parse_int(row.get("last_seen_result_rows")),
                    "task_count": parse_int(row.get("task_count")),
                    "split_recovery": bool(item.get("split_recovery")),
                    "pid_count": parse_int(item.get("pid_count")),
                    "prepared_reason": row.get("prepared_reason") or "",
                }
            )
        return output

    for row in schedule_rows:
        if effective_row_status(row) != "running":
            continue
        batch_file = str(row.get("batch_file") or "")
        output.append(
            {
                "slot_id": parse_int(row.get("slot_id")),
                "batch_file": batch_file,
                "batch_number": parse_batch_number(batch_file),
                "round_index": parse_int(row.get("round_index")),
                "attempt_index": parse_int(row.get("attempt_index")),
                "status": effective_row_status(row),
                "queue_state": row.get("queue_state") or "",
                "active_attempt": row.get("active_attempt") or "",
                "classifier_rows": parse_int(row.get("last_seen_classifier_rows")),
                "result_rows": parse_int(row.get("last_seen_result_rows")),
                "task_count": parse_int(row.get("task_count")),
                "split_recovery": False,
                "pid_count": 0,
                "prepared_reason": row.get("prepared_reason") or "",
            }
        )
    output.sort(key=lambda item: (parse_int(item.get("round_index")), parse_int(item.get("slot_id")), str(item.get("batch_file"))))
    return output


def stale_schedule_running_batches(
    *,
    state: dict[str, object] | None,
    schedule_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    active_batch_files = {str(item.get("batch_file") or "") for item in active_slots_from_state(state)}
    if not active_batch_files:
        return []
    stale: list[dict[str, object]] = []
    for row in schedule_rows:
        batch_file = str(row.get("batch_file") or "")
        if effective_row_status(row) != "running" or batch_file in active_batch_files:
            continue
        stale.append(
            {
                "batch_file": batch_file,
                "batch_number": parse_batch_number(batch_file),
                "round_index": parse_int(row.get("round_index")),
                "slot_id": parse_int(row.get("slot_id")),
                "attempt_index": parse_int(row.get("attempt_index")),
                "classifier_rows": parse_int(row.get("last_seen_classifier_rows")),
                "result_rows": parse_int(row.get("last_seen_result_rows")),
                "task_count": parse_int(row.get("task_count")),
                "prepared_reason": row.get("prepared_reason") or "",
            }
        )
    stale.sort(key=lambda item: (parse_int(item.get("round_index")), parse_int(item.get("batch_number"))))
    return stale


def summarize_rounds(state: dict[str, object], schedule_rows: list[dict[str, str]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    if not schedule_rows:
        return output
    grouped: dict[int, list[dict[str, str]]] = {}
    for row in schedule_rows:
        try:
            round_index = int(row.get("round_index") or "0")
        except ValueError:
            continue
        grouped.setdefault(round_index, []).append(row)
    for round_index in sorted(grouped):
        rows = grouped[round_index]
        status_counts: dict[str, int] = {}
        classifier_rows = 0
        result_rows = 0
        all_completed = True
        for row in rows:
            status = effective_row_status(row)
            status_counts[status] = status_counts.get(status, 0) + 1
            try:
                classifier_rows += int(row.get("last_seen_classifier_rows") or "0")
            except ValueError:
                pass
            try:
                result_rows += int(row.get("last_seen_result_rows") or "0")
            except ValueError:
                pass
            if not row_is_resolved(row):
                all_completed = False
        output.append(
            {
                "round_index": round_index,
                "status_counts": status_counts,
                "classifier_rows": classifier_rows,
                "result_rows": result_rows,
                "completed": all_completed,
            }
        )
    return output


def batches_for_round(schedule_rows: list[dict[str, str]], round_index: int | None) -> list[dict[str, object]]:
    if round_index is None:
        return []
    rows: list[dict[str, object]] = []
    for row in schedule_rows:
        try:
            row_round_index = int(row.get("round_index") or "0")
        except ValueError:
            continue
        if row_round_index != round_index:
            continue
        rows.append(
            {
                "batch_file": row.get("batch_file") or "",
                "status": effective_row_status(row),
                "active_attempt": row.get("active_attempt") or "",
                "classifier_rows": int(row.get("last_seen_classifier_rows") or "0"),
                "result_rows": int(row.get("last_seen_result_rows") or "0"),
                "prepared_reason": row.get("prepared_reason") or "",
            }
        )
    rows.sort(key=lambda item: str(item["batch_file"]))
    return rows


def collect_heartbeat_points(
    *,
    latest_job: dict[str, object] | None,
    state: dict[str, object] | None,
    managed_processes: list[dict[str, object]],
    runs_dir: Path | None,
) -> list[dict[str, str]]:
    points: list[dict[str, str]] = []

    def add_point(source: str, dt: datetime | None) -> None:
        if dt is None:
            return
        points.append({"source": source, "timestamp": dt.astimezone(timezone.utc).isoformat()})

    if latest_job is not None:
        add_point("latest_job.launched_at", parse_timestamp(latest_job.get("launched_at")))
    if state is not None:
        add_point("supervisor_state.updated_at", parse_timestamp(state.get("updated_at")))
    if runs_dir is not None:
        add_point("file:supervisor_state.json", path_mtime_utc(runs_dir / "supervisor_state.json"))
        add_point("file:schedule.csv", path_mtime_utc(runs_dir / "schedule.csv"))
        add_point("file:supervisor_events.log", path_mtime_utc(runs_dir / "supervisor_events.log"))
        add_point("file:supervisor_live.log", path_mtime_utc(runs_dir / "supervisor_live.log"))
        add_point("file:supervisor_host_state.json", path_mtime_utc(runs_dir / DEFAULT_HOST_STATE_JSON))
        add_point("file:supervisor_host_events.log", path_mtime_utc(runs_dir / DEFAULT_HOST_EVENTS_LOG))

    for item in managed_processes:
        if not isinstance(item, dict):
            continue
        log_path = item.get("log_path")
        batch_file = str(item.get("batch_file") or "")
        attempt_index = item.get("attempt_index")
        if isinstance(log_path, str) and log_path:
            add_point(
                f"worker_log:{batch_file}:attempt_{attempt_index}",
                path_mtime_utc(Path(log_path)),
            )
        add_point(
            f"worker_started:{batch_file}:attempt_{attempt_index}",
            parse_timestamp(item.get("started_at")),
        )
    return points


def latest_heartbeat(points: list[dict[str, str]]) -> dict[str, str] | None:
    best: dict[str, str] | None = None
    best_dt: datetime | None = None
    for point in points:
        dt = parse_timestamp(point.get("timestamp"))
        if dt is None:
            continue
        if best_dt is None or dt > best_dt:
            best_dt = dt
            best = point
    return best


def derive_job_status(
    *,
    latest_job: dict[str, object] | None,
    state: dict[str, object] | None,
    managed_processes: list[dict[str, object]],
    heartbeat: dict[str, str] | None,
    heartbeat_grace_seconds: int,
    host_process_lines: list[str],
    systemd_unit: dict[str, object] | None,
) -> str:
    if systemd_unit and bool(systemd_unit.get("queried")):
        active_state = str(systemd_unit.get("ActiveState") or "").strip()
        if active_state in SYSTEMD_RUNNING_STATES:
            return "running"
        if active_state == "failed":
            return "failed"
        if active_state in {"inactive", "deactivating"}:
            if latest_job is None and state is None:
                return "missing"
            if not managed_processes and not host_process_lines:
                phase = str((state or {}).get("phase") or "").strip().lower()
                if phase == "completed":
                    return "completed"
                return "stopped_or_stale"

    if state is None:
        if latest_job is None:
            return "missing"
        return "launched_no_state"

    phase = str(state.get("phase") or "").strip().lower()
    if phase == "completed":
        return "completed"
    if phase in {"failed", "error"}:
        return "failed"

    alive_workers = [proc for proc in managed_processes if is_pid_running(proc.get("pid"))]
    if alive_workers:
        return "running"

    if host_process_lines:
        return "running"

    heartbeat_at = parse_timestamp((heartbeat or {}).get("timestamp"))
    now = datetime.now(timezone.utc)
    if heartbeat_at is not None:
        age_seconds = (now - heartbeat_at).total_seconds()
        if age_seconds <= heartbeat_grace_seconds:
            heartbeat_source = str((heartbeat or {}).get("source") or "")
            job_mode = str((latest_job or {}).get("mode") or "").strip()
            if job_mode == "foreground":
                return "running"
            if not alive_workers and not host_process_lines and heartbeat_source.startswith("worker_log:"):
                return "orphaned_worker_activity"
            return "running"

    updated_at = parse_timestamp(state.get("updated_at"))
    if updated_at is not None:
        age_seconds = (now - updated_at).total_seconds()
        if age_seconds <= DEFAULT_RUNNING_GRACE_SECONDS:
            return "running_recently_updated"

    if latest_job and is_pid_running(latest_job.get("pid")):
        return "running_pid_visible"
    return "stopped_or_stale"


def build_payload(args: argparse.Namespace) -> dict[str, object]:
    latest_job = load_json(args.latest_job_json.resolve())
    runs_dir: Path | None = args.runs_dir.resolve() if args.runs_dir else None
    if runs_dir is None and latest_job and isinstance(latest_job.get("runs_dir"), str):
        runs_dir = Path(str(latest_job["runs_dir"])).resolve()

    state: dict[str, object] | None = None
    schedule_rows: list[dict[str, str]] = []
    events_tail: list[str] = []
    if runs_dir is not None:
        state = load_json(runs_dir / "supervisor_state.json")
        schedule_rows = read_schedule_rows(runs_dir / "schedule.csv")
        events_tail = read_events_tail(runs_dir / "supervisor_events.log", args.events_tail)

    managed_processes_raw = []
    if isinstance(state, dict) and isinstance(state.get("managed_processes"), list):
        managed_processes_raw = [item for item in state["managed_processes"] if isinstance(item, dict)]
    managed_processes = [
        {
            "batch_file": item.get("batch_file") or "",
            "round_index": item.get("round_index"),
            "attempt_index": item.get("attempt_index"),
            "pid": item.get("pid"),
            "started_at": item.get("started_at"),
            "log_path": item.get("log_path") or "",
            "pid_alive": is_pid_running(item.get("pid")),
        }
        for item in managed_processes_raw
    ]

    scheduler_mode = "queue"
    backlog_summary = build_backlog_summary(schedule_rows)
    active_progress = build_active_progress(state=state, schedule_rows=schedule_rows)
    earliest_open_round_index = backlog_summary.get("earliest_open_round_index")

    rounds = summarize_rounds(state or {}, schedule_rows)
    active_batches = build_active_batches(state=state, schedule_rows=schedule_rows)
    stale_running_batches = stale_schedule_running_batches(state=state, schedule_rows=schedule_rows)
    unit_name = str((latest_job or {}).get("unit_name") or "")
    systemd_unit = read_systemd_unit_status(unit_name) if unit_name else {
        "available": False,
        "queried": False,
        "unit_name": "",
    }
    host_process_info = collect_host_process_lines(runs_dir)
    heartbeat_points = collect_heartbeat_points(
        latest_job=latest_job,
        state=state,
        managed_processes=managed_processes_raw,
        runs_dir=runs_dir,
    )
    heartbeat = latest_heartbeat(heartbeat_points)
    heartbeat_age_seconds = None
    heartbeat_at = parse_timestamp((heartbeat or {}).get("timestamp"))
    if heartbeat_at is not None:
        heartbeat_age_seconds = int((datetime.now(timezone.utc) - heartbeat_at).total_seconds())
    pid_visibility = "unknown"
    if managed_processes:
        pid_visibility = "visible" if any(item.get("pid_alive") for item in managed_processes) else "not_visible_from_current_context"
    payload = {
        "status": derive_job_status(
            latest_job=latest_job,
            state=state,
            managed_processes=managed_processes_raw,
            heartbeat=heartbeat,
            heartbeat_grace_seconds=args.heartbeat_grace_seconds,
            host_process_lines=host_process_info["lines"],
            systemd_unit=systemd_unit,
        ),
        "latest_job_json": str(args.latest_job_json.resolve()),
        "runs_dir": str(runs_dir) if runs_dir is not None else None,
        "launched_at": latest_job.get("launched_at") if latest_job else None,
        "unit_name": unit_name or None,
        "batch_window": {
            "start_batch": latest_job.get("start_batch") if latest_job else None,
            "end_batch": latest_job.get("end_batch") if latest_job else None,
        },
        "task_window": {
            "first_task_index": latest_job.get("first_task_index") if latest_job else None,
            "last_task_index": latest_job.get("last_task_index") if latest_job else None,
        },
        "phase": state.get("phase") if state else None,
        "scheduler_mode": scheduler_mode,
        "updated_at": state.get("updated_at") if state else None,
        "heartbeat_grace_seconds": args.heartbeat_grace_seconds,
        "latest_heartbeat": heartbeat,
        "heartbeat_age_seconds": heartbeat_age_seconds,
        "pid_visibility": pid_visibility,
        "host_process_check": {
            "available": host_process_info["available"],
            "scope": host_process_info["scope"],
            "match_count": len(host_process_info["lines"]),
            "lines": host_process_info["lines"],
        },
        "systemd_unit_check": systemd_unit,
        "earliest_open_round_index": earliest_open_round_index,
        "active_progress": active_progress,
        "backlog_summary": backlog_summary,
        "target_rounds": state.get("target_rounds") if state else None,
        "max_workers": state.get("max_workers") if state else None,
        "slots": state.get("slots") if state else None,
        "waiting_queue": state.get("waiting_queue") if state else None,
        "tail_retry_queue": state.get("tail_retry_queue") if state else None,
        "collect_queue": state.get("collect_queue") if state else None,
        "deferred_queue": state.get("deferred_queue") if state else None,
        "active_workers": managed_processes,
        "round_summaries": rounds,
        "active_batches": active_batches,
        "earliest_backlog_group_batches": batches_for_round(schedule_rows, earliest_open_round_index),
        "stale_schedule_running_batches": stale_running_batches,
        "recent_events": events_tail,
    }
    return payload


def print_human(payload: dict[str, object]) -> None:
    print(f"status: {payload.get('status')}")
    if payload.get("unit_name"):
        print(f"unit_name: {payload.get('unit_name')}")
    print(f"runs_dir: {payload.get('runs_dir')}")
    print(f"launched_at: {payload.get('launched_at')}")
    print(f"scheduler_mode: {payload.get('scheduler_mode')}")
    batch_window = payload.get("batch_window") or {}
    if isinstance(batch_window, dict):
        print(
            "batch_window: "
            f"{batch_window.get('start_batch')} -> {batch_window.get('end_batch')}"
        )
    task_window = payload.get("task_window") or {}
    if isinstance(task_window, dict):
        print(
            "task_window: "
            f"{task_window.get('first_task_index')} -> {task_window.get('last_task_index')}"
        )
    print(f"phase: {payload.get('phase')}")
    print(f"updated_at: {payload.get('updated_at')}")
    print(f"pid_visibility: {payload.get('pid_visibility')}")
    host_process_check = payload.get("host_process_check")
    if isinstance(host_process_check, dict):
        print(
            "host_process_check: "
            f"available={host_process_check.get('available')} "
            f"scope={host_process_check.get('scope')} "
            f"match_count={host_process_check.get('match_count')}"
        )
    systemd_unit_check = payload.get("systemd_unit_check")
    if isinstance(systemd_unit_check, dict):
        print(
            "systemd_unit_check: "
            f"available={systemd_unit_check.get('available')} "
            f"queried={systemd_unit_check.get('queried')} "
            f"active={systemd_unit_check.get('ActiveState')} "
            f"sub={systemd_unit_check.get('SubState')}"
        )
    heartbeat = payload.get("latest_heartbeat")
    if isinstance(heartbeat, dict):
        print(
            "latest_heartbeat: "
            f"{heartbeat.get('timestamp')} "
            f"from {heartbeat.get('source')} "
            f"age_seconds={payload.get('heartbeat_age_seconds')}"
        )
    else:
        print("latest_heartbeat: none age_seconds=None")
    if payload.get("earliest_open_round_index") is not None:
        print(f"earliest_open_group_index: {payload.get('earliest_open_round_index')}")
    if payload.get("max_workers") is not None:
        print(f"max_workers: {payload.get('max_workers')}")

    active_progress = payload.get("active_progress")
    if isinstance(active_progress, dict):
        print(
            "active_progress: "
            f"source={active_progress.get('source')} "
            f"batch_range={active_progress.get('active_batch_min')}->{active_progress.get('active_batch_max')} "
            f"frontier_batch={active_progress.get('frontier_batch_number')}"
        )

    backlog_summary = payload.get("backlog_summary")
    if isinstance(backlog_summary, dict):
        print(
            "backlog_summary: "
            f"waiting={backlog_summary.get('waiting_count')}@group{backlog_summary.get('waiting_earliest_round_index')} "
            f"tail_retry={backlog_summary.get('tail_retry_count')}@group{backlog_summary.get('tail_retry_earliest_round_index')} "
            f"collect={backlog_summary.get('collect_count')}@group{backlog_summary.get('collect_earliest_round_index')} "
            f"deferred={backlog_summary.get('deferred_count')}@group{backlog_summary.get('deferred_earliest_round_index')}"
        )

    target_rounds = payload.get("target_rounds")
    if isinstance(target_rounds, list):
        print("target_queue_groups:", ", ".join(str(item) for item in target_rounds))

    active_workers = payload.get("active_workers")
    if isinstance(active_workers, list):
        alive_count = sum(1 for item in active_workers if isinstance(item, dict) and item.get("pid_alive"))
        print(f"active_workers: {len(active_workers)} tracked, {alive_count} alive")
        for item in active_workers:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"group={item.get('round_index')} "
                f"batch={item.get('batch_file')} "
                f"attempt={item.get('attempt_index')} "
                f"pid={item.get('pid')} "
                f"pid_alive={item.get('pid_alive')}"
            )

    slots = payload.get("slots")
    if isinstance(slots, list) and slots:
        print("slots:")
        for item in slots:
            if not isinstance(item, dict):
                continue
            if item.get("state") == "idle":
                print(f"  - slot={item.get('slot_id')} state=idle")
                continue
            print(
                "  - "
                f"slot={item.get('slot_id')} "
                f"state={item.get('state')} "
                f"group={item.get('round_index')} "
                f"batch={item.get('batch_file')} "
                f"attempt={item.get('attempt_index')} "
                f"split_recovery={item.get('split_recovery')} "
                f"pid_count={item.get('pid_count')}"
            )

    active_batches = payload.get("active_batches")
    if isinstance(active_batches, list) and active_batches:
        print("active_batches:")
        for item in active_batches:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"slot={item.get('slot_id')} "
                f"group={item.get('round_index')} "
                f"batch={item.get('batch_file')} "
                f"attempt={item.get('attempt_index')} "
                f"status={item.get('status')} "
                f"rows={item.get('result_rows')}/{item.get('task_count')} "
                f"split_recovery={item.get('split_recovery')} "
                f"pid_count={item.get('pid_count')}"
            )
    else:
        print("active_batches: none")

    for key in ["waiting_queue", "tail_retry_queue", "collect_queue", "deferred_queue"]:
        queue_items = payload.get(key)
        if isinstance(queue_items, list) and queue_items:
            print(f"{key}:")
            for item in queue_items[:20]:
                if not isinstance(item, dict):
                    continue
                print(f"  - {item}")

    if isinstance(host_process_check, dict):
        lines = host_process_check.get("lines")
        if isinstance(lines, list) and lines:
            print("host_process_lines:")
            for line in lines[:10]:
                print(f"  {line}")

    earliest_backlog_group_batches = payload.get("earliest_backlog_group_batches")
    if isinstance(earliest_backlog_group_batches, list) and earliest_backlog_group_batches:
        print("earliest_backlog_group_batches:")
        for item in earliest_backlog_group_batches:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"batch={item.get('batch_file')} "
                f"status={item.get('status')} "
                f"attempt={item.get('active_attempt')} "
                f"classifier_rows={item.get('classifier_rows')} "
                f"result_rows={item.get('result_rows')} "
                f"prepared_reason={item.get('prepared_reason')}"
            )

    stale_schedule_running = payload.get("stale_schedule_running_batches")
    if isinstance(stale_schedule_running, list) and stale_schedule_running:
        print("stale_schedule_running_batches:")
        for item in stale_schedule_running:
            if isinstance(item, dict):
                print(f"  - {item}")

    recent_events = payload.get("recent_events")
    if isinstance(recent_events, list) and recent_events:
        print("recent_events:")
        for line in recent_events:
            print(f"  {line}")


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    if args.json:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return
    print_human(payload)


if __name__ == "__main__":
    main()
