# Part4: Token-to-Company Harness Plan

## 0. Required Read Order

Every Part4 run, prompt update, script update, verifier pass, or collector change must treat this file as the controlling contract.

Before running a Part4 batch worker:

1. Read this `Plan.md`.
2. Read `part4_analyse_token_to_company/pipeline.md`.
3. Read `part4_analyse_token_to_company/scripts/4_founder_company_prompt.txt`.
4. Use the harness scripts in `part4_analyse_token_to_company/scripts/`.

If a prompt, script, skill file, or worker note conflicts with this plan, this plan wins unless the user explicitly changes it.

Current status rule:

- the existing execution scripts under `part4_analyse_token_to_company/` should be treated as legacy v2 harness code
- production runs under this plan must update the scripts to match the contracts below before being trusted

## 1. Goal

The Part4 goal is to ensure that every token is routed through a complete founder/company/foundation discovery workflow with explicit evidence tracking.

For every token, the harness must attempt all three targets:

1. `founder_people`
2. `related_companies`
3. `foundation_or_orgs`

The goal is not:

- broad token summarization
- market analysis
- exchange / investor / partner discovery as a substitute for issuer or operator mapping
- inferring entities from outside knowledge without evidence
- silently dropping tokens because no trigger sentence was found

The completeness goal is:

- every token must go through all three target checks
- unresolved targets must escalate
- high-risk token types must route to the correct playbook
- no token may disappear because of batch-local indexing, trigger misses, or partial worker output

## 2. Inputs

Preparation input must be the union of the CoinGecko token list and the CoinMarketCap token list.

Required raw inputs:

- CoinGecko token list
- CoinMarketCap token list
- CoinGecko about / metadata text when available
- CoinMarketCap about / metadata text when available
- website metadata from either source when available

Preparation output becomes the harness source of truth:

- `part4_analyse_token_to_company/output/token_master.csv`

`token_master.csv` must contain one row per canonical token and must be the only batching source for Part4.

## 3. Global Token Identity

Preparation must generate a stable global key:

- `token_id`

`token_id` is mandatory and must be stable across reruns, batches, validation, verification, fallback, and final merge.

Recommended construction priority:

1. matched `coingecko_slug + cmc_slug`
2. one trusted slug plus exact normalized token name and symbol
3. exact normalized token name plus symbol when only one source exists

Every downstream file must use `token_id` as the merge key.

Do not use batch-local `row_index` as the primary identity key.

`row_index` may exist only as a transient batch execution helper, never as the final merge authority.

## 4. Token Router

Preparation must assign:

- `token_type`
- `routing_reason`

Allowed `token_type` values:

- `base_asset`
- `protocol_token`
- `exchange_token`
- `fiat_stablecoin`
- `wrapped_or_bridged`
- `liquid_staking_or_receipt`
- `synthetic_or_fund`
- `meme_or_community`
- `unknown`

Routing matters because the evidence playbook is not the same for all tokens.

Examples:

- `wrapped_or_bridged`: do not inherit the issuer or founder of the underlying token unless the evidence explicitly ties that entity to the wrapped token
- `liquid_staking_or_receipt`: prioritize protocol operator, issuing entity, DAO, and foundation over underlying chain founders
- `fiat_stablecoin`: prioritize issuing entity, trust structure, operator, consortium, and legal issuer
- `exchange_token`: prioritize exchange operator, issuer, parent company, and foundation

The router is mandatory. It is not optional metadata.

## 5. Reduced Output Set

The current output set is too fragmented. Consolidate into the following final outputs:

