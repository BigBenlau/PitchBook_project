#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
DEFAULT_LATEST_JOB_JSON = PART6_DIR / "agent_runs" / "crypto_investor_longrun_latest.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Release completed part6 worker registry entries when the supervisor process "
            "cannot distinguish exited zombie workers from live workers."
        )
    )
    parser.add_argument("--latest-job-json", type=Path, default=DEFAULT_LATEST_JOB_JSON)
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=30)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def read_schedule(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))


def data_rows(path: str) -> int:
    target = Path(path)
    if not target.exists():
        return 0
    return max(0, sum(1 for _ in target.open(encoding="utf-8", errors="replace")) - 1)


def resolve_runs_dir(args: argparse.Namespace) -> Path:
    if args.runs_dir is not None:
        return args.runs_dir.resolve()
    latest_job = load_json(args.latest_job_json.resolve()) or {}
    runs_dir = latest_job.get("runs_dir")
    if not runs_dir:
        raise SystemExit("Unable to resolve runs_dir.")
    return Path(str(runs_dir)).resolve()


def completed_running_batches(schedule_rows: list[dict[str, str]]) -> set[str]:
    completed: set[str] = set()
    for row in schedule_rows:
        if str(row.get("status") or "").strip() != "running":
            continue
        active_attempt = Path(str(row.get("active_attempt") or ""))
        if not (active_attempt / "final_message.md").exists():
            continue
        task_count = int(str(row.get("task_count") or "0") or "0")
        if task_count <= 0:
            continue
        if data_rows(str(row.get("classifier_results_csv") or "")) != task_count:
            continue
        if data_rows(str(row.get("results_csv") or "")) != task_count:
            continue
        batch_file = str(row.get("batch_file") or "").strip()
        if batch_file:
            completed.add(batch_file)
    return completed


def all_queue_work_done(schedule_rows: list[dict[str, str]]) -> bool:
    if not schedule_rows:
        return False
    for row in schedule_rows:
        status = str(row.get("status") or "").strip()
        collect_state = str(row.get("collect_state") or "").strip()
        if status == "deferred_long_tail":
            continue
        if status == "completed" and collect_state == "done":
            continue
        return False
    return True


def append_event(events_log: Path, message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat()
    with events_log.open("a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")


def reap_once(runs_dir: Path) -> int:
    schedule_rows = read_schedule(runs_dir / "schedule.csv")
    if not schedule_rows:
        return 0
    registry_path = runs_dir / "supervisor_registry.json"
    registry = load_json(registry_path) or []
    if not isinstance(registry, list) or not registry:
        return 0
    completed = completed_running_batches(schedule_rows)
    if not completed:
        return 0
    kept: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    for entry in registry:
        if not isinstance(entry, dict):
            continue
        if str(entry.get("batch_file") or "") in completed:
            removed.append(entry)
        else:
            kept.append(entry)
    if not removed:
        return 0
    tmp = registry_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(kept, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, registry_path)
    batch_names = ",".join(sorted(Path(batch).stem for batch in completed))
    append_event(
        runs_dir / "supervisor_events.log",
        f"[registry_reaper:release_completed_workers] removed={len(removed)} batches={batch_names}",
    )
    return len(removed)


def main() -> None:
    args = parse_args()
    runs_dir = resolve_runs_dir(args)
    while True:
        removed = reap_once(runs_dir)
        if removed:
            print(f"released {removed} completed worker registry entr{'y' if removed == 1 else 'ies'}", flush=True)
        if not args.watch:
            return
        schedule_rows = read_schedule(runs_dir / "schedule.csv")
        state = load_json(runs_dir / "supervisor_state.json") or {}
        if all_queue_work_done(schedule_rows) or str(state.get("phase") or "").strip() == "completed":
            return
        time.sleep(max(1, args.poll_seconds))


if __name__ == "__main__":
    main()
