# Batch Workflow

## 1. Preparation from CG + CMC Union

Build `token_master.csv` and deterministic batch CSVs:

```bash
python3 part4_analyse_token_to_company/scripts/0_prepare_input_batches.py \
  --coingecko-csv part3_find_token_list_at_cg_and_cmc/output/coingecko_about.csv \
  --cmc-csv part3_find_token_list_at_cg_and_cmc/output/cmc_about_qa.csv \
  --token-master-csv part4_analyse_token_to_company/output/token_master.csv \
  --batch-dir part4_analyse_token_to_company/input/batches \
  --manifest part4_analyse_token_to_company/input/batch_manifest.csv \
  --batch-size 500 \
  --overwrite
```

Expected outputs:

- `part4_analyse_token_to_company/output/token_master.csv`
- `part4_analyse_token_to_company/input/batch_manifest.csv`
- `part4_analyse_token_to_company/input/batches/batch_0001.csv`

Each token row must already contain:

- `token_id`
- `token_type`

## 2. Prepare Worker Run Directories

```bash
python3 part4_analyse_token_to_company/scripts/1_prepare_worker_runs.py \
  --manifest part4_analyse_token_to_company/input/batch_manifest.csv \
  --token-master-csv part4_analyse_token_to_company/output/token_master.csv \
  --runs-dir part4_analyse_token_to_company/agent_runs/token_company_parallel \
  --workers 5 \
  --force
```

For `batch_0001`, the important files are:

```text
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/prepared_batch.csv
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/official_evidence.csv
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/entity_sentences.csv
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_results.csv
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/layer3_packet.jsonl
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/verification/verification_report.csv
```

Use `prepared_batch.csv` as the immutable per-batch source of truth.

## 3. Layer 2 First: Official Evidence

Collect official/company evidence before using CG/CMC founder text:

```bash
python3 part4_analyse_token_to_company/2_layer2_official_evidence/1_collect_official_evidence.py \
  --input-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/prepared_batch.csv \
  --output-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/official_evidence.csv \
  --max-pages 6 \
  --max-paragraphs 6
```

If network access is unavailable, stop and report the limitation rather than pretending official evidence was collected.

## 4. Target-Aware Sentence Extraction

Build sentence candidates with official evidence first, then CG/CMC supplementation:

```bash
python3 part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/2_filter_candidate_sentences.py \
  --batch-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/prepared_batch.csv \
  --official-evidence-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/official_evidence.csv \
  --output-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/entity_sentences.csv
```

The output is grouped by:

- `token_id`
- `target_group` (`founder`, `related_company`, `foundation`)

## 5. Build One Extraction Task Per Token

```bash
python3 part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/3_extract_founder_companies.py \
  --batch-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/prepared_batch.csv \
  --sentences-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/entity_sentences.csv \
  --tasks-jsonl part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_tasks.jsonl \
  --batch-dir part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/codex_batches \
  --result-template part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_results.csv \
  --batch-size 10
```

Hard rule:

- task builder must emit one task for every token in `prepared_batch.csv`, even if no sentence matched

## 6. Worker Output Contract

The worker must write exactly one row per `token_id` to:

```text
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_results.csv
```

Required field-level statuses:

- `founder_status`
- `related_company_status`
- `foundation_status`

Allowed values:

- `supported`
- `unresolved`
- `not_applicable`

If any target remains unresolved:

- keep the token row
- set `status=pending_layer3`
- add the token to `layer3_packet.jsonl`

## 7. Optional Validation Pass

If you need a lightweight validation artifact before verification:

```bash
python3 part4_analyse_token_to_company/3_layer3_review_agent/1_validate_extraction_results.py \
  --results-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_results.csv \
  --sentences-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/entity_sentences.csv \
  --output-csv part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/token_entity_results_validated.csv
```

This file is diagnostic only. The batch contract still centers on `token_entity_results.csv`.

## 8. Verification

Verifier output path:

```text
part4_analyse_token_to_company/agent_runs/token_company_parallel/batch_0001/verification/verification_report.csv
```

If `recommended_action = edit_row`, the verifier must provide `corrected_result_row_json` with a full replacement row.

## 9. Consolidation

```bash
python3 part4_analyse_token_to_company/scripts/2_collect_results.py \
  --runs-dir part4_analyse_token_to_company/agent_runs/token_company_parallel \
  --replace-output
```

Expected consolidated outputs:

- `part4_analyse_token_to_company/agent_runs/token_company/token_entity_results.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/token_entity_review_queue.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/verification_findings.csv`
- `part4_analyse_token_to_company/agent_runs/token_company/checkpoint.json`

The collector merges by `token_id`, applies authoritative verifier edits, rejects silent token drops, and rebuilds the review queue from unresolved fields.
