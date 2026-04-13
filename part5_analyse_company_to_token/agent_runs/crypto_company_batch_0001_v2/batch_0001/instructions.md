# Part5 Worker Run

You are Worker 1 in round 1 for the part5 company-to-token review.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Exclusive write scope:
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001

Read:
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/Plan.md
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_task_batches/crypto_company_batch_0001_v2/batch_0001.jsonl
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/tasks.jsonl
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_prompt_template.md

Task range:
- batch_file: batch_0001.jsonl
- task_count: 30
- first_task_index: 1
- first_company: Zebpay
- last_task_index: 30
- last_company: SolarMente

Method:
- Follow the rendered prompt in each JSONL task.
- For every company, first classify company type, crypto project likelihood, search tier, project_search_required, risk flags, and classifier reason.
- Write one classifier/router row per company to `classifier_results.csv`.
- Use `search_tier = full`, `light`, or `skip_candidate` according to `Plan.md`.
- Use `project_search_required = yes` for `full` and `light`; use `no` only for `skip_candidate`.
- If `search_tier = skip_candidate`, write one completed result row with `token_ticker = []` and a clear `project_search_reason` derived from `classifier_reason`.
- If `search_tier = light`, run a bounded token-existence check.
- If `search_tier = full`, search freely to identify company -> project -> fungible token ticker mapping.
- Prefer official and primary sources, but do not limit research to official website, CoinGecko, or CoinMarketCap.
- Return exactly one CSV row per company.
- If no supported token is found, set `token_ticker` to `[]`.
- If multiple tokens are found, keep one row and put all symbols in `token_ticker` as a JSON list, e.g. `["ABC","XYZ"]`.
- Also use JSON-list strings for `project_name`, `project_url`, `token_name`, and `token_url`.
- Do not use stock ticker, NFT-only symbol, chain name, or product code as a fungible token ticker unless the evidence clearly supports it.

Write:
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/classifier_results.csv
- /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/results.csv

Classifier CSV header:
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,search_tier,project_search_required,risk_flags,classifier_reason

CSV header:
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,project_search_required,project_search_reason,project_name,project_url,status,completed_at,token_ticker,token_name,token_url,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review

Final response should report:
- classifier rows written
- total data rows written
- rows with non-empty `token_ticker`
- rows with `token_ticker = []`
- rows by `search_tier`
- `needs_manual_review = yes` count
- classifier file path
- results file path
