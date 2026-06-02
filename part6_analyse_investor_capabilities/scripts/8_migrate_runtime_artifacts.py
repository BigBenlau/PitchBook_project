#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from part6_runtime_contract import (
    VERIFICATION_MODE_NONE,
    VERIFICATION_MODE_REQUIRED,
    resolve_effective_verification_mode,
)
from part6_schedule_io import load_csv_rows_with_fields, load_schedule_csv_with_fields, write_schedule_csv


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent
DEFAULT_AGENT_RUNS_DIR = PART6_DIR / "agent_runs"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Migrate part6 runtime artifacts in place: canonicalize schedule.csv to *_investor "
            "fields plus explicit verification_mode, and canonicalize launcher_state metadata."
        )
    )
    parser.add_argument("--agent-runs-dir", type=Path, default=DEFAULT_AGENT_RUNS_DIR)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def resolve_repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def effective_mode_for_row(row: dict[str, str]) -> tuple[str, str]:
    classifier_raw = str(row.get("classifier_results_csv") or "").strip()
    classifier_path = resolve_repo_path(classifier_raw) if classifier_raw else None
    return resolve_effective_verification_mode(
        row.get("verification_mode"),
        classifier_csv=classifier_path,
    )


def canonicalize_schedule(schedule_csv: Path, *, dry_run: bool) -> tuple[bool, dict[str, int]]:
    raw_fieldnames, _ = load_csv_rows_with_fields(schedule_csv)
    fieldnames, rows = load_schedule_csv_with_fields(schedule_csv)
    if not rows:
        return False, {"rows": 0, "required": 0, "none": 0}

    changed = raw_fieldnames != fieldnames
    required_count = 0
    none_count = 0
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        updated = dict(row)
        mode, _ = effective_mode_for_row(updated)
        if updated.get("verification_mode") != mode:
            updated["verification_mode"] = mode
            changed = True
        if mode == VERIFICATION_MODE_REQUIRED:
            required_count += 1
        elif mode == VERIFICATION_MODE_NONE:
            none_count += 1
        normalized_rows.append(updated)

    if changed and not dry_run:
        write_schedule_csv(schedule_csv, normalized_rows, fieldnames=fieldnames)
    return changed, {"rows": len(rows), "required": required_count, "none": none_count}


def schedule_summary(schedule_csv: Path) -> dict[str, Any]:
    fieldnames, rows = load_schedule_csv_with_fields(schedule_csv)
    if not rows:
        return {
            "fieldnames": fieldnames,
            "rows": rows,
            "first_investor": "",
            "last_investor": "",
            "verification_mode": VERIFICATION_MODE_REQUIRED,
        }

    first_row = rows[0]
    last_row = rows[-1]
    overall_mode = VERIFICATION_MODE_NONE
    for row in rows:
        mode, _ = effective_mode_for_row(row)
        if mode == VERIFICATION_MODE_REQUIRED:
            overall_mode = VERIFICATION_MODE_REQUIRED
            break
    return {
        "fieldnames": fieldnames,
        "rows": rows,
        "first_investor": str(first_row.get("first_investor") or ""),
        "last_investor": str(last_row.get("last_investor") or ""),
        "verification_mode": overall_mode,
    }


def canonicalize_launcher_payload(path: Path, *, dry_run: bool) -> bool:
    payload = read_json(path)
    if not payload:
        return False

    schedule_csv_raw = str(payload.get("schedule_csv") or "").strip()
    runs_dir_raw = str(payload.get("runs_dir") or "").strip()
    schedule_csv: Path | None = None
    if schedule_csv_raw:
        schedule_csv = resolve_repo_path(schedule_csv_raw)
    elif runs_dir_raw:
        candidate = resolve_repo_path(runs_dir_raw) / "schedule.csv"
        if candidate.exists():
            schedule_csv = candidate

    changed = False
    if schedule_csv is not None and schedule_csv.exists():
        summary = schedule_summary(schedule_csv)
        for key in ("first_company", "last_company"):
            if key in payload:
                payload.pop(key, None)
                changed = True
        if payload.get("first_investor") != summary["first_investor"]:
            payload["first_investor"] = summary["first_investor"]
            changed = True
        if payload.get("last_investor") != summary["last_investor"]:
            payload["last_investor"] = summary["last_investor"]
            changed = True
        if payload.get("verification_mode") != summary["verification_mode"]:
            payload["verification_mode"] = summary["verification_mode"]
            changed = True

    if changed and not dry_run:
        write_json(path, payload)
    return changed


def main() -> None:
    args = parse_args()
    agent_runs_dir = args.agent_runs_dir.resolve()

    schedule_paths = sorted(agent_runs_dir.rglob("schedule.csv"))
    launcher_paths = sorted(agent_runs_dir.rglob("launcher_state.json"))

    migrated_schedules: list[str] = []
    schedule_reports: list[str] = []
    for schedule_csv in schedule_paths:
        changed, counts = canonicalize_schedule(schedule_csv, dry_run=args.dry_run)
        if changed:
            migrated_schedules.append(str(schedule_csv))
        schedule_reports.append(
            f"{schedule_csv}: rows={counts['rows']} required={counts['required']} none={counts['none']} changed={changed}"
        )

    migrated_launchers: list[str] = []
    for launcher_json in launcher_paths:
        if canonicalize_launcher_payload(launcher_json, dry_run=args.dry_run):
            migrated_launchers.append(str(launcher_json))

    mode = "DRY RUN" if args.dry_run else "MIGRATED"
    print(f"{mode} schedules: {len(migrated_schedules)}/{len(schedule_paths)}")
    for line in schedule_reports:
        print(f"- {line}")
    print(f"{mode} launcher JSONs: {len(migrated_launchers)}/{len(launcher_paths)}")
    for path in migrated_launchers:
        print(f"- {path}")


if __name__ == "__main__":
    main()
