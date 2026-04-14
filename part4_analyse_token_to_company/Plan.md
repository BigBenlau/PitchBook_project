# Part4: Token-to-Company Harness Plan

## 0. Required Read Order

Every Part4 run, worker instruction, prompt update, script update, verification pass, or collector change must treat this file as the controlling contract.

Before running a Part4 batch worker:

1. Read this `Plan.md`.
2. Read `part4_analyse_token_to_company/pipeline.md`.
3. Read `part4_analyse_token_to_company/4_founder_company_prompt.txt`.
4. Use the harness scripts in `part4_analyse_token_to_company/scripts/`.

If a prompt, skill file, worker note, or script behavior conflicts with this plan, this plan wins unless the user explicitly changes it.

## 1. Goal

Input:

- `part4_analyse_token_to_company/input/batch_manifest.csv`
- `part4_analyse_token_to_company/input/batches/batch_XXXX.csv`

Outputs:

- `part4_analyse_token_to_company/agent_runs/token_company/founder_company_extracted.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/founder_company_validated.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/founder_company_review_queue.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/verification_findings.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

The task is to extract, with evidence:

1. `founder_people`
2. `related_companies`
3. `foundation_or_orgs`

The task is not:

- broad token summarization
- market analysis
- partner / investor / exchange discovery as a substitute for issuer or operator mapping
- inferring founder/company/org from outside knowledge without evidence

## 2. Harness Architecture

The Part4 process is a harness around the existing 3-layer extraction pipeline. Layer scripts remain the extraction core; the harness adds scheduling, validation, verifier feedback, and checkpointing.

Pipeline stages:

1. Batch manifest and immutable batch inputs.
2. Worker run preparation with per-batch isolated run directories.
3. Layer 2 official evidence collection.
4. Layer 1 candidate sentence filtering.
5. Extraction task build and worker result completion.
6. Validation and batch review queue generation.
7. Fresh round-end verifier for each completed batch.
8. Collector validation, verifier gating, consolidated outputs, and checkpoint update.

Harness scripts:

- `scripts/1_prepare_worker_runs.py`
- `scripts/2_collect_results.py`

Core layer scripts reused by workers:

- `0_prepare_input_batches.py`
- `1_layer1_cg_cmc_baseline/2_filter_candidate_sentences.py`
- `1_layer1_cg_cmc_baseline/3_extract_founder_companies.py`
- `2_layer2_official_evidence/1_collect_official_evidence.py`
- `3_layer3_review_agent/1_validate_extraction_results.py`
- `3_layer3_review_agent/2_build_review_queue.py`

## 3. Run Layout

Prepared worker runs live under:

- `part4_analyse_token_to_company/agent_runs/token_company_parallel/`

Each batch has an isolated run directory:

- `part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/`

Expected per-batch files:

- `merged_input.csv`
- `official_evidence.csv`
- `token_evidence_sentences.csv`
- `founder_company_tasks.jsonl`
- `codex_batches/`
- `founder_company_extracted.csv`
- `founder_company_validated.csv`
- `founder_company_review_queue.csv`
- `agent_packet.jsonl` when Layer 3 fallback is needed
- `verification/verification_report.csv`
- `verification/verification_summary.md`

The schedule authority is:

- `part4_analyse_token_to_company/agent_runs/token_company_parallel/schedule.csv`

## 4. Worker Contract

Each worker owns exactly one prepared batch run directory.

Worker rules:

- Read only its assigned batch input and instructions.
- Write only inside its assigned run directory.
- Produce exactly one extracted result row and one validated row for every input token row.
- Do not write directly to consolidated final outputs.
- Use JSON arrays for entity fields and evidence spans.
- Use `completed` when the row is finished and `pending_agent` only when Layer 3 fallback is still required.

Batch execution order:

1. Run official evidence collection.
2. Run candidate sentence filtering.
3. Run extraction task build.
4. Complete `founder_company_extracted.csv`.
5. Run validation to produce `founder_company_validated.csv`.
6. Run review queue build.
7. If unresolved rows remain, write `agent_packet.jsonl`.
8. Hand off to a fresh verifier.

## 5. Verification Contract

Every completed batch must end with a fresh verifier. This is mandatory.

The verifier reads:

- this `Plan.md`
- `pipeline.md`
- batch input
- candidate sentences
- validated results
- review queue

Verifier goals:

- detect missing founders / related companies / orgs
- detect over-reported entities
- detect wrong entity type assignment
- detect weak-evidence rows that should stay in review
- detect rows that should escalate to Layer 3 fallback

Required verifier report header:

```csv
row_index,token_name,worker_founder_people,worker_related_companies,worker_foundation_or_orgs,verifier_founder_people,verifier_related_companies,verifier_foundation_or_orgs,verdict,error_type,error_reason,evidence_notes,recommended_action
```

Allowed `verdict` values:

- `pass`
- `suspected_missing_entity`
- `suspected_extra_entity`
- `wrong_entity_type`
- `insufficient_evidence`
- `search_should_escalate`
- `formatting_error`

Allowed `recommended_action` values:

- `accept_worker_row`
- `edit_row`
- `mark_manual_review`
- `rerun_row`
- `rerun_batch`
- `update_prompt_or_process`

Round completion gate:

- a batch is not complete until `verification_report.csv` and `verification_summary.md` exist
- non-`pass` verifier rows must have an action
- unresolved `edit_row` / `rerun_*` / `update_prompt_or_process` actions block merge

## 6. Collector Contract

The collector is:

- `scripts/2_collect_results.py`

Collector responsibilities:

- validate extracted row schema and row counts
- validate validated row schema and row counts
- ensure extracted and validated rows align on shared fields
- ensure each batch has a review queue file
- enforce verifier gates before merge
- merge consolidated extracted and validated outputs
- merge verifier findings
- rebuild the final review queue from consolidated validated rows
- update `checkpoint.json`

Collector does not silently ignore:

- missing rows
- duplicate `row_index`
- malformed JSON arrays
- unresolved verifier edits
- missing verification summaries

## 7. Checkpoint Contract

The only resume authority is:

- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

Required checkpoint fields:

- `completed_rows_in_final_results`
- `completed_through_row_index`
- `completed_through_batch`
- `next_batch_to_process`
- `extracted_results_csv`
- `validated_results_csv`
- `review_queue_csv`
- `verification_findings_csv`

Resume rule:

- start from `next_batch_to_process`
- do not rerun merged batches unless explicitly requested
- if a prepared run exists but is not merged, validate it before deciding to merge or rerun

## 8. Current Operating Rule

`run_sample_3layer_pipeline.py` is a sample runner, not the preferred production harness.

For harness-managed runs, the required order is:

1. `0_prepare_input_batches.py`
2. `scripts/1_prepare_worker_runs.py`
3. batch workers complete prepared run directories
4. fresh per-batch verifier
5. `scripts/2_collect_results.py`
