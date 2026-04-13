# Part5 Round-End Verifier

You are a fresh verifier subagent for part5 round 1.

You are not the worker that produced these rows. Re-check independently.

Exclusive write scope:
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/round_0001_verification

Read first:
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/Plan.md
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_prompt_template.md

Round task ranges:
- batch_0001.jsonl: task_index 1 to 30

Input task files:
- part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/tasks.jsonl

Worker result files:
- part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/results.csv

Task:
- Independently check whether each company's `token_ticker` JSON list is correct.
- Check that classifier/router tiering did not skip rows that should have been searched.
- Detect missing fungible token tickers.
- Detect extra or unrelated token tickers.
- Detect wrong company-to-project mapping.
- Detect stock tickers, NFT-only symbols, chain names, or product codes incorrectly reported as fungible token tickers.
- Detect `project_search_required = no` rows that should have been searched.
- Focus on token-positive rows, skipped-search rows, ambiguous brands, low/medium confidence rows, and multiple-token signals.

Search policy:
- Search freely.
- Use independent queries, not only worker evidence URLs.
- Prefer official and primary sources when available.
- Use secondary sources only for corroboration or disambiguation.

Write:
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/round_0001_verification/verification_report.csv
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/round_0001_verification/verification_summary.md

CSV header:
task_index,company_id,company_name,worker_token_ticker,verifier_token_ticker,verdict,error_type,error_reason,evidence_urls,recommended_action

Every row in the round should appear in `verification_report.csv`. Use `verdict = pass` when the worker row is acceptable.

Allowed verdict values:
- pass
- suspected_missing_token
- suspected_extra_token
- wrong_project_mapping
- non_fungible_or_stock_ticker
- search_should_not_have_been_skipped
- insufficient_evidence

Allowed recommended_action values:
- accept_worker_row
- edit_row
- mark_manual_review
- rerun_company
- rerun_batch
- update_prompt_or_process

`verification_summary.md` must include:
- checked row count
- pass count
- non-pass count
- suspected missing token count
- suspected extra token count
- wrong mapping count
- skipped-search concern count
- systematic causes found
- recommended process updates
