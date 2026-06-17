#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
PART5_TO_PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART5_TO_PART6_DIR.parent
PITCHBOOK_DIR = REPO_ROOT / "STANFORD_20260201"

DEFAULT_PART5_RESULTS = REPO_ROOT / "part5_analyse_company_to_token" / "agent_runs" / "crypto_company" / "results.csv"
DEFAULT_OUTPUT_DIR = PART5_TO_PART6_DIR / "output"
DEFAULT_BATCH_SIZE = 30

SEARCH_POLICY = "part5_token_company_investor_graph_then_web_search_with_primary_source_priority"
AGENT_TASK_SCOPE = "investor_router|capability_classification"

PART6_INPUT_COLUMNS = [
    "task_index",
    "InvestorID",
    "InvestorName",
    "InvestorAlsoKnownAs",
    "InvestorFormerName",
    "InvestorLegalName",
    "Website",
    "normalized_domain",
    "ParentCompany",
    "Exchange",
    "Ticker",
    "HQLocation",
    "HQCountry",
    "PrimaryInvestorType",
    "OtherInvestorTypes",
    "PreferredInvestmentTypes",
    "PreferredVerticals",
    "OtherInvestmentPreferences",
    "LastClosedFundName",
    "LastClosedFundType",
    "Description",
    "MatchedKeywords",
    "MatchedColumns",
    "InvestorCapabilityContext",
    "SearchPolicy",
    "AgentTaskScope",
]

TOKEN_COMPANY_COLUMNS = [
    "company_id",
    "company_name",
    "normalized_domain",
    "company_type",
    "token_symbols",
    "token_names",
    "token_urls",
    "token_results",
    "confidence",
    "needs_manual_review",
]

AUDIT_COLUMNS = [
    "InvestorID",
    "InvestorName",
    "source_methods",
    "source_count",
    "token_company_count",
    "deal_count",
    "lead_deal_count",
    "fund_count",
    "token_company_ids",
    "token_company_names",
    "deal_ids",
    "fund_ids",
    "matched_keywords",
    "matched_columns",
    "context",
]


@dataclass
class TokenCompany:
    company_id: str
    company_name: str
    normalized_domain: str
    company_type: str
    token_symbols: str
    token_names: str
    token_urls: str
    token_results: str
    confidence: str
    needs_manual_review: str


@dataclass
class InvestorEvidence:
    investor_id: str
    investor_names: Counter[str] = field(default_factory=Counter)
    source_methods: Counter[str] = field(default_factory=Counter)
    company_ids: set[str] = field(default_factory=set)
    company_names: Counter[str] = field(default_factory=Counter)
    deal_ids: set[str] = field(default_factory=set)
    lead_deal_ids: set[str] = field(default_factory=set)
    fund_ids: set[str] = field(default_factory=set)
    context_parts: list[str] = field(default_factory=list)

    def add(
        self,
        *,
        source_method: str,
        investor_name: str = "",
        company_id: str = "",
        company_name: str = "",
        deal_id: str = "",
        is_lead: str = "",
        fund_id: str = "",
        context: str = "",
    ) -> None:
        if investor_name:
            self.investor_names[normalize_text(investor_name)] += 1
        self.source_methods[source_method] += 1
        if company_id:
            self.company_ids.add(company_id)
        if company_name:
            self.company_names[normalize_text(company_name)] += 1
        if deal_id:
            self.deal_ids.add(deal_id)
            if normalize_bool(is_lead):
                self.lead_deal_ids.add(deal_id)
        if fund_id:
            self.fund_ids.add(fund_id)
        if context:
            self.context_parts.append(normalize_text(context))

    @property
    def display_name(self) -> str:
        if not self.investor_names:
            return ""
        return self.investor_names.most_common(1)[0][0]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Part6 investor input CSV from Part5 token-bearing companies.",
    )
    parser.add_argument("--part5-results-csv", type=Path, default=DEFAULT_PART5_RESULTS)
    parser.add_argument("--pitchbook-dir", type=Path, default=PITCHBOOK_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--description-max-chars", type=int, default=700)
    parser.add_argument("--context-max-chars", type=int, default=400)
    parser.add_argument(
        "--require-investor-metadata",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Drop investor IDs that are not present in Investor.csv.",
    )
    return parser.parse_args()


def normalize_text(value: str | None) -> str:
    return " ".join((value or "").split())


def truncate_text(value: str, max_chars: int) -> str:
    value = normalize_text(value)
    if max_chars <= 0 or len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip()


def normalize_bool(value: str | None) -> bool:
    return normalize_text(value).lower() in {"yes", "true", "1", "y"}


def parse_token_results(value: str | None) -> list[dict[str, str]]:
    raw = normalize_text(value)
    if not raw or raw == "[]":
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid token_results JSON: {exc}: {raw[:200]}") from exc
    if not isinstance(parsed, list):
        raise SystemExit("token_results must be a JSON list")
    token_objects: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        normalized = {
            "token_symbol": normalize_text(str(item.get("token_symbol", ""))),
            "token_name": normalize_text(str(item.get("token_name", ""))),
            "token_url": normalize_text(str(item.get("token_url", ""))),
        }
        for optional_key in ["reason", "evidence_urls", "evidence_source_types"]:
            if optional_key in item:
                value = item[optional_key]
                if isinstance(value, list):
                    normalized[optional_key] = [
                        normalize_text(str(entry)) for entry in value if normalize_text(str(entry))
                    ]
                else:
                    normalized[optional_key] = normalize_text(str(value))
        if normalized["token_symbol"] or normalized["token_name"] or normalized["token_url"]:
            token_objects.append(normalized)
    return token_objects


def unique_nonempty(values: Iterable[str], limit: int = 0) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = normalize_text(value)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if limit > 0 and len(result) >= limit:
            break
    return result


def derive_normalized_domain(website: str) -> str:
    raw = normalize_text(website)
    if not raw:
        return ""
    candidate = raw if "://" in raw else f"https://{raw}"
    parsed = urlparse(candidate)
    host = (parsed.netloc or parsed.path).strip().lower()
    return host[4:] if host.startswith("www.") else host


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def iter_csv(path: Path) -> Iterable[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        yield from csv.DictReader(infile)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in fieldnames})


