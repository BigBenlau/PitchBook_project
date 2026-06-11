#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any

from part6_schema import (
    CAPABILITY_FLAG_COLUMNS,
    CLASSIFIER_CSV_COLUMNS,
    RESULT_CSV_COLUMNS,
    parse_json_list,
)


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent
DEFAULT_BATCH_DIR = REPO_ROOT / "part5_to_part6" / "output" / "part6_batches"
DEFAULT_FINAL_DIR = PART6_DIR / "agent_runs" / "crypto_investor"

IDENTITY_LITERAL_EXEMPT_COLUMNS = {
    "task_index",
    "investor_id",
    "investor_name",
    "normalized_domain",
    "primary_investor_type",
}

DANGEROUS_LITERAL_PATTERNS = [
    "$(",
    "`",
    "{{",
    "}}",
    "<TODO",
    "date -u",
]

SOFT_PLACEHOLDER_PATTERNS = [
    r"(^|[\s<>{}\[\]()/\\|;:,])(?:TODO|TBD)(?=$|[\s<>{}\[\]()/\\|;:,])",
    r"\bplaceholder[-_ ]?(?:value|text|url|date|summary|literal|todo|tbd)\b",
    r"\bofficial_site_placeholder\b",
    r"\bname_typo_or_placeholder\b",
    r"\bplaceholder-like\b",
]

SKIP_BLOCKER_PATTERNS = [
    r"crypto(?:currency)?|digital[- ]asset|virtual[- ]asset",
    r"blockchain|\bweb3\b|\btoken\b|\bdao\b|\bnft\b|metaverse",
    r"\bdefi\b|decentralized finance",
    r"\bfintech\b|financial services|payments?|banking|insurance",
    r"capital markets|securities|derivatives|foreign exchange|\bfx\b|commodit(?:y|ies)",
    r"\binvest(?:or|ment|ing|s)?\b|\bfund\b|\bfunds\b|funding|portfolio|backer",
    r"venture capital|\bvc\b|private equity|\bpe\b|asset manager|asset management",
    r"family office|angel investor|accelerator|incubator|corporate venture",
    r"\botc\b",
    r"over[- ]the[- ]counter",
    r"\bblock trade",
    r"\brfq\b",
    r"off[- ]exchange",
    r"market[- ]making|market maker",
    r"liquidity provider|liquidity provision|liquidity[- ]provision",
    r"designated liquidity|designated market",
    r"\bbrokerage\b|\bbroker\b|prime broker",
    r"execution service|trade execution|order execution|order handling",
    r"matching engine|trading venue|\bexchange\b",
    r"\bdex\b|\bamm\b|swap protocol|perp dex",
    r"lending protocol|borrowing protocol|liquid staking|restaking|yield strategy",
    r"\bmev\b|liquidation|on[- ]chain arbitrage",
    r"algorithmic trading|quantitative trading|systematic trading",
    r"high[- ]frequency trading|\bhft\b|low[- ]latency trading|automated trading",
    r"sub[- ]fund|sub fund|fund[- ]of[- ]funds|\bfof\b",
    r"feeder fund|umbrella fund|parallel fund|protected cell|\bspv\b",
    r"venture arm|investment arm|crypto arm",
    r"proprietary capital|balance[- ]sheet venture|corporate venture arm",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate authoritative part6 final CSVs against canonical Part5-to-Part6 "
            "input order, schema, and deterministic skip/literal guards."
        ),
    )
    parser.add_argument("--batch-dir", type=Path, default=DEFAULT_BATCH_DIR)
    parser.add_argument("--schedule-csv", type=Path, default=None)
    parser.add_argument("--final-dir", type=Path, default=DEFAULT_FINAL_DIR)
    parser.add_argument("--results-csv", type=Path, default=None)
    parser.add_argument("--classifier-results-csv", type=Path, default=None)
    parser.add_argument("--expected-row-count", type=int, default=None)
    parser.add_argument("--max-errors", type=int, default=120)
    return parser.parse_args()


