# Part4: Token-to-Entity Harness Plan

## 0. Required Read Order

Every part4 run, prompt update, worker launch, verifier run, and collector merge must treat this file as the controlling contract.

Read in this order:

1. `part4_analyse_token_to_company/Plan.md`
2. `part4_analyse_token_to_company/agent_prompt_template.md`
3. `part4_analyse_token_to_company/runtime/ARCHITECTURE.md`

If prompt text, worker text, or scripts conflict with this plan, this plan wins unless the user explicitly changes it.

## 1. Goal

Map each token row to zero, one, or multiple responsible entities that can be stably linked to the token or the token's operating project.

Default upstream source:

- `part3_find_token_list_at_cg_and_cmc/output/coingecko_coinmarketcap_union.csv`

Authoritative final outputs:

- `part4_analyse_token_to_company/agent_runs/token_company/results.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/classifier_results.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/needs_manual_review.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

One final row must exist per token task.

The task is:

- token identity classification
- token -> project mapping
- project -> responsible-entity mapping
- evidence-backed capture of related entities such as companies, foundations, issuers, associations, trusts, or other legal wrappers

The task is not:

- price, market, or investment analysis
- token listing history
- on-chain holder analytics
- founder biography research unless needed to resolve entity identity

## 2. Harness Architecture

Part4 uses the same four-layer production model as part5:

1. LLM worker
2. runtime controller
3. verifier
4. collector

The execution pipeline is:

1. Normalize token inputs into fixed-size JSONL batches.
2. Prepare run directories and attempt skeletons.
3. Run a classifier/router stage per token.
4. Write classifier decisions to batch-local `classifier_results.csv`.
5. Route each token to `full`, `light`, or `skip_candidate`.
6. Run project/company mapping search for `full` rows.
7. Run bounded evidence checks for `light` rows.
8. Write one result row per token to batch-local `results.csv`.
9. Run a fresh verifier for the completed scope.
10. Let collector validate, apply verifier decisions, and merge clean rows into final outputs.
11. Update checkpoint only after merge.

Queue-mode unattended backlog remains the default longrun model. Round mode is retained as a fallback.

## 3. Input Contract

The default builder assumes the union token list from part3, but the user may later provide a richer input CSV. The part4 runtime is designed so the input contract can evolve without changing the control plane.

Normalized batch input columns:

- `task_index`
- `canonical_slug`
- `token_name`
- `token_symbol`
- `cg_name`
- `cg_symbol`
- `cg_slug`
- `cg_url`
- `cmc_name`
- `cmc_symbol`
- `cmc_slug`
- `cmc_url`
- `cmc_rank`
- `from_cg`
- `from_cmc`
- `match_method`
- `source_presence`
- `search_policy`
- `agent_task_scope`

Compatibility fields may also appear in `tasks.jsonl` for runtime display and lease metadata:

- `company_id`
- `company_name`
- `normalized_domain`

In part4 these compatibility fields are internal aliases only:

- `company_id` mirrors `canonical_slug`
- `company_name` mirrors `token_name`
- `normalized_domain` mirrors `canonical_slug`

## 4. Stage 1: Classifier / Router

Each token must first pass through a classifier/router stage before deeper project/entity mapping.

Classifier output header:

```csv
task_index,canonical_slug,token_symbol,token_name,token_origin_type,entity_link_likelihood,search_tier,entity_search_required,risk_flags,classifier_reason
```

Allowed `token_origin_type` values:

- `layer1_or_l2`
- `protocol_or_app`
- `exchange_token`
- `stablecoin`
- `wrapped_or_bridged_asset`
- `liquid_staking_or_restaking`
- `asset_backed_or_rwa`
- `meme_or_community`
- `governance_or_utility`
- `unclear`

Allowed `entity_link_likelihood` values:

- `high`
- `medium`
- `low`
- `none`
- `unclear`

Allowed `search_tier` values:

- `full`
- `light`
- `skip_candidate`

Allowed `entity_search_required` values:

- `yes`
- `no`

Classifier purpose:

- identify whether the token likely maps to a responsible entity such as an operating company, foundation, exchange operator, issuer, association, trust, or wrapper issuer
- decide how much search budget is justified
- record why the chosen search tier is appropriate

Conservative rules:

- if a token clearly belongs to an active protocol, foundation, exchange, or issuer, use `full`
- if the token appears real but entity linkage is thin, use `light`
- use `skip_candidate` only when the row is obviously noise, duplicate, dead-end, or cannot justify entity search

## 5. Stage 2: Search Worker

The worker maps:

1. token identity
2. project identity
3. responsible-entity identity

The worker must search for:

- the token's canonical CoinGecko page when `from_cg = 1` or `cg_url` is present
- the token's canonical CoinMarketCap page when `from_cmc = 1` or `cmc_url` is present
- official token/project pages
- docs, foundation, issuer, or exchange operator pages
- legal entity mentions
- stable project/entity continuity across current and former brands

Mandatory page-visit rule:

- if the row belongs to CoinGecko, the worker must directly visit the `cg_url` page derived from the slug
- if the row belongs to CoinMarketCap, the worker must directly visit the `cmc_url` page derived from the slug
- if the row belongs to both CoinGecko and CoinMarketCap, both pages must be visited in the same research flow
- do not rely only on name search, snippets, or secondary summaries when these canonical token pages are available

The worker must not infer entity linkage only from token aggregators if the linkage cannot be tied back to official or otherwise stable evidence.

Entity capture rules:

- Record an entity only when stable evidence shows it is an issuer, operator, steward, legal counterparty, or other directly responsible entity for the token or project.
- Valid entity types include companies, foundations, associations, trusts, DAO legal wrappers, nonprofits, government-linked issuers, and other legal entities.
- Do not map generic advocacy groups, meetup/community organizations, historical marketing foundations, grant programs, or unrelated nonprofits merely because they mention the token.
- A decentralized network may still resolve to no mapped entity when there is no canonical issuer, operator, steward, or legal counterparty.
- Bitcoin-style examples should not automatically map to a historical `Bitcoin Foundation` or similar advocacy body unless the evidence shows actual issuer/operator/steward responsibility.

## 6. Output Schema

Result output header:

```csv
task_index,canonical_slug,token_symbol,token_name,token_origin_type,entity_link_likelihood,entity_search_required,entity_search_reason,project_name,project_url,mapped_entity_name,mapped_entity_legal_name,mapped_entity_type,mapped_entity_url,mapped_entity_country,entity_relation_type,status,completed_at,has_entity_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review
```

Column rules:

- `task_index`: immutable task identity
- `canonical_slug`: immutable token identity
- `token_symbol`: immutable token identity
- `token_name`: immutable token identity
- `token_origin_type`: classifier result
- `entity_link_likelihood`: classifier result
- `entity_search_required`: `yes` or `no`
- `entity_search_reason`: short explanation of the search decision or no-entity conclusion
- `project_name`: JSON list string
- `project_url`: JSON list string
- `mapped_entity_name`: JSON list string
- `mapped_entity_legal_name`: JSON list string
- `mapped_entity_type`: JSON list string
- `mapped_entity_url`: JSON list string
- `mapped_entity_country`: JSON list string
- `entity_relation_type`: JSON list string
- `status`: must be `completed`
- `completed_at`: ISO timestamp or blank in worker output
- `has_entity_evidence`: short evidence summary, never blank
- `evidence_urls`: `|`-separated absolute HTTP(S) URLs
- `evidence_source_types`: `|`-separated lowercase source labels
- `confidence`: `high`, `medium`, or `low`
- `needs_manual_review`: `yes` or `no`

List-valued columns must stay valid JSON lists after CSV parsing.

Allowed `mapped_entity_type` values:

- `company`
- `foundation`
- `issuer`
- `association`
- `trust`
- `dao_legal_wrapper`
- `nonprofit`
- `government_entity`
- `other_legal_entity`
- `unclear`

## 7. Evidence Contract

Positive entity-link evidence should tie at least:

- token
- to project
- to a responsible entity such as a company / issuer / operator / foundation / association / trust

Good evidence sources:

- official project sites
- issuer pages
- foundation or docs pages
- exchange operator pages
- legal disclosures
- reliable secondary sources that corroborate official identity

Weak evidence alone is not enough:

- aggregator pages with no entity back-link
- social handles with no project/entity continuity
- token logo similarity
- symbol similarity

## 8. Manual Review Rules

Set `needs_manual_review = yes` only when ambiguity remains after a real resolution pass.

Typical triggers:

- multiple plausible entities
- unclear foundation vs operating company split
- wrapper/bridge token with ambiguous issuer
- token migration / rebrand / acquisition ambiguity
- conflicting primary and secondary evidence

Do not use manual review as a substitute for missing search work.

## 9. Verifier

Every completed scope needs a fresh verifier.

Verifier output header:

```csv
task_index,canonical_slug,token_symbol,token_name,classifier_search_tier,worker_mapped_entity_name,verifier_search_tier,verifier_mapped_entity_name,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

