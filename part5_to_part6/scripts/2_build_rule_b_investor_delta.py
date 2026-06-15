#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Iterable


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_TO_PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_TO_PART6_DIR.parent
BASE_BUILDER_PATH = SCRIPT_DIR / "1_build_part6_investor_input.py"

DEFAULT_PART5_RESULTS = (
    REPO_ROOT
    / "part5_analyse_company_to_token"
    / "agent_runs"
    / "crypto_company"
    / "results.csv"
)
DEFAULT_PITCHBOOK_DIR = REPO_ROOT / "STANFORD_20260201"
DEFAULT_CURRENT_PART6_INPUT = PART5_TO_PART6_DIR / "output" / "part6_investor_input.csv"
DEFAULT_CURRENT_AUDIT = PART5_TO_PART6_DIR / "output" / "investor_candidate_audit.csv"
DEFAULT_OUTPUT_DIR = PART5_TO_PART6_DIR / "output" / "rule_b_delta"

RULE_B_COMPANY_COLUMNS = [
    "company_id",
    "company_name",
    "normalized_domain",
    "company_type",
    "include_rule_B",
    "rule_B_token_ticker",
    "rule_B_token_name",
    "rule_B_token_url",
    "confidence",
    "needs_manual_review",
]

MEMBERSHIP_COLUMNS = [
    "InvestorID",
    "InvestorName",
    "delta_status",
    "in_current_list",
    "in_rule_b_list",
    "current_task_index",
    "rule_b_task_index",
    "current_token_company_count",
    "rule_b_company_count",
    "current_source_methods",
    "rule_b_source_methods",
    "PrimaryInvestorType",
    "Website",
    "normalized_domain",
]

REMOVAL_COLUMNS = [
    "InvestorID",
    "InvestorName",
    "current_task_index",
    "PrimaryInvestorType",
    "Website",
    "normalized_domain",
    "current_token_company_count",
    "current_source_methods",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the Rule B investor universe with the same four PitchBook paths as "
            "part5_to_part6, then compare it with the current Part6 investor input."
        )
    )
    parser.add_argument("--part5-results-csv", type=Path, default=DEFAULT_PART5_RESULTS)
    parser.add_argument("--pitchbook-dir", type=Path, default=DEFAULT_PITCHBOOK_DIR)
    parser.add_argument("--current-part6-input", type=Path, default=DEFAULT_CURRENT_PART6_INPUT)
    parser.add_argument("--current-audit-csv", type=Path, default=DEFAULT_CURRENT_AUDIT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--description-max-chars", type=int, default=700)
    parser.add_argument("--context-max-chars", type=int, default=400)
    parser.add_argument(
        "--require-investor-metadata",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Drop Rule B investor IDs that are not present in Investor.csv.",
    )
    return parser.parse_args()


def load_base_builder() -> ModuleType:
    module_name = "part5_to_part6_base_builder"
    spec = importlib.util.spec_from_file_location(module_name, BASE_BUILDER_PATH)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load base builder: {BASE_BUILDER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.is_file():
        raise SystemExit(f"{label} does not exist or is not a file: {resolved}")
    return resolved


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})


def parse_token_objects(raw: str) -> list[dict[str, str]]:
    value = (raw or "").strip()
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid rule_B_token_results JSON: {exc}: {value[:200]}") from exc
    if not isinstance(parsed, list):
        raise SystemExit("rule_B_token_results must be a JSON list")
    return [item for item in parsed if isinstance(item, dict)]


