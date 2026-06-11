# Part6 Agent Prompt Template

Before doing any part6 investor capability work, read:

1. `part6_analyse_investor_capabilities/Plan.md`
2. this file

If this file conflicts with `Plan.md`, `Plan.md` wins.

Capability drift guard:
- Use only the current definitions in `Plan.md`, this prompt, and the generated worker/verifier instructions for this run.
- Do not copy labels, thresholds, or capability boundaries from old `results.csv`, old audit reports, old repair files, or memory from previous part6 runs.
- If a source or old output conflicts with the current definition, follow the current definition and record the reason in `evidence_summary` or verifier feedback.

## Scope

Task goal:
- classify each investor into an archetype
- decide `search_tier`
- determine whether the investor should be labeled `yes/no` for:
  - `otc_trading`
  - `algorithm_trading`
  - `market_making`
  - `execution_services`
  - `defi`
  - `sub_fund`
- write one classifier row and one result row per investor

Do not do:
- token mapping
- valuation analysis
- market commentary
- entity merging across unrelated PitchBook rows

## Required Workflow

1. Read `Plan.md`.
2. Read the assigned investor row.
3. Determine why the row appears in the Part5-to-Part6 investor graph batch. Use `MatchedKeywords`, `MatchedColumns`, and `InvestorCapabilityContext` to understand the token-company relationship path.
4. Copy `task_index`, `investor_id`, `investor_name`, `normalized_domain`, and `primary_investor_type` exactly from the top-level task fields. Do not infer, normalize, or replace these input metadata values.
5. Fill `investor_archetype`, `crypto_native_likelihood`, `operating_capability_likelihood`, `search_tier`, `capability_search_required`, `risk_flags`, and `classifier_reason`.
6. Write the classifier row.
7. Use `search_tier = skip_candidate` only for rows that are clearly and completely unrelated to crypto/Web3, financial services, investing/funds, trading/execution/liquidity, DeFi, and parent/sub-fund structure. If `search_tier = skip_candidate`, write a completed result row with all six capability flags = `no`, `capability_labels = []`, a clear `capability_search_reason`, and a non-empty `evidence_summary` documenting why the row is completely unrelated.
8. If `search_tier = light`, run bounded local-first plus web-confirmation probes.
9. If `search_tier = full`, search more broadly with primary-source priority.
10. Write one result row per investor.
11. Keep `capability_labels` synchronized with the six boolean capability columns.
12. If evidence conflicts or the label boundary is genuinely ambiguous, set `needs_manual_review = yes`.

## Classification Rules

Allowed `investor_archetype` values:
- `traditional_vc_or_pe`
- `crypto_native_vc`
- `hedge_fund_or_quant`
- `market_maker_or_otc_firm`
- `asset_manager_or_family_office`
- `accelerator_or_incubator`
- `angel_or_individual`
- `exchange_affiliated_investor`
- `operating_company_disguised_as_investor`
- `fund_vehicle_or_fund_platform`
- `unclear`

Allowed likelihood values:
- `high`
- `medium`
- `low`
- `none`
- `unclear`

Allowed `search_tier` values:
- `full`
- `light`
- `skip_candidate`

Allowed `capability_search_required` values:
- `yes`
- `no`

Hard rules:
- `full` or `light` requires `capability_search_required = yes`
- `skip_candidate` requires `capability_search_required = no`
- `skip_candidate` is a narrow exception. The default for any potentially relevant investor row is `light` or `full`; use agent search unless the row is clearly unrelated.
- `skip_candidate` requires both `crypto_native_likelihood` and `operating_capability_likelihood` to be `none` or `low`; if either likelihood is `high`, `medium`, or `unclear`, use `light` or `full` instead
- if the row, local input fields, domain, parent, description, preferred verticals, matched keywords/context, official site, or trusted database profile contains any possible crypto/Web3/blockchain/digital-asset/token/DAO/NFT/metaverse/gaming-in-Web3, fintech/financial-services/payments/banking/insurance/capital-markets, investor/fund/VC/PE/asset-manager/family-office/angel/accelerator/incubator/corporate-venture, OTC / liquidity / market making / execution / routing / brokerage / quant / DeFi / feeder / umbrella / SPV / fund-of-funds language, do not use `skip_candidate`
- before using `skip_candidate`, run exact-name, alias/former-name, exact-domain, official portfolio/backer, and trusted-database probes; if those probes show any possible crypto/Web3, financial, investor/fund, trading/execution/liquidity, DeFi, or sub-fund/parent structure signal, use `light` or `full`
- if uncertain between `skip_candidate` and `light`, use `light`

