# Part5 Worker Run

You are Worker {{WORKER_SLOT}} in round {{ROUND_INDEX}} for the Part5 formal company-to-token review.

This execution segment must run in a fresh worker context. Do not rely on memory from any previous batch or segment.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Batch root context:
- {{RUN_DIR}}

Runtime strategy references:
- {{RUNTIME_ARCHITECTURE}}
- {{RUNTIME_POLICY}}

The attempt runtime wrapper provides the only authoritative write scope and output paths. Do not invent or substitute write targets.

Read:
- {{PLAN_MD}}
- {{BATCH_FILE}}
- {{TASKS_FILE}}
- {{PROMPT_TEMPLATE}}

Task range:
- batch_file: {{BATCH_FILE_NAME}}
- task_count: {{TASK_COUNT}}
- first_task_index: {{FIRST_TASK_INDEX}}
- first_company: {{FIRST_COMPANY}}
- last_task_index: {{LAST_TASK_INDEX}}
- last_company: {{LAST_COMPANY}}

Method:
- Read `Plan.md` and `agent_prompt_template.md` once, then process each JSONL `input_row`.
- `task_index`, `company_id`, `company_name`, and `normalized_domain` are immutable. Copy them exactly from `tasks.jsonl`.
- Classify company type, crypto project likelihood, search tier, project_search_required, risk flags, and classifier reason.
- Write one classifier row per company to the active attempt `classifier_results.csv`.
- Write one formal result row per company to the active attempt `results.csv`.
- Append rows incrementally as soon as each company is completed.
- Do not start with broad repository scans, cross-batch history lookups, manifest sweeps, or unrelated batch exploration.
- Complete the earliest pending company first and append both rows before wider fan-out.
- Obey narrowed recovery caps and lease checks if the wrapper defines them.

Formal token rule:
- Include a token only when strong, direct, stable evidence shows that the company is an officially recognized founding entity, co-founding entity, or original founding organization of the token's blockchain/protocol ecosystem.
- Exclude ordinary dApps, wallets, exchanges, DEXs, staking providers, validators without founding evidence, investors, launchpads, incubators, market makers, later ecosystem funds, portfolio companies, and ordinary ecosystem participants.
- If multiple tokens qualify, keep one row and put all mappings in `token_results`.
- If no token qualifies, set `token_results = []` and write a clear `token_decision_reason`.
- Write `token_symbol` as the JSON list of every `token_symbol` value from `token_results`, in the same order.
- Keep `token_results` in the final CSV column because it is the widest payload field.
- Before closing a no-token row, run a bounded exact-domain, alias, former-name, and token-family probe when relevant.

Evidence requirements:
- Prefer official and primary sources.
- Secondary sources may corroborate but should not replace direct founding-entity evidence for high-confidence inclusion.
- Each token result object must include `token_symbol`, `token_name`, `token_url`, `reason`, `evidence_urls`, and `evidence_source_types`.
- `project_name`, `project_url`, `token_symbol`, and `token_results` must be JSON-list strings.
- `has_token_evidence` must summarize evidence, not bare `yes` or `no`.
- `evidence_urls` must be `|`-separated HTTP(S) URLs.
- `evidence_source_types` must be `|`-separated lowercase labels.
- `confidence` must be exactly `high`, `medium`, or `low`.
- `needs_manual_review` must be exactly `yes` or `no`.

Classifier CSV header:
{{CLASSIFIER_CSV_HEADER}}

Result CSV header:
{{RESULT_CSV_HEADER}}

Final response should report:
- classifier rows written
- total data rows written
- rows with non-empty `token_results`
- rows with `token_results = []`
- rows with `project_search_required = yes` and `token_results = []`
- rows with `project_search_required = no` and `token_results = []`
- rows by `search_tier`
- `needs_manual_review = yes` count
- authoritative classifier file path
- authoritative results file path
- blocker count
- issue feedback for the main agent, if any
