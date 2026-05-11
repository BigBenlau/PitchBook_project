#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from part4_schedule_io import write_schedule_csv

SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent
RUNTIME_DIR = PART4_DIR / "runtime"
DEFAULT_RUNS_DIR = PART4_DIR / "agent_runs" / "token_company_parallel"
DEFAULT_POLICY_PATH = RUNTIME_DIR / "policy.json"
WORKER_BASE_TEMPLATE_PATH = RUNTIME_DIR / "worker_base_template.md"

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

RUNTIME_DEFAULTS = {
    "base_instructions_file": "",
    "attempts_dir": "",
    "active_attempt": "",
    "attempt_index": "1",
    "attempt_metadata_file": "",
    "current_attempt_mode": "",
    "prepared_mode": "",
    "prepared_reason": "",
    "last_failure_type": "",
    "failure_counts_json": "",
    "consecutive_no_progress_attempts": "0",
    "respawn_count": "0",
    "last_rerun_reason": "",
    "last_rerun_at": "",
    "started_at": "",
    "round_entry_started_at": "",
    "first_row_at": "",
    "last_progress_at": "",
    "last_seen_classifier_rows": "0",
    "last_seen_result_rows": "0",
    "active_lease_file": "",
    "lease_id": "",
    "attempt_start_prefix_rows": "0",
    "planned_rotate": "",
    "segment_target_rows": "0",
    "segment_hard_cap_rows": "0",
    "completion_mode": "",
    "deferred_at": "",
    "deferred_reason": "",
    "startup_failure_count": "0",
    "stall_failure_count": "0",
    "escalation_level": "0",
    "status": "prepared",
}

FULL_BATCH_ATTEMPT_MODES = {"fresh_full_batch", "fresh_restart", "continue_from_prefix"}
SEGMENT_RECOVERY_ATTEMPT_MODES = {"narrowed_suffix_only"}

LAUNCH_QUEUE_COLUMNS = [
    "round_index",
    "worker_slot",
    "batch_file",
    "attempt_index",
    "lease_id",
    "attempt_mode",
    "model",
    "reasoning_effort",
    "task_count",
    "start_task_index",
    "start_company",
    "existing_prefix_rows",
    "attempt_start_prefix_rows",
    "segment_target_rows",
    "segment_hard_cap_rows",
    "instructions_file",
    "classifier_results_csv",
    "results_csv",
    "launch_reason",
]

ACTION_COLUMNS = [
    "round_index",
    "worker_slot",
    "batch_file",
    "attempt_index",
    "lease_id",
    "action",
    "recommended_mode",
    "model",
    "reasoning_effort",
    "reason",
    "classifier_rows",
    "result_rows",
    "prefix_rows",
    "attempt_rows_added",
]

