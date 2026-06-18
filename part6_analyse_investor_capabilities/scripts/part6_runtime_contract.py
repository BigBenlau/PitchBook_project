#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


VERIFICATION_MODE_REQUIRED = "required"
DEFAULT_VERIFICATION_MODE = VERIFICATION_MODE_REQUIRED
VERIFICATION_MODE_VALUES = {
    VERIFICATION_MODE_REQUIRED,
}
LEGACY_VERIFICATION_MODE_ALIASES = {
    "": DEFAULT_VERIFICATION_MODE,
    "none": DEFAULT_VERIFICATION_MODE,
    "disabled": DEFAULT_VERIFICATION_MODE,
    "skip": DEFAULT_VERIFICATION_MODE,
    "template_only": DEFAULT_VERIFICATION_MODE,
}
SEARCH_REQUIREMENT_UNKNOWN = "unknown"
SEARCH_REQUIREMENT_SKIP_ONLY = "skip_only"
SEARCH_REQUIREMENT_SEARCHED = "searched"

SCHEDULE_FIELD_ALIASES = {
    "first_company": "first_investor",
    "last_company": "last_investor",
    "start_company": "start_investor",
    "end_company": "end_investor",
}
REVERSE_SCHEDULE_FIELD_ALIASES: dict[str, tuple[str, ...]] = {}
for legacy_name, canonical_name in SCHEDULE_FIELD_ALIASES.items():
    REVERSE_SCHEDULE_FIELD_ALIASES.setdefault(canonical_name, tuple())
    REVERSE_SCHEDULE_FIELD_ALIASES[canonical_name] = (
        *REVERSE_SCHEDULE_FIELD_ALIASES[canonical_name],
        legacy_name,
    )


def normalize_verification_mode(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in VERIFICATION_MODE_VALUES:
        return raw
    if raw in LEGACY_VERIFICATION_MODE_ALIASES:
        return LEGACY_VERIFICATION_MODE_ALIASES[raw]
    return DEFAULT_VERIFICATION_MODE


def parse_verification_mode_arg(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if raw in VERIFICATION_MODE_VALUES or raw in LEGACY_VERIFICATION_MODE_ALIASES:
        return normalize_verification_mode(raw)
    supported = ", ".join(sorted(VERIFICATION_MODE_VALUES))
    raise ValueError(f"Unsupported verification mode {value!r}. Expected one of: {supported}.")


def infer_search_requirement_from_classifier_csv(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return SEARCH_REQUIREMENT_UNKNOWN
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or "search_tier" not in reader.fieldnames:
                return SEARCH_REQUIREMENT_UNKNOWN
            saw_rows = False
            for row in reader:
                saw_rows = True
                search_tier = str((row or {}).get("search_tier") or "").strip().lower()
                if search_tier and search_tier != "skip_candidate":
                    return SEARCH_REQUIREMENT_SEARCHED
            return SEARCH_REQUIREMENT_SKIP_ONLY if saw_rows else SEARCH_REQUIREMENT_UNKNOWN
    except OSError:
        return SEARCH_REQUIREMENT_UNKNOWN


def resolve_effective_verification_mode(
    explicit_mode: Any,
    *,
    classifier_csv: Path | None = None,
) -> tuple[str, str]:
    normalized_mode = normalize_verification_mode(explicit_mode)
    if normalized_mode == VERIFICATION_MODE_REQUIRED:
        return VERIFICATION_MODE_REQUIRED, "schedule_required"

    if classifier_csv is None:
        return VERIFICATION_MODE_REQUIRED, "verification_unknown_defaults_required"

    search_requirement = infer_search_requirement_from_classifier_csv(classifier_csv)
    if search_requirement == SEARCH_REQUIREMENT_SEARCHED:
        return VERIFICATION_MODE_REQUIRED, "searched_data_requires_verification"
    if search_requirement == SEARCH_REQUIREMENT_SKIP_ONLY:
        return VERIFICATION_MODE_REQUIRED, "skip_candidate_only_still_requires_verification"
    return VERIFICATION_MODE_REQUIRED, "verification_unknown_defaults_required"


def canonical_schedule_field(field: Any) -> str:
    raw = str(field or "").strip()
    if not raw:
        return ""
    return SCHEDULE_FIELD_ALIASES.get(raw, raw)


def schedule_row_value(row: dict[str, Any], field: str, default: str = "") -> str:
    if field in row and str(row.get(field, "") or "").strip():
        return str(row.get(field, "") or "")
    for legacy_name in REVERSE_SCHEDULE_FIELD_ALIASES.get(field, ()):
        if legacy_name in row and str(row.get(legacy_name, "") or "").strip():
            return str(row.get(legacy_name, "") or "")
    return default


def normalize_schedule_rows(
    fieldnames: list[str] | tuple[str, ...] | None,
    rows: list[dict[str, Any]],
) -> tuple[list[str], list[dict[str, str]], bool]:
    normalized_fieldnames: list[str] = []
    seen: set[str] = set()
    changed = False

    for raw_field in fieldnames or []:
        canonical_field = canonical_schedule_field(raw_field)
        if not canonical_field:
            changed = True
            continue
        if canonical_field != str(raw_field or "").strip():
            changed = True
        if canonical_field in seen:
            changed = True
            continue
        seen.add(canonical_field)
        normalized_fieldnames.append(canonical_field)

    if "verification_mode" not in seen:
        normalized_fieldnames.append("verification_mode")
        seen.add("verification_mode")
        changed = True

    normalized_rows: list[dict[str, str]] = []
    for raw_row in rows:
        normalized_row = {
            field: schedule_row_value(raw_row, field, "")
            for field in normalized_fieldnames
        }
        original_mode = schedule_row_value(raw_row, "verification_mode", DEFAULT_VERIFICATION_MODE)
        normalized_mode = normalize_verification_mode(original_mode)
        if normalized_mode != str(original_mode or ""):
            changed = True
        normalized_row["verification_mode"] = normalized_mode

        for key, value in raw_row.items():
            canonical_key = canonical_schedule_field(key)
            normalized_value = normalized_row.get(canonical_key, "")
            source_value = "" if value is None else str(value)
            if canonical_key not in normalized_row:
                changed = True
                continue
            if canonical_key != str(key or "").strip():
                changed = True
            if normalized_value != source_value and source_value:
                changed = True
        normalized_rows.append(normalized_row)

    return normalized_fieldnames, normalized_rows, changed
