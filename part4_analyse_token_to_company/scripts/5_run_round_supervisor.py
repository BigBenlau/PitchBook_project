#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import csv
import ctypes
import json
import os
import shlex
import signal
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from part4_schedule_io import write_schedule_csv

SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent
DEFAULT_AGENT_RUNS_DIR = PART4_DIR / "agent_runs"
DEFAULT_LATEST_JOB_JSON = DEFAULT_AGENT_RUNS_DIR / "token_company_longrun_latest.json"
DEFAULT_FALLBACK_RUNS_DIR = DEFAULT_AGENT_RUNS_DIR / "token_company_parallel_eval_current"
DEFAULT_FINAL_DIR = PART4_DIR / "agent_runs" / "token_company"
DEFAULT_OPS_DIR = PART4_DIR / "agent_runs" / "token_company_ops"
DEFAULT_SCHEDULE_CSV = "schedule.csv"
DEFAULT_STATE_JSON = "supervisor_state.json"
DEFAULT_REGISTRY_JSON = "supervisor_registry.json"
DEFAULT_LOCK_FILE = "supervisor.lock"
DEFAULT_EVENTS_LOG = "supervisor_events.log"
DEFAULT_COLLECT_CHECKPOINT_JSON = "collect_checkpoint.json"
DEFAULT_STARTUP_TIMEOUT_SECONDS = 480
DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS = 240
DEFAULT_POLL_SECONDS = 30
DEFAULT_BATCH_TIMEOUT_SECONDS = 7200
DEFAULT_MAX_BATCH_RESTARTS = 8
DEFAULT_SPLIT_BATCH_RESPAWN_THRESHOLD = 5
DEFAULT_SPLIT_BATCH_FAILURE_THRESHOLD = 3
DEFAULT_CODEX_BIN = shutil.which("codex") or "codex"
DEFAULT_WORKER_SANDBOX_MODE = os.environ.get("PART4_WORKER_SANDBOX_MODE", "danger-full-access")
DEFAULT_SPLIT_SHARD_SIZE = 15
DEFAULT_SPLIT_SHARD_COUNT = 2
SPLIT_BATCH_LAUNCH_REASON = "split_batch_2x15"
SPLIT_STATE_FILE_NAME = "split_recovery_state.json"
SPLIT_OUTCOME_FILE_NAME = "search_outcome.json"
SPLIT_SHARDS_DIR_NAME = "split_recovery"
SPLIT_MERGED_CLASSIFIER_FILE_NAME = "merged_classifier_results.csv"
SPLIT_MERGED_RESULTS_FILE_NAME = "merged_results.csv"
SPLIT_MERGE_MANIFEST_FILE_NAME = "merge_manifest.json"
DEFERRED_LONG_TAIL_CSV = "deferred_long_tail_batches.csv"
DEFERRED_LONG_TAIL_MD = "deferred_long_tail_batches.md"
GLOBAL_LONG_TAIL_BACKLOG_CSV = DEFAULT_OPS_DIR / "long_tail_batches_pending.csv"
RETRY_CAPPED_CSV = "retry_capped_batches.csv"
RETRY_CAPPED_MD = "retry_capped_batches.md"
GLOBAL_RETRY_CAPPED_BACKLOG_CSV = DEFAULT_OPS_DIR / "retry_capped_batches_pending.csv"
PARTIAL_COMPLETE_RETRY_PENDING_STATUS = "partial_complete_retry_pending"
WORKER_FAILED_RETRY_PENDING_STATUS = "worker_failed_retry_pending"
SCHEMA_ERROR_QUARANTINED_STATUS = "schema_error_quarantined"
COLLECT_BLOCKED_STATUS = "collect_blocked"
NONBLOCKING_FAILURE_STATUSES = {
    PARTIAL_COMPLETE_RETRY_PENDING_STATUS,
    WORKER_FAILED_RETRY_PENDING_STATUS,
    SCHEMA_ERROR_QUARANTINED_STATUS,
    COLLECT_BLOCKED_STATUS,
}
RETRY_CAPPED_STATUS = "retry_capped"
RETRY_CAPPED_REASON = "restart_limit_exceeded"
ROUND_RESOLVED_STATUSES = {"completed", "deferred_long_tail", RETRY_CAPPED_STATUS, *NONBLOCKING_FAILURE_STATUSES}
PR_SET_PDEATHSIG = 1
SUPERVISOR_LOST_REASON = "supervisor_lost"
SUPERVISOR_FATAL_REASON = "supervisor_fatal"
SUPERVISOR_LOST_QUEUE_STATE = "supervisor_lost"
SUPERVISOR_CONTEXT: dict[str, Any] = {}
SUPERVISOR_SHUTDOWN_HANDLED = False
WORKER_ACTIVITY_TAIL_LINES = 120
STRONG_WORKER_ACTIVITY_TYPES = {"web_search", "file_change", "agent_message"}
ANY_WORKER_ACTIVITY_TYPES = STRONG_WORKER_ACTIVITY_TYPES | {"command_execution"}

SPLIT_BATCH_FAILURE_TYPES = {
    "startup_no_row",
    "header_only_timeout",
    "partial_stall",
    "row_count_mismatch",
    "schema_error",
    "agent_unresponsive",
    "verifier_forced_rerun",
}