def unique_nonempty(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = " ".join((value or "").split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def load_rule_b_companies(
    path: Path,
    base: ModuleType,
) -> tuple[dict[str, object], list[dict[str, str]]]:
    companies: dict[str, object] = {}
    output_rows: list[dict[str, str]] = []
    for row in read_csv(path):
        if (row.get("include_rule_B") or "").strip() != "yes":
            continue
        token_objects = parse_token_objects(row.get("rule_B_token_results", ""))
        if not token_objects:
            raise SystemExit(
                "Rule B positive row has no token objects: "
                f"task_index={row.get('task_index', '')} company_id={row.get('company_id', '')}"
            )
        company_id = base.normalize_text(row.get("company_id"))
        if not company_id:
            continue
        tickers = unique_nonempty(item.get("token_symbol", "") for item in token_objects)
        names = unique_nonempty(item.get("token_name", "") for item in token_objects)
        urls = unique_nonempty(item.get("token_url", "") for item in token_objects)
        company = base.TokenCompany(
            company_id=company_id,
            company_name=base.normalize_text(row.get("company_name")),
            normalized_domain=base.normalize_text(row.get("normalized_domain")),
            company_type=base.normalize_text(row.get("company_type")),
            token_ticker=json.dumps(tickers, ensure_ascii=False),
            token_name=json.dumps(names, ensure_ascii=False),
            token_url=json.dumps(urls, ensure_ascii=False),
            confidence=base.normalize_text(row.get("confidence")),
            needs_manual_review=base.normalize_text(row.get("needs_manual_review")),
        )
        companies[company_id] = company
        output_rows.append(
            {
                "company_id": company_id,
                "company_name": company.company_name,
                "normalized_domain": company.normalized_domain,
                "company_type": company.company_type,
                "include_rule_B": "yes",
                "rule_B_token_ticker": company.token_ticker,
                "rule_B_token_name": company.token_name,
                "rule_B_token_url": company.token_url,
                "confidence": company.confidence,
                "needs_manual_review": company.needs_manual_review,
            }
        )
    output_rows.sort(key=lambda item: item["company_id"])
    return companies, output_rows


def collect_rule_b_investors(
    base: ModuleType,
    pitchbook_dir: Path,
    companies: dict[str, object],
) -> tuple[dict[str, object], dict[str, dict[str, str]], dict[str, list[dict[str, str]]]]:
    evidence: dict[str, object] = {}
    base.collect_company_investors(pitchbook_dir, companies, evidence)
    deals = base.load_deals_for_companies(pitchbook_dir, companies)
    base.collect_deal_investors(pitchbook_dir, companies, deals, evidence)
    base.collect_investor_investment_relation(pitchbook_dir, companies, evidence)
    fund_hits = base.collect_fund_investment_relation(pitchbook_dir, companies)
    fund_names = base.load_fund_names(pitchbook_dir, set(fund_hits))
    base.collect_fund_investors(pitchbook_dir, companies, fund_hits, fund_names, evidence)
    return evidence, deals, fund_hits


def reindex_rows(rows: Iterable[dict[str, str]], columns: list[str]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=1):
        normalized = {column: row.get(column, "") for column in columns}
        normalized["task_index"] = str(index)
        output.append(normalized)
    return output


def map_unique(rows: list[dict[str, str]], key: str, label: str) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        value = (row.get(key) or "").strip()
        if not value:
            raise SystemExit(f"{label} contains a blank {key}")
        if value in result:
            raise SystemExit(f"{label} contains duplicate {key}: {value}")
        result[value] = row
    return result


def audit_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        (row.get("InvestorID") or "").strip(): row
        for row in rows
        if (row.get("InvestorID") or "").strip()
    }


def build_membership_rows(
    current_by_id: dict[str, dict[str, str]],
    rule_b_by_id: dict[str, dict[str, str]],
    current_audit: dict[str, dict[str, str]],
    rule_b_audit: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for investor_id in sorted(set(current_by_id) | set(rule_b_by_id)):
        current = current_by_id.get(investor_id, {})
        rule_b = rule_b_by_id.get(investor_id, {})
        current_evidence = current_audit.get(investor_id, {})
        rule_b_evidence = rule_b_audit.get(investor_id, {})
        if current and rule_b:
            status = "intersection"
        elif rule_b:
            status = "rule_b_only_added"
        else:
            status = "current_only_removed"
        preferred = rule_b or current
        rows.append(
            {
                "InvestorID": investor_id,
                "InvestorName": preferred.get("InvestorName", ""),
                "delta_status": status,
                "in_current_list": "yes" if current else "no",
                "in_rule_b_list": "yes" if rule_b else "no",
                "current_task_index": current.get("task_index", ""),
                "rule_b_task_index": rule_b.get("task_index", ""),
                "current_token_company_count": current_evidence.get("token_company_count", ""),
                "rule_b_company_count": rule_b_evidence.get("token_company_count", ""),
                "current_source_methods": current_evidence.get("source_methods", ""),
                "rule_b_source_methods": rule_b_evidence.get("source_methods", ""),
                "PrimaryInvestorType": preferred.get("PrimaryInvestorType", ""),
                "Website": preferred.get("Website", ""),
                "normalized_domain": preferred.get("normalized_domain", ""),
            }
        )
    status_order = {"rule_b_only_added": 0, "current_only_removed": 1, "intersection": 2}
    return sorted(
        rows,
        key=lambda row: (
            status_order[row["delta_status"]],
            row["InvestorName"].lower(),
            row["InvestorID"],
        ),
    )


def source_counts(evidence_by_investor: dict[str, object]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for evidence in evidence_by_investor.values():
        counts.update(evidence.source_methods)
    return dict(counts)


def unique_investor_counts_by_method(evidence_by_investor: dict[str, object]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for evidence in evidence_by_investor.values():
        counts.update(evidence.source_methods.keys())
    return dict(counts)


def main() -> None:
    args = parse_args()
    base = load_base_builder()
    part5_results = ensure_file(args.part5_results_csv, "part5_results_csv")
    current_part6_input = ensure_file(args.current_part6_input, "current_part6_input")
    current_audit_csv = ensure_file(args.current_audit_csv, "current_audit_csv")
    pitchbook_dir = args.pitchbook_dir.resolve()
    if not pitchbook_dir.is_dir():
        raise SystemExit(f"pitchbook_dir does not exist or is not a directory: {pitchbook_dir}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    rule_b_companies, rule_b_company_rows = load_rule_b_companies(part5_results, base)
    if not rule_b_companies:
        raise SystemExit("No include_rule_B=yes companies were found.")

    evidence, deals, fund_hits = collect_rule_b_investors(base, pitchbook_dir, rule_b_companies)
    metadata = base.load_investor_metadata(pitchbook_dir, set(evidence))
    rule_b_rows = base.build_part6_rows(
        evidence,
        metadata,
        require_metadata=args.require_investor_metadata,
        description_max_chars=args.description_max_chars,
        context_max_chars=args.context_max_chars,
    )
    for row in rule_b_rows:
        row["MatchedKeywords"] = row["MatchedKeywords"].replace(
            "part5_token_company", "part5_rule_b_company"
        )
        row["InvestorCapabilityContext"] = row["InvestorCapabilityContext"].replace(
            "Part5 token-company investor graph", "Part5 Rule B company investor graph"
        )

    current_rows = read_csv(current_part6_input)
    current_by_id = map_unique(current_rows, "InvestorID", "current Part6 input")
    rule_b_by_id = map_unique(rule_b_rows, "InvestorID", "Rule B Part6 input")

    current_audit_rows = read_csv(current_audit_csv)
    rule_b_audit_rows = base.build_audit_rows(evidence)
    current_audit_by_id = audit_map(current_audit_rows)
    rule_b_audit_by_id = audit_map(rule_b_audit_rows)

    added_ids = set(rule_b_by_id) - set(current_by_id)
    removed_ids = set(current_by_id) - set(rule_b_by_id)
    intersection_ids = set(current_by_id) & set(rule_b_by_id)

    added_rows = reindex_rows(
        (row for row in rule_b_rows if row["InvestorID"] in added_ids),
        base.PART6_INPUT_COLUMNS,
    )
    intersection_rows = reindex_rows(
        (row for row in rule_b_rows if row["InvestorID"] in intersection_ids),
        base.PART6_INPUT_COLUMNS,
    )
    removal_rows = []
    for row in current_rows:
        investor_id = row["InvestorID"]
        if investor_id not in removed_ids:
            continue
        audit = current_audit_by_id.get(investor_id, {})
        removal_rows.append(
            {
                "InvestorID": investor_id,
                "InvestorName": row.get("InvestorName", ""),
                "current_task_index": row.get("task_index", ""),
                "PrimaryInvestorType": row.get("PrimaryInvestorType", ""),
                "Website": row.get("Website", ""),
                "normalized_domain": row.get("normalized_domain", ""),
                "current_token_company_count": audit.get("token_company_count", ""),
                "current_source_methods": audit.get("source_methods", ""),
            }
        )

    membership_rows = build_membership_rows(
        current_by_id,
        rule_b_by_id,
        current_audit_by_id,
        rule_b_audit_by_id,
    )
    missing_metadata = sorted(set(evidence) - set(metadata))

    outputs = {
        "rule_b_company_universe_csv": output_dir / "rule_b_company_universe.csv",
        "rule_b_investor_candidate_audit_csv": output_dir / "rule_b_investor_candidate_audit.csv",
        "rule_b_part6_investor_input_csv": output_dir / "rule_b_part6_investor_input.csv",
        "rule_b_only_added_part6_input_csv": output_dir / "rule_b_only_added_part6_input.csv",
        "current_only_removed_investors_csv": output_dir / "current_only_removed_investors.csv",
        "intersection_part6_input_csv": output_dir / "intersection_part6_input.csv",
        "investor_membership_delta_csv": output_dir / "investor_membership_delta.csv",
        "summary_json": output_dir / "summary.json",
    }

    write_csv(outputs["rule_b_company_universe_csv"], RULE_B_COMPANY_COLUMNS, rule_b_company_rows)
    write_csv(
        outputs["rule_b_investor_candidate_audit_csv"],
        base.AUDIT_COLUMNS,
        rule_b_audit_rows,
    )
    write_csv(
        outputs["rule_b_part6_investor_input_csv"],
        base.PART6_INPUT_COLUMNS,
        reindex_rows(rule_b_rows, base.PART6_INPUT_COLUMNS),
    )
    write_csv(
        outputs["rule_b_only_added_part6_input_csv"],
        base.PART6_INPUT_COLUMNS,
        added_rows,
    )
    write_csv(outputs["current_only_removed_investors_csv"], REMOVAL_COLUMNS, removal_rows)
    write_csv(
        outputs["intersection_part6_input_csv"],
        base.PART6_INPUT_COLUMNS,
        intersection_rows,
    )
    write_csv(outputs["investor_membership_delta_csv"], MEMBERSHIP_COLUMNS, membership_rows)

    summary = {
        "rule_b_company_count": len(rule_b_companies),
        "rule_b_company_deal_count": len(deals),
        "rule_b_fund_count": len(fund_hits),
        "rule_b_investor_candidates_before_metadata_filter": len(evidence),
        "rule_b_investors_with_metadata": len(rule_b_by_id),
        "rule_b_missing_investor_metadata_count": len(missing_metadata),
        "rule_b_missing_investor_metadata_ids": missing_metadata,
        "current_investor_count": len(current_by_id),
        "rule_b_investor_count": len(rule_b_by_id),
        "intersection_investor_count": len(intersection_ids),
        "rule_b_only_added_investor_count": len(added_ids),
        "current_only_removed_investor_count": len(removed_ids),
        "net_investor_count_change": len(rule_b_by_id) - len(current_by_id),
        "rule_b_source_relationship_counts": source_counts(evidence),
        "rule_b_unique_investor_counts_by_method": unique_investor_counts_by_method(evidence),
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    outputs["summary_json"].write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Rule B companies: {len(rule_b_companies)}")
    print(f"Rule B investor candidates: {len(evidence)}")
    print(f"Rule B investors with metadata: {len(rule_b_by_id)}")
    print(f"Current investors: {len(current_by_id)}")
    print(f"Intersection: {len(intersection_ids)}")
    print(f"Rule B only added: {len(added_ids)}")
    print(f"Current only removed: {len(removed_ids)}")
    print(f"Net change: {len(rule_b_by_id) - len(current_by_id):+d}")
    print(f"Output: {output_dir}")


if __name__ == "__main__":
    main()