- `part4_analyse_token_to_company/agent_runs/token_company/token_master.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/token_entity_results.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/token_entity_review_queue.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/verification_findings.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

Per-batch working files should be reduced to:

- `prepared_batch.csv`
- `official_evidence.csv`
- `entity_sentences.csv`
- `token_entity_results.csv`
- `layer3_packet.jsonl` only when unresolved fields remain
- `verification/verification_report.csv`
- `verification/verification_summary.md`

Do not keep separate batch-local `extracted`, `validated`, and `review_queue` CSVs when one results file plus one derived review queue is enough.

## 6. Reduced Result Schema

Use one consolidated result row per token.

Required columns for `token_entity_results.csv`:

```csv
token_id,token_name,token_symbol,coingecko_slug,cmc_slug,token_href,official_website,token_type,founder_people,founder_status,founder_evidence_spans,related_companies,related_company_status,related_company_evidence_spans,foundation_or_orgs,foundation_status,foundation_evidence_spans,source_urls,source_labels,confidence,needs_manual_review,notes,status
```

Status columns are field-level, not row-level:

- `founder_status`
- `related_company_status`
- `foundation_status`

Allowed field status values:

- `supported`
- `unresolved`
- `not_applicable`

Global row `status` is execution state:

- `completed`
- `pending_layer3`

Drop unnecessary columns from the final output, including:

- batch-local helper fields
- duplicate source-risk columns that can be recomputed
- raw trigger keywords in final outputs
- `error` columns unless a row is still `pending_layer3`
- separate `suggested_confidence_cap` in final outputs

Keep diagnostic detail in verifier findings or batch-local artifacts, not in the final merged table.

## 7. Field-Level Completeness Contract

Completeness is not row-level. It is target-level.

For each token:

- `founder_people` must be evaluated
- `related_companies` must be evaluated
- `foundation_or_orgs` must be evaluated

Each target must end in one of:

- `supported`
- `unresolved`
- `not_applicable`

Rules:

- a token is not considered fully handled if one field is supported but the other two were never checked
- a token with `founder_status = supported` and `related_company_status = unresolved` must still escalate
- `not_applicable` is only allowed when the token type and evidence clearly justify it
- empty arrays without field status are invalid

## 8. Workflow Order

The workflow must be reordered.

Old tendency:

- CG/CMC text first
- founder extraction first
- official site second

New required order:

1. Preparation from CG + CMC union into `token_master.csv`
2. Generate `token_id`
3. Run `token_type` router
4. Build immutable batch inputs from `token_master.csv`
5. Collect official/company evidence first
6. Extract high-signal company / foundation / operator / issuer sentences from official evidence
7. Add CG/CMC founder-history evidence as a supplement, not as the first authority for company/foundation
8. Run field-level extraction for all three targets
9. Run field-level completeness gate
10. Build `layer3_packet.jsonl` only for unresolved targets
11. Run a fresh verifier
12. Merge authoritative corrected rows
13. Rebuild final review queue from unresolved fields only
14. Update checkpoint

## 9. Evidence Priority

Evidence order is target-aware.

For `related_companies` and `foundation_or_orgs`, prefer:

1. official site legal/about/foundation/governance/company pages
2. docs / whitepaper / litepaper / FAQ
3. trusted official blog or announcement pages
4. CG/CMC text only as support, not as sole high-confidence basis

For `founder_people`, use:

1. official site team/about/history pages
2. official docs / whitepaper / bios
3. CG/CMC founder-history text as supplemental evidence when official evidence is thin

Hard rule:

- official/company evidence must run before founder supplementation

## 10. Candidate Sentence Strategy

Do not use one generic trigger list for all three targets.

Required sentence extraction groups:

1. founder triggers
2. related-company triggers
3. foundation/org triggers

Examples that must be treated separately:

- founder: `founder`, `co-founder`, `created by`, `invented by`
- related company: `issuer`, `issuing entity`, `operator`, `developed by`, `maintained by`, `parent company`, `trust company`
- foundation/org: `foundation`, `dao`, `association`, `labs`, `governed by`

No token may be dropped only because none of the founder triggers matched.

If no high-signal sentences are found:

- keep the token row
- mark unresolved fields
- escalate according to the field-level completeness gate

## 11. Layer 3 Fallback

Layer 3 is mandatory for unresolved fields. It is not a passive note.

Layer 3 input must be structured and field-aware:

- `token_id`
- `token_type`
- `token_name`
- `token_symbol`
- `coingecko_slug`
- `cmc_slug`
- `official_website`
- official company/foundation evidence snippets
- CG/CMC founder-history snippets
- current field statuses
- explicit unresolved targets

Layer 3 output must return a complete replacement row for the token, not a partial comment.

## 12. Verifier Contract

Every completed batch must end with a fresh verifier.

Verifier responsibilities:

- detect missing founders, companies, and orgs
- detect wrong entity typing
- detect rows where field completeness was not honored
- detect routing mistakes from `token_type`
- detect tokens that should have escalated to Layer 3

The verifier must be authoritative for row correction.

Required `verification_report.csv` header:

```csv
token_id,token_name,worker_founder_status,worker_related_company_status,worker_foundation_status,verifier_founder_status,verifier_related_company_status,verifier_foundation_status,verdict,error_type,error_reason,evidence_notes,recommended_action,corrected_result_row_json
```

Allowed `recommended_action` values:

- `accept_worker_row`
- `edit_row`
- `mark_manual_review`
- `rerun_token`
- `rerun_batch`
- `update_prompt_or_process`

Authoritative correction rule:

- if `recommended_action = edit_row`, `corrected_result_row_json` is required
- `corrected_result_row_json` must contain the full result-row schema
- the collector applies it directly if it passes validation

## 13. Collector Contract

Collector responsibilities:

- validate `token_id` uniqueness across all outputs
- validate one result row per token
- validate field-level completeness statuses
- reject silent token drops
- reject unresolved verifier edits
- merge authoritative verifier corrections
- rebuild final review queue from unresolved fields
- update checkpoint

Collector must fail the run if:

- a token exists in `token_master.csv` but not in merged outputs
- a token appears in multiple batches with conflicting rows
- a token has empty arrays for all targets but no unresolved status
- a verifier requested `edit_row` without a valid corrected row

## 14. Checkpoint Contract

The only resume authority is:

- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

Required checkpoint fields:

- `completed_tokens_in_final_results`
- `completed_through_token_id`
- `completed_through_batch`
- `next_batch_to_process`
- `token_master_csv`
- `token_entity_results_csv`
- `token_entity_review_queue_csv`
- `verification_findings_csv`

## 15. Current Design Direction

The design objective is now explicit:

- every token must go through the three-target workflow
- every unresolved target must escalate
- every high-risk token type must route correctly
- no token may disappear because of trigger misses, batch-local ids, or partial batch execution

That is the success criterion for Part4.
