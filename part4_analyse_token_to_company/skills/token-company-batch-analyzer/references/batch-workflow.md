# Batch Workflow

## Batch Creation

Create batch inputs from a full merged CSV:

```bash
python3 part4_analyse_token_to_company/0_prepare_input_batches.py \
  --input-csv part4_analyse_token_to_company/tmp/full/coingecko_about_with_cmc_about.csv \
  --batch-size 500 \
  --overwrite
```

Expected outputs:

- `part4_analyse_token_to_company/input/batch_manifest.csv`
- `part4_analyse_token_to_company/input/batches/batch_0001.csv`

## Per-Batch Layout

For `batch_0001`:

```text
part4_analyse_token_to_company/tmp/batch_0001/
part4_analyse_token_to_company/output/batch_results/batch_0001/
```

Use `tmp/batch_0001/merged_input.csv` as the batch-local merged input.

## Layer 1: Candidate Sentences

```bash
python3 part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/2_filter_candidate_sentences.py \
  --merged-csv part4_analyse_token_to_company/tmp/batch_0001/merged_input.csv \
  --official-evidence-csv part4_analyse_token_to_company/tmp/batch_0001/official_evidence.csv \
  --output-csv part4_analyse_token_to_company/tmp/batch_0001/token_evidence_sentences.csv
```

If official evidence has not been collected yet, the script still processes CG/CMC text.

## Layer 1 Extraction Task Build

```bash
python3 part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/3_extract_founder_companies.py \
  --input-csv part4_analyse_token_to_company/tmp/batch_0001/token_evidence_sentences.csv \
  --tasks-jsonl part4_analyse_token_to_company/tmp/batch_0001/founder_company_tasks.jsonl \
  --batch-dir part4_analyse_token_to_company/tmp/batch_0001/codex_batches \
  --result-template part4_analyse_token_to_company/tmp/batch_0001/founder_company_extracted.csv \
  --batch-size 10
```

The generated `codex_batches/*.md` are the model/agent task packets for extraction.

## Layer 2: Official Evidence

Run only for rows requiring official evidence. If no subset file exists yet, use the batch input.

```bash
python3 part4_analyse_token_to_company/2_layer2_official_evidence/1_collect_official_evidence.py \
  --input-csv part4_analyse_token_to_company/tmp/batch_0001/merged_input.csv \
  --output-csv part4_analyse_token_to_company/tmp/batch_0001/official_evidence.csv \
  --max-pages 5 \
  --max-paragraphs 5
```

Then rerun candidate sentence filtering so official evidence is included.

## Validation

After extraction results are available:

```bash
python3 part4_analyse_token_to_company/3_layer3_review_agent/1_validate_extraction_results.py \
  --results-csv part4_analyse_token_to_company/tmp/batch_0001/founder_company_extracted.csv \
  --sentences-csv part4_analyse_token_to_company/tmp/batch_0001/token_evidence_sentences.csv \
  --output-csv part4_analyse_token_to_company/output/batch_results/batch_0001/founder_company_validated.csv
```

## Review Queue

```bash
python3 part4_analyse_token_to_company/3_layer3_review_agent/2_build_review_queue.py \
  --input-csv part4_analyse_token_to_company/output/batch_results/batch_0001/founder_company_validated.csv \
  --output-csv part4_analyse_token_to_company/output/batch_results/batch_0001/founder_company_review_queue.csv
```

## Agent Fallback Packet

If unresolved rows remain, create an agent packet in:

```text
part4_analyse_token_to_company/output/agent_packets/batch_0001.jsonl
```

Each packet should include:

- token identity
- candidate sentences
- official paragraphs
- validation issues
- exact question for founder_people, related_companies, foundation_or_orgs

Do not ask the fallback agent to broadly summarize the token.
