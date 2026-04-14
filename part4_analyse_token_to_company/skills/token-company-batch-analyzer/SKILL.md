---
name: token-company-batch-analyzer
description: Analyze Part4 token batches under the token_id-based harness to extract founder_people, related_companies, and foundation_or_orgs with field-level completeness, official/company evidence priority, and authoritative verification. Use when Codex is asked to process, validate, review, or parallelize one or more Part4 token-to-company batches.
---

# Token Company Batch Analyzer

## Overview

Use this skill to process `part4_analyse_token_to_company` batches under the current harness contract.

The three targets are:

- `founder_people`
- `related_companies`
- `foundation_or_orgs`

Every token must evaluate all three targets. Do not silently skip a token because sentence triggers are thin or absent.

## Current Contract

The current harness is based on:

- global stable `token_id`
- `token_type` routing at preparation time
- official/company evidence first
- field-level completeness, not row-level completeness

Allowed field statuses:

- `supported`
- `unresolved`
- `not_applicable`

If any target remains unresolved, the token must stay in the workflow and escalate to Layer 3 / review.

## Project Layout

Assume the project root is the workspace root containing `part4_analyse_token_to_company/`.

Important paths:

- `part4_analyse_token_to_company/output/token_master.csv`
- `part4_analyse_token_to_company/input/batch_manifest.csv`
- `part4_analyse_token_to_company/input/batches/batch_0001.csv`
- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/prepared_batch.csv`
- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/official_evidence.csv`
- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/entity_sentences.csv`
- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_results.csv`
- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/layer3_packet.jsonl`
- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/verification/verification_report.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/token_entity_results.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/token_entity_review_queue.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/verification_findings.csv`

## Workflow

For a batch-processing request:

1. Build or refresh `token_master.csv` from the CG + CMC union.
2. Confirm each token has a stable `token_id`.
3. Confirm each token has a `token_type`.
4. Split immutable batch CSVs from `token_master.csv`.
5. Prepare worker run directories with `prepared_batch.csv`.
6. Collect official/company evidence first.
7. Build target-aware sentence candidates.
8. Create one extraction task per token in the batch.
9. Produce exactly one `token_entity_results.csv` row per `token_id`.
10. Escalate unresolved fields to `layer3_packet.jsonl`.
11. Run fresh verification.
12. Merge authoritative verifier corrections and rebuild the review queue.

Detailed command patterns: read [batch-workflow.md](references/batch-workflow.md).

Risk and review rules: read [risk-rules.md](references/risk-rules.md).

## Parallel Batch Handling

If the user asks to process multiple batches simultaneously, use one worker/agent per batch when the environment supports parallel agents.

Rules for parallel work:

- Assign each worker exactly one batch ID.
- Each worker may write only to its own `agent_runs/.../batch_XXXX/` directory.
- Do not edit `token_master.csv` or `batch_manifest.csv` concurrently unless explicitly coordinated.
- Do not merge final outputs until all targeted batches finish.

## Extraction Standards

For `founder_people`, include only explicitly named founders, co-founders, creators, inventors, or pseudonymous creators.

For `related_companies`, include only directly responsible issuer, developer, operator, parent company, trust company, or commercial entity.

For `foundation_or_orgs`, include only foundations, DAOs, labs, associations, or directly tied non-company organizations.

Never classify these as `related_companies` unless the evidence explicitly says issuer/developer/operator/parent:

- exchange listing platforms
- investors
- partners
- custodians
- market makers
- ecosystem participants

For wrapped, bridged, staked, liquid-staking, or synthetic tokens, do not inherit the founder/company/foundation of the underlying asset unless the evidence directly ties that entity to the token being analyzed.

## Output Requirements

Current per-batch required output:

- `token_entity_results.csv`
- `layer3_packet.jsonl` only when unresolved fields remain
- `verification/verification_report.csv`
- `verification/verification_summary.md`

Current consolidated outputs:

- `token_entity_results.csv`
- `token_entity_review_queue.csv`
- `verification_findings.csv`
- `checkpoint.json`

Use JSON arrays for entity and evidence fields.

## Stop Conditions

Stop and report if:

- the batch CSV is missing
- required `token_id` columns are missing
- a script would overwrite another batch's run directory
- official evidence collection needs network access and the environment cannot provide it
- Layer 3 fallback is required but no agent execution path is available