def resolve_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else (REPO_ROOT / path)


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        raise SystemExit(f"Missing CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def batch_sort_key(path: Path) -> int:
    try:
        return int(path.stem.split("_", 1)[1])
    except (IndexError, ValueError):
        return 0


def load_schedule_tasks(schedule_csv: Path) -> list[dict[str, Any]]:
    _, rows = read_csv(schedule_csv)
    tasks: list[dict[str, Any]] = []
    rows.sort(
        key=lambda row: (
            int(str(row.get("queue_order") or "0") or "0"),
            int(str(row.get("round_index") or "0") or "0"),
            str(row.get("batch_file") or ""),
        )
    )
    for row in rows:
        tasks_file = str(row.get("tasks_file") or "").strip()
        if not tasks_file:
            raise SystemExit(f"Schedule row is missing tasks_file: {row.get('batch_file')}")
        tasks.extend(load_jsonl(resolve_path(tasks_file)))
    return tasks


def load_batch_dir_tasks(batch_dir: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in sorted(batch_dir.glob("batch_*.jsonl"), key=batch_sort_key):
        tasks.extend(load_jsonl(path))
    return tasks


def task_identity(task: dict[str, Any]) -> dict[str, str]:
    return {
        "task_index": str(task.get("task_index") or ""),
        "investor_id": str(task.get("investor_id") or ""),
        "investor_name": str(task.get("investor_name") or ""),
        "normalized_domain": str(task.get("normalized_domain") or ""),
        "primary_investor_type": str(task.get("primary_investor_type") or ""),
    }


def input_search_text(task: dict[str, Any]) -> str:
    input_row = task.get("input_row")
    if not isinstance(input_row, dict):
        return ""
    fields = [
        "InvestorName",
        "InvestorAlsoKnownAs",
        "InvestorFormerName",
        "InvestorLegalName",
        "Website",
        "ParentCompany",
        "PrimaryInvestorType",
        "OtherInvestorTypes",
        "PreferredInvestmentTypes",
        "PreferredVerticals",
        "OtherInvestmentPreferences",
        "LastClosedFundName",
        "LastClosedFundType",
        "Description",
        "MatchedKeywords",
        "InvestorCapabilityContext",
    ]
    return " | ".join(str(input_row.get(field) or "") for field in fields).lower()


def has_skip_blocker_signal(task: dict[str, Any]) -> bool:
    text = input_search_text(task)
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in SKIP_BLOCKER_PATTERNS)


def contains_placeholder(value: str) -> bool:
    upper = value.upper()
    if any(pattern.upper() in upper for pattern in DANGEROUS_LITERAL_PATTERNS):
        return True
    return any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in SOFT_PLACEHOLDER_PATTERNS)


def url_contains_dangerous_literal(url: str) -> bool:
    upper = url.upper()
    return any(pattern.upper() in upper for pattern in DANGEROUS_LITERAL_PATTERNS)


def capability_labels_from_row(row: dict[str, str]) -> list[str]:
    return [column for column in CAPABILITY_FLAG_COLUMNS if row.get(column) == "yes"]


