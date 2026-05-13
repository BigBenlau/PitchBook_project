# Part6 Agent Prompt Template

Before doing any part6 investor capability work, read:

1. `part6_analyse_investor_capabilities/Plan.md`
2. this file

If this file conflicts with `Plan.md`, `Plan.md` wins.

## Scope

Task goal:
- classify each investor into an archetype
- decide `search_tier`
- determine whether the investor should be labeled `yes/no` for:
  - `otc_trading`
  - `algorithm_trading`
  - `market_making`
  - `execution_services`
  - `defi`
  - `sub_fund`
- write one classifier row and one result row per investor

Do not do:
- token mapping
- valuation analysis
- market commentary
- entity merging across unrelated PitchBook rows

## Required Workflow

1. Read `Plan.md`.
2. Read the assigned investor row.
3. Determine why the row appears in `crypto_investor.csv`.
4. Fill `primary_investor_type`, `investor_archetype`, `crypto_native_likelihood`, `operating_capability_likelihood`, `search_tier`, `capability_search_required`, `risk_flags`, and `classifier_reason`.
5. Write the classifier row.
6. If `search_tier = skip_candidate`, write a completed result row with all six capability flags = `no`, `capability_labels = []`, and a clear `capability_search_reason`.
7. If `search_tier = light`, run bounded local-first plus web-confirmation probes.
8. If `search_tier = full`, search more broadly with primary-source priority.
9. Write one result row per investor.
10. Keep `capability_labels` synchronized with the six boolean capability columns.
11. If evidence conflicts or the label boundary is genuinely ambiguous, set `needs_manual_review = yes`.

## Classification Rules

Allowed `investor_archetype` values:
- `traditional_vc_or_pe`
- `crypto_native_vc`
- `hedge_fund_or_quant`
- `market_maker_or_otc_firm`
- `asset_manager_or_family_office`
- `accelerator_or_incubator`
- `angel_or_individual`
- `exchange_affiliated_investor`
- `operating_company_disguised_as_investor`
- `fund_vehicle_or_fund_platform`
- `unclear`

Allowed likelihood values:
- `high`
- `medium`
- `low`
- `none`
- `unclear`

Allowed `search_tier` values:
- `full`
- `light`
- `skip_candidate`

Allowed `capability_search_required` values:
- `yes`
- `no`

Hard rules:
- `full` or `light` requires `capability_search_required = yes`
- `skip_candidate` requires `capability_search_required = no`
- if the row or official site contains OTC / liquidity / market making / execution / routing / brokerage / quant / DeFi / feeder / umbrella / SPV / fund-of-funds language, do not use `skip_candidate`

## Capability Rules

Mark `otc_trading = yes` only with explicit OTC desk / block trading / bilateral trading evidence.

Mark `algorithm_trading = yes` only with explicit algorithmic / quantitative / systematic / HFT / low-latency trading evidence.

Mark `market_making = yes` only with explicit market making / liquidity provision evidence.

Mark `execution_services = yes` only with explicit execution / smart order routing / order routing / brokerage / prime brokerage / liquidity access evidence.

Mark `defi = yes` only if the investor itself operates, specializes in, or explicitly markets DeFi-native capability or product exposure. Funding DeFi startups alone is insufficient.

Mark `sub_fund = yes` only with explicit sub-fund / feeder / umbrella / parallel fund / SPV / fund platform / fund-of-funds evidence. A standard closed fund is insufficient.

## Output Schemas

Classifier CSV header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,risk_flags,classifier_reason
```

Result CSV header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,capability_search_reason,status,completed_at,capability_labels,otc_trading,algorithm_trading,market_making,execution_services,defi,sub_fund,other_flags,evidence_urls,evidence_source_types,evidence_summary,confidence,needs_manual_review
```

Rules:
- `risk_flags`, `other_flags`, and `capability_labels` must be JSON list strings
- `capability_labels` must exactly equal the list of capability columns whose value is `yes`
- `status` should be `completed`
- `evidence_urls` should use `|`-separated absolute HTTP(S) URLs
- `evidence_source_types` should use `|`-separated lowercase source labels
- `confidence` must be `high`, `medium`, or `low`
