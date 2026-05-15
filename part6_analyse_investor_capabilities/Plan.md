# Part6: Investor Capability Harness Plan

## Goal

Input:
- `part2_build_crypto_candidate/output/crypto_investor.csv`

Authoritative outputs:
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/classifier_results.csv`
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/results.csv`
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/needs_manual_review.csv`
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/checkpoint.json`

The task is to classify each investor for these capability labels:
- `otc_trading`
- `algorithm_trading`
- `market_making`
- `execution_services`
- `defi`
- `sub_fund`

The harness may also record supplemental `other_flags`, but the six labels above are the required core outputs.

## Architecture

The harness follows the existing multi-round control-plane shape established in part5:
1. extract compact investor inputs from `crypto_investor.csv`
2. build fixed-size JSONL batches
3. run a classifier/router pass for every investor
4. write classifier decisions to `classifier_results.csv`
5. route each investor to `full`, `light`, or `skip_candidate`
6. run investor capability search workers
7. run round-end verifier review
8. merge verified clean rows into the global final outputs
9. regenerate `needs_manual_review.csv`
10. update checkpoint

Recommended defaults:
- `batch_size = 30`
- `workers = 5`
- queue-mode is the default unattended long-run path

## Input Contract

Required extracted fields:
- `task_index`
- `InvestorID`
- `InvestorName`
- `InvestorAlsoKnownAs`
- `InvestorFormerName`
- `InvestorLegalName`
- `Website`
- `normalized_domain`
- `ParentCompany`
- `Exchange`
- `Ticker`
- `HQLocation`
- `HQCountry`
- `PrimaryInvestorType`
- `OtherInvestorTypes`
- `PreferredInvestmentTypes`
- `PreferredVerticals`
- `OtherInvestmentPreferences`
- `LastClosedFundName`
- `LastClosedFundType`
- `Description`
- `MatchedKeywords`
- `MatchedColumns`
- `InvestorCapabilityContext`

Text limits:
- `Description`: max 700 chars
- `InvestorCapabilityContext`: max 400 chars

## Stage 1: Classifier / Router

`classifier_results.csv` header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,risk_flags,classifier_reason
```

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

Routing rules:
- `full`
  - explicit OTC / market making / trading / liquidity / execution / brokerage / quant / DeFi / protocol / exchange / fund-vehicle signals
  - operating-company-like descriptions under investor entities
- `light`
  - crypto investor but mostly investment preference signal
  - ambiguous crypto-native positioning that still deserves bounded confirmation
- `skip_candidate`
  - weak crypto keyword inclusion only, with no operating-capability signal

Conservative rule:
- if uncertain between `skip_candidate` and `light`, use `light`

## Stage 2: Result Schema

`results.csv` header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,capability_search_reason,status,completed_at,capability_labels,otc_trading,algorithm_trading,market_making,execution_services,defi,sub_fund,other_flags,evidence_urls,evidence_source_types,evidence_summary,confidence,needs_manual_review
```

Rules:
- one row per investor
- the six capability columns must be `yes` or `no`
- `capability_labels` must be the JSON list of every capability column set to `yes`
- `other_flags` must be a JSON list string
- `evidence_urls` must be non-empty for searched rows
- `evidence_source_types` must be non-empty for searched rows
- `confidence` must be `high`, `medium`, or `low`

Capability interpretation rules:
- `defi = yes` requires evidence the investor itself operates, specializes in, or explicitly markets DeFi-native capability; merely investing in DeFi is not enough
- `sub_fund = yes` requires explicit sub-fund / feeder / umbrella / parallel-fund / SPV / fund-of-funds evidence; a normal closed fund is not enough

## Verification

Verifier focus:
- false positives on `market_making`, `execution_services`, and `defi`
- weak `sub_fund` inferences from generic fund metadata
- skipped rows that should have been searched
- operating-company profiles incorrectly treated as pure VC/angel records

`verification_report.csv` header:

```csv
task_index,investor_id,investor_name,classifier_search_tier,worker_capability_labels,verifier_search_tier,verifier_capability_labels,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

## Long-Run Behavior

- prefer `scripts/6_start_long_running_supervisor.py` for detached backlog runs
- prefer queue mode for unattended work
- use `scripts/7_check_longrun_status.py` as the canonical status entrypoint
- preserve the established two-stage long-tail handling:
  - first timeout parks the batch for one tail retry
  - second timeout becomes terminal `deferred_long_tail`