## Capability Rules

Global source hierarchy: current official source wins over current official portfolio/backer pages, which win over trusted third-party databases, which win over stale databases, ordinary news, social media, and local PitchBook input. If a current official source conflicts with a trusted database, prefer the official source. Use ordinary news, social media, and local PitchBook only as search/disambiguation context, not as direct `yes` evidence.

Current evidence means the capability, holding, child structure, service, product, venue, protocol, or portfolio/support relationship is still shown in current official pages, current official documents, current official portfolio/backer pages, current official product/service pages, current official filings, or current trusted third-party database profiles. Archive pages, old announcements, stale database entries, removed official pages, discontinued products, bankrupt/liquidated entities, wound-down funds, stopped protocols, or unconfirmed historical mentions do not support `yes`.

Controlled attribution means the investor row is the parent/mother entity and the source shows a wholly owned subsidiary, controlled subsidiary, controlled operating division, controlled business unit, controlled brand/platform, or official group entity. Do not treat portfolio companies, minority investments, LP investments, partners, ecosystem members, unaffiliated affiliates, ordinary clients, or service providers as controlled subsidiaries/operating units.

For all non-`defi` labels, portfolio-company-only evidence, investee product features, generic crypto exposure, educational content, third-party allocations, and associated-person employment/founder/advisor links do not support `yes` unless the source clearly attributes current operating control or service operation to the investor row.

Set `needs_manual_review = yes` after one extra disambiguation pass when entity identity, current status, parent/control relationship, official-vs-database conflict, self-operated-vs-third-party service, or source attribution remains unclear. Do not force a `yes` from ambiguous evidence.

Mark `otc_trading = yes` as a current operating-capability label, not an investment-exposure label. Use `yes` only when official sources or trusted third-party databases show that the investor itself currently provides OTC trading service, or when the investor is a parent company and a controlled subsidiary, venture arm, or operating unit currently provides OTC trading service.

OTC trading includes OTC desk, OTC trading, over-the-counter trading, block trading, off-exchange trading, bilateral trading, bilateral liquidity, institutional OTC, dealer-to-client OTC, and centralized dealer/broker/counterparty RFQ. Both crypto/digital-asset OTC and traditional finance OTC can qualify, including OTC equities / OTC Markets securities trading, OTC derivatives, FX OTC, fixed-income OTC, commodities OTC, bilateral options, and swaps, when the investor itself currently provides that service.

Parent attribution for OTC is one-way only: a parent company can inherit a controlled subsidiary / venture arm / operating unit's current OTC service, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's OTC service unless that row itself provides OTC service.

Mark `otc_trading = no` when the only evidence is portfolio exposure, investment in an OTC company, broker-dealer status alone, market-maker status alone, inter-dealer participant status alone, liquidity-provider language alone, deep-liquidity language alone, OTC access/connection to third-party counterparties, OTC settlement/custody/post-trade support, DEX RFQ, intent/on-chain RFQ, on-chain block trade, secondary-market token holding, or founder/advisor/executive association. Also mark `no` when the only OTC evidence is historical and the entity is bankrupt, stopped, liquidated, the service/product is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation.

Use the same evidence standard as `defi`: official sources and trusted third-party databases can support `otc_trading = yes`; local PitchBook input data alone, ordinary news, and social media cannot.

