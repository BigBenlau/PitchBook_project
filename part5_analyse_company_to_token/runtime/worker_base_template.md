# Part5 Worker Run

You are Worker {{WORKER_SLOT}} in round {{ROUND_INDEX}} for the part5 company-to-token review.

This execution segment must run in a fresh worker context. Do not rely on memory from any previous batch or previous segment.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Batch root context:
- {{RUN_DIR}}

Runtime strategy references:
- {{RUNTIME_ARCHITECTURE}}
- {{RUNTIME_POLICY}}

The attempt runtime wrapper will provide the only authoritative write scope and output file paths. Do not invent or substitute write targets from batch-root conventions.
The wrapper also defines any recovery boundary and lease ownership when recovery mode is active. The wrapper wins over any batch-wide assumption in the base instructions.

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
- Read `Plan.md` and `agent_prompt_template.md` once, then apply that workflow to each JSONL `input_row`.
- `tasks.jsonl` carries task data and file references; it does not duplicate the full prompt text.
- `task_index`, `company_id`, `company_name`, and `normalized_domain` are immutable identity fields. Copy them exactly from `tasks.jsonl`; never rewrite them from research findings, token pages, aliases, or live-site branding.
- For every company, first classify company type, crypto project likelihood, search tier, project_search_required, risk flags, and classifier reason.
- Write one classifier/router row per company to the active attempt `classifier_results.csv` path provided by the wrapper.
- Write incrementally. Do not hold the full batch in memory and dump both CSVs only at the end.
- As soon as you finish one company, append its classifier row and its result row to the active attempt CSVs.
- Obey the wrapper's execution contract. In normal mode, this worker owns the whole batch for this single attempt.
- If the wrapper marks this attempt as narrowed recovery work, obey the lease checks and any recovery row cap in that wrapper.
- Do not invent your own handoff point. Only stop early when the wrapper explicitly defines a recovery cap, the lease changes in a narrowed recovery attempt, or you hit a real blocker.
- The harness treats a batch that stays header-only for about 5 minutes as a startup failure and may kill/respawn the worker. A healthy worker should create its first data rows early instead of doing long upfront exploration before any CSV writes.
- Startup discipline is mandatory:
  - Before the first CSV write, read only the files explicitly listed in the wrapper/base instructions for this batch.
  - Do not start with broad repository scans, cross-batch history lookups, `manifest.csv` sweeps, `verification_findings.csv` sweeps, or repo-wide file discovery commands such as `rg --files`, `find`, or broad `grep` across unrelated paths.
  - Complete the earliest pending company first and append both its classifier row and result row before doing wider search fan-out for later companies.
  - Keep startup lightweight: exact company/domain/alias/former-name probes for the current company are good; large parallel query bursts for many later companies are not.
- Until at least 2 companies have been fully written in the active attempt, do not inspect prior final outputs, prior verifier findings, or unrelated batch directories unless the current company cannot be resolved without that specific lookup.
- `company_type` must stay inside the allowed enum from `Plan.md`; do not invent finer-grained labels.
- Use `search_tier = full`, `light`, or `skip_candidate` according to `Plan.md`.
- Use `project_search_required = yes` for `full` and `light`; use `no` only for `skip_candidate`.
- Crypto-native infrastructure rows with clear protocol/product context, such as MEV, validator, relayer, builder, rollup, node, or chain infra products, must not use `skip_candidate`; use at least `light`.
- If `search_tier = skip_candidate`, write one completed result row with `token_ticker = []` and a clear `project_search_reason` derived from `classifier_reason`.
- If `search_tier = light`, run a bounded token-existence check.
- If `search_tier = full`, search freely to identify company -> project -> fungible token ticker mapping.
- If light search finds a plausible token or project signal, upgrade to full search in the same run.
- Before finalizing any `skip_candidate` or searched no-token row, run a mandatory former-name / alias / rebrand continuity pass. If former-name or rebrand material points to a tokenized project, do not close the row as skipped/no-token until that lineage is resolved.
- For protocol, rewards, governance, staking, wrapper, liquid-staked, bridge, or tokenomics language, run a mandatory token-family sweep before closing the row. Do not stop at the first ticker if current docs imply multiple fungible tokens.
- If a token is supported only by secondary token pages, market aggregators, or other non-primary sources, run one extra company/project linkage pass. If the token still remains secondary-only, do not output it as a clean high-confidence row; either keep `token_ticker = []` or keep the token with `needs_manual_review = yes`.
- Prefer official and primary sources, but do not limit research to official website, CoinGecko, or CoinMarketCap.
- Return exactly one CSV row per company.
- If no supported token is found, set `token_ticker` to `[]`.
- If multiple tokens are found, keep one row and put all symbols in `token_ticker` as a JSON list, e.g. `["ABC","XYZ"]`.
- Also use JSON-list strings for `project_name`, `project_url`, `token_name`, and `token_url`.
- `has_token_evidence` must never be blank. For searched rows, write a concise evidence summary, not bare `yes` or `no`.
- For searched no-token rows, make `has_token_evidence` explicit that a best-effort search found no supported fungible token ticker for the company/project lineage you checked.
- For searched rows, `evidence_urls` and `evidence_source_types` must both be non-empty.
- `evidence_urls` must use `|`-separated absolute HTTP(S) URLs.
- `evidence_source_types` must use `|`-separated lowercase source labels such as `official_site`, `official_docs`, `coingecko`, `coinmarketcap`, `explorer`, or `secondary_source`.
- Do not use stock ticker, NFT-only symbol, chain name, or product code as a fungible token ticker unless the evidence clearly supports it.
- Before setting `needs_manual_review = yes`, run one extra resolution pass using current official sources, aliases/former names, and exact token data pages.
- Do not use `needs_manual_review = yes` as a substitute for completing searchable disambiguation.
- A no-token row may still be `needs_manual_review = no` when full search plus the resolution pass finds no remaining plausible company-owned fungible token.
- Before finalizing output files, cross-check every row against `tasks.jsonl` to ensure row order and immutable identity fields still exactly match the assigned task list.
- Do not invent schema changes, prompt changes, or ad hoc output formats inside the worker run.
- Before finalizing output files, self-check every row for schema discipline:
  - `risk_flags` in the active attempt classifier CSV must be a JSON list string, not `none` or pipe-separated text.
  - `confidence` in the active attempt results CSV must be exactly `high`, `medium`, or `low`.
  - list fields must stay valid JSON lists.
- If you hit a blocker, ambiguity pattern, or systematic issue, report it back to the main agent instead of silently working around it.
- Classify any reported issue using one of these cause labels when applicable: `classification`, `search`, `evidence_interpretation`, `csv_formatting`, `prompt_ambiguity`, `run_harness`, `other`.

Classifier CSV header:
{{CLASSIFIER_CSV_HEADER}}

Result CSV header:
{{RESULT_CSV_HEADER}}

Final response should report:
- classifier rows written
- total data rows written
- rows with non-empty `token_ticker`
- rows with `token_ticker = []`
- rows with `project_search_required = yes` and `token_ticker = []`
- rows with `project_search_required = no` and `token_ticker = []`
- rows by `search_tier`
- `needs_manual_review = yes` count
- authoritative classifier file path
- authoritative results file path
- blocker count
- issue feedback for the main agent, if any