WRAPPER_BEGIN = "--- BEGIN BASE INSTRUCTIONS ---"
WRAPPER_END = "--- END BASE INSTRUCTIONS ---"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage part4 round runtime: launch queues, attempt isolation, and policy-driven recovery.",
    )
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--schedule-csv", type=Path, default=None)
    parser.add_argument("--policy-json", type=Path, default=DEFAULT_POLICY_PATH)
    parser.add_argument("--round-index", type=int, required=True)
    parser.add_argument(
        "--batch-file",
        action="append",
        default=[],
        help=(
            "Optional batch scope within the selected round. Repeatable. Accepts the schedule "
            "batch_file value, an absolute path, or a basename like batch_0226.jsonl."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-launches", action="store_true")
    mode.add_argument("--mark-round-started", action="store_true")
    mode.add_argument("--watch-round", action="store_true")
    parser.add_argument("--startup-no-row-timeout-seconds", type=int, default=0)
    parser.add_argument("--partial-stall-timeout-seconds", type=int, default=0)
    return parser.parse_args()


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def resolve_batch_scope(
    raw_batch_values: list[str],
    schedule_rows: list[dict[str, str]],
    *,
    round_index: int,
) -> set[str]:
    requested = [str(value or "").strip() for value in raw_batch_values if str(value or "").strip()]
    if not requested:
        return set()

    candidates: list[tuple[str, Path]] = []
    for row in schedule_rows:
        if parse_optional_int(row.get("round_index"), 0) != round_index:
            continue
        batch_file = str(row.get("batch_file") or "").strip()
        if not batch_file:
            continue
        candidates.append((batch_file, resolve_path(batch_file)))

    resolved_scope: set[str] = set()
    missing: list[str] = []
    for raw in requested:
        raw_path = Path(raw)
        raw_name = raw_path.name
        matched = False
        for batch_file, batch_path in candidates:
            if raw == batch_file or raw_name == Path(batch_file).name:
                resolved_scope.add(batch_file)
                matched = True
                break
            try:
                requested_path = raw_path.resolve() if raw_path.is_absolute() else (REPO_ROOT / raw_path).resolve()
            except OSError:
                requested_path = None
            if requested_path is not None and requested_path == batch_path:
                resolved_scope.add(batch_file)
                matched = True
                break
        if not matched:
            missing.append(raw)

    if missing:
        available = ", ".join(Path(batch_file).name for batch_file, _ in candidates) or "none"
        raise SystemExit(
            "Requested --batch-file values are not present in the selected round: "
            f"{', '.join(missing)}. Available in round {round_index}: {available}"
        )
    return resolved_scope


def attempt_index_from_dir(path: Path) -> int:
    match = re.match(r"attempt_(\d+)$", path.name)
    if not match:
        return 0
    return parse_optional_int(match.group(1), 0)


def attempt_metadata_path(attempt_dir: Path) -> Path:
    return attempt_dir / "attempt_metadata.json"


def active_lease_path_for_row(row: dict[str, str]) -> Path:
    raw = (row.get("active_lease_file") or "").strip()
    if raw:
        return resolve_path(raw)
    return batch_root(row) / "active_attempt_lease.json"


def load_attempt_metadata(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def make_lease_id(row: dict[str, str], attempt_index: int) -> str:
    timestamp = now_utc().strftime("%Y%m%dT%H%M%S%fZ")
    worker_slot = parse_optional_int(row.get("worker_slot"), 0)
    return f"slot{worker_slot:02d}-attempt{attempt_index:04d}-{timestamp}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return now_utc().isoformat()


def parse_optional_int(value: Any, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def parse_iso(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def load_policy(path: Path) -> dict[str, Any]:
    policy = load_json(path)
    policy.setdefault("status_model", {})
    policy.setdefault("failure_types", {})
    policy.setdefault("failure_count_defaults", {})
    policy.setdefault("escalation_rules", [])
    policy.setdefault("timeouts", {})
    policy.setdefault("segment_policy", {})
    return policy


def segment_policy_values(policy: dict[str, Any]) -> dict[str, int]:
    raw = policy.get("segment_policy") or {}
    target_rows = parse_optional_int(raw.get("target_rows_per_attempt"), 12)
    hard_cap_rows = parse_optional_int(raw.get("hard_cap_rows_per_attempt"), 15)
    rotate_idle_seconds = parse_optional_int(raw.get("planned_rotate_idle_seconds"), 45)
    if target_rows <= 0:
        target_rows = 12
    if hard_cap_rows < target_rows:
        hard_cap_rows = target_rows
    if rotate_idle_seconds < 0:
        rotate_idle_seconds = 45
    return {
        "target_rows_per_attempt": target_rows,
        "hard_cap_rows_per_attempt": hard_cap_rows,
        "planned_rotate_idle_seconds": rotate_idle_seconds,
    }


def attempt_uses_segment_contract(attempt_mode: str) -> bool:
    return (attempt_mode or "").strip() in SEGMENT_RECOVERY_ATTEMPT_MODES


def requires_search_guarantee(row: dict[str, str]) -> bool:
    markers = [
        str(row.get("batch_file") or ""),
        str(row.get("run_dir") or ""),
        str(row.get("tasks_file") or ""),
    ]
    return any("rerun_manual_fallbacks" in marker for marker in markers)


def canonical_failure_reason_tokens(reason: str) -> list[str]:
    alias_map = {
        "severe_schema_error": "schema_error",
        "schema_error": "schema_error",
        "search_tier_too_conservative": "verifier_forced_rerun",
        "search_should_not_have_been_skipped": "verifier_forced_rerun",
        "rerun_company": "verifier_forced_rerun",
        "rerun_batch": "verifier_forced_rerun",
    }
    tokens = [token.strip() for token in str(reason or "").split("|") if token.strip()]
    if not tokens:
        return []
    canonical: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        mapped = alias_map.get(token, token)
        if mapped and mapped not in seen:
            canonical.append(mapped)
            seen.add(mapped)
    return canonical


def is_qc_forced_rerun(row: dict[str, str]) -> bool:
    reasons = [
        str(row.get("last_failure_type") or "").strip(),
        str(row.get("prepared_reason") or "").strip(),
        str(row.get("last_rerun_reason") or "").strip(),
    ]
    for reason in reasons:
        tokens = canonical_failure_reason_tokens(reason)
        if any(token in {"schema_error", "verifier_forced_rerun"} for token in tokens):
            return True
    return False


def default_failure_counts(policy: dict[str, Any]) -> dict[str, int]:
    raw = policy.get("failure_count_defaults") or {}
    return {key: int(value) for key, value in raw.items()}


def parse_failure_counts(value: str, policy: dict[str, Any]) -> dict[str, int]:
    counts = default_failure_counts(policy)
    raw = (value or "").strip()
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            for key, raw_value in parsed.items():
                counts[str(key)] = parse_optional_int(raw_value, counts.get(str(key), 0))
    return counts


def encode_failure_counts(counts: dict[str, int]) -> str:
    ordered = {key: int(counts[key]) for key in sorted(counts)}
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))


def normalize_status(status: str, started_at: str) -> str:
    raw = (status or "").strip()
    if raw in {"prepared", "running", "needs_rerun", "completed", "deferred_long_tail"}:
        return raw
    if raw in {"pending", "pending_launch", ""}:
        return "prepared"
    if raw == "rerun_batch":
        return "needs_rerun"
    if raw == "partial":
        return "running" if (started_at or "").strip() else "prepared"
    return "prepared"


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows = [{field: row.get(field, "") for field in fieldnames} for row in reader]
    return fieldnames, rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_schedule(path: Path, policy: dict[str, Any]) -> tuple[list[str], list[dict[str, str]]]:
    header, rows = load_csv(path)
    if not header:
        raise SystemExit(f"Schedule CSV has no header: {path}")
    required_order = list(header)
    for key in RUNTIME_DEFAULTS:
        if key not in required_order:
            required_order.append(key)
    for row in rows:
        for key, value in RUNTIME_DEFAULTS.items():
            row.setdefault(key, value)
        row["status"] = normalize_status(row.get("status", ""), row.get("started_at", ""))
        row["failure_counts_json"] = encode_failure_counts(
            parse_failure_counts(row.get("failure_counts_json", ""), policy)
        )
    return required_order, rows


def write_schedule(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    normalized_rows = []
    for row in rows:
        normalized = dict(row)
        for key, value in RUNTIME_DEFAULTS.items():
            normalized.setdefault(key, value)
        normalized_rows.append({field: normalized.get(field, "") for field in fieldnames})
    write_schedule_csv(path, normalized_rows, fieldnames=fieldnames)


def load_tasks(path: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def count_rows(path: Path, expected_header: list[str]) -> tuple[int, bool, list[dict[str, str]]]:
    if not path.exists() or not path.is_file():
        return 0, False, []
    header, rows = load_csv(path)
    return len(rows), header == expected_header, rows


def batch_root(row: dict[str, str]) -> Path:
    return resolve_path(row["run_dir"])


def attempts_dir_for_row(row: dict[str, str]) -> Path:
    raw = (row.get("attempts_dir") or "").strip()
    if raw:
        return resolve_path(raw)
    return batch_root(row) / "attempts"


def active_attempt_dir_for_row(row: dict[str, str]) -> Path:
    raw = (row.get("active_attempt") or "").strip()
    if raw:
        return resolve_path(raw)
    return attempts_dir_for_row(row) / f"attempt_{parse_optional_int(row.get('attempt_index'), 1):04d}"


def base_instructions_path_for_row(row: dict[str, str]) -> Path:
    raw = (row.get("base_instructions_file") or "").strip()
    if raw:
        return resolve_path(raw)
    return batch_root(row) / "base_worker_instructions.md"


def attempt_paths_for_row(row: dict[str, str]) -> list[Path]:
    attempts_dir = attempts_dir_for_row(row)
    if not attempts_dir.exists() or not attempts_dir.is_dir():
        return []
    return sorted(
        [path for path in attempts_dir.iterdir() if path.is_dir() and re.match(r"attempt_\d+$", path.name)],
        key=attempt_index_from_dir,
    )


def inspect_attempt_dir(
    attempt_dir: Path,
    tasks: list[dict[str, Any]],
    expected_rows: int,
) -> dict[str, Any]:
    classifier_path = attempt_dir / "classifier_results.csv"
    results_path = attempt_dir / "results.csv"
    instructions_path = attempt_dir / "worker_instructions.md"
    metadata_path = attempt_metadata_path(attempt_dir)
    metadata = load_attempt_metadata(metadata_path)
    classifier_rows, classifier_header_ok, classifier_data = count_rows(classifier_path, CLASSIFIER_CSV_COLUMNS)
    result_rows, results_header_ok, result_data = count_rows(results_path, RESULT_CSV_COLUMNS)
    last_activity = 0.0
    for path in [classifier_path, results_path, instructions_path, metadata_path]:
        if path.exists():
            try:
                last_activity = max(last_activity, path.stat().st_mtime)
            except OSError:
                pass

    prefix_len = 0
    compare_count = min(len(tasks), len(classifier_data), len(result_data))
    prefix_valid = classifier_header_ok and results_header_ok
    for index in range(compare_count):
        expected_task_index = str(tasks[index].get("task_index", ""))
        if classifier_data[index].get("task_index", "") != expected_task_index:
            prefix_valid = False
            break
        if result_data[index].get("task_index", "") != expected_task_index:
            prefix_valid = False
            break
        prefix_len += 1
    if compare_count < max(classifier_rows, result_rows):
        prefix_valid = False

    if prefix_valid and classifier_rows == expected_rows and result_rows == expected_rows:
        state = "completed"
    elif classifier_rows == 0 and result_rows == 0 and classifier_header_ok and results_header_ok:
        state = "header_only"
    elif prefix_valid and prefix_len > 0:
        state = "partial_prefix"
    else:
        state = "partial_misaligned"

    return {
        "attempt_dir": attempt_dir,
        "attempt_index": attempt_index_from_dir(attempt_dir),
        "attempt_metadata_file": metadata_path,
        "metadata": metadata,
        "classifier_path": classifier_path,
        "results_path": results_path,
        "instructions_path": instructions_path,
        "classifier_rows": classifier_rows,
        "result_rows": result_rows,
        "classifier_header_ok": classifier_header_ok,
        "results_header_ok": results_header_ok,
        "classifier_data": classifier_data,
        "result_data": result_data,
        "prefix_len": prefix_len,
        "prefix_valid": prefix_valid,
        "state": state,
        "last_activity": last_activity,
    }


def attempt_candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, int, float, int]:
    state_rank = {
        "completed": 4,
        "partial_prefix": 3,
        "header_only": 1,
        "partial_misaligned": 0,
    }.get(str(candidate.get("state", "")), 0)
    return (
        state_rank,
        parse_optional_int(candidate.get("prefix_len"), 0),
        min(
            parse_optional_int(candidate.get("classifier_rows"), 0),
            parse_optional_int(candidate.get("result_rows"), 0),
        ),
        float(candidate.get("last_activity") or 0.0),
        parse_optional_int(candidate.get("attempt_index"), 0),
    )


def update_batch_lease_file(
    row: dict[str, str],
    attempt_dir: Path,
    lease_id: str,
    attempt_index: int,
    attempt_start_prefix_rows: int,
    segment_policy: dict[str, int],
) -> Path:
    lease_path = active_lease_path_for_row(row)
    write_json(
        lease_path,
        {
            "lease_id": lease_id,
            "attempt_index": attempt_index,
            "active_attempt": str(attempt_dir),
            "attempt_start_prefix_rows": attempt_start_prefix_rows,
            "segment_target_rows": segment_policy["target_rows_per_attempt"],
            "segment_hard_cap_rows": segment_policy["hard_cap_rows_per_attempt"],
            "updated_at": iso_now(),
        },
    )
    return lease_path


def sync_attempt_metadata(
    row: dict[str, str],
    attempt_dir: Path,
    *,
    lease_id: str,
    attempt_start_prefix_rows: int,
    attempt_mode: str,
    segment_policy: dict[str, int],
) -> Path:
    metadata_path = attempt_metadata_path(attempt_dir)
    existing = load_attempt_metadata(metadata_path)
    payload = {
        "attempt_index": attempt_index_from_dir(attempt_dir),
        "attempt_mode": attempt_mode,
        "lease_id": lease_id,
        "attempt_start_prefix_rows": attempt_start_prefix_rows,
        "segment_target_rows": segment_policy["target_rows_per_attempt"],
        "segment_hard_cap_rows": segment_policy["hard_cap_rows_per_attempt"],
        "updated_at": iso_now(),
    }
    payload.update({key: value for key, value in existing.items() if key not in payload})
    write_json(metadata_path, payload)
    return metadata_path


def reconcile_active_attempt(row: dict[str, str], policy: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    updated = dict(row)
    tasks = load_tasks(resolve_path(updated["tasks_file"]))
    expected_rows = parse_optional_int(updated.get("task_count"), 0)
    candidates = [inspect_attempt_dir(path, tasks, expected_rows) for path in attempt_paths_for_row(updated)]
    if not candidates:
        inspection = inspect_row(updated)
        return updated, inspection

    best = max(candidates, key=attempt_candidate_sort_key)
    current_attempt_dir = active_attempt_dir_for_row(updated).resolve()
    current_candidate = next(
        (candidate for candidate in candidates if Path(candidate["attempt_dir"]).resolve() == current_attempt_dir),
        None,
    )
    if current_candidate is not None:
        current_metadata = current_candidate.get("metadata") or {}
        current_mode = str(
            current_metadata.get("attempt_mode")
            or updated.get("current_attempt_mode")
            or updated.get("prepared_mode")
            or "fresh_full_batch"
        )
        current_has_progress = min(
            parse_optional_int(current_candidate.get("classifier_rows"), 0),
            parse_optional_int(current_candidate.get("result_rows"), 0),
        ) > 0
        if current_mode == "fresh_restart":
            best = current_candidate
        elif str(best.get("state", "")) != "completed":
            if current_mode in FULL_BATCH_ATTEMPT_MODES:
                best = current_candidate
            elif current_has_progress and parse_optional_int(current_candidate.get("prefix_len"), 0) >= parse_optional_int(best.get("prefix_len"), 0):
                best = current_candidate
    metadata = best.get("metadata") or {}
    attempt_dir = Path(best["attempt_dir"]).resolve()
    instructions_path = Path(best["instructions_path"]).resolve()
    metadata_path = Path(best["attempt_metadata_file"]).resolve()
    attempt_index = parse_optional_int(metadata.get("attempt_index"), parse_optional_int(best.get("attempt_index"), 0))
    lease_id = str(metadata.get("lease_id") or updated.get("lease_id") or make_lease_id(updated, attempt_index or 1))
    attempt_start_prefix_rows = parse_optional_int(
        metadata.get("attempt_start_prefix_rows"),
        parse_optional_int(updated.get("attempt_start_prefix_rows"), 0),
    )
    resolved_attempt_mode = str(
        metadata.get("attempt_mode")
        or updated.get("current_attempt_mode")
        or updated.get("prepared_mode")
        or ("continue_from_prefix" if attempt_start_prefix_rows > 0 else "fresh_full_batch")
    )
    segment_values = segment_policy_values(policy)
    metadata_path = sync_attempt_metadata(
        updated,
        attempt_dir,
        lease_id=lease_id,
        attempt_start_prefix_rows=attempt_start_prefix_rows,
        attempt_mode=resolved_attempt_mode,
        segment_policy=segment_values,
    )
    lease_path = update_batch_lease_file(
        updated,
        attempt_dir,
        lease_id,
        attempt_index or parse_optional_int(best.get("attempt_index"), 0),
        attempt_start_prefix_rows,
        segment_values,
    )

    updated["attempts_dir"] = relative_path(attempts_dir_for_row(updated))
    updated["active_attempt"] = relative_path(attempt_dir)
    updated["attempt_index"] = str(attempt_index or parse_optional_int(best.get("attempt_index"), 1))
    updated["attempt_metadata_file"] = relative_path(metadata_path)
    updated["classifier_results_csv"] = relative_path(Path(best["classifier_path"]).resolve())
    updated["results_csv"] = relative_path(Path(best["results_path"]).resolve())
    updated["instructions_file"] = relative_path(instructions_path)
    updated["active_lease_file"] = relative_path(lease_path)
    updated["lease_id"] = lease_id
    updated["current_attempt_mode"] = resolved_attempt_mode
    updated["attempt_start_prefix_rows"] = str(attempt_start_prefix_rows)
    updated["segment_target_rows"] = str(segment_values["target_rows_per_attempt"])
    updated["segment_hard_cap_rows"] = str(segment_values["hard_cap_rows_per_attempt"])

    inspection = inspect_row(updated)
    return updated, inspection


def inspect_row(row: dict[str, str]) -> dict[str, Any]:
    expected_rows = parse_optional_int(row.get("task_count"), 0)
    classifier_path = resolve_path(row["classifier_results_csv"])
    results_path = resolve_path(row["results_csv"])
    classifier_rows, classifier_header_ok, classifier_data = count_rows(classifier_path, CLASSIFIER_CSV_COLUMNS)
    result_rows, results_header_ok, result_data = count_rows(results_path, RESULT_CSV_COLUMNS)
    last_activity = 0.0
    for path in [classifier_path, results_path]:
        if path.exists():
            try:
                last_activity = max(last_activity, path.stat().st_mtime)
            except OSError:
                pass

    tasks = load_tasks(resolve_path(row["tasks_file"]))
    prefix_len = 0
    compare_count = min(len(tasks), len(classifier_data), len(result_data))
    prefix_valid = True
    for index in range(compare_count):
        expected_task_index = str(tasks[index].get("task_index", ""))
        if classifier_data[index].get("task_index", "") != expected_task_index:
            prefix_valid = False
            break
        if result_data[index].get("task_index", "") != expected_task_index:
            prefix_valid = False
            break
        prefix_len += 1
    if compare_count < max(classifier_rows, result_rows):
        prefix_valid = False

    if classifier_header_ok and results_header_ok and classifier_rows == expected_rows and result_rows == expected_rows:
        state = "completed"
    elif classifier_rows == 0 and result_rows == 0:
        state = "header_only"
    elif prefix_valid and prefix_len > 0:
        state = "partial_prefix"
    else:
        state = "partial_misaligned"

    return {
        "expected_rows": expected_rows,
        "classifier_rows": classifier_rows,
        "result_rows": result_rows,
        "classifier_header_ok": classifier_header_ok,
        "results_header_ok": results_header_ok,
        "classifier_data": classifier_data,
        "result_data": result_data,
        "prefix_len": prefix_len,
        "prefix_valid": prefix_valid,
        "state": state,
        "last_activity": last_activity,
        "tasks": tasks,
        "classifier_path": classifier_path,
        "results_path": results_path,
    }


def load_worker_base_template() -> str:
    return WORKER_BASE_TEMPLATE_PATH.read_text(encoding="utf-8")


def render_worker_base_instructions(row: dict[str, str], tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        raise SystemExit(f"Task file has no rows for {row.get('batch_file', '')}")
    first = tasks[0]
    last = tasks[-1]
    batch_file = resolve_path(row["batch_file"])
    run_dir = resolve_path(row["run_dir"])
    mapping = {
        "WORKER_SLOT": str(row.get("worker_slot", "")),
        "ROUND_INDEX": str(row.get("round_index", "")),
        "RUN_DIR": str(run_dir),
        "RUNTIME_ARCHITECTURE": str(RUNTIME_DIR / "ARCHITECTURE.md"),
        "RUNTIME_POLICY": str(RUNTIME_DIR / "policy.json"),
        "PLAN_MD": str(PART4_DIR / "Plan.md"),
        "BATCH_FILE": str(batch_file),
        "TASKS_FILE": str(resolve_path(row["tasks_file"])),
        "PROMPT_TEMPLATE": str(PART4_DIR / "agent_prompt_template.md"),
        "BATCH_FILE_NAME": batch_file.name,
        "TASK_COUNT": str(len(tasks)),
        "FIRST_TASK_INDEX": str(first.get("task_index", "")),
        "FIRST_COMPANY": str(first.get("company_name", "")),
        "LAST_TASK_INDEX": str(last.get("task_index", "")),
        "LAST_COMPANY": str(last.get("company_name", "")),
        "CLASSIFIER_CSV_HEADER": ",".join(CLASSIFIER_CSV_COLUMNS),
        "RESULT_CSV_HEADER": ",".join(RESULT_CSV_COLUMNS),
    }
    rendered = load_worker_base_template()
    for key, value in mapping.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    if requires_search_guarantee(row):
        rendered = (
            f"{rendered.rstrip()}\n\n"
            "Search-guarantee override for previously manual-fallback batches:\n"
            "- This rerun window exists to guarantee actual search coverage. Do not use `search_tier = skip_candidate` in this rerun batch.\n"
            "- Every token in this batch must receive at least `light` search, so `entity_search_required` must be `yes` for every token.\n"
            "- A no-entity conclusion is allowed only after real search using current official/exact-match sources, with non-empty `evidence_urls` and `evidence_source_types`.\n"
            "- Do not close a row as no-entity only from token-type heuristics; perform the bounded or full search first, then conclude `mapped_entity_name = []` if appropriate.\n"
        )
    return rendered


def ensure_base_instructions(base_instructions: Path, row: dict[str, str], tasks: list[dict[str, Any]]) -> str:
    rendered = render_worker_base_instructions(row, tasks)
    base_instructions.parent.mkdir(parents=True, exist_ok=True)
    current = base_instructions.read_text(encoding="utf-8") if base_instructions.exists() else ""
    if current != rendered:
        base_instructions.write_text(rendered, encoding="utf-8")
    return rendered


def write_header(path: Path, columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(columns)


def copy_prefix_rows(src: Path, dst: Path, columns: list[str], prefix_len: int) -> None:
    header, rows = load_csv(src)
    selected = rows[:prefix_len]
    if header != columns:
        write_header(dst, columns)
        return
    write_csv(dst, columns, [{column: row.get(column, "") for column in columns} for row in selected])


def render_attempt_instruction(
    *,
    base_instruction_text: str,
    row: dict[str, str],
    attempt_dir: Path,
    attempt_mode: str,
    prefix_len: int,
    next_task_index: str,
    next_company: str,
    lease_id: str,
    active_lease_file: Path,
    segment_target_rows: int,
    segment_hard_cap_rows: int,
    segment_end_task_index: str,
    segment_end_company: str,
) -> str:
    uses_segment_contract = attempt_uses_segment_contract(attempt_mode)
    if prefix_len > 0:
        prefix_note = (
            f"- This attempt already contains a preserved prefix of {prefix_len} completed rows.\n"
            f"- Continue from task_index {next_task_index} ({next_company}) onward.\n"
            "- Do not duplicate or rewrite the preserved prefix rows. Append only the remaining rows in order.\n"
        )
        startup_priority = (
            f"- Startup priority: complete task_index {next_task_index} ({next_company}) first and append both CSV rows before any broad historical lookup or multi-company search fan-out.\n"
        )
    else:
        prefix_note = "- Start from the first task and write rows in order.\n"
        startup_priority = (
            f"- Startup priority: complete task_index {next_task_index} ({next_company}) first and append both CSV rows before any broad historical lookup or multi-company search fan-out.\n"
        )
    if uses_segment_contract:
        ownership_note = (
            f"- This is a narrowed recovery segment, not a normal full-batch attempt.\n"
            f"- attempt_start_prefix_rows: {prefix_len}\n"
            f"- required lease_id: {lease_id}\n"
            f"- active lease file: {active_lease_file}\n"
            f"- preferred handoff after about {segment_target_rows} new rows in this attempt.\n"
            f"- hard cap for new rows in this attempt: {segment_hard_cap_rows}.\n"
            f"- If you reach the hard cap before the batch is complete, stop and hand off after finishing the current token's writes.\n"
            f"- The intended recovery segment end is task_index {segment_end_task_index} ({segment_end_company}) unless the batch completes earlier.\n"
            "- Before starting each new token, re-read the active lease file. If its `lease_id` no longer matches this wrapper, stop instead of writing more rows.\n"
        )
    elif attempt_mode == "continue_from_prefix":
        ownership_note = (
            f"- This is a recovery attempt with a preserved prefix of {prefix_len} rows.\n"
            f"- required lease_id: {lease_id}\n"
            f"- active lease file: {active_lease_file}\n"
            "- Own the remaining suffix in this single fresh worker and continue until the batch is complete or an explicit blocker is reached.\n"
            "- Do not proactively hand off after an arbitrary row cap in this mode.\n"
            "- Do not poll the lease file before every company in this normal recovery mode; the main agent should terminate stale workers directly when replacing them.\n"
        )
    else:
        ownership_note = (
            "- This is the normal full-batch attempt.\n"
            f"- required lease_id: {lease_id}\n"
            f"- active lease file: {active_lease_file}\n"
            "- Own the entire batch in this single fresh worker and continue until the batch is complete or an explicit blocker is reached.\n"
            "- Do not proactively segment or hand off mid-batch in this mode.\n"
            "- Do not poll the lease file before every company in this normal full-batch mode; the main agent should terminate stale workers directly when replacing them.\n"
        )

    return (
        "# Attempt Runtime Wrapper\n\n"
        f"- attempt_mode: {attempt_mode}\n"
        f"- attempt_dir: {attempt_dir}\n"
        f"- authoritative write scope: {attempt_dir}\n"
        f"- authoritative classifier CSV: {attempt_dir / 'classifier_results.csv'}\n"
        f"- authoritative results CSV: {attempt_dir / 'results.csv'}\n"
        f"- authoritative tasks file: {resolve_path(row['tasks_file'])}\n"
        "- Ignore older attempt directories and older CSV locations.\n"
        "- Interpret any bare `classifier_results.csv` or `results.csv` references in the base instructions as the authoritative attempt CSVs listed above.\n"
        f"{prefix_note}"
        f"{startup_priority}"
        f"{ownership_note}"
        "- Write incrementally. Append rows as soon as each token is completed.\n"
        "- Before the first completed token is written, do not scan `manifest.csv`, prior `verification_findings.csv`, prior final outputs, or unrelated batch directories.\n"
        "- Before 2 completed tokens are written, keep auxiliary lookups narrowly scoped to the current token unless a specific ambiguity requires more.\n"
        "- The harness watches startup no-row and partial-stall conditions. Lack of row growth may cause this attempt to be terminated.\n\n"
        f"{WRAPPER_BEGIN}\n\n"
        f"{base_instruction_text.rstrip()}\n\n"
        f"{WRAPPER_END}\n"
    )


def upgrade_row_to_attempt_architecture(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    segment_values = segment_policy_values(load_policy(DEFAULT_POLICY_PATH))
    attempts_dir = attempts_dir_for_row(updated)
    attempts_dir.mkdir(parents=True, exist_ok=True)

    active_attempt = active_attempt_dir_for_row(updated)
    active_attempt.mkdir(parents=True, exist_ok=True)

    current_classifier = resolve_path(updated["classifier_results_csv"])
    current_results = resolve_path(updated["results_csv"])
    base_instructions = base_instructions_path_for_row(updated)
    tasks = load_tasks(resolve_path(updated["tasks_file"]))
    base_instruction_text = ensure_base_instructions(base_instructions, updated, tasks)

    target_classifier = active_attempt / "classifier_results.csv"
    target_results = active_attempt / "results.csv"
    target_instructions = active_attempt / "worker_instructions.md"

    for src, dst, columns in [
        (current_classifier, target_classifier, CLASSIFIER_CSV_COLUMNS),
        (current_results, target_results, RESULT_CSV_COLUMNS),
    ]:
        if src.resolve() != dst.resolve() and src.exists() and src.is_file() and not dst.exists():
            shutil.copyfile(src, dst)
        elif not dst.exists():
            write_header(dst, columns)

    updated["base_instructions_file"] = relative_path(base_instructions)
    updated["attempts_dir"] = relative_path(attempts_dir)
    updated["active_attempt"] = relative_path(active_attempt)
    updated["attempt_index"] = str(parse_optional_int(updated.get("attempt_index"), attempt_index_from_dir(active_attempt) or 1))
    updated["classifier_results_csv"] = relative_path(target_classifier)
    updated["results_csv"] = relative_path(target_results)
    updated["instructions_file"] = relative_path(target_instructions)
    if not updated.get("lease_id"):
        updated["lease_id"] = make_lease_id(updated, parse_optional_int(updated.get("attempt_index"), 1))
    if not updated.get("current_attempt_mode"):
        updated["current_attempt_mode"] = updated.get("prepared_mode") or "fresh_full_batch"
    updated["segment_target_rows"] = str(
        parse_optional_int(updated.get("segment_target_rows"), segment_values["target_rows_per_attempt"])
    )
    updated["segment_hard_cap_rows"] = str(
        parse_optional_int(updated.get("segment_hard_cap_rows"), segment_values["hard_cap_rows_per_attempt"])
    )

    inspection = inspect_row(updated)
    prefix_len = inspection["prefix_len"] if inspection["prefix_valid"] else 0
    tasks = inspection["tasks"]
    next_task_index = str(tasks[prefix_len].get("task_index", "")) if prefix_len < len(tasks) else ""
    next_company = str(tasks[prefix_len].get("company_name", "")) if prefix_len < len(tasks) else ""
    attempt_start_prefix_rows = parse_optional_int(updated.get("attempt_start_prefix_rows"), 0)
    lease_id = str(updated.get("lease_id") or make_lease_id(updated, parse_optional_int(updated.get("attempt_index"), 1)))
    active_lease_file = update_batch_lease_file(
        updated,
        active_attempt,
        lease_id,
        parse_optional_int(updated.get("attempt_index"), 1),
        attempt_start_prefix_rows,
        segment_values,
    )
    metadata_path = sync_attempt_metadata(
        updated,
        active_attempt,
        lease_id=lease_id,
        attempt_start_prefix_rows=attempt_start_prefix_rows,
        attempt_mode=updated.get("current_attempt_mode") or updated.get("prepared_mode") or ("continue_from_prefix" if prefix_len > 0 else "fresh_full_batch"),
        segment_policy=segment_values,
    )
    updated["attempt_metadata_file"] = relative_path(metadata_path)
    updated["active_lease_file"] = relative_path(active_lease_file)
    updated["lease_id"] = lease_id
    segment_hard_cap_rows = parse_optional_int(updated.get("segment_hard_cap_rows"), segment_values["hard_cap_rows_per_attempt"])
    segment_end_index = min(len(tasks), prefix_len + segment_hard_cap_rows)
    if segment_end_index > 0 and segment_end_index <= len(tasks):
        segment_end_task = tasks[segment_end_index - 1]
        segment_end_task_index = str(segment_end_task.get("task_index", ""))
        segment_end_company = str(segment_end_task.get("company_name", ""))
    else:
        segment_end_task_index = ""
        segment_end_company = ""
    target_instructions.write_text(
        render_attempt_instruction(
            base_instruction_text=base_instruction_text,
            row=updated,
            attempt_dir=active_attempt,
            attempt_mode=updated.get("current_attempt_mode") or updated.get("prepared_mode") or ("continue_from_prefix" if prefix_len > 0 else "fresh_full_batch"),
            prefix_len=prefix_len,
            next_task_index=next_task_index,
            next_company=next_company,
            lease_id=lease_id,
            active_lease_file=active_lease_file,
            segment_target_rows=parse_optional_int(updated.get("segment_target_rows"), segment_values["target_rows_per_attempt"]),
            segment_hard_cap_rows=segment_hard_cap_rows,
            segment_end_task_index=segment_end_task_index,
            segment_end_company=segment_end_company,
        ),
        encoding="utf-8",
    )
    return updated


def increment_failure_count(row: dict[str, str], policy: dict[str, Any], failure_type: str) -> dict[str, str]:
    updated = dict(row)
    counts = parse_failure_counts(updated.get("failure_counts_json", ""), policy)
    counts[failure_type] = counts.get(failure_type, 0) + 1
    updated["failure_counts_json"] = encode_failure_counts(counts)
    updated["last_failure_type"] = failure_type
    updated["consecutive_no_progress_attempts"] = str(
        parse_optional_int(updated.get("consecutive_no_progress_attempts"), 0) + 1
    )
    updated["last_rerun_reason"] = failure_type
    updated["last_rerun_at"] = iso_now()
    updated["status"] = "needs_rerun"
    updated["planned_rotate"] = ""
    if failure_type in {"startup_no_row", "header_only_timeout", "agent_unresponsive"}:
        updated["startup_failure_count"] = str(parse_optional_int(updated.get("startup_failure_count"), 0) + 1)
    if failure_type in {"partial_stall", "row_count_mismatch", "schema_error"}:
        updated["stall_failure_count"] = str(parse_optional_int(updated.get("stall_failure_count"), 0) + 1)
    updated["escalation_level"] = str(
        max(
            parse_optional_int(updated.get("startup_failure_count"), 0),
            parse_optional_int(updated.get("stall_failure_count"), 0),
            parse_optional_int(updated.get("consecutive_no_progress_attempts"), 0),
        )
    )
    return updated


def reset_progress_counters(row: dict[str, str]) -> dict[str, str]:
    updated = dict(row)
    updated["consecutive_no_progress_attempts"] = "0"
    return updated


def mark_planned_rotate(row: dict[str, str], reason: str) -> dict[str, str]:
    updated = dict(row)
    updated["status"] = "needs_rerun"
    updated["prepared_mode"] = "continue_from_prefix"
    updated["prepared_reason"] = "planned_rotate"
    updated["planned_rotate"] = reason
    updated["last_rerun_reason"] = "planned_rotate"
    updated["last_rerun_at"] = iso_now()
    updated["consecutive_no_progress_attempts"] = "0"
    return updated


def choose_escalation(row: dict[str, str], policy: dict[str, Any]) -> dict[str, Any]:
    counts = parse_failure_counts(row.get("failure_counts_json", ""), policy)
    no_progress_attempts = parse_optional_int(row.get("consecutive_no_progress_attempts"), 0)
    chosen: dict[str, Any] | None = None
    for rule in policy.get("escalation_rules", []):
        min_no_progress = parse_optional_int(rule.get("min_no_progress_attempts"), 0)
        if no_progress_attempts < min_no_progress:
            continue
        tracked_types = [str(value) for value in rule.get("any_failure_types", [])]
        if tracked_types and not any(counts.get(value, 0) > 0 for value in tracked_types):
            continue
        chosen = rule
    if chosen is None:
        chosen = {
            "name": "fallback",
            "model": "gpt-5.4-mini",
            "reasoning_effort": "medium",
            "preferred_attempt_mode": "fresh_full_batch",
        }
    return chosen


def derive_attempt_mode(preferred_mode: str, inspection: dict[str, Any]) -> str:
    if preferred_mode == "narrowed_suffix_only" and inspection["prefix_valid"] and inspection["prefix_len"] > 0:
        return "narrowed_suffix_only"
    if preferred_mode == "continue_from_prefix" and inspection["prefix_valid"] and inspection["prefix_len"] > 0:
        return "continue_from_prefix"
    if inspection["prefix_valid"] and inspection["prefix_len"] > 0 and preferred_mode not in {"fresh_restart", "fresh_full_batch"}:
        return "continue_from_prefix"
    if preferred_mode in {"fresh_restart", "fresh_full_batch"}:
        return preferred_mode
    if inspection["prefix_valid"] and inspection["prefix_len"] > 0:
        return "continue_from_prefix"
    return "fresh_restart"


def launch_start_index(attempt_mode: str, inspection: dict[str, Any]) -> int:
    if attempt_mode in {"continue_from_prefix", "narrowed_suffix_only"}:
        return inspection["prefix_len"]
    return 0


def build_launch_row(row: dict[str, str], inspection: dict[str, Any], policy: dict[str, Any]) -> dict[str, str]:
    rule = choose_escalation(row, policy)
    attempt_mode = row.get("prepared_mode") or derive_attempt_mode(str(rule.get("preferred_attempt_mode", "fresh_full_batch")), inspection)
    start_index = launch_start_index(attempt_mode, inspection)
    tasks = inspection["tasks"]
    if start_index >= len(tasks):
        start_task_index = ""
        start_company = ""
    else:
        start_task_index = str(tasks[start_index].get("task_index", ""))
        start_company = str(tasks[start_index].get("company_name", ""))
    existing_prefix_rows = str(inspection["prefix_len"] if attempt_mode in {"continue_from_prefix", "narrowed_suffix_only"} else 0)
    return {
        "round_index": row["round_index"],
        "worker_slot": row["worker_slot"],
        "batch_file": row["batch_file"],
        "attempt_index": row["attempt_index"],
        "lease_id": row.get("lease_id", ""),
        "attempt_mode": attempt_mode,
        "model": str(rule.get("model", "gpt-5.4-mini")),
        "reasoning_effort": str(rule.get("reasoning_effort", "medium")),
        "task_count": row["task_count"],
        "start_task_index": start_task_index,
        "start_company": start_company,
        "existing_prefix_rows": existing_prefix_rows,
        "attempt_start_prefix_rows": row.get("attempt_start_prefix_rows", existing_prefix_rows),
        "segment_target_rows": row.get("segment_target_rows", ""),
        "segment_hard_cap_rows": row.get("segment_hard_cap_rows", ""),
        "instructions_file": row["instructions_file"],
        "classifier_results_csv": row["classifier_results_csv"],
        "results_csv": row["results_csv"],
        "launch_reason": row.get("prepared_reason") or row.get("last_failure_type") or "initial_launch",
    }


def create_recovery_attempt(
    row: dict[str, str],
    inspection: dict[str, Any],
    attempt_mode: str,
    launch_reason: str,
    policy: dict[str, Any],
) -> dict[str, str]:
    updated = dict(row)
    segment_values = segment_policy_values(policy)
    attempts_dir = attempts_dir_for_row(updated)
    attempts_dir.mkdir(parents=True, exist_ok=True)
    next_attempt_index = parse_optional_int(updated.get("attempt_index"), 1) + 1
    attempt_dir = attempts_dir / f"attempt_{next_attempt_index:04d}"
    attempt_dir.mkdir(parents=True, exist_ok=True)

    classifier_path = attempt_dir / "classifier_results.csv"
    results_path = attempt_dir / "results.csv"
    instructions_path = attempt_dir / "worker_instructions.md"
    metadata_path = attempt_metadata_path(attempt_dir)

    prefix_len = inspection["prefix_len"] if attempt_mode in {"continue_from_prefix", "narrowed_suffix_only"} else 0
    if prefix_len > 0:
        copy_prefix_rows(inspection["classifier_path"], classifier_path, CLASSIFIER_CSV_COLUMNS, prefix_len)
        copy_prefix_rows(inspection["results_path"], results_path, RESULT_CSV_COLUMNS, prefix_len)
    else:
        write_header(classifier_path, CLASSIFIER_CSV_COLUMNS)
        write_header(results_path, RESULT_CSV_COLUMNS)

    base_instruction_path = base_instructions_path_for_row(updated)
    tasks = inspection["tasks"]
    base_instruction_text = ensure_base_instructions(base_instruction_path, updated, tasks)
    next_task_index = str(tasks[prefix_len].get("task_index", "")) if prefix_len < len(tasks) else ""
    next_company = str(tasks[prefix_len].get("company_name", "")) if prefix_len < len(tasks) else ""
    lease_id = make_lease_id(updated, next_attempt_index)
    active_lease_file = update_batch_lease_file(
        updated,
        attempt_dir,
        lease_id,
        next_attempt_index,
        prefix_len,
        segment_values,
    )
    metadata_path = sync_attempt_metadata(
        updated,
        attempt_dir,
        lease_id=lease_id,
        attempt_start_prefix_rows=prefix_len,
        attempt_mode=attempt_mode,
        segment_policy=segment_values,
    )
    segment_hard_cap_rows = segment_values["hard_cap_rows_per_attempt"]
    segment_end_index = min(len(tasks), prefix_len + segment_hard_cap_rows)
    if segment_end_index > 0 and segment_end_index <= len(tasks):
        segment_end_task = tasks[segment_end_index - 1]
        segment_end_task_index = str(segment_end_task.get("task_index", ""))
        segment_end_company = str(segment_end_task.get("company_name", ""))
    else:
        segment_end_task_index = ""
        segment_end_company = ""
    instructions_path.write_text(
        render_attempt_instruction(
            base_instruction_text=base_instruction_text,
            row=updated,
            attempt_dir=attempt_dir,
            attempt_mode=attempt_mode,
            prefix_len=prefix_len,
            next_task_index=next_task_index,
            next_company=next_company,
            lease_id=lease_id,
            active_lease_file=active_lease_file,
            segment_target_rows=segment_values["target_rows_per_attempt"],
            segment_hard_cap_rows=segment_hard_cap_rows,
            segment_end_task_index=segment_end_task_index,
            segment_end_company=segment_end_company,
        ),
        encoding="utf-8",
    )

    updated["active_attempt"] = relative_path(attempt_dir)
    updated["attempt_index"] = str(next_attempt_index)
    updated["attempt_metadata_file"] = relative_path(metadata_path)
    updated["classifier_results_csv"] = relative_path(classifier_path)
    updated["results_csv"] = relative_path(results_path)
    updated["instructions_file"] = relative_path(instructions_path)
    updated["active_lease_file"] = relative_path(active_lease_file)
    updated["lease_id"] = lease_id
    updated["current_attempt_mode"] = attempt_mode
    updated["attempt_start_prefix_rows"] = str(prefix_len)
    updated["planned_rotate"] = ""
    updated["segment_target_rows"] = str(segment_values["target_rows_per_attempt"])
    updated["segment_hard_cap_rows"] = str(segment_values["hard_cap_rows_per_attempt"])
    updated["status"] = "prepared"
    updated["prepared_mode"] = attempt_mode
    updated["prepared_reason"] = launch_reason
    updated["respawn_count"] = str(parse_optional_int(updated.get("respawn_count"), 0) + 1)
    updated["last_seen_classifier_rows"] = str(prefix_len)
    updated["last_seen_result_rows"] = str(prefix_len)
    updated["started_at"] = ""
    updated["first_row_at"] = ""
    updated["last_progress_at"] = ""
    return updated


def build_spawn_prompt(row: dict[str, str], model: str, reasoning: str, launch_reason: str, attempt_mode: str) -> str:
    if attempt_uses_segment_contract(attempt_mode):
        ownership_note = "- This is a narrowed recovery segment. Respect the wrapper lease check and the recovery row cap.\n"
    elif attempt_mode == "continue_from_prefix":
        ownership_note = "- This is a recovery attempt with a preserved prefix. Own the remaining suffix in one fresh worker and do not proactively hand off mid-batch.\n"
    else:
        ownership_note = "- This is the normal full-batch attempt. Own the whole batch in one fresh worker and exit after this single attempt finishes.\n"
    return (
        f"Use a fresh worker subagent for exactly one part4 batch attempt, then exit. Recommended model: {model}, reasoning {reasoning}.\n\n"
        f"Launch reason: {launch_reason}.\n"
        f"Attempt mode: {attempt_mode}.\n"
        f"Lease id: {row.get('lease_id', '')}.\n"
        f"Attempt start prefix rows: {row.get('attempt_start_prefix_rows', '')}.\n"
        f"Recovery segment target rows: {row.get('segment_target_rows', '')}. Recovery hard cap rows: {row.get('segment_hard_cap_rows', '')}.\n"
        "Startup requirement:\n"
        "- Read only the batch-specific instructions and inputs first.\n"
        "- Complete the earliest pending token and write the first classifier/result rows early.\n"
        "- Do not begin with repo-wide scans, `manifest.csv` sweeps, `verification_findings.csv` lookups, or broad exploration of unrelated batches.\n"
        f"{ownership_note}"
        f"Read the worker instructions:\n{resolve_path(row['instructions_file'])}\n\n"
        f"Then execute the batch and write results only to:\n{resolve_path(row['classifier_results_csv'])}\n{resolve_path(row['results_csv'])}\n"
    )


def write_launch_queue(runs_dir: Path, round_index: int, rows: list[dict[str, str]]) -> tuple[Path, Path]:
    csv_path = runs_dir / f"launch_queue_round_{round_index:04d}.csv"
    md_path = runs_dir / f"launch_queue_round_{round_index:04d}.md"
    write_csv(csv_path, LAUNCH_QUEUE_COLUMNS, rows)
    lines = [f"# Round {round_index} Launch Queue", ""]
    for row in rows:
        lines.extend(
            [
                f"## Worker {row['worker_slot']} - {Path(row['batch_file']).name}",
                "",
                "```text",
                build_spawn_prompt(
                    row,
                    row["model"],
                    row["reasoning_effort"],
                    row["launch_reason"],
                    row["attempt_mode"],
                ),
                "```",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return csv_path, md_path


def write_action_plan(runs_dir: Path, round_index: int, rows: list[dict[str, str]]) -> tuple[Path, Path]:
    csv_path = runs_dir / f"runtime_actions_round_{round_index:04d}.csv"
    md_path = runs_dir / f"runtime_actions_round_{round_index:04d}.md"
    if rows:
        write_csv(csv_path, ACTION_COLUMNS, rows)
        lines = [f"# Round {round_index} Runtime Actions", ""]
        for row in rows:
            lines.append(
                f"- {Path(row['batch_file']).name}: {row['action']} / {row['reason']} / mode {row['recommended_mode']} / model {row['model']} {row['reasoning_effort']} / lease {row.get('lease_id', '')}"
            )
        md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        for path in [csv_path, md_path]:
            if path.exists():
                path.unlink()
    return csv_path, md_path


def prepare_launches(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    policy: dict[str, Any],
    batch_scope: set[str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    updated_rows: list[dict[str, str]] = []
    launch_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = upgrade_row_to_attempt_architecture(row)
        updated, inspection = reconcile_active_attempt(updated, policy)
        updated["status"] = normalize_status(updated.get("status", ""), updated.get("started_at", ""))
        if parse_optional_int(updated.get("round_index"), 0) != round_index:
            updated_rows.append(updated)
            continue
        if batch_scope and str(updated.get("batch_file") or "") not in batch_scope:
            updated_rows.append(updated)
            continue

        if updated.get("status") == "deferred_long_tail":
            updated_rows.append(updated)
            continue

        if inspection["state"] == "completed" and not (updated.get("status") == "needs_rerun" and is_qc_forced_rerun(updated)):
            updated["status"] = "completed"
            updated["completion_mode"] = updated.get("completion_mode") or "normal"
            updated["prepared_mode"] = ""
            updated["prepared_reason"] = ""
            updated["planned_rotate"] = ""
            updated["last_seen_classifier_rows"] = str(inspection["classifier_rows"])
            updated["last_seen_result_rows"] = str(inspection["result_rows"])
            updated = reset_progress_counters(updated)
            updated_rows.append(updated)
            continue

        if updated["status"] == "running":
            updated_rows.append(updated)
            continue

        if updated["status"] == "needs_rerun":
            rule = choose_escalation(updated, policy)
            requested_mode = updated.get("prepared_mode") or str(rule.get("preferred_attempt_mode", "fresh_restart"))
            if requested_mode == "fresh_restart" and inspection["state"] == "partial_misaligned" and inspection["prefix_valid"] and inspection["prefix_len"] > 0:
                requested_mode = "continue_from_prefix"
            attempt_mode = derive_attempt_mode(requested_mode, inspection)
            launch_reason = updated.get("prepared_reason") or updated.get("last_failure_type") or updated.get("last_rerun_reason") or "needs_rerun"
            updated = create_recovery_attempt(updated, inspection, attempt_mode, launch_reason, policy)
            if attempt_mode == "fresh_restart":
                inspection = inspect_row(updated)
            else:
                updated, inspection = reconcile_active_attempt(updated, policy)
        else:
            if inspection["state"] == "partial_misaligned":
                updated = increment_failure_count(updated, policy, "schema_error")
                rule = choose_escalation(updated, policy)
                preferred_mode = str(rule.get("preferred_attempt_mode", "fresh_restart"))
                if preferred_mode == "fresh_restart" and inspection["prefix_valid"] and inspection["prefix_len"] > 0:
                    preferred_mode = "continue_from_prefix"
                attempt_mode = derive_attempt_mode(preferred_mode, inspection)
                updated = create_recovery_attempt(updated, inspection, attempt_mode, updated["last_failure_type"], policy)
                updated, inspection = reconcile_active_attempt(updated, policy)
            else:
                updated["status"] = "prepared"
                if inspection["prefix_valid"] and inspection["prefix_len"] > 0:
                    updated["prepared_mode"] = "continue_from_prefix"
                    updated["prepared_reason"] = updated.get("prepared_reason") or "resume_partial_batch"
                else:
                    updated["prepared_mode"] = "fresh_full_batch"
                    updated["prepared_reason"] = updated.get("prepared_reason") or "initial_launch"
                updated["current_attempt_mode"] = updated["prepared_mode"]
                updated["planned_rotate"] = ""
                updated["last_seen_classifier_rows"] = str(inspection["classifier_rows"])
                updated["last_seen_result_rows"] = str(inspection["result_rows"])

        launch_rows.append(build_launch_row(updated, inspection, policy))
        updated_rows.append(updated)
    return updated_rows, launch_rows


def mark_round_started(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    batch_scope: set[str] | None = None,
) -> list[dict[str, str]]:
    started_at = iso_now()
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        updated["status"] = normalize_status(updated.get("status", ""), updated.get("started_at", ""))
        in_scope = (
            parse_optional_int(updated.get("round_index"), 0) == round_index
            and (not batch_scope or str(updated.get("batch_file") or "") in batch_scope)
        )
        if in_scope and updated.get("status") == "prepared":
            updated["status"] = "running"
            updated["current_attempt_mode"] = updated.get("prepared_mode") or updated.get("current_attempt_mode") or "fresh_full_batch"
            updated["planned_rotate"] = ""
            updated["started_at"] = started_at
            updated["round_entry_started_at"] = updated.get("round_entry_started_at") or started_at
            if parse_optional_int(updated.get("last_seen_classifier_rows"), 0) > 0 or parse_optional_int(updated.get("last_seen_result_rows"), 0) > 0:
                updated["first_row_at"] = updated.get("first_row_at") or started_at
                updated["last_progress_at"] = updated.get("last_progress_at") or started_at
        updated_rows.append(updated)
    return updated_rows


def watch_round(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    policy: dict[str, Any],
    startup_timeout_seconds: int,
    partial_stall_timeout_seconds: int,
    batch_scope: set[str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    updated_rows: list[dict[str, str]] = []
    actions: list[dict[str, str]] = []
    current_time = now_utc()
    current_iso = current_time.isoformat()
    startup_timeout = startup_timeout_seconds or parse_optional_int(policy.get("timeouts", {}).get("startup_no_row_seconds"), 300)
    stall_timeout = partial_stall_timeout_seconds or parse_optional_int(policy.get("timeouts", {}).get("partial_stall_seconds"), 240)
    segment_values = segment_policy_values(policy)

    for row in schedule_rows:
        updated = upgrade_row_to_attempt_architecture(row)
        updated, inspection = reconcile_active_attempt(updated, policy)
        updated["status"] = normalize_status(updated.get("status", ""), updated.get("started_at", ""))
        if parse_optional_int(updated.get("round_index"), 0) != round_index:
            updated_rows.append(updated)
            continue
        if batch_scope and str(updated.get("batch_file") or "") not in batch_scope:
            updated_rows.append(updated)
            continue

        if updated.get("status") == "deferred_long_tail":
            updated_rows.append(updated)
            continue

        classifier_rows = inspection["classifier_rows"]
        result_rows = inspection["result_rows"]
        previous_classifier_rows = parse_optional_int(updated.get("last_seen_classifier_rows"), 0)
        previous_result_rows = parse_optional_int(updated.get("last_seen_result_rows"), 0)
        progress_increased = classifier_rows > previous_classifier_rows or result_rows > previous_result_rows
        attempt_start_prefix_rows = parse_optional_int(updated.get("attempt_start_prefix_rows"), 0)
        attempt_rows_added = max(0, parse_optional_int(inspection.get("prefix_len"), 0) - attempt_start_prefix_rows)
        current_attempt_mode = (updated.get("current_attempt_mode") or updated.get("prepared_mode") or "fresh_full_batch").strip()
        uses_segment_contract = attempt_uses_segment_contract(current_attempt_mode)
        updated["last_seen_classifier_rows"] = str(classifier_rows)
        updated["last_seen_result_rows"] = str(result_rows)

        if inspection["state"] == "completed":
            updated["status"] = "completed"
            updated["completion_mode"] = updated.get("completion_mode") or "normal"
            updated["prepared_mode"] = ""
            updated["prepared_reason"] = ""
            updated["planned_rotate"] = ""
            updated["first_row_at"] = updated.get("first_row_at") or current_iso
            updated["last_progress_at"] = current_iso
            updated = reset_progress_counters(updated)
            updated_rows.append(updated)
            continue

        if classifier_rows > 0 or result_rows > 0:
            updated["first_row_at"] = updated.get("first_row_at") or current_iso
        if progress_increased:
            updated["last_progress_at"] = current_iso
            updated = reset_progress_counters(updated)

        if updated.get("status") != "running" or not updated.get("started_at"):
            updated_rows.append(updated)
            continue

        started_at = parse_iso(updated.get("started_at", "")) or current_time
        last_progress_at = parse_iso(updated.get("last_progress_at", "")) or parse_iso(updated.get("first_row_at", "")) or started_at
        elapsed_since_start = int((current_time - started_at).total_seconds())
        elapsed_since_progress = int((current_time - last_progress_at).total_seconds())

        planned_rotate_reason = ""
        failure_type = ""
        if inspection["state"] == "header_only" and elapsed_since_start >= startup_timeout:
            failure_type = "startup_no_row"
        elif (
            uses_segment_contract
            and inspection["state"] == "partial_prefix"
            and inspection["prefix_len"] < inspection["expected_rows"]
            and attempt_rows_added >= parse_optional_int(updated.get("segment_hard_cap_rows"), segment_values["hard_cap_rows_per_attempt"])
        ):
            planned_rotate_reason = "segment_hard_cap_reached"
        elif (
            uses_segment_contract
            and inspection["state"] == "partial_prefix"
            and inspection["prefix_len"] < inspection["expected_rows"]
            and attempt_rows_added >= parse_optional_int(updated.get("segment_target_rows"), segment_values["target_rows_per_attempt"])
            and elapsed_since_progress >= segment_values["planned_rotate_idle_seconds"]
        ):
            planned_rotate_reason = "segment_target_reached"
        elif inspection["state"] == "partial_prefix" and elapsed_since_progress >= stall_timeout:
            failure_type = "partial_stall"
        elif inspection["state"] == "partial_misaligned" and elapsed_since_progress >= stall_timeout:
            failure_type = "row_count_mismatch"

        if failure_type:
            updated = increment_failure_count(updated, policy, failure_type)
            rule = choose_escalation(updated, policy)
            preferred_mode = str(rule.get("preferred_attempt_mode", "fresh_restart"))
            if failure_type == "row_count_mismatch" and preferred_mode == "fresh_restart" and inspection["prefix_valid"] and inspection["prefix_len"] > 0:
                preferred_mode = "continue_from_prefix"
            attempt_mode = derive_attempt_mode(preferred_mode, inspection)
            updated["prepared_mode"] = attempt_mode
            updated["prepared_reason"] = failure_type
            actions.append(
                {
                    "round_index": updated["round_index"],
                    "worker_slot": updated["worker_slot"],
                    "batch_file": updated["batch_file"],
                    "attempt_index": updated["attempt_index"],
                    "lease_id": updated.get("lease_id", ""),
                    "action": "kill_and_respawn",
                    "recommended_mode": attempt_mode,
                    "model": str(rule.get("model", "gpt-5.4-mini")),
                    "reasoning_effort": str(rule.get("reasoning_effort", "medium")),
                    "reason": failure_type,
                    "classifier_rows": str(classifier_rows),
                    "result_rows": str(result_rows),
                    "prefix_rows": str(inspection["prefix_len"]),
                    "attempt_rows_added": str(attempt_rows_added),
                }
            )
        elif planned_rotate_reason:
            updated = mark_planned_rotate(updated, planned_rotate_reason)
            rule = choose_escalation(updated, policy)
            actions.append(
                {
                    "round_index": updated["round_index"],
                    "worker_slot": updated["worker_slot"],
                    "batch_file": updated["batch_file"],
                    "attempt_index": updated["attempt_index"],
                    "lease_id": updated.get("lease_id", ""),
                    "action": "rotate_segment",
                    "recommended_mode": "continue_from_prefix",
                    "model": str(rule.get("model", "gpt-5.4-mini")),
                    "reasoning_effort": str(rule.get("reasoning_effort", "medium")),
                    "reason": planned_rotate_reason,
                    "classifier_rows": str(classifier_rows),
                    "result_rows": str(result_rows),
                    "prefix_rows": str(inspection["prefix_len"]),
                    "attempt_rows_added": str(attempt_rows_added),
                }
            )
        else:
            updated["status"] = "running"
            updated["planned_rotate"] = ""

        updated_rows.append(updated)

    return updated_rows, actions


def main() -> None:
    args = parse_args()
    runs_dir = args.runs_dir.resolve()
    schedule_csv = resolve_path(args.schedule_csv) if args.schedule_csv else runs_dir / "schedule.csv"
    policy = load_policy(resolve_path(args.policy_json))
    fieldnames, schedule_rows = load_schedule(schedule_csv, policy)
    batch_scope = resolve_batch_scope(args.batch_file, schedule_rows, round_index=args.round_index)

    if args.prepare_launches:
        updated_rows, launch_rows = prepare_launches(
            schedule_rows,
            args.round_index,
            policy,
            batch_scope=batch_scope or None,
        )
        write_schedule(schedule_csv, fieldnames, updated_rows)
        launch_csv, launch_md = write_launch_queue(runs_dir, args.round_index, launch_rows)
        print(f"Schedule CSV: {schedule_csv}")
        print(f"Launch queue rows: {len(launch_rows)}")
        print(f"Launch queue CSV: {launch_csv}")
        print(f"Launch queue markdown: {launch_md}")
        if batch_scope:
            print(f"Batch scope: {', '.join(sorted(Path(item).name for item in batch_scope))}")
        return

    if args.mark_round_started:
        updated_rows = mark_round_started(schedule_rows, args.round_index, batch_scope=batch_scope or None)
        write_schedule(schedule_csv, fieldnames, updated_rows)
        print(f"Schedule CSV: {schedule_csv}")
        if batch_scope:
            print(f"Marked {len(batch_scope)} batch(es) in round {args.round_index} as started.")
        else:
            print(f"Marked round {args.round_index} as started.")
        return

    updated_rows, action_rows = watch_round(
        schedule_rows=schedule_rows,
        round_index=args.round_index,
        policy=policy,
        startup_timeout_seconds=args.startup_no_row_timeout_seconds,
        partial_stall_timeout_seconds=args.partial_stall_timeout_seconds,
        batch_scope=batch_scope or None,
    )
    write_schedule(schedule_csv, fieldnames, updated_rows)
    actions_csv, actions_md = write_action_plan(runs_dir, args.round_index, action_rows)
    print(f"Schedule CSV: {schedule_csv}")
    print(f"Runtime actions: {len(action_rows)}")
    if action_rows:
        print(f"Runtime actions CSV: {actions_csv}")
        print(f"Runtime actions markdown: {actions_md}")
        for row in action_rows[:20]:
            print(
                f"- {Path(row['batch_file']).name}: {row['action']} / {row['reason']} / {row['recommended_mode']} / {row['model']} {row['reasoning_effort']}"
            )
        raise SystemExit("Round runtime watch detected actions.")


if __name__ == "__main__":
    main()
