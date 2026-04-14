# Part4 Worker Run

You are processing `batch_0002` in the Part4 token-to-company harness.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Exclusive write scope:
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/agent_runs/token_company_parallel_test/batch_0002

Read first:
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/Plan.md
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/pipeline.md
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/4_founder_company_prompt.txt
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/agent_runs/token_company_parallel_test/batch_0002/merged_input.csv

Task range:
- batch_id: batch_0002
- task_count: 10
- first_token: USDS
- last_token: Wrapped Beacon ETH

Required workflow:
1. Run Layer 2 official evidence collection into `official_evidence.csv`.
2. Run candidate sentence filtering into `token_evidence_sentences.csv`.
3. Run extraction task building into `founder_company_tasks.jsonl` and `codex_batches/`.
4. Complete `founder_company_extracted.csv` with exactly one row per input row.
5. Run validation into `founder_company_validated.csv`.
6. Run review queue build into `founder_company_review_queue.csv`.
7. If unresolved rows remain, write `agent_packet.jsonl` for Layer 3 fallback.
8. Spawn a fresh verifier and produce `verification_report.csv` and `verification_summary.md`.

Worker output rules:
- Keep JSON arrays valid in `founder_people`, `related_companies`, `foundation_or_orgs`, and `evidence_spans`.
- Use only explicit source evidence from CG, CMC, and collected official paragraphs.
- `confidence` must be one of `high`, `medium`, `low`.
- `status` should be `completed` for finished rows or `pending_agent` when fallback is still required.
- Do not leave missing rows. Every input row must have a corresponding result row.