def load_token_companies(part5_results_csv: Path) -> dict[str, TokenCompany]:
    token_companies: dict[str, TokenCompany] = {}
    for row in iter_csv(part5_results_csv):
        company_id = normalize_text(row.get("company_id"))
        token_objects = parse_token_results(row.get("token_results"))
        if not company_id or not token_objects:
            continue
        token_symbols = unique_nonempty(item.get("token_symbol", "") for item in token_objects)
        token_names = unique_nonempty(item.get("token_name", "") for item in token_objects)
        token_urls = unique_nonempty(item.get("token_url", "") for item in token_objects)
        token_companies[company_id] = TokenCompany(
            company_id=company_id,
            company_name=normalize_text(row.get("company_name")),
            normalized_domain=normalize_text(row.get("normalized_domain")),
            company_type=normalize_text(row.get("company_type")),
            token_symbols=json.dumps(token_symbols, ensure_ascii=False),
            token_names=json.dumps(token_names, ensure_ascii=False),
            token_urls=json.dumps(token_urls, ensure_ascii=False),
            token_results=json.dumps(token_objects, ensure_ascii=False),
            confidence=normalize_text(row.get("confidence")),
            needs_manual_review=normalize_text(row.get("needs_manual_review")),
        )
    return token_companies


def load_deals_for_companies(pitchbook_dir: Path, token_companies: dict[str, TokenCompany]) -> dict[str, dict[str, str]]:
    deals: dict[str, dict[str, str]] = {}
    company_ids = set(token_companies)
    for row in iter_csv(pitchbook_dir / "Deal.csv"):
        company_id = normalize_text(row.get("CompanyID"))
        deal_id = normalize_text(row.get("DealID"))
        if company_id in company_ids and deal_id:
            deals[deal_id] = {
                "DealID": deal_id,
                "CompanyID": company_id,
                "CompanyName": normalize_text(row.get("CompanyName")),
                "DealDate": normalize_text(row.get("DealDate")),
                "DealType": normalize_text(row.get("DealType")),
                "DealClass": normalize_text(row.get("DealClass")),
                "DealSize": normalize_text(row.get("DealSize")),
            }
    return deals


def add_investor(evidence: dict[str, InvestorEvidence], investor_id: str, **kwargs: str) -> None:
    investor_id = normalize_text(investor_id)
    if not investor_id:
        return
    if investor_id not in evidence:
        evidence[investor_id] = InvestorEvidence(investor_id=investor_id)
    evidence[investor_id].add(**kwargs)


