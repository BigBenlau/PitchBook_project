#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any


CAPABILITY_FLAG_COLUMNS = [
    "otc_trading",
    "algorithm_trading",
    "market_making",
    "execution_services",
    "defi",
    "sub_fund",
]

RESULT_CSV_COLUMNS = [
    "task_index",
    "investor_id",
    "investor_name",
    "normalized_domain",
    "primary_investor_type",
    "investor_archetype",
    "crypto_native_likelihood",
    "operating_capability_likelihood",
    "search_tier",
    "capability_search_required",
    "capability_search_reason",
    "status",
    "completed_at",
    "capability_labels",
    *CAPABILITY_FLAG_COLUMNS,
    "other_flags",
    "evidence_urls",
    "evidence_source_types",
    "evidence_summary",
    "confidence",
    "needs_manual_review",
]

CLASSIFIER_CSV_COLUMNS = [
    "task_index",
    "investor_id",
    "investor_name",
    "normalized_domain",
    "primary_investor_type",
    "investor_archetype",
    "crypto_native_likelihood",
    "operating_capability_likelihood",
    "search_tier",
    "capability_search_required",
    "risk_flags",
    "classifier_reason",
]

VERIFICATION_CSV_COLUMNS = [
    "task_index",
    "investor_id",
    "investor_name",
    "classifier_search_tier",
    "worker_capability_labels",
    "verifier_search_tier",
    "verifier_capability_labels",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_urls",
    "recommended_action",
    "corrected_result_row_json",
]

ALLOWED_INVESTOR_ARCHETYPES = {
    "traditional_vc_or_pe",
    "crypto_native_vc",
    "hedge_fund_or_quant",
    "market_maker_or_otc_firm",
    "asset_manager_or_family_office",
    "accelerator_or_incubator",
    "angel_or_individual",
    "exchange_affiliated_investor",
    "operating_company_disguised_as_investor",
    "fund_vehicle_or_fund_platform",
    "unclear",
}

ALLOWED_LIKELIHOODS = {"high", "medium", "low", "none", "unclear"}
ALLOWED_YES_NO = {"yes", "no"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_SEARCH_TIERS = {"full", "light", "skip_candidate"}

ALLOWED_VERDICTS = {
    "pass",
    "suspected_missing_capability",
    "suspected_extra_capability",
    "wrong_archetype_or_mapping",
    "search_tier_too_conservative",
    "search_should_not_have_been_skipped",
    "insufficient_evidence",
}

ALLOWED_VERIFICATION_ACTIONS = {
    "accept_worker_row",
    "edit_row",
    "mark_manual_review",
    "rerun_investor",
    "rerun_batch",
    "update_prompt_or_process",
}

BLOCKING_VERIFICATION_ACTIONS = {
    "edit_row",
    "rerun_investor",
    "rerun_batch",
    "update_prompt_or_process",
}


def parse_json_list(raw: str) -> list[Any]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def to_json_list_string(values: list[str]) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return json.dumps(cleaned, ensure_ascii=False)


def capability_labels_from_row(row: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for column in CAPABILITY_FLAG_COLUMNS:
        if str(row.get(column, "")).strip() == "yes":
            labels.append(column)
    return labels


def ensure_capability_labels(row: dict[str, Any]) -> dict[str, Any]:
    labels = capability_labels_from_row(row)
    row["capability_labels"] = to_json_list_string(labels)
    return row
