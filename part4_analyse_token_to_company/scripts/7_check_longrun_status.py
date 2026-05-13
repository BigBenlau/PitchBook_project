#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
DEFAULT_LATEST_JOB_JSON = PART4_DIR / "agent_runs" / "token_company_longrun_latest.json"
DEFAULT_EVENTS_TAIL = 20
DEFAULT_RUNNING_GRACE_SECONDS = 180
DEFAULT_HEARTBEAT_GRACE_SECONDS = 900
DEFAULT_WORKER_LOG_TAIL_LINES = 120
DEFAULT_NOTABLE_EVENTS_TAIL = 25
DEFAULT_RECENT_SEARCH_QUERY_LIMIT = 5
DEFAULT_HOST_STATE_JSON = "supervisor_host_state.json"
DEFAULT_HOST_EVENTS_LOG = "supervisor_host_events.log"
SYSTEMD_RUNNING_STATES = {"active", "activating", "reloading"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read the latest long-running token-company supervisor metadata and report "
            "whether the job is still running, which round it is on, and the current "
            "batch / worker progress."
        )
    )
    parser.add_argument("--latest-job-json", type=Path, default=DEFAULT_LATEST_JOB_JSON)
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--events-tail", type=int, default=DEFAULT_EVENTS_TAIL)
    parser.add_argument("--heartbeat-grace-seconds", type=int, default=DEFAULT_HEARTBEAT_GRACE_SECONDS)
    parser.add_argument(
        "--include-systemd-check",
        action="store_true",
        help="Optionally query systemd --user. Disabled by default because many sandboxed environments cannot access the user bus.",
    )
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict) or not payload:
        return None
    return payload


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


def is_pgid_running(pgid: object) -> bool:
    if not isinstance(pgid, int) or pgid <= 0:
        return False
    try:
        os.killpg(pgid, 0)
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


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError, AttributeError):
        return default


def batch_label(batch_file: object) -> str:
    text = str(batch_file or "").strip()
    if not text:
        return ""
    return Path(text).name


