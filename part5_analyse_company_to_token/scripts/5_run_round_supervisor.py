#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import csv
import json
import os
import shlex
import signal
import shutil
import subprocess
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from part5_schedule_io import write_schedule_csv

SCRIPT_DIR = Path(__file__).resolve().parent
PART5_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_DIR.parent
DEFAULT_RUNS_DIR = PART5_DIR / "agent_runs" / "crypto_company_parallel"
DEFAULT_FINAL_DIR = PART5_DIR / "agent_runs" / "crypto_company"
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
DEFAULT_SPLIT_BATCH_RESPAWN_THRESHOLD = 5
DEFAULT_SPLIT_BATCH_FAILURE_THRESHOLD = 3
DEFAULT_CODEX_BIN = shutil.which("codex") or "codex"
DEFAULT_SPLIT_SHARD_SIZE = 15
DEFAULT_SPLIT_SHARD_COUNT = 2
SPLIT_BATCH_LAUNCH_REASON = "split_batch_2x15"
SPLIT_STATE_FILE_NAME = "split_recovery_state.json"
SPLIT_OUTCOME_FILE_NAME = "search_outcome.json"
SPLIT_SHARDS_DIR_NAME = "split_recovery"
DEFERRED_LONG_TAIL_CSV = "deferred_long_tail_batches.csv"
DEFERRED_LONG_TAIL_MD = "deferred_long_tail_batches.md"
GLOBAL_LONG_TAIL_BACKLOG_CSV = DEFAULT_FINAL_DIR / "long_tail_batches_pending.csv"
ROUND_RESOLVED_STATUSES = {"completed", "deferred_long_tail"}
SUPERVISOR_CONTEXT: dict[str, Any] = {}

SPLIT_BATCH_FAILURE_TYPES = {
    "startup_no_row",
    "header_only_timeout",
    "partial_stall",
    "row_count_mismatch",
    "schema_error",
    "agent_unresponsive",
    "verifier_forced_rerun",
}

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the fixed part5 round harness: prepare -> launch -> mark-started -> "
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
    company_type = normalized.get("company_type", "")
    if company_type == "invesment_or_holdings":
        normalized["company_type"] = "investment_or_holdings"

    if fieldnames == RESULT_CSV_COLUMNS:
        token_ticker = normalized.get("token_ticker", "").strip()
        token_name = normalized.get("token_name", "").strip()
        token_url = normalized.get("token_url", "").strip()
        if not token_ticker and not token_name and not token_url:
            normalized["token_ticker"] = "[]"
            normalized["token_name"] = "[]"
            normalized["token_url"] = "[]"

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


def effective_row_status(row: dict[str, str]) -> str:
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


def reconcile_deferred_long_tail_rows(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    changed = False
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
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


def log_event(events_log: Path, message: str) -> None:
    events_log.parent.mkdir(parents=True, exist_ok=True)
    with events_log.open("a", encoding="utf-8") as outfile:
        outfile.write(f"{iso_now()} {message}\n")


def set_supervisor_context(
    *,
    runs_dir: Path,
    schedule_csv: Path,
    state_json: Path,
    registry_json: Path,
    events_log: Path,
    target_rounds: list[int],
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
        }
    )


