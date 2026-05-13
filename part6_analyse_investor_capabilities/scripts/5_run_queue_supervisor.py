#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
import time
from pathlib import Path
from typing import Any

from part6_schedule_io import write_schedule_csv


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent

QUEUE_SCHEDULE_COLUMNS = [
    "slot_id",
    "queue_order",
    "queue_state",
    "collect_state",
    "ready_to_collect_at",
    "collected_at",
    "last_collected_attempt_index",
    "collect_failure_reason",
    "tail_retry_pending",
    "tail_retry_count",
]
COLLECT_STATE_VALUES = {"pending", "running", "done", "failed", "skipped"}
RUNNING_PHASES = {
    "watch",
    "fill_slots",
    "collect",
    "split_recovery",
    "deferred_long_tail",
    "tail_retry_pending",
}
DEFAULT_MAX_TAIL_RETRIES = 1
TAIL_RETRY_PENDING_VALUE = "yes"


def load_round_supervisor_module() -> Any:
    module_path = SCRIPT_DIR / "5_run_round_supervisor.py"
    spec = importlib.util.spec_from_file_location("part6_round_supervisor", module_path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load round supervisor helpers from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ROUND = load_round_supervisor_module()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the queue-based part6 harness: keep up to N active batch slots, "
            "launch the next waiting batch immediately, and collect completed batches "
            "independently without round barriers."
        ),
    )
    parser.add_argument("--runs-dir", type=Path, default=ROUND.DEFAULT_RUNS_DIR)
    parser.add_argument("--schedule-csv", type=Path, default=None)
    parser.add_argument("--start-round-index", type=int, required=True)
    parser.add_argument("--round-count", type=int, required=True)
    parser.add_argument("--max-workers", type=int, default=5)
    parser.add_argument("--poll-seconds", type=int, default=ROUND.DEFAULT_POLL_SECONDS)
    parser.add_argument(
        "--batch-timeout-seconds",
        type=int,
        default=ROUND.DEFAULT_BATCH_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--startup-no-row-timeout-seconds",
        type=int,
        default=ROUND.DEFAULT_STARTUP_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--partial-stall-timeout-seconds",
        type=int,
        default=ROUND.DEFAULT_PARTIAL_STALL_TIMEOUT_SECONDS,
    )
    parser.add_argument("--codex-bin", default=ROUND.DEFAULT_CODEX_BIN)
    parser.add_argument("--state-json", type=Path, default=None)
    parser.add_argument("--registry-json", type=Path, default=None)
    parser.add_argument("--events-log", type=Path, default=None)
    parser.add_argument(
        "--disable-split-batch-recovery",
        action="store_true",
        help="Disable automatic 2-worker split recovery for long-tail batches.",
    )
    parser.add_argument(
        "--split-batch-respawn-threshold",
        dest="split_batch_respawn_threshold",
        type=int,
        default=ROUND.DEFAULT_SPLIT_BATCH_RESPAWN_THRESHOLD,
    )
    parser.add_argument(
        "--split-batch-failure-threshold",
        dest="split_batch_failure_threshold",
        type=int,
        default=ROUND.DEFAULT_SPLIT_BATCH_FAILURE_THRESHOLD,
    )
    return parser.parse_args()


def effective_status(row: dict[str, str]) -> str:
    if ROUND.row_is_deferred_long_tail(row):
        return "deferred_long_tail"
    return str(row.get("status") or "").strip() or "prepared"


