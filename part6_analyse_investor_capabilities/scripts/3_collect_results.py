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

from part6_schedule_io import write_schedule_csv
from part6_schema import (
    ALLOWED_CONFIDENCE,
    ALLOWED_INVESTOR_ARCHETYPES,
    ALLOWED_LIKELIHOODS,
    ALLOWED_SEARCH_TIERS,
    ALLOWED_VERDICTS,
    ALLOWED_VERIFICATION_ACTIONS,
    ALLOWED_YES_NO,
    BLOCKING_VERIFICATION_ACTIONS,
    CAPABILITY_FLAG_COLUMNS,
    CLASSIFIER_CSV_COLUMNS,
    RESULT_CSV_COLUMNS,
    VERIFICATION_CSV_COLUMNS,
    capability_labels_from_row,
    ensure_capability_labels,
    parse_json_list,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent

DEFAULT_RUNS_DIR = PART6_DIR / "agent_runs" / "crypto_investor_parallel"
DEFAULT_FINAL_DIR = PART6_DIR / "agent_runs" / "crypto_investor"
DEFAULT_BATCH_DIR = PART6_DIR / "agent_task_batches" / "crypto_investor"
DEFAULT_RUNTIME_POLICY_JSON = PART6_DIR / "runtime" / "policy.json"
AUTO_RERUN_BATCHES_CSV = "lint_rerun_batches.csv"
AUTO_RERUN_BATCHES_MD = "lint_rerun_batches.md"
STARTUP_RESPAWN_BATCHES_CSV = "startup_respawn_batches.csv"
STARTUP_RESPAWN_BATCHES_MD = "startup_respawn_batches.md"
HEADER_ONLY_RERUN_BATCHES_CSV = "header_only_rerun_batches.csv"
HEADER_ONLY_RERUN_BATCHES_MD = "header_only_rerun_batches.md"
DEFAULT_STARTUP_NO_ROW_TIMEOUT_SECONDS = 300
DEFAULT_HEADER_ONLY_TIMEOUT_SECONDS = 300

LIST_COLUMNS = [
    "capability_labels",
    "other_flags",
]
SOURCE_TYPE_PATTERN = re.compile(r"^[a-z0-9_]+$")

RUNTIME_ACTIVE_STATUSES = {"prepared", "running", "needs_rerun", "completed", "deferred_long_tail"}
RUNTIME_RESOLVED_STATUSES = {"completed", "deferred_long_tail"}
RUNTIME_FAILURE_ALIASES = {
    "startup_no_first_row_timeout": "startup_no_row",
    "header_only_timeout_both_outputs": "header_only_timeout",
    "partial_stall_timeout": "partial_stall",
    "row_count_mismatch": "row_count_mismatch",
    "severe_schema_error": "schema_error",
    "schema_error": "schema_error",
    "search_tier_too_conservative": "verifier_forced_rerun",
    "search_should_not_have_been_skipped": "verifier_forced_rerun",
    "rerun_investor": "verifier_forced_rerun",
    "rerun_batch": "verifier_forced_rerun",
}


def canonicalize_runtime_failure_reasons(reason: str) -> list[str]:
    tokens = [token.strip() for token in str(reason or "").split("|") if token.strip()]
    if not tokens:
        return ["schema_error"]

    canonical: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        mapped = RUNTIME_FAILURE_ALIASES.get(token, token)
        if mapped and mapped not in seen:
            canonical.append(mapped)
            seen.add(mapped)
    return canonical or ["schema_error"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect part6 worker result CSVs, enforce verifier gates, and update final outputs.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Worker runs directory containing schedule.csv and per-batch results.csv files.",
    )
    parser.add_argument(
        "--schedule-csv",
        type=Path,
        default=None,
        help="Schedule CSV. Defaults to <runs-dir>/schedule.csv.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Final merged results CSV. Defaults to part6_analyse_investor_capabilities/agent_runs/crypto_investor/results.csv.",
    )
    parser.add_argument(
        "--classifier-results-csv",
        type=Path,
        default=None,
        help="Final classifier/router CSV. Defaults to part6_analyse_investor_capabilities/agent_runs/crypto_investor/classifier_results.csv.",
    )
    parser.add_argument(
        "--manual-review-csv",
        type=Path,
        default=None,
        help="Manual review CSV. Defaults to part6_analyse_investor_capabilities/agent_runs/crypto_investor/needs_manual_review.csv.",
    )
    parser.add_argument(
        "--verification-findings-csv",
        type=Path,
        default=None,
        help="Merged verifier report CSV. Defaults to part6_analyse_investor_capabilities/agent_runs/crypto_investor/verification_findings.csv.",
    )
    parser.add_argument(
        "--checkpoint-json",
        type=Path,
        default=None,
        help="Checkpoint JSON. Defaults to part6_analyse_investor_capabilities/agent_runs/crypto_investor/checkpoint.json.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Write outputs even when scheduled worker rows are missing or validation errors exist.",
    )
    parser.add_argument(
        "--allow-unresolved-verification",
        action="store_true",
        help="Allow merge when verifier recommends edit/rerun/process updates. Intended only for debug.",
    )
    parser.add_argument(
        "--skip-verification",
        action="store_true",
        help="Skip mandatory verifier checks. Intended only for legacy/debug runs.",
    )
    parser.add_argument(
        "--replace-output",
        action="store_true",
        help="Replace existing final results instead of appending to a v2 final CSV.",
    )
    parser.add_argument(
        "--cleanup-run-artifacts",
        action="store_true",
        help="Delete scheduled per-batch/per-round run artifacts after a successful merge.",
    )
    parser.add_argument(
        "--lint-only",
        action="store_true",
        help="Run classifier/worker validation only and do not write or merge outputs.",
    )
    parser.add_argument(
        "--watch-header-only",
        action="store_true",
        help="Watch the current round for stale header-only outputs and auto-mark needs_rerun without waiting for full lint.",
    )
    parser.add_argument(
        "--watch-startup-no-row",
        action="store_true",
        help="Watch the current round for startup failures where both CSVs remain header-only and request immediate kill+respawn.",
    )
    parser.add_argument(
        "--round-index",
        type=int,
        default=0,
        help="Round index to inspect with startup/header-only watch modes. Required when schedule.csv contains multiple incomplete rounds.",
    )
    parser.add_argument(
        "--batch-file",
        action="append",
        default=[],
        help=(
            "Optional batch scope for lint/collect. Repeatable. Accepts the schedule batch_file "
            "value, an absolute path, or a basename like batch_0226.jsonl."
        ),
    )
    parser.add_argument(
        "--startup-no-row-timeout-seconds",
        type=int,
        default=DEFAULT_STARTUP_NO_ROW_TIMEOUT_SECONDS,
        help="Seconds to wait before kill+respawn when both CSVs remain header-only. Defaults to 480.",
    )
    parser.add_argument(
        "--header-only-timeout-seconds",
        type=int,
        default=DEFAULT_HEADER_ONLY_TIMEOUT_SECONDS,
        help="Seconds to wait before auto-rerunning a batch whose outputs remain header-only. Defaults to 300.",
    )
    parser.add_argument(
        "--fail-on-identity-drift",
        action="store_true",
        help="Treat any immutable-identity override from tasks.jsonl as a validation failure.",
    )
    parser.add_argument(
        "--repair-identity-drift-in-place",
        action="store_true",
        help="Rewrite scheduled classifier/results CSV identity fields from tasks.jsonl before validation.",
    )
    return parser.parse_args()


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def resolve_batch_scope(
    schedule_rows: list[dict[str, str]],
    raw_batch_values: list[str],
) -> list[str]:
    requested = [str(value or "").strip() for value in raw_batch_values if str(value or "").strip()]
    if not requested:
        return []

    batch_lookup: list[tuple[str, Path]] = []
    for row in schedule_rows:
        batch_file = str(row.get("batch_file") or "").strip()
        if not batch_file:
            continue
        batch_lookup.append((batch_file, resolve_path(batch_file)))

    resolved_scope: list[str] = []
    seen: set[str] = set()
    missing: list[str] = []
    for raw in requested:
        raw_path = Path(raw)
        raw_name = raw_path.name
        matched_value = ""
        try:
            requested_path = raw_path.resolve() if raw_path.is_absolute() else (REPO_ROOT / raw_path).resolve()
        except OSError:
            requested_path = None
        for batch_file, batch_path in batch_lookup:
            if raw == batch_file or raw_name == Path(batch_file).name:
                matched_value = batch_file
                break
            if requested_path is not None and requested_path == batch_path:
                matched_value = batch_file
                break
        if not matched_value:
            missing.append(raw)
            continue
        if matched_value not in seen:
            resolved_scope.append(matched_value)
            seen.add(matched_value)

    if missing:
        available = ", ".join(Path(batch_file).name for batch_file, _ in batch_lookup) or "none"
        raise SystemExit(
            "Requested --batch-file values are not present in schedule.csv: "
            f"{', '.join(missing)}. Available batches: {available}"
        )
    return resolved_scope


def load_runtime_policy(path: Path = DEFAULT_RUNTIME_POLICY_JSON) -> dict:
    with path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def default_failure_counts() -> dict[str, int]:
    policy = load_runtime_policy()
    raw = policy.get("failure_count_defaults") or {}
    return {str(key): int(value) for key, value in raw.items()}


def parse_failure_counts_json(value: str) -> dict[str, int]:
    counts = default_failure_counts()
    raw = (value or "").strip()
    if not raw:
        return counts
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return counts
    if isinstance(parsed, dict):
        for key, raw_value in parsed.items():
            counts[str(key)] = parse_optional_int(raw_value, counts.get(str(key), 0))
    return counts


def encode_failure_counts_json(counts: dict[str, int]) -> str:
    return json.dumps({key: int(counts[key]) for key in sorted(counts)}, ensure_ascii=False, separators=(",", ":"))


def normalize_runtime_status(status: str, started_at: str) -> str:
    raw = (status or "").strip()
    if raw in RUNTIME_ACTIVE_STATUSES:
        return raw
    if raw in {"pending", "pending_launch", ""}:
        return "prepared"
    if raw == "rerun_batch":
        return "needs_rerun"
    if raw == "partial":
        return "running" if (started_at or "").strip() else "prepared"
    if raw == "completed":
        return "completed"
    return "prepared"


def is_deferred_long_tail_row(row: dict[str, str]) -> bool:
    status = normalize_runtime_status(row.get("status", ""), row.get("started_at", ""))
    completion_mode = (row.get("completion_mode") or "").strip()
    if status == "deferred_long_tail":
        return True
    if status == "completed":
        return False
    return completion_mode == "deferred_long_tail"


def effective_runtime_status(row: dict[str, str]) -> str:
    if is_deferred_long_tail_row(row):
        return "deferred_long_tail"
    return normalize_runtime_status(row.get("status", ""), row.get("started_at", ""))


def is_resolved_runtime_row(row: dict[str, str]) -> bool:
    return effective_runtime_status(row) in RUNTIME_RESOLVED_STATUSES


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


def map_rerun_reason_to_failure_type(reason: str) -> str:
    return "|".join(canonicalize_runtime_failure_reasons(reason))


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows = [repair_extra_columns(row, fieldnames) for row in reader]
        return fieldnames, rows


def count_rows(path: Path, expected_header: list[str]) -> tuple[int, bool, list[dict[str, str]]]:
    if not path.exists() or not path.is_file():
        return 0, False, []
    header, rows = load_csv(path)
    return len(rows), header == expected_header, rows


def load_tasks_jsonl(path: Path) -> list[dict]:
    tasks: list[dict] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def build_tasks_by_index(path: Path) -> dict[int, dict]:
    tasks_by_index: dict[int, dict] = {}
    for task in load_tasks_jsonl(path):
        raw_task_index = str(task.get("task_index", "")).strip()
        if not raw_task_index:
            continue
        try:
            task_index = int(raw_task_index)
        except ValueError:
            continue
        tasks_by_index[task_index] = task
    return tasks_by_index


def make_identity_override_tracker() -> dict[str, object]:
    return {"count": 0, "samples": [], "by_source": {}}


def split_pipe_list(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw or raw == "[]":
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in raw.split("|") if item.strip()]


def record_identity_override(
    tracker: dict[str, object] | None,
    source: Path,
    task_index: int,
    investor_name: str,
    changes: list[str],
) -> None:
    if tracker is None or not changes:
        return
    tracker["count"] = int(tracker.get("count", 0)) + 1
    samples = tracker.setdefault("samples", [])
    by_source = tracker.setdefault("by_source", {})
    if isinstance(by_source, dict):
        source_key = str(source)
        by_source[source_key] = int(by_source.get(source_key, 0)) + 1
    if isinstance(samples, list) and len(samples) < 10:
        samples.append(
            f"{source}: task_index={task_index} company={investor_name}: "
            + "; ".join(changes)
        )


def canonicalize_identity_fields(
    row: dict[str, str],
    task: dict,
    source: Path,
    tracker: dict[str, object] | None = None,
) -> dict[str, str]:
    normalized = dict(row)
    task_index = str(task.get("task_index", normalized.get("task_index", "")))
    investor_name = str(task.get("investor_name", normalized.get("investor_name", "")))
    changes: list[str] = []
    for key, expected in [
        ("task_index", task_index),
        ("investor_id", str(task.get("investor_id", normalized.get("investor_id", "")))),
        ("investor_name", investor_name),
    ]:
        actual = str(normalized.get(key, ""))
        if actual != expected:
            changes.append(f"{key} overridden from {actual!r} to {expected!r}")
        normalized[key] = expected
    if "normalized_domain" in normalized:
        expected_domain = str(task.get("normalized_domain", normalized.get("normalized_domain", "")))
        actual_domain = str(normalized.get("normalized_domain", ""))
        if actual_domain != expected_domain:
            changes.append(
                f"normalized_domain overridden from {actual_domain!r} to {expected_domain!r}"
            )
        normalized["normalized_domain"] = expected_domain
    record_identity_override(
        tracker=tracker,
        source=source,
        task_index=int(task_index) if task_index else -1,
        investor_name=investor_name,
        changes=changes,
    )
    return normalized


def repair_extra_columns(row: dict, fieldnames: list[str]) -> dict[str, str]:
    """Repair rows where unquoted commas split evidence_summary."""
    if None not in row:
        return {field: row.get(field, "") for field in fieldnames}

    values = [row.get(field, "") for field in fieldnames] + list(row.get(None) or [])
    if len(values) <= len(fieldnames):
        return {field: values[index] if index < len(values) else "" for index, field in enumerate(fieldnames)}

    if "evidence_summary" not in fieldnames:
        return {field: row.get(field, "") for field in fieldnames}

    evidence_index = fieldnames.index("evidence_summary")
    tail_count = 4
    fixed_values = (
        values[:evidence_index]
        + [",".join(values[evidence_index : len(values) - tail_count])]
        + values[len(values) - tail_count :]
    )
    return {
        field: fixed_values[index] if index < len(fixed_values) else ""
        for index, field in enumerate(fieldnames)
    }


def load_schedule(path: Path) -> list[dict[str, str]]:
    header, rows = load_csv(path)
    if not header:
        raise SystemExit(f"Schedule CSV has no header: {path}")
    return rows


def parse_optional_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return default


def attempt_index_from_dir(path: Path) -> int:
    match = re.match(r"attempt_(\d+)$", path.name)
    if not match:
        return 0
    return parse_optional_int(match.group(1), default=0)


def attempt_metadata_path(attempt_dir: Path) -> Path:
    return attempt_dir / "attempt_metadata.json"


def load_attempt_metadata(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def inspect_attempt_candidate(schedule_row: dict[str, str], attempt_dir: Path) -> dict[str, Any]:
    tasks = load_tasks_jsonl(ensure_file(resolve_path(schedule_row["tasks_file"]), "Tasks JSONL"))
    expected_rows = parse_optional_int(schedule_row.get("task_count"), default=0)
    classifier_path = attempt_dir / "classifier_results.csv"
    results_path = attempt_dir / "results.csv"
    classifier_rows, classifier_header_ok, classifier_data = 0, False, []
    result_rows, results_header_ok, result_data = 0, False, []
    if classifier_path.exists() and classifier_path.is_file():
        classifier_rows, classifier_header_ok, classifier_data = count_rows(classifier_path, CLASSIFIER_CSV_COLUMNS)
    if results_path.exists() and results_path.is_file():
        result_rows, results_header_ok, result_data = count_rows(results_path, RESULT_CSV_COLUMNS)

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

    last_activity = 0.0
    for path in [classifier_path, results_path, attempt_metadata_path(attempt_dir), attempt_dir / "worker_instructions.md"]:
        if path.exists():
            try:
                last_activity = max(last_activity, path.stat().st_mtime)
            except OSError:
                pass

    return {
        "attempt_dir": attempt_dir,
        "attempt_index": attempt_index_from_dir(attempt_dir),
        "metadata": load_attempt_metadata(attempt_metadata_path(attempt_dir)),
        "classifier_path": classifier_path,
        "results_path": results_path,
        "instructions_path": attempt_dir / "worker_instructions.md",
        "prefix_len": prefix_len,
        "classifier_rows": classifier_rows,
        "result_rows": result_rows,
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
        parse_optional_int(candidate.get("prefix_len"), default=0),
        min(
            parse_optional_int(candidate.get("classifier_rows"), default=0),
            parse_optional_int(candidate.get("result_rows"), default=0),
        ),
        float(candidate.get("last_activity") or 0.0),
        parse_optional_int(candidate.get("attempt_index"), default=0),
    )


def reconcile_schedule_attempts(schedule_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        attempts_dir_raw = (updated.get("attempts_dir") or "").strip()
        if not attempts_dir_raw:
            updated_rows.append(updated)
            continue
        attempts_dir = resolve_path(attempts_dir_raw)
        if not attempts_dir.exists() or not attempts_dir.is_dir():
            updated_rows.append(updated)
            continue
        candidates = [
            inspect_attempt_candidate(updated, path)
            for path in sorted(attempts_dir.iterdir(), key=attempt_index_from_dir)
            if path.is_dir() and re.match(r"attempt_\d+$", path.name)
        ]
        if not candidates:
            updated_rows.append(updated)
            continue
        best = max(candidates, key=attempt_candidate_sort_key)
        metadata = best.get("metadata") or {}
        updated["active_attempt"] = str(best["attempt_dir"])
        updated["attempt_index"] = str(
            parse_optional_int(metadata.get("attempt_index"), default=parse_optional_int(best.get("attempt_index"), default=1))
        )
        updated["attempt_metadata_file"] = str(attempt_metadata_path(Path(best["attempt_dir"])))
        updated["classifier_results_csv"] = str(best["classifier_path"])
        updated["results_csv"] = str(best["results_path"])
        updated["instructions_file"] = str(best["instructions_path"])
        if metadata.get("lease_id"):
            updated["lease_id"] = str(metadata.get("lease_id"))
        if metadata.get("attempt_start_prefix_rows") is not None:
            updated["attempt_start_prefix_rows"] = str(parse_optional_int(metadata.get("attempt_start_prefix_rows"), default=0))
        if metadata.get("segment_target_rows") is not None:
            updated["segment_target_rows"] = str(parse_optional_int(metadata.get("segment_target_rows"), default=0))
        if metadata.get("segment_hard_cap_rows") is not None:
            updated["segment_hard_cap_rows"] = str(parse_optional_int(metadata.get("segment_hard_cap_rows"), default=0))
        updated["last_seen_classifier_rows"] = str(best.get("classifier_rows", 0))
        updated["last_seen_result_rows"] = str(best.get("result_rows", 0))
        updated_rows.append(updated)
    return updated_rows


def inspect_csv_output(
    path: Path,
    expected_header: list[str],
    expected_rows: int,
) -> dict[str, object]:
    if not path.exists() or not path.is_file():
        return {
            "path": path,
            "exists": False,
            "header_matches": False,
            "row_count": 0,
            "state": "missing",
            "mtime": 0.0,
        }

    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0

    try:
        header, rows = load_csv(path)
    except Exception:
        return {
            "path": path,
            "exists": True,
            "header_matches": False,
            "row_count": 0,
            "state": "unreadable",
            "mtime": mtime,
        }

    row_count = len(rows)
    header_matches = header == expected_header
    if not header_matches:
        state = "header_mismatch"
    elif row_count == 0:
        state = "header_only"
    elif expected_rows > 0 and row_count == expected_rows:
        state = "completed"
    else:
        state = "partial"

    return {
        "path": path,
        "exists": True,
        "header_matches": header_matches,
        "row_count": row_count,
        "state": state,
        "mtime": mtime,
    }


def inspect_batch_outputs(schedule_row: dict[str, str]) -> dict[str, object]:
    expected_rows = parse_optional_int(schedule_row.get("task_count"), default=0)
    classifier_path = resolve_path(schedule_row.get("classifier_results_csv") or "")
    results_path = resolve_path(schedule_row.get("results_csv") or "")
    classifier_state = inspect_csv_output(
        classifier_path,
        CLASSIFIER_CSV_COLUMNS,
        expected_rows,
    )
    results_state = inspect_csv_output(
        results_path,
        RESULT_CSV_COLUMNS,
        expected_rows,
    )

    current_status = effective_runtime_status(schedule_row)
    if current_status == "deferred_long_tail":
        schedule_status = "deferred_long_tail"
    elif (
        classifier_state["state"] == "completed"
        and results_state["state"] == "completed"
    ):
        schedule_status = "completed"
    elif current_status in {"prepared", "running", "needs_rerun"}:
        schedule_status = current_status
    else:
        schedule_status = "prepared"

    last_activity = max(
        float(classifier_state.get("mtime") or 0.0),
        float(results_state.get("mtime") or 0.0),
    )

    return {
        "classifier": classifier_state,
        "results": results_state,
        "schedule_status": schedule_status,
        "last_activity": last_activity,
    }


def refresh_schedule_statuses(schedule_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        updated["status"] = str(inspect_batch_outputs(row)["schedule_status"])
        updated_rows.append(updated)
    return updated_rows


def get_incomplete_rounds(schedule_rows: list[dict[str, str]]) -> list[int]:
    rounds = {
        parse_optional_int(row.get("round_index"), default=0)
        for row in schedule_rows
        if not is_resolved_runtime_row(row)
    }
    return sorted(value for value in rounds if value > 0)


def resolve_watch_round_index(schedule_rows: list[dict[str, str]], requested_round: int) -> int | None:
    incomplete_rounds = get_incomplete_rounds(schedule_rows)
    if not incomplete_rounds:
        return None
    if requested_round > 0:
        if requested_round not in incomplete_rounds:
            raise SystemExit(
                f"--round-index={requested_round} is not an incomplete round in schedule.csv. "
                f"Available incomplete rounds: {','.join(str(value) for value in incomplete_rounds)}"
            )
        return requested_round
    if len(incomplete_rounds) > 1:
        raise SystemExit(
            "--watch-header-only requires --round-index when schedule.csv contains multiple incomplete rounds: "
            + ",".join(str(value) for value in incomplete_rounds)
        )
    return incomplete_rounds[0]


def resolve_lint_round_indexes(schedule_rows: list[dict[str, str]], requested_round: int) -> list[int]:
    available_rounds = sorted(
        {
            parse_optional_int(row.get("round_index"), default=0)
            for row in schedule_rows
            if parse_optional_int(row.get("round_index"), default=0) > 0
        }
    )
    if requested_round > 0:
        if requested_round not in available_rounds:
            raise SystemExit(
                f"--round-index={requested_round} is not present in schedule.csv. "
                f"Available rounds: {','.join(str(value) for value in available_rounds)}"
            )
        return [requested_round]

    completed_rounds: list[int] = []
    for round_index in available_rounds:
        round_rows = [
            row for row in schedule_rows if parse_optional_int(row.get("round_index"), default=0) == round_index
        ]
        if round_rows and all(is_resolved_runtime_row(row) for row in round_rows):
            completed_rounds.append(round_index)
        else:
            break
    if completed_rounds:
        return completed_rounds

    watch_round_index = resolve_watch_round_index(schedule_rows, 0)
    return [watch_round_index] if watch_round_index is not None else []


def parse_task_index(row: dict[str, str], source: Path) -> int:
    raw = (row.get("task_index") or "").strip()
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Invalid task_index in {source}: {raw!r}") from None


def parse_batch_number(batch_file: str) -> int:
    stem = Path(batch_file).stem
    try:
        return int(stem.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def compute_checkpoint_batch_stats(schedule_rows: list[dict[str, str]]) -> dict[str, int]:
    batch_numbers = sorted(
        {
            parse_batch_number(row.get("batch_file", ""))
            for row in schedule_rows
            if parse_batch_number(row.get("batch_file", "")) > 0
        }
    )
    if not batch_numbers:
        return {
            "window_start_batch": 1,
            "contiguous_completed_through_batch": 0,
            "next_missing_batch": 1,
            "pending_batch_count": 0,
        }
    resolved_numbers = {
        parse_batch_number(row.get("batch_file", ""))
        for row in schedule_rows
        if parse_batch_number(row.get("batch_file", "")) > 0 and is_resolved_runtime_row(row)
    }
    window_start_batch = batch_numbers[0]
    contiguous = window_start_batch - 1
    next_missing = window_start_batch
    for batch_number in batch_numbers:
        expected_next = contiguous + 1
        if batch_number != expected_next:
            next_missing = expected_next
            break
        if batch_number not in resolved_numbers:
            next_missing = expected_next
            break
        contiguous = batch_number
        next_missing = contiguous + 1
    pending_count = sum(1 for batch_number in batch_numbers if batch_number not in resolved_numbers)
    return {
        "window_start_batch": window_start_batch,
        "contiguous_completed_through_batch": contiguous,
        "next_missing_batch": next_missing,
        "pending_batch_count": pending_count,
    }


def path_within(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_json_list(value: str) -> bool:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def json_list_length(value: str) -> int:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return -1
    return len(parsed) if isinstance(parsed, list) else -1


def normalize_confidence_value(value: object) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return raw
    if raw in ALLOWED_CONFIDENCE:
        return raw
    try:
        numeric = float(raw)
    except ValueError:
        return raw
    if numeric >= 0.8:
        return "high"
    if numeric >= 0.5:
        return "medium"
    return "low"


def normalize_risk_flags_value(value: object) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw or raw.lower() == "none":
        return "[]"
    if validate_json_list(raw):
        return raw
    if "|" in raw:
        flags = [part.strip() for part in raw.split("|") if part.strip()]
    else:
        flags = [raw]
    return json.dumps(flags, ensure_ascii=False)


def normalize_json_list_string(value: object) -> str:
    raw = "" if value is None else str(value).strip()
    if not raw:
        return ""
    if validate_json_list(raw):
        try:
            return json.dumps(json.loads(raw), ensure_ascii=False, separators=(",", ":"))
        except json.JSONDecodeError:
            return raw
    repaired_candidates: list[str] = []
    repaired = raw.replace('""', '"')
    if repaired != raw:
        repaired_candidates.append(repaired)
        if repaired.endswith('"'):
            repaired_candidates.append(repaired[:-1])
    if raw.startswith('"') and raw.endswith('"'):
        try:
            inner = json.loads(raw)
        except json.JSONDecodeError:
            inner = None
        if isinstance(inner, str):
            repaired_candidates.append(inner)
    for candidate in repaired_candidates:
        candidate = candidate.strip()
        if not candidate:
            continue
        if validate_json_list(candidate):
            try:
                return json.dumps(json.loads(candidate), ensure_ascii=False, separators=(",", ":"))
            except json.JSONDecodeError:
                continue
    return raw


ISO_8601_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def looks_like_iso_8601_utc(value: object) -> bool:
    raw = "" if value is None else str(value).strip()
    return bool(ISO_8601_UTC_PATTERN.match(raw))


def looks_like_http_pipe_list(value: object) -> bool:
    raw = "" if value is None else str(value).strip()
    if not raw or "|" not in raw:
        return False
    parts = split_pipe_list(raw)
    return bool(parts) and all(part.startswith(("http://", "https://")) for part in parts)


def looks_like_source_type_pipe_list(value: object) -> bool:
    raw = "" if value is None else str(value).strip()
    if not raw or "|" not in raw:
        return False
    parts = split_pipe_list(raw)
    return bool(parts) and all(SOURCE_TYPE_PATTERN.match(part) for part in parts)


def repair_shifted_result_row(row: dict[str, str]) -> dict[str, str]:
    repaired = dict(row)

    search_required = (repaired.get("capability_search_required") or "").strip()
    search_reason = (repaired.get("capability_search_reason") or "").strip()
    if search_required in {"light", "deep", "skip_candidate"} and search_reason in ALLOWED_YES_NO:
        repaired["capability_search_required"], repaired["capability_search_reason"] = search_reason, search_required

    if (repaired.get("status") or "").strip() != "completed" and (repaired.get("capability_labels") or "").strip() == "completed":
        repaired["status"] = "completed"
        repaired["capability_labels"] = "[]"

    if looks_like_http_pipe_list(repaired.get("confidence", "")) and not split_pipe_list(repaired.get("evidence_urls", "")):
        repaired["evidence_urls"] = (repaired.get("confidence") or "").strip()
        repaired["confidence"] = "low"

    if looks_like_source_type_pipe_list(repaired.get("needs_manual_review", "")) and not split_pipe_list(repaired.get("evidence_source_types", "")):
        repaired["evidence_source_types"] = (repaired.get("needs_manual_review") or "").strip()
        repaired["needs_manual_review"] = "yes"

    for column in LIST_COLUMNS:
        repaired[column] = normalize_json_list_string(repaired.get(column, ""))
    for column in CAPABILITY_FLAG_COLUMNS:
        if (repaired.get(column) or "").strip() not in ALLOWED_YES_NO:
            repaired[column] = "no"
    ensure_capability_labels(repaired)

    return repaired


def normalize_result_row_payload(payload: dict) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for column in RESULT_CSV_COLUMNS:
        value = payload.get(column, "")
        if value is None:
            normalized[column] = ""
        elif column == "confidence":
            normalized[column] = normalize_confidence_value(value)
        elif column in LIST_COLUMNS and isinstance(value, list):
            normalized[column] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        elif column in LIST_COLUMNS:
            normalized[column] = normalize_json_list_string(value)
        else:
            normalized[column] = str(value)
    for column in CAPABILITY_FLAG_COLUMNS:
        normalized[column] = str(payload.get(column, normalized.get(column, "no")) or "no")
    ensure_capability_labels(normalized)
    return normalized


def parse_corrected_result_row(
    value: str,
    source: Path,
    task_index: int,
) -> tuple[dict[str, str] | None, list[str]]:
    raw = (value or "").strip()
    if not raw:
        return None, [f"{source}: task_index={task_index}: edit_row requires corrected_result_row_json"]
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, [f"{source}: task_index={task_index}: corrected_result_row_json is not valid JSON"]
    if not isinstance(parsed, dict):
        return None, [f"{source}: task_index={task_index}: corrected_result_row_json must be a JSON object"]

    missing = [column for column in RESULT_CSV_COLUMNS if column not in parsed]
    if missing:
        return None, [
            f"{source}: task_index={task_index}: corrected_result_row_json is missing columns "
            + ",".join(missing)
        ]

    normalized = normalize_result_row_payload(parsed)
    errors = validate_result_row(normalized, source)
    return normalized, errors


def validate_result_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    for column in LIST_COLUMNS:
        value = (row.get(column) or "").strip()
        if not value:
            errors.append(f"{column} is blank")
        elif not validate_json_list(value):
            errors.append(f"{column} is not a valid JSON list: {value!r}")

    if row.get("status") != "completed":
        errors.append("status must be completed")
    if row.get("investor_archetype") not in ALLOWED_INVESTOR_ARCHETYPES:
        errors.append("investor_archetype uses an invalid value")
    if row.get("crypto_native_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("crypto_native_likelihood uses an invalid value")
    if row.get("operating_capability_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("operating_capability_likelihood uses an invalid value")
    if row.get("search_tier") not in ALLOWED_SEARCH_TIERS:
        errors.append("search_tier uses an invalid value")
    if row.get("capability_search_required") not in ALLOWED_YES_NO:
        errors.append("capability_search_required must be yes or no")
    if row.get("needs_manual_review") not in ALLOWED_YES_NO:
        errors.append("needs_manual_review must be yes or no")
    if row.get("confidence") not in ALLOWED_CONFIDENCE:
        errors.append("confidence must be high, medium, or low")
    if row.get("search_tier") in {"full", "light"} and row.get("capability_search_required") != "yes":
        errors.append("full/light search_tier requires capability_search_required=yes")
    if row.get("search_tier") == "skip_candidate" and row.get("capability_search_required") != "no":
        errors.append("skip_candidate requires capability_search_required=no")
    if row.get("capability_search_required") == "no" and not (row.get("capability_search_reason") or "").strip():
        errors.append("capability_search_required=no requires capability_search_reason")
    for column in CAPABILITY_FLAG_COLUMNS:
        if row.get(column) not in ALLOWED_YES_NO:
            errors.append(f"{column} must be yes or no")
    evidence_summary = (row.get("evidence_summary") or "").strip()
    evidence_urls = split_pipe_list(row.get("evidence_urls", ""))
    evidence_source_types = split_pipe_list(row.get("evidence_source_types", ""))
    if not evidence_summary:
        errors.append("evidence_summary is blank")
    if (row.get("capability_search_required") or "").strip() == "yes":
        if not evidence_urls:
            errors.append("searched rows require non-empty evidence_urls")
        if not evidence_source_types:
            errors.append("searched rows require non-empty evidence_source_types")
        if evidence_summary.lower() in {"yes", "no"}:
            errors.append("searched rows must summarize evidence in evidence_summary, not bare yes/no")
    if (row.get("evidence_urls") or "").strip():
        invalid_urls = [
            value for value in evidence_urls if not value.startswith(("http://", "https://"))
        ]
        if invalid_urls:
            errors.append("evidence_urls contains non-http values")
    if (row.get("evidence_source_types") or "").strip():
        invalid_source_types = [
            value for value in evidence_source_types if not SOURCE_TYPE_PATTERN.match(value)
        ]
        if invalid_source_types:
            errors.append("evidence_source_types contains invalid labels")

    label_values = parse_json_list(row.get("capability_labels", ""))
    expected_labels = capability_labels_from_row(row)
    if label_values != expected_labels:
        errors.append("capability_labels must match the yes-valued capability columns")
    if label_values:
        if not evidence_urls:
            errors.append("capability-positive rows require evidence_urls")
        if not evidence_source_types:
            errors.append("capability-positive rows require evidence_source_types")
        if evidence_summary.lower() in {"", "no", "none", "false"}:
            errors.append("capability-positive rows require affirmative evidence_summary summary")
    if not label_values and (row.get("capability_search_required") or "").strip() == "yes":
        if evidence_summary.lower() == "yes":
            errors.append("capability-negative searched rows cannot use bare yes in evidence_summary")

    if errors:
        task_index = row.get("task_index", "")
        investor_name = row.get("investor_name", "")
        return [f"{source}: task_index={task_index} investor={investor_name}: {error}" for error in errors]
    return []


def validate_classifier_row(row: dict[str, str], source: Path) -> list[str]:
    errors: list[str] = []
    if row.get("investor_archetype") not in ALLOWED_INVESTOR_ARCHETYPES:
        errors.append("investor_archetype uses an invalid value")
    if row.get("crypto_native_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("crypto_native_likelihood uses an invalid value")
    if row.get("operating_capability_likelihood") not in ALLOWED_LIKELIHOODS:
        errors.append("operating_capability_likelihood uses an invalid value")
    search_tier = row.get("search_tier")
    capability_search_required = row.get("capability_search_required")
    if search_tier not in ALLOWED_SEARCH_TIERS:
        errors.append("search_tier uses an invalid value")
    if capability_search_required not in ALLOWED_YES_NO:
        errors.append("capability_search_required must be yes or no")
    if search_tier in {"full", "light"} and capability_search_required != "yes":
        errors.append("full/light search_tier requires capability_search_required=yes")
    if search_tier == "skip_candidate" and capability_search_required != "no":
        errors.append("skip_candidate requires capability_search_required=no")
    if search_tier == "skip_candidate" and row.get("crypto_native_likelihood") in {"high", "medium", "unclear"}:
        errors.append("skip_candidate cannot have high, medium, or unclear likelihood")
    risk_flags = (row.get("risk_flags") or "").strip()
    if not risk_flags:
        errors.append("risk_flags is blank")
    elif not validate_json_list(risk_flags):
        errors.append(f"risk_flags is not a valid JSON list: {risk_flags!r}")
    if not (row.get("classifier_reason") or "").strip():
        errors.append("classifier_reason is blank")

    if errors:
        task_index = row.get("task_index", "")
        investor_name = row.get("investor_name", "")
        return [f"{source}: task_index={task_index} investor={investor_name}: {error}" for error in errors]
    return []


def collect_classifier_rows(
    schedule_rows: list[dict[str, str]],
    identity_override_tracker: dict[str, object] | None = None,
) -> tuple[list[dict[str, str]], list[str], dict[int, dict[str, str]]]:
    classifier_rows: list[dict[str, str]] = []
    validation_errors: list[str] = []
    seen_task_indexes: set[int] = set()
    duplicate_task_indexes: set[int] = set()

    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        tasks_file_raw = (schedule_row.get("tasks_file") or "").strip()
        if not tasks_file_raw:
            validation_errors.append(f"{schedule_row.get('batch_file')}: missing tasks_file in schedule")
            continue
        tasks_file = ensure_file(resolve_path(tasks_file_raw), "Tasks JSONL")
        tasks_by_index = build_tasks_by_index(tasks_file)
        classifier_raw = (schedule_row.get("classifier_results_csv") or "").strip()
        if not classifier_raw:
            validation_errors.append(f"{schedule_row.get('batch_file')}: missing classifier_results_csv in schedule")
            continue
        classifier_csv = ensure_file(resolve_path(classifier_raw), "Classifier results CSV")
        header, rows = load_csv(classifier_csv)
        if header != CLASSIFIER_CSV_COLUMNS:
            validation_errors.append(f"{classifier_csv}: header mismatch")
        if len(rows) != task_count:
            validation_errors.append(f"{classifier_csv}: expected {task_count} rows, found {len(rows)}")
        for row in rows:
            task_index = parse_task_index(row, classifier_csv)
            task = tasks_by_index.get(task_index)
            if not task:
                validation_errors.append(
                    f"{classifier_csv}: task_index={task_index}: missing task row in {tasks_file}"
                )
                continue
            row = canonicalize_identity_fields(row, task, classifier_csv, identity_override_tracker)
            row = canonicalize_classifier_row(row)
            if task_index in seen_task_indexes:
                duplicate_task_indexes.add(task_index)
            seen_task_indexes.add(task_index)
            validation_errors.extend(validate_classifier_row(row, classifier_csv))
            if requires_search_guarantee(schedule_row):
                if row.get("search_tier") == "skip_candidate":
                    validation_errors.append(
                        f"{classifier_csv}: task_index={task_index}: search-guarantee rerun batches forbid search_tier=skip_candidate"
                    )
                if row.get("capability_search_required") != "yes":
                    validation_errors.append(
                        f"{classifier_csv}: task_index={task_index}: search-guarantee rerun batches require capability_search_required=yes"
                    )
            classifier_rows.append({column: row.get(column, "") for column in CLASSIFIER_CSV_COLUMNS})

    if duplicate_task_indexes:
        validation_errors.append(
            "Duplicate classifier task_index values: "
            + ",".join(str(value) for value in sorted(duplicate_task_indexes))
        )

    classifier_rows.sort(key=lambda row: int(row["task_index"]))
    return classifier_rows, validation_errors, {int(row["task_index"]): row for row in classifier_rows}


def validate_row_order_against_tasks(
    schedule_row: dict[str, str],
    rows: list[dict[str, str]],
    results_csv: Path,
) -> list[str]:
    validation_errors: list[str] = []
    tasks_file_raw = (schedule_row.get("tasks_file") or "").strip()
    if not tasks_file_raw:
        validation_errors.append(f"{results_csv}: missing tasks_file in schedule")
        return validation_errors

    tasks_file = ensure_file(resolve_path(tasks_file_raw), "Tasks JSONL")
    tasks = load_tasks_jsonl(tasks_file)
    compare_count = min(len(tasks), len(rows))
    for index in range(compare_count):
        task = tasks[index]
        row = rows[index]
        expected_task_index = str(task.get("task_index", ""))
        actual_task_index = (row.get("task_index") or "").strip()
        if actual_task_index != expected_task_index:
            expected_investor_name = str(task.get("investor_name", ""))
            actual_investor_name = (row.get("investor_name") or "").strip()
            validation_errors.append(
                f"{results_csv}: row {index + 2}: expected "
                f"task_index={expected_task_index} company={expected_investor_name!r}, found "
                f"task_index={actual_task_index} company={actual_investor_name!r}"
            )
    return validation_errors


def canonicalize_result_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {column: row.get(column, "") for column in RESULT_CSV_COLUMNS}
    if normalized.get("status") == "complete":
        normalized["status"] = "completed"
    normalized["confidence"] = normalize_confidence_value(normalized.get("confidence", ""))
    for column in LIST_COLUMNS:
        normalized[column] = normalize_json_list_string(normalized.get(column, ""))
    normalized = repair_shifted_result_row(normalized)
    normalized["confidence"] = normalize_confidence_value(normalized.get("confidence", ""))
    return normalized


def canonicalize_classifier_row(row: dict[str, str]) -> dict[str, str]:
    normalized = {column: row.get(column, "") for column in CLASSIFIER_CSV_COLUMNS}
    normalized["risk_flags"] = normalize_risk_flags_value(normalized.get("risk_flags", ""))
    return normalized


def requires_search_guarantee(schedule_row: dict[str, str]) -> bool:
    markers = [
        str(schedule_row.get("batch_file") or ""),
        str(schedule_row.get("run_dir") or ""),
        str(schedule_row.get("tasks_file") or ""),
    ]
    return any("rerun_manual_fallbacks" in marker for marker in markers)


def collect_worker_rows(
    schedule_rows: list[dict[str, str]],
    classifier_rows_by_task: dict[int, dict[str, str]],
    identity_override_tracker: dict[str, object] | None = None,
) -> tuple[list[dict[str, str]], list[str], int]:
    merged_rows: list[dict[str, str]] = []
    validation_errors: list[str] = []
    expected_total = 0
    duplicate_task_indexes: set[int] = set()
    seen_task_indexes: set[int] = set()

    for schedule_row in schedule_rows:
        task_count = int(schedule_row.get("task_count") or 0)
        expected_total += task_count
        tasks_file = ensure_file(resolve_path(schedule_row["tasks_file"]), "Tasks JSONL")
        tasks_by_index = build_tasks_by_index(tasks_file)
        results_csv = ensure_file(resolve_path(schedule_row["results_csv"]), "Worker results CSV")
        header, rows = load_csv(results_csv)
        if header != RESULT_CSV_COLUMNS:
            validation_errors.append(f"{results_csv}: header mismatch")
        if len(rows) != task_count:
            validation_errors.append(f"{results_csv}: expected {task_count} rows, found {len(rows)}")
        validation_errors.extend(validate_row_order_against_tasks(schedule_row, rows, results_csv))
        for row in rows:
            row = canonicalize_result_row(row)
            task_index = parse_task_index(row, results_csv)
            task = tasks_by_index.get(task_index)
            if not task:
                validation_errors.append(
                    f"{results_csv}: task_index={task_index}: missing task row in {tasks_file}"
                )
                continue
            row = canonicalize_identity_fields(row, task, results_csv, identity_override_tracker)
            if task_index in seen_task_indexes:
                duplicate_task_indexes.add(task_index)
            seen_task_indexes.add(task_index)
            validation_errors.extend(validate_result_row(row, results_csv))
            if requires_search_guarantee(schedule_row) and row.get("capability_search_required") != "yes":
                validation_errors.append(
                    f"{results_csv}: task_index={task_index}: search-guarantee rerun batches require capability_search_required=yes"
                )
            classifier_row = classifier_rows_by_task.get(task_index)
            if not classifier_row:
                validation_errors.append(f"{results_csv}: task_index={task_index}: missing classifier row")
            else:
                for column in ["investor_archetype", "crypto_native_likelihood", "capability_search_required"]:
                    if row.get(column) != classifier_row.get(column):
                        validation_errors.append(
                            f"{results_csv}: task_index={task_index}: {column} does not match classifier_results.csv"
                        )
            merged_rows.append({column: row.get(column, "") for column in RESULT_CSV_COLUMNS})

    if duplicate_task_indexes:
        validation_errors.append(
            "Duplicate task_index values: "
            + ",".join(str(value) for value in sorted(duplicate_task_indexes))
        )

    merged_rows.sort(key=lambda row: int(row["task_index"]))
    return merged_rows, validation_errors, expected_total


def collect_verification_rows(
    schedule_rows: list[dict[str, str]],
    worker_rows_by_task: dict[int, dict[str, str]],
    classifier_rows_by_task: dict[int, dict[str, str]],
    skip_verification: bool,
    allow_unresolved_verification: bool,
    identity_override_tracker: dict[str, object] | None = None,
) -> tuple[list[dict[str, str]], list[str]]:
    if skip_verification:
        return [], []

    validation_errors: list[str] = []
    report_to_expected_tasks: dict[Path, dict[int, dict]] = {}
    report_to_summary: dict[Path, Path] = {}

    for schedule_row in schedule_rows:
        report_raw = (schedule_row.get("verification_report_csv") or "").strip()
        summary_raw = (schedule_row.get("verification_summary_md") or "").strip()
        if not report_raw:
            validation_errors.append(f"{schedule_row.get('batch_file')}: missing verification_report_csv in schedule")
            continue
        report_path = resolve_path(report_raw)
        report_to_expected_tasks.setdefault(report_path, {})
        report_to_summary[report_path] = resolve_path(summary_raw) if summary_raw else Path()
        tasks_file_raw = (schedule_row.get("tasks_file") or "").strip()
        if not tasks_file_raw:
            validation_errors.append(f"{schedule_row.get('batch_file')}: missing tasks_file in schedule")
            continue
        tasks_file = ensure_file(resolve_path(tasks_file_raw), "Tasks JSONL")
        for task_index, task in build_tasks_by_index(tasks_file).items():
            report_to_expected_tasks[report_path][task_index] = task

    all_verifier_rows: list[dict[str, str]] = []
    for report_path, expected_tasks_by_index in sorted(report_to_expected_tasks.items()):
        expected_tasks = set(expected_tasks_by_index)
        report = ensure_file(report_path, "Verification report CSV")
        summary = report_to_summary.get(report_path)
        if summary and not summary.exists():
            validation_errors.append(f"{summary}: missing verification_summary.md")

        header, rows = load_csv(report)
        if header != VERIFICATION_CSV_COLUMNS:
            validation_errors.append(f"{report}: header mismatch")
        scoped_rows = [
            row
            for row in rows
            if parse_optional_int(row.get("task_index"), default=0) in expected_tasks
        ]
        if len(scoped_rows) != len(expected_tasks):
            validation_errors.append(
                f"{report}: expected {len(expected_tasks)} verifier rows for scoped tasks, found {len(scoped_rows)}"
            )

        seen_report_tasks: set[int] = set()
        for row in scoped_rows:
            task_index = parse_task_index(row, report)
            seen_report_tasks.add(task_index)
            expected_task = expected_tasks_by_index.get(task_index)
            verdict = (row.get("verdict") or "").strip()
            action = (row.get("recommended_action") or "").strip()
            classifier_search_tier = (row.get("classifier_search_tier") or "").strip()
            verifier_search_tier = (row.get("verifier_search_tier") or "").strip()
            if verdict not in ALLOWED_VERDICTS:
                validation_errors.append(f"{report}: task_index={task_index}: invalid verdict {verdict!r}")
            if action not in ALLOWED_VERIFICATION_ACTIONS:
                validation_errors.append(f"{report}: task_index={task_index}: invalid recommended_action {action!r}")
            if classifier_search_tier not in ALLOWED_SEARCH_TIERS:
                validation_errors.append(
                    f"{report}: task_index={task_index}: invalid classifier_search_tier {classifier_search_tier!r}"
                )
            classifier_row = classifier_rows_by_task.get(task_index)
            if classifier_row and classifier_search_tier != (classifier_row.get("search_tier") or "").strip():
                validation_errors.append(
                    f"{report}: task_index={task_index}: classifier_search_tier does not match classifier_results.csv"
                )
            if verifier_search_tier not in ALLOWED_SEARCH_TIERS:
                validation_errors.append(
                    f"{report}: task_index={task_index}: invalid verifier_search_tier {verifier_search_tier!r}"
                )
            if verdict == "pass" and action != "accept_worker_row":
                validation_errors.append(f"{report}: task_index={task_index}: pass verdict must use accept_worker_row")
            if verdict != "pass" and not (row.get("error_reason") or "").strip():
                validation_errors.append(f"{report}: task_index={task_index}: non-pass verdict requires error_reason")
            if action == "edit_row":
                corrected_row, corrected_errors = parse_corrected_result_row(
                    row.get("corrected_result_row_json", ""),
                    report,
                    task_index,
                )
                validation_errors.extend(corrected_errors)
                if corrected_row:
                    if expected_task:
                        corrected_row["task_index"] = str(expected_task.get("task_index", task_index))
                        corrected_row["investor_id"] = str(expected_task.get("investor_id", ""))
                        corrected_row["investor_name"] = str(expected_task.get("investor_name", ""))
                        corrected_row["normalized_domain"] = str(expected_task.get("normalized_domain", ""))
                    if classifier_row:
                        for column in ["investor_archetype", "crypto_native_likelihood", "capability_search_required"]:
                            corrected_row[column] = classifier_row.get(column, "")
                    row["corrected_result_row_json"] = json.dumps(
                        corrected_row,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    if corrected_row.get("task_index") != str(task_index):
                        validation_errors.append(
                            f"{report}: task_index={task_index}: corrected_result_row_json task_index mismatch"
                        )
                    expected_investor_id = (
                        str(expected_task.get("investor_id", ""))
                        if expected_task
                        else (row.get("investor_id") or "")
                    )
                    if corrected_row.get("investor_id") != expected_investor_id:
                        validation_errors.append(
                            f"{report}: task_index={task_index}: corrected_result_row_json investor_id mismatch"
                        )
                    verifier_capability_labels = normalize_json_list_string(row.get("verifier_capability_labels", ""))
                    corrected_capability_labels = normalize_json_list_string(corrected_row.get("capability_labels", ""))
                    if verifier_capability_labels and corrected_capability_labels != verifier_capability_labels:
                        validation_errors.append(
                            f"{report}: task_index={task_index}: corrected_result_row_json capability_labels must match verifier_capability_labels"
                        )
            if not allow_unresolved_verification and action in BLOCKING_VERIFICATION_ACTIONS:
                worker_row = worker_rows_by_task.get(task_index)
                edit_resolved = (
                    action == "edit_row"
                    and bool((row.get("corrected_result_row_json") or "").strip())
                )
                if not edit_resolved:
                    validation_errors.append(
                        f"{report}: task_index={task_index}: verifier action {action} blocks merge until resolved"
                    )
            verifier_row = {column: row.get(column, "") for column in VERIFICATION_CSV_COLUMNS}
            if expected_task:
                verifier_row = canonicalize_identity_fields(
                    verifier_row,
                    expected_task,
                    report,
                    identity_override_tracker,
                )
            all_verifier_rows.append(verifier_row)

        missing = expected_tasks - seen_report_tasks
        if missing:
            validation_errors.append(
                f"{report}: missing verifier rows for task_index "
                + ",".join(str(value) for value in sorted(missing)[:20])
            )

    all_verifier_rows.sort(key=lambda row: int(row["task_index"]))
    return all_verifier_rows, validation_errors


def apply_verifier_review_decisions(
    worker_rows: list[dict[str, str]],
    verifier_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    if not verifier_rows:
        return worker_rows

    verifier_by_task = {
        int(row["task_index"]): row
        for row in verifier_rows
    }
    updated_rows: list[dict[str, str]] = []

    for row in worker_rows:
        task_index = int(row["task_index"])
        verifier_row = verifier_by_task.get(task_index)
        updated_row = dict(row)
        if verifier_row:
            action = (verifier_row.get("recommended_action") or "").strip()

            if action == "mark_manual_review":
                updated_row["needs_manual_review"] = "yes"
            elif action == "accept_worker_row":
                # Preserve worker/manual-review state unless the verifier explicitly
                # resolves it via an edited row or mark_manual_review decision.
                updated_row["needs_manual_review"] = updated_row.get("needs_manual_review", "no") or "no"
            elif action == "edit_row":
                corrected_row, corrected_errors = parse_corrected_result_row(
                    verifier_row.get("corrected_result_row_json", ""),
                    Path("<verification-report>"),
                    task_index,
                )
                if corrected_row and not corrected_errors:
                    updated_row = corrected_row

        updated_rows.append(updated_row)

    return updated_rows


def validate_rows_against_classifier(
    rows: list[dict[str, str]],
    classifier_rows_by_task: dict[int, dict[str, str]],
    source_label: str,
) -> list[str]:
    validation_errors: list[str] = []
    for row in rows:
        task_index = int(row["task_index"])
        classifier_row = classifier_rows_by_task.get(task_index)
        if not classifier_row:
            validation_errors.append(f"{source_label}: task_index={task_index}: missing classifier row")
            continue
        for column in ["investor_archetype", "crypto_native_likelihood", "capability_search_required"]:
            if row.get(column) != classifier_row.get(column):
                validation_errors.append(
                    f"{source_label}: task_index={task_index}: {column} does not match classifier_results.csv"
                )
    return validation_errors


def load_existing_results(path: Path, replace_output: bool) -> list[dict[str, str]]:
    if replace_output or not path.exists():
        return []
    header, rows = load_csv(path)
    if header != RESULT_CSV_COLUMNS:
        raise SystemExit(
            f"Existing output CSV is not v2 schema: {path}. "
            "Use --replace-output or write to a different --output-csv."
        )
    return [{column: row.get(column, "") for column in RESULT_CSV_COLUMNS} for row in rows]


def load_existing_classifier_results(path: Path, replace_output: bool) -> list[dict[str, str]]:
    if replace_output or not path.exists():
        return []
    header, rows = load_csv(path)
    if header != CLASSIFIER_CSV_COLUMNS:
        raise SystemExit(
            f"Existing classifier CSV is not current schema: {path}. "
            "Use --replace-output or write to a different --classifier-results-csv."
    )
    return [{column: row.get(column, "") for column in CLASSIFIER_CSV_COLUMNS} for row in rows]


def load_existing_verification_findings(path: Path, replace_output: bool) -> list[dict[str, str]]:
    if replace_output or not path.exists():
        return []
    header, rows = load_csv(path)
    if header != VERIFICATION_CSV_COLUMNS:
        raise SystemExit(
            f"Existing verification findings CSV is not current schema: {path}. "
            "Use --replace-output or write to a different --verification-findings-csv."
        )
    return [{column: row.get(column, "") for column in VERIFICATION_CSV_COLUMNS} for row in rows]


def merge_existing_and_new(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[int]]:
    overwritten_task_indexes: list[int] = []
    rows_by_task: dict[int, dict[str, str]] = {}
    for row in existing_rows:
        rows_by_task[parse_task_index(row, Path("<existing-output>"))] = row
    for row in new_rows:
        task_index = parse_task_index(row, Path("<new-output>"))
        if task_index in rows_by_task:
            overwritten_task_indexes.append(task_index)
        rows_by_task[task_index] = row
    overwritten_task_indexes = sorted(set(overwritten_task_indexes))
    return [rows_by_task[index] for index in sorted(rows_by_task)], overwritten_task_indexes


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_generic_csv(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    write_csv(path, list(rows[0].keys()), rows)


def write_schedule_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        return
    write_schedule_csv(path, rows, fieldnames=list(rows[0].keys()))


def rewrite_identity_fields_in_place(schedule_rows: list[dict[str, str]]) -> list[str]:
    repaired_files: list[str] = []

    for schedule_row in schedule_rows:
        tasks_file_raw = (schedule_row.get("tasks_file") or "").strip()
        if not tasks_file_raw:
            continue
        tasks = load_tasks_jsonl(ensure_file(resolve_path(tasks_file_raw), "Tasks JSONL"))

        for key, expected_header in [
            ("classifier_results_csv", CLASSIFIER_CSV_COLUMNS),
            ("results_csv", RESULT_CSV_COLUMNS),
        ]:
            csv_raw = (schedule_row.get(key) or "").strip()
            if not csv_raw:
                continue
            csv_path = ensure_file(resolve_path(csv_raw), "Scheduled CSV")
            header, rows = load_csv(csv_path)
            if header != expected_header:
                continue
            if not rows or not tasks:
                continue

            updated_rows: list[dict[str, str]] = []
            changed = False
            for index, row in enumerate(rows):
                updated = dict(row)
                if index < len(tasks):
                    task = tasks[index]
                    for field in ["task_index", "investor_id", "investor_name"]:
                        expected = str(task.get(field, updated.get(field, "")))
                        if str(updated.get(field, "")) != expected:
                            changed = True
                        updated[field] = expected
                    if "normalized_domain" in updated:
                        expected_domain = str(
                            task.get("normalized_domain", updated.get("normalized_domain", ""))
                        )
                        if str(updated.get("normalized_domain", "")) != expected_domain:
                            changed = True
                        updated["normalized_domain"] = expected_domain
                updated_rows.append({column: updated.get(column, "") for column in header})

            if changed:
                write_csv(csv_path, header, updated_rows)
                repaired_files.append(str(csv_path))

    return repaired_files


def extract_source_label(error: str) -> str | None:
    if error.startswith("<post-verifier-output>"):
        return "<post-verifier-output>"
    if error.startswith("identity_drift: "):
        remainder = error[len("identity_drift: ") :]
        return remainder.split(":", 1)[0].strip() or None
    if error.startswith("/") or error.startswith("<"):
        return error.split(":", 1)[0].strip() or None
    return None


def extract_task_index_from_error(error: str) -> int | None:
    match = re.search(r"task_index=(\d+)", error)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def build_task_index_to_schedule_row(schedule_rows: list[dict[str, str]]) -> dict[int, dict[str, str]]:
    mapping: dict[int, dict[str, str]] = {}
    for row in schedule_rows:
        try:
            first = int(row.get("first_task_index") or 0)
            last = int(row.get("last_task_index") or 0)
        except ValueError:
            continue
        for task_index in range(first, last + 1):
            mapping[task_index] = row
    return mapping


def build_source_to_schedule_row(schedule_rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    mapping: dict[str, dict[str, str]] = {}
    for row in schedule_rows:
        for key in [
            "classifier_results_csv",
            "results_csv",
            "verification_report_csv",
            "tasks_file",
        ]:
            raw = (row.get(key) or "").strip()
            if not raw:
                continue
            mapping[str(resolve_path(raw))] = row
    return mapping


def infer_rerun_category(error: str) -> str | None:
    if "header mismatch" in error:
        return "header_mismatch"
    if "expected " in error and " rows, found " in error:
        return "row_count_mismatch"
    if ": row " in error and "expected task_index=" in error:
        return "row_order_mismatch"
    if "task_index=" in error:
        schema_markers = (
            "is not a valid JSON list",
            "status must be",
            "needs_manual_review must be",
            "confidence must be",
            "skip_candidate cannot have",
            "contains non-http values",
            "contains invalid labels",
            "has invalid",
            "must be yes or no",
            "must be high, medium, or low",
            "does not match classifier_results.csv",
        )
        if any(marker in error for marker in schema_markers):
            return "schema_error"
    return None


def analyze_lint_failures(
    schedule_rows: list[dict[str, str]],
    validation_errors: list[str],
) -> list[dict[str, str]]:
    if not validation_errors:
        return []

    source_to_schedule = build_source_to_schedule_row(schedule_rows)
    task_index_to_schedule = build_task_index_to_schedule_row(schedule_rows)
    by_batch: dict[str, dict[str, object]] = {}

    def ensure_bucket(schedule_row: dict[str, str]) -> dict[str, object]:
        batch_key = str(schedule_row.get("batch_file") or "")
        bucket = by_batch.setdefault(
            batch_key,
            {
                "row": schedule_row,
                "categories": set(),
                "error_count": 0,
                "samples": [],
                "row_level_error_count": 0,
            },
        )
        return bucket

    for error in validation_errors:
        schedule_row: dict[str, str] | None = None
        source_label = extract_source_label(error)
        if source_label and source_label in source_to_schedule:
            schedule_row = source_to_schedule[source_label]
        else:
            task_index = extract_task_index_from_error(error)
            if task_index is not None:
                schedule_row = task_index_to_schedule.get(task_index)
        if not schedule_row:
            continue

        bucket = ensure_bucket(schedule_row)
        bucket["error_count"] = int(bucket["error_count"]) + 1
        samples = bucket["samples"]
        if isinstance(samples, list) and len(samples) < 5:
            samples.append(error)

        category = infer_rerun_category(error)
        if category:
            categories = bucket["categories"]
            if isinstance(categories, set):
                categories.add(category)
        elif source_label and source_label.startswith("/") and "task_index=" in error:
            bucket["row_level_error_count"] = int(bucket["row_level_error_count"]) + 1

    rerun_rows: list[dict[str, str]] = []
    for batch_key, bucket in by_batch.items():
        categories = set(bucket.get("categories", set()))
        row_level_error_count = int(bucket.get("row_level_error_count", 0))
        if row_level_error_count >= 8:
            categories.add("severe_schema_error")
        if not categories:
            continue

        schedule_row = dict(bucket["row"])
        reasons = sorted(categories)
        rerun_rows.append(
            {
                "batch_file": batch_key,
                "run_dir": str(schedule_row.get("run_dir") or ""),
                "status": "needs_rerun",
                "first_task_index": str(schedule_row.get("first_task_index") or ""),
                "last_task_index": str(schedule_row.get("last_task_index") or ""),
                "reason": "|".join(reasons),
                "error_count": str(bucket.get("error_count", 0)),
                "sample_errors": " || ".join(bucket.get("samples", [])),
            }
        )

    rerun_rows.sort(key=lambda row: row["batch_file"])
    return rerun_rows


def analyze_header_only_timeouts(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    timeout_seconds: int,
) -> list[dict[str, str]]:
    now_timestamp = datetime.now(timezone.utc).timestamp()
    rerun_rows: list[dict[str, str]] = []

    for schedule_row in schedule_rows:
        if parse_optional_int(schedule_row.get("round_index"), default=0) != round_index:
            continue
        if (schedule_row.get("status") or "").strip() == "completed":
            continue

        inspection = inspect_batch_outputs(schedule_row)
        classifier_state = str(inspection["classifier"].get("state", ""))
        results_state = str(inspection["results"].get("state", ""))
        last_activity = float(inspection.get("last_activity") or 0.0)
        if last_activity <= 0:
            continue

        idle_seconds = int(max(0.0, now_timestamp - last_activity))
        if idle_seconds < timeout_seconds:
            continue

        reason = ""
        if classifier_state == "header_only" and results_state == "header_only":
            reason = "header_only_timeout_both_outputs"
        elif classifier_state == "completed" and results_state == "header_only":
            reason = "header_only_timeout_results_csv"
        elif classifier_state == "header_only" and results_state == "completed":
            reason = "header_only_timeout_classifier_csv"
        if not reason:
            continue

        rerun_rows.append(
            {
                "round_index": str(round_index),
                "batch_file": str(schedule_row.get("batch_file") or ""),
                "run_dir": str(schedule_row.get("run_dir") or ""),
                "status": "needs_rerun",
                "first_task_index": str(schedule_row.get("first_task_index") or ""),
                "last_task_index": str(schedule_row.get("last_task_index") or ""),
                "reason": reason,
                "idle_seconds": str(idle_seconds),
                "timeout_seconds": str(timeout_seconds),
                "last_activity_utc": datetime.fromtimestamp(
                    last_activity,
                    tz=timezone.utc,
                ).isoformat(),
                "classifier_state": classifier_state,
                "results_state": results_state,
            }
        )

    rerun_rows.sort(key=lambda row: row["batch_file"])
    return rerun_rows


def analyze_startup_no_row_timeouts(
    schedule_rows: list[dict[str, str]],
    round_index: int,
    timeout_seconds: int,
) -> list[dict[str, str]]:
    now_timestamp = datetime.now(timezone.utc).timestamp()
    rerun_rows: list[dict[str, str]] = []

    for schedule_row in schedule_rows:
        if parse_optional_int(schedule_row.get("round_index"), default=0) != round_index:
            continue
        if (schedule_row.get("status") or "").strip() == "completed":
            continue

        inspection = inspect_batch_outputs(schedule_row)
        classifier_state = str(inspection["classifier"].get("state", ""))
        results_state = str(inspection["results"].get("state", ""))
        if classifier_state != "header_only" or results_state != "header_only":
            continue

        last_activity = float(inspection.get("last_activity") or 0.0)
        if last_activity <= 0:
            continue

        idle_seconds = int(max(0.0, now_timestamp - last_activity))
        if idle_seconds < timeout_seconds:
            continue

        rerun_rows.append(
            {
                "round_index": str(round_index),
                "batch_file": str(schedule_row.get("batch_file") or ""),
                "run_dir": str(schedule_row.get("run_dir") or ""),
                "status": "needs_rerun",
                "first_task_index": str(schedule_row.get("first_task_index") or ""),
                "last_task_index": str(schedule_row.get("last_task_index") or ""),
                "reason": "startup_no_first_row_timeout",
                "idle_seconds": str(idle_seconds),
                "timeout_seconds": str(timeout_seconds),
                "last_activity_utc": datetime.fromtimestamp(
                    last_activity,
                    tz=timezone.utc,
                ).isoformat(),
                "classifier_state": classifier_state,
                "results_state": results_state,
            }
        )

    rerun_rows.sort(key=lambda row: row["batch_file"])
    return rerun_rows


def mark_rerun_batches_in_schedule(
    schedule_csv: Path,
    schedule_rows: list[dict[str, str]],
    rerun_rows: list[dict[str, str]],
) -> None:
    rerun_by_batch = {row["batch_file"]: row for row in rerun_rows}
    rerun_batches = set(rerun_by_batch)
    rerun_timestamp = datetime.now(timezone.utc).isoformat()
    updated_rows: list[dict[str, str]] = []
    for row in schedule_rows:
        updated = dict(row)
        updated["status"] = effective_runtime_status(updated)
        if is_deferred_long_tail_row(updated):
            updated = canonicalize_deferred_long_tail_row(updated)
            updated["respawn_count"] = str(parse_optional_int(updated.get("respawn_count"), default=0))
            updated["last_rerun_reason"] = str(updated.get("last_rerun_reason", ""))
            updated["last_rerun_at"] = str(updated.get("last_rerun_at", ""))
            updated["failure_counts_json"] = encode_failure_counts_json(
                parse_failure_counts_json(updated.get("failure_counts_json", ""))
            )
            updated_rows.append(updated)
            continue
        if row.get("batch_file") in rerun_batches:
            rerun_row = rerun_by_batch.get(str(row.get("batch_file") or "")) or {}
            failure_type = map_rerun_reason_to_failure_type(str(rerun_row.get("reason", "")))
            counts = parse_failure_counts_json(updated.get("failure_counts_json", ""))
            failure_tokens = canonicalize_runtime_failure_reasons(failure_type)
            for failure_token in failure_tokens:
                counts[failure_token] = counts.get(failure_token, 0) + 1
            updated["status"] = "needs_rerun"
            updated["prepared_reason"] = failure_type
            updated["last_failure_type"] = failure_type
            updated["failure_counts_json"] = encode_failure_counts_json(counts)
            updated["consecutive_no_progress_attempts"] = str(
                parse_optional_int(updated.get("consecutive_no_progress_attempts"), default=0) + 1
            )
            updated["respawn_count"] = str(
                parse_optional_int(updated.get("respawn_count"), default=0) + 1
            )
            updated["last_rerun_reason"] = failure_type
            updated["last_rerun_at"] = rerun_timestamp
            prefix_rows = max(
                parse_optional_int(updated.get("last_seen_classifier_rows"), default=0),
                parse_optional_int(updated.get("last_seen_result_rows"), default=0),
            )
            if any(token in {"schema_error", "verifier_forced_rerun"} for token in failure_tokens):
                updated["prepared_mode"] = "fresh_restart"
            else:
                updated["prepared_mode"] = "continue_from_prefix" if prefix_rows > 0 else "fresh_restart"
        else:
            updated["respawn_count"] = str(parse_optional_int(updated.get("respawn_count"), default=0))
            updated["last_rerun_reason"] = str(updated.get("last_rerun_reason", ""))
            updated["last_rerun_at"] = str(updated.get("last_rerun_at", ""))
            updated["failure_counts_json"] = encode_failure_counts_json(
                parse_failure_counts_json(updated.get("failure_counts_json", ""))
            )
        updated_rows.append(updated)
    write_schedule_rows(schedule_csv, updated_rows)


def write_lint_rerun_plan(runs_dir: Path, rerun_rows: list[dict[str, str]]) -> None:
    csv_path = runs_dir / AUTO_RERUN_BATCHES_CSV
    md_path = runs_dir / AUTO_RERUN_BATCHES_MD

    if not rerun_rows:
        for path in [csv_path, md_path]:
            if path.exists():
                path.unlink()
        return

    write_csv(
        csv_path,
        [
            "batch_file",
            "run_dir",
            "status",
            "first_task_index",
            "last_task_index",
            "reason",
            "error_count",
            "sample_errors",
        ],
        rerun_rows,
    )

    lines = [
        "# Auto Rerun Batches",
        "",
        "These batches were auto-marked `needs_rerun` during lint because the failure pattern looks structural rather than research-related.",
        "",
    ]
    for row in rerun_rows:
        lines.extend(
            [
                f"- {Path(row['batch_file']).name}: {row['reason']} ({row['first_task_index']}..{row['last_task_index']}, errors={row['error_count']})",
                f"  sample: {row['sample_errors']}",
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_header_only_rerun_plan(
    runs_dir: Path,
    round_index: int | None,
    timeout_seconds: int,
    rerun_rows: list[dict[str, str]],
) -> None:
    csv_path = runs_dir / HEADER_ONLY_RERUN_BATCHES_CSV
    md_path = runs_dir / HEADER_ONLY_RERUN_BATCHES_MD

    if not rerun_rows:
        for path in [csv_path, md_path]:
            if path.exists():
                path.unlink()
        return

    write_csv(
        csv_path,
        [
            "round_index",
            "batch_file",
            "run_dir",
            "status",
            "first_task_index",
            "last_task_index",
            "reason",
            "idle_seconds",
            "timeout_seconds",
            "last_activity_utc",
            "classifier_state",
            "results_state",
        ],
        rerun_rows,
    )

    lines = [
        "# Header-only Timeout Reruns",
        "",
        "These batches were auto-marked `needs_rerun` before full lint because worker outputs stayed header-only past the timeout.",
        "",
        f"- round_index: {round_index if round_index is not None else 'n/a'}",
        f"- timeout_seconds: {timeout_seconds}",
        "",
    ]
    for row in rerun_rows:
        lines.extend(
            [
                f"- {Path(row['batch_file']).name}: {row['reason']} ({row['first_task_index']}..{row['last_task_index']}, idle={row['idle_seconds']}s)",
                f"  last_activity_utc: {row['last_activity_utc']}",
                f"  classifier_state: {row['classifier_state']}, results_state: {row['results_state']}",
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_startup_respawn_plan(
    runs_dir: Path,
    round_index: int | None,
    timeout_seconds: int,
    rerun_rows: list[dict[str, str]],
) -> None:
    csv_path = runs_dir / STARTUP_RESPAWN_BATCHES_CSV
    md_path = runs_dir / STARTUP_RESPAWN_BATCHES_MD

    if not rerun_rows:
        for path in [csv_path, md_path]:
            if path.exists():
                path.unlink()
        return

    write_csv(
        csv_path,
        [
            "round_index",
            "batch_file",
            "run_dir",
            "status",
            "first_task_index",
            "last_task_index",
            "reason",
            "idle_seconds",
            "timeout_seconds",
            "last_activity_utc",
            "classifier_state",
            "results_state",
        ],
        rerun_rows,
    )

    lines = [
        "# Startup Respawn Batches",
        "",
        "These batches were auto-marked `needs_rerun` because both CSVs stayed header-only past the startup timeout. Kill the current worker agents and respawn fresh workers immediately.",
        "",
        f"- round_index: {round_index if round_index is not None else 'n/a'}",
        f"- timeout_seconds: {timeout_seconds}",
        "",
    ]
    for row in rerun_rows:
        lines.extend(
            [
                f"- {Path(row['batch_file']).name}: {row['reason']} ({row['first_task_index']}..{row['last_task_index']}, idle={row['idle_seconds']}s)",
                f"  last_activity_utc: {row['last_activity_utc']}",
                f"  classifier_state: {row['classifier_state']}, results_state: {row['results_state']}",
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_checkpoint(
    path: Path,
    final_rows: list[dict[str, str]],
    schedule_rows: list[dict[str, str]],
    output_csv: Path,
    classifier_results_csv: Path,
    manual_review_csv: Path,
    verification_findings_csv: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    max_task_index = max((int(row["task_index"]) for row in final_rows), default=0)
    max_batch = max((parse_batch_number(row.get("batch_file", "")) for row in schedule_rows), default=0)
    batch_stats = compute_checkpoint_batch_stats(schedule_rows)
    total_batches = max_batch
    batch_dir_candidates: list[Path] = []
    for row in schedule_rows:
        batch_file_value = (row.get("batch_file") or "").strip()
        if not batch_file_value:
            continue
        batch_path = resolve_path(batch_file_value)
        batch_parent = batch_path.parent
        if batch_parent.exists():
            batch_dir_candidates.append(batch_parent)
    if DEFAULT_BATCH_DIR.exists():
        batch_dir_candidates.append(DEFAULT_BATCH_DIR.resolve())
    for batch_dir in batch_dir_candidates:
        batch_count = max(
            (parse_batch_number(candidate.name) for candidate in batch_dir.glob("batch_*.jsonl")),
            default=0,
        )
        if batch_count:
            total_batches = max(total_batches, batch_count)

    checkpoint = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": "v2",
        "completed_rows_in_final_results": len(final_rows),
        "completed_through_task_index": max_task_index,
        "completed_through_batch": batch_stats["contiguous_completed_through_batch"],
        "max_collected_batch_seen": max_batch,
        "window_start_batch": batch_stats["window_start_batch"],
        "contiguous_completed_through_batch": batch_stats["contiguous_completed_through_batch"],
        "next_missing_batch": batch_stats["next_missing_batch"],
        "pending_batch_count": batch_stats["pending_batch_count"],
        "next_batch_to_process": batch_stats["next_missing_batch"],
        "next_task_index_to_process": max_task_index + 1,
        "batch_size": 30,
        "workers": 5,
        "total_batches": total_batches,
        "classifier_results_csv": str(classifier_results_csv),
        "final_results_csv": str(output_csv),
        "manual_review_csv": str(manual_review_csv),
        "verification_findings_csv": str(verification_findings_csv),
        "status": (
            f"ready_for_batch_{batch_stats['next_missing_batch']:04d}"
            if batch_stats["next_missing_batch"] > 0
            else "ready"
        ),
    }
    path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def cleanup_run_artifacts(runs_dir: Path, schedule_rows: list[dict[str, str]], schedule_csv: Path) -> list[str]:
    removed: list[str] = []
    removed_dirs: set[Path] = set()
    removed_files: set[Path] = set()
    cleanup_globs = list((load_runtime_policy().get("cleanup_artifacts_globs") or []))

    for schedule_row in schedule_rows:
        run_dir_raw = (schedule_row.get("run_dir") or "").strip()
        if run_dir_raw:
            run_dir = resolve_path(run_dir_raw)
            if (
                run_dir.exists()
                and run_dir.is_dir()
                and run_dir not in removed_dirs
                and path_within(runs_dir, run_dir)
            ):
                shutil.rmtree(run_dir)
                removed_dirs.add(run_dir)
                removed.append(str(run_dir))

        for key in [
            "verification_report_csv",
            "verification_summary_md",
            "verifier_instructions_file",
        ]:
            path_raw = (schedule_row.get(key) or "").strip()
            if not path_raw:
                continue
            artifact = resolve_path(path_raw)
            if (
                artifact.exists()
                and artifact.is_file()
                and artifact not in removed_files
                and path_within(runs_dir, artifact)
            ):
                artifact.unlink()
                removed_files.add(artifact)
                removed.append(str(artifact))

    for pattern in cleanup_globs:
        for extra_file in sorted(runs_dir.glob(pattern)):
            if extra_file.exists() and extra_file.is_file() and extra_file not in removed_files:
                extra_file.unlink()
                removed_files.add(extra_file)
                removed.append(str(extra_file))

    for empty_dir in sorted(runs_dir.glob("**/*"), reverse=True):
        if empty_dir.is_dir():
            try:
                empty_dir.rmdir()
                removed.append(str(empty_dir))
            except OSError:
                pass

    return removed


def main() -> None:
    args = parse_args()
    if args.watch_startup_no_row and args.watch_header_only:
        raise SystemExit("Use either --watch-startup-no-row or --watch-header-only, not both at once.")
    if args.startup_no_row_timeout_seconds < 0:
        raise SystemExit("--startup-no-row-timeout-seconds must be 0 or greater.")
    if args.header_only_timeout_seconds < 0:
        raise SystemExit("--header-only-timeout-seconds must be 0 or greater.")
    runs_dir = args.runs_dir.resolve()
    schedule_csv = ensure_file(
        args.schedule_csv.resolve() if args.schedule_csv else runs_dir / "schedule.csv",
        "Schedule CSV",
    )
    output_csv = (
        args.output_csv.resolve()
        if args.output_csv
        else (DEFAULT_FINAL_DIR / "results.csv").resolve()
    )
    classifier_results_csv = (
        args.classifier_results_csv.resolve()
        if args.classifier_results_csv
        else (DEFAULT_FINAL_DIR / "classifier_results.csv").resolve()
    )
    manual_review_csv = (
        args.manual_review_csv.resolve()
        if args.manual_review_csv
        else (DEFAULT_FINAL_DIR / "needs_manual_review.csv").resolve()
    )
    verification_findings_csv = (
        args.verification_findings_csv.resolve()
        if args.verification_findings_csv
        else (DEFAULT_FINAL_DIR / "verification_findings.csv").resolve()
    )
    checkpoint_json = (
        args.checkpoint_json.resolve()
        if args.checkpoint_json
        else (DEFAULT_FINAL_DIR / "checkpoint.json").resolve()
    )

    loaded_schedule_rows = load_schedule(schedule_csv)
    reconciled_schedule_rows = reconcile_schedule_attempts(loaded_schedule_rows)
    schedule_rows = refresh_schedule_statuses(reconciled_schedule_rows)
    if not schedule_rows:
        raise SystemExit("Schedule has no rows.")
    if schedule_rows != loaded_schedule_rows:
        write_schedule_rows(schedule_csv, schedule_rows)
        loaded_schedule_rows = [dict(row) for row in schedule_rows]

    if args.watch_startup_no_row:
        watch_round_index = resolve_watch_round_index(schedule_rows, args.round_index)
        startup_respawn_rows = analyze_startup_no_row_timeouts(
            schedule_rows=schedule_rows,
            round_index=watch_round_index,
            timeout_seconds=args.startup_no_row_timeout_seconds,
        ) if watch_round_index is not None else []
        write_startup_respawn_plan(
            runs_dir=runs_dir,
            round_index=watch_round_index,
            timeout_seconds=args.startup_no_row_timeout_seconds,
            rerun_rows=startup_respawn_rows,
        )
        if schedule_rows != loaded_schedule_rows or startup_respawn_rows:
            mark_rerun_batches_in_schedule(schedule_csv, schedule_rows, startup_respawn_rows)

        incomplete_rounds = get_incomplete_rounds(schedule_rows)
        print(f"Schedule CSV: {schedule_csv}")
        print(f"Round watch index: {watch_round_index if watch_round_index is not None else 'none'}")
        print(f"Incomplete rounds: {','.join(str(value) for value in incomplete_rounds) if incomplete_rounds else 'none'}")
        print(f"Startup no-row timeout seconds: {args.startup_no_row_timeout_seconds}")
        print(f"Auto respawn batches: {len(startup_respawn_rows)}")
        for row in startup_respawn_rows[:20]:
            print(
                f"- needs_rerun: {Path(row['batch_file']).name} "
                f"({row['reason']}, idle={row['idle_seconds']}s)"
            )
        if startup_respawn_rows:
            print(f"Respawn plan CSV: {runs_dir / STARTUP_RESPAWN_BATCHES_CSV}")
            raise SystemExit(
                "Startup no-row timeout detected. Auto-marked needs_rerun rows in schedule.csv."
            )
        return

    if args.watch_header_only:
        watch_round_index = resolve_watch_round_index(schedule_rows, args.round_index)
        header_only_rerun_rows = analyze_header_only_timeouts(
            schedule_rows=schedule_rows,
            round_index=watch_round_index,
            timeout_seconds=args.header_only_timeout_seconds,
        ) if watch_round_index is not None else []
        write_header_only_rerun_plan(
            runs_dir=runs_dir,
            round_index=watch_round_index,
            timeout_seconds=args.header_only_timeout_seconds,
            rerun_rows=header_only_rerun_rows,
        )
        if schedule_rows != loaded_schedule_rows or header_only_rerun_rows:
            mark_rerun_batches_in_schedule(schedule_csv, schedule_rows, header_only_rerun_rows)

        incomplete_rounds = get_incomplete_rounds(schedule_rows)
        print(f"Schedule CSV: {schedule_csv}")
        print(f"Round watch index: {watch_round_index if watch_round_index is not None else 'none'}")
        print(f"Incomplete rounds: {','.join(str(value) for value in incomplete_rounds) if incomplete_rounds else 'none'}")
        print(f"Header-only timeout seconds: {args.header_only_timeout_seconds}")
        print(f"Auto rerun batches: {len(header_only_rerun_rows)}")
        for row in header_only_rerun_rows[:20]:
            print(
                f"- needs_rerun: {Path(row['batch_file']).name} "
                f"({row['reason']}, idle={row['idle_seconds']}s)"
            )
        if header_only_rerun_rows:
            print(f"Rerun plan CSV: {runs_dir / HEADER_ONLY_RERUN_BATCHES_CSV}")
            raise SystemExit(
                "Header-only timeout detected. Auto-marked needs_rerun rows in schedule.csv."
            )
        return

    repaired_identity_files: list[str] = []
    if args.repair_identity_drift_in_place:
        repaired_identity_files = rewrite_identity_fields_in_place(schedule_rows)

    identity_override_tracker = make_identity_override_tracker()
    skip_verification = args.skip_verification or args.lint_only
    pipeline_schedule_rows = schedule_rows
    scoped_round_indexes: list[int] = []
    scoped_batch_files = resolve_batch_scope(schedule_rows, args.batch_file)
    if args.lint_only:
        if args.round_index > 0:
            scoped_round_indexes = resolve_lint_round_indexes(schedule_rows, args.round_index)
        elif not scoped_batch_files:
            scoped_round_indexes = resolve_lint_round_indexes(schedule_rows, args.round_index)
    elif args.round_index > 0:
        available_rounds = sorted(
            {
                parse_optional_int(row.get("round_index"), default=0)
                for row in schedule_rows
                if parse_optional_int(row.get("round_index"), default=0) > 0
            }
        )
        if args.round_index not in available_rounds:
            raise SystemExit(
                f"--round-index={args.round_index} is not present in schedule.csv. "
                f"Available rounds: {','.join(str(value) for value in available_rounds)}"
            )
        scoped_round_indexes = [args.round_index]
    if scoped_round_indexes:
        scoped_round_set = set(scoped_round_indexes)
        pipeline_schedule_rows = [
            row
            for row in schedule_rows
            if parse_optional_int(row.get("round_index"), default=0) in scoped_round_set
        ]
    if scoped_batch_files:
        scoped_batch_set = set(scoped_batch_files)
        pipeline_schedule_rows = [
            row
            for row in pipeline_schedule_rows
            if str(row.get("batch_file") or "").strip() in scoped_batch_set
        ]
        if not pipeline_schedule_rows:
            round_scope_text = (
                f" within rounds {','.join(str(value) for value in scoped_round_indexes)}"
                if scoped_round_indexes
                else ""
            )
            raise SystemExit(
                "Requested batch scope did not match any rows"
                f"{round_scope_text}: {', '.join(Path(value).name for value in scoped_batch_files)}"
            )
    deferred_long_tail_rows = [row for row in pipeline_schedule_rows if is_deferred_long_tail_row(row)]
    if deferred_long_tail_rows:
        pipeline_schedule_rows = [
            row for row in pipeline_schedule_rows if not is_deferred_long_tail_row(row)
        ]

    classifier_rows, validation_errors, classifier_rows_by_task = collect_classifier_rows(
        pipeline_schedule_rows,
        identity_override_tracker=identity_override_tracker,
    )
    new_rows, worker_errors, expected_total = collect_worker_rows(
        pipeline_schedule_rows,
        classifier_rows_by_task,
        identity_override_tracker=identity_override_tracker,
    )
    validation_errors.extend(worker_errors)
    worker_rows_by_task = {int(row["task_index"]): row for row in new_rows}
    verifier_rows, verifier_errors = collect_verification_rows(
        schedule_rows=pipeline_schedule_rows,
        worker_rows_by_task=worker_rows_by_task,
        classifier_rows_by_task=classifier_rows_by_task,
        skip_verification=skip_verification,
        allow_unresolved_verification=args.allow_unresolved_verification,
        identity_override_tracker=identity_override_tracker,
    )
    validation_errors.extend(verifier_errors)
    new_rows = apply_verifier_review_decisions(new_rows, verifier_rows)
    worker_rows_by_task = {int(row["task_index"]): row for row in new_rows}
    for row in new_rows:
        validation_errors.extend(validate_result_row(row, Path("<post-verifier-output>")))
    validation_errors.extend(
        validate_rows_against_classifier(
            rows=new_rows,
            classifier_rows_by_task=classifier_rows_by_task,
            source_label="<post-verifier-output>",
        )
    )
    identity_override_count = int(identity_override_tracker.get("count", 0))
    identity_override_samples = list(identity_override_tracker.get("samples", []))
    identity_override_by_source = dict(identity_override_tracker.get("by_source", {}))
    identity_override_summary = sorted(
        identity_override_by_source.items(),
        key=lambda item: (-item[1], item[0]),
    )

    if args.fail_on_identity_drift and identity_override_count and not args.allow_partial:
        validation_errors.append(
            f"Immutable identity drift detected in {identity_override_count} rows. "
            "Workers must preserve task_index/investor_id/investor_name/normalized_domain exactly from tasks.jsonl."
        )
        for source, count in identity_override_summary[:20]:
            validation_errors.append(f"identity_drift: {source}: {count} overridden rows")

    lint_rerun_rows = analyze_lint_failures(pipeline_schedule_rows, validation_errors)
    write_lint_rerun_plan(runs_dir, lint_rerun_rows)
    if lint_rerun_rows:
        mark_rerun_batches_in_schedule(schedule_csv, schedule_rows, lint_rerun_rows)

    if args.lint_only:
        if validation_errors and not args.allow_partial:
            if lint_rerun_rows:
                print("Auto-marked rerun batches:")
                for row in lint_rerun_rows[:20]:
                    print(f"- {Path(row['batch_file']).name}: {row['reason']} (errors={row['error_count']})")
                if len(lint_rerun_rows) > 20:
                    print(f"- ... {len(lint_rerun_rows) - 20} more batches")
                print(f"Rerun plan CSV: {runs_dir / AUTO_RERUN_BATCHES_CSV}")
            print("Validation errors:")
            for error in validation_errors[:80]:
                print(f"- {error}")
            if len(validation_errors) > 80:
                print(f"- ... {len(validation_errors) - 80} more")
            raise SystemExit("Lint failed. Auto-marked needs_rerun rows in schedule.csv where applicable.")
        print(f"Lint schedule CSV: {schedule_csv}")
        if scoped_round_indexes:
            print(f"Lint round scope: {','.join(str(value) for value in scoped_round_indexes)}")
        if scoped_batch_files:
            print(f"Lint batch scope: {', '.join(Path(value).name for value in scoped_batch_files)}")
        print(f"Classifier rows: {len(classifier_rows)}")
        print(f"Worker rows: {len(new_rows)}")
        print(f"Verifier rows checked during lint: {len(verifier_rows)}")
        print(f"Validation errors: {len(validation_errors)}")
        print(f"Auto rerun batches: {len(lint_rerun_rows)}")
        print(f"Deferred long-tail batches skipped: {len(deferred_long_tail_rows)}")
        for row in deferred_long_tail_rows[:20]:
            print(f"- deferred_long_tail: {Path(row['batch_file']).name}")
        for row in lint_rerun_rows[:20]:
            print(f"- needs_rerun: {Path(row['batch_file']).name} ({row['reason']})")
        print(f"Identity repair files: {len(repaired_identity_files)}")
        for path in repaired_identity_files[:20]:
            print(f"- repaired: {path}")
        print(f"Identity overrides applied: {identity_override_count}")
        if identity_override_summary:
            print("Identity overrides by file:")
            for source, count in identity_override_summary[:10]:
                print(f"- {count}: {source}")
        if identity_override_samples:
            print("Identity override samples:")
            for sample in identity_override_samples[:10]:
                print(f"- {sample}")
        return

    existing_rows = load_existing_results(output_csv, replace_output=args.replace_output)
    final_rows, overwritten_result_task_indexes = merge_existing_and_new(existing_rows, new_rows)

    existing_classifier_rows = load_existing_classifier_results(
        classifier_results_csv,
        replace_output=args.replace_output,
    )
    final_classifier_rows, overwritten_classifier_task_indexes = merge_existing_and_new(
        existing_classifier_rows,
        classifier_rows,
    )

    existing_verifier_rows = load_existing_verification_findings(
        verification_findings_csv,
        replace_output=args.replace_output,
    )
    final_verifier_rows, overwritten_verifier_task_indexes = merge_existing_and_new(
        existing_verifier_rows,
        verifier_rows,
    )

    manual_rows = [
        row for row in final_rows if (row.get("needs_manual_review") or "").strip() == "yes"
    ]

    if validation_errors and not args.allow_partial:
        print("Validation errors:")
        for error in validation_errors[:80]:
            print(f"- {error}")
        if len(validation_errors) > 80:
            print(f"- ... {len(validation_errors) - 80} more")
        raise SystemExit("Refusing to write outputs. Fix errors or pass --allow-partial for debug output.")

    write_csv(output_csv, RESULT_CSV_COLUMNS, final_rows)
    write_csv(classifier_results_csv, CLASSIFIER_CSV_COLUMNS, final_classifier_rows)
    write_csv(manual_review_csv, RESULT_CSV_COLUMNS, manual_rows)
    if verifier_rows or existing_verifier_rows:
        write_csv(verification_findings_csv, VERIFICATION_CSV_COLUMNS, final_verifier_rows)
    write_checkpoint(
        path=checkpoint_json,
        final_rows=final_rows,
        schedule_rows=schedule_rows,
        output_csv=output_csv,
        classifier_results_csv=classifier_results_csv,
        manual_review_csv=manual_review_csv,
        verification_findings_csv=verification_findings_csv,
    )
    removed_artifacts: list[str] = []
    if args.cleanup_run_artifacts:
        removed_artifacts = cleanup_run_artifacts(
            runs_dir=runs_dir,
            schedule_rows=schedule_rows,
            schedule_csv=schedule_csv,
        )

    print(f"Schedule CSV: {schedule_csv}")
    print(f"Expected new rows: {expected_total}")
    print(f"Classifier rows: {len(classifier_rows)}")
    print(f"New rows: {len(new_rows)}")
    print(f"Final rows: {len(final_rows)}")
    print(f"Manual review rows: {len(manual_rows)}")
    print(f"Verifier rows: {len(verifier_rows)}")
    print(f"Final verifier rows: {len(final_verifier_rows)}")
    print(f"Validation errors: {len(validation_errors)}")
    print(f"Overwritten existing final rows: {len(overwritten_result_task_indexes)}")
    print(f"Overwritten existing classifier rows: {len(overwritten_classifier_task_indexes)}")
    print(f"Overwritten existing verifier rows: {len(overwritten_verifier_task_indexes)}")
    print(f"Deferred long-tail batches skipped: {len(deferred_long_tail_rows)}")
    for row in deferred_long_tail_rows[:20]:
        print(f"- deferred_long_tail: {Path(row['batch_file']).name}")
    print(f"Final output CSV: {output_csv}")
    print(f"Classifier results CSV: {classifier_results_csv}")
    print(f"Manual review CSV: {manual_review_csv}")
    if scoped_round_indexes:
        print(f"Collect round scope: {','.join(str(value) for value in scoped_round_indexes)}")
    if scoped_batch_files:
        print(f"Collect batch scope: {', '.join(Path(value).name for value in scoped_batch_files)}")
    print(f"Verification findings CSV: {verification_findings_csv}")
    print(f"Checkpoint JSON: {checkpoint_json}")
    print(f"Identity repair files: {len(repaired_identity_files)}")
    for path in repaired_identity_files[:20]:
        print(f"- repaired: {path}")
    print(f"Identity overrides applied: {identity_override_count}")
    if identity_override_summary:
        print("Identity overrides by file:")
        for source, count in identity_override_summary[:10]:
            print(f"- {count}: {source}")
    if identity_override_samples:
        print("Identity override samples:")
        for sample in identity_override_samples[:10]:
            print(f"- {sample}")
    if args.cleanup_run_artifacts:
        print(f"Removed run artifacts: {len(removed_artifacts)}")


if __name__ == "__main__":
    main()