Mark `algorithm_trading = yes` only as a current operating-capability label, not an investment-exposure label. Use `yes` only when official sources or trusted third-party databases show that the investor itself currently uses, provides, or operates algorithmic, quantitative, systematic, HFT/high-frequency, low-latency trading-engine, automated trading-strategy, or algorithm-trading service/agency capability, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.

Algorithm trading can be crypto or traditional finance. Traditional quant trading, systematic trading, HFT, low-latency trading engines, and current trading-bot / grid-bot / AI-bot strategies can qualify only when explicitly operated or provided by the investor row, or inherited one-way by a parent row from a controlled subsidiary / operating unit.

Parent attribution for `algorithm_trading` is one-way only: a parent company can inherit a controlled subsidiary / operating unit's current algorithm-trading capability, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's algorithm-trading capability unless that row itself has the capability.

Hard negative rule: mark `algorithm_trading = no` when the only evidence is portfolio exposure, investment in a quant/HFT/bot company, market-maker status alone, proprietary-trading status alone, liquidity-provider language alone, "technology-driven trading firm" language alone, sophisticated trading-technology language alone, API/FIX/connectivity access, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing or execution algorithms alone, brokerage/prime-brokerage/execution-desk/liquidity-access products, secondary-market token holding, or founder/advisor/executive association. These do not become `algorithm_trading = yes` unless the same source explicitly states current algorithmic/quantitative/systematic/HFT/automated trading strategy or algorithm-trading service/agency capability for the investor row.

Historical algorithm-trading service does not qualify. If the entity is bankrupt, stopped, liquidated, the strategy/service/product is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `algorithm_trading = no`. Use the same evidence standard as `defi` and `otc_trading`: official sources and trusted third-party databases can support `algorithm_trading = yes`; local PitchBook input data alone, ordinary news, and social media cannot.

Mark `market_making = yes` only as a current operating-capability label, not an investment-exposure label. Use `yes` only when official sources or trusted third-party databases show that the investor itself currently provides market making or liquidity provision service using its own, proprietary, balance-sheet, or otherwise controlled capital/liquidity, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.

Market making can be crypto or traditional finance. Traditional designated market maker, ETF/options/equities/fixed-income/FX/commodities market making, official market maker, and designated liquidity provider roles can qualify only when the source shows the investor is currently acting as a liquidity provider / LP / market maker with capital at risk, not merely quoting, routing, matching, or accessing liquidity.

Parent attribution for `market_making` is one-way only: a parent company can inherit a controlled subsidiary / operating unit's current market-making capability, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's market-making capability unless that row itself has the capability.

OTC desk liquidity can support `market_making = yes` when the investor's own OTC desk currently provides bilateral/RFQ liquidity as a principal, market maker, or balance-sheet liquidity provider. Judge `otc_trading` separately.

AMM, DEX, and liquidity-pool operation do not qualify by themselves. Mark `market_making = yes` only if the investor itself provides assets/capital into the pool or market as an LP/market maker/designated liquidity provider. Creating, operating, managing, or governing an AMM/DEX/pool without providing liquidity capital is `market_making = no`.

Hard negative rule: mark `market_making = no` when the only evidence is portfolio exposure, investment in a market maker/liquidity provider, generic liquidity-provider language, "provides liquidity" marketing language, deep-liquidity language, liquidity access, connecting clients to liquidity providers, sourcing liquidity, providing quotes only, request-for-quote pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker/execution-desk status alone, proprietary-trading/HFT/quant-trading status alone, passive fund investment, passive LP allocation, client portfolio allocation, token/protocol liquidity support or ecosystem funding that is not the investor's own ongoing LP/market-maker role, third-party market-maker allocations, secondary-market token holding, or founder/advisor/executive association. These do not become `market_making = yes` unless the same source explicitly states current market-making or liquidity-provision service with the investor's controlled capital/liquidity role.

