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
    "verdict",
    "error_type",
    "error_reason",
    "evidence_urls",
    "recommended_action",
    "corrected_result_row_json",
]

TOKEN_RESULT_COLUMNS = [
    "token_results",
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