def resolve_default_runs_dir() -> Path:
    try:
        payload = json.loads(DEFAULT_LATEST_JOB_JSON.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return DEFAULT_FALLBACK_RUNS_DIR
    runs_dir_raw = str(payload.get("runs_dir") or "").strip()
    if not runs_dir_raw:
        return DEFAULT_FALLBACK_RUNS_DIR
    candidate = Path(runs_dir_raw).expanduser()
    try:
        candidate = candidate.resolve()
    except OSError:
        return DEFAULT_FALLBACK_RUNS_DIR
    if candidate.exists() and candidate.name.startswith("token_company_parallel_eval_"):
        return candidate
    return DEFAULT_FALLBACK_RUNS_DIR


DEFAULT_RUNS_DIR = resolve_default_runs_dir()


def supervisor_lock_path(runs_dir: Path) -> Path:
    return DEFAULT_OPS_DIR / "locks" / f"{runs_dir.name}.{DEFAULT_LOCK_FILE}"

CLASSIFIER_CSV_COLUMNS = [
    "task_index",
    "canonical_slug",
    "token_symbol",
    "token_name",
    "token_origin_type",
    "entity_link_likelihood",
    "search_tier",
    "entity_search_required",
    "risk_flags",
    "classifier_reason",
]

RESULT_CSV_COLUMNS = [
    "task_index",
    "canonical_slug",
    "token_symbol",
    "token_name",
    "token_origin_type",
    "entity_link_likelihood",
    "entity_search_required",
    "entity_search_reason",
    "project_name",
    "project_url",
    "mapped_entity_name",
    "mapped_entity_legal_name",
    "mapped_entity_type",
    "mapped_entity_url",
    "mapped_entity_country",
    "entity_relation_type",
    "status",
    "completed_at",
    "has_entity_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
]


class SupervisorSignalExit(SystemExit):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(128 + signum)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the fixed part4 round harness: prepare -> launch -> mark-started -> "
            "watch -> lint -> next round. The supervisor blocks until all requested "
            "rounds complete and lint clean."
        ),
    )
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--schedule-csv", type=Path, default=None)
    parser.add_argument("--start-round-index", type=int, required=True)
    parser.add_argument("--round-count", type=int, required=True)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument(
        "--batch-timeout-seconds",
        type=int,
        default=DEFAULT_BATCH_TIMEOUT_SECONDS,
        help=(
            "Maximum wall-clock time per batch within the main longrun. "
            "When exceeded, the batch is marked deferred_long_tail, its current state is recorded, "
            "and the supervisor continues to later rounds."
        ),
    )
    parser.add_argument(
        "--max-batch-restarts",
        type=int,
        default=DEFAULT_MAX_BATCH_RESTARTS,
        help=(
            "Hard cap on how many reruns one batch may consume within the same run. "
            "The initial launch does not count; only reruns / respawns count. "
            "Once exceeded, the batch is marked retry_capped and the supervisor continues to other queue work."
        ),
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
    parser.add_argument("--codex-bin", default=DEFAULT_CODEX_BIN)
    parser.add_argument("--state-json", type=Path, default=None)
    parser.add_argument("--registry-json", type=Path, default=None)
    parser.add_argument("--events-log", type=Path, default=None)
    parser.add_argument(
        "--disable-split-batch-recovery",
        action="store_true",
        help="Disable automatic 2-worker split recovery for long-tail batches.",
    )
    parser.add_argument(
        "--disable-manual-fallback",
        dest="disable_split_batch_recovery",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--split-batch-respawn-threshold",
        dest="split_batch_respawn_threshold",
        type=int,
        default=DEFAULT_SPLIT_BATCH_RESPAWN_THRESHOLD,
        help="Minimum respawn/attempt count before a batch is eligible for automatic 2-worker split recovery.",
    )
    parser.add_argument(
        "--manual-fallback-respawn-threshold",
        dest="split_batch_respawn_threshold",
        type=int,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--split-batch-failure-threshold",
        dest="split_batch_failure_threshold",
        type=int,
        default=DEFAULT_SPLIT_BATCH_FAILURE_THRESHOLD,
        help="Minimum summed retry failure count before a batch is eligible for automatic 2-worker split recovery.",
    )
    parser.add_argument(
        "--manual-fallback-failure-threshold",
        dest="split_batch_failure_threshold",
        type=int,
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat()


def resolve_runs_path(runs_dir: Path, path: Path | None, fallback_name: str) -> Path:
    if path is None:
        return (runs_dir / fallback_name).resolve()
    return path.resolve() if path.is_absolute() else (runs_dir / path).resolve()


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = [str(name or "").strip() for name in (reader.fieldnames or [])]
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized_row: dict[str, str] = {}
            for original_name, value in raw_row.items():
                key = str(original_name or "").strip()
                normalized_row[key] = "" if value is None else str(value)
            rows.append(normalized_row)
        if fieldnames:
            return [{field: row.get(field, "") for field in fieldnames} for row in rows]
        return rows


def load_csv_rows_with_fields(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = [str(name or "").strip() for name in (reader.fieldnames or [])]
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            normalized_row: dict[str, str] = {}
            for original_name, value in raw_row.items():
                key = str(original_name or "").strip()
                normalized_row[key] = "" if value is None else str(value)
            rows.append({field: normalized_row.get(field, "") for field in fieldnames})
        return fieldnames, rows


def read_schedule(schedule_csv: Path) -> list[dict[str, str]]:
    rows = load_csv_rows(schedule_csv)
    if not rows:
        raise SystemExit(f"Schedule has no rows: {schedule_csv}")
    return rows


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_row_fields(row: dict[str, Any], fieldnames: list[str]) -> dict[str, str]:
    normalized = {field: str(row.get(field, "") or "") for field in fieldnames}
    token_origin_type = normalized.get("token_origin_type", "")
    if token_origin_type == "invesment_or_holdings":
        normalized["token_origin_type"] = "investment_or_holdings"

    if fieldnames == RESULT_CSV_COLUMNS:
        mapped_entity_name = normalized.get("mapped_entity_name", "").strip()
        mapped_entity_legal_name = normalized.get("mapped_entity_legal_name", "").strip()
        mapped_entity_url = normalized.get("mapped_entity_url", "").strip()
        if not mapped_entity_name and not mapped_entity_legal_name and not mapped_entity_url:
            normalized["mapped_entity_name"] = "[]"
            normalized["mapped_entity_legal_name"] = "[]"
            normalized["mapped_entity_type"] = "[]"
            normalized["mapped_entity_url"] = "[]"

        manual_value = normalized.get("needs_manual_review", "").strip()
        confidence_value = normalized.get("confidence", "").strip()
        if manual_value in {"low", "medium", "high"} and not confidence_value:
            normalized["confidence"] = manual_value
            normalized["needs_manual_review"] = "no"

    return normalized


def write_schedule(schedule_csv: Path, rows: list[dict[str, str]]) -> None:
    write_schedule_csv(schedule_csv, rows)


def write_schedule_with_fields(
    schedule_csv: Path,
    fieldnames: list[str] | tuple[str, ...],
    rows: list[dict[str, str]],
) -> list[str]:
    return write_schedule_csv(schedule_csv, rows, fieldnames=list(fieldnames))


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def parse_failure_counts(value: str) -> dict[str, int]:
    raw = (value or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    counts: dict[str, int] = {}
    for key, item in parsed.items():
        counts[str(key)] = parse_int(item, 0)
    return counts


def resolve_repo_path(raw: str) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def read_last_lines(path: Path, limit: int) -> list[str]:
    tail: deque[str] = deque(maxlen=max(limit, 1))
    with path.open("r", encoding="utf-8", errors="replace") as infile:
        for line in infile:
            tail.append(line.rstrip("\n"))
    return list(tail)


def path_mtime_utc(path: Path) -> datetime | None:
    if not path.exists():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def inspect_worker_log_activity(log_path: Path, *, tail_lines: int = WORKER_ACTIVITY_TAIL_LINES) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "available": False,
        "last_activity_at": None,
        "last_activity_type": "",
        "last_activity_source": "",
        "activity_signal_count": 0,
        "strong_activity_count": 0,
    }
    if not log_path.exists() or not log_path.is_file():
        return summary

    summary["available"] = True
    log_mtime = path_mtime_utc(log_path)
    summary["last_activity_at"] = log_mtime

    last_activity_type = ""
    last_activity_source = ""
    activity_signal_count = 0
    strong_activity_count = 0
    for line in read_last_lines(log_path, tail_lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict) or str(payload.get("type") or "").strip() != "item.completed":
            continue
        item = payload.get("item")
        if not isinstance(item, dict):
            continue
        item_type = str(item.get("type") or "").strip()
        if not item_type or item_type not in ANY_WORKER_ACTIVITY_TYPES:
            continue
        activity_signal_count += 1
        last_activity_type = item_type
        if item_type in STRONG_WORKER_ACTIVITY_TYPES:
            strong_activity_count += 1
            last_activity_source = "strong_signal"
        elif not last_activity_source:
            last_activity_source = "command_signal"

    summary["last_activity_type"] = last_activity_type
    summary["last_activity_source"] = last_activity_source
    summary["activity_signal_count"] = activity_signal_count
    summary["strong_activity_count"] = strong_activity_count
    return summary


def activity_is_recent(activity: dict[str, Any], current_time: datetime, *, grace_seconds: int) -> bool:
    if grace_seconds <= 0:
        return False
    last_activity_at = activity.get("last_activity_at")
    if not isinstance(last_activity_at, datetime):
        return False
    if parse_int(activity.get("activity_signal_count"), 0) <= 0:
        return False
    return (current_time - last_activity_at).total_seconds() <= grace_seconds


def activity_timeout_profile(
    *,
    startup_timeout_seconds: int,
    partial_stall_timeout_seconds: int,
) -> dict[str, int]:
    startup_soft = startup_timeout_seconds or DEFAULT_STARTUP_TIMEOUT_SECONDS
    startup_hard = max(startup_soft, 1200 if startup_soft <= DEFAULT_STARTUP_TIMEOUT_SECONDS else startup_soft * 2)
    stall_soft = partial_stall_timeout_seconds or DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS
    stall_hard = max(stall_soft, 900 if stall_soft <= DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS else stall_soft * 3)
    activity_grace = max(180, min(startup_hard, max(stall_soft, 300)))
    return {
        "startup_soft_seconds": startup_soft,
        "startup_hard_seconds": startup_hard,
        "stall_soft_seconds": stall_soft,
        "stall_hard_seconds": stall_hard,
        "activity_grace_seconds": activity_grace,
    }


def round_rows(schedule_rows: list[dict[str, str]], round_index: int) -> list[dict[str, str]]:
    return [
        row
        for row in schedule_rows
        if parse_int(row.get("round_index"), 0) == round_index
    ]


def available_rounds(schedule_rows: list[dict[str, str]]) -> list[int]:
    return sorted(
        {
            parse_int(row.get("round_index"), 0)
            for row in schedule_rows
            if parse_int(row.get("round_index"), 0) > 0
        }
    )


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
    if status == RETRY_CAPPED_STATUS:
        return True
    if status in {"completed", "deferred_long_tail"}:
        return False
    return completion_mode == RETRY_CAPPED_STATUS


def row_has_nonblocking_failure_status(row: dict[str, str]) -> bool:
    status = (row.get("status") or "").strip()
    completion_mode = (row.get("completion_mode") or "").strip()
    if status in NONBLOCKING_FAILURE_STATUSES:
        return True
    if status in {"completed", "deferred_long_tail", RETRY_CAPPED_STATUS}:
        return False
    return completion_mode in NONBLOCKING_FAILURE_STATUSES


def effective_row_status(row: dict[str, str]) -> str:
    if row_has_nonblocking_failure_status(row):
        status = (row.get("status") or "").strip()
        if status in NONBLOCKING_FAILURE_STATUSES:
            return status
        return completion_mode if (completion_mode := (row.get("completion_mode") or "").strip()) else "unknown"
    if row_is_retry_capped(row):
        return RETRY_CAPPED_STATUS
    if row_is_deferred_long_tail(row):
        return "deferred_long_tail"
    return (row.get("status") or "").strip()


def row_is_resolved(row: dict[str, str]) -> bool:
    return effective_row_status(row) in ROUND_RESOLVED_STATUSES


def canonicalize_deferred_long_tail_row(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    updated["status"] = "deferred_long_tail"
    updated["prepared_mode"] = ""
    updated["prepared_reason"] = "long_tail_timeout"
    updated["last_failure_type"] = "long_tail_timeout"
    updated["last_rerun_reason"] = "long_tail_timeout"
    updated["completion_mode"] = "deferred_long_tail"
    if not (updated.get("deferred_reason") or "").strip():
        updated["deferred_reason"] = "batch_timeout_exceeded"
    if not (updated.get("last_rerun_at") or "").strip():
        updated["last_rerun_at"] = str(updated.get("deferred_at") or "")
    return updated


def canonicalize_retry_capped_row(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    updated["status"] = RETRY_CAPPED_STATUS
    updated["prepared_mode"] = ""
    updated["prepared_reason"] = RETRY_CAPPED_REASON
    updated["last_failure_type"] = RETRY_CAPPED_REASON
    updated["last_rerun_reason"] = RETRY_CAPPED_REASON
    updated["completion_mode"] = RETRY_CAPPED_STATUS
    if not (updated.get("deferred_reason") or "").strip():
        updated["deferred_reason"] = RETRY_CAPPED_REASON
    retry_capped_at = str(
        updated.get("retry_capped_at")
        or updated.get("deferred_at")
        or updated.get("last_rerun_at")
        or ""
    ).strip()
    if retry_capped_at:
        updated["retry_capped_at"] = retry_capped_at
        updated["deferred_at"] = updated.get("deferred_at") or retry_capped_at
        updated["last_rerun_at"] = updated.get("last_rerun_at") or retry_capped_at
    return updated


def reconcile_deferred_long_tail_rows(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    changed = False
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        if row_is_retry_capped(updated):
            canonical = canonicalize_retry_capped_row(updated)
            if canonical != updated:
                changed = True
            updated_rows.append(canonical)
            continue
        if row_is_deferred_long_tail(updated):
            canonical = canonicalize_deferred_long_tail_row(updated)
            if canonical != updated:
                changed = True
            updated_rows.append(canonical)
            continue
        updated_rows.append(updated)
    if changed:
        write_schedule(schedule_csv, updated_rows)
    return updated_rows


def determine_resume_round_index(
    schedule_rows: list[dict[str, str]],
    target_rounds: list[int],
) -> int:
    for round_index in target_rounds:
        rows = round_rows(schedule_rows, round_index)
        if rows and any(not row_is_resolved(row) for row in rows):
            return round_index
    return target_rounds[-1] + 1


def round_completed(schedule_rows: list[dict[str, str]], round_index: int) -> bool:
    rows = round_rows(schedule_rows, round_index)
    return bool(rows) and all(row_is_resolved(row) for row in rows)


def summarize_round(schedule_rows: list[dict[str, str]], round_index: int) -> dict[str, Any]:
    rows = round_rows(schedule_rows, round_index)
    status_counts = Counter(effective_row_status(row) for row in rows)
    classifier_rows = sum(parse_int(row.get("last_seen_classifier_rows"), 0) for row in rows)
    result_rows = sum(parse_int(row.get("last_seen_result_rows"), 0) for row in rows)
    return {
        "round_index": round_index,
        "batch_count": len(rows),
        "status_counts": dict(status_counts),
        "classifier_rows": classifier_rows,
        "result_rows": result_rows,
        "completed": round_completed(schedule_rows, round_index),
    }


def parse_iso_optional(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def write_long_tail_backlog(
    runs_dir: Path,
    deferred_rows: list[dict[str, str]],
) -> None:
    csv_path = runs_dir / DEFERRED_LONG_TAIL_CSV
    md_path = runs_dir / DEFERRED_LONG_TAIL_MD
    fieldnames = [
        "round_index",
        "worker_slot",
        "batch_file",
        "run_dir",
        "active_attempt",
        "attempt_index",
        "first_task_index",
        "last_task_index",
        "status",
        "reason",
        "elapsed_seconds",
        "timeout_seconds",
        "classifier_rows",
        "result_rows",
        "round_entry_started_at",
        "first_row_at",
        "last_progress_at",
        "deferred_at",
    ]

    def deferred_backlog_key(row: dict[str, str]) -> str:
        batch_file = str(row.get("batch_file") or "").strip()
        if batch_file:
            return batch_file
        return (
            f"round={parse_int(row.get('round_index'), 0)}|"
            f"slot={str(row.get('worker_slot') or '').strip()}|"
            f"tasks={parse_int(row.get('first_task_index'), 0)}-{parse_int(row.get('last_task_index'), 0)}"
        )

    local_index: dict[str, dict[str, str]] = {}
    for row in load_csv_rows(csv_path):
        local_index[deferred_backlog_key(row)] = {
            field: str(row.get(field) or "")
            for field in fieldnames
        }
    for row in deferred_rows:
        local_index[deferred_backlog_key(row)] = {
            field: str(row.get(field) or "")
            for field in fieldnames
        }
    merged_local_rows = sorted(
        local_index.values(),
        key=lambda row: (
            parse_int(row.get("round_index"), 0),
            parse_int(row.get("first_task_index"), 0),
            str(row.get("batch_file") or ""),
        ),
    )
    write_csv_rows(csv_path, fieldnames, merged_local_rows)

    lines = [
        "# Deferred Long Tail Batches",
        "",
        "These batches exceeded the main-run wall clock budget and were deferred for a later dedicated rerun.",
        "",
    ]
    for row in merged_local_rows:
        lines.append(
            f"- round {row['round_index']} {Path(row['batch_file']).name}: "
            f"{row['classifier_rows']}/{row['result_rows']} rows seen, "
            f"elapsed={row['elapsed_seconds']}s, reason={row['reason']}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    backlog_path = GLOBAL_LONG_TAIL_BACKLOG_CSV
    existing_rows = load_csv_rows(backlog_path)
    index: dict[str, dict[str, str]] = {}
    for row in existing_rows:
        key = deferred_backlog_key(row)
        index[key] = {
            "runs_dir": str(row.get("runs_dir") or ""),
            **{
                field: str(row.get(field) or "")
                for field in fieldnames
            },
        }
    for row in deferred_rows:
        enriched = dict(row)
        enriched["runs_dir"] = str(runs_dir)
        key = deferred_backlog_key(enriched)
        index[key] = {
            "runs_dir": str(enriched.get("runs_dir") or ""),
            **{
                field: str(enriched.get(field) or "")
                for field in fieldnames
            },
        }
    merged_rows = sorted(
        index.values(),
        key=lambda row: (
            parse_int(row.get("round_index"), 0),
            parse_int(row.get("first_task_index"), 0),
            str(row.get("batch_file") or ""),
        ),
    )
    write_csv_rows(
        backlog_path,
        ["runs_dir"] + fieldnames,
        merged_rows,
    )


def write_retry_capped_backlog(
    runs_dir: Path,
    capped_rows: list[dict[str, str]],
) -> None:
    csv_path = runs_dir / RETRY_CAPPED_CSV
    md_path = runs_dir / RETRY_CAPPED_MD
    fieldnames = [
        "round_index",
        "worker_slot",
        "batch_file",
        "run_dir",
        "active_attempt",
        "attempt_index",
        "attempt_rerun_count",
        "respawn_count",
        "split_max_spawn_count",
        "split_total_spawn_count",
        "split_max_rerun_count",
        "split_total_rerun_count",
        "rerun_count",
        "restart_count",
        "max_batch_restarts",
        "first_task_index",
        "last_task_index",
        "status",
        "reason",
        "classifier_rows",
        "result_rows",
        "round_entry_started_at",
        "first_row_at",
        "last_progress_at",
        "retry_capped_at",
    ]

    def capped_backlog_key(row: dict[str, str]) -> str:
        batch_file = str(row.get("batch_file") or "").strip()
        if batch_file:
            return batch_file
        return (
            f"round={parse_int(row.get('round_index'), 0)}|"
            f"slot={str(row.get('worker_slot') or '').strip()}|"
            f"tasks={parse_int(row.get('first_task_index'), 0)}-{parse_int(row.get('last_task_index'), 0)}"
        )

    local_index: dict[str, dict[str, str]] = {}
    for row in load_csv_rows(csv_path):
        local_index[capped_backlog_key(row)] = {
            field: str(row.get(field) or "")
            for field in fieldnames
        }
    for row in capped_rows:
        local_index[capped_backlog_key(row)] = {
            field: str(row.get(field) or "")
            for field in fieldnames
        }
    merged_local_rows = sorted(
        local_index.values(),
        key=lambda row: (
            parse_int(row.get("round_index"), 0),
            parse_int(row.get("first_task_index"), 0),
            str(row.get("batch_file") or ""),
        ),
    )
    write_csv_rows(csv_path, fieldnames, merged_local_rows)

    lines = [
        "# Retry-Capped Batches",
        "",
        "These batches exceeded the configured restart budget and were capped so the queue could continue.",
        "",
    ]
    for row in merged_local_rows:
        lines.append(
            f"- round {row['round_index']} {Path(row['batch_file']).name}: "
            f"rerun_count={row['rerun_count']}/{row['max_batch_restarts']}, "
            f"rows={row['classifier_rows']}/{row['result_rows']}, reason={row['reason']}"
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    backlog_path = GLOBAL_RETRY_CAPPED_BACKLOG_CSV
    existing_rows = load_csv_rows(backlog_path)
    index: dict[str, dict[str, str]] = {}
    for row in existing_rows:
        key = capped_backlog_key(row)
        index[key] = {
            "runs_dir": str(row.get("runs_dir") or ""),
            **{
                field: str(row.get(field) or "")
                for field in fieldnames
            },
        }
    for row in capped_rows:
        enriched = dict(row)
        enriched["runs_dir"] = str(runs_dir)
        key = capped_backlog_key(enriched)
        index[key] = {
            "runs_dir": str(enriched.get("runs_dir") or ""),
            **{
                field: str(enriched.get(field) or "")
                for field in fieldnames
            },
        }
    merged_rows = sorted(
        index.values(),
        key=lambda row: (
            parse_int(row.get("round_index"), 0),
            parse_int(row.get("first_task_index"), 0),
            str(row.get("batch_file") or ""),
        ),
    )
    write_csv_rows(
        backlog_path,
        ["runs_dir"] + fieldnames,
        merged_rows,
    )


def compute_restart_metrics(
    row: dict[str, str],
    *,
    split_state: dict[str, Any] | None = None,
) -> dict[str, int]:
    if split_state is None:
        split_state = load_json_dict(split_state_path_for_row(row))
    shard_spawn_counts = [
        parse_int(shard.get("spawn_count"), 0)
        for shard in split_state.get("shards", [])
        if isinstance(shard, dict)
    ]
    attempt_index = parse_int(row.get("attempt_index"), 0)
    attempt_rerun_count = max(attempt_index - 1, 0)
    respawn_count = parse_int(row.get("respawn_count"), 0)
    split_max_spawn_count = max(shard_spawn_counts, default=0)
    split_total_spawn_count = sum(shard_spawn_counts)
    split_max_rerun_count = max(split_max_spawn_count - 1, 0)
    split_total_rerun_count = sum(max(count - 1, 0) for count in shard_spawn_counts)
    rerun_count = max(attempt_rerun_count, respawn_count, split_max_rerun_count)
    return {
        "attempt_index": attempt_index,
        "attempt_rerun_count": attempt_rerun_count,
        "respawn_count": respawn_count,
        "split_max_spawn_count": split_max_spawn_count,
        "split_total_spawn_count": split_total_spawn_count,
        "split_max_rerun_count": split_max_rerun_count,
        "split_total_rerun_count": split_total_rerun_count,
        "rerun_count": rerun_count,
        "restart_count": rerun_count,
    }


def analyze_retry_capped_rows(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    *,
    max_batch_restarts: int,
) -> list[dict[str, str]]:
    if max_batch_restarts <= 0:
        return []

    retry_capped_rows: list[dict[str, str]] = []
    for row in round_rows(schedule_rows, round_index):
        if row_is_resolved(row):
            continue
        split_state = load_json_dict(split_state_path_for_row(row))
        metrics = compute_restart_metrics(row, split_state=split_state)
        if metrics["rerun_count"] <= max_batch_restarts:
            continue
        retry_capped_rows.append(
            {
                "round_index": str(row.get("round_index") or ""),
                "worker_slot": str(row.get("worker_slot") or ""),
                "batch_file": str(row.get("batch_file") or ""),
                "run_dir": str(row.get("run_dir") or ""),
                "active_attempt": str(row.get("active_attempt") or ""),
                "attempt_index": str(metrics["attempt_index"]),
                "attempt_rerun_count": str(metrics["attempt_rerun_count"]),
                "respawn_count": str(metrics["respawn_count"]),
                "split_max_spawn_count": str(metrics["split_max_spawn_count"]),
                "split_total_spawn_count": str(metrics["split_total_spawn_count"]),
                "split_max_rerun_count": str(metrics["split_max_rerun_count"]),
                "split_total_rerun_count": str(metrics["split_total_rerun_count"]),
                "rerun_count": str(metrics["rerun_count"]),
                "restart_count": str(metrics["restart_count"]),
                "max_batch_restarts": str(max_batch_restarts),
                "first_task_index": str(row.get("first_task_index") or ""),
                "last_task_index": str(row.get("last_task_index") or ""),
                "status": RETRY_CAPPED_STATUS,
                "reason": RETRY_CAPPED_REASON,
                "classifier_rows": str(row.get("last_seen_classifier_rows") or "0"),
                "result_rows": str(row.get("last_seen_result_rows") or "0"),
                "round_entry_started_at": str(row.get("round_entry_started_at") or ""),
                "first_row_at": str(row.get("first_row_at") or ""),
                "last_progress_at": str(row.get("last_progress_at") or ""),
                "retry_capped_at": iso_now(),
            }
        )
    return retry_capped_rows


def analyze_long_tail_deferred_rows(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    *,
    timeout_seconds: int,
) -> list[dict[str, str]]:
    if timeout_seconds <= 0:
        return []

    now = now_utc()
    deferred_rows: list[dict[str, str]] = []
    for row in round_rows(schedule_rows, round_index):
        if row_is_resolved(row):
            continue

        round_entry_started_at = parse_iso_optional(str(row.get("round_entry_started_at") or ""))
        if round_entry_started_at is None:
            round_entry_started_at = (
                parse_iso_optional(str(row.get("started_at") or ""))
                or parse_iso_optional(str(row.get("first_row_at") or ""))
            )
        if round_entry_started_at is None:
            continue

        elapsed_seconds = int((now - round_entry_started_at).total_seconds())
        if elapsed_seconds < timeout_seconds:
            continue

        deferred_rows.append(
            {
                "round_index": str(row.get("round_index") or ""),
                "worker_slot": str(row.get("worker_slot") or ""),
                "batch_file": str(row.get("batch_file") or ""),
                "run_dir": str(row.get("run_dir") or ""),
                "active_attempt": str(row.get("active_attempt") or ""),
                "attempt_index": str(row.get("attempt_index") or ""),
                "first_task_index": str(row.get("first_task_index") or ""),
                "last_task_index": str(row.get("last_task_index") or ""),
                "status": "deferred_long_tail",
                "reason": "batch_timeout_exceeded",
                "elapsed_seconds": str(elapsed_seconds),
                "timeout_seconds": str(timeout_seconds),
                "classifier_rows": str(row.get("last_seen_classifier_rows") or "0"),
                "result_rows": str(row.get("last_seen_result_rows") or "0"),
                "round_entry_started_at": str(row.get("round_entry_started_at") or ""),
                "first_row_at": str(row.get("first_row_at") or ""),
                "last_progress_at": str(row.get("last_progress_at") or ""),
                "deferred_at": iso_now(),
            }
        )
    return deferred_rows


def mark_long_tail_deferred(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    deferred_rows: list[dict[str, str]],
    *,
    schedule_fieldnames: list[str] | None = None,
    runs_dir: Path,
    events_log: Path,
) -> list[dict[str, str]]:
    if not deferred_rows:
        return schedule_rows

    deferred_by_batch = {str(row.get("batch_file") or ""): row for row in deferred_rows}
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        batch_file = str(updated.get("batch_file") or "")
        deferred = deferred_by_batch.get(batch_file)
        if not deferred:
            updated_rows.append(updated)
            continue

        updated["status"] = "deferred_long_tail"
        updated["prepared_mode"] = ""
        updated["prepared_reason"] = "long_tail_timeout"
        updated["last_failure_type"] = "long_tail_timeout"
        updated["last_rerun_reason"] = "long_tail_timeout"
        updated["last_rerun_at"] = str(deferred.get("deferred_at") or iso_now())
        updated["planned_rotate"] = ""
        updated["completion_mode"] = "deferred_long_tail"
        updated["deferred_at"] = str(deferred.get("deferred_at") or iso_now())
        updated["deferred_reason"] = str(deferred.get("reason") or "batch_timeout_exceeded")
        split_state = load_json_dict(split_state_path_for_row(updated))
        if split_state_active(split_state):
            split_state["state"] = "deferred_long_tail"
            split_state["deferred_at"] = updated["deferred_at"]
            write_json_dict(split_state_path_for_row(updated), split_state)
        log_event(
            events_log,
            (
                "[long_tail:deferred] "
                f"round={updated.get('round_index', '')} slot={updated.get('worker_slot', '')} "
                f"batch={batch_file} attempt={updated.get('attempt_index', '')} "
                f"classifier_rows={updated.get('last_seen_classifier_rows', '0')} "
                f"result_rows={updated.get('last_seen_result_rows', '0')}"
            ),
        )
        updated_rows.append(updated)

    fieldnames = list(schedule_fieldnames or [])
    if not fieldnames:
        fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
    if not fieldnames and updated_rows:
        fieldnames = list(updated_rows[0].keys())
    write_schedule_with_fields(schedule_csv, fieldnames, updated_rows)
    write_long_tail_backlog(runs_dir, deferred_rows)
    return updated_rows


def mark_retry_capped_rows(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    retry_capped_rows: list[dict[str, str]],
    *,
    schedule_fieldnames: list[str] | None = None,
    runs_dir: Path,
    events_log: Path,
) -> list[dict[str, str]]:
    if not retry_capped_rows:
        return schedule_rows

    capped_by_batch = {str(row.get("batch_file") or ""): row for row in retry_capped_rows}
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        batch_file = str(updated.get("batch_file") or "")
        capped = capped_by_batch.get(batch_file)
        if not capped:
            updated_rows.append(updated)
            continue

        retry_capped_at = str(capped.get("retry_capped_at") or iso_now())
        updated["status"] = RETRY_CAPPED_STATUS
        updated["prepared_mode"] = ""
        updated["prepared_reason"] = RETRY_CAPPED_REASON
        updated["last_failure_type"] = RETRY_CAPPED_REASON
        updated["last_rerun_reason"] = RETRY_CAPPED_REASON
        updated["last_rerun_at"] = retry_capped_at
        updated["planned_rotate"] = ""
        updated["completion_mode"] = RETRY_CAPPED_STATUS
        updated["deferred_at"] = str(updated.get("deferred_at") or retry_capped_at)
        updated["deferred_reason"] = str(capped.get("reason") or RETRY_CAPPED_REASON)
        updated["retry_capped_at"] = retry_capped_at
        rerun_count = str(capped.get("rerun_count") or capped.get("restart_count") or "")
        updated["retry_cap_rerun_count"] = rerun_count
        updated["retry_cap_restart_count"] = rerun_count
        updated["retry_cap_limit"] = str(capped.get("max_batch_restarts") or "")
        split_state = load_json_dict(split_state_path_for_row(updated))
        if split_state_active(split_state):
            split_state["state"] = RETRY_CAPPED_STATUS
            split_state["retry_capped_at"] = retry_capped_at
            split_state["retry_cap_rerun_count"] = updated["retry_cap_rerun_count"]
            split_state["retry_cap_restart_count"] = updated["retry_cap_restart_count"]
            split_state["retry_cap_limit"] = updated["retry_cap_limit"]
            write_json_dict(split_state_path_for_row(updated), split_state)
        log_event(
            events_log,
            (
                "[retry_cap:deferred] "
                f"round={updated.get('round_index', '')} slot={updated.get('worker_slot', '')} "
                f"batch={batch_file} attempt={updated.get('attempt_index', '')} "
                f"rerun_count={updated.get('retry_cap_rerun_count', '')} "
                f"limit={updated.get('retry_cap_limit', '')} "
                f"classifier_rows={updated.get('last_seen_classifier_rows', '0')} "
                f"result_rows={updated.get('last_seen_result_rows', '0')}"
            ),
        )
        updated_rows.append(updated)

    fieldnames = list(schedule_fieldnames or [])
    if not fieldnames:
        fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
    if not fieldnames and updated_rows:
        fieldnames = list(updated_rows[0].keys())
    write_schedule_with_fields(schedule_csv, fieldnames, updated_rows)
    write_retry_capped_backlog(runs_dir, retry_capped_rows)
    return updated_rows


def log_event(events_log: Path, message: str) -> None:
    events_log.parent.mkdir(parents=True, exist_ok=True)
    with events_log.open("a", encoding="utf-8") as outfile:
        outfile.write(f"{iso_now()} {message}\n")


def signal_name(signum: int) -> str:
    try:
        return signal.Signals(signum).name
    except ValueError:
        return f"SIG{signum}"


def _supervisor_signal_handler(signum: int, _frame: object) -> None:
    raise SupervisorSignalExit(signum)


def install_supervisor_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, _supervisor_signal_handler)
    signal.signal(signal.SIGINT, _supervisor_signal_handler)


def set_supervisor_context(
    *,
    runs_dir: Path,
    schedule_csv: Path,
    state_json: Path,
    registry_json: Path,
    events_log: Path,
    target_rounds: list[int],
    scheduler_mode: str,
) -> None:
    SUPERVISOR_CONTEXT.clear()
    SUPERVISOR_CONTEXT.update(
        {
            "runs_dir": runs_dir,
            "schedule_csv": schedule_csv,
            "state_json": state_json,
            "registry_json": registry_json,
            "events_log": events_log,
            "target_rounds": list(target_rounds),
            "scheduler_mode": str(scheduler_mode or "round"),
        }
    )


def launcher_state_path_for_runs_dir(runs_dir: Path) -> Path:
    return runs_dir / "launcher_state.json"


def should_update_latest_job_record(
    existing_payload: dict[str, Any],
    candidate_payload: dict[str, Any],
) -> bool:
    if not existing_payload:
        return True
    existing_runs_dir = str(existing_payload.get("runs_dir") or "").strip()
    candidate_runs_dir = str(candidate_payload.get("runs_dir") or "").strip()
    if existing_runs_dir and candidate_runs_dir and existing_runs_dir == candidate_runs_dir:
        return True

    existing_launched_at = parse_iso_optional(str(existing_payload.get("launched_at") or ""))
    candidate_launched_at = parse_iso_optional(str(candidate_payload.get("launched_at") or ""))
    if candidate_launched_at is not None and existing_launched_at is not None:
        return candidate_launched_at >= existing_launched_at
    if candidate_launched_at is not None and existing_launched_at is None:
        return True
    if candidate_launched_at is None and existing_launched_at is not None:
        return False
    if candidate_runs_dir and not existing_runs_dir:
        return True
    return False


def write_latest_job_record_if_current(path: Path, payload: dict[str, Any]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing_payload = load_json_dict(path)
    if not should_update_latest_job_record(existing_payload, payload):
        return False
    write_json_dict(path, payload)
    return True


def update_launcher_state_status(
    runs_dir: Path,
    *,
    status: str,
    extra: dict[str, Any] | None = None,
) -> None:
    launcher_path = launcher_state_path_for_runs_dir(runs_dir)
    payload = load_json_dict(launcher_path)
    payload["runs_dir"] = str(runs_dir)
    payload["latest_job_json"] = str(
        payload.get("latest_job_json")
        or (PART4_DIR / "agent_runs" / "token_company_longrun_latest.json")
    )
    payload["status"] = status
    payload["status_updated_at"] = iso_now()
    if extra:
        payload.update(extra)
    launcher_path.parent.mkdir(parents=True, exist_ok=True)
    launcher_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    latest_job_raw = str(payload.get("latest_job_json") or "").strip()
    if latest_job_raw:
        latest_job_path = Path(latest_job_raw).expanduser()
        write_latest_job_record_if_current(latest_job_path, payload)


def current_round_index_from_state(
    state_json: Path,
    target_rounds: list[int],
) -> int:
    current_round_index = target_rounds[0] if target_rounds else 0
    state_existing = load_json_dict(state_json)
    if state_existing:
        current_round_index = parse_int(state_existing.get("current_round_index"), current_round_index)
    return current_round_index


def write_lifecycle_state(
    path: Path,
    *,
    runs_dir: Path,
    target_rounds: list[int],
    current_round_index: int,
    phase: str,
    schedule_rows: list[dict[str, str]],
    registry: list[dict[str, Any]],
    scheduler_mode: str,
    lifecycle_status: str,
    lifecycle_reason: str,
) -> None:
    payload = load_json_dict(path)
    payload.update(
        {
            "updated_at": iso_now(),
            "runs_dir": str(runs_dir),
            "target_rounds": target_rounds,
            "current_round_index": current_round_index,
            "phase": phase,
            "scheduler_mode": scheduler_mode,
            "managed_processes": registry,
            "round_summaries": {
                str(round_index): summarize_round(schedule_rows, round_index)
                for round_index in target_rounds
            },
            "lifecycle_status": lifecycle_status,
            "lifecycle_reason": lifecycle_reason,
            "lifecycle_updated_at": iso_now(),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def log_supervisor_terminal_failure(exc: BaseException) -> None:
    if SUPERVISOR_SHUTDOWN_HANDLED:
        return
    events_log_raw = SUPERVISOR_CONTEXT.get("events_log")
    runs_dir_raw = SUPERVISOR_CONTEXT.get("runs_dir")
    schedule_csv_raw = SUPERVISOR_CONTEXT.get("schedule_csv")
    state_json_raw = SUPERVISOR_CONTEXT.get("state_json")
    registry_json_raw = SUPERVISOR_CONTEXT.get("registry_json")
    target_rounds_raw = SUPERVISOR_CONTEXT.get("target_rounds")

    if not isinstance(events_log_raw, Path):
        return

    detail = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)).rstrip()
    if isinstance(exc, SystemExit):
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 0:
            return
        log_event(events_log_raw, f"[supervisor:exit_nonzero] code={code} detail={detail}")
    else:
        log_event(events_log_raw, f"[supervisor:fatal] {detail}")

    try:
        finalize_supervisor_abort(
            reason=SUPERVISOR_FATAL_REASON,
            phase="failed",
            launcher_status="failed",
        )
    except BaseException:
        return


def load_registry(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(payload, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in payload:
        if isinstance(item, dict):
            cleaned.append(item)
    return cleaned


def save_registry(path: Path, registry: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_state(
    path: Path,
    *,
    runs_dir: Path,
    target_rounds: list[int],
    current_round_index: int,
    phase: str,
    schedule_rows: list[dict[str, str]],
    registry: list[dict[str, Any]],
) -> None:
    payload = {
        "updated_at": iso_now(),
        "runs_dir": str(runs_dir),
        "target_rounds": target_rounds,
        "current_round_index": current_round_index,
        "phase": phase,
        "scheduler_mode": "round",
        "strict_wait_for_all_rounds": True,
        "round_summaries": {
            str(round_index): summarize_round(schedule_rows, round_index)
            for round_index in target_rounds
        },
        "managed_processes": registry,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_command(cmd: list[str], *, cwd: Path, events_log: Path, label: str) -> subprocess.CompletedProcess[str]:
    log_event(events_log, f"[command:start] {label}: {' '.join(shlex.quote(part) for part in cmd)}")
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
    )
    if completed.stdout.strip():
        log_event(events_log, f"[command:stdout] {label}:\n{completed.stdout.rstrip()}")
    if completed.stderr.strip():
        log_event(events_log, f"[command:stderr] {label}:\n{completed.stderr.rstrip()}")
    log_event(events_log, f"[command:end] {label}: returncode={completed.returncode}")
    return completed


def process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def process_group_alive(pgid: int) -> bool:
    if pgid <= 0:
        return False
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def registry_entry_alive(entry: dict[str, Any]) -> bool:
    pid = parse_int(entry.get("pid"), 0)
    pgid = parse_int(entry.get("pgid"), 0)
    return process_alive(pid) or process_group_alive(pgid)


def build_worker_preexec_fn(parent_pid: int):
    def _preexec() -> None:
        os.setsid()
        try:
            libc = ctypes.CDLL(None)
            if hasattr(libc, "prctl"):
                libc.prctl(PR_SET_PDEATHSIG, signal.SIGTERM, 0, 0, 0)
        except BaseException:
            pass
        if os.getppid() != parent_pid:
            os.kill(os.getpid(), signal.SIGTERM)

    return _preexec


def resolve_codex_bin(binary: str) -> str:
    candidate = str(binary or "").strip()
    if not candidate:
        raise SystemExit("codex binary path is empty.")
    expanded = Path(candidate).expanduser()
    if expanded.is_absolute():
        if expanded.exists():
            return str(expanded.resolve())
        raise SystemExit(f"codex binary not found: {candidate}")
    resolved = shutil_which(candidate)
    if resolved:
        return str(Path(resolved).resolve())
    raise SystemExit(f"codex binary not found: {candidate}")


def process_cmdline(pid: int) -> str:
    if pid <= 0:
        return ""
    try:
        return Path(f"/proc/{pid}/cmdline").read_text(encoding="utf-8", errors="ignore").replace("\x00", " ").strip()
    except OSError:
        return ""


def supervisor_process_matches(pid: int, *, runs_dir: Path) -> bool:
    cmdline = process_cmdline(pid)
    if not cmdline:
        return False
    return (
        ("5_run_round_supervisor.py" in cmdline or "5_run_queue_supervisor.py" in cmdline)
        and str(runs_dir) in cmdline
    )


def acquire_supervisor_lock(path: Path, *, runs_dir: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        existing_pid = parse_int(payload.get("pid"), 0)
        existing_runs_dir = str(payload.get("runs_dir") or "")
        if (
            existing_pid > 0
            and process_alive(existing_pid)
            and supervisor_process_matches(existing_pid, runs_dir=Path(existing_runs_dir or runs_dir))
        ):
            raise SystemExit(
                f"Another supervisor is already running for {existing_runs_dir or runs_dir}: pid={existing_pid}"
            )
    payload = {
        "pid": os.getpid(),
        "runs_dir": str(runs_dir),
        "started_at": iso_now(),
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def _cleanup() -> None:
        try:
            if not path.exists():
                return
            payload = json.loads(path.read_text(encoding="utf-8"))
            if parse_int(payload.get("pid"), 0) == os.getpid():
                path.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError):
            return

    atexit.register(_cleanup)


def terminate_process_group(*, pid: int, pgid: int, events_log: Path, reason: str) -> None:
    resolved_pgid = pgid
    if resolved_pgid <= 0 and pid > 0:
        try:
            resolved_pgid = os.getpgid(pid)
        except ProcessLookupError:
            resolved_pgid = 0

    if resolved_pgid > 0 and process_group_alive(resolved_pgid):
        log_event(events_log, f"[worker:terminate] pid={pid} pgid={resolved_pgid} reason={reason}")
        try:
            os.killpg(resolved_pgid, signal.SIGTERM)
        except ProcessLookupError:
            resolved_pgid = 0
        deadline = time.time() + 10
        while resolved_pgid > 0 and time.time() < deadline:
            if not process_group_alive(resolved_pgid):
                return
            time.sleep(0.25)
        if resolved_pgid > 0 and process_group_alive(resolved_pgid):
            try:
                os.killpg(resolved_pgid, signal.SIGKILL)
            except ProcessLookupError:
                return
        return

    if pid <= 0 or not process_alive(pid):
        return
    log_event(events_log, f"[worker:terminate_fallback_pid] pid={pid} reason={reason}")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + 10
    while time.time() < deadline:
        if not process_alive(pid):
            return
        time.sleep(0.25)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def terminate_registry_entry(entry: dict[str, Any], events_log: Path, reason: str) -> None:
    terminate_process_group(
        pid=parse_int(entry.get("pid"), 0),
        pgid=parse_int(entry.get("pgid"), 0),
        events_log=events_log,
        reason=reason,
    )


def cleanup_registry(registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in registry:
        if registry_entry_alive(item):
            cleaned.append(item)
    return cleaned


def mark_schedule_for_supervisor_abort(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    *,
    reason: str,
) -> list[dict[str, str]]:
    now_iso = iso_now()
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        status = effective_row_status(updated)
        queue_state = str(updated.get("queue_state") or "").strip()
        collect_state = str(updated.get("collect_state") or "").strip()
        current_progress_rows = min(
            parse_int(updated.get("last_seen_classifier_rows"), 0),
            parse_int(updated.get("last_seen_result_rows"), 0),
        )
        attempt_start_prefix_rows = parse_int(updated.get("attempt_start_prefix_rows"), 0)

        if status == "completed":
            if collect_state == "running":
                updated["collect_state"] = "pending"
                updated["collect_failure_reason"] = reason
                updated["queue_state"] = "ready_to_collect"
                updated["ready_to_collect_at"] = (
                    str(updated.get("ready_to_collect_at") or "").strip()
                    or str(updated.get("last_progress_at") or "").strip()
                    or now_iso
                )
                updated["slot_id"] = ""
            updated_rows.append(updated)
            continue

        inflight = status == "running" or queue_state in {"launching", "running", "collecting", SUPERVISOR_LOST_QUEUE_STATE}
        if inflight:
            counts = parse_failure_counts(updated.get("failure_counts_json", ""))
            counts[reason] = counts.get(reason, 0) + 1
            updated["status"] = "needs_rerun"
            updated["prepared_mode"] = "continue_from_prefix" if current_progress_rows > attempt_start_prefix_rows else "fresh_restart"
            updated["prepared_reason"] = reason
            updated["last_failure_type"] = reason
            updated["failure_counts_json"] = json.dumps(counts, ensure_ascii=False, separators=(",", ":"))
            updated["last_rerun_reason"] = reason
            updated["last_rerun_at"] = now_iso
            updated["planned_rotate"] = ""
            updated["queue_state"] = SUPERVISOR_LOST_QUEUE_STATE
            updated["collect_state"] = "pending"
            updated["collect_failure_reason"] = reason
            updated["tail_retry_pending"] = ""
            updated["slot_id"] = ""
            updated_rows.append(updated)
            continue

        updated_rows.append(updated)

    fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
    write_schedule_with_fields(schedule_csv, fieldnames, updated_rows)
    return updated_rows


def finalize_supervisor_abort(
    *,
    reason: str,
    phase: str,
    launcher_status: str,
    signal_text: str = "",
) -> None:
    global SUPERVISOR_SHUTDOWN_HANDLED
    if SUPERVISOR_SHUTDOWN_HANDLED:
        return
    SUPERVISOR_SHUTDOWN_HANDLED = True

    runs_dir_raw = SUPERVISOR_CONTEXT.get("runs_dir")
    schedule_csv_raw = SUPERVISOR_CONTEXT.get("schedule_csv")
    state_json_raw = SUPERVISOR_CONTEXT.get("state_json")
    registry_json_raw = SUPERVISOR_CONTEXT.get("registry_json")
    events_log_raw = SUPERVISOR_CONTEXT.get("events_log")
    target_rounds_raw = SUPERVISOR_CONTEXT.get("target_rounds")
    scheduler_mode = str(SUPERVISOR_CONTEXT.get("scheduler_mode") or "round")
    if not all(isinstance(item, Path) for item in [runs_dir_raw, schedule_csv_raw, state_json_raw, registry_json_raw, events_log_raw]):
        return
    if not isinstance(target_rounds_raw, list) or not target_rounds_raw:
        return

    log_suffix = f" signal={signal_text}" if signal_text else ""
    log_event(events_log_raw, f"[supervisor:abort] reason={reason} phase={phase}{log_suffix}")

    registry = cleanup_registry(load_registry(registry_json_raw))
    for entry in list(registry):
        terminate_registry_entry(entry, events_log_raw, reason)
    registry = cleanup_registry(load_registry(registry_json_raw))
    save_registry(registry_json_raw, registry)

    schedule_rows = read_schedule(schedule_csv_raw)
    schedule_rows = mark_schedule_for_supervisor_abort(
        schedule_csv_raw,
        schedule_rows,
        reason=reason,
    )
    current_round_index = current_round_index_from_state(state_json_raw, target_rounds_raw)
    write_lifecycle_state(
        state_json_raw,
        runs_dir=runs_dir_raw,
        target_rounds=target_rounds_raw,
        current_round_index=current_round_index,
        phase=phase,
        schedule_rows=schedule_rows,
        registry=registry,
        scheduler_mode=scheduler_mode,
        lifecycle_status=launcher_status,
        lifecycle_reason=reason,
    )
    update_launcher_state_status(
        runs_dir_raw,
        status=launcher_status,
        extra={
            "shutdown_reason": reason,
            "shutdown_signal": signal_text,
        },
    )


def handle_supervisor_signal_exit(exc: SupervisorSignalExit) -> None:
    finalize_supervisor_abort(
        reason=SUPERVISOR_LOST_REASON,
        phase="abandoned",
        launcher_status="abandoned_by_supervisor",
        signal_text=signal_name(exc.signum),
    )


def terminate_for_batch_files(
    batch_files: set[str],
    registry: list[dict[str, Any]],
    events_log: Path,
    *,
    reason: str,
) -> list[dict[str, Any]]:
    if not batch_files:
        return cleanup_registry(registry)
    remaining: list[dict[str, Any]] = []
    for entry in registry:
        entry_batch = str(entry.get("batch_file") or "").strip()
        if entry_batch in batch_files:
            terminate_registry_entry(entry, events_log, reason)
        else:
            remaining.append(entry)
    return cleanup_registry(remaining)


def registry_match(action: dict[str, str], entry: dict[str, Any]) -> bool:
    action_lease = (action.get("lease_id") or "").strip()
    entry_lease = str(entry.get("lease_id") or "").strip()
    if action_lease and entry_lease and action_lease == entry_lease:
        return True
    action_batch = (action.get("batch_file") or "").strip()
    entry_batch = str(entry.get("batch_file") or "").strip()
    action_attempt = parse_int(action.get("attempt_index"), 0)
    entry_attempt = parse_int(entry.get("attempt_index"), 0)
    return bool(action_batch) and action_batch == entry_batch and action_attempt == entry_attempt


def terminate_for_round(round_index: int, registry: list[dict[str, Any]], events_log: Path) -> list[dict[str, Any]]:
    remaining: list[dict[str, Any]] = []
    for entry in registry:
        if parse_int(entry.get("round_index"), 0) == round_index:
            terminate_registry_entry(entry, events_log, f"round_{round_index}_cleanup")
        else:
            remaining.append(entry)
    return cleanup_registry(remaining)


def active_full_batch_running(
    registry: list[dict[str, Any]],
    *,
    batch_file: str,
    attempt_index: int,
) -> bool:
    for entry in registry:
        if str(entry.get("split_shard_id") or "").strip():
            continue
        if str(entry.get("batch_file") or "") != batch_file:
            continue
        if parse_int(entry.get("attempt_index"), 0) != attempt_index:
            continue
        if registry_entry_alive(entry):
            return True
    return False


def detect_dead_worker_reason(log_path: Path) -> str:
    if not log_path.exists():
        return "worker_process_exited"
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return "worker_process_exited"
    lowered = text.lower()
    if "context window" in lowered or "ran out of room in the model's context window" in lowered:
        return "context_window_exhausted"
    if "turn.failed" in lowered:
        return "worker_turn_failed"
    return "worker_process_exited"


def clear_rerun_runtime_markers(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    updated["queue_state"] = "queued"
    updated["slot_id"] = ""
    updated["started_at"] = ""
    updated["round_entry_started_at"] = ""
    updated["health_state"] = "needs_rerun"
    updated["soft_timeout_warned_at"] = ""
    updated["last_timeout_warning_reason"] = ""
    updated["next_eligible_retry_at"] = ""
    return updated


def mark_dead_worker_reruns(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    *,
    round_index: int,
    registry: list[dict[str, Any]],
    events_log: Path,
) -> tuple[list[dict[str, str]], bool]:
    changed = False
    updated_rows: list[dict[str, str]] = []
    now_iso = iso_now()
    for row in schedule_rows:
        updated = dict(row)
        if row_is_deferred_long_tail(updated):
            updated_rows.append(canonicalize_deferred_long_tail_row(updated))
            continue
        if parse_int(updated.get("round_index"), 0) != round_index:
            updated_rows.append(updated)
            continue
        if (updated.get("status") or "").strip() != "running":
            updated_rows.append(updated)
            continue
        if split_state_active(load_json_dict(split_state_path_for_row(updated))):
            updated_rows.append(updated)
            continue

        batch_file = str(updated.get("batch_file") or "")
        attempt_index = parse_int(updated.get("attempt_index"), 0)
        if active_full_batch_running(registry, batch_file=batch_file, attempt_index=attempt_index):
            updated_rows.append(updated)
            continue

        tasks_path = resolve_repo_path(str(updated.get("tasks_file") or ""))
        classifier_path = resolve_repo_path(str(updated.get("classifier_results_csv") or ""))
        results_path = resolve_repo_path(str(updated.get("results_csv") or ""))
        tasks = load_jsonl_tasks(tasks_path)
        inspection = inspect_attempt_outputs(
            classifier_path=classifier_path,
            results_path=results_path,
            tasks=tasks,
        )
        if inspection["state"] == "completed":
            updated["status"] = "completed"
            updated["completion_mode"] = updated.get("completion_mode") or "normal"
            updated["prepared_mode"] = ""
            updated["prepared_reason"] = ""
            updated["planned_rotate"] = ""
            updated["last_seen_classifier_rows"] = str(inspection["classifier_rows"])
            updated["last_seen_result_rows"] = str(inspection["result_rows"])
            updated["last_progress_at"] = now_iso
            log_event(
                events_log,
                (
                    "[worker:reconciled_completed] "
                    f"round={updated.get('round_index', '')} slot={updated.get('worker_slot', '')} "
                    f"batch={batch_file} attempt={attempt_index} "
                    f"classifier_rows={inspection['classifier_rows']} result_rows={inspection['result_rows']}"
                ),
            )
            changed = True
            updated_rows.append(updated)
            continue

        failure_type = "row_count_mismatch" if inspection["state"] == "partial_misaligned" else "agent_unresponsive"
        log_reason = detect_dead_worker_reason(resolve_repo_path(str(updated.get("active_attempt") or "")) / "supervisor_worker.log")
        if (
            str(updated.get("prepared_reason") or "").strip() == failure_type
            and str(updated.get("last_rerun_reason") or "").strip() == failure_type
            and parse_int(updated.get("last_seen_classifier_rows"), 0) == inspection["classifier_rows"]
            and parse_int(updated.get("last_seen_result_rows"), 0) == inspection["result_rows"]
        ):
            updated["status"] = "needs_rerun"
            updated["last_failure_type"] = failure_type
            updated = clear_rerun_runtime_markers(updated)
            changed = True
            updated_rows.append(updated)
            continue
        counts = parse_failure_counts(updated.get("failure_counts_json", ""))
        counts[failure_type] = counts.get(failure_type, 0) + 1
        updated["status"] = "needs_rerun"
        updated["last_failure_type"] = failure_type
        updated["failure_counts_json"] = json.dumps(counts, ensure_ascii=False, separators=(",", ":"))
        updated["last_rerun_reason"] = failure_type
        updated["last_rerun_at"] = now_iso
        updated["prepared_mode"] = "continue_from_prefix" if inspection["state"] == "partial_prefix" and inspection["prefix_len"] > 0 else "fresh_restart"
        updated["prepared_reason"] = failure_type
        updated["planned_rotate"] = ""
        updated["respawn_count"] = str(parse_int(updated.get("respawn_count"), 0) + 1)
        if failure_type == "agent_unresponsive":
            updated["stall_failure_count"] = str(parse_int(updated.get("stall_failure_count"), 0) + 1)
        updated = clear_rerun_runtime_markers(updated)
        log_event(
            events_log,
            (
                "[worker:dead_rerun] "
                f"round={updated.get('round_index', '')} slot={updated.get('worker_slot', '')} "
                f"batch={batch_file} attempt={attempt_index} "
                f"inspection_state={inspection['state']} prefix_len={inspection['prefix_len']} "
                f"failure_type={failure_type} log_reason={log_reason}"
            ),
        )
        changed = True
        updated_rows.append(updated)

    if changed:
        write_schedule(schedule_csv, updated_rows)
    return updated_rows, changed


def terminate_for_actions(
    actions: list[dict[str, str]],
    registry: list[dict[str, Any]],
    events_log: Path,
) -> list[dict[str, Any]]:
    remaining: list[dict[str, Any]] = []
    for entry in registry:
        matched = any(registry_match(action, entry) for action in actions)
        if matched:
            terminate_registry_entry(entry, events_log, f"runtime_action:{entry.get('batch_file', '')}")
        else:
            remaining.append(entry)
    return cleanup_registry(remaining)


def launch_log_path(instructions_file: Path) -> Path:
    return instructions_file.parent / "supervisor_worker.log"


def launch_final_message_path(instructions_file: Path) -> Path:
    return instructions_file.parent / "final_message.md"


def bootstrap_codex_home(target_home: Path) -> Path:
    source_home = Path.home() / ".codex"
    target_home.mkdir(parents=True, exist_ok=True)
    for name in ["auth.json", "config.toml", "installation_id", "version.json"]:
        source = source_home / name
        target = target_home / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
    return target_home


def spawn_worker(
    launch_row: dict[str, str],
    *,
    codex_bin: str,
    events_log: Path,
) -> dict[str, Any]:
    instructions_file = (REPO_ROOT / launch_row["instructions_file"]).resolve()
    final_message_path = launch_final_message_path(instructions_file)
    log_path = launch_log_path(instructions_file)
    codex_home = bootstrap_codex_home(instructions_file.parent / ".codex_home")
    prompt = (
        f"Read {instructions_file} and execute it fully. "
        "Obey its write scope and output paths exactly."
    )
    cmd = [
        codex_bin,
        "-a",
        "never",
        "--search",
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "-m",
        launch_row.get("model") or "gpt-5.4-mini",
        "-s",
        DEFAULT_WORKER_SANDBOX_MODE,
        "--json",
        "-o",
        str(final_message_path),
        prompt,
    ]
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    env.setdefault("TMPDIR", "/tmp")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as logfile:
        process = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=logfile,
            stderr=subprocess.STDOUT,
            preexec_fn=build_worker_preexec_fn(os.getpid()),
        )
    entry = {
        "round_index": parse_int(launch_row.get("round_index"), 0),
        "worker_slot": parse_int(launch_row.get("worker_slot"), 0),
        "batch_file": launch_row.get("batch_file", ""),
        "attempt_index": parse_int(launch_row.get("attempt_index"), 0),
        "lease_id": launch_row.get("lease_id", ""),
        "instructions_file": str(instructions_file),
        "log_path": str(log_path),
        "final_message_path": str(final_message_path),
        "pid": process.pid,
        "pgid": process.pid,
        "started_at": iso_now(),
    }
    log_event(
        events_log,
        (
            "[worker:spawn] "
            f"round={entry['round_index']} slot={entry['worker_slot']} "
            f"attempt={entry['attempt_index']} pid={entry['pid']} pgid={entry['pgid']} "
            f"batch={entry['batch_file']}"
        ),
    )
    return entry


def parse_runtime_actions(runs_dir: Path, round_index: int) -> list[dict[str, str]]:
    return load_csv_rows(runs_dir / f"runtime_actions_round_{round_index:04d}.csv")


def parse_launch_queue(runs_dir: Path, round_index: int) -> list[dict[str, str]]:
    return load_csv_rows(runs_dir / f"launch_queue_round_{round_index:04d}.csv")


def relevant_failure_total(row: dict[str, str]) -> int:
    counts = parse_failure_counts(row.get("failure_counts_json", ""))
    return sum(counts.get(name, 0) for name in SPLIT_BATCH_FAILURE_TYPES)


def split_state_path_for_row(row: dict[str, str]) -> Path:
    active_attempt_dir = resolve_repo_path(str(row.get("active_attempt") or ""))
    return active_attempt_dir / SPLIT_STATE_FILE_NAME


def split_outcome_path_for_row(row: dict[str, str]) -> Path:
    active_attempt_dir = resolve_repo_path(str(row.get("active_attempt") or ""))
    return active_attempt_dir / SPLIT_OUTCOME_FILE_NAME


def split_root_for_row(row: dict[str, str]) -> Path:
    active_attempt_dir = resolve_repo_path(str(row.get("active_attempt") or ""))
    return active_attempt_dir / SPLIT_SHARDS_DIR_NAME


def split_merged_classifier_path_for_row(row: dict[str, str]) -> Path:
    return split_root_for_row(row) / SPLIT_MERGED_CLASSIFIER_FILE_NAME


def split_merged_results_path_for_row(row: dict[str, str]) -> Path:
    return split_root_for_row(row) / SPLIT_MERGED_RESULTS_FILE_NAME


def split_merge_manifest_path_for_row(row: dict[str, str]) -> Path:
    return split_root_for_row(row) / SPLIT_MERGE_MANIFEST_FILE_NAME


def load_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json_dict(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_jsonl_tasks(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            raw = line.strip()
            if raw:
                tasks.append(json.loads(raw))
    return tasks


def write_jsonl_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as outfile:
        for task in tasks:
            outfile.write(json.dumps(task, ensure_ascii=False) + "\n")


def split_state_active(split_state: dict[str, Any]) -> bool:
    return str(split_state.get("state") or "").strip() in {"prepared", "running"}


def batch_has_any_active_split(row: dict[str, str]) -> bool:
    attempts_dir_raw = str(row.get("attempts_dir") or "").strip()
    if not attempts_dir_raw:
        return False
    attempts_dir = resolve_repo_path(attempts_dir_raw)
    if not attempts_dir.exists() or not attempts_dir.is_dir():
        return False
    for attempt_dir in sorted(attempts_dir.glob("attempt_*")):
        split_state = load_json_dict(attempt_dir / SPLIT_STATE_FILE_NAME)
        if split_state_active(split_state):
            return True
    return False


def select_split_recovery_candidates(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    *,
    respawn_threshold: int,
    failure_threshold: int,
) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    for row in round_rows(schedule_rows, round_index):
        status = (row.get("status") or "").strip()
        if status not in {"running", "needs_rerun"}:
            continue
        split_state = load_json_dict(split_state_path_for_row(row))
        if split_state_active(split_state) or batch_has_any_active_split(row):
            continue
        respawn_count = parse_int(row.get("respawn_count"), 0)
        attempt_index = parse_int(row.get("attempt_index"), 0)
        relevant_failures = relevant_failure_total(row)
        if max(respawn_count, attempt_index) < respawn_threshold:
            continue
        if relevant_failures < failure_threshold:
            continue
        selected.append(dict(row))
    return selected


def mark_split_recovery_requested(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    selected_rows: list[dict[str, str]],
    *,
    events_log: Path,
) -> list[dict[str, str]]:
    if not selected_rows:
        return schedule_rows
    batch_files = {str(row.get("batch_file") or "") for row in selected_rows}
    updated_rows: list[dict[str, str]] = []
    now_iso = iso_now()
    for row in schedule_rows:
        updated = dict(row)
        if str(updated.get("batch_file") or "") in batch_files:
            updated["status"] = "needs_rerun"
            updated["prepared_mode"] = "fresh_restart"
            updated["prepared_reason"] = SPLIT_BATCH_LAUNCH_REASON
            updated["planned_rotate"] = ""
            updated["last_rerun_reason"] = SPLIT_BATCH_LAUNCH_REASON
            updated["last_rerun_at"] = now_iso
            log_event(
                events_log,
                (
                    "[split_batch:request] "
                    f"round={updated.get('round_index', '')} slot={updated.get('worker_slot', '')} "
                    f"batch={updated.get('batch_file', '')} attempt={updated.get('attempt_index', '')}"
                ),
            )
        updated_rows.append(updated)
    write_schedule(schedule_csv, updated_rows)
    return updated_rows


def partition_tasks(tasks: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if not tasks:
        return []
    if len(tasks) <= DEFAULT_SPLIT_SHARD_SIZE:
        return [tasks]
    return [tasks[:DEFAULT_SPLIT_SHARD_SIZE], tasks[DEFAULT_SPLIT_SHARD_SIZE:]]


def task_window(tasks: list[dict[str, Any]]) -> tuple[str, str, str, str]:
    if not tasks:
        return "", "", "", ""
    first = tasks[0]
    last = tasks[-1]
    return (
        str(first.get("task_index", "")),
        str(first.get("company_name", "")),
        str(last.get("task_index", "")),
        str(last.get("company_name", "")),
    )


def inspect_attempt_outputs(
    *,
    classifier_path: Path,
    results_path: Path,
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    classifier_fields, classifier_rows = load_csv_rows_with_fields(classifier_path)
    result_fields, result_rows = load_csv_rows_with_fields(results_path)
    classifier_header_ok = classifier_fields == CLASSIFIER_CSV_COLUMNS
    result_header_ok = result_fields == RESULT_CSV_COLUMNS
    prefix_len = 0
    compare_count = min(len(tasks), len(classifier_rows), len(result_rows))
    prefix_valid = classifier_header_ok and result_header_ok
    for index in range(compare_count):
        expected_task_index = str(tasks[index].get("task_index", ""))
        if classifier_rows[index].get("task_index", "") != expected_task_index:
            prefix_valid = False
            break
        if result_rows[index].get("task_index", "") != expected_task_index:
            prefix_valid = False
            break
        prefix_len += 1
    if compare_count < max(len(classifier_rows), len(result_rows)):
        prefix_valid = False
    last_activity = 0.0
    for path in [classifier_path, results_path]:
        if path.exists():
            try:
                last_activity = max(last_activity, path.stat().st_mtime)
            except OSError:
                pass
    if prefix_valid and len(classifier_rows) == len(tasks) and len(result_rows) == len(tasks):
        state = "completed"
    elif len(classifier_rows) == 0 and len(result_rows) == 0 and classifier_header_ok and result_header_ok:
        state = "header_only"
    elif prefix_valid and prefix_len > 0:
        state = "partial_prefix"
    else:
        state = "partial_misaligned"
    return {
        "classifier_rows": len(classifier_rows),
        "result_rows": len(result_rows),
        "classifier_header_ok": classifier_header_ok,
        "result_header_ok": result_header_ok,
        "classifier_data": classifier_rows,
        "result_data": result_rows,
        "prefix_len": prefix_len,
        "prefix_valid": prefix_valid,
        "state": state,
        "last_activity": last_activity,
    }


def parse_json_list(raw: str) -> list[Any]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def summarize_result_rows(rows: list[dict[str, str]], task_count: int) -> dict[str, Any]:
    mapped_entity_rows = 0
    searched_no_entity_rows = 0
    skip_candidate_rows = 0
    manual_review_rows = 0
    for row in rows:
        entity_values = parse_json_list(row.get("mapped_entity_name", ""))
        if entity_values:
            mapped_entity_rows += 1
        else:
            if (row.get("entity_search_required") or "").strip() == "yes":
                searched_no_entity_rows += 1
            else:
                skip_candidate_rows += 1
        if (row.get("needs_manual_review") or "").strip() == "yes":
            manual_review_rows += 1
    summary = {
        "task_count": task_count,
        "rows_written": len(rows),
        "rows_with_entity": mapped_entity_rows,
        "rows_without_entity": max(0, len(rows) - mapped_entity_rows),
        "searched_no_entity_rows": searched_no_entity_rows,
        "skip_candidate_rows": skip_candidate_rows,
        "manual_review_rows": manual_review_rows,
        "search_complete": len(rows) == task_count,
    }
    if len(rows) < task_count:
        summary["completion_reason"] = "interrupted_incomplete"
    elif mapped_entity_rows > 0:
        summary["completion_reason"] = "completed_with_entities_found"
    elif searched_no_entity_rows == task_count:
        summary["completion_reason"] = "all_tokens_searched_no_entity"
    else:
        summary["completion_reason"] = "all_rows_resolved_zero_entity_mixed_skip_and_search"
    return summary


def find_schedule_row(
    schedule_rows: list[dict[str, str]],
    *,
    batch_file: str,
    attempt_index: int,
) -> dict[str, str] | None:
    for row in schedule_rows:
        if str(row.get("batch_file") or "") != batch_file:
            continue
        if parse_int(row.get("attempt_index"), 0) != attempt_index:
            continue
        return dict(row)
    return None


def split_requires_search_guarantee(row: dict[str, str]) -> bool:
    markers = [
        str(row.get("batch_file") or ""),
        str(row.get("run_dir") or ""),
        str(row.get("tasks_file") or ""),
        str(row.get("active_attempt") or ""),
    ]
    return any("rerun_manual_fallbacks" in marker for marker in markers)


def render_split_worker_instruction(
    *,
    base_instruction_text: str,
    row: dict[str, str],
    shard_id: str,
    shard_dir: Path,
    shard_tasks_path: Path,
    classifier_path: Path,
    results_path: Path,
    shard_tasks: list[dict[str, Any]],
    existing_prefix_rows: int,
) -> str:
    first_task_index, first_company, last_task_index, last_company = task_window(shard_tasks)
    if existing_prefix_rows > 0 and existing_prefix_rows < len(shard_tasks):
        next_task = shard_tasks[existing_prefix_rows]
        prefix_note = (
            f"- This shard already contains a preserved prefix of {existing_prefix_rows} completed rows.\n"
            f"- Continue from task_index {next_task.get('task_index', '')} ({next_task.get('company_name', '')}) onward.\n"
            "- Do not rewrite completed shard rows. Append only the remaining shard rows in order.\n"
        )
    else:
        prefix_note = "- Start from the first shard task and write shard rows in order.\n"
    if split_requires_search_guarantee(row):
        search_guarantee_note = (
            "- Search guarantee mode is active for this shard.\n"
            "- Every token in this shard must be searched before you conclude that no reliable entity mapping exists.\n"
            "- Do not use `search_tier = skip_candidate` in classifier output for this shard.\n"
            "- Set `entity_search_required = yes` for every token in this shard.\n"
            "- If no reliable entity mapping exists after best-effort research, keep `mapped_entity_name = []` but still include real evidence URLs and source types.\n"
            "- Do not use `needs_manual_review = yes` as a substitute for skipping search.\n"
        )
    else:
        search_guarantee_note = ""
    return (
        "# Split Search Wrapper\n\n"
        f"- split_mode: {SPLIT_BATCH_LAUNCH_REASON}\n"
        f"- shard_id: {shard_id}\n"
        f"- parent batch: {row.get('batch_file', '')}\n"
        f"- active attempt dir: {resolve_repo_path(str(row.get('active_attempt') or ''))}\n"
        f"- authoritative shard dir: {shard_dir}\n"
        f"- authoritative shard tasks file: {shard_tasks_path}\n"
        f"- authoritative shard classifier CSV: {classifier_path}\n"
        f"- authoritative shard results CSV: {results_path}\n"
        f"- shard task_count: {len(shard_tasks)}\n"
        f"- shard first task_index/company: {first_task_index} / {first_company}\n"
        f"- shard last task_index/company: {last_task_index} / {last_company}\n"
        "- This worker owns exactly this shard and must not write sibling shard files or the parent attempt CSVs directly.\n"
        f"{prefix_note}"
        f"{search_guarantee_note}"
        "- If a token truly has no supported entity mapping after best-effort search, keep `mapped_entity_name = []` but still provide real evidence and keep the row schema-valid.\n"
        "- Do not fabricate placeholder manual-review rows just to close the shard.\n"
        "- Finish the assigned shard, write rows incrementally, then exit.\n\n"
        f"{base_instruction_text.rstrip()}\n"
    )


def initialize_split_recovery(
    row: dict[str, str],
    *,
    events_log: Path,
) -> dict[str, Any]:
    split_state_path = split_state_path_for_row(row)
    existing = load_json_dict(split_state_path)
    if split_state_active(existing):
        return existing

    active_attempt_dir = resolve_repo_path(str(row.get("active_attempt") or ""))
    tasks_path = resolve_repo_path(str(row.get("tasks_file") or ""))
    base_instructions_path = resolve_repo_path(str(row.get("base_instructions_file") or ""))
    tasks = load_jsonl_tasks(tasks_path)
    shards = partition_tasks(tasks)
    split_root = split_root_for_row(row)
    split_root.mkdir(parents=True, exist_ok=True)
    base_instruction_text = base_instructions_path.read_text(encoding="utf-8")

    shard_entries: list[dict[str, Any]] = []
    for index, shard_tasks in enumerate(shards, start=1):
        shard_id = f"shard_{index:02d}"
        shard_dir = split_root / shard_id
        shard_dir.mkdir(parents=True, exist_ok=True)
        shard_tasks_path = shard_dir / "tasks.jsonl"
        classifier_path = shard_dir / "classifier_results.csv"
        results_path = shard_dir / "results.csv"
        instructions_path = shard_dir / "worker_instructions.md"
        final_message_path = shard_dir / "final_message.md"
        write_jsonl_tasks(shard_tasks_path, shard_tasks)
        if not classifier_path.exists():
            write_csv_rows(classifier_path, CLASSIFIER_CSV_COLUMNS, [])
        if not results_path.exists():
            write_csv_rows(results_path, RESULT_CSV_COLUMNS, [])
        inspection = inspect_attempt_outputs(
            classifier_path=classifier_path,
            results_path=results_path,
            tasks=shard_tasks,
        )
        instructions_path.write_text(
            render_split_worker_instruction(
                base_instruction_text=base_instruction_text,
                row=row,
                shard_id=shard_id,
                shard_dir=shard_dir,
                shard_tasks_path=shard_tasks_path,
                classifier_path=classifier_path,
                results_path=results_path,
                shard_tasks=shard_tasks,
                existing_prefix_rows=inspection["prefix_len"] if inspection["state"] == "partial_prefix" else 0,
            ),
            encoding="utf-8",
        )
        first_task_index, first_company, last_task_index, last_company = task_window(shard_tasks)
        shard_entries.append(
            {
                "shard_id": shard_id,
                "status": "prepared",
                "tasks_file": str(shard_tasks_path),
                "classifier_results_csv": str(classifier_path),
                "results_csv": str(results_path),
                "instructions_file": str(instructions_path),
                "final_message_path": str(final_message_path),
                "task_count": len(shard_tasks),
                "start_task_index": first_task_index,
                "start_company": first_company,
                "end_task_index": last_task_index,
                "end_company": last_company,
                "spawn_count": 0,
                "started_at": "",
                "first_row_at": "",
                "last_progress_at": "",
                "last_failure_reason": "",
                "rows_written": 0,
            }
        )

    payload = {
        "mode": SPLIT_BATCH_LAUNCH_REASON,
        "state": "prepared",
        "created_at": iso_now(),
        "updated_at": iso_now(),
        "round_index": parse_int(row.get("round_index"), 0),
        "worker_slot": parse_int(row.get("worker_slot"), 0),
        "batch_file": str(row.get("batch_file") or ""),
        "attempt_index": parse_int(row.get("attempt_index"), 0),
        "task_count": len(tasks),
        "progress_classifier_rows": 0,
        "progress_result_rows": 0,
        "shards": shard_entries,
        "outcome_file": str(split_outcome_path_for_row(row)),
        "merged_classifier_results_csv": str(split_merged_classifier_path_for_row(row)),
        "merged_results_csv": str(split_merged_results_path_for_row(row)),
        "merge_manifest_json": str(split_merge_manifest_path_for_row(row)),
    }
    write_json_dict(split_state_path, payload)
    log_event(
        events_log,
        (
            "[split_batch:init] "
            f"round={row.get('round_index', '')} slot={row.get('worker_slot', '')} "
            f"batch={row.get('batch_file', '')} attempt={row.get('attempt_index', '')}"
        ),
    )
    return payload


def spawn_instruction_worker(
    *,
    instructions_file: Path,
    final_message_path: Path,
    model: str,
    round_index: int,
    worker_slot: int,
    batch_file: str,
    attempt_index: int,
    codex_bin: str,
    events_log: Path,
    lease_id: str = "",
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        instructions_rel = str(instructions_file.resolve().relative_to(REPO_ROOT))
    except ValueError:
        instructions_rel = os.path.relpath(str(instructions_file.resolve()), str(REPO_ROOT))
    launch_row = {
        "round_index": str(round_index),
        "worker_slot": str(worker_slot),
        "batch_file": batch_file,
        "attempt_index": str(attempt_index),
        "lease_id": lease_id,
        "instructions_file": instructions_rel,
        "model": model,
    }
    entry = spawn_worker(
        launch_row,
        codex_bin=codex_bin,
        events_log=events_log,
    )
    if extra_fields:
        entry.update(extra_fields)
    if str(entry.get("final_message_path") or "") != str(final_message_path):
        entry["final_message_path"] = str(final_message_path)
    return entry


def split_shard_registry_match(entry: dict[str, Any], *, batch_file: str, attempt_index: int, shard_id: str) -> bool:
    return (
        str(entry.get("batch_file") or "") == batch_file
        and parse_int(entry.get("attempt_index"), 0) == attempt_index
        and str(entry.get("split_shard_id") or "") == shard_id
    )


def terminate_split_shard(
    registry: list[dict[str, Any]],
    *,
    batch_file: str,
    attempt_index: int,
    shard_id: str,
    events_log: Path,
    reason: str,
) -> list[dict[str, Any]]:
    remaining: list[dict[str, Any]] = []
    for entry in registry:
        if split_shard_registry_match(entry, batch_file=batch_file, attempt_index=attempt_index, shard_id=shard_id):
            terminate_registry_entry(entry, events_log, reason)
        else:
            remaining.append(entry)
    return cleanup_registry(remaining)


def active_split_shard_running(
    registry: list[dict[str, Any]],
    *,
    batch_file: str,
    attempt_index: int,
    shard_id: str,
) -> bool:
    for entry in registry:
        if split_shard_registry_match(entry, batch_file=batch_file, attempt_index=attempt_index, shard_id=shard_id):
            if registry_entry_alive(entry):
                return True
    return False


def respawn_split_shard(
    row: dict[str, str],
    split_state: dict[str, Any],
    shard: dict[str, Any],
    *,
    registry: list[dict[str, Any]],
    codex_bin: str,
    events_log: Path,
    reason: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    batch_file = str(row.get("batch_file") or "")
    attempt_index = parse_int(row.get("attempt_index"), 0)
    shard_id = str(shard.get("shard_id") or "")
    registry = terminate_split_shard(
        registry,
        batch_file=batch_file,
        attempt_index=attempt_index,
        shard_id=shard_id,
        events_log=events_log,
        reason=reason,
    )
    shard_tasks = load_jsonl_tasks(Path(str(shard["tasks_file"])))
    classifier_path = Path(str(shard["classifier_results_csv"]))
    results_path = Path(str(shard["results_csv"]))
    inspection = inspect_attempt_outputs(
        classifier_path=classifier_path,
        results_path=results_path,
        tasks=shard_tasks,
    )
    if inspection["state"] == "partial_misaligned":
        write_csv_rows(classifier_path, CLASSIFIER_CSV_COLUMNS, [])
        write_csv_rows(results_path, RESULT_CSV_COLUMNS, [])
        inspection = inspect_attempt_outputs(
            classifier_path=classifier_path,
            results_path=results_path,
            tasks=shard_tasks,
        )
    base_instructions_path = resolve_repo_path(str(row.get("base_instructions_file") or ""))
    Path(str(shard["instructions_file"])).write_text(
        render_split_worker_instruction(
            base_instruction_text=base_instructions_path.read_text(encoding="utf-8"),
            row=row,
            shard_id=shard_id,
            shard_dir=Path(str(shard["instructions_file"])).parent,
            shard_tasks_path=Path(str(shard["tasks_file"])),
            classifier_path=classifier_path,
            results_path=results_path,
            shard_tasks=shard_tasks,
            existing_prefix_rows=inspection["prefix_len"] if inspection["state"] == "partial_prefix" else 0,
        ),
        encoding="utf-8",
    )
    shard["spawn_count"] = parse_int(shard.get("spawn_count"), 0) + 1
    shard["status"] = "running"
    shard["started_at"] = iso_now()
    shard["first_row_at"] = shard.get("first_row_at") or ""
    shard["last_progress_at"] = shard["started_at"]
    shard["last_failure_reason"] = reason
    split_state["state"] = "running"
    split_state["updated_at"] = iso_now()
    entry = spawn_instruction_worker(
        instructions_file=Path(str(shard["instructions_file"])),
        final_message_path=Path(str(shard["final_message_path"])),
        model="gpt-5.4-mini",
        round_index=parse_int(row.get("round_index"), 0),
        worker_slot=parse_int(row.get("worker_slot"), 0),
        batch_file=batch_file,
        attempt_index=attempt_index,
        codex_bin=codex_bin,
        events_log=events_log,
        lease_id=str(row.get("lease_id") or ""),
        extra_fields={
            "split_shard_id": shard_id,
            "split_state_file": str(split_state_path_for_row(row)),
        },
    )
    registry.append(entry)
    return split_state, registry


def spawn_pending_split_shards(
    row: dict[str, str],
    split_state: dict[str, Any],
    *,
    registry: list[dict[str, Any]],
    codex_bin: str,
    events_log: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for shard in split_state.get("shards", []):
        shard_id = str(shard.get("shard_id") or "")
        if active_split_shard_running(
            registry,
            batch_file=str(row.get("batch_file") or ""),
            attempt_index=parse_int(row.get("attempt_index"), 0),
            shard_id=shard_id,
        ):
            continue
        if str(shard.get("status") or "") in {"completed", "running"}:
            continue
        split_state, registry = respawn_split_shard(
            row,
            split_state,
            shard,
            registry=registry,
            codex_bin=codex_bin,
            events_log=events_log,
            reason="split_shard_launch",
        )
    return split_state, registry


def merge_split_outputs(
    row: dict[str, str],
    split_state: dict[str, Any],
    *,
    events_log: Path,
) -> dict[str, Any]:
    tasks = load_jsonl_tasks(resolve_repo_path(str(row.get("tasks_file") or "")))
    merged_classifier_rows: list[dict[str, str]] = []
    merged_result_rows: list[dict[str, str]] = []
    for shard in split_state.get("shards", []):
        shard_tasks = load_jsonl_tasks(Path(str(shard["tasks_file"])))
        inspection = inspect_attempt_outputs(
            classifier_path=Path(str(shard["classifier_results_csv"])),
            results_path=Path(str(shard["results_csv"])),
            tasks=shard_tasks,
        )
        if inspection["state"] != "completed":
            raise SystemExit(
                f"Cannot merge split shard before completion: {row.get('batch_file', '')} {shard.get('shard_id', '')}"
            )
        merged_classifier_rows.extend(
            [normalize_row_fields(item, CLASSIFIER_CSV_COLUMNS) for item in inspection["classifier_data"]]
        )
        merged_result_rows.extend(
            [normalize_row_fields(item, RESULT_CSV_COLUMNS) for item in inspection["result_data"]]
        )

    if len(merged_classifier_rows) != len(tasks) or len(merged_result_rows) != len(tasks):
        raise SystemExit(
            f"Split merge row count mismatch for {row.get('batch_file', '')}: "
            f"classifier={len(merged_classifier_rows)} results={len(merged_result_rows)} expected={len(tasks)}"
        )
    for index, task in enumerate(tasks):
        expected_task_index = str(task.get("task_index", ""))
        if merged_classifier_rows[index].get("task_index", "") != expected_task_index:
            raise SystemExit(
                f"Split merge classifier order mismatch for {row.get('batch_file', '')} at position {index}"
            )
        if merged_result_rows[index].get("task_index", "") != expected_task_index:
            raise SystemExit(
                f"Split merge result order mismatch for {row.get('batch_file', '')} at position {index}"
            )

    classifier_path = resolve_repo_path(str(row.get("classifier_results_csv") or ""))
    results_path = resolve_repo_path(str(row.get("results_csv") or ""))
    merged_classifier_path = split_merged_classifier_path_for_row(row)
    merged_results_path = split_merged_results_path_for_row(row)
    merge_manifest_path = split_merge_manifest_path_for_row(row)
    write_csv_rows(classifier_path, CLASSIFIER_CSV_COLUMNS, merged_classifier_rows)
    write_csv_rows(results_path, RESULT_CSV_COLUMNS, merged_result_rows)
    write_csv_rows(merged_classifier_path, CLASSIFIER_CSV_COLUMNS, merged_classifier_rows)
    write_csv_rows(merged_results_path, RESULT_CSV_COLUMNS, merged_result_rows)

    summary = summarize_result_rows(merged_result_rows, len(tasks))
    summary.update(
        {
            "mode": SPLIT_BATCH_LAUNCH_REASON,
            "batch_file": str(row.get("batch_file") or ""),
            "attempt_index": parse_int(row.get("attempt_index"), 0),
            "merged_at": iso_now(),
            "merged_classifier_results_csv": str(merged_classifier_path),
            "merged_results_csv": str(merged_results_path),
            "merge_manifest_json": str(merge_manifest_path),
            "authoritative_source": "split_merged",
        }
    )
    outcome_path = split_outcome_path_for_row(row)
    write_json_dict(outcome_path, summary)
    write_json_dict(
        merge_manifest_path,
        {
            "mode": SPLIT_BATCH_LAUNCH_REASON,
            "batch_file": str(row.get("batch_file") or ""),
            "attempt_index": parse_int(row.get("attempt_index"), 0),
            "merged_at": summary["merged_at"],
            "merged_classifier_results_csv": str(merged_classifier_path),
            "merged_results_csv": str(merged_results_path),
            "task_count": len(tasks),
            "rows_written": summary["rows_written"],
            "rows_with_entity": summary["rows_with_entity"],
            "searched_no_entity_rows": summary["searched_no_entity_rows"],
            "skip_candidate_rows": summary["skip_candidate_rows"],
            "manual_review_rows": summary["manual_review_rows"],
            "completion_reason": summary["completion_reason"],
            "authoritative_source": "split_merged",
        },
    )
    final_message_path = resolve_repo_path(str(row.get("active_attempt") or "")) / "final_message.md"
    final_message_path.write_text(
        (
            f"Split batch recovery merged successfully.\n"
            f"mode: {summary['mode']}\n"
            f"rows_written: {summary['rows_written']}/{summary['task_count']}\n"
            f"rows_with_entity: {summary['rows_with_entity']}\n"
            f"searched_no_entity_rows: {summary['searched_no_entity_rows']}\n"
            f"skip_candidate_rows: {summary['skip_candidate_rows']}\n"
            f"manual_review_rows: {summary['manual_review_rows']}\n"
            f"completion_reason: {summary['completion_reason']}\n"
        ),
        encoding="utf-8",
    )
    split_state["state"] = "merged"
    split_state["progress_classifier_rows"] = len(tasks)
    split_state["progress_result_rows"] = len(tasks)
    split_state["updated_at"] = iso_now()
    split_state["merged_classifier_results_csv"] = str(merged_classifier_path)
    split_state["merged_results_csv"] = str(merged_results_path)
    split_state["merge_manifest_json"] = str(merge_manifest_path)
    split_state["authoritative_source"] = "split_merged"
    write_json_dict(split_state_path_for_row(row), split_state)
    log_event(
        events_log,
        (
            "[split_batch:merge] "
            f"round={row.get('round_index', '')} slot={row.get('worker_slot', '')} "
            f"batch={row.get('batch_file', '')} attempt={row.get('attempt_index', '')} "
            f"rows_with_entity={summary['rows_with_entity']} "
            f"searched_no_entity_rows={summary['searched_no_entity_rows']} "
            f"skip_candidate_rows={summary['skip_candidate_rows']} "
            f"completion_reason={summary['completion_reason']}"
        ),
    )
    return summary


def manage_split_recoveries(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    *,
    round_index: int,
    registry: list[dict[str, Any]],
    codex_bin: str,
    events_log: Path,
    startup_timeout_seconds: int,
    partial_stall_timeout_seconds: int,
) -> tuple[list[dict[str, str]], list[dict[str, Any]], bool]:
    changed = False
    updated_rows: list[dict[str, str]] = []
    now = now_utc()
    now_iso = iso_now()
    timeout_profile = activity_timeout_profile(
        startup_timeout_seconds=startup_timeout_seconds,
        partial_stall_timeout_seconds=partial_stall_timeout_seconds,
    )
    for row in schedule_rows:
        updated = dict(row)
        if parse_int(updated.get("round_index"), 0) != round_index:
            updated_rows.append(updated)
            continue
        split_state_path = split_state_path_for_row(updated)
        split_state = load_json_dict(split_state_path)
        if not split_state_active(split_state):
            updated_rows.append(updated)
            continue

        previous_progress_classifier_rows = parse_int(updated.get("last_seen_classifier_rows"), 0)
        previous_progress_result_rows = parse_int(updated.get("last_seen_result_rows"), 0)
        progress_classifier_rows = 0
        progress_result_rows = 0
        all_completed = True
        batch_health_state = "healthy_active"
        batch_warning_reason = ""
        batch_next_retry_at = ""
        latest_worker_activity_at: datetime | None = None
        latest_worker_activity_type = ""
        latest_worker_activity_source = ""
        split_state["state"] = "running"
        for shard in split_state.get("shards", []):
            shard_tasks = load_jsonl_tasks(Path(str(shard["tasks_file"])))
            inspection = inspect_attempt_outputs(
                classifier_path=Path(str(shard["classifier_results_csv"])),
                results_path=Path(str(shard["results_csv"])),
                tasks=shard_tasks,
            )
            shard_id = str(shard.get("shard_id") or "")
            progress_classifier_rows += min(inspection["classifier_rows"], len(shard_tasks))
            progress_result_rows += min(inspection["result_rows"], len(shard_tasks))
            if inspection["classifier_rows"] > 0 or inspection["result_rows"] > 0:
                shard["first_row_at"] = shard.get("first_row_at") or now_iso
            if inspection["prefix_len"] > parse_int(shard.get("rows_written"), 0):
                shard["rows_written"] = inspection["prefix_len"]
                shard["last_progress_at"] = now_iso
                changed = True

            if inspection["state"] == "completed":
                shard["status"] = "completed"
                shard["rows_written"] = len(shard_tasks)
                continue

            all_completed = False
            shard["status"] = "running"
            worker_log_path = launch_log_path(Path(str(shard["instructions_file"])))
            worker_activity = inspect_worker_log_activity(worker_log_path)
            worker_activity_recent = activity_is_recent(
                worker_activity,
                now,
                grace_seconds=timeout_profile["activity_grace_seconds"],
            )
            shard["last_worker_activity_at"] = (
                worker_activity["last_activity_at"].isoformat()
                if isinstance(worker_activity.get("last_activity_at"), datetime)
                else ""
            )
            shard["last_worker_activity_type"] = str(worker_activity.get("last_activity_type") or "")
            shard["last_worker_activity_source"] = str(worker_activity.get("last_activity_source") or "")
            if isinstance(worker_activity.get("last_activity_at"), datetime):
                candidate = worker_activity["last_activity_at"]
                if latest_worker_activity_at is None or candidate > latest_worker_activity_at:
                    latest_worker_activity_at = candidate
                    latest_worker_activity_type = str(worker_activity.get("last_activity_type") or "")
                    latest_worker_activity_source = str(worker_activity.get("last_activity_source") or "")
            shard_running = active_split_shard_running(
                registry,
                batch_file=str(updated.get("batch_file") or ""),
                attempt_index=parse_int(updated.get("attempt_index"), 0),
                shard_id=shard_id,
            )
            started_at_raw = shard.get("started_at") or shard.get("last_progress_at") or now_iso
            try:
                started_at = datetime.fromisoformat(str(started_at_raw))
            except ValueError:
                started_at = now
            last_progress_raw = shard.get("last_progress_at") or shard.get("first_row_at") or shard.get("started_at") or now_iso
            try:
                last_progress_at = datetime.fromisoformat(str(last_progress_raw))
            except ValueError:
                last_progress_at = started_at
            elapsed_since_start = int((now - started_at).total_seconds())
            elapsed_since_progress = int((now - last_progress_at).total_seconds())

            if inspection["state"] == "header_only" and elapsed_since_start >= timeout_profile["startup_hard_seconds"] and not worker_activity_recent:
                split_state, registry = respawn_split_shard(
                    updated,
                    split_state,
                    shard,
                    registry=registry,
                    codex_bin=codex_bin,
                    events_log=events_log,
                    reason="split_startup_no_row",
                )
                changed = True
                continue
            if inspection["state"] in {"partial_prefix", "partial_misaligned"} and elapsed_since_progress >= timeout_profile["stall_hard_seconds"] and not worker_activity_recent:
                split_state, registry = respawn_split_shard(
                    updated,
                    split_state,
                    shard,
                    registry=registry,
                    codex_bin=codex_bin,
                    events_log=events_log,
                    reason="split_partial_stall" if inspection["state"] == "partial_prefix" else "split_row_count_mismatch",
                )
                changed = True
                continue
            if not shard_running and str(shard.get("status") or "") != "completed":
                split_state, registry = respawn_split_shard(
                    updated,
                    split_state,
                    shard,
                    registry=registry,
                    codex_bin=codex_bin,
                    events_log=events_log,
                    reason="split_process_exited",
                )
                changed = True
                continue

            if inspection["state"] == "header_only" and elapsed_since_start >= timeout_profile["startup_soft_seconds"]:
                batch_health_state = "slow_active" if worker_activity_recent else "silent_suspect"
                batch_warning_reason = batch_warning_reason or "split_startup_no_row_soft_timeout"
                batch_next_retry_at = (started_at + timedelta(seconds=timeout_profile["startup_hard_seconds"])).isoformat()
            elif inspection["state"] in {"partial_prefix", "partial_misaligned"} and elapsed_since_progress >= timeout_profile["stall_soft_seconds"]:
                batch_health_state = "slow_active" if worker_activity_recent else "silent_suspect"
                batch_warning_reason = batch_warning_reason or (
                    "split_partial_stall_soft_timeout"
                    if inspection["state"] == "partial_prefix"
                    else "split_row_count_mismatch_soft_timeout"
                )
                batch_next_retry_at = (last_progress_at + timedelta(seconds=timeout_profile["stall_hard_seconds"])).isoformat()

        split_state["progress_classifier_rows"] = progress_classifier_rows
        split_state["progress_result_rows"] = progress_result_rows
        split_state["updated_at"] = now_iso
        write_json_dict(split_state_path, split_state)

        updated["status"] = "running"
        updated["last_seen_classifier_rows"] = str(progress_classifier_rows)
        updated["last_seen_result_rows"] = str(progress_result_rows)
        updated["health_state"] = batch_health_state
        updated["last_worker_activity_at"] = latest_worker_activity_at.isoformat() if latest_worker_activity_at else ""
        updated["last_worker_activity_type"] = latest_worker_activity_type
        updated["last_worker_activity_source"] = latest_worker_activity_source
        if batch_warning_reason:
            updated["soft_timeout_warned_at"] = updated.get("soft_timeout_warned_at") or now_iso
            updated["last_timeout_warning_reason"] = batch_warning_reason
            updated["next_eligible_retry_at"] = batch_next_retry_at
        else:
            updated["soft_timeout_warned_at"] = ""
            updated["last_timeout_warning_reason"] = ""
            updated["next_eligible_retry_at"] = ""
        progress_increased = (
            progress_classifier_rows > previous_progress_classifier_rows
            or progress_result_rows > previous_progress_result_rows
        )
        if progress_classifier_rows > 0 or progress_result_rows > 0:
            updated["first_row_at"] = updated.get("first_row_at") or now_iso
            if progress_increased:
                updated["last_progress_at"] = now_iso
        changed = True

        if all_completed:
            summary = merge_split_outputs(updated, split_state, events_log=events_log)
            updated["status"] = "completed"
            updated["prepared_mode"] = ""
            updated["prepared_reason"] = ""
            updated["planned_rotate"] = ""
            updated["health_state"] = "completed"
            updated["soft_timeout_warned_at"] = ""
            updated["last_timeout_warning_reason"] = ""
            updated["next_eligible_retry_at"] = ""
            updated["classifier_results_csv"] = str(split_merged_classifier_path_for_row(updated))
            updated["results_csv"] = str(split_merged_results_path_for_row(updated))
            updated["last_seen_classifier_rows"] = str(parse_int(updated.get("task_count"), 0))
            updated["last_seen_result_rows"] = str(parse_int(updated.get("task_count"), 0))
            updated["last_rerun_reason"] = summary["completion_reason"]
            updated["last_rerun_at"] = now_iso
        updated_rows.append(updated)

    if changed:
        write_schedule(schedule_csv, updated_rows)
    return updated_rows, cleanup_registry(registry), changed


def handle_launch_rows(
    launch_rows: list[dict[str, str]],
    *,
    schedule_csv: Path,
    runs_dir: Path,
    round_index: int,
    registry: list[dict[str, Any]],
    codex_bin: str,
    events_log: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not launch_rows:
        return cleanup_registry(registry), read_schedule(schedule_csv)
    schedule_rows = read_schedule(schedule_csv)
    for launch_row in launch_rows:
        if str(launch_row.get("launch_reason") or "") == SPLIT_BATCH_LAUNCH_REASON:
            schedule_row = find_schedule_row(
                schedule_rows,
                batch_file=str(launch_row.get("batch_file") or ""),
                attempt_index=parse_int(launch_row.get("attempt_index"), 0),
            )
            if schedule_row is None:
                raise SystemExit(
                    f"Unable to resolve schedule row for split recovery: {launch_row.get('batch_file', '')}"
                )
            split_state = initialize_split_recovery(schedule_row, events_log=events_log)
            split_state, registry = spawn_pending_split_shards(
                schedule_row,
                split_state,
                registry=registry,
                codex_bin=codex_bin,
                events_log=events_log,
            )
            write_json_dict(split_state_path_for_row(schedule_row), split_state)
        else:
            registry.append(
                spawn_worker(
                    launch_row,
                    codex_bin=codex_bin,
                    events_log=events_log,
                )
            )
    registry = cleanup_registry(registry)
    run_mark_started(round_index, runs_dir=runs_dir, events_log=events_log)
    return registry, read_schedule(schedule_csv)


def run_prepare(
    round_index: int,
    *,
    runs_dir: Path,
    events_log: Path,
) -> list[dict[str, str]]:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "4_manage_round_runtime.py"),
        "--runs-dir",
        str(runs_dir),
        "--round-index",
        str(round_index),
        "--prepare-launches",
    ]
    completed = run_command(cmd, cwd=REPO_ROOT, events_log=events_log, label=f"prepare_round_{round_index}")
    if completed.returncode != 0:
        raise SystemExit(f"prepare-launches failed for round {round_index}")
    return parse_launch_queue(runs_dir, round_index)


def run_mark_started(round_index: int, *, runs_dir: Path, events_log: Path) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "4_manage_round_runtime.py"),
        "--runs-dir",
        str(runs_dir),
        "--round-index",
        str(round_index),
        "--mark-round-started",
    ]
    completed = run_command(cmd, cwd=REPO_ROOT, events_log=events_log, label=f"mark_started_round_{round_index}")
    if completed.returncode != 0:
        raise SystemExit(f"mark-round-started failed for round {round_index}")


def run_watch(
    round_index: int,
    *,
    runs_dir: Path,
    startup_timeout_seconds: int,
    partial_stall_timeout_seconds: int,
    events_log: Path,
) -> list[dict[str, str]]:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "4_manage_round_runtime.py"),
        "--runs-dir",
        str(runs_dir),
        "--round-index",
        str(round_index),
        "--watch-round",
        "--startup-no-row-timeout-seconds",
        str(startup_timeout_seconds),
        "--partial-stall-timeout-seconds",
        str(partial_stall_timeout_seconds),
    ]
    completed = run_command(cmd, cwd=REPO_ROOT, events_log=events_log, label=f"watch_round_{round_index}")
    if completed.returncode == 0:
        return []
    actions = parse_runtime_actions(runs_dir, round_index)
    if actions:
        return actions
    raise SystemExit(f"watch-round failed for round {round_index} without runtime actions")


def run_lint(round_index: int, *, runs_dir: Path, events_log: Path) -> bool:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "3_collect_results.py"),
        "--runs-dir",
        str(runs_dir),
        "--round-index",
        str(round_index),
        "--lint-only",
        "--repair-identity-drift-in-place",
        "--fail-on-identity-drift",
    ]
    completed = run_command(cmd, cwd=REPO_ROOT, events_log=events_log, label=f"lint_round_{round_index}")
    return completed.returncode == 0


def run_collect(round_index: int, *, runs_dir: Path, events_log: Path) -> bool:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "3_collect_results.py"),
        "--runs-dir",
        str(runs_dir),
        "--round-index",
        str(round_index),
        "--repair-identity-drift-in-place",
        "--fail-on-identity-drift",
        "--skip-verification",
        "--output-csv",
        str((DEFAULT_FINAL_DIR / "results.csv").resolve()),
        "--manual-review-csv",
        str((DEFAULT_FINAL_DIR / "needs_manual_review.csv").resolve()),
        "--classifier-results-csv",
        str((DEFAULT_FINAL_DIR / "classifier_results.csv").resolve()),
        "--verification-findings-csv",
        str((DEFAULT_OPS_DIR / "verification_findings.csv").resolve()),
        "--checkpoint-json",
        str((runs_dir / DEFAULT_COLLECT_CHECKPOINT_JSON).resolve()),
    ]
    completed = run_command(cmd, cwd=REPO_ROOT, events_log=events_log, label=f"collect_round_{round_index}")
    return completed.returncode == 0


def ensure_requested_rounds_exist(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> None:
    seen = set(available_rounds(schedule_rows))
    missing = [round_index for round_index in target_rounds if round_index not in seen]
    if missing:
        raise SystemExit(
            f"Requested rounds are not present in schedule.csv: {','.join(str(value) for value in missing)}"
        )


def main() -> None:
    args = parse_args()
    if args.start_round_index <= 0:
        raise SystemExit("--start-round-index must be greater than 0.")
    if args.round_count <= 0:
        raise SystemExit("--round-count must be greater than 0.")
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be greater than 0.")
    if args.max_batch_restarts <= 0:
        raise SystemExit("--max-batch-restarts must be greater than 0.")
    if args.split_batch_respawn_threshold <= 0:
        raise SystemExit("--split-batch-respawn-threshold must be greater than 0.")
    if args.split_batch_failure_threshold <= 0:
        raise SystemExit("--split-batch-failure-threshold must be greater than 0.")

    runs_dir = args.runs_dir.resolve()
    schedule_csv = resolve_runs_path(runs_dir, args.schedule_csv, DEFAULT_SCHEDULE_CSV)
    state_json = resolve_runs_path(runs_dir, args.state_json, DEFAULT_STATE_JSON)
    registry_json = resolve_runs_path(runs_dir, args.registry_json, DEFAULT_REGISTRY_JSON)
    events_log = resolve_runs_path(runs_dir, args.events_log, DEFAULT_EVENTS_LOG)
    lock_file = supervisor_lock_path(runs_dir)
    target_rounds = list(range(args.start_round_index, args.start_round_index + args.round_count))
    set_supervisor_context(
        runs_dir=runs_dir,
        schedule_csv=schedule_csv,
        state_json=state_json,
        registry_json=registry_json,
        events_log=events_log,
        target_rounds=target_rounds,
        scheduler_mode="round",
    )
    install_supervisor_signal_handlers()

    args.codex_bin = resolve_codex_bin(args.codex_bin)

    acquire_supervisor_lock(lock_file, runs_dir=runs_dir)
    registry = cleanup_registry(load_registry(registry_json))
    save_registry(registry_json, registry)
    schedule_rows = read_schedule(schedule_csv)
    schedule_rows = reconcile_deferred_long_tail_rows(schedule_csv, schedule_rows)
    ensure_requested_rounds_exist(schedule_rows, target_rounds)

    log_event(
        events_log,
        (
            "[supervisor:start] "
            f"rounds={target_rounds[0]}-{target_rounds[-1]} "
            f"poll={args.poll_seconds}s startup_timeout={args.startup_no_row_timeout_seconds}s "
            f"stall_timeout={args.partial_stall_timeout_seconds}s "
            f"batch_timeout={args.batch_timeout_seconds}s "
            f"max_batch_restarts={args.max_batch_restarts} "
            f"split_thresholds=respawn>={args.split_batch_respawn_threshold},failures>={args.split_batch_failure_threshold}"
        ),
    )

    current_round_index = determine_resume_round_index(schedule_rows, target_rounds)
    if current_round_index > target_rounds[-1]:
        registry = cleanup_registry(registry)
        save_registry(registry_json, registry)
        write_state(
            state_json,
            runs_dir=runs_dir,
            target_rounds=target_rounds,
            current_round_index=target_rounds[-1],
            phase="completed",
            schedule_rows=schedule_rows,
            registry=registry,
        )
        update_launcher_state_status(runs_dir, status="completed")
        log_event(events_log, f"[supervisor:complete] rounds={target_rounds[0]}-{target_rounds[-1]}")
        return
    if current_round_index != target_rounds[0]:
        log_event(
            events_log,
            (
                "[supervisor:resume] "
                f"requested_start_round={target_rounds[0]} resume_round={current_round_index}"
            ),
        )
    while current_round_index <= target_rounds[-1]:
        schedule_rows = reconcile_deferred_long_tail_rows(schedule_csv, read_schedule(schedule_csv))
        write_state(
            state_json,
            runs_dir=runs_dir,
            target_rounds=target_rounds,
            current_round_index=current_round_index,
            phase="prepare",
            schedule_rows=schedule_rows,
            registry=registry,
        )

        launch_rows = run_prepare(current_round_index, runs_dir=runs_dir, events_log=events_log)
        if launch_rows:
            registry, schedule_rows = handle_launch_rows(
                launch_rows,
                schedule_csv=schedule_csv,
                runs_dir=runs_dir,
                round_index=current_round_index,
                registry=registry,
                codex_bin=args.codex_bin,
                events_log=events_log,
            )
            save_registry(registry_json, registry)

        while True:
            registry = cleanup_registry(registry)
            save_registry(registry_json, registry)
            schedule_rows = reconcile_deferred_long_tail_rows(schedule_csv, read_schedule(schedule_csv))
            schedule_rows, dead_worker_changed = mark_dead_worker_reruns(
                schedule_csv,
                schedule_rows,
                round_index=current_round_index,
                registry=registry,
                events_log=events_log,
            )
            if dead_worker_changed:
                launch_rows = run_prepare(current_round_index, runs_dir=runs_dir, events_log=events_log)
                if launch_rows:
                    registry, schedule_rows = handle_launch_rows(
                        launch_rows,
                        schedule_csv=schedule_csv,
                        runs_dir=runs_dir,
                        round_index=current_round_index,
                        registry=registry,
                        codex_bin=args.codex_bin,
                        events_log=events_log,
                    )
                    save_registry(registry_json, registry)
                continue
            schedule_rows, registry, split_changed = manage_split_recoveries(
                schedule_csv,
                schedule_rows,
                round_index=current_round_index,
                registry=registry,
                codex_bin=args.codex_bin,
                events_log=events_log,
                startup_timeout_seconds=args.startup_no_row_timeout_seconds,
                partial_stall_timeout_seconds=args.partial_stall_timeout_seconds,
            )
            if split_changed:
                save_registry(registry_json, registry)

            retry_capped_rows = analyze_retry_capped_rows(
                schedule_rows,
                current_round_index,
                max_batch_restarts=args.max_batch_restarts,
            )
            if retry_capped_rows:
                retry_capped_batch_files = {
                    str(row.get("batch_file") or "")
                    for row in retry_capped_rows
                    if str(row.get("batch_file") or "").strip()
                }
                registry = terminate_for_batch_files(
                    retry_capped_batch_files,
                    registry,
                    events_log,
                    reason=f"round_{current_round_index}_retry_limit",
                )
                schedule_fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
                schedule_rows = mark_retry_capped_rows(
                    schedule_csv,
                    schedule_rows,
                    retry_capped_rows,
                    schedule_fieldnames=schedule_fieldnames,
                    runs_dir=runs_dir,
                    events_log=events_log,
                )
                save_registry(registry_json, registry)
                write_state(
                    state_json,
                    runs_dir=runs_dir,
                    target_rounds=target_rounds,
                    current_round_index=current_round_index,
                    phase=RETRY_CAPPED_STATUS,
                    schedule_rows=schedule_rows,
                    registry=registry,
                )
                continue

            deferred_rows = analyze_long_tail_deferred_rows(
                schedule_rows,
                current_round_index,
                timeout_seconds=args.batch_timeout_seconds,
            )
            if deferred_rows:
                deferred_batch_files = {
                    str(row.get("batch_file") or "")
                    for row in deferred_rows
                    if str(row.get("batch_file") or "").strip()
                }
                registry = terminate_for_batch_files(
                    deferred_batch_files,
                    registry,
                    events_log,
                    reason=f"round_{current_round_index}_long_tail_timeout",
                )
                schedule_fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
                schedule_rows = mark_long_tail_deferred(
                    schedule_csv,
                    schedule_rows,
                    deferred_rows,
                    schedule_fieldnames=schedule_fieldnames,
                    runs_dir=runs_dir,
                    events_log=events_log,
                )
                save_registry(registry_json, registry)
                write_state(
                    state_json,
                    runs_dir=runs_dir,
                    target_rounds=target_rounds,
                    current_round_index=current_round_index,
                    phase="deferred_long_tail",
                    schedule_rows=schedule_rows,
                    registry=registry,
                )
                continue

            if not args.disable_split_batch_recovery:
                split_rows = select_split_recovery_candidates(
                    schedule_rows,
                    current_round_index,
                    respawn_threshold=args.split_batch_respawn_threshold,
                    failure_threshold=args.split_batch_failure_threshold,
                )
                if split_rows:
                    registry = terminate_for_batch_files(
                        {str(row.get("batch_file") or "") for row in split_rows},
                        registry,
                        events_log,
                        reason=f"round_{current_round_index}_split_recovery",
                    )
                    schedule_rows = mark_split_recovery_requested(
                        schedule_csv,
                        schedule_rows,
                        split_rows,
                        events_log=events_log,
                    )
                    save_registry(registry_json, registry)
                    launch_rows = run_prepare(current_round_index, runs_dir=runs_dir, events_log=events_log)
                    if launch_rows:
                        registry, schedule_rows = handle_launch_rows(
                            launch_rows,
                            schedule_csv=schedule_csv,
                            runs_dir=runs_dir,
                            round_index=current_round_index,
                            registry=registry,
                            codex_bin=args.codex_bin,
                            events_log=events_log,
                        )
                        save_registry(registry_json, registry)
                    write_state(
                        state_json,
                        runs_dir=runs_dir,
                        target_rounds=target_rounds,
                        current_round_index=current_round_index,
                        phase="split_recovery",
                        schedule_rows=schedule_rows,
                        registry=registry,
                    )
                    continue
            write_state(
                state_json,
                runs_dir=runs_dir,
                target_rounds=target_rounds,
                current_round_index=current_round_index,
                phase="watch",
                schedule_rows=schedule_rows,
                registry=registry,
            )

            if round_completed(schedule_rows, current_round_index):
                registry = terminate_for_round(current_round_index, registry, events_log)
                save_registry(registry_json, registry)
                write_state(
                    state_json,
                    runs_dir=runs_dir,
                    target_rounds=target_rounds,
                    current_round_index=current_round_index,
                    phase="lint",
                    schedule_rows=read_schedule(schedule_csv),
                    registry=registry,
                )
                lint_ok = run_lint(current_round_index, runs_dir=runs_dir, events_log=events_log)
                schedule_rows = reconcile_deferred_long_tail_rows(schedule_csv, read_schedule(schedule_csv))
                if lint_ok:
                    collect_ok = run_collect(current_round_index, runs_dir=runs_dir, events_log=events_log)
                    if not collect_ok:
                        raise SystemExit(
                            f"Round {current_round_index} lint passed, but collect failed. "
                            "Global final outputs were not safely synchronized."
                        )
                    log_event(events_log, f"[round:complete] round={current_round_index} lint_clean=yes")
                    current_round_index += 1
                    break

                log_event(events_log, f"[round:lint_failed] round={current_round_index} re-entering prepare")
                deferred_rows = analyze_long_tail_deferred_rows(
                    schedule_rows,
                    current_round_index,
                    timeout_seconds=args.batch_timeout_seconds,
                )
                if deferred_rows:
                    deferred_batch_files = {
                        str(row.get("batch_file") or "")
                        for row in deferred_rows
                        if str(row.get("batch_file") or "").strip()
                    }
                    registry = terminate_for_batch_files(
                        deferred_batch_files,
                        registry,
                        events_log,
                        reason=f"round_{current_round_index}_long_tail_timeout_after_lint",
                    )
                    schedule_fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
                    schedule_rows = mark_long_tail_deferred(
                        schedule_csv,
                        schedule_rows,
                        deferred_rows,
                        schedule_fieldnames=schedule_fieldnames,
                        runs_dir=runs_dir,
                        events_log=events_log,
                    )
                    save_registry(registry_json, registry)
                    write_state(
                        state_json,
                        runs_dir=runs_dir,
                        target_rounds=target_rounds,
                        current_round_index=current_round_index,
                        phase="deferred_long_tail",
                        schedule_rows=schedule_rows,
                        registry=registry,
                    )
                    continue

                launch_rows = run_prepare(current_round_index, runs_dir=runs_dir, events_log=events_log)
                if not launch_rows:
                    raise SystemExit(
                        f"Lint failed for round {current_round_index}, but prepare-launches produced no rerun queue."
                    )
                registry, schedule_rows = handle_launch_rows(
                    launch_rows,
                    schedule_csv=schedule_csv,
                    runs_dir=runs_dir,
                    round_index=current_round_index,
                    registry=registry,
                    codex_bin=args.codex_bin,
                    events_log=events_log,
                )
                save_registry(registry_json, registry)
                continue

            has_active_split = any(
                split_state_active(load_json_dict(split_state_path_for_row(row)))
                for row in round_rows(schedule_rows, current_round_index)
            )
            if has_active_split:
                time.sleep(args.poll_seconds)
                continue

            actions = run_watch(
                current_round_index,
                runs_dir=runs_dir,
                startup_timeout_seconds=args.startup_no_row_timeout_seconds,
                partial_stall_timeout_seconds=args.partial_stall_timeout_seconds,
                events_log=events_log,
            )
            if actions:
                registry = terminate_for_actions(actions, registry, events_log)
                save_registry(registry_json, registry)
                launch_rows = run_prepare(current_round_index, runs_dir=runs_dir, events_log=events_log)
                if launch_rows:
                    registry, schedule_rows = handle_launch_rows(
                        launch_rows,
                        schedule_csv=schedule_csv,
                        runs_dir=runs_dir,
                        round_index=current_round_index,
                        registry=registry,
                        codex_bin=args.codex_bin,
                        events_log=events_log,
                    )
                    save_registry(registry_json, registry)
                continue

            time.sleep(args.poll_seconds)

    registry = cleanup_registry(registry)
    save_registry(registry_json, registry)
    schedule_rows = read_schedule(schedule_csv)
    write_state(
        state_json,
        runs_dir=runs_dir,
        target_rounds=target_rounds,
        current_round_index=target_rounds[-1],
        phase="completed",
        schedule_rows=schedule_rows,
        registry=registry,
    )
    update_launcher_state_status(runs_dir, status="completed")
    log_event(events_log, f"[supervisor:complete] rounds={target_rounds[0]}-{target_rounds[-1]}")


def shutil_which(binary: str) -> str | None:
    from shutil import which

    return which(binary)


if __name__ == "__main__":
    try:
        main()
    except SupervisorSignalExit as exc:
        handle_supervisor_signal_exit(exc)
        raise SystemExit(128 + exc.signum)
    except BaseException as exc:
        log_supervisor_terminal_failure(exc)
        raise