Historical market making does not qualify. If the entity is bankrupt, stopped, liquidated, the market-making service is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `market_making = no`. Use the same evidence standard as `defi`, `otc_trading`, and `algorithm_trading`: official sources and trusted third-party databases can support `market_making = yes`; local PitchBook input data alone, ordinary news, and social media cannot.

Mark `execution_services = yes` only as a current operating-capability label, not an investment-exposure label. Use `yes` only when official sources or trusted third-party databases show that the investor itself currently provides or operates trade execution, order placement, order handling, executable brokerage, execution venue, matching engine, exchange/CEX, ATS/MTF/ECN, agency execution, prime-brokerage execution, DMA/execution access with executable order entry, DEX, swap, perp DEX, AMM, or on-chain trading protocol capability, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.

Execution services can be crypto or traditional finance. Traditional brokerage execution, agency execution, prime-brokerage execution, executable DMA, exchange execution, ATS/MTF/ECN execution, and crypto CEX/DEX/swap/AMM/on-chain trading infrastructure can qualify only when the investor itself provides the transaction venue, matching/order handling, or actual trade/order execution path.

Parent attribution for `execution_services` is one-way only: a parent company can inherit a controlled subsidiary / operating unit's current execution capability, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's execution capability unless that row itself has the capability.

Exchange / trading venue / matching engine operation qualifies. CEX, traditional exchange, ATS, ECN, MTF, DEX, swap, perp DEX, AMM, and on-chain trading protocol operation qualify for `execution_services = yes` even if they do not qualify for `market_making`.

OTC desk does not automatically qualify. Mark `execution_services = yes` for OTC only when the source explicitly shows trade execution, order handling, brokerage, RFQ execution, or comparable executable transaction service; otherwise judge only `otc_trading`.

Broker service qualifies only when it can actually place, handle, route-to-execution, or execute client/user orders. Custody, financing, settlement, clearing, reporting, post-trade support, market data, analytics, portfolio management, and custody-only prime services do not qualify.

Hard negative rule: mark `execution_services = no` when the only evidence is portfolio exposure, investment in a broker/exchange/DEX/execution platform, API/FIX/connectivity access alone, routing or smart order routing alone, liquidity access alone, liquidity aggregation alone, connecting users to third-party venues/counterparties/liquidity providers, wallet connection to an external DEX/venue, white-label or embedded third-party execution, redirect-to-external-venue trading, wallet/portfolio/analytics app with view-only or external-link trading, custody/settlement/clearing/post-trade-only service, market-making status alone, OTC desk status alone, exchange listing, maker/taker fee schedule, secondary-market token holding, or founder/advisor/executive association. These do not become `execution_services = yes` unless the same source explicitly states that the investor itself controls/provides actual order placement, order handling, broker service, matching/venue operation, swap/trade operation, or trade execution capability.

Historical execution service does not qualify. If the entity is bankrupt, stopped, liquidated, the execution service/product/venue/protocol is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `execution_services = no`. Use the same evidence standard as `defi`, `otc_trading`, `algorithm_trading`, and `market_making`: official sources and trusted third-party databases can support `execution_services = yes`; local PitchBook input data alone, ordinary news, and social media cannot.

Mark `defi = yes` as a current DeFi trading / DeFi protocol operation label. The core question is whether the investor currently does DeFi trading or DeFi operations, not whether it merely has investment exposure to DeFi companies.