def collect_company_investors(
    pitchbook_dir: Path,
    token_companies: dict[str, TokenCompany],
    evidence: dict[str, InvestorEvidence],
) -> None:
    company_ids = set(token_companies)
    for row in iter_csv(pitchbook_dir / "CompanyInvestorRelation.csv"):
        company_id = normalize_text(row.get("CompanyID"))
        if company_id not in company_ids:
            continue
        company = token_companies[company_id]
        add_investor(
            evidence,
            row.get("InvestorID", ""),
            source_method="company_investor_relation",
            investor_name=row.get("InvestorName", ""),
            company_id=company_id,
            company_name=company.company_name or row.get("CompanyName", ""),
            context=(
                f"CompanyInvestorRelation: {company.company_name}; "
                f"status={normalize_text(row.get('InvestorStatus'))}; "
                f"holding={normalize_text(row.get('Holding'))}; "
                f"since={normalize_text(row.get('InvestorSince'))}"
            ),
        )


def collect_deal_investors(
    pitchbook_dir: Path,
    token_companies: dict[str, TokenCompany],
    deals: dict[str, dict[str, str]],
    evidence: dict[str, InvestorEvidence],
) -> None:
    for row in iter_csv(pitchbook_dir / "DealInvestorRelation.csv"):
        deal_id = normalize_text(row.get("DealID"))
        deal = deals.get(deal_id)
        if not deal:
            continue
        company = token_companies[deal["CompanyID"]]
        add_investor(
            evidence,
            row.get("InvestorID", ""),
            source_method="deal_investor_relation",
            investor_name=row.get("InvestorName", ""),
            company_id=company.company_id,
            company_name=company.company_name or deal.get("CompanyName", ""),
            deal_id=deal_id,
            is_lead=row.get("IsLeadInvestor", ""),
            fund_id=row.get("InvestorFundID", ""),
            context=(
                f"DealInvestorRelation: {company.company_name}; "
                f"deal={deal_id}; date={deal.get('DealDate')}; type={deal.get('DealType')}; "
                f"lead={normalize_text(row.get('IsLeadInvestor'))}; fund={normalize_text(row.get('InvestorFundName'))}"
            ),
        )


def collect_investor_investment_relation(
    pitchbook_dir: Path,
    token_companies: dict[str, TokenCompany],
    evidence: dict[str, InvestorEvidence],
) -> None:
    company_ids = set(token_companies)
    for row in iter_csv(pitchbook_dir / "InvestorInvestmentRelation.csv"):
        company_id = normalize_text(row.get("CompanyID"))
        if company_id not in company_ids:
            continue
        company = token_companies[company_id]
        add_investor(
            evidence,
            row.get("InvestorID", ""),
            source_method="investor_investment_relation",
            company_id=company_id,
            company_name=company.company_name or row.get("CompanyName", ""),
            deal_id=row.get("DealID", ""),
            context=(
                f"InvestorInvestmentRelation: {company.company_name}; "
                f"deal={normalize_text(row.get('DealID'))}; date={normalize_text(row.get('DealDate'))}; "
                f"type={normalize_text(row.get('DealType'))}; co_investors={normalize_text(row.get('CoInvestors'))}"
            ),
        )


def collect_fund_investment_relation(
    pitchbook_dir: Path,
    token_companies: dict[str, TokenCompany],
) -> dict[str, list[dict[str, str]]]:
    company_ids = set(token_companies)
    fund_hits: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in iter_csv(pitchbook_dir / "FundInvestmentRelation.csv"):
        company_id = normalize_text(row.get("CompanyID"))
        fund_id = normalize_text(row.get("FundID"))
        if company_id in company_ids and fund_id:
            fund_hits[fund_id].append(
                {
                    "FundID": fund_id,
                    "CompanyID": company_id,
                    "CompanyName": token_companies[company_id].company_name or normalize_text(row.get("CompanyName")),
                    "DealID": normalize_text(row.get("DealID")),
                    "DealDate": normalize_text(row.get("DealDate")),
                    "DealType": normalize_text(row.get("DealType")),
                    "InvestmentStatus": normalize_text(row.get("InvestmentStatus")),
                }
            )
    return fund_hits


