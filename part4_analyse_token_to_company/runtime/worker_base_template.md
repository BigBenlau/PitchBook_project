# Part4 Worker Run

You are Worker {{WORKER_SLOT}} in round {{ROUND_INDEX}} for the part4 token-to-company review.

This execution segment must run in a fresh worker context. Do not rely on memory from previous batches or earlier attempts.

Read:

- {{PLAN_MD}}
- {{BATCH_FILE}}
- {{TASKS_FILE}}
- {{PROMPT_TEMPLATE}}

Runtime references:

- {{RUNTIME_ARCHITECTURE}}
- {{RUNTIME_POLICY}}

Task range:

- batch_file: {{BATCH_FILE_NAME}}
- task_count: {{TASK_COUNT}}
- first_task_index: {{FIRST_TASK_INDEX}}
- first_token: {{FIRST_COMPANY}}
- last_task_index: {{LAST_TASK_INDEX}}
- last_token: {{LAST_COMPANY}}

Rules:

- `task_index`, `canonical_slug`, `token_symbol`, and `token_name` are immutable identity fields
- write one classifier row and one result row per token
- write incrementally; do not hold the whole batch until the end
- complete the earliest pending token first and append its rows early
- do not hand-edit CSV text, shell-append CSV lines, or rewrite the whole CSV ad hoc
- all classifier/result row writes must go through `part4_analyse_token_to_company/scripts/part4_safe_csv_append.py`
- when writing a row, pass the authoritative `tasks.jsonl` with `--tasks-file` so immutable identity fields are enforced from the task row
- when the attempt wrapper provides `attempt_metadata.json`, also pass it with `--attempt-metadata` so preserved recovery-prefix rows cannot be rewritten
- if `cg_url` exists in the task row, directly visit that CoinGecko slug page
- if `cmc_url` exists in the task row, directly visit that CoinMarketCap slug page
- if both `cg_url` and `cmc_url` exist, visit both pages in the same research flow before closing the token
- do not start with repo-wide scans or broad unrelated exploration
- prefer official and primary sources, but use reliable secondary sources for corroboration when needed
- `mapped_entity_name` and related entity fields are JSON list strings
- `mapped_entity_type` must classify each mapped entity as `company`, `foundation`, `issuer`, `association`, `trust`, `dao_legal_wrapper`, `nonprofit`, `government_entity`, `other_legal_entity`, or `unclear`
- only map issuer / operator / steward / legal-counterparty style entities; do not map generic advocacy groups or incidental community organizations
- if multiple entities each have strong, direct, and stable responsibility evidence, keep all of them in parallel JSON-list positions instead of collapsing to one entity
- foundation + operating company, issuer + operator, and association + legal wrapper are all valid parallel patterns when each entity independently clears the evidence bar
- do not drop an operating company only because a foundation appears more official, and do not drop a foundation only because a company appears more operational
- if no reliable entity mapping is found after real search, keep mapped entity list fields as `[]`
- `has_entity_evidence` must never be blank
- `evidence_urls` must be absolute HTTP(S) URLs joined by `|`
- `evidence_source_types` must use lowercase underscore labels joined by `|`
- multi-entity output by itself is not a reason to set `needs_manual_review = yes`; use manual review only when inclusion/exclusion is still unresolved after best-effort source checking

Classifier CSV header:

{{CLASSIFIER_CSV_HEADER}}

Result CSV header:

{{RESULT_CSV_HEADER}}

Safe write pattern:

- stage a structured JSON object for the current row in the active attempt directory
- call `python3 part4_analyse_token_to_company/scripts/part4_safe_csv_append.py --schema classifier ...` for the classifier row
- call `python3 part4_analyse_token_to_company/scripts/part4_safe_csv_append.py --schema result ...` for the result row
- pass `--tasks-file` on every write, and pass `--attempt-metadata` whenever the wrapper provides an authoritative attempt metadata path
- use `--row-json-file` for larger payloads instead of trying to inline fragile shell quoting
