---
name: token-company-batch-analyzer
description: Analyze crypto token batches in part4_analyse_token_to_company to extract founder_people, related_companies, and foundation_or_orgs using the project's 3-layer pipeline. Use when Codex is asked to process, validate, review, or parallelize one or more Part4 token-to-company batch CSVs, generate agent packets, or reduce founder/company extraction risks for large token sets.
---

# Token Company Batch Analyzer

## Overview

Use this skill to process `part4_analyse_token_to_company` batches through the 3-layer token-to-company pipeline.

The target outputs are:

- `founder_people`
- `related_companies`
- `foundation_or_orgs`

Use `unknown` or empty arrays when evidence is insufficient. Do not fill gaps with outside knowledge.

## Project Layout

Assume the project root is the workspace root containing `part4_analyse_token_to_company/`.

Important folders:

- `part4_analyse_token_to_company/input/batches/`: immutable batch CSVs.
- `part4_analyse_token_to_company/tmp/batch_XXXX/`: per-batch intermediate files.
- `part4_analyse_token_to_company/output/batch_results/batch_XXXX/`: per-batch final files.
- `part4_analyse_token_to_company/output/agent_packets/`: unresolved/conflict rows for agent fallback.
- `part4_analyse_token_to_company/output/final/`: consolidated final outputs.

## Workflow

For a batch-processing request:

1. Identify the batch IDs and batch CSV paths.
2. Create `tmp/batch_XXXX/` and `output/batch_results/batch_XXXX/`.
3. Run Layer 1 on every row in the batch.
4. Run Layer 2 only for unresolved, low-confidence, or high-risk rows.
5. Generate Layer 3 agent packets only for rows still unresolved or conflicting after Layer 2.
6. Validate results and build review queue.
7. Write only final batch results to `output/batch_results/batch_XXXX/`; keep intermediate files in `tmp/`.

Detailed command patterns: read [batch-workflow.md](references/batch-workflow.md).

Risk and review rules: read [risk-rules.md](references/risk-rules.md).

## Parallel Batch Handling

If the user asks to process multiple batches simultaneously, use one worker/agent per batch when the environment supports parallel agents.

Rules for parallel work:

- Assign each worker exactly one batch ID.
- Each worker may write only to its own `tmp/batch_XXXX/` and `output/batch_results/batch_XXXX/`.
- Shared files such as `batch_manifest.csv` should not be edited concurrently unless explicitly coordinated.
- Agent packets should be written to unique files such as `output/agent_packets/batch_XXXX.jsonl`.
- Do not merge final outputs until all targeted batches finish.

## Extraction Standards

For `founder_people`, include only explicitly named founders, co-founders, creators, inventors, or pseudonymous creators.

For `related_companies`, include only directly related issuer, developer, operator, parent company, trust company, or commercial entity.

For `foundation_or_orgs`, include only foundations, DAOs, labs, associations, or non-company organizations directly tied to the token.

Never classify these as `related_companies` unless evidence explicitly says issuer/developer/operator/parent:

- exchange listing platforms
- investors
- partners
- custodians
- market makers
- ecosystem participants

For wrapped, bridged, staked, liquid-staking, or synthetic tokens, do not inherit the founder/company of the underlying asset unless evidence directly ties that entity to the wrapped/bridged/staked token.

## Output Requirements

Every non-empty extracted field must have evidence.

Final per-batch files should include:

- `founder_company_validated.csv`
- `founder_company_review_queue.csv`
- `agent_packet.jsonl` if Layer 3 is needed

Use JSON arrays for entity fields and evidence spans.

## Stop Conditions

Stop and report if:

- The batch CSV is missing.
- Required columns are missing.
- A script would overwrite another batch's tmp/output folder.
- Network access is needed for official evidence but unavailable.
- Layer 3 agent fallback is required but agent execution is not available.