def load_fund_names(pitchbook_dir: Path, fund_ids: set[str]) -> dict[str, str]:
    names: dict[str, str] = {}
    if not fund_ids:
        return names
    for row in iter_csv(pitchbook_dir / "Fund.csv"):
        fund_id = normalize_text(row.get("FundID"))
        if fund_id in fund_ids:
            names[fund_id] = normalize_text(row.get("FundName"))
    return names


def collect_fund_investors(
    pitchbook_dir: Path,
    token_companies: dict[str, TokenCompany],
    fund_hits: dict[str, list[dict[str, str]]],
    fund_names: dict[str, str],
    evidence: dict[str, InvestorEvidence],
) -> None:
    if not fund_hits:
        return
    for row in iter_csv(pitchbook_dir / "FundInvestorRelation.csv"):
        fund_id = normalize_text(row.get("FundID"))
        hits = fund_hits.get(fund_id)
        if not hits:
            continue
        fund_name = fund_names.get(fund_id, "")
        for hit in hits:
            company = token_companies[hit["CompanyID"]]
            add_investor(
                evidence,
                row.get("InvestorID", ""),
                source_method="fund_investment_relation",
                investor_name=row.get("InvestorName", ""),
                company_id=company.company_id,
                company_name=company.company_name or hit.get("CompanyName", ""),
                deal_id=hit.get("DealID", ""),
                fund_id=fund_id,
                context=(
                    f"FundInvestmentRelation: {company.company_name}; "
                    f"fund={fund_name or fund_id}; deal={hit.get('DealID')}; "
                    f"date={hit.get('DealDate')}; status={hit.get('InvestmentStatus')}"
                ),
            )


def load_investor_metadata(pitchbook_dir: Path, investor_ids: set[str]) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    if not investor_ids:
        return metadata
    for row in iter_csv(pitchbook_dir / "Investor.csv"):
        investor_id = normalize_text(row.get("InvestorID"))
        if investor_id in investor_ids:
            metadata[investor_id] = row
    return metadata


def unique_ordered(values: Iterable[str], limit: int = 0) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = normalize_text(value)
        if not value or value in seen:
            continue
        seen.add(value)
        result.append(value)
        if limit > 0 and len(result) >= limit:
            break
    return result


def build_context(evidence: InvestorEvidence, row: dict[str, str], max_chars: int) -> str:
    parts = [
        f"Part5 token-company investor graph: {len(evidence.company_ids)} token companies, "
        f"{len(evidence.deal_ids)} deals, {len(evidence.fund_ids)} funds",
        f"source_methods={','.join(evidence.source_methods.keys())}",
    ]
    for column in ["PrimaryInvestorType", "OtherInvestorTypes", "PreferredVerticals", "PreferredInvestmentTypes"]:
        value = normalize_text(row.get(column))
        if value:
            parts.append(f"{column}: {value}")
    parts.extend(unique_ordered(evidence.context_parts, limit=4))
    return truncate_text(" | ".join(parts), max_chars)


def build_matched_keywords(evidence: InvestorEvidence) -> str:
    values = [
        "part5_token_company",
        *[f"source:{method}" for method in evidence.source_methods.keys()],
    ]
    if evidence.lead_deal_ids:
        values.append("lead_investor")
    if evidence.fund_ids:
        values.append("fund_linked")
    return "|".join(values)


def build_matched_columns(evidence: InvestorEvidence) -> str:
    method_to_columns = {
        "company_investor_relation": "CompanyInvestorRelation.CompanyID|CompanyInvestorRelation.InvestorID",
        "deal_investor_relation": "Deal.CompanyID|DealInvestorRelation.DealID|DealInvestorRelation.InvestorID",
        "investor_investment_relation": "InvestorInvestmentRelation.CompanyID|InvestorInvestmentRelation.InvestorID",
        "fund_investment_relation": "FundInvestmentRelation.CompanyID|FundInvestorRelation.FundID|FundInvestorRelation.InvestorID",
    }
    columns: list[str] = []
    for method in evidence.source_methods:
        columns.extend(method_to_columns[method].split("|"))
    return "|".join(unique_ordered(columns))


