#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable

from part6_schema import ALLOWED_VERDICTS, ALLOWED_VERIFICATION_ACTIONS


def verification_summary_is_uninitialized(summary_path: Path) -> bool:
    try:
        text = summary_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return "- status: pending" in text


def verification_gate_state(
    row: dict[str, str],
    *,
    resolve_repo_path: Callable[[str], Path],
    load_jsonl_tasks: Callable[[Path], list[dict[str, Any]]],
) -> tuple[str, str]:
    report_raw = str(row.get("verification_report_csv") or "").strip()
    summary_raw = str(row.get("verification_summary_md") or "").strip()
    if not report_raw or not summary_raw:
        return "pending", "missing_verification_artifacts"
    report_path = resolve_repo_path(report_raw)
    summary_path = resolve_repo_path(summary_raw)
    tasks_path_raw = str(row.get("tasks_file") or "").strip()
    if not report_path.exists() or not summary_path.exists() or not tasks_path_raw:
        return "pending", "missing_verification_artifacts"

    expected_task_indexes = {
        str(task.get("task_index", "")).strip()
        for task in load_jsonl_tasks(resolve_repo_path(tasks_path_raw))
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
                if verdict not in ALLOWED_VERDICTS:
                    return "pending", "invalid_verifier_verdict"
                if recommended_action not in ALLOWED_VERIFICATION_ACTIONS:
                    return "pending", "invalid_verifier_action"
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
        if not saw_any_report_rows and not seen_task_indexes and verification_summary_is_uninitialized(summary_path):
            return "pending", "required_verifier_not_started"
        return "pending", "missing_verifier_rows"
    return "ready", ""


def round_verification_gate_state(
    rows: list[dict[str, str]],
    *,
    resolve_repo_path: Callable[[str], Path],
    load_jsonl_tasks: Callable[[Path], list[dict[str, Any]]],
) -> dict[str, Any]:
    rerun_batch_files: list[str] = []
    pending_reasons: list[str] = []
    saw_ready_rows = False

    for row in rows:
        batch_file = str(row.get("batch_file") or "").strip()
        gate_state, gate_reason = verification_gate_state(
            row,
            resolve_repo_path=resolve_repo_path,
            load_jsonl_tasks=load_jsonl_tasks,
        )
        if gate_state == "rerun_required":
            if batch_file and batch_file not in rerun_batch_files:
                rerun_batch_files.append(batch_file)
            continue
        if gate_state == "pending" and gate_reason:
            pending_reasons.append(gate_reason)
            continue
        if gate_state == "ready":
            saw_ready_rows = True

    if rerun_batch_files:
        return {
            "state": "rerun_required",
            "reason": "verifier_forced_rerun",
            "batch_files": rerun_batch_files,
        }
    if pending_reasons:
        return {
            "state": "pending",
            "reason": pending_reasons[0],
            "batch_files": [],
        }
    if saw_ready_rows:
        return {
            "state": "ready",
            "reason": "",
            "batch_files": [],
        }
    return {
        "state": "pending",
        "reason": "missing_verifier_rows",
        "batch_files": [],
    }
