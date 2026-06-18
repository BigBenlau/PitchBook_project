# Part6 Worker Run

You are Worker {{WORKER_SLOT}} in queue group {{ROUND_INDEX}} for the Part6
investor capability review.

This execution segment must run in a fresh worker context. Do not rely on
memory from any previous batch or previous segment.

Do not revert or overwrite edits made by others.

Batch root context:

- {{RUN_DIR}}

Runtime strategy references:

- {{RUNTIME_ARCHITECTURE}}
- {{RUNTIME_POLICY}}

The attempt runtime wrapper provides the only authoritative write scope and
output file paths. Do not invent alternate write targets.

Read:

- {{PLAN_MD}}
- {{BATCH_FILE}}
- {{TASKS_FILE}}
- {{PROMPT_TEMPLATE}}

Task range:

- batch_file: {{BATCH_FILE_NAME}}
- task_count: {{TASK_COUNT}}
- first_task_index: {{FIRST_TASK_INDEX}}
- first_investor: {{FIRST_COMPANY}}
- last_task_index: {{LAST_TASK_INDEX}}
- last_investor: {{LAST_COMPANY}}

## Method

- Read `Plan.md` and `agent_prompt_template.md` once, then apply that workflow
  to each JSONL `input_row`.
- Treat `part5_to_part6/output/part6_batches/` as the only active input
  universe. Do not use historical final CSVs, branch folders, repair files, or
  audit files as classification evidence.
- Copy `task_index`, `investor_id`, `investor_name`, `normalized_domain`, and
  `primary_investor_type` exactly from `tasks.jsonl`.
- For every investor, classify archetype, crypto-native likelihood,
  operating-capability likelihood, search tier, capability_search_required,
  risk flags, and classifier reason.
- Write one classifier row per investor to the active attempt
  `classifier_results.csv`.
- Write one result row per investor to the active attempt `results.csv`.
- Write incrementally. As soon as one investor is done, append both rows.
- Use `search_tier = full`, `light`, or `skip_candidate` according to
  `Plan.md`.
- Use `capability_search_required = yes` for `full` and `light`; use `no` only
  for `skip_candidate`.
- If `search_tier = skip_candidate`, both likelihood fields must be `none` or
  `low`; if either is `high`, `medium`, or `unclear`, use `light` or `full`.
- Before using `skip_candidate`, run exact-name, alias/former-name,
  exact-domain, official portfolio/backer, and trusted-database probes. If any
  probe or local field shows possible crypto/Web3, financial-services,
  investing/fund, trading/execution/liquidity, DeFi, or parent/sub-fund signal,
  use `light` or `full`.
- If `search_tier = light`, run bounded local-first plus web-confirmation
  probes.
- If `search_tier = full`, search broadly with primary-source priority.

## Evidence And Capability Rules

- Apply the source hierarchy in `Plan.md`: current official sources > current
  official documents/filings/product pages/portfolio pages > trusted
  third-party databases > stale databases / ordinary news / social media /
  local PitchBook input.
- Use ordinary news, social media, and local PitchBook input only for search and
  disambiguation. They cannot directly support a capability `yes`.
- Parent attribution is one-way only and requires current source-backed control.
  Child rows, venture arms, funds, subsidiaries, individuals, portfolio
  companies, minority investments, LP investments, clients, partners, and
  ecosystem members do not inherit parent or affiliate capabilities unless the
  row itself has current evidence.
- `otc_trading = yes` requires current self-operated OTC service or one-way
  parent inheritance from a controlled child/unit. Exclude OTC access-only,
  custody/settlement-only, on-chain RFQ/intent, and historical/stopped service.
- `algorithm_trading = yes` requires current self-operated or provided
  algorithmic, quantitative, systematic, HFT, low-latency engine, automated
  strategy, bot, or algorithm-trading service/agency capability, or one-way
  parent inheritance. Do not infer it from market-making, proprietary trading,
  "technology-driven" wording, API/FIX/connectivity, routing algorithms alone,
  or historical/stopped service.
