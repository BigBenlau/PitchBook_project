from __future__ import annotations

import json
from typing import Any


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
    "token_results",
    "token_decision_reason",
    "include_rule_A",
    "rule_A_token_results",
    "rule_A_decision_reason",
    "include_rule_B",
    "rule_B_token_results",
    "rule_B_decision_reason",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
]

LEGACY_RESULT_CSV_COLUMNS_WITH_RULES = [
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
    "include_rule_A",
    "rule_A_token_symbol",
    "rule_A_token_name",
    "rule_A_reason",
    "rule_A_evidence_urls",
    "include_rule_B",
    "rule_B_token_symbol",
    "rule_B_token_name",
    "rule_B_reason",
    "rule_B_evidence_urls",
    "token_url",
    "has_token_evidence",
    "evidence_urls",
    "evidence_source_types",
    "confidence",
    "needs_manual_review",
]

LEGACY_RESULT_CSV_COLUMNS_NO_RULES = [
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

VERIFICATION_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "classifier_search_tier",
    "worker_token_results",
    "verifier_search_tier",
    "verifier_token_results",
    "worker_rule_A_token_results",
    "verifier_rule_A_token_results",
    "worker_rule_B_token_results",
    "verifier_rule_B_token_results",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_urls",
    "recommended_action",
    "corrected_result_row_json",
]

LEGACY_VERIFICATION_CSV_COLUMNS = [
    "task_index",
    "company_id",
    "company_name",
    "classifier_search_tier",
    "worker_token_ticker",
    "verifier_search_tier",
    "verifier_token_ticker",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_urls",
    "recommended_action",
    "corrected_result_row_json",
]

TOKEN_RESULT_COLUMNS = [
    "token_results",
    "rule_A_token_results",
    "rule_B_token_results",
]

JSON_LIST_COLUMNS = [
    "project_name",
    "project_url",
    *TOKEN_RESULT_COLUMNS,
]


def parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    raw = str(value or "").strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def json_list_string(value: Any) -> str:
    if isinstance(value, str):
        parsed = parse_json_list(value)
        if parsed or value.strip() == "[]":
            return json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        return "[]"
    if isinstance(value, list):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return "[]"


def split_pipe_list(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split("|") if item.strip()]


def _legacy_list(row: dict[str, Any], column: str) -> list[str]:
    return [str(item) for item in parse_json_list(row.get(column, ""))]


def _legacy_token_results(row: dict[str, Any]) -> list[dict[str, Any]]:
    symbols = _legacy_list(row, "token_ticker")
    names = _legacy_list(row, "token_name")
    urls = _legacy_list(row, "token_url")
    evidence_urls = split_pipe_list(row.get("evidence_urls", ""))
    source_types = split_pipe_list(row.get("evidence_source_types", ""))
    results: list[dict[str, Any]] = []
    for index, symbol in enumerate(symbols):
        results.append(
            {
                "token_symbol": symbol,
                "token_name": names[index] if index < len(names) else "",
                "token_url": urls[index] if index < len(urls) else "",
                "reason": str(row.get("project_search_reason", "") or ""),
                "evidence_urls": evidence_urls,
                "evidence_source_types": source_types,
            }
        )
    return results


def _legacy_rule_results(row: dict[str, Any], rule: str) -> list[dict[str, Any]]:
    prefix = f"rule_{rule}"
    symbols = _legacy_list(row, f"{prefix}_token_symbol")
    names = _legacy_list(row, f"{prefix}_token_name")
    reasons = _legacy_list(row, f"{prefix}_reason")
    evidence_urls = split_pipe_list(row.get(f"{prefix}_evidence_urls", ""))
    results: list[dict[str, Any]] = []
    for index, symbol in enumerate(symbols):
        results.append(
            {
                "token_symbol": symbol,
                "token_name": names[index] if index < len(names) else "",
                "token_url": "",
                "reason": reasons[index] if index < len(reasons) else "",
                "evidence_urls": evidence_urls,
                "evidence_source_types": [],
            }
        )
    return results


def migrate_legacy_result_row(row: dict[str, Any]) -> dict[str, str]:
    migrated = {column: str(row.get(column, "") or "") for column in RESULT_CSV_COLUMNS}
    migrated["token_results"] = json.dumps(_legacy_token_results(row), ensure_ascii=False, separators=(",", ":"))
    migrated["token_decision_reason"] = str(row.get("project_search_reason", "") or "")
    for rule in ["A", "B"]:
        include_column = f"include_rule_{rule}"
        result_column = f"rule_{rule}_token_results"
        reason_column = f"rule_{rule}_decision_reason"
        legacy_reason_values = _legacy_list(row, f"rule_{rule}_reason")
        migrated[include_column] = str(row.get(include_column, "") or "pending")
        migrated[result_column] = json.dumps(
            _legacy_rule_results(row, rule),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        migrated[reason_column] = "; ".join(legacy_reason_values)
    return migrated