Allowed verdicts:

- `pass`
- `suspected_missing_company`
- `suspected_extra_company`
- `wrong_project_mapping`
- `wrong_company_mapping`
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

## 10. Checkpoint and Resume Contract

Resume authority:

- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

Required checkpoint fields:

- `completed_rows_in_final_results`
- `completed_through_task_index`
- `completed_through_batch`
- `next_batch_to_process`
- `next_task_index_to_process`
- `classifier_results_csv`
- `final_results_csv`
- `manual_review_csv`

Do not resume from temporary attempt directories as the primary source of truth.

## 11. Runtime Strategy Layer

Authoritative runtime files:

- `part4_analyse_token_to_company/runtime/policy.json`
- `part4_analyse_token_to_company/runtime/worker_base_template.md`
- `part4_analyse_token_to_company/runtime/ARCHITECTURE.md`
- `part4_analyse_token_to_company/runtime/README.md`

Default unattended entrypoint:

1. `scripts/2_prepare_worker_runs.py`
2. `scripts/6_start_long_running_supervisor.py --scheduler-mode queue`
3. `scripts/7_check_longrun_status.py`

All runtime-side `schedule.csv` writes must use:

- `part4_analyse_token_to_company/scripts/part4_schedule_io.py`

## 12. Current Operating State

This checkout currently contains the part4 runtime scaffold only.

Current interpretation:

- no authoritative final token-company results should be assumed yet
- no detached longrun should be assumed yet
- input schema can still be enriched later without replacing the supervisor/runtime layer