Use `defi = yes` when official sources or trusted third-party databases show, as of the agent search time, any of these:
- the investor itself currently operates a DeFi protocol, product, venue, or service such as a DEX, AMM, swap, lending/borrowing/credit protocol, vault/yield protocol, liquid-staking/restaking protocol, perp DEX, derivatives/options protocol, prediction market, DeFi liquidity-management protocol, or comparable on-chain financial protocol;
- the investor itself currently trades through DeFi protocols, including DEX/AMM/swap trading, perp/derivatives/options protocol trading, on-chain RFQ/intent trading, lending/borrowing/credit use, DeFi leverage/collateral activity, vault/yield farming, liquid staking/restaking, LP capital deployment, DeFi market making/liquidity provision, on-chain arbitrage, MEV, liquidations, or comparable on-chain DeFi strategy;
- the investor is a fund vehicle, asset manager, hedge fund, trading firm, DAO/treasury, or operating company whose current strategy or managed assets are explicitly described as doing DeFi trading, on-chain trading, DeFi yield strategy, DeFi liquidity provision, DeFi arbitrage/MEV/liquidation, or other DeFi protocol-use activity;
- the investor is a parent/mother entity and a controlled subsidiary, controlled operating unit, controlled fund vehicle, or controlled trading/investment arm currently does DeFi trading or DeFi protocol operation. Attribution is one-way only: a child, venture arm, fund, or individual row does not inherit the parent company's DeFi activity unless that row itself has current DeFi trading/operation evidence.

DeFi market making, DEX/AMM LP activity, DeFi liquidity-provider roles, yield farming, liquid staking/restaking, on-chain arbitrage, MEV, and liquidations count as DeFi operations when the source ties the activity to the investor's own or managed capital/strategy.

Operating a DeFi protocol counts as `defi = yes` even when there is no evidence that the investor uses its own capital to trade on the protocol. Operating DeFi-adjacent infrastructure alone does not count unless it is itself a DeFi financial protocol or the investor also has DeFi trading/protocol-use evidence.

Oracle, bridge, cross-chain messaging, L1/L2, wallet, custody, validator/staking infrastructure, generic MEV infrastructure, RWA infrastructure, and other DeFi-adjacent infrastructure do not support `defi = yes` merely because the investor invests in or operates them. They support `defi = yes` only when the investor uses them for DeFi trading/protocol activity or operates a DeFi financial protocol built around trading, lending, staking/restaking, yield, liquidity, derivatives, or comparable on-chain financial activity.

Token investment, SAFT, treasury round participation, grant, accelerator support, ecosystem funding, and portfolio/backer exposure to a DeFi company do not by themselves support `defi = yes`. They can support `defi = yes` only when the same current official/trusted evidence also shows that the investor itself, its managed fund vehicle, or a controlled child is doing DeFi trading, deploying liquidity/yield/staking/restaking capital, or operating a DeFi protocol.

Use current official pages, official filings, official docs, fund strategy pages, protocol/team pages, treasury/governance pages, and trusted databases such as RootData, Crunchbase, CB Insights, CoinCarp, AngelList, and similar investment databases. Do not use local PitchBook input data alone as `defi = yes` evidence. Do not rely on ordinary news or social media alone.

Mark `defi = no` when the only evidence is a crypto/Web3/blockchain name, thesis, vertical, or fund strategy; DeFi company portfolio exposure; token investment/SAFT/grant/accelerator/ecosystem support without DeFi trading/protocol-use evidence; secondary-market token holding; DeFi-adjacent infrastructure investment/operation without DeFi financial protocol operation; CEX/broker/customer DeFi access where customers trade but the investor does not use its own/managed capital; founder/advisor/executive employment or token ownership without disclosed DeFi trading/operation; historical DeFi activity that has stopped, wound down, pivoted away, or gone bankrupt; or an unrelated affiliate relationship. For individuals, require explicit personal DeFi trading/protocol-operation evidence, not only founder/advisor/executive/investor status.

Mark `sub_fund = yes` only as a current structure / attribution label, not an operating-capability label. Judge it from the current investor row as the parent/mother entity: use `yes` only when official sources or trusted third-party databases show that the current investor currently owns, controls, contains, or has under it a sub-fund, fund vehicle, venture arm, investment arm, crypto arm, dedicated capital pool, dedicated investment/trading branch, or comparable sub-fund-like structure.