def log_supervisor_terminal_failure(exc: BaseException) -> None:
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

    if not all(isinstance(item, Path) for item in [runs_dir_raw, schedule_csv_raw, state_json_raw, registry_json_raw]):
        return
    if not isinstance(target_rounds_raw, list) or not target_rounds_raw:
        return

    try:
        schedule_rows = read_schedule(schedule_csv_raw)
    except BaseException:
        schedule_rows = []
    try:
        registry = cleanup_registry(load_registry(registry_json_raw))
    except BaseException:
        registry = []

    if not schedule_rows:
        return

    current_round_index = target_rounds_raw[0]
    state_existing = load_json_dict(state_json_raw)
    if state_existing:
        current_round_index = parse_int(state_existing.get("current_round_index"), current_round_index)

    try:
        write_state(
            state_json_raw,
            runs_dir=runs_dir_raw,
            target_rounds=target_rounds_raw,
            current_round_index=current_round_index,
            phase="failed",
            schedule_rows=schedule_rows,
            registry=registry,
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


def terminate_pid(pid: int, events_log: Path, reason: str) -> None:
    if pid <= 0 or not process_alive(pid):
        return
    log_event(events_log, f"[worker:terminate] pid={pid} reason={reason}")
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        return
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.time() + 10
    while time.time() < deadline:
        if not process_alive(pid):
            return
        time.sleep(0.25)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return


def cleanup_registry(registry: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    for item in registry:
        pid = parse_int(item.get("pid"), 0)
        if process_alive(pid):
            cleaned.append(item)
    return cleaned


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
            terminate_pid(parse_int(entry.get("pid"), 0), events_log, reason)
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
            terminate_pid(parse_int(entry.get("pid"), 0), events_log, f"round_{round_index}_cleanup")
        else:
            remaining.append(entry)
    return cleanup_registry(remaining)


def active_full_batch_pid(
    registry: list[dict[str, Any]],
    *,
    batch_file: str,
    attempt_index: int,
) -> int:
    for entry in registry:
        if str(entry.get("split_shard_id") or "").strip():
            continue
        if str(entry.get("batch_file") or "") != batch_file:
            continue
        if parse_int(entry.get("attempt_index"), 0) != attempt_index:
            continue
        pid = parse_int(entry.get("pid"), 0)
        if process_alive(pid):
            return pid
    return 0


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
        if active_full_batch_pid(registry, batch_file=batch_file, attempt_index=attempt_index):
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
            terminate_pid(
                parse_int(entry.get("pid"), 0),
                events_log,
                f"runtime_action:{entry.get('batch_file', '')}",
            )
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
        "workspace-write",
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
            start_new_session=True,
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
        "started_at": iso_now(),
    }
    log_event(
        events_log,
        (
            "[worker:spawn] "
            f"round={entry['round_index']} slot={entry['worker_slot']} "
            f"attempt={entry['attempt_index']} pid={entry['pid']} "
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
    token_rows = 0
    searched_no_token_rows = 0
    skip_candidate_rows = 0
    manual_review_rows = 0
    for row in rows:
        token_values = parse_json_list(row.get("token_ticker", ""))
        if token_values:
            token_rows += 1
        else:
            if (row.get("project_search_required") or "").strip() == "yes":
                searched_no_token_rows += 1
            else:
                skip_candidate_rows += 1
        if (row.get("needs_manual_review") or "").strip() == "yes":
            manual_review_rows += 1
    summary = {
        "task_count": task_count,
        "rows_written": len(rows),
        "rows_with_ticker": token_rows,
        "rows_without_ticker": max(0, len(rows) - token_rows),
        "searched_no_token_rows": searched_no_token_rows,
        "skip_candidate_rows": skip_candidate_rows,
        "manual_review_rows": manual_review_rows,
        "search_complete": len(rows) == task_count,
    }
    if len(rows) < task_count:
        summary["completion_reason"] = "interrupted_incomplete"
    elif token_rows > 0:
        summary["completion_reason"] = "completed_with_tokens_found"
    elif searched_no_token_rows == task_count:
        summary["completion_reason"] = "all_companies_searched_no_token"
    else:
        summary["completion_reason"] = "all_rows_resolved_zero_ticker_mixed_skip_and_search"
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
            "- Every company in this shard must be searched before you conclude that no fungible token ticker exists.\n"
            "- Do not use `search_tier = skip_candidate` in classifier output for this shard.\n"
            "- Set `project_search_required = yes` for every company in this shard.\n"
            "- If a company appears non-tokenized after best-effort research, keep `token_ticker = []` but still include real evidence URLs and source types.\n"
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
        "- If a company truly has no supported fungible token ticker after best-effort search, keep `token_ticker = []` but still provide real evidence and keep the row schema-valid.\n"
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
    split_root = active_attempt_dir / SPLIT_SHARDS_DIR_NAME
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
            terminate_pid(parse_int(entry.get("pid"), 0), events_log, reason)
        else:
            remaining.append(entry)
    return cleanup_registry(remaining)


def active_split_shard_pid(
    registry: list[dict[str, Any]],
    *,
    batch_file: str,
    attempt_index: int,
    shard_id: str,
) -> int:
    for entry in registry:
        if split_shard_registry_match(entry, batch_file=batch_file, attempt_index=attempt_index, shard_id=shard_id):
            pid = parse_int(entry.get("pid"), 0)
            if process_alive(pid):
                return pid
    return 0


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
        if active_split_shard_pid(
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
    write_csv_rows(classifier_path, CLASSIFIER_CSV_COLUMNS, merged_classifier_rows)
    write_csv_rows(results_path, RESULT_CSV_COLUMNS, merged_result_rows)

    summary = summarize_result_rows(merged_result_rows, len(tasks))
    summary.update(
        {
            "mode": SPLIT_BATCH_LAUNCH_REASON,
            "batch_file": str(row.get("batch_file") or ""),
            "attempt_index": parse_int(row.get("attempt_index"), 0),
            "merged_at": iso_now(),
        }
    )
    outcome_path = split_outcome_path_for_row(row)
    write_json_dict(outcome_path, summary)
    final_message_path = resolve_repo_path(str(row.get("active_attempt") or "")) / "final_message.md"
    final_message_path.write_text(
        (
            f"Split batch recovery merged successfully.\n"
            f"mode: {summary['mode']}\n"
            f"rows_written: {summary['rows_written']}/{summary['task_count']}\n"
            f"rows_with_ticker: {summary['rows_with_ticker']}\n"
            f"searched_no_token_rows: {summary['searched_no_token_rows']}\n"
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
    write_json_dict(split_state_path_for_row(row), split_state)
    log_event(
        events_log,
        (
            "[split_batch:merge] "
            f"round={row.get('round_index', '')} slot={row.get('worker_slot', '')} "
            f"batch={row.get('batch_file', '')} attempt={row.get('attempt_index', '')} "
            f"rows_with_ticker={summary['rows_with_ticker']} "
            f"searched_no_token_rows={summary['searched_no_token_rows']} "
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

        progress_classifier_rows = 0
        progress_result_rows = 0
        all_completed = True
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
            alive_pid = active_split_shard_pid(
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

            if inspection["state"] == "header_only" and elapsed_since_start >= startup_timeout_seconds:
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
            if inspection["state"] in {"partial_prefix", "partial_misaligned"} and elapsed_since_progress >= partial_stall_timeout_seconds:
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
            if not alive_pid and str(shard.get("status") or "") != "completed":
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

        split_state["progress_classifier_rows"] = progress_classifier_rows
        split_state["progress_result_rows"] = progress_result_rows
        split_state["updated_at"] = now_iso
        write_json_dict(split_state_path, split_state)

        updated["status"] = "running"
        updated["last_seen_classifier_rows"] = str(progress_classifier_rows)
        updated["last_seen_result_rows"] = str(progress_result_rows)
        if progress_classifier_rows > 0 or progress_result_rows > 0:
            updated["first_row_at"] = updated.get("first_row_at") or now_iso
            updated["last_progress_at"] = now_iso
        changed = True

        if all_completed:
            summary = merge_split_outputs(updated, split_state, events_log=events_log)
            updated["status"] = "completed"
            updated["prepared_mode"] = ""
            updated["prepared_reason"] = ""
            updated["planned_rotate"] = ""
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
        str((DEFAULT_FINAL_DIR / "verification_findings.csv").resolve()),
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
    if args.split_batch_respawn_threshold <= 0:
        raise SystemExit("--split-batch-respawn-threshold must be greater than 0.")
    if args.split_batch_failure_threshold <= 0:
        raise SystemExit("--split-batch-failure-threshold must be greater than 0.")

    runs_dir = args.runs_dir.resolve()
    schedule_csv = resolve_runs_path(runs_dir, args.schedule_csv, DEFAULT_SCHEDULE_CSV)
    state_json = resolve_runs_path(runs_dir, args.state_json, DEFAULT_STATE_JSON)
    registry_json = resolve_runs_path(runs_dir, args.registry_json, DEFAULT_REGISTRY_JSON)
    events_log = resolve_runs_path(runs_dir, args.events_log, DEFAULT_EVENTS_LOG)
    lock_file = runs_dir / DEFAULT_LOCK_FILE
    target_rounds = list(range(args.start_round_index, args.start_round_index + args.round_count))
    set_supervisor_context(
        runs_dir=runs_dir,
        schedule_csv=schedule_csv,
        state_json=state_json,
        registry_json=registry_json,
        events_log=events_log,
        target_rounds=target_rounds,
    )

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
    log_event(events_log, f"[supervisor:complete] rounds={target_rounds[0]}-{target_rounds[-1]}")


def shutil_which(binary: str) -> str | None:
    from shutil import which

    return which(binary)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        log_supervisor_terminal_failure(exc)
        raise
