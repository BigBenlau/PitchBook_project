# Part6 Worker Run

You are Worker {{WORKER_SLOT}} in round {{ROUND_INDEX}} for the part6 investor capability review.

This execution segment must run in a fresh worker context. Do not rely on memory from any previous batch or previous segment.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Batch root context:
- {{RUN_DIR}}

Runtime strategy references:
- {{RUNTIME_ARCHITECTURE}}
- {{RUNTIME_POLICY}}

The attempt runtime wrapper provides the only authoritative write scope and output file paths. Do not invent alternate write targets.

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

Method:
- Read `Plan.md` and `agent_prompt_template.md` once, then apply that workflow to each JSONL `input_row`.
- `task_index`, `investor_id`, `investor_name`, `normalized_domain`, and `primary_investor_type` are immutable input metadata fields. Copy them exactly from `tasks.jsonl`.
- For every investor, first classify archetype, crypto-native likelihood, operating-capability likelihood, search tier, capability_search_required, risk flags, and classifier reason.
- Write one classifier row per investor to the active attempt `classifier_results.csv`.
- Write incrementally. As soon as one investor is done, append both classifier and result rows.
- Use `search_tier = full`, `light`, or `skip_candidate` according to `Plan.md`.
- Use `capability_search_required = yes` for `full` and `light`; use `no` only for `skip_candidate`.
- If `search_tier = skip_candidate`, both `crypto_native_likelihood` and `operating_capability_likelihood` must be `none` or `low`; if either is `high`, `medium`, or `unclear`, use `light` or `full` instead.
- If `search_tier = skip_candidate`, still write one completed result row with all six capability flags set to `no`, `capability_labels = []`, a clear `capability_search_reason`, and a non-empty `evidence_summary` describing the exact-name/domain probes or local-context checks.
- Before using `skip_candidate`, run exact-name, alias/former-name, exact-domain, official portfolio/backer, and trusted-database probes. If those probes show exchange, OTC, DEX, AMM, liquidity, routing, brokerage, quant, DeFi product, current DeFi investment/backing/support, feeder, umbrella, protected-cell, SPV, parallel fund, fund-of-funds, proprietary-capital investment arm, balance-sheet venture arm, corporate venture arm, or dedicated parent-company crypto/Web3 investment branch signals, use `light` or `full`.
- If `search_tier = light`, run the bounded local-first plus web-confirmation playbook.
- If `search_tier = full`, search freely, prioritizing official and primary sources.
- Apply the global source hierarchy: current official source > current official portfolio/backer page > trusted third-party database > stale database / ordinary news / social media / local PitchBook input. If current official sources conflict with trusted databases, prefer the official source. Use ordinary news, social media, and local PitchBook only as search/disambiguation context, not direct `yes` evidence.
- Current evidence means the capability, holding, child structure, service, product, venue, protocol, or portfolio/support relationship is still shown in current official pages/docs/product pages/filings/portfolio pages or current trusted third-party database profiles. Archive pages, old announcements, stale database entries, removed official pages, discontinued products, bankrupt/liquidated entities, wound-down funds, stopped protocols, or unconfirmed historical mentions do not support `yes`.
- Controlled attribution requires a wholly owned subsidiary, controlled subsidiary, controlled operating division, controlled business unit, controlled brand/platform, or official group entity. Portfolio companies, minority investments, LP investments, partners, ecosystem members, unaffiliated affiliates, ordinary clients, and service providers are not controlled subsidiaries/operating units.
- Treat `otc_trading` as a current operating-capability label, not an investment-exposure label. Use `otc_trading = yes` only when official sources or trusted third-party databases show that the investor itself currently provides OTC trading service, or when the investor is a parent company and a controlled subsidiary, venture arm, or operating unit currently provides OTC trading service.
- OTC trading includes OTC desk, OTC trading, over-the-counter trading, block trading, off-exchange trading, bilateral trading, bilateral liquidity, institutional OTC, dealer-to-client OTC, and centralized dealer/broker/counterparty RFQ. Both crypto/digital-asset OTC and traditional finance OTC can qualify, including OTC equities / OTC Markets securities trading, OTC derivatives, FX OTC, fixed-income OTC, commodities OTC, bilateral options, and swaps, when the investor itself currently provides that service.
- Parent attribution for OTC is one-way only: a parent company can inherit a controlled subsidiary / venture arm / operating unit's current OTC service, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's OTC service unless that row itself provides OTC service.
- Mark `otc_trading = no` when the only evidence is portfolio exposure, investment in an OTC company, broker-dealer status alone, market-maker status alone, inter-dealer participant status alone, liquidity-provider language alone, deep-liquidity language alone, OTC access/connection to third-party counterparties, OTC settlement/custody/post-trade support, DEX RFQ, intent/on-chain RFQ, on-chain block trade, secondary-market token holding, or founder/advisor/executive association. Also mark `no` when the only OTC evidence is historical and the entity is bankrupt, stopped, liquidated, the service/product is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation.
- Use the same evidence standard as `defi`: official sources and trusted third-party databases can support `otc_trading = yes`; local PitchBook input data alone, ordinary news, and social media cannot.
- Judge `execution_services` separately from `otc_trading`. Do not automatically infer `execution_services` from OTC; require explicit order placement, order handling, executable brokerage, RFQ execution, trade execution, matching/venue operation, or comparable executable transaction evidence.
- Treat `algorithm_trading` as a current operating-capability label, not an investment-exposure label. Use `algorithm_trading = yes` only when official sources or trusted third-party databases show that the investor itself currently uses, provides, or operates algorithmic, quantitative, systematic, HFT/high-frequency, low-latency trading-engine, automated trading-strategy, or algorithm-trading service/agency capability, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.
- Apply a hard negative rule for `algorithm_trading`: portfolio exposure, investment in a quant/HFT/bot company, market-maker status alone, proprietary-trading status alone, liquidity-provider language alone, "technology-driven trading firm" language alone, sophisticated trading-technology language alone, API/FIX/connectivity access, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing/execution algorithms alone, brokerage/prime-brokerage/execution-desk/liquidity-access products, secondary-market token holding, and founder/advisor/executive association are not enough for `algorithm_trading = yes`.
- Algorithm trading can be crypto or traditional finance, but current explicit operation/provision is required. Traditional quant trading, systematic trading, HFT, low-latency trading engines, and current trading-bot / grid-bot / AI-bot strategies qualify only when explicitly operated or provided by the investor row, or inherited one-way by a parent row from a controlled subsidiary / operating unit. Historical, stopped, bankrupt, discontinued, or stale-only evidence is `algorithm_trading = no`.
- Treat `market_making` as a current operating-capability label, not an investment-exposure label. Use `market_making = yes` only when official sources or trusted third-party databases show that the investor itself currently provides market making or liquidity provision service using its own, proprietary, balance-sheet, or otherwise controlled capital/liquidity, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.
- Apply a hard negative rule for `market_making`: portfolio exposure, investment in a market maker/liquidity provider, generic liquidity-provider language, "provides liquidity" marketing language, deep-liquidity language, liquidity access, connecting clients to liquidity providers, sourcing liquidity, providing quotes only, request-for-quote pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker/execution-desk status alone, proprietary-trading/HFT/quant-trading status alone, passive fund investment, passive LP allocation, client portfolio allocation, token/protocol liquidity support or ecosystem funding that is not the investor's own ongoing LP/market-maker role, AMM/DEX/pool operation without LP capital, third-party market-maker allocations, secondary-market token holding, and founder/advisor/executive association are not enough for `market_making = yes`.
- Market making can be crypto or traditional finance, but current explicit liquidity-capital provision is required. Official/designated market maker, designated liquidity provider, LP, principal liquidity, balance-sheet liquidity, traditional market maker, or OTC bilateral/RFQ liquidity roles qualify only when the source shows the investor currently provides capital/liquidity as a market maker or LP, or inherited one-way by a parent row from a controlled subsidiary / operating unit. Historical, stopped, bankrupt, discontinued, or stale-only evidence is `market_making = no`.
- Treat `execution_services` as a current operating-capability label, not an investment-exposure label. Use `execution_services = yes` only when official sources or trusted third-party databases show that the investor itself currently provides or operates trade execution, order placement, order handling, executable brokerage, execution venue, matching engine, exchange/CEX, ATS/MTF/ECN, agency execution, prime-brokerage execution, DMA/execution access with executable order entry, DEX, swap, perp DEX, AMM, or on-chain trading protocol capability, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.
- Apply a hard negative rule for `execution_services`: portfolio exposure, investment in a broker/exchange/DEX/execution platform, API/FIX/connectivity access alone, routing or smart order routing alone, liquidity access alone, liquidity aggregation alone, connecting users to third-party venues/counterparties/liquidity providers, wallet connection to an external DEX/venue, white-label or embedded third-party execution, redirect-to-external-venue trading, wallet/portfolio/analytics app with view-only or external-link trading, custody/settlement/clearing/post-trade-only service, market-making status alone, OTC desk status alone, exchange listing, maker/taker fee schedule, secondary-market token holding, and founder/advisor/executive association are not enough for `execution_services = yes`.
- Execution services can be crypto or traditional finance, but current actual transaction capability is required. Broker service qualifies only when it can place, handle, route-to-execution, or execute client/user orders. CEX, traditional exchange, ATS, ECN, MTF, DEX, swap, perp DEX, AMM, and on-chain trading protocol operation qualify when the investor itself operates the trading/swap/venue/protocol function. Historical, stopped, bankrupt, discontinued, or stale-only evidence is `execution_services = no`.
- Treat DEX/AMM/swap/liquidity-pool protocol infrastructure as candidates for `execution_services` when the investor itself operates the trading/swap/venue/protocol function; AMM/DEX/pool operation alone is not `market_making` unless the investor itself provides LP capital. For `defi`, apply the current DeFi exposure / investment / support / operation rules below.
- Treat `sub_fund` as a current structure / attribution label judged from the current investor row as the parent/mother entity. Use `sub_fund = yes` only when official sources or trusted third-party databases show that the current investor currently owns, controls, contains, or has under it a sub-fund, fund vehicle, venture arm, investment arm, crypto arm, dedicated capital pool, dedicated investment/trading branch, or comparable sub-fund-like structure.
- Traditional sub-fund structures and broad internal structures qualify only when they are current child structures under the current investor as parent/mother entity. Candidate child structures include sub-fund, feeder fund, master-feeder, umbrella fund compartment, parallel fund, SPV, segregated portfolio, protected cell, fund platform, fund-of-funds vehicle, venture arm, investment arm, crypto arm, proprietary-capital investment arm, balance-sheet venture arm, dedicated strategy division, and specialized internal capital pool.
- Apply a hard negative rule for `sub_fund`: row itself being a fund vehicle, feeder, SPV, protected cell, venture arm, investment arm, crypto arm, subsidiary, brand, business unit, accelerator, incubator, ecosystem program, portfolio company, ordinary CVC type, externally managed fund, generic fund manager, ordinary closed fund, `LastClosedFundName`, `PrimaryInvestorType`, or name terms such as Ventures, Capital, Labs, Crypto Fund, Fund I, or SPV is not enough for `sub_fund = yes`. Do not use specific sample entities as hard positives. Historical, liquidated, wound-down, closed, no-longer-investing, discontinued, or stale-only child structures are `sub_fund = no`.
- For founders, individuals, parent/group entities, controlled affiliates, and branded operating platforms, accept attribution only when the source clearly ties the capability to the investor row through ownership, control, executive role, or brand/platform identity. If still ambiguous after one extra search pass, set `needs_manual_review = yes`.
- Exclude portfolio-company-only evidence for non-`defi` capabilities, generic crypto exposure, exchange listings, maker/taker fees, third-party market-maker token allocations, and educational content unless they clearly describe the investor's own operating capability. For `defi`, current portfolio/investment/support exposure can support `yes` under the DeFi rules below.
- Mark `defi = yes` as a current DeFi exposure / investment / support / operation label. It includes direct DeFi operation and current DeFi investment exposure.
- Use `defi = yes` when official sources or trusted third-party databases show, as of the agent search time, that the investor itself operates, invests in, backs, grants, incubates, accelerates, ecosystem-funds, liquidity-supports, or otherwise supports a DeFi or DeFi-adjacent company/protocol.
- Also use `defi = yes` when a controlled venture arm, controlled investment arm, controlled fund vehicle, current official public portfolio, or source-attributed parent-controlled investment activity connected to the investor row currently has DeFi or DeFi-adjacent exposure.
- DeFi and DeFi-adjacent companies/protocols include DEX, AMM, swap, lending, borrowing, credit, vault, yield, liquid staking, restaking, oracle, bridge, cross-chain messaging, L1/L2, wallet, custody, staking infrastructure, MEV infrastructure, RWA, NFT finance, perp DEX, derivatives protocol, prediction market, intent/RFQ protocol, DeFi liquidity management, and on-chain execution infrastructure.
- Token round / SAFT / treasury round participation, grants, accelerator support, ecosystem funding, and liquidity support count as DeFi investment/support when tied to a DeFi or DeFi-adjacent company/protocol. Secondary-market token holding, founder tokens, or undisclosed token positions do not count.
- Use current official pages, official filings, and trusted databases such as RootData, Crunchbase, CB Insights, CoinCarp, AngelList, and similar investment databases. Do not use local PitchBook input data alone as `defi = yes` evidence. Do not rely on ordinary news or social media alone. If a complete current official portfolio omits an older news-only investment, prefer the official portfolio.
- Mark `defi = no` when the only evidence is a crypto/Web3/blockchain name, thesis, vertical, or fund strategy; a clearly exited, stopped, wound-down, removed, pivoted, or bankrupt historical DeFi investment; secondary-market token holding; founder/advisor/executive employment or token ownership without disclosed investment/backing; or an unrelated affiliate relationship. For individual investors, require disclosed investment/backing/grant/portfolio evidence, not only founder/advisor/executive status.
- For `sub_fund`, apply the current parent/mother-entity structure standard. Accept traditional fund structures and broad internal arms only when they are current child structures under the current investor row, and reject name-only, row-itself-is-a-child, manager-only, and stale/historical evidence.
- For all labels, set `needs_manual_review = yes` after one extra disambiguation pass when entity identity, current status, parent/control relationship, official-vs-database conflict, self-operated-vs-third-party service, or source attribution remains unclear. Do not force a `yes` from ambiguous evidence.
- Keep the six capability columns and `capability_labels` consistent. `capability_labels` must equal the JSON list of all capability columns whose value is `yes`.
- `other_flags`, `risk_flags`, and any snapshot list fields must be valid JSON-list strings.
- `evidence_urls` must use `|`-separated absolute HTTP(S) URLs.
- `evidence_source_types` must use `|`-separated lowercase labels such as `official_site`, `official_docs`, `official_filing`, `official_blog_or_press`, `trusted_database`, `secondary_profile`, `ordinary_news_context`, or `local_csv`. Do not use `ordinary_news_context` or `local_csv` as direct `yes` support.
- `completed_at` must be a literal ISO-8601 timestamp; never write shell syntax such as `$(date -u ...)`.
- `evidence_urls` and `evidence_source_types` are pipe-list fields, not JSON-list fields; for no-search skip rows leave them blank instead of writing `[]`.
- `evidence_summary` must be non-empty for every result row. For `skip_candidate`, summarize the probes/checks and why they support all six capability flags = `no`.
- `confidence` must be exactly `high`, `medium`, or `low`.
- Before final response, validate that no `skip_candidate` classifier row has `crypto_native_likelihood` or `operating_capability_likelihood` set to `high`, `medium`, or `unclear`.
- If you hit a blocker or systematic ambiguity, report it back to the main agent instead of silently working around it.

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