Traditional sub-fund structures can support `sub_fund = yes` only when they are current structures under the current investor as parent/mother entity. These include sub-fund, feeder fund, master-feeder, umbrella fund compartment, parallel fund, SPV, segregated portfolio, protected cell, fund platform, and fund-of-funds vehicle.

Broad operating-company / proprietary-trading / CVC structures can support `sub_fund = yes` only when they are current structures under the current investor as parent/mother entity. Venture arms, investment arms, crypto arms, proprietary-capital investment arms, balance-sheet venture arms, dedicated strategy divisions, and specialized internal capital pools qualify when sources show the relationship and the dedicated investment/trading/capital mandate.

Hard negative rule: mark `sub_fund = no` when the only evidence is that the row itself appears to be a fund vehicle, feeder, SPV, protected cell, venture arm, investment arm, crypto arm, subsidiary, brand, business unit, accelerator, incubator, ecosystem program, portfolio company, ordinary CVC type, externally managed fund, generic fund manager, ordinary closed fund, `LastClosedFundName`, `PrimaryInvestorType`, or name terms such as Ventures, Capital, Labs, Crypto Fund, Fund I, or SPV. These do not become `sub_fund = yes` unless the current investor row is the parent/mother entity that currently has the child fund/vehicle/arm, or the row itself also has its own current child sub-fund-like structure.

A manager row is `sub_fund = no` when the only evidence is that it manages funds for others. A parent / holding / umbrella / platform / company row can be `sub_fund = yes` when it currently has sub-funds, fund vehicles, venture arms, investment arms, or comparable child structures under it.

Historical sub-fund structures do not qualify. If the child fund/vehicle/arm is liquidated, wound down, closed, no longer investing, discontinued, or only supported by stale evidence with no current official/trusted confirmation, mark `sub_fund = no`. Use the same evidence standard as the other labels: official sources and trusted third-party databases can support `sub_fund = yes`; local PitchBook input data alone, ordinary news, and social media cannot.