def parse_batch_number(batch_file: str) -> int:
    stem = Path(batch_file).stem
    try:
        return int(stem.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def parse_slot_id(value: Any) -> int:
    return ROUND.parse_int(value, 0)


def parse_tail_retry_count(value: Any) -> int:
    return max(0, ROUND.parse_int(value, 0))


def row_tail_retry_pending(row: dict[str, str]) -> bool:
    return str(row.get("tail_retry_pending") or "").strip().lower() == TAIL_RETRY_PENDING_VALUE


def row_sort_key(row: dict[str, str]) -> tuple[int, int, str]:
    queue_order = ROUND.parse_int(row.get("queue_order"), 0)
    batch_number = parse_batch_number(str(row.get("batch_file") or ""))
    if queue_order <= 0:
        queue_order = batch_number
    return (
        queue_order if queue_order > 0 else 10**9,
        ROUND.parse_int(row.get("round_index"), 0),
        str(row.get("batch_file") or ""),
    )


def load_schedule_with_queue_columns(
    schedule_csv: Path,
    *,
    state_hint: dict[str, Any] | None,
) -> tuple[list[str], list[dict[str, str]]]:
    fieldnames, raw_rows = ROUND.load_csv_rows_with_fields(schedule_csv)
    if not raw_rows:
        raise SystemExit(f"Schedule has no rows: {schedule_csv}")

    updated_fields = list(fieldnames)
    changed = False
    for field in QUEUE_SCHEDULE_COLUMNS:
        if field not in updated_fields:
            updated_fields.append(field)
            changed = True

    collected_round_cutoff = 0
    if state_hint and str(state_hint.get("scheduler_mode") or "").strip() != "queue":
        collected_round_cutoff = max(0, ROUND.parse_int(state_hint.get("current_round_index"), 0) - 1)

    normalized_rows: list[dict[str, str]] = []
    for index, raw_row in enumerate(raw_rows, start=1):
        updated = {field: str(raw_row.get(field, "") or "") for field in updated_fields}
        batch_number = parse_batch_number(updated.get("batch_file", ""))
        if not updated.get("queue_order"):
            updated["queue_order"] = str(batch_number or index)
            changed = True
        status = effective_status(updated)
        collect_state = str(updated.get("collect_state") or "").strip()
        if collect_state not in COLLECT_STATE_VALUES:
            if status == "deferred_long_tail":
                collect_state = "skipped"
            elif status == "completed" and ROUND.parse_int(updated.get("round_index"), 0) <= collected_round_cutoff:
                collect_state = "done"
            else:
                collect_state = "pending"
            updated["collect_state"] = collect_state
            changed = True
        if (
            collect_state == "done"
            and not updated.get("last_collected_attempt_index")
            and status == "completed"
            and ROUND.parse_int(updated.get("round_index"), 0) <= collected_round_cutoff
        ):
            updated["last_collected_attempt_index"] = str(updated.get("attempt_index") or "")
            changed = True
        normalized_tail_retry_pending = TAIL_RETRY_PENDING_VALUE if row_tail_retry_pending(updated) else ""
        if updated.get("tail_retry_pending") != normalized_tail_retry_pending:
            updated["tail_retry_pending"] = normalized_tail_retry_pending
            changed = True
        normalized_tail_retry_count = str(parse_tail_retry_count(updated.get("tail_retry_count")))
        if updated.get("tail_retry_count") != normalized_tail_retry_count:
            updated["tail_retry_count"] = normalized_tail_retry_count
            changed = True
        normalized_rows.append(updated)

    if changed:
        write_schedule_csv(schedule_csv, normalized_rows, fieldnames=updated_fields)
    return updated_fields, normalized_rows


def row_has_live_registry_entry(row: dict[str, str], registry: list[dict[str, Any]]) -> bool:
    batch_file = str(row.get("batch_file") or "")
    attempt_index = ROUND.parse_int(row.get("attempt_index"), 0)
    for entry in registry:
        if str(entry.get("batch_file") or "") != batch_file:
            continue
        if ROUND.parse_int(entry.get("attempt_index"), 0) != attempt_index:
            continue
        if ROUND.process_alive(ROUND.parse_int(entry.get("pid"), 0)):
            return True
    return False


def row_has_active_split(row: dict[str, str]) -> bool:
    return ROUND.split_state_active(ROUND.load_json_dict(ROUND.split_state_path_for_row(row)))


def row_is_actively_running(row: dict[str, str], registry: list[dict[str, Any]]) -> bool:
    if effective_status(row) != "running":
        return False
    return row_has_live_registry_entry(row, registry) or row_has_active_split(row)


def normalize_queue_rows(
    schedule_rows: list[dict[str, str]],
    *,
    registry: list[dict[str, Any]],
    max_workers: int,
) -> tuple[list[dict[str, str]], bool]:
    changed = False
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        status = effective_status(updated)
        collect_state = str(updated.get("collect_state") or "").strip()
        current_attempt_index = ROUND.parse_int(updated.get("attempt_index"), 0)
        last_collected_attempt_index = ROUND.parse_int(updated.get("last_collected_attempt_index"), 0)
        has_live_registry = row_has_live_registry_entry(updated, registry)
        has_active_split = row_has_active_split(updated)
        attempt_start_prefix_rows = ROUND.parse_int(updated.get("attempt_start_prefix_rows"), 0)
        current_progress_rows = min(
            ROUND.parse_int(updated.get("last_seen_classifier_rows"), 0),
            ROUND.parse_int(updated.get("last_seen_result_rows"), 0),
        )
        has_attempt_progress = current_progress_rows > attempt_start_prefix_rows
        rerun_reason = str(
            updated.get("prepared_reason") or updated.get("last_rerun_reason") or ""
        ).strip()
        split_launch_requested = rerun_reason == ROUND.SPLIT_BATCH_LAUNCH_REASON
        queue_state = str(updated.get("queue_state") or "").strip()
        progress_implies_live_attempt = has_attempt_progress and (
            parse_slot_id(updated.get("slot_id")) > 0 or queue_state in {"running", "launching"}
        )

        if last_collected_attempt_index > 0 and current_attempt_index > last_collected_attempt_index and collect_state == "done":
            updated["collect_state"] = "pending"
            updated["collected_at"] = ""
            collect_state = "pending"
            changed = True

        if status in {"prepared", "needs_rerun"} and (
            has_live_registry
            or has_active_split
            or (progress_implies_live_attempt and not split_launch_requested)
        ):
            updated["status"] = "running"
            status = "running"
            changed = True
            if not str(updated.get("started_at") or "").strip():
                started_at = ""
                for entry in registry:
                    if str(entry.get("batch_file") or "") != str(updated.get("batch_file") or ""):
                        continue
                    if ROUND.parse_int(entry.get("attempt_index"), 0) != current_attempt_index:
                        continue
                    if not ROUND.process_alive(ROUND.parse_int(entry.get("pid"), 0)):
                        continue
                    started_at = str(entry.get("started_at") or "").strip()
                    if started_at:
                        break
                started_at = started_at or str(updated.get("last_rerun_at") or "").strip() or ROUND.iso_now()
                updated["started_at"] = started_at
                updated["round_entry_started_at"] = str(updated.get("round_entry_started_at") or "").strip() or started_at
                changed = True
            if (
                ROUND.parse_int(updated.get("last_seen_classifier_rows"), 0) > 0
                or ROUND.parse_int(updated.get("last_seen_result_rows"), 0) > 0
            ):
                if not str(updated.get("first_row_at") or "").strip():
                    updated["first_row_at"] = str(updated.get("started_at") or "").strip() or ROUND.iso_now()
                    changed = True
                if not str(updated.get("last_progress_at") or "").strip():
                    updated["last_progress_at"] = str(updated.get("started_at") or "").strip() or ROUND.iso_now()
                    changed = True

        if status == "deferred_long_tail":
            if updated.get("tail_retry_pending"):
                updated["tail_retry_pending"] = ""
                changed = True
            if updated.get("queue_state") != "deferred_long_tail":
                updated["queue_state"] = "deferred_long_tail"
                changed = True
            if updated.get("collect_state") != "skipped":
                updated["collect_state"] = "skipped"
                changed = True
            if updated.get("slot_id"):
                updated["slot_id"] = ""
                changed = True
            updated_rows.append(updated)
            continue

        if status == "completed":
            if updated.get("tail_retry_pending"):
                updated["tail_retry_pending"] = ""
                changed = True
            desired_queue_state = "completed" if collect_state == "done" else "collecting" if collect_state == "running" else "ready_to_collect"
            if updated.get("queue_state") != desired_queue_state:
                updated["queue_state"] = desired_queue_state
                changed = True
            if desired_queue_state == "ready_to_collect" and not updated.get("ready_to_collect_at"):
                updated["ready_to_collect_at"] = updated.get("last_progress_at") or updated.get("started_at") or updated.get("last_rerun_at") or ROUND.iso_now()
                changed = True
            if updated.get("slot_id"):
                updated["slot_id"] = ""
                changed = True
            updated_rows.append(updated)
            continue

        if status in {"prepared", "needs_rerun"}:
            desired_queue_state = "tail_retry_pending" if row_tail_retry_pending(updated) else "queued"
            if updated.get("queue_state") != desired_queue_state:
                updated["queue_state"] = desired_queue_state
                changed = True
            if updated.get("slot_id"):
                updated["slot_id"] = ""
                changed = True
            updated_rows.append(updated)
            continue

        if status == "running":
            if updated.get("tail_retry_pending"):
                updated["tail_retry_pending"] = ""
                changed = True
            # Keep `running` sticky until runtime reconciliation explicitly proves the
            # attempt is dead or completed. This avoids duplicate launches after a
            # crash between spawn and registry persistence.
            desired_queue_state = "running"
            if updated.get("queue_state") != desired_queue_state:
                updated["queue_state"] = desired_queue_state
                changed = True
            updated_rows.append(updated)
            continue

        if updated.get("queue_state") != "queued":
            updated["queue_state"] = "queued"
            changed = True
        if updated.get("slot_id"):
            updated["slot_id"] = ""
            changed = True
        updated_rows.append(updated)

    used_slots = {
        parse_slot_id(row.get("slot_id"))
        for row in updated_rows
        if row_is_actively_running(row, registry) and 1 <= parse_slot_id(row.get("slot_id")) <= max_workers
    }
    available_slots = [slot_id for slot_id in range(1, max_workers + 1) if slot_id not in used_slots]
    pending_slot_rows = [
        row
        for row in updated_rows
        if row_is_actively_running(row, registry) and parse_slot_id(row.get("slot_id")) <= 0
    ]
    pending_slot_rows.sort(key=row_sort_key)
    for row, slot_id in zip(pending_slot_rows, available_slots):
        row["slot_id"] = str(slot_id)
        changed = True
    return updated_rows, changed


def save_schedule(schedule_csv: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    normalized_rows = [{field: str(row.get(field, "") or "") for field in fieldnames} for row in rows]
    write_schedule_csv(schedule_csv, normalized_rows, fieldnames=fieldnames)


def refresh_schedule(
    schedule_csv: Path,
    *,
    fieldnames: list[str],
    state_hint: dict[str, Any] | None,
    registry: list[dict[str, Any]],
    max_workers: int,
) -> list[dict[str, str]]:
    schedule_rows = ROUND.reconcile_deferred_long_tail_rows(schedule_csv, ROUND.read_schedule(schedule_csv))
    schedule_rows, changed = normalize_queue_rows(
        schedule_rows,
        registry=registry,
        max_workers=max_workers,
    )
    if changed:
        save_schedule(schedule_csv, fieldnames, schedule_rows)
    return schedule_rows


def target_scope_rows(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> list[dict[str, str]]:
    target_set = set(target_rounds)
    return [
        row
        for row in schedule_rows
        if ROUND.parse_int(row.get("round_index"), 0) in target_set
    ]


def row_has_open_queue_work(row: dict[str, str]) -> bool:
    status = effective_status(row)
    if status == "deferred_long_tail":
        return False
    if status == "completed" and str(row.get("collect_state") or "").strip() == "done":
        return False
    return True


def earliest_open_round(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> int:
    target_set = set(target_rounds)
    open_rounds = sorted(
        {
            ROUND.parse_int(row.get("round_index"), 0)
            for row in schedule_rows
            if ROUND.parse_int(row.get("round_index"), 0) in target_set and row_has_open_queue_work(row)
        }
    )
    if open_rounds:
        return open_rounds[0]
    return target_rounds[-1]


def waiting_rows(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> list[dict[str, str]]:
    rows = [
        row
        for row in target_scope_rows(schedule_rows, target_rounds)
        if effective_status(row) in {"prepared", "needs_rerun"} and not row_tail_retry_pending(row)
    ]
    rows.sort(key=row_sort_key)
    return rows


def tail_retry_rows(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> list[dict[str, str]]:
    rows = [
        row
        for row in target_scope_rows(schedule_rows, target_rounds)
        if effective_status(row) in {"prepared", "needs_rerun"} and row_tail_retry_pending(row)
    ]
    rows.sort(key=row_sort_key)
    return rows


def ready_to_collect_rows(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> list[dict[str, str]]:
    rows = [
        row
        for row in target_scope_rows(schedule_rows, target_rounds)
        if effective_status(row) == "completed" and str(row.get("collect_state") or "").strip() != "done"
    ]
    rows.sort(key=row_sort_key)
    return rows


def verification_summary_is_uninitialized(summary_path: Path) -> bool:
    try:
        text = summary_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "- status: pending" in text


def verification_gate_state(row: dict[str, str]) -> tuple[str, str]:
    report_raw = str(row.get("verification_report_csv") or "").strip()
    summary_raw = str(row.get("verification_summary_md") or "").strip()
    if not report_raw or not summary_raw:
        return "pending", "missing_verification_artifacts"
    report_path = ROUND.resolve_repo_path(report_raw)
    summary_path = ROUND.resolve_repo_path(summary_raw)
    tasks_path_raw = str(row.get("tasks_file") or "").strip()
    if not report_path.exists() or not summary_path.exists() or not tasks_path_raw:
        return "pending", "missing_verification_artifacts"

    expected_task_indexes = {
        str(task.get("task_index", "")).strip()
        for task in ROUND.load_jsonl_tasks(ROUND.resolve_repo_path(tasks_path_raw))
        if str(task.get("task_index", "")).strip()
    }
    if not expected_task_indexes:
        return "pending", "missing_tasks"

    seen_task_indexes: set[str] = set()
    saw_any_report_rows = False
    try:
        with report_path.open("r", encoding="utf-8", newline="") as handle:
            for report_row in csv.DictReader(handle):
                saw_any_report_rows = True
                task_index = str(report_row.get("task_index") or "").strip()
                if task_index not in expected_task_indexes:
                    continue
                seen_task_indexes.add(task_index)
                verdict = str(report_row.get("verdict") or "").strip()
                recommended_action = str(report_row.get("recommended_action") or "").strip()
                if verdict and verdict != "pass" and not recommended_action:
                    return "pending", "non_pass_without_action"
                if recommended_action in {"rerun_batch", "rerun_investor"}:
                    return "rerun_required", recommended_action
                if recommended_action == "update_prompt_or_process":
                    return "pending", "update_prompt_or_process"
                if recommended_action == "edit_row" and not str(report_row.get("corrected_result_row_json") or "").strip():
                    return "pending", "edit_row_missing_correction"
    except OSError:
        return "pending", "verification_read_error"

    if seen_task_indexes != expected_task_indexes:
        if (
            not saw_any_report_rows
            and not seen_task_indexes
            and verification_summary_is_uninitialized(summary_path)
        ):
            # Legacy round-mode runs collected with --skip-verification and left the
            # verifier report/summary as empty templates. Queue mode must not deadlock
            # forever on those uninitialized artifacts.
            return "ready_skip_verification", "legacy_uninitialized_verifier"
        return "pending", "missing_verifier_rows"
    return "ready", ""


def deferred_rows(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> list[dict[str, str]]:
    rows = [
        row
        for row in target_scope_rows(schedule_rows, target_rounds)
        if effective_status(row) == "deferred_long_tail"
    ]
    rows.sort(key=row_sort_key)
    return rows


def active_running_rows(
    schedule_rows: list[dict[str, str]],
    target_rounds: list[int],
    registry: list[dict[str, Any]],
) -> list[dict[str, str]]:
    rows = [
        row
        for row in target_scope_rows(schedule_rows, target_rounds)
        if row_is_actively_running(row, registry)
    ]
    rows.sort(key=lambda row: (parse_slot_id(row.get("slot_id")), *row_sort_key(row)))
    return rows


def live_worker_process_count(registry: list[dict[str, Any]]) -> int:
    return sum(1 for entry in registry if ROUND.process_alive(ROUND.parse_int(entry.get("pid"), 0)))


def build_slots(
    schedule_rows: list[dict[str, str]],
    *,
    target_rounds: list[int],
    registry: list[dict[str, Any]],
    max_workers: int,
) -> list[dict[str, Any]]:
    slots: list[dict[str, Any]] = []
    active_rows = active_running_rows(schedule_rows, target_rounds, registry)
    row_by_slot = {
        parse_slot_id(row.get("slot_id")): row
        for row in active_rows
        if 1 <= parse_slot_id(row.get("slot_id")) <= max_workers
    }
    for slot_id in range(1, max_workers + 1):
        row = row_by_slot.get(slot_id)
        if row is None:
            slots.append({"slot_id": slot_id, "state": "idle"})
            continue
        batch_file = str(row.get("batch_file") or "")
        attempt_index = ROUND.parse_int(row.get("attempt_index"), 0)
        pid_count = sum(
            1
            for entry in registry
            if str(entry.get("batch_file") or "") == batch_file
            and ROUND.parse_int(entry.get("attempt_index"), 0) == attempt_index
            and ROUND.process_alive(ROUND.parse_int(entry.get("pid"), 0))
        )
        slots.append(
            {
                "slot_id": slot_id,
                "state": "running",
                "batch_file": batch_file,
                "round_index": ROUND.parse_int(row.get("round_index"), 0),
                "attempt_index": attempt_index,
                "queue_state": row.get("queue_state") or "",
                "split_recovery": row_has_active_split(row),
                "pid_count": pid_count,
            }
        )
    return slots


def write_state(
    path: Path,
    *,
    runs_dir: Path,
    target_rounds: list[int],
    phase: str,
    schedule_rows: list[dict[str, str]],
    registry: list[dict[str, Any]],
    max_workers: int,
) -> None:
    waiting = waiting_rows(schedule_rows, target_rounds)
    tail_retry_queue = tail_retry_rows(schedule_rows, target_rounds)
    collect_queue = ready_to_collect_rows(schedule_rows, target_rounds)
    deferred_queue = deferred_rows(schedule_rows, target_rounds)
    current_round_index = earliest_open_round(schedule_rows, target_rounds)
    payload = {
        "updated_at": ROUND.iso_now(),
        "runs_dir": str(runs_dir),
        "target_rounds": target_rounds,
        "current_round_index": current_round_index,
        "phase": phase,
        "scheduler_mode": "queue",
        "strict_wait_for_all_rounds": False,
        "max_workers": max_workers,
        "slots": build_slots(
            schedule_rows,
            target_rounds=target_rounds,
            registry=registry,
            max_workers=max_workers,
        ),
        "waiting_queue": [
            {
                "batch_file": row.get("batch_file") or "",
                "round_index": ROUND.parse_int(row.get("round_index"), 0),
                "status": effective_status(row),
                "queue_state": row.get("queue_state") or "",
                "prepared_reason": row.get("prepared_reason") or "",
            }
            for row in waiting
        ],
        "tail_retry_queue": [
            {
                "batch_file": row.get("batch_file") or "",
                "round_index": ROUND.parse_int(row.get("round_index"), 0),
                "status": effective_status(row),
                "queue_state": row.get("queue_state") or "",
                "prepared_reason": row.get("prepared_reason") or "",
                "tail_retry_count": parse_tail_retry_count(row.get("tail_retry_count")),
            }
            for row in tail_retry_queue
        ],
        "collect_queue": [
            {
                "batch_file": row.get("batch_file") or "",
                "round_index": ROUND.parse_int(row.get("round_index"), 0),
                "attempt_index": ROUND.parse_int(row.get("attempt_index"), 0),
                "collect_state": row.get("collect_state") or "",
                "ready_to_collect_at": row.get("ready_to_collect_at") or "",
            }
            for row in collect_queue
        ],
        "deferred_queue": [
            {
                "batch_file": row.get("batch_file") or "",
                "round_index": ROUND.parse_int(row.get("round_index"), 0),
                "deferred_reason": row.get("deferred_reason") or "",
            }
            for row in deferred_queue
        ],
        "completed_batch_count": sum(
            1
            for row in target_scope_rows(schedule_rows, target_rounds)
            if effective_status(row) == "deferred_long_tail"
            or (effective_status(row) == "completed" and str(row.get("collect_state") or "").strip() == "done")
        ),
        "collect_backlog_count": len(collect_queue),
        "tail_retry_backlog_count": len(tail_retry_queue),
        "round_summaries": {
            str(round_index): ROUND.summarize_round(schedule_rows, round_index)
            for round_index in target_rounds
        },
        "managed_processes": registry,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_mark_started_for_batches(
    round_index: int,
    batch_files: list[str],
    *,
    runs_dir: Path,
    events_log: Path,
) -> None:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "4_manage_round_runtime.py"),
        "--runs-dir",
        str(runs_dir),
        "--round-index",
        str(round_index),
        "--mark-round-started",
    ]
    for batch_file in batch_files:
        cmd.extend(["--batch-file", batch_file])
    completed = ROUND.run_command(
        cmd,
        cwd=ROUND.REPO_ROOT,
        events_log=events_log,
        label=f"mark_started_round_{round_index}_selected",
    )
    if completed.returncode != 0:
        raise SystemExit(f"mark-round-started failed for round {round_index} batch scope")


def run_prepare_for_batches(
    round_index: int,
    batch_files: list[str],
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
    for batch_file in batch_files:
        cmd.extend(["--batch-file", batch_file])
    completed = ROUND.run_command(
        cmd,
        cwd=ROUND.REPO_ROOT,
        events_log=events_log,
        label=f"prepare_round_{round_index}_selected",
    )
    if completed.returncode != 0:
        raise SystemExit(f"prepare-launches failed for round {round_index} batch scope")
    return ROUND.parse_launch_queue(runs_dir, round_index)


def run_lint_for_batches(
    batch_files: list[str],
    *,
    runs_dir: Path,
    events_log: Path,
) -> bool:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "3_collect_results.py"),
        "--runs-dir",
        str(runs_dir),
        "--lint-only",
        "--repair-identity-drift-in-place",
        "--fail-on-identity-drift",
    ]
    for batch_file in batch_files:
        cmd.extend(["--batch-file", batch_file])
    completed = ROUND.run_command(cmd, cwd=ROUND.REPO_ROOT, events_log=events_log, label="lint_batches")
    return completed.returncode == 0


def run_collect_for_batches(
    batch_files: list[str],
    *,
    runs_dir: Path,
    events_log: Path,
    skip_verification: bool = False,
) -> bool:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "3_collect_results.py"),
        "--runs-dir",
        str(runs_dir),
        "--repair-identity-drift-in-place",
        "--fail-on-identity-drift",
        "--output-csv",
        str((ROUND.DEFAULT_FINAL_DIR / "results.csv").resolve()),
        "--manual-review-csv",
        str((ROUND.DEFAULT_FINAL_DIR / "needs_manual_review.csv").resolve()),
        "--classifier-results-csv",
        str((ROUND.DEFAULT_FINAL_DIR / "classifier_results.csv").resolve()),
        "--verification-findings-csv",
        str((ROUND.DEFAULT_FINAL_DIR / "verification_findings.csv").resolve()),
        "--checkpoint-json",
        str((runs_dir / ROUND.DEFAULT_COLLECT_CHECKPOINT_JSON).resolve()),
    ]
    if skip_verification:
        cmd.append("--skip-verification")
    for batch_file in batch_files:
        cmd.extend(["--batch-file", batch_file])
    completed = ROUND.run_command(cmd, cwd=ROUND.REPO_ROOT, events_log=events_log, label="collect_batches")
    return completed.returncode == 0


def reset_csv_to_header(path: Path, fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()


def quarantine_attempt_outputs(row: dict[str, str], *, reason: str, events_log: Path) -> None:
    timestamp = ROUND.iso_now().replace(":", "").replace("-", "")
    targets = [
        (ROUND.resolve_repo_path(str(row.get("classifier_results_csv") or "")), ROUND.CLASSIFIER_CSV_COLUMNS),
        (ROUND.resolve_repo_path(str(row.get("results_csv") or "")), ROUND.RESULT_CSV_COLUMNS),
    ]
    batch_file = str(row.get("batch_file") or "")
    attempt_index = str(row.get("attempt_index") or "")
    for path, fieldnames in targets:
        if not str(path):
            continue
        if path.exists():
            archived = path.with_name(f"{path.stem}.{reason}.{timestamp}{path.suffix}.bak")
            try:
                path.replace(archived)
                ROUND.log_event(
                    events_log,
                    f"[queue:quarantine_attempt_output] batch={batch_file} attempt={attempt_index} path={path} archived={archived}",
                )
            except OSError as exc:
                ROUND.log_event(
                    events_log,
                    f"[queue:quarantine_attempt_output_failed] batch={batch_file} attempt={attempt_index} path={path} error={exc}",
                )
        reset_csv_to_header(path, fieldnames)


def apply_batch_row_updates(
    schedule_rows: list[dict[str, str]],
    *,
    batch_files: list[str],
    update_fn,
) -> list[dict[str, str]]:
    target = set(batch_files)
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        if str(row.get("batch_file") or "") in target:
            updated_rows.append(update_fn(dict(row)))
        else:
            updated_rows.append(dict(row))
    return updated_rows


def reserve_launch_slots(
    schedule_rows: list[dict[str, str]],
    *,
    selections: list[dict[str, Any]],
) -> list[dict[str, str]]:
    by_batch = {str(item["launch_row"]["batch_file"]): item for item in selections}
    started_at = ROUND.iso_now()

    def _update(row: dict[str, str]) -> dict[str, str]:
        selection = by_batch[str(row.get("batch_file") or "")]
        launch_row = selection["launch_row"]
        instructions_path = str(launch_row.get("instructions_file") or "").strip()
        active_attempt = ""
        if instructions_path:
            active_attempt_path = Path(ROUND.resolve_repo_path(instructions_path)).parent
            try:
                active_attempt = str(active_attempt_path.resolve().relative_to(ROUND.REPO_ROOT))
            except ValueError:
                active_attempt = os.path.relpath(str(active_attempt_path.resolve()), str(ROUND.REPO_ROOT))
        row["slot_id"] = str(selection["slot_id"])
        row["queue_state"] = "launching"
        row["status"] = "running"
        row["attempt_index"] = str(launch_row.get("attempt_index") or row.get("attempt_index") or "")
        row["lease_id"] = str(launch_row.get("lease_id") or row.get("lease_id") or "")
        row["instructions_file"] = instructions_path or row.get("instructions_file") or ""
        row["classifier_results_csv"] = str(
            launch_row.get("classifier_results_csv") or row.get("classifier_results_csv") or ""
        )
        row["results_csv"] = str(launch_row.get("results_csv") or row.get("results_csv") or "")
        if active_attempt:
            row["active_attempt"] = active_attempt
        row["collect_state"] = "pending"
        row["collect_failure_reason"] = ""
        row["ready_to_collect_at"] = ""
        row["current_attempt_mode"] = (
            str(launch_row.get("attempt_mode") or "").strip()
            or row.get("prepared_mode")
            or row.get("current_attempt_mode")
            or "fresh_full_batch"
        )
        row["tail_retry_pending"] = ""
        row["attempt_start_prefix_rows"] = str(
            launch_row.get("attempt_start_prefix_rows") or row.get("attempt_start_prefix_rows") or ""
        )
        row["segment_target_rows"] = str(launch_row.get("segment_target_rows") or row.get("segment_target_rows") or "")
        row["segment_hard_cap_rows"] = str(
            launch_row.get("segment_hard_cap_rows") or row.get("segment_hard_cap_rows") or ""
        )
        row["planned_rotate"] = ""
        row["started_at"] = row.get("started_at") or started_at
        row["round_entry_started_at"] = row.get("round_entry_started_at") or started_at
        if ROUND.parse_int(row.get("last_seen_classifier_rows"), 0) > 0 or ROUND.parse_int(row.get("last_seen_result_rows"), 0) > 0:
            row["first_row_at"] = row.get("first_row_at") or started_at
            row["last_progress_at"] = row.get("last_progress_at") or started_at
        return row

    return apply_batch_row_updates(schedule_rows, batch_files=list(by_batch), update_fn=_update)


def mark_batches_collecting(schedule_rows: list[dict[str, str]], batch_files: list[str]) -> list[dict[str, str]]:
    now_iso = ROUND.iso_now()

    def _update(row: dict[str, str]) -> dict[str, str]:
        row["queue_state"] = "collecting"
        row["collect_state"] = "running"
        row["ready_to_collect_at"] = row.get("ready_to_collect_at") or now_iso
        row["collect_failure_reason"] = ""
        return row

    return apply_batch_row_updates(schedule_rows, batch_files=batch_files, update_fn=_update)


def mark_batches_collected(schedule_rows: list[dict[str, str]], batch_files: list[str]) -> list[dict[str, str]]:
    now_iso = ROUND.iso_now()

    def _update(row: dict[str, str]) -> dict[str, str]:
        row["queue_state"] = "completed"
        row["collect_state"] = "done"
        row["collected_at"] = now_iso
        row["last_collected_attempt_index"] = str(row.get("attempt_index") or "")
        row["collect_failure_reason"] = ""
        row["tail_retry_pending"] = ""
        row["slot_id"] = ""
        return row

    return apply_batch_row_updates(schedule_rows, batch_files=batch_files, update_fn=_update)


def mark_batches_collect_failed(
    schedule_rows: list[dict[str, str]],
    *,
    batch_files: list[str],
    reason: str,
) -> list[dict[str, str]]:
    now_iso = ROUND.iso_now()

    def _update(row: dict[str, str]) -> dict[str, str]:
        row["status"] = "needs_rerun"
        row["queue_state"] = "queued"
        row["collect_state"] = "pending"
        row["collect_failure_reason"] = reason
        row["prepared_mode"] = "fresh_restart"
        row["prepared_reason"] = reason
        row["last_failure_type"] = "schema_error" if reason == "lint_failed" else reason
        row["last_rerun_reason"] = reason
        row["last_rerun_at"] = now_iso
        row["tail_retry_pending"] = ""
        row["slot_id"] = ""
        return row

    return apply_batch_row_updates(schedule_rows, batch_files=batch_files, update_fn=_update)


def mark_batches_verifier_rerun(
    schedule_rows: list[dict[str, str]],
    *,
    batch_files: list[str],
    reason: str,
) -> list[dict[str, str]]:
    now_iso = ROUND.iso_now()

    def _update(row: dict[str, str]) -> dict[str, str]:
        row["status"] = "needs_rerun"
        row["queue_state"] = "queued"
        row["collect_state"] = "pending"
        row["collect_failure_reason"] = reason
        row["prepared_mode"] = "fresh_restart"
        row["prepared_reason"] = "verifier_forced_rerun"
        row["last_failure_type"] = "verifier_forced_rerun"
        row["last_rerun_reason"] = "verifier_forced_rerun"
        row["last_rerun_at"] = now_iso
        row["tail_retry_pending"] = ""
        row["slot_id"] = ""
        return row

    return apply_batch_row_updates(schedule_rows, batch_files=batch_files, update_fn=_update)


def tail_retry_launch_allowed(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> bool:
    return not waiting_rows(schedule_rows, target_rounds) and not ready_to_collect_rows(schedule_rows, target_rounds)


def gather_launch_rows(
    target_rounds: list[int],
    *,
    schedule_rows: list[dict[str, str]],
    registry: list[dict[str, Any]],
    runs_dir: Path,
    events_log: Path,
) -> list[dict[str, str]]:
    allow_tail_retry = tail_retry_launch_allowed(schedule_rows, target_rounds)
    launch_rows: list[dict[str, str]] = []
    for round_index in target_rounds:
        round_rows = ROUND.round_rows(schedule_rows, round_index)
        if not round_rows:
            continue
        batch_scope = {
            str(row.get("batch_file") or "")
            for row in round_rows
            if (
                row_is_actively_running(row, registry)
                or (
                    effective_status(row) in {"prepared", "needs_rerun"}
                    and (allow_tail_retry or not row_tail_retry_pending(row))
                )
            )
        }
        if not batch_scope:
            continue
        launch_rows.extend(
            run_prepare_for_batches(
                round_index,
                sorted(batch_scope),
                runs_dir=runs_dir,
                events_log=events_log,
            )
        )
        schedule_rows = ROUND.read_schedule(runs_dir / ROUND.DEFAULT_SCHEDULE_CSV)
    return launch_rows


def select_launches(
    schedule_rows: list[dict[str, str]],
    *,
    target_rounds: list[int],
    launch_rows: list[dict[str, str]],
    registry: list[dict[str, Any]],
    max_workers: int,
) -> list[dict[str, Any]]:
    if not launch_rows:
        return []
    active_rows = active_running_rows(schedule_rows, target_rounds, registry)
    used_slots = {
        parse_slot_id(row.get("slot_id"))
        for row in active_rows
        if 1 <= parse_slot_id(row.get("slot_id")) <= max_workers
    }
    available_slots = [slot_id for slot_id in range(1, max_workers + 1) if slot_id not in used_slots]
    process_budget = max(0, max_workers - live_worker_process_count(registry))
    if not available_slots or process_budget <= 0:
        return []

    row_by_batch = {str(row.get("batch_file") or ""): row for row in schedule_rows}
    sorted_launch_rows = sorted(
        launch_rows,
        key=lambda row: row_sort_key(row_by_batch.get(str(row.get("batch_file") or ""), row)),
    )
    selections: list[dict[str, Any]] = []
    for launch_row, slot_id in zip(sorted_launch_rows, available_slots[:process_budget]):
        selections.append({"launch_row": launch_row, "slot_id": slot_id})
    return selections


def spawn_selected_launches(
    selections: list[dict[str, Any]],
    *,
    schedule_rows: list[dict[str, str]],
    registry: list[dict[str, Any]],
    codex_bin: str,
    events_log: Path,
) -> list[dict[str, Any]]:
    for selection in selections:
        launch_row = selection["launch_row"]
        if str(launch_row.get("launch_reason") or "") == ROUND.SPLIT_BATCH_LAUNCH_REASON:
            schedule_row = ROUND.find_schedule_row(
                schedule_rows,
                batch_file=str(launch_row.get("batch_file") or ""),
                attempt_index=ROUND.parse_int(launch_row.get("attempt_index"), 0),
            )
            if schedule_row is None:
                raise SystemExit(
                    f"Unable to resolve schedule row for split recovery: {launch_row.get('batch_file', '')}"
                )
            split_state = ROUND.initialize_split_recovery(schedule_row, events_log=events_log)
            split_state, registry = ROUND.spawn_pending_split_shards(
                schedule_row,
                split_state,
                registry=registry,
                codex_bin=codex_bin,
                events_log=events_log,
            )
            ROUND.write_json_dict(ROUND.split_state_path_for_row(schedule_row), split_state)
        else:
            registry.append(
                ROUND.spawn_worker(
                    launch_row,
                    codex_bin=codex_bin,
                    events_log=events_log,
                )
            )
    return ROUND.cleanup_registry(registry)


def queue_run_complete(schedule_rows: list[dict[str, str]], target_rounds: list[int]) -> bool:
    return not any(row_has_open_queue_work(row) for row in target_scope_rows(schedule_rows, target_rounds))


def park_tail_retry_rows(
    schedule_rows: list[dict[str, str]],
    *,
    deferred_rows: list[dict[str, str]],
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

        current_rows = min(
            ROUND.parse_int(updated.get("last_seen_classifier_rows"), 0),
            ROUND.parse_int(updated.get("last_seen_result_rows"), 0),
        )
        updated["status"] = "needs_rerun"
        updated["queue_state"] = "tail_retry_pending"
        updated["collect_state"] = "pending"
        updated["collect_failure_reason"] = ""
        updated["prepared_mode"] = "continue_from_prefix" if current_rows > 0 else "fresh_restart"
        updated["prepared_reason"] = "tail_retry_after_primary_drain"
        updated["last_failure_type"] = "long_tail_timeout"
        updated["last_rerun_reason"] = "long_tail_timeout"
        updated["last_rerun_at"] = str(deferred.get("deferred_at") or ROUND.iso_now())
        updated["completion_mode"] = ""
        updated["deferred_at"] = ""
        updated["deferred_reason"] = ""
        updated["ready_to_collect_at"] = ""
        updated["collected_at"] = ""
        updated["slot_id"] = ""
        updated["planned_rotate"] = ""
        updated["started_at"] = ""
        updated["round_entry_started_at"] = ""
        updated["first_row_at"] = ""
        updated["last_progress_at"] = ""
        updated["tail_retry_pending"] = TAIL_RETRY_PENDING_VALUE
        updated["tail_retry_count"] = str(parse_tail_retry_count(updated.get("tail_retry_count")) + 1)

        split_state_path = ROUND.split_state_path_for_row(updated)
        split_state = ROUND.load_json_dict(split_state_path)
        if ROUND.split_state_active(split_state):
            split_state["state"] = "tail_retry_pending"
            split_state["queued_at"] = updated["last_rerun_at"]
            split_state["updated_at"] = ROUND.iso_now()
            ROUND.write_json_dict(split_state_path, split_state)

        ROUND.log_event(
            events_log,
            (
                "[tail_retry:parked] "
                f"round={updated.get('round_index', '')} "
                f"batch={batch_file} "
                f"attempt={updated.get('attempt_index', '')} "
                f"tail_retry_count={updated.get('tail_retry_count', '0')} "
                f"classifier_rows={updated.get('last_seen_classifier_rows', '0')} "
                f"result_rows={updated.get('last_seen_result_rows', '0')}"
            ),
        )
        updated_rows.append(updated)
    return updated_rows


def main() -> None:
    args = parse_args()
    if args.start_round_index <= 0:
        raise SystemExit("--start-round-index must be greater than 0.")
    if args.round_count <= 0:
        raise SystemExit("--round-count must be greater than 0.")
    if args.max_workers <= 0:
        raise SystemExit("--max-workers must be greater than 0.")
    if args.poll_seconds <= 0:
        raise SystemExit("--poll-seconds must be greater than 0.")
    if args.split_batch_respawn_threshold <= 0:
        raise SystemExit("--split-batch-respawn-threshold must be greater than 0.")
    if args.split_batch_failure_threshold <= 0:
        raise SystemExit("--split-batch-failure-threshold must be greater than 0.")

    runs_dir = args.runs_dir.resolve()
    schedule_csv = ROUND.resolve_runs_path(runs_dir, args.schedule_csv, ROUND.DEFAULT_SCHEDULE_CSV)
    state_json = ROUND.resolve_runs_path(runs_dir, args.state_json, ROUND.DEFAULT_STATE_JSON)
    registry_json = ROUND.resolve_runs_path(runs_dir, args.registry_json, ROUND.DEFAULT_REGISTRY_JSON)
    events_log = ROUND.resolve_runs_path(runs_dir, args.events_log, ROUND.DEFAULT_EVENTS_LOG)
    lock_file = runs_dir / ROUND.DEFAULT_LOCK_FILE
    target_rounds = list(range(args.start_round_index, args.start_round_index + args.round_count))
    ROUND.set_supervisor_context(
        runs_dir=runs_dir,
        schedule_csv=schedule_csv,
        state_json=state_json,
        registry_json=registry_json,
        events_log=events_log,
        target_rounds=target_rounds,
    )

    args.codex_bin = ROUND.resolve_codex_bin(args.codex_bin)

    _, initial_rows = load_schedule_with_queue_columns(schedule_csv, state_hint=ROUND.load_json_dict(state_json))
    ROUND.ensure_requested_rounds_exist(initial_rows, target_rounds)
    ROUND.acquire_supervisor_lock(lock_file, runs_dir=runs_dir)

    registry = ROUND.cleanup_registry(ROUND.load_registry(registry_json))
    ROUND.save_registry(registry_json, registry)
    schedule_rows = refresh_schedule(
        schedule_csv,
        fieldnames=ROUND.load_csv_rows_with_fields(schedule_csv)[0],
        state_hint=ROUND.load_json_dict(state_json),
        registry=registry,
        max_workers=args.max_workers,
    )
    fieldnames, _ = load_schedule_with_queue_columns(schedule_csv, state_hint=ROUND.load_json_dict(state_json))

    ROUND.log_event(
        events_log,
        (
            "[queue_supervisor:start] "
            f"rounds={target_rounds[0]}-{target_rounds[-1]} "
            f"max_workers={args.max_workers} poll={args.poll_seconds}s "
            f"startup_timeout={args.startup_no_row_timeout_seconds}s "
            f"stall_timeout={args.partial_stall_timeout_seconds}s "
            f"batch_timeout={args.batch_timeout_seconds}s "
            f"split_thresholds=respawn>={args.split_batch_respawn_threshold},failures>={args.split_batch_failure_threshold}"
        ),
    )

    while True:
        registry = ROUND.cleanup_registry(ROUND.load_registry(registry_json))
        ROUND.save_registry(registry_json, registry)
        schedule_rows = refresh_schedule(
            schedule_csv,
            fieldnames=fieldnames,
            state_hint=ROUND.load_json_dict(state_json),
            registry=registry,
            max_workers=args.max_workers,
        )

        if queue_run_complete(schedule_rows, target_rounds) and not active_running_rows(schedule_rows, target_rounds, registry):
            write_state(
                state_json,
                runs_dir=runs_dir,
                target_rounds=target_rounds,
                phase="completed",
                schedule_rows=schedule_rows,
                registry=registry,
                max_workers=args.max_workers,
            )
            ROUND.log_event(events_log, f"[queue_supervisor:complete] rounds={target_rounds[0]}-{target_rounds[-1]}")
            return

        phase = "watch"

        for round_index in target_rounds:
            schedule_rows, dead_worker_changed = ROUND.mark_dead_worker_reruns(
                schedule_csv,
                schedule_rows,
                round_index=round_index,
                registry=registry,
                events_log=events_log,
            )
            if dead_worker_changed:
                phase = "watch"
        registry = ROUND.cleanup_registry(ROUND.load_registry(registry_json))
        ROUND.save_registry(registry_json, registry)
        schedule_rows = refresh_schedule(
            schedule_csv,
            fieldnames=fieldnames,
            state_hint=ROUND.load_json_dict(state_json),
            registry=registry,
            max_workers=args.max_workers,
        )

        split_changed_any = False
        for round_index in target_rounds:
            schedule_rows, registry, split_changed = ROUND.manage_split_recoveries(
                schedule_csv,
                schedule_rows,
                round_index=round_index,
                registry=registry,
                codex_bin=args.codex_bin,
                events_log=events_log,
                startup_timeout_seconds=args.startup_no_row_timeout_seconds,
                partial_stall_timeout_seconds=args.partial_stall_timeout_seconds,
            )
            split_changed_any = split_changed_any or split_changed
        if split_changed_any:
            ROUND.save_registry(registry_json, registry)
            schedule_rows = refresh_schedule(
                schedule_csv,
                fieldnames=fieldnames,
                state_hint=ROUND.load_json_dict(state_json),
                registry=registry,
                max_workers=args.max_workers,
            )
            phase = "split_recovery"

        # Reconcile completed outputs before long-tail analysis so finished batches are not
        # incorrectly deferred just because their status has not been refreshed yet.
        _ = gather_launch_rows(
            target_rounds,
            schedule_rows=schedule_rows,
            registry=registry,
            runs_dir=runs_dir,
            events_log=events_log,
        )
        schedule_rows = refresh_schedule(
            schedule_csv,
            fieldnames=fieldnames,
            state_hint=ROUND.load_json_dict(state_json),
            registry=registry,
            max_workers=args.max_workers,
        )

        deferred_any = False
        parked_tail_retry_any = False
        for round_index in target_rounds:
            deferred_batch_rows = ROUND.analyze_long_tail_deferred_rows(
                schedule_rows,
                round_index,
                timeout_seconds=args.batch_timeout_seconds,
            )
            if not deferred_batch_rows:
                continue
            deferred_any = True
            registry = ROUND.terminate_for_batch_files(
                {
                    str(row.get("batch_file") or "")
                    for row in deferred_batch_rows
                    if str(row.get("batch_file") or "").strip()
                },
                registry,
                events_log,
                reason=f"queue_round_{round_index}_long_tail_timeout",
            )
            parked_batch_files: set[str] = set()
            parked_deferred_rows = [
                row
                for row in deferred_batch_rows
                if parse_tail_retry_count(
                    (
                        ROUND.find_schedule_row(
                            schedule_rows,
                            batch_file=str(row.get("batch_file") or ""),
                            attempt_index=ROUND.parse_int(row.get("attempt_index"), 0),
                        )
                        or {}
                    ).get("tail_retry_count", "0")
                ) < DEFAULT_MAX_TAIL_RETRIES
            ]
            parked_batch_files = {str(row.get("batch_file") or "") for row in parked_deferred_rows}
            terminal_deferred_rows = [
                row
                for row in deferred_batch_rows
                if str(row.get("batch_file") or "") not in parked_batch_files
            ]
            if parked_deferred_rows:
                schedule_rows = park_tail_retry_rows(
                    schedule_rows,
                    deferred_rows=parked_deferred_rows,
                    events_log=events_log,
                )
                save_schedule(schedule_csv, fieldnames, schedule_rows)
                parked_tail_retry_any = True
            if terminal_deferred_rows:
                schedule_rows = ROUND.mark_long_tail_deferred(
                    schedule_csv,
                    schedule_rows,
                    terminal_deferred_rows,
                    schedule_fieldnames=fieldnames,
                    runs_dir=runs_dir,
                    events_log=events_log,
                )
        if deferred_any:
            ROUND.save_registry(registry_json, registry)
            schedule_rows = refresh_schedule(
                schedule_csv,
                fieldnames=fieldnames,
                state_hint=ROUND.load_json_dict(state_json),
                registry=registry,
                max_workers=args.max_workers,
            )
            phase = "tail_retry_pending" if parked_tail_retry_any else "deferred_long_tail"

        if not args.disable_split_batch_recovery:
            split_requested = False
            for round_index in target_rounds:
                split_rows = ROUND.select_split_recovery_candidates(
                    schedule_rows,
                    round_index,
                    respawn_threshold=args.split_batch_respawn_threshold,
                    failure_threshold=args.split_batch_failure_threshold,
                )
                if not split_rows:
                    continue
                split_requested = True
                registry = ROUND.terminate_for_batch_files(
                    {str(row.get("batch_file") or "") for row in split_rows},
                    registry,
                    events_log,
                    reason=f"queue_round_{round_index}_split_recovery",
                )
                schedule_rows = ROUND.mark_split_recovery_requested(
                    schedule_csv,
                    schedule_rows,
                    split_rows,
                    events_log=events_log,
                )
            if split_requested:
                ROUND.save_registry(registry_json, registry)
                schedule_rows = refresh_schedule(
                    schedule_csv,
                    fieldnames=fieldnames,
                    state_hint=ROUND.load_json_dict(state_json),
                    registry=registry,
                    max_workers=args.max_workers,
                )
                phase = "split_recovery"

        launch_rows = gather_launch_rows(
            target_rounds,
            schedule_rows=schedule_rows,
            registry=registry,
            runs_dir=runs_dir,
            events_log=events_log,
        )
        schedule_rows = refresh_schedule(
            schedule_csv,
            fieldnames=fieldnames,
            state_hint=ROUND.load_json_dict(state_json),
            registry=registry,
            max_workers=args.max_workers,
        )

        selections = select_launches(
            schedule_rows,
            target_rounds=target_rounds,
            launch_rows=launch_rows,
            registry=registry,
            max_workers=args.max_workers,
        )
        if selections:
            phase = "fill_slots"
            schedule_rows = reserve_launch_slots(schedule_rows, selections=selections)
            save_schedule(schedule_csv, fieldnames, schedule_rows)
            registry = spawn_selected_launches(
                selections,
                schedule_rows=schedule_rows,
                registry=registry,
                codex_bin=args.codex_bin,
                events_log=events_log,
            )
            ROUND.save_registry(registry_json, registry)
            batch_files_by_round: dict[int, list[str]] = {}
            for selection in selections:
                launch_row = selection["launch_row"]
                round_index = ROUND.parse_int(launch_row.get("round_index"), 0)
                batch_files_by_round.setdefault(round_index, []).append(str(launch_row.get("batch_file") or ""))
            for round_index, batch_files in sorted(batch_files_by_round.items()):
                run_mark_started_for_batches(
                    round_index,
                    batch_files,
                    runs_dir=runs_dir,
                    events_log=events_log,
                )
            for selection in selections:
                launch_row = selection["launch_row"]
                round_index = ROUND.parse_int(launch_row.get("round_index"), 0)
                ROUND.log_event(
                    events_log,
                    (
                        "[queue:launch] "
                        f"slot={selection['slot_id']} round={round_index} "
                        f"batch={launch_row.get('batch_file', '')} "
                        f"attempt={launch_row.get('attempt_index', '')}"
                    ),
                )
            schedule_rows = refresh_schedule(
                schedule_csv,
                fieldnames=fieldnames,
                state_hint=ROUND.load_json_dict(state_json),
                registry=registry,
                max_workers=args.max_workers,
            )
            write_state(
                state_json,
                runs_dir=runs_dir,
                target_rounds=target_rounds,
                phase=phase,
                schedule_rows=schedule_rows,
                registry=registry,
                max_workers=args.max_workers,
            )
            continue

        collect_rows = ready_to_collect_rows(schedule_rows, target_rounds)
        collect_row: dict[str, str] | None = None
        collect_skip_verification = False
        verifier_rerun_row: tuple[dict[str, str], str] | None = None
        for row in collect_rows:
            gate_state, gate_reason = verification_gate_state(row)
            if gate_state == "rerun_required":
                verifier_rerun_row = (row, gate_reason)
                break
            if gate_state == "ready":
                collect_row = row
                collect_skip_verification = False
                break
            if gate_state == "ready_skip_verification":
                collect_row = row
                collect_skip_verification = True
                break

        if verifier_rerun_row is not None:
            rerun_row, rerun_reason = verifier_rerun_row
            batch_file = str(rerun_row.get("batch_file") or "")
            schedule_rows = mark_batches_verifier_rerun(
                schedule_rows,
                batch_files=[batch_file],
                reason=rerun_reason,
            )
            save_schedule(schedule_csv, fieldnames, schedule_rows)
            ROUND.log_event(
                events_log,
                f"[queue:verifier_rerun] batch={batch_file} reason={rerun_reason}",
            )
            continue

        if collect_row is not None:
            batch_file = str(collect_row.get("batch_file") or "")
            ROUND.log_event(
                events_log,
                f"[queue:collect_start] batch={batch_file} attempt={collect_row.get('attempt_index', '')}",
            )
            if collect_skip_verification:
                ROUND.log_event(
                    events_log,
                    f"[queue:collect_skip_verification] batch={batch_file} reason=legacy_uninitialized_verifier",
                )
            schedule_rows = mark_batches_collecting(schedule_rows, [batch_file])
            save_schedule(schedule_csv, fieldnames, schedule_rows)
            write_state(
                state_json,
                runs_dir=runs_dir,
                target_rounds=target_rounds,
                phase="collect",
                schedule_rows=schedule_rows,
                registry=registry,
                max_workers=args.max_workers,
            )
            lint_ok = run_lint_for_batches([batch_file], runs_dir=runs_dir, events_log=events_log)
            registry = ROUND.cleanup_registry(ROUND.load_registry(registry_json))
            ROUND.save_registry(registry_json, registry)
            schedule_rows = refresh_schedule(
                schedule_csv,
                fieldnames=fieldnames,
                state_hint=ROUND.load_json_dict(state_json),
                registry=registry,
                max_workers=args.max_workers,
            )
            if not lint_ok:
                quarantine_attempt_outputs(collect_row, reason="lint_failed", events_log=events_log)
                schedule_rows = mark_batches_collect_failed(
                    schedule_rows,
                    batch_files=[batch_file],
                    reason="lint_failed",
                )
                save_schedule(schedule_csv, fieldnames, schedule_rows)
                ROUND.log_event(events_log, f"[queue:collect_lint_failed] batch={batch_file}")
                continue

            collect_ok = run_collect_for_batches(
                [batch_file],
                runs_dir=runs_dir,
                events_log=events_log,
                skip_verification=collect_skip_verification,
            )
            registry = ROUND.cleanup_registry(ROUND.load_registry(registry_json))
            ROUND.save_registry(registry_json, registry)
            schedule_rows = refresh_schedule(
                schedule_csv,
                fieldnames=fieldnames,
                state_hint=ROUND.load_json_dict(state_json),
                registry=registry,
                max_workers=args.max_workers,
            )
            if not collect_ok:
                raise SystemExit(
                    f"Batch collect failed for {batch_file}. Global final outputs were not safely synchronized."
                )
            schedule_rows = mark_batches_collected(schedule_rows, [batch_file])
            save_schedule(schedule_csv, fieldnames, schedule_rows)
            ROUND.log_event(events_log, f"[queue:collect_complete] batch={batch_file}")
            continue

        write_state(
            state_json,
            runs_dir=runs_dir,
            target_rounds=target_rounds,
            phase=phase,
            schedule_rows=schedule_rows,
            registry=registry,
            max_workers=args.max_workers,
        )
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        ROUND.log_supervisor_terminal_failure(exc)
        raise