def read_last_lines(path: Path, limit: int) -> list[str]:
    if not path.exists():
        return []
    last_lines: deque[str] = deque(maxlen=max(limit, 1))
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            last_lines.append(line.rstrip("\n"))
    return list(last_lines)


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
        if "part4" not in line:
            continue
        if "grep part4" in line:
            continue
        if current_pid_text in line:
            continue
        if "7_check_longrun_status.py" in line:
            continue
        lines.append(line)
    if not lines:
        return {
            "available": True,
            "scope": "part4",
            "lines": [],
        }

    if runs_dir is None:
        return {
            "available": True,
            "scope": "part4",
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


def parse_event_timestamp(line: str) -> datetime | None:
    token = str(line or "").strip().split(" ", 1)[0]
    if not token:
        return None
    return parse_timestamp(token)


def parse_event_tag(line: str) -> str:
    text = str(line or "")
    start = text.find("[")
    if start < 0:
        return ""
    end = text.find("]", start + 1)
    if end < 0:
        return ""
    return text[start + 1:end].strip()


def summarize_events_log(path: Path, *, notable_tail: int = DEFAULT_NOTABLE_EVENTS_TAIL) -> dict[str, object]:
    if not path.exists():
        return {
            "available": False,
            "path": str(path),
            "last_event_at": None,
            "event_counts": {},
            "recent_notable_events": [],
        }

    notable_events: deque[str] = deque(maxlen=max(notable_tail, 1))
    counters: Counter[str] = Counter()
    last_event_at: datetime | None = None
    last_event_line = ""
    notable_prefixes = (
        "worker:",
        "split_batch:",
        "tail_retry:",
        "long_tail:",
        "retry_cap:",
        "collect:",
        "queue_supervisor:",
        "supervisor:",
    )

    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            if not line:
                continue

            event_at = parse_event_timestamp(line)
            if event_at is not None and (last_event_at is None or event_at > last_event_at):
                last_event_at = event_at
                last_event_line = line

            tag = parse_event_tag(line)
            if tag:
                if tag.startswith(notable_prefixes):
                    counters[tag] += 1
                    notable_events.append(line)
                elif tag == "command:end":
                    counters[tag] += 1
                    if "returncode=0" not in line:
                        counters["command:end_nonzero"] += 1
                        notable_events.append(line)
                elif tag == "command:stderr":
                    counters[tag] += 1
                    notable_events.append(line)

            stripped = line.strip()
            if stripped.startswith("- batch_"):
                counters["runtime_action_batch_line"] += 1
                notable_events.append(line)
            elif "Runtime actions:" in line:
                counters["runtime_action_summary_line"] += 1
                notable_events.append(line)
            elif "Round runtime watch detected actions." in line:
                counters["runtime_watch_detected_actions"] += 1
                notable_events.append(line)

    return {
        "available": True,
        "path": str(path),
        "last_event_at": last_event_at.isoformat() if last_event_at else None,
        "last_event_line": last_event_line,
        "event_counts": dict(sorted(counters.items())),
        "recent_notable_events": list(notable_events),
    }


def summarize_worker_log(path: Path, *, tail_lines: int = DEFAULT_WORKER_LOG_TAIL_LINES) -> dict[str, object]:
    if not path.exists():
        return {
            "available": False,
            "path": str(path),
            "log_mtime": None,
            "json_lines_tail": 0,
            "web_search_completed_tail": 0,
            "file_change_completed_tail": 0,
            "agent_message_completed_tail": 0,
            "recent_search_queries": [],
            "last_agent_message": None,
        }

    counts: Counter[str] = Counter()
    recent_queries: deque[str] = deque(maxlen=DEFAULT_RECENT_SEARCH_QUERY_LIMIT)
    last_agent_message = ""
    json_lines = 0
    for line in read_last_lines(path, tail_lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        json_lines += 1
        event_type = str(payload.get("type") or "").strip()
        if event_type:
            counts[event_type] += 1
        item = payload.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "").strip()
        if item_type and event_type:
            counts[f"{item_type}:{event_type}"] += 1
        if event_type != "item.completed":
            continue
        if item_type == "web_search":
            query = str(item.get("query") or "").strip()
            if query:
                recent_queries.append(query)
        elif item_type == "agent_message":
            text = str(item.get("text") or "").strip()
            if text:
                last_agent_message = text

    return {
        "available": True,
        "path": str(path),
        "log_mtime": (path_mtime_utc(path).isoformat() if path_mtime_utc(path) else None),
        "json_lines_tail": json_lines,
        "web_search_completed_tail": counts.get("web_search:item.completed", 0),
        "file_change_completed_tail": counts.get("file_change:item.completed", 0),
        "agent_message_completed_tail": counts.get("agent_message:item.completed", 0),
        "recent_search_queries": list(recent_queries),
        "last_agent_message": last_agent_message or None,
    }


def parse_failure_counts(row: dict[str, str]) -> dict[str, int]:
    raw = str(row.get("failure_counts_json") or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return {
        str(key): safe_int(value)
        for key, value in payload.items()
        if safe_int(value) > 0
    }


def build_progress_overview(schedule_rows: list[dict[str, str]]) -> dict[str, int]:
    overview = {
        "total_batches": len(schedule_rows),
        "resolved_batches": 0,
        "open_batches": 0,
        "batches_with_classifier_rows": 0,
        "batches_with_result_rows": 0,
        "batches_with_failures": 0,
        "total_classifier_rows": 0,
        "total_result_rows": 0,
    }
    for row in schedule_rows:
        status = effective_row_status(row)
        if row_is_resolved(row):
            overview["resolved_batches"] += 1
        else:
            overview["open_batches"] += 1
        classifier_rows = max(
            safe_int(row.get("last_seen_classifier_rows")),
            safe_int(row.get("best_valid_classifier_rows")),
        )
        result_rows = max(
            safe_int(row.get("last_seen_result_rows")),
            safe_int(row.get("best_valid_result_rows")),
        )
        overview["total_classifier_rows"] += classifier_rows
        overview["total_result_rows"] += result_rows
        if classifier_rows > 0:
            overview["batches_with_classifier_rows"] += 1
        if result_rows > 0:
            overview["batches_with_result_rows"] += 1
        if (
            safe_int(row.get("respawn_count")) > 0
            or safe_int(row.get("startup_failure_count")) > 0
            or safe_int(row.get("stall_failure_count")) > 0
            or parse_failure_counts(row)
            or status in {"retry_capped", "deferred_long_tail"}
        ):
            overview["batches_with_failures"] += 1
    return overview


def row_is_deferred_long_tail(row: dict[str, str]) -> bool:
    status = (row.get("status") or "").strip()
    completion_mode = (row.get("completion_mode") or "").strip()
    if status == "deferred_long_tail":
        return True
    if status == "completed":
        return False
    return completion_mode == "deferred_long_tail"


def row_is_retry_capped(row: dict[str, str]) -> bool:
    status = (row.get("status") or "").strip()
    completion_mode = (row.get("completion_mode") or "").strip()
    if status == "retry_capped":
        return True
    if status in {"completed", "deferred_long_tail"}:
        return False
    return completion_mode == "retry_capped"


def effective_row_status(row: dict[str, str]) -> str:
    raw_status = (row.get("status") or "").strip()
    completion_mode = (row.get("completion_mode") or "").strip()
    if raw_status in {
        "partial_complete_retry_pending",
        "worker_failed_retry_pending",
        "schema_error_quarantined",
        "collect_blocked",
    }:
        return raw_status
    if completion_mode in {
        "partial_complete_retry_pending",
        "worker_failed_retry_pending",
        "schema_error_quarantined",
        "collect_blocked",
    }:
        return completion_mode
    if row_is_retry_capped(row):
        return "retry_capped"
    if row_is_deferred_long_tail(row):
        return "deferred_long_tail"
    return (row.get("status") or "").strip() or "unknown"


def row_is_resolved(row: dict[str, str]) -> bool:
    return effective_row_status(row) in {
        "completed",
        "deferred_long_tail",
        "retry_capped",
        "partial_complete_retry_pending",
        "worker_failed_retry_pending",
        "schema_error_quarantined",
        "collect_blocked",
    }


def row_has_open_queue_work(row: dict[str, str]) -> bool:
    status = effective_row_status(row)
    if status in {
        "deferred_long_tail",
        "retry_capped",
        "partial_complete_retry_pending",
        "worker_failed_retry_pending",
        "schema_error_quarantined",
        "collect_blocked",
    }:
        return False
    if status == "completed" and str(row.get("collect_state") or "").strip() == "done":
        return False
    return True


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
            classifier_rows += max(
                safe_int(row.get("last_seen_classifier_rows")),
                safe_int(row.get("best_valid_classifier_rows")),
            )
            result_rows += max(
                safe_int(row.get("last_seen_result_rows")),
                safe_int(row.get("best_valid_result_rows")),
            )
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


def current_round_batches(
    schedule_rows: list[dict[str, str]],
    current_round_index: int | None,
    *,
    worker_log_by_batch: dict[str, dict[str, object]] | None = None,
) -> list[dict[str, object]]:
    if current_round_index is None:
        return []
    worker_log_by_batch = worker_log_by_batch or {}
    rows: list[dict[str, object]] = []
    for row in schedule_rows:
        try:
            round_index = int(row.get("round_index") or "0")
        except ValueError:
            continue
        if round_index != current_round_index:
            continue
        batch_file = row.get("batch_file") or ""
        status = effective_row_status(row)
        failure_counts = parse_failure_counts(row)
        live_classifier_rows = safe_int(row.get("last_seen_classifier_rows"))
        live_result_rows = safe_int(row.get("last_seen_result_rows"))
        best_valid_classifier_rows = safe_int(row.get("best_valid_classifier_rows"))
        best_valid_result_rows = safe_int(row.get("best_valid_result_rows"))
        classifier_rows = max(live_classifier_rows, best_valid_classifier_rows)
        result_rows = max(live_result_rows, best_valid_result_rows)
        rows.append(
            {
                "batch_file": batch_file,
                "batch_name": batch_label(batch_file),
                "status": status,
                "active_attempt": row.get("active_attempt") or "",
                "attempt_index": safe_int(row.get("attempt_index")),
                "classifier_rows": classifier_rows,
                "result_rows": result_rows,
                "live_classifier_rows": live_classifier_rows,
                "live_result_rows": live_result_rows,
                "best_valid_classifier_rows": best_valid_classifier_rows,
                "best_valid_result_rows": best_valid_result_rows,
                "best_valid_attempt_index": safe_int(row.get("best_valid_attempt_index")),
                "best_valid_updated_at": row.get("best_valid_updated_at") or "",
                "best_valid_source": row.get("best_valid_source") or "",
                "prepared_reason": row.get("prepared_reason") or "",
                "respawn_count": safe_int(row.get("respawn_count")),
                "startup_failure_count": safe_int(row.get("startup_failure_count")),
                "stall_failure_count": safe_int(row.get("stall_failure_count")),
                "last_failure_type": row.get("last_failure_type") or "",
                "last_rerun_reason": row.get("last_rerun_reason") or "",
                "health_state": row.get("health_state") or "",
                "last_worker_activity_at": row.get("last_worker_activity_at") or "",
                "last_worker_activity_type": row.get("last_worker_activity_type") or "",
                "last_worker_activity_source": row.get("last_worker_activity_source") or "",
                "soft_timeout_warned_at": row.get("soft_timeout_warned_at") or "",
                "last_timeout_warning_reason": row.get("last_timeout_warning_reason") or "",
                "next_eligible_retry_at": row.get("next_eligible_retry_at") or "",
                "first_row_at": row.get("first_row_at") or "",
                "last_progress_at": row.get("last_progress_at") or "",
                "deferred_reason": row.get("deferred_reason") or "",
                "failure_counts": failure_counts,
                "worker_log_activity": worker_log_by_batch.get(batch_file),
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
    schedule_rows: list[dict[str, str]],
    managed_processes: list[dict[str, object]],
    heartbeat: dict[str, str] | None,
    heartbeat_grace_seconds: int,
    event_summary: dict[str, object] | None,
    progress_overview: dict[str, int] | None,
    host_process_lines: list[str],
    systemd_unit: dict[str, object] | None,
) -> tuple[str, str]:
    if state is None:
        if latest_job is None:
            return "missing", "No latest job metadata and no supervisor_state.json were found."
        return "launched_no_state", "Latest job exists, but supervisor_state.json is missing."

    phase = str(state.get("phase") or "").strip().lower()
    if phase == "completed":
        return "completed", "supervisor_state.json reports phase=completed."
    if phase == "abandoned":
        return "abandoned_by_supervisor", "supervisor_state.json reports phase=abandoned."
    if phase in {"failed", "error"}:
        return "failed", f"supervisor_state.json reports phase={phase}."

    latest_status = str((latest_job or {}).get("status") or "").strip().lower()
    if latest_status == "abandoned_by_supervisor":
        return "abandoned_by_supervisor", "latest job metadata reports abandoned_by_supervisor."
    if latest_status == "failed":
        return "failed", "latest job metadata reports failed."
    if latest_status == "completed":
        return "completed", "latest job metadata reports completed."

    open_rows = [row for row in schedule_rows if row_has_open_queue_work(row)]
    resolved_rows = [row for row in schedule_rows if row_is_resolved(row)]
    batches_with_rows = (progress_overview or {}).get("batches_with_result_rows", 0)
    batches_with_failures = (progress_overview or {}).get("batches_with_failures", 0)
    event_counts = {}
    if isinstance(event_summary, dict) and isinstance(event_summary.get("event_counts"), dict):
        event_counts = {
            str(key): safe_int(value)
            for key, value in event_summary["event_counts"].items()
        }

    alive_workers = [
        proc
        for proc in managed_processes
        if is_pid_running(proc.get("pid")) or is_pgid_running(proc.get("pgid"))
    ]
    if alive_workers:
        if batches_with_failures > 0 or event_counts.get("worker:dead_rerun", 0) > 0:
            return "running_with_runtime_failures", "Visible worker processes are alive and recent failures were recorded."
        if batches_with_rows > 0:
            return "running_with_progress", "Visible worker processes are alive and result rows are increasing."
        return "running", "Visible worker processes are alive."

    if host_process_lines:
        if batches_with_failures > 0 or event_counts.get("worker:dead_rerun", 0) > 0:
            return "running_with_runtime_failures", "Host process scan found active run commands and recent failures were recorded."
        if batches_with_rows > 0:
            return "running_with_progress", "Host process scan found active run commands and result rows are increasing."
        return "running", "Host process scan found active run commands."

    heartbeat_at = parse_timestamp((heartbeat or {}).get("timestamp"))
    now = datetime.now(timezone.utc)
    if heartbeat_at is not None:
        age_seconds = (now - heartbeat_at).total_seconds()
        if age_seconds <= heartbeat_grace_seconds:
            if open_rows:
                if batches_with_failures > 0 or event_counts.get("worker:dead_rerun", 0) > 0:
                    return "running_with_runtime_failures", "Recent worker/event log heartbeat exists and at least one batch has reruns or failure counters."
                if batches_with_rows > 0:
                    return "running_with_progress", "Recent worker/event log heartbeat exists and at least one batch has result rows."
                return "running_log_confirmed", "Recent log heartbeat exists for unresolved schedule rows."
            if schedule_rows and len(resolved_rows) == len(schedule_rows):
                return "completed", "All schedule rows are resolved and recent logs exist."

    updated_at = parse_timestamp(state.get("updated_at"))
    if updated_at is not None:
        age_seconds = (now - updated_at).total_seconds()
        if age_seconds <= DEFAULT_RUNNING_GRACE_SECONDS and open_rows:
            if batches_with_failures > 0:
                return "running_with_runtime_failures", "supervisor_state.json was updated recently and unresolved rows already show failures."
            return "running_log_confirmed", "supervisor_state.json was updated recently for unresolved rows."

    if latest_job and is_pid_running(latest_job.get("pid")):
        return "running_pid_visible", "The launcher PID from latest job metadata is still visible."

    if schedule_rows and len(resolved_rows) == len(schedule_rows):
        return "completed", "All schedule rows are resolved."
    if open_rows:
        if batches_with_rows > 0:
            return "stalled_after_partial_progress", "Unresolved rows remain, but no recent runtime heartbeat is visible after partial progress."
        return "stopped_or_stale", "Unresolved rows remain, but there is no recent runtime heartbeat in logs or metadata."
    return "stopped_or_stale", "No running signal is visible in logs, metadata, or process checks."


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
            "pgid": item.get("pgid"),
            "started_at": item.get("started_at"),
            "log_path": item.get("log_path") or "",
            "pid_alive": is_pid_running(item.get("pid")),
            "pgid_alive": is_pgid_running(item.get("pgid")),
        }
        for item in managed_processes_raw
    ]

    state_round_index = None
    if isinstance(state, dict):
        try:
            state_round_index = int(state.get("current_round_index"))
        except (TypeError, ValueError):
            state_round_index = None

    scheduler_mode = "round"
    if latest_job and isinstance(latest_job.get("scheduler_mode"), str) and latest_job.get("scheduler_mode"):
        scheduler_mode = str(latest_job.get("scheduler_mode"))
    if isinstance(state, dict) and isinstance(state.get("scheduler_mode"), str) and state.get("scheduler_mode"):
        scheduler_mode = str(state.get("scheduler_mode"))

    current_round_index = state_round_index
    if schedule_rows:
        unresolved_rounds = sorted(
            {
                int(row.get("round_index") or "0")
                for row in schedule_rows
                if int(row.get("round_index") or "0") > 0
                and (
                    row_has_open_queue_work(row)
                    if scheduler_mode == "queue"
                    else not row_is_resolved(row)
                )
            }
        )
        if unresolved_rounds:
            schedule_round_index = unresolved_rounds[0]
            if current_round_index != schedule_round_index:
                current_round_index = schedule_round_index

    rounds = summarize_rounds(state or {}, schedule_rows)
    unit_name = str((latest_job or {}).get("unit_name") or "")
    if args.include_systemd_check and unit_name:
        systemd_unit = read_systemd_unit_status(unit_name)
    else:
        systemd_unit = {
            "available": False,
            "queried": False,
            "unit_name": unit_name,
            "disabled": not args.include_systemd_check,
        }
    host_process_info = collect_host_process_lines(runs_dir)
    events_summary = summarize_events_log(runs_dir / "supervisor_events.log") if runs_dir is not None else {
        "available": False,
        "path": None,
        "last_event_at": None,
        "event_counts": {},
        "recent_notable_events": [],
    }
    heartbeat_points = collect_heartbeat_points(
        latest_job=latest_job,
        state=state,
        managed_processes=managed_processes_raw,
        runs_dir=runs_dir,
    )
    heartbeat = latest_heartbeat(heartbeat_points)
    worker_log_activity: list[dict[str, object]] = []
    worker_log_by_batch: dict[str, dict[str, object]] = {}
    for item in managed_processes:
        log_path = str(item.get("log_path") or "").strip()
        batch_file = str(item.get("batch_file") or "").strip()
        summary = summarize_worker_log(Path(log_path)) if log_path else {
            "available": False,
            "path": log_path,
            "log_mtime": None,
            "json_lines_tail": 0,
            "web_search_completed_tail": 0,
            "file_change_completed_tail": 0,
            "agent_message_completed_tail": 0,
            "recent_search_queries": [],
            "last_agent_message": None,
        }
        activity = {
            "batch_file": batch_file,
            "batch_name": batch_label(batch_file),
            "attempt_index": item.get("attempt_index"),
            "round_index": item.get("round_index"),
            "pid_alive": item.get("pid_alive"),
            "pgid_alive": item.get("pgid_alive"),
            **summary,
        }
        worker_log_activity.append(activity)
        if batch_file:
            worker_log_by_batch[batch_file] = activity

    for row in schedule_rows:
        batch_file = str(row.get("batch_file") or "").strip()
        if not batch_file or batch_file in worker_log_by_batch:
            continue
        active_attempt = str(row.get("active_attempt") or "").strip()
        if not active_attempt:
            continue
        log_path = Path(active_attempt) / "supervisor_worker.log"
        summary = summarize_worker_log(log_path)
        activity = {
            "batch_file": batch_file,
            "batch_name": batch_label(batch_file),
            "attempt_index": safe_int(row.get("attempt_index")),
            "round_index": safe_int(row.get("round_index")),
            "pid_alive": False,
            "pgid_alive": False,
            **summary,
        }
        worker_log_by_batch[batch_file] = activity
        worker_log_activity.append(activity)

    progress_overview = build_progress_overview(schedule_rows)
    status, status_reason = derive_job_status(
        latest_job=latest_job,
        state=state,
        schedule_rows=schedule_rows,
        managed_processes=managed_processes_raw,
        heartbeat=heartbeat,
        heartbeat_grace_seconds=args.heartbeat_grace_seconds,
        event_summary=events_summary,
        progress_overview=progress_overview,
        host_process_lines=host_process_info["lines"],
        systemd_unit=systemd_unit,
    )
    pid_visibility = "unknown"
    if managed_processes:
        pid_visibility = (
            "visible"
            if any(item.get("pid_alive") or item.get("pgid_alive") for item in managed_processes)
            else "not_visible_from_current_context"
        )
    payload = {
        "status": status,
        "status_reason": status_reason,
        "status_basis": "schedule.csv + supervisor_state.json + supervisor_events.log + worker logs",
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
        "pid_visibility": pid_visibility,
        "host_process_check": {
            "available": host_process_info["available"],
            "scope": host_process_info["scope"],
            "match_count": len(host_process_info["lines"]),
            "lines": host_process_info["lines"],
        },
        "systemd_unit_check": systemd_unit,
        "current_round_index": current_round_index,
        "target_rounds": state.get("target_rounds") if state else None,
        "max_workers": state.get("max_workers") if state else None,
        "slots": state.get("slots") if state else None,
        "waiting_queue": state.get("waiting_queue") if state else None,
        "tail_retry_queue": state.get("tail_retry_queue") if state else None,
        "collect_queue": state.get("collect_queue") if state else None,
        "deferred_queue": state.get("deferred_queue") if state else None,
        "progress_overview": progress_overview,
        "events_summary": events_summary,
        "active_workers": managed_processes,
        "worker_log_activity": worker_log_activity,
        "round_summaries": rounds,
        "current_round_batches": current_round_batches(
            schedule_rows,
            current_round_index,
            worker_log_by_batch=worker_log_by_batch,
        ),
        "recent_events": events_tail,
    }
    return payload


def print_human(payload: dict[str, object]) -> None:
    print(f"status: {payload.get('status')}")
    print(f"status_reason: {payload.get('status_reason')}")
    print(f"status_basis: {payload.get('status_basis')}")
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
            f"sub={systemd_unit_check.get('SubState')} "
            f"disabled={systemd_unit_check.get('disabled')}"
        )
    heartbeat = payload.get("latest_heartbeat")
    if isinstance(heartbeat, dict):
        print(
            "latest_heartbeat: "
            f"{heartbeat.get('timestamp')} "
            f"from {heartbeat.get('source')}"
        )
    progress_overview = payload.get("progress_overview")
    if isinstance(progress_overview, dict):
        print(
            "progress_overview: "
            f"total_batches={progress_overview.get('total_batches')} "
            f"open_batches={progress_overview.get('open_batches')} "
            f"resolved_batches={progress_overview.get('resolved_batches')} "
            f"batches_with_result_rows={progress_overview.get('batches_with_result_rows')} "
            f"batches_with_failures={progress_overview.get('batches_with_failures')} "
            f"total_result_rows={progress_overview.get('total_result_rows')}"
        )
    print(f"current_round_index: {payload.get('current_round_index')}")
    if payload.get("max_workers") is not None:
        print(f"max_workers: {payload.get('max_workers')}")

    target_rounds = payload.get("target_rounds")
    if isinstance(target_rounds, list):
        print("target_rounds:", ", ".join(str(item) for item in target_rounds))

    active_workers = payload.get("active_workers")
    if isinstance(active_workers, list):
        alive_count = sum(1 for item in active_workers if isinstance(item, dict) and item.get("pid_alive"))
        print(f"active_workers: {len(active_workers)} tracked, {alive_count} alive")
        for item in active_workers:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"round={item.get('round_index')} "
                f"batch={item.get('batch_file')} "
                f"attempt={item.get('attempt_index')} "
                f"pid={item.get('pid')} "
                f"pid_alive={item.get('pid_alive')} "
                f"pgid={item.get('pgid')} "
                f"pgid_alive={item.get('pgid_alive')}"
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
                f"round={item.get('round_index')} "
                f"batch={item.get('batch_file')} "
                f"attempt={item.get('attempt_index')} "
                f"split_recovery={item.get('split_recovery')} "
                f"pid_count={item.get('pid_count')}"
            )

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

    events_summary = payload.get("events_summary")
    if isinstance(events_summary, dict):
        print(
            "events_summary: "
            f"last_event_at={events_summary.get('last_event_at')} "
            f"event_counts={events_summary.get('event_counts')}"
        )
        notable = events_summary.get("recent_notable_events")
        if isinstance(notable, list) and notable:
            print("recent_notable_events:")
            for line in notable[-10:]:
                print(f"  {line}")

    round_summaries = payload.get("round_summaries")
    if isinstance(round_summaries, list) and round_summaries:
        print("round_summaries:")
        for item in round_summaries:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"round={item.get('round_index')} "
                f"completed={item.get('completed')} "
                f"classifier_rows={item.get('classifier_rows')} "
                f"result_rows={item.get('result_rows')} "
                f"status_counts={item.get('status_counts')}"
            )

    current_round_batches = payload.get("current_round_batches")
    if isinstance(current_round_batches, list) and current_round_batches:
        print("current_round_batches:")
        for item in current_round_batches:
            if not isinstance(item, dict):
                continue
            print(
                "  - "
                f"batch={item.get('batch_name') or item.get('batch_file')} "
                f"status={item.get('status')} "
                f"attempt_index={item.get('attempt_index')} "
                f"classifier_rows={item.get('classifier_rows')} "
                f"result_rows={item.get('result_rows')} "
                f"best_valid_classifier_rows={item.get('best_valid_classifier_rows')} "
                f"best_valid_result_rows={item.get('best_valid_result_rows')} "
                f"respawn_count={item.get('respawn_count')} "
                f"startup_failures={item.get('startup_failure_count')} "
                f"stall_failures={item.get('stall_failure_count')} "
                f"health_state={item.get('health_state')} "
                f"last_failure_type={item.get('last_failure_type')} "
                f"last_rerun_reason={item.get('last_rerun_reason')} "
                f"prepared_reason={item.get('prepared_reason')}"
            )
            if item.get("best_valid_updated_at"):
                print(
                    "    best_valid: "
                    f"attempt_index={item.get('best_valid_attempt_index')} "
                    f"updated_at={item.get('best_valid_updated_at')} "
                    f"source={item.get('best_valid_source')}"
                )
            if item.get("last_timeout_warning_reason"):
                print(
                    "    health_warning: "
                    f"reason={item.get('last_timeout_warning_reason')} "
                    f"warned_at={item.get('soft_timeout_warned_at')} "
                    f"next_retry_at={item.get('next_eligible_retry_at')}"
                )
            if item.get("last_worker_activity_at"):
                print(
                    "    last_worker_activity: "
                    f"at={item.get('last_worker_activity_at')} "
                    f"type={item.get('last_worker_activity_type')} "
                    f"source={item.get('last_worker_activity_source')}"
                )
            worker_activity = item.get("worker_log_activity")
            if isinstance(worker_activity, dict):
                print(
                    "    worker_log: "
                    f"log_mtime={worker_activity.get('log_mtime')} "
                    f"web_search_completed_tail={worker_activity.get('web_search_completed_tail')} "
                    f"file_change_completed_tail={worker_activity.get('file_change_completed_tail')} "
                    f"agent_message_completed_tail={worker_activity.get('agent_message_completed_tail')}"
                )
                if worker_activity.get("last_agent_message"):
                    print(f"    last_agent_message: {worker_activity.get('last_agent_message')}")
                recent_queries = worker_activity.get("recent_search_queries")
                if isinstance(recent_queries, list) and recent_queries:
                    print("    recent_search_queries:")
                    for query in recent_queries[-3:]:
                        print(f"      {query}")

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