Audit-driven boundary checks:
- OTC desks, OTC portals, centralized RFQ/block-trading flows, off-exchange trading, bilateral trading, or bilateral liquidity can support `otc_trading` when the entity itself, or a controlled child inherited by a parent row, currently provides the OTC service. Do not automatically infer `execution_services`; judge execution separately from explicit order placement, order handling, executable brokerage, RFQ execution, trade execution, matching/venue operation, or comparable executable transaction evidence.
- Algorithmic, quantitative, systematic, HFT/high-frequency, low-latency trading-engine, automated trading-strategy, or investor-operated/provided trading-bot / grid-bot / AI-bot evidence can support `algorithm_trading` only when it shows current operating capability for the investor row or one-way parent attribution from a controlled subsidiary / operating unit. Hard negative rule: do not infer `algorithm_trading` from market-maker status, proprietary-trading status, liquidity-provider language, "technology-driven trading firm" language, API/FIX/connectivity, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing/execution algorithms alone, brokerage/prime-brokerage/execution desks, or liquidity-access products. Judge `execution_services` separately under the execution rules above.
- Market-making, official market-maker, designated liquidity-provider, LP, principal liquidity, balance-sheet liquidity, or OTC bilateral/RFQ liquidity evidence can support `market_making` only when it shows the investor itself currently provides capital/liquidity as a market maker or LP, or when one-way parent attribution applies. Hard negative rule: do not infer `market_making` from generic liquidity-provider/deep-liquidity language, liquidity access, quotes/pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker status, proprietary-trading/HFT/quant status, AMM/DEX/pool operation without LP capital, protocol/token liquidity support that is not the investor's own ongoing LP/market-maker role, or third-party market-maker allocations.
- Execution services require current actual transaction capability: order placement, order handling, executable broker service, trade execution, matching engine, trading venue, exchange/CEX, ATS/MTF/ECN, DEX, swap, perp DEX, AMM, or on-chain trading protocol operation. Hard negative rule: do not infer `execution_services` from routing/smart routing alone, API/FIX/connectivity alone, liquidity access/aggregation alone, connecting to third-party liquidity/venues, external wallet-to-DEX links, custody/settlement/clearing/post-trade-only services, market making alone, OTC desk alone, or view-only wallet/portfolio/analytics tools.
- DEX, AMM, swap, liquidity-pool, or protocol trading infrastructure can support `execution_services` when the investor itself operates the trading/swap/venue/protocol function. For `defi`, require current DeFi trading, DeFi LP/yield/staking/restaking, on-chain arbitrage/MEV/liquidation, DeFi market-making/liquidity provision, managed DeFi strategy, or DeFi protocol operation under the DeFi rules above.
- `sub_fund` requires evidence that the current investor row is the parent/mother entity that currently has the child structure. Current child sub-funds, feeder/master-feeder/umbrella compartments, protected cells, segregated portfolios, parallel funds, SPVs, fund platforms, fund-of-funds vehicles, venture arms, investment arms, crypto arms, dedicated strategy divisions, or specialized internal capital pools can support `sub_fund` when the parent/child relationship is explicit.
- Hard negative rule: do not infer `sub_fund` because the row itself is a fund vehicle, feeder, SPV, protected cell, venture arm, investment arm, crypto arm, subsidiary, brand, ordinary business unit, accelerator, incubator, ecosystem program, portfolio company, ordinary CVC type, externally managed vehicle, generic fund manager, ordinary closed fund, `LastClosedFundName`, `PrimaryInvestorType`, or name terms such as Ventures, Capital, Labs, Crypto Fund, Fund I, or SPV. Do not use specific sample entities as hard positives; apply only the parent/mother-entity rule and source-backed relationship rule.
- For founders, individuals, parent/group entities, controlled affiliates, and branded operating platforms, accept attribution only when the source clearly ties the capability to the investor row through ownership, control, executive role, or brand/platform identity. If attribution is plausible but uncertain, set `needs_manual_review = yes`.
- Exclude portfolio-company-only evidence, generic crypto exposure, exchange listings, maker/taker fees, third-party market-making allocations, and educational content unless they clearly describe the investor's own operating capability. For `defi`, portfolio/investment/support exposure alone is not enough; require current DeFi trading, DeFi protocol-use, managed DeFi strategy, liquidity/yield/staking/restaking deployment, on-chain arbitrage/MEV/liquidation, or DeFi protocol operation under the DeFi rules above.

## Output Schemas

Classifier CSV header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,risk_flags,classifier_reason
```

Result CSV header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,capability_search_reason,status,completed_at,capability_labels,otc_trading,algorithm_trading,market_making,execution_services,defi,sub_fund,other_flags,evidence_urls,evidence_source_types,evidence_summary,confidence,needs_manual_review
```

Rules:
- `risk_flags`, `other_flags`, and `capability_labels` must be JSON list strings
- `capability_labels` must exactly equal the list of capability columns whose value is `yes`
- any `search_tier = skip_candidate` row must have `capability_search_required = no`, all six capability columns set to `no`, `capability_labels = []`, and both likelihood columns set to `none` or `low`
- `status` should be `completed`
- `completed_at` must be a literal ISO-8601 timestamp; never write shell syntax such as `$(date -u ...)`
- `evidence_urls` should use `|`-separated absolute HTTP(S) URLs
- `evidence_source_types` should use `|`-separated lowercase source labels such as `official_site`, `official_docs`, `official_filing`, `official_blog_or_press`, `trusted_database`, `secondary_profile`, `ordinary_news_context`, or `local_csv`. Do not use `ordinary_news_context` or `local_csv` as direct `yes` support.
- `evidence_urls` and `evidence_source_types` are pipe-list fields, not JSON-list fields; for no-search skip rows leave them blank instead of writing `[]`
- `evidence_summary` must be non-empty for every result row. For `skip_candidate`, summarize the probes/checks and why they support all six capability flags = `no`.
- `confidence` must be `high`, `medium`, or `low`