def validate_sequence(
    *,
    label: str,
    rows: list[dict[str, str]],
    expected_tasks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if len(rows) != len(expected_tasks):
        errors.append(f"{label}: expected {len(expected_tasks)} rows, found {len(rows)}")
        return
    for index, (row, task) in enumerate(zip(rows, expected_tasks), start=1):
        expected = task_identity(task)
        for field, expected_value in expected.items():
            actual = str(row.get(field) or "")
            if actual != expected_value:
                errors.append(
                    f"{label}: physical row {index + 1}: {field} mismatch; "
                    f"expected {expected_value!r}, found {actual!r}"
                )


def validate_literal_guards(label: str, rows: list[dict[str, str]], errors: list[str]) -> None:
    for row in rows:
        task_index = str(row.get("task_index") or "")
        for column, value in row.items():
            if column in IDENTITY_LITERAL_EXEMPT_COLUMNS:
                continue
            if column == "evidence_urls":
                continue
            text = str(value or "")
            if contains_placeholder(text):
                errors.append(f"{label}: task_index={task_index}: stale placeholder/literal in {column}")
        if label == "results":
            completed_at = str(row.get("completed_at") or "")
            if completed_at and not re.match(r"^\d{4}-\d{2}-\d{2}T", completed_at):
                errors.append(f"{label}: task_index={task_index}: completed_at is not an ISO-like timestamp")
            evidence_urls = str(row.get("evidence_urls") or "").strip()
            if evidence_urls == "[]":
                errors.append(f"{label}: task_index={task_index}: evidence_urls is JSON literal []")
            for url in [part.strip() for part in evidence_urls.split("|") if part.strip()]:
                if not url.startswith(("http://", "https://")):
                    errors.append(f"{label}: task_index={task_index}: evidence_urls contains non-http value")
                if url_contains_dangerous_literal(url):
                    errors.append(f"{label}: task_index={task_index}: evidence_urls contains shell/template literal")


def validate_skip_rules(
    *,
    classifier_rows: list[dict[str, str]],
    result_rows: list[dict[str, str]],
    expected_tasks: list[dict[str, Any]],
    errors: list[str],
) -> None:
    for classifier_row, result_row, task in zip(classifier_rows, result_rows, expected_tasks):
        task_index = str(task.get("task_index") or "")
        for label, row in [("classifier", classifier_row), ("results", result_row)]:
            search_tier = str(row.get("search_tier") or "")
            required = str(row.get("capability_search_required") or "")
            if search_tier == "skip_candidate" and required != "no":
                errors.append(f"{label}: task_index={task_index}: skip_candidate requires capability_search_required=no")
            if search_tier in {"full", "light"} and required != "yes":
                errors.append(f"{label}: task_index={task_index}: full/light requires capability_search_required=yes")
            if search_tier == "skip_candidate" and (
                row.get("crypto_native_likelihood") in {"high", "medium", "unclear"}
                or row.get("operating_capability_likelihood") in {"high", "medium", "unclear"}
            ):
                errors.append(f"{label}: task_index={task_index}: skip_candidate has high/medium/unclear likelihood")
            if search_tier == "skip_candidate" and has_skip_blocker_signal(task):
                errors.append(f"{label}: task_index={task_index}: skip_candidate violates deterministic capability signal guard")
        if result_row.get("search_tier") == "skip_candidate":
            if capability_labels_from_row(result_row):
                errors.append(f"results: task_index={task_index}: skip_candidate has positive capability labels")
            if str(result_row.get("evidence_urls") or "").strip():
                errors.append(f"results: task_index={task_index}: skip_candidate should not carry evidence_urls")


def validate_classifier_alignment(
    classifier_rows: list[dict[str, str]],
    result_rows: list[dict[str, str]],
    errors: list[str],
) -> None:
    classifier_by_task = {str(row.get("task_index") or ""): row for row in classifier_rows}
    result_by_task = {str(row.get("task_index") or ""): row for row in result_rows}
    if set(classifier_by_task) != set(result_by_task):
        missing_classifier = sorted(set(result_by_task) - set(classifier_by_task), key=int)
        missing_results = sorted(set(classifier_by_task) - set(result_by_task), key=int)
        if missing_classifier:
            errors.append(f"classifier_results.csv missing task_index values: {missing_classifier[:20]}")
        if missing_results:
            errors.append(f"results.csv missing task_index values: {missing_results[:20]}")
        return
    for task_index in sorted(classifier_by_task, key=int):
        classifier_row = classifier_by_task[task_index]
        result_row = result_by_task[task_index]
        for field in [
            "investor_id",
            "investor_name",
            "normalized_domain",
            "primary_investor_type",
            "investor_archetype",
            "crypto_native_likelihood",
            "operating_capability_likelihood",
            "search_tier",
            "capability_search_required",
        ]:
            if str(classifier_row.get(field) or "") != str(result_row.get(field) or ""):
                errors.append(f"task_index={task_index}: classifier/results mismatch in {field}")


def validate_result_labels(result_rows: list[dict[str, str]], errors: list[str]) -> None:
    for row in result_rows:
        task_index = str(row.get("task_index") or "")
        parsed_labels = [str(value) for value in parse_json_list(str(row.get("capability_labels") or ""))]
        expected_labels = capability_labels_from_row(row)
        if parsed_labels != expected_labels:
            errors.append(f"results: task_index={task_index}: capability_labels do not match yes-valued capability flags")
        for column in CAPABILITY_FLAG_COLUMNS:
            if row.get(column) not in {"yes", "no"}:
                errors.append(f"results: task_index={task_index}: {column} must be yes/no")


def validate_task_index_range(expected_tasks: list[dict[str, Any]], errors: list[str]) -> None:
    indexes: list[int] = []
    for task in expected_tasks:
        try:
            indexes.append(int(str(task.get("task_index") or "")))
        except ValueError:
            errors.append(f"input task has invalid task_index: {task.get('task_index')!r}")
    if not indexes:
        errors.append("input task set is empty")
        return
    expected = list(range(1, len(indexes) + 1))
    if indexes != expected:
        errors.append(
            f"input task_index sequence must be 1..{len(indexes)} in order; "
            f"found first={indexes[:5]} last={indexes[-5:]}"
        )


def main() -> None:
    args = parse_args()
    final_dir = args.final_dir.resolve()
    results_csv = args.results_csv.resolve() if args.results_csv else final_dir / "results.csv"
    classifier_csv = (
        args.classifier_results_csv.resolve()
        if args.classifier_results_csv
        else final_dir / "classifier_results.csv"
    )
    if args.schedule_csv:
        expected_tasks = load_schedule_tasks(args.schedule_csv.resolve())
        source_label = str(args.schedule_csv.resolve())
    else:
        expected_tasks = load_batch_dir_tasks(args.batch_dir.resolve())
        source_label = str(args.batch_dir.resolve())
    expected_count = args.expected_row_count if args.expected_row_count is not None else len(expected_tasks)

    result_header, result_rows = read_csv(results_csv)
    classifier_header, classifier_rows = read_csv(classifier_csv)
    errors: list[str] = []

    if result_header != RESULT_CSV_COLUMNS:
        errors.append("results.csv header does not match current schema")
    if classifier_header != CLASSIFIER_CSV_COLUMNS:
        errors.append("classifier_results.csv header does not match current schema")
    if len(expected_tasks) != expected_count:
        errors.append(f"canonical input count from {source_label} is {len(expected_tasks)}, expected {expected_count}")
    if len(result_rows) != expected_count:
        errors.append(f"results.csv row count is {len(result_rows)}, expected {expected_count}")
    if len(classifier_rows) != expected_count:
        errors.append(f"classifier_results.csv row count is {len(classifier_rows)}, expected {expected_count}")

    validate_task_index_range(expected_tasks, errors)
    validate_sequence(label="results", rows=result_rows, expected_tasks=expected_tasks, errors=errors)
    validate_sequence(label="classifier_results", rows=classifier_rows, expected_tasks=expected_tasks, errors=errors)
    validate_classifier_alignment(classifier_rows, result_rows, errors)
    validate_literal_guards("results", result_rows, errors)
    validate_literal_guards("classifier_results", classifier_rows, errors)
    validate_result_labels(result_rows, errors)
    validate_skip_rules(
        classifier_rows=classifier_rows,
        result_rows=result_rows,
        expected_tasks=expected_tasks,
        errors=errors,
    )

    print(f"Canonical input rows: {len(expected_tasks)}")
    print(f"Expected row count: {expected_count}")
    print(f"results.csv rows: {len(result_rows)}")
    print(f"classifier_results.csv rows: {len(classifier_rows)}")
    print(f"Validation errors: {len(errors)}")
    if errors:
        for error in errors[: args.max_errors]:
            print(f"- {error}")
        if len(errors) > args.max_errors:
            print(f"- ... {len(errors) - args.max_errors} more")
        raise SystemExit("Final output validation failed.")


if __name__ == "__main__":
    main()