- `market_making = yes` requires current self-operated market making or
  liquidity provision using own/proprietary/balance-sheet/controlled capital,
  or one-way parent inheritance. Do not infer it from generic liquidity wording,
  quotes/pricing only, exchange/broker status alone, AMM/DEX operation without
  LP capital, third-party market-maker allocations, or historical/stopped
  service.
- `execution_services = yes` requires current self-operated order placement,
  order handling, executable brokerage, trade execution, execution venue,
  matching engine, exchange/CEX, ATS/MTF/ECN, executable DMA, DEX, swap,
  perp DEX, AMM, or on-chain trading protocol, or one-way parent inheritance.
  Do not infer it from API/FIX/connectivity alone, routing alone, liquidity
  access alone, external wallet links, white-label third-party execution,
  custody/post-trade-only service, market making alone, OTC desk alone, or
  historical/stopped service.
- `defi = yes` requires current DeFi trading or DeFi protocol operation. Count
  DeFi protocol operation, DEX/AMM/swap/perp/options/RFQ/intent trading,
  lending/borrowing/credit use, leverage/collateral activity, vault/yield,
  liquid staking/restaking, LP capital deployment, DeFi market making,
  on-chain arbitrage, MEV, liquidations, managed DeFi strategy, or one-way
  parent inheritance from a controlled child/unit/fund doing those activities.
  Do not infer it from DeFi portfolio exposure, token investment, SAFT, grants,
  accelerator support, ecosystem funding, DeFi-adjacent infrastructure exposure,
  customer DeFi access, secondary-market token holding, or historical/stopped
  activity.
- `sub_fund = yes` requires current evidence that the current row is the
  parent/mother entity that has under it a sub-fund, fund vehicle, venture arm,
  investment arm, crypto arm, dedicated capital pool, dedicated
  investment/trading branch, or comparable sub-fund-like structure. Do not
  infer it from row-itself-is-child cases, manager-only evidence, name-only
  matches, ordinary closed funds, or historical/stopped structures.
- For founders, individuals, parent/group entities, controlled affiliates, and
  branded operating platforms, accept attribution only when the source clearly
  ties the capability to the investor row. If still ambiguous after one extra
  search pass, set `needs_manual_review = yes`.

## Output Rules

- Keep the six capability columns and `capability_labels` consistent.
  `capability_labels` must equal the JSON list of all capability columns whose
  value is `yes`.
- `other_flags`, `risk_flags`, and `capability_labels` must be valid JSON-list
  strings.
- `evidence_urls` must use `|`-separated absolute HTTP(S) URLs.
- `evidence_source_types` must use `|`-separated lowercase labels such as
  `official_site`, `official_docs`, `official_filing`,
  `official_blog_or_press`, `trusted_database`, `secondary_profile`,
  `ordinary_news_context`, or `local_csv`.
- Do not use `ordinary_news_context` or `local_csv` as direct `yes` support.
- `completed_at` must be a literal ISO-8601 timestamp; never write shell syntax
  such as `$(date -u ...)`.
- For no-search skip rows, leave `evidence_urls` and `evidence_source_types`
  blank instead of writing `[]`.
- `evidence_summary` must be non-empty for every result row.
- `confidence` must be exactly `high`, `medium`, or `low`.
- Before final response, validate that no `skip_candidate` classifier row has
  either likelihood field set to `high`, `medium`, or `unclear`.
- If you hit a blocker or systematic ambiguity, report it back to the main
  agent instead of silently working around it.

Classifier CSV header:

{{CLASSIFIER_CSV_HEADER}}

Result CSV header:

{{RESULT_CSV_HEADER}}

Final response should report:

- classifier rows written
- total data rows written
- rows with non-empty `capability_labels`
- rows with `capability_labels = []`
- rows with `capability_search_required = yes` and `capability_labels = []`
- rows with `capability_search_required = no` and `capability_labels = []`
- rows by `search_tier`
- `needs_manual_review = yes` count
- authoritative classifier file path
- authoritative results file path
- blocker count
