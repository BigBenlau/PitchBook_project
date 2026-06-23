# Part5 Plan: Company To Formal Token Mapping

## Objective

Part5 maps each crypto-relevant company row to zero, one, or multiple fungible token mappings under one formal rule.

A token may be included only when strong, direct, and stable evidence shows that the company is an officially recognized founding entity, co-founding entity, or original founding organization of the token's blockchain or protocol ecosystem.

The final result must contain exactly one row per company. Multiple qualifying tokens stay in the same row as a JSON object-list string in `token_results`, which is placed as the final CSV column to keep the wide object payload out of the middle of the table.

## Formal Inclusion Rule

Include a token only when evidence supports all of the following:

- The token is a fungible crypto token, not a stock ticker, NFT-only symbol, chain name without token evidence, product code, or informal community label.
- The company is an official founding entity, co-founding entity, or original founding organization of the blockchain/protocol ecosystem connected to that token.
- The company-token relationship is direct and stable, not only a later partnership, listing, investment, service relationship, portfolio relationship, or ecosystem participation.
- Evidence comes from official or high-quality primary sources when available. Secondary sources may corroborate but should not replace direct evidence for high-confidence inclusion.

Exclude a token when the company is only a later venture arm, ecosystem fund, portfolio company, dApp, wallet, exchange, DEX, staking provider, incubator, investor, market maker, liquidity provider, token-sale participant, ordinary ecosystem participant, or product issuer without founding-organization evidence.

Foundation plus operating company can both be included only when each entity independently has strong direct founding-entity evidence.

## Worker Workflow

1. Read `tasks.jsonl`, `Plan.md`, `agent_prompt_template.md`, and the runtime wrapper for the current attempt.
2. Write one classifier row per company with the approved classifier schema.
3. Decide `search_tier` as `full`, `light`, or `skip_candidate`.
4. For `skip_candidate`, write a completed result row with `token_results = []` and a clear `token_decision_reason`.
5. For `light` and `full`, search from the company outward for formal founding-entity token evidence.
6. If a plausible token is found, verify company/project/token identity, fungibility, and founding-entity relationship.
7. Preserve all qualifying token mappings in `token_results`; do not collapse multiple valid mappings into one.
8. If no qualifying token is found, write `token_results = []` and explain the exclusion reason.
9. Append classifier and result rows incrementally as each company is completed.
10. Keep immutable task identity fields exactly as provided in `tasks.jsonl`.

Use `gpt-5.5` with `xhigh` reasoning as the default model for workers, reruns, and verification.

## Output Schema

Result CSV header:

```text
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,project_search_required,project_search_reason,project_name,project_url,status,completed_at,token_symbol,token_decision_reason,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review,token_results
```

List-valued fields:

- `project_name`
- `project_url`
- `token_symbol`
- `token_results`

Each `token_results` object must include:

```json
{
  "token_symbol": "",
  "token_name": "",
  "token_url": "",
  "reason": "",
  "evidence_urls": [],
  "evidence_source_types": []
}
```

Required row semantics:

- `status` must be `completed`.
- `token_symbol` must be a JSON list string equal to all `token_symbol` values extracted from `token_results`, in the same order.
- `token_results` must be a valid JSON list string. Use `[]` when no qualifying token exists.
- `token_decision_reason` is required when `token_results = []`.
- `confidence` must be `high`, `medium`, or `low`.
- `needs_manual_review` must be `yes` or `no`.
- Searched rows must include non-empty `has_token_evidence`, `evidence_urls`, and `evidence_source_types`.

## Verifier Workflow

The verifier independently reviews each worker row and checks:

- missing formal founding-entity token mappings
- extra or unrelated token mappings
- wrong company/project/token identity
- non-fungible, stock ticker, NFT-only, product-code, or chain-name contamination
- overly conservative `search_tier`
- unreasonable `skip_candidate`
- insufficient evidence for inclusion or exclusion

Verifier CSV header:

```text
task_index,company_id,company_name,classifier_search_tier,worker_token_results,verifier_search_tier,verifier_token_results,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

Allowed verdicts:

- `pass`
- `missing_token`
- `extra_token`
- `wrong_token_mapping`
- `invalid_token_result_json`
- `suspected_missing_token`
- `suspected_extra_token`
- `wrong_project_mapping`
- `non_fungible_or_stock_ticker`
- `search_tier_too_conservative`
- `search_should_not_have_been_skipped`
- `insufficient_evidence`

Allowed recommended actions:

- `accept_worker_row`
- `edit_row`
- `mark_manual_review`
- `rerun_company`
- `rerun_batch`
- `update_prompt_or_process`

## Runtime Workflow

The default unattended path is:

1. Build or refresh batch inputs with `scripts/1_build_company_token_batches.py`.
2. Prepare run skeletons with `scripts/2_prepare_worker_runs.py`.
3. Launch longrun supervisor with `scripts/6_start_long_running_supervisor.py --scheduler-mode queue`.
4. Queue supervisor keeps worker slots full and delegates launch/watch/collect actions.
5. Runtime controller handles startup failures, partial stalls, continuation attempts, narrowed suffix attempts, and split recovery according to `runtime/policy.json`.
6. Collector validates worker and verifier outputs with `scripts/3_collect_results.py`.
7. Status checks use `scripts/7_check_longrun_status.py`.

All runtime-side writes to live `schedule.csv` must go through `scripts/part5_schedule_io.py`.

## Result Migration Invariant

The current formal results were migrated from the previous founding-entity output. For every task row:

- new `token_results` equals the previous founding-entity token result list
- `token_symbol` is derived only from `token_results[*].token_symbol`
- new `token_decision_reason` equals the previous founding-entity decision reason
- row identity and order are unchanged
- no company row is added or removed

Future runs must produce only the formal schema above.