def build_part6_rows(
    evidence_by_investor: dict[str, InvestorEvidence],
    metadata_by_investor: dict[str, dict[str, str]],
    *,
    require_metadata: bool,
    description_max_chars: int,
    context_max_chars: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    sorted_evidence = sorted(
        evidence_by_investor.values(),
        key=lambda item: (
            -len(item.company_ids),
            -len(item.deal_ids),
            -sum(item.source_methods.values()),
            item.display_name.lower(),
            item.investor_id,
        ),
    )
    for task_index, evidence in enumerate(sorted_evidence, start=1):
        source = metadata_by_investor.get(evidence.investor_id)
        if not source and require_metadata:
            continue
        source = source or {}
        investor_name = normalize_text(source.get("InvestorName")) or evidence.display_name
        matched_keywords = build_matched_keywords(evidence)
        matched_columns = build_matched_columns(evidence)
        row = {
            "task_index": str(len(rows) + 1),
            "InvestorID": evidence.investor_id,
            "InvestorName": investor_name,
            "InvestorAlsoKnownAs": normalize_text(source.get("InvestorAlsoKnownAs")),
            "InvestorFormerName": normalize_text(source.get("InvestorFormerName")),
            "InvestorLegalName": normalize_text(source.get("InvestorLegalName")),
            "Website": normalize_text(source.get("Website")),
            "normalized_domain": derive_normalized_domain(source.get("Website", "")),
            "ParentCompany": normalize_text(source.get("ParentCompany")),
            "Exchange": normalize_text(source.get("Exchange")),
            "Ticker": normalize_text(source.get("Ticker")),
            "HQLocation": normalize_text(source.get("HQLocation")),
            "HQCountry": normalize_text(source.get("HQCountry")),
            "PrimaryInvestorType": normalize_text(source.get("PrimaryInvestorType")),
            "OtherInvestorTypes": normalize_text(source.get("OtherInvestorTypes")),
            "PreferredInvestmentTypes": normalize_text(source.get("PreferredInvestmentTypes")),
            "PreferredVerticals": normalize_text(source.get("PreferredVerticals")),
            "OtherInvestmentPreferences": normalize_text(source.get("OtherInvestmentPreferences")),
            "LastClosedFundName": normalize_text(source.get("LastClosedFundName")),
            "LastClosedFundType": normalize_text(source.get("LastClosedFundType")),
            "Description": truncate_text(source.get("Description", ""), description_max_chars),
            "MatchedKeywords": matched_keywords,
            "MatchedColumns": matched_columns,
            "InvestorCapabilityContext": build_context(evidence, source, context_max_chars),
            "SearchPolicy": SEARCH_POLICY,
            "AgentTaskScope": AGENT_TASK_SCOPE,
        }
        rows.append({column: row.get(column, "") for column in PART6_INPUT_COLUMNS})
    return rows


def build_audit_rows(evidence_by_investor: dict[str, InvestorEvidence]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for evidence in sorted(evidence_by_investor.values(), key=lambda item: (item.display_name.lower(), item.investor_id)):
        rows.append(
            {
                "InvestorID": evidence.investor_id,
                "InvestorName": evidence.display_name,
                "source_methods": "|".join(evidence.source_methods.keys()),
                "source_count": str(sum(evidence.source_methods.values())),
                "token_company_count": str(len(evidence.company_ids)),
                "deal_count": str(len(evidence.deal_ids)),
                "lead_deal_count": str(len(evidence.lead_deal_ids)),
                "fund_count": str(len(evidence.fund_ids)),
                "token_company_ids": "|".join(sorted(evidence.company_ids)),
                "token_company_names": "|".join(unique_ordered(evidence.company_names.keys())),
                "deal_ids": "|".join(sorted(evidence.deal_ids)),
                "fund_ids": "|".join(sorted(evidence.fund_ids)),
                "matched_keywords": build_matched_keywords(evidence),
                "matched_columns": build_matched_columns(evidence),
                "context": truncate_text(" | ".join(unique_ordered(evidence.context_parts)), 1000),
            }
        )
    return rows


def write_summary(
    path: Path,
    *,
    token_companies: dict[str, TokenCompany],
    deals: dict[str, dict[str, str]],
    fund_hits: dict[str, list[dict[str, str]]],
    evidence_by_investor: dict[str, InvestorEvidence],
    metadata_by_investor: dict[str, dict[str, str]],
    part6_rows: list[dict[str, str]],
    outputs: dict[str, Path],
) -> None:
    source_counts = Counter()
    for evidence in evidence_by_investor.values():
        source_counts.update(evidence.source_methods)
    missing_metadata = sorted(set(evidence_by_investor) - set(metadata_by_investor))
    payload = {
        "part5_token_company_count": len(token_companies),
        "token_company_deal_count": len(deals),
        "fund_count_from_token_companies": len(fund_hits),
        "unique_investor_candidates_before_metadata_filter": len(evidence_by_investor),
        "unique_investors_with_metadata": len(metadata_by_investor),
        "part6_input_rows": len(part6_rows),
        "source_method_counts": dict(source_counts),
        "missing_investor_metadata_count": len(missing_metadata),
        "missing_investor_metadata_ids_sample": missing_metadata[:50],
        "outputs": {key: str(value) for key, value in outputs.items()},
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    part5_results_csv = ensure_file(args.part5_results_csv, "part5_results_csv")
    pitchbook_dir = args.pitchbook_dir.resolve()
    if not pitchbook_dir.exists() or not pitchbook_dir.is_dir():
        raise SystemExit(f"pitchbook_dir does not exist or is not a directory: {pitchbook_dir}")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    token_companies = load_token_companies(part5_results_csv)
    if not token_companies:
        raise SystemExit("No Part5 companies with non-empty token_results were found.")

    evidence_by_investor: dict[str, InvestorEvidence] = {}
    collect_company_investors(pitchbook_dir, token_companies, evidence_by_investor)
    deals = load_deals_for_companies(pitchbook_dir, token_companies)
    collect_deal_investors(pitchbook_dir, token_companies, deals, evidence_by_investor)
    collect_investor_investment_relation(pitchbook_dir, token_companies, evidence_by_investor)
    fund_hits = collect_fund_investment_relation(pitchbook_dir, token_companies)
    fund_names = load_fund_names(pitchbook_dir, set(fund_hits))
    collect_fund_investors(pitchbook_dir, token_companies, fund_hits, fund_names, evidence_by_investor)

    metadata_by_investor = load_investor_metadata(pitchbook_dir, set(evidence_by_investor))
    part6_rows = build_part6_rows(
        evidence_by_investor,
        metadata_by_investor,
        require_metadata=args.require_investor_metadata,
        description_max_chars=args.description_max_chars,
        context_max_chars=args.context_max_chars,
    )
    if not part6_rows:
        raise SystemExit("No Part6 investor rows were produced.")

    token_company_rows = [
        {
            "company_id": company.company_id,
            "company_name": company.company_name,
            "normalized_domain": company.normalized_domain,
            "company_type": company.company_type,
            "token_symbols": company.token_symbols,
            "token_names": company.token_names,
            "token_urls": company.token_urls,
            "token_results": company.token_results,
            "confidence": company.confidence,
            "needs_manual_review": company.needs_manual_review,
        }
        for company in sorted(token_companies.values(), key=lambda item: item.company_id)
    ]
    outputs = {
        "part6_investor_input_csv": output_dir / "part6_investor_input.csv",
        "investor_candidate_audit_csv": output_dir / "investor_candidate_audit.csv",
        "token_company_universe_csv": output_dir / "token_company_universe.csv",
        "summary_json": output_dir / "summary.json",
    }
    write_csv(outputs["part6_investor_input_csv"], PART6_INPUT_COLUMNS, part6_rows)
    write_csv(outputs["investor_candidate_audit_csv"], AUDIT_COLUMNS, build_audit_rows(evidence_by_investor))
    write_csv(outputs["token_company_universe_csv"], TOKEN_COMPANY_COLUMNS, token_company_rows)
    write_summary(
        outputs["summary_json"],
        token_companies=token_companies,
        deals=deals,
        fund_hits=fund_hits,
        evidence_by_investor=evidence_by_investor,
        metadata_by_investor=metadata_by_investor,
        part6_rows=part6_rows,
        outputs=outputs,
    )

    print(f"Part5 token companies: {len(token_companies)}")
    print(f"Token-company deals: {len(deals)}")
    print(f"Investor candidates: {len(evidence_by_investor)}")
    print(f"Part6 input rows: {len(part6_rows)}")
    print(f"Output: {outputs['part6_investor_input_csv']}")
    print(f"Audit: {outputs['investor_candidate_audit_csv']}")
    print(f"Summary: {outputs['summary_json']}")


if __name__ == "__main__":
    main()
