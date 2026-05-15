#!/usr/bin/env python3
from __future__ import annotations

import csv
import fcntl
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
OPS_LOCKS_DIR = PART4_DIR / "agent_runs" / "token_company_ops" / "locks"


def schedule_lock_path(path: Path) -> Path:
    try:
        relative = path.resolve().relative_to(PART4_DIR / "agent_runs")
        lock_name = "." + str(relative).replace("/", "__") + ".lock"
    except ValueError:
        lock_name = f".{path.name}.lock"
    return OPS_LOCKS_DIR / lock_name


def load_csv_rows_with_fields(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = list(reader.fieldnames or [])
        rows = [{field: str(row.get(field, "") or "") for field in fieldnames} for row in reader]
    return fieldnames, rows


def merge_fieldnames(
    primary_fieldnames: list[str] | tuple[str, ...] | None,
    existing_fieldnames: list[str] | tuple[str, ...] | None,
    rows: list[dict[str, Any]],
) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()

    def add_field(raw: Any) -> None:
        field = str(raw or "").strip()
        if not field or field in seen:
            return
        seen.add(field)
        merged.append(field)

    for field in primary_fieldnames or []:
        add_field(field)
    for field in existing_fieldnames or []:
        add_field(field)
    for row in rows:
        for field in row.keys():
            add_field(field)
    return merged


def normalize_rows(rows: list[dict[str, Any]], fieldnames: list[str]) -> list[dict[str, str]]:
    return [{field: str(row.get(field, "") or "") for field in fieldnames} for row in rows]


@contextmanager
def locked_schedule(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = schedule_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lockfile:
        fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_UN)


def atomic_write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_raw = tempfile.mkstemp(
        prefix=f".{path.name}.tmp.",
        suffix=".csv",
        dir=path.parent,
    )
    temp_path = Path(temp_raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            outfile.flush()
            os.fsync(outfile.fileno())
        os.replace(temp_path, path)
        try:
            dir_fd = os.open(path.parent, os.O_DIRECTORY)
        except OSError:
            dir_fd = None
        if dir_fd is not None:
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def merge_schedule_rows(
    existing_rows: list[dict[str, str]],
    new_rows: list[dict[str, Any]],
    fieldnames: list[str],
) -> list[dict[str, str]]:
    if not existing_rows:
        return normalize_rows(new_rows, fieldnames)

    def batch_key(row: dict[str, Any]) -> str:
        return str(row.get("batch_file") or "").strip()

    new_keys = [batch_key(row) for row in new_rows]
    existing_keys = [batch_key(row) for row in existing_rows]
    if any(not key for key in new_keys) or any(not key for key in existing_keys):
        return normalize_rows(new_rows, fieldnames)

    merged_by_key = {key: dict(row) for key, row in zip(existing_keys, existing_rows)}
    new_only_order: list[str] = []
    for key, row in zip(new_keys, new_rows):
        if key not in merged_by_key:
            new_only_order.append(key)
        merged_by_key[key] = dict(row)

    ordered_keys = list(existing_keys)
    seen = set(existing_keys)
    for key in new_only_order:
        if key in seen:
            continue
        ordered_keys.append(key)
        seen.add(key)

    merged_rows = [merged_by_key[key] for key in ordered_keys if key in merged_by_key]
    return normalize_rows(merged_rows, fieldnames)


def write_schedule_csv(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    fieldnames: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    if not rows:
        raise SystemExit(f"Refusing to write empty schedule: {path}")
    with locked_schedule(path):
        existing_fieldnames, existing_rows = load_csv_rows_with_fields(path)
        merged_fieldnames = merge_fieldnames(fieldnames, existing_fieldnames, rows)
        merged_rows = merge_schedule_rows(existing_rows, rows, merged_fieldnames)
        atomic_write_csv(path, merged_fieldnames, merged_rows)
    return merged_fieldnames
