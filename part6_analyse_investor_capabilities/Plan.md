# Part6: Investor Capability Harness Plan

## Goal

Input:
- `part5_to_part6/output/part6_batches/batch_*.jsonl`

Source lineage:
- Part5 identifies token-bearing companies from `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`.
- `part5_to_part6/scripts/1_build_part6_investor_input.py` expands those companies into related investors through PitchBook investor/deal/fund relationships.
- `part5_to_part6/output/part6_batches/` is the canonical Part6 task input. Each JSONL row contains immutable task identity fields and a Part6-shaped `input_row`.

Authoritative outputs:
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/classifier_results.csv`
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/results.csv`
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/needs_manual_review.csv`
- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/checkpoint.json`

The task is to classify each investor for these capability labels:
- `otc_trading`
- `algorithm_trading`
- `market_making`
- `execution_services`
- `defi`
- `sub_fund`

The harness may also record supplemental `other_flags`, but the six labels above are the required core outputs.

## Architecture

The harness uses a queue-only control plane:
1. consume fixed-size JSONL batches from `part5_to_part6/output/part6_batches/`
2. prepare isolated worker run directories from those batch files
3. run a classifier/router pass for every investor
4. write classifier decisions to `classifier_results.csv`
5. route each investor to `full`, `light`, or `skip_candidate`
6. run investor capability search workers
7. run verifier review for completed queue groups
8. merge verified clean rows into the global final outputs
9. regenerate `needs_manual_review.csv`
10. update checkpoint

Recommended defaults:
- `batch_size = 30`
- `workers = 8`
- `scheduler_mode = queue_only`
- worker/verifier model is fixed to `gpt-5.5`
- reasoning effort is fixed to `xhigh`

Do not use round-mode scheduling for Part6. `round_index` may still appear in schedule and verifier filenames as a queue-group identifier, but it is not a progress metric and must not be reported as current progress.

Capability drift guard:
- The current definitions in this `Plan.md`, `agent_prompt_template.md`, and generated worker/verifier instructions are authoritative.
- Workers and verifiers must not copy labels or boundaries from older `results.csv`, audit reports, repair files, or memory from previous runs.
- When old outputs conflict with current definitions, follow the current definitions and record the reason in `evidence_summary` or verifier feedback.

## Input Contract

Required extracted fields:
- `task_index`
- `InvestorID`
- `InvestorName`
- `InvestorAlsoKnownAs`
- `InvestorFormerName`
- `InvestorLegalName`
- `Website`
- `normalized_domain`
- `ParentCompany`
- `Exchange`
- `Ticker`
- `HQLocation`
- `HQCountry`
- `PrimaryInvestorType`
- `OtherInvestorTypes`
- `PreferredInvestmentTypes`
- `PreferredVerticals`
- `OtherInvestmentPreferences`
- `LastClosedFundName`
- `LastClosedFundType`
- `Description`
- `MatchedKeywords`
- `MatchedColumns`
- `InvestorCapabilityContext`
- `SearchPolicy`
- `AgentTaskScope`

Text limits:
- `Description`: max 700 chars
- `InvestorCapabilityContext`: max 400 chars

## Stage 1: Classifier / Router

`classifier_results.csv` header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,risk_flags,classifier_reason
```

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

Routing rules:
- `full`
  - explicit OTC / market making / trading / liquidity / execution / brokerage / quant / DeFi / protocol / exchange / fund-vehicle signals
  - operating-company-like descriptions under investor entities
- `light`
  - crypto investor but mostly investment preference signal
  - ambiguous crypto-native positioning that still deserves bounded confirmation
- `skip_candidate`
  - only for rows that are clearly and completely unrelated to crypto/Web3, financial services, investing/funds, trading/execution/liquidity, DeFi, and parent/sub-fund structure after local context review
  - do not use for weak crypto keyword inclusion; weak crypto/Web3/fintech/investor signals still require at least `light` search

Conservative rule:
- if uncertain between `skip_candidate` and `light`, use `light`
- `skip_candidate` is a narrow exception. The default for any potentially relevant row is `light` or `full`, because agent search is required unless the row is clearly unrelated.
- `skip_candidate` rows must use `none` or `low` for both `crypto_native_likelihood` and `operating_capability_likelihood`; if either likelihood is `high`, `medium`, or `unclear`, route the row to `light` or `full` instead
- do not use `skip_candidate` when the row, local input fields, website/domain, aliases, parent, description, preferred verticals, matched keywords/context, related official docs, exact-domain probes, official portfolio/backer pages, or trusted third-party databases show any possible crypto/Web3/blockchain/digital-asset/token/DAO/NFT/metaverse/gaming-in-Web3, fintech/financial-services/payments/banking/insurance/capital-markets, investor/fund/VC/PE/asset-manager/family-office/angel/accelerator/incubator/corporate-venture, exchange, OTC, DEX, AMM, liquidity, market-making, routing, brokerage, quant, systematic trading, DeFi protocol operation, DeFi trading, DeFi LP/yield/staking/restaking activity, on-chain arbitrage/MEV/liquidation strategy, feeder, umbrella, SPV, protected cell, parallel fund, fund-of-funds, proprietary-capital investment arm, balance-sheet venture arm, corporate venture arm, or dedicated parent-company crypto/Web3 investment branch signal
- before assigning `skip_candidate`, document why the row is completely unrelated. If that statement would be weak or based on missing evidence, route to `light`.

## Stage 2: Result Schema

`results.csv` header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,capability_search_reason,status,completed_at,capability_labels,otc_trading,algorithm_trading,market_making,execution_services,defi,sub_fund,other_flags,evidence_urls,evidence_source_types,evidence_summary,confidence,needs_manual_review
```

Rules:
- one row per investor
- copy `task_index`, `investor_id`, `investor_name`, `normalized_domain`, and `primary_investor_type` exactly from the top-level task fields; do not infer or replace input metadata
- the six capability columns must be `yes` or `no`
- `capability_labels` must be the JSON list of every capability column set to `yes`
- `other_flags` must be a JSON list string
- `completed_at` must be a literal ISO-8601 timestamp; never write shell syntax such as `$(date -u ...)`
- `evidence_urls` must be non-empty for searched rows
- `evidence_source_types` must be non-empty for searched rows
- `evidence_urls` and `evidence_source_types` are pipe-list fields, not JSON-list fields; for no-search skip rows leave them blank instead of writing `[]`
- `evidence_source_types` should use lowercase labels such as `official_site`, `official_docs`, `official_filing`, `official_blog_or_press`, `trusted_database`, `secondary_profile`, `ordinary_news_context`, or `local_csv`. Do not use `ordinary_news_context` or `local_csv` as direct `yes` support.
- `evidence_summary` must be non-empty for every result row. For `skip_candidate`, summarize the exact-name/domain probes or local-context checks and why they support all six capability flags = `no`.
- `confidence` must be `high`, `medium`, or `low`

Capability interpretation rules:
- Global source hierarchy: current official source wins over current official portfolio/backer pages, which win over trusted third-party databases, which win over stale databases, ordinary news, social media, and local PitchBook input. If a current official source conflicts with a trusted database, prefer the official source. Use ordinary news, social media, and local PitchBook only as search/disambiguation context, not as direct `yes` evidence.
- Current evidence means the capability, holding, child structure, service, product, venue, protocol, or portfolio/support relationship is still shown in current official pages, current official documents, current official portfolio/backer pages, current official product/service pages, current official filings, or current trusted third-party database profiles. Archive pages, old announcements, stale database entries, removed official pages, discontinued products, bankrupt/liquidated entities, wound-down funds, stopped protocols, or unconfirmed historical mentions do not support `yes`.
- Controlled attribution means the investor row is the parent/mother entity and the source shows a wholly owned subsidiary, controlled subsidiary, controlled operating division, controlled business unit, controlled brand/platform, or official group entity. Do not treat portfolio companies, minority investments, LP investments, partners, ecosystem members, unaffiliated affiliates, ordinary clients, or service providers as controlled subsidiaries/operating units.
- For all non-`defi` labels, portfolio-company-only evidence, investee product features, generic crypto exposure, educational content, third-party allocations, and associated-person employment/founder/advisor links do not support `yes` unless the source clearly attributes current operating control or service operation to the investor row.
- Set `needs_manual_review = yes` after one extra disambiguation pass when entity identity, current status, parent/control relationship, official-vs-database conflict, self-operated-vs-third-party service, or source attribution remains unclear. Do not force a `yes` from ambiguous evidence.
- `otc_trading = yes` is a current operating-capability label, not an investment-exposure label. Mark it only when official sources or trusted third-party databases show that the investor itself currently provides OTC trading service, or when the investor is a parent company and a controlled subsidiary, venture arm, or operating unit currently provides OTC trading service.
- OTC trading includes OTC desk, OTC trading, over-the-counter trading, block trading, off-exchange trading, bilateral trading, bilateral liquidity, institutional OTC, dealer-to-client OTC, and centralized dealer/broker/counterparty RFQ. Both crypto/digital-asset OTC and traditional finance OTC can qualify, including OTC equities / OTC Markets securities trading, OTC derivatives, FX OTC, fixed-income OTC, commodities OTC, bilateral options, and swaps, when the investor itself currently provides that service.
- Parent attribution for OTC is one-way only: a parent company can inherit a controlled subsidiary / venture arm / operating unit's current OTC service, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's OTC service unless that row itself provides OTC service.
- Do not mark `otc_trading = yes` from portfolio exposure, investment in an OTC company, broker-dealer status alone, market-maker status alone, inter-dealer participant status alone, liquidity-provider language alone, deep-liquidity language alone, OTC access/connection to third-party counterparties, OTC settlement/custody/post-trade support, DEX RFQ, intent/on-chain RFQ, on-chain block trade, secondary-market token holding, or founder/advisor/executive association.
- Historical OTC service does not qualify. If the entity is bankrupt, stopped, liquidated, the OTC product/service is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `otc_trading = no`.
- Use the same evidence standard as `defi`: official sources and trusted third-party databases can support `otc_trading = yes`; local PitchBook input data alone, ordinary news, and social media cannot.
- `algorithm_trading = yes` is a current operating-capability label, not an investment-exposure label. Mark it only when official sources or trusted third-party databases show that the investor itself currently uses, provides, or operates algorithmic, quantitative, systematic, HFT/high-frequency, low-latency trading-engine, automated trading-strategy, or algorithm-trading service/agency capability, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.
- Algorithm trading can be crypto or traditional finance. Traditional quant trading, systematic trading, HFT, low-latency trading engines, and current trading-bot / grid-bot / AI-bot strategies can qualify when they are explicitly operated or provided by the investor row, or inherited one-way by a parent row from a controlled subsidiary / operating unit.
- Parent attribution for `algorithm_trading` is one-way only: a parent company can inherit a controlled subsidiary / operating unit's current algorithm-trading capability, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's algorithm-trading capability unless that row itself has the capability.
- Do not mark `algorithm_trading = yes` from portfolio exposure, investment in a quant/HFT/bot company, market-maker status alone, proprietary-trading status alone, liquidity-provider language alone, "technology-driven trading firm" language alone, sophisticated trading-technology language alone, API/FIX/connectivity access, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing or execution algorithms alone, brokerage/prime-brokerage/execution-desk/liquidity-access products, secondary-market token holding, or founder/advisor/executive association. These are hard negatives unless the same source explicitly states current algorithmic/quantitative/systematic/HFT/automated trading strategy or algorithm-trading service/agency capability for the investor row.
- Historical algorithm-trading service does not qualify. If the entity is bankrupt, stopped, liquidated, the strategy/service/product is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `algorithm_trading = no`.
- Use the same evidence standard as `defi` and `otc_trading`: official sources and trusted third-party databases can support `algorithm_trading = yes`; local PitchBook input data alone, ordinary news, and social media cannot.
- `market_making = yes` is a current operating-capability label, not an investment-exposure label. Mark it only when official sources or trusted third-party databases show that the investor itself currently provides market making or liquidity provision service using its own, proprietary, balance-sheet, or otherwise controlled capital/liquidity, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.
- Market making can be crypto or traditional finance. Traditional designated market maker, ETF/options/equities/fixed-income/FX/commodities market making, official market maker, and designated liquidity provider roles can qualify when the source shows the investor is currently acting as a liquidity provider / LP / market maker with capital at risk, not merely quoting, routing, matching, or accessing liquidity.
- Parent attribution for `market_making` is one-way only: a parent company can inherit a controlled subsidiary / operating unit's current market-making capability, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's market-making capability unless that row itself has the capability.
- OTC desk liquidity can support `market_making = yes` when the investor's own OTC desk currently provides bilateral/RFQ liquidity as a principal, market maker, or balance-sheet liquidity provider. Judge `otc_trading` separately.
- AMM, DEX, and liquidity-pool operation do not qualify by themselves. Mark `market_making = yes` only if the investor itself provides assets/capital into the pool or market as an LP/market maker/designated liquidity provider. Creating, operating, managing, or governing an AMM/DEX/pool without providing liquidity capital is `market_making = no`.
- Do not mark `market_making = yes` from portfolio exposure, investment in a market maker/liquidity provider, generic liquidity-provider language, "provides liquidity" marketing language, deep-liquidity language, liquidity access, connecting clients to liquidity providers, sourcing liquidity, providing quotes only, request-for-quote pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker/execution-desk status alone, proprietary-trading/HFT/quant-trading status alone, passive fund investment, passive LP allocation, client portfolio allocation, token/protocol liquidity support or ecosystem funding that is not the investor's own ongoing LP/market-maker role, third-party market-maker allocations, secondary-market token holding, or founder/advisor/executive association. These are hard negatives unless the same source explicitly states current market-making or liquidity-provision service with the investor's controlled capital/liquidity role.
- Historical market making does not qualify. If the entity is bankrupt, stopped, liquidated, the market-making service is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `market_making = no`.
- Use the same evidence standard as `defi`, `otc_trading`, and `algorithm_trading`: official sources and trusted third-party databases can support `market_making = yes`; local PitchBook input data alone, ordinary news, and social media cannot.
- `execution_services = yes` is a current operating-capability label, not an investment-exposure label. Mark it only when official sources or trusted third-party databases show that the investor itself currently provides or operates trade execution, order placement, order handling, executable brokerage, execution venue, matching engine, exchange/CEX, ATS/MTF/ECN, agency execution, prime-brokerage execution, DMA/execution access with executable order entry, DEX, swap, perp DEX, AMM, or on-chain trading protocol capability, or when the investor is a parent company and a controlled subsidiary or operating unit currently has that capability.
- Execution services can be crypto or traditional finance. Traditional brokerage execution, agency execution, prime-brokerage execution, executable DMA, exchange execution, ATS/MTF/ECN execution, and crypto CEX/DEX/swap/AMM/on-chain trading infrastructure can qualify when the investor itself provides the transaction venue, matching/order handling, or actual trade/order execution path.
- Parent attribution for `execution_services` is one-way only: a parent company can inherit a controlled subsidiary / operating unit's current execution capability, but a subsidiary, venture arm, fund, or individual row does not inherit the parent company's execution capability unless that row itself has the capability.
- Exchange / trading venue / matching engine operation qualifies. CEX, traditional exchange, ATS, ECN, MTF, DEX, swap, perp DEX, AMM, and on-chain trading protocol operation qualify for `execution_services = yes` even if they do not qualify for `market_making`.
- OTC desk does not automatically qualify. Mark `execution_services = yes` for OTC only when the source explicitly shows trade execution, order handling, brokerage, RFQ execution, or comparable executable transaction service; otherwise judge only `otc_trading`.
- Broker service qualifies only when it can actually place, handle, route-to-execution, or execute client/user orders. Custody, financing, settlement, clearing, reporting, post-trade support, market data, analytics, portfolio management, and custody-only prime services do not qualify.
- Do not mark `execution_services = yes` from portfolio exposure, investment in a broker/exchange/DEX/execution platform, API/FIX/connectivity access alone, routing or smart order routing alone, liquidity access alone, liquidity aggregation alone, connecting users to third-party venues/counterparties/liquidity providers, wallet connection to an external DEX/venue, white-label or embedded third-party execution, redirect-to-external-venue trading, wallet/portfolio/analytics app with view-only or external-link trading, custody/settlement/clearing/post-trade-only service, market-making status alone, OTC desk status alone, exchange listing, maker/taker fee schedule, secondary-market token holding, or founder/advisor/executive association. These are hard negatives unless the same source explicitly states that the investor itself controls/provides actual order placement, order handling, broker service, matching/venue operation, swap/trade operation, or trade execution capability.
- Historical execution service does not qualify. If the entity is bankrupt, stopped, liquidated, the execution service/product/venue/protocol is discontinued, the official service page is gone, or only stale database evidence remains with no current official/trusted confirmation, mark `execution_services = no`.
- Use the same evidence standard as `defi`, `otc_trading`, `algorithm_trading`, and `market_making`: official sources and trusted third-party databases can support `execution_services = yes`; local PitchBook input data alone, ordinary news, and social media cannot.
- `defi = yes` is a current DeFi trading / DeFi protocol operation label. The core question is whether the investor currently does DeFi trading or DeFi operations, not whether it merely has investment exposure to DeFi companies.
- Mark `defi = yes` when official sources or trusted third-party databases show, as of the agent search time, at least one of these conditions:
  - the investor itself currently operates a DeFi protocol, product, venue, or service such as a DEX, AMM, swap, lending/borrowing/credit protocol, vault/yield protocol, liquid-staking/restaking protocol, perp DEX, derivatives/options protocol, prediction market, DeFi liquidity-management protocol, or comparable on-chain financial protocol;
  - the investor itself currently trades through DeFi protocols, including DEX/AMM/swap trading, perp/derivatives/options protocol trading, on-chain RFQ/intent trading, lending/borrowing/credit use, DeFi leverage/collateral activity, vault/yield farming, liquid staking/restaking, LP capital deployment, DeFi market making/liquidity provision, on-chain arbitrage, MEV, liquidations, or comparable on-chain DeFi strategy;
  - the investor is a fund vehicle, asset manager, hedge fund, trading firm, DAO/treasury, or operating company whose current strategy or managed assets are explicitly described as doing DeFi trading, on-chain trading, DeFi yield strategy, DeFi liquidity provision, DeFi arbitrage/MEV/liquidation, or other DeFi protocol-use activity;
  - the investor is a parent/mother entity and a controlled subsidiary, controlled operating unit, controlled fund vehicle, or controlled trading/investment arm currently does DeFi trading or DeFi protocol operation. Attribution is one-way only: a child, venture arm, fund, or individual row does not inherit the parent company's DeFi activity unless that row itself has current DeFi trading/operation evidence.
- DeFi market making, DEX/AMM LP activity, DeFi liquidity-provider roles, yield farming, liquid staking/restaking, on-chain arbitrage, MEV, and liquidations count as DeFi operations when the source ties the activity to the investor's own or managed capital/strategy.
- Operating a DeFi protocol counts as `defi = yes` even when there is no evidence that the investor uses its own capital to trade on the protocol. Operating DeFi-adjacent infrastructure alone does not count unless it is itself a DeFi financial protocol or the investor also has DeFi trading/protocol-use evidence.
- Oracle, bridge, cross-chain messaging, L1/L2, wallet, custody, validator/staking infrastructure, generic MEV infrastructure, RWA infrastructure, and other DeFi-adjacent infrastructure do not support `defi = yes` merely because the investor invests in or operates them. They support `defi = yes` only when the investor uses them for DeFi trading/protocol activity or operates a DeFi financial protocol built around trading, lending, staking/restaking, yield, liquidity, derivatives, or comparable on-chain financial activity.
- Token investment, SAFT, treasury round participation, grant, accelerator support, ecosystem funding, and portfolio/backer exposure to a DeFi company do not by themselves support `defi = yes`. They can support `defi = yes` only when the same current official/trusted evidence also shows that the investor itself, its managed fund vehicle, or a controlled child is doing DeFi trading, deploying liquidity/yield/staking/restaking capital, or operating a DeFi protocol.
- Official sources include investor strategy/product/service pages, fund strategy pages, official filings, official docs, protocol/team pages, treasury/governance pages, and official announcements that describe current DeFi trading or DeFi protocol operation. Trusted third-party databases can support `defi = yes` only when they explicitly describe current DeFi trading/protocol-use/operation, not merely DeFi-sector investments. Do not use local PitchBook input data by itself as `defi = yes` evidence, and do not rely on ordinary news or social media alone when official/trusted-database evidence is unavailable.
- Mark `defi = no` when the only evidence is a crypto/Web3/blockchain name, thesis, vertical, or fund strategy; DeFi company portfolio exposure; token investment/SAFT/grant/accelerator/ecosystem support without DeFi trading/protocol-use evidence; secondary-market token holding; DeFi-adjacent infrastructure investment/operation without DeFi financial protocol operation; CEX/broker/customer DeFi access where customers trade but the investor does not use its own/managed capital; founder/advisor/executive employment or token ownership without disclosed DeFi trading/operation; historical DeFi activity that has stopped, wound down, pivoted away, or gone bankrupt; or an unrelated/ungrounded affiliate relationship.
- For individual investors, require explicit evidence of personal DeFi trading, DeFi protocol operation, DeFi LP/yield/staking/restaking activity, on-chain arbitrage/MEV/liquidation, or comparable DeFi operation. Do not infer `defi = yes` merely from being a founder, advisor, executive, employee, token holder, or investor in a DeFi company.
- Set `needs_manual_review = yes` when entity identity, current DeFi trading/operation status, parent/control relationship, manager-vs-fund attribution, official-vs-database conflict, DeFi protocol vs DeFi-adjacent infrastructure classification, pivot/shutdown status, or investment-vs-protocol-use attribution is ambiguous after targeted search.
- `sub_fund = yes` is a current structure / attribution label, not an operating-capability label. Judge it from the current investor row as the parent/mother entity: mark `yes` only when official sources or trusted third-party databases show that the current investor currently owns, controls, contains, or has under it a sub-fund, fund vehicle, venture arm, investment arm, crypto arm, dedicated capital pool, dedicated investment/trading branch, or comparable sub-fund-like structure.
- Traditional sub-fund structures can support `sub_fund = yes` only when they are current structures under the current investor as parent/mother entity. These include sub-fund, feeder fund, master-feeder, umbrella fund compartment, parallel fund, SPV, segregated portfolio, protected cell, fund platform, and fund-of-funds vehicle.
- Broad operating-company / proprietary-trading / CVC structures can support `sub_fund = yes` only when they are current structures under the current investor as parent/mother entity. Venture arms, investment arms, crypto arms, proprietary-capital investment arms, balance-sheet venture arms, dedicated strategy divisions, and specialized internal capital pools qualify when sources show the relationship and the dedicated investment/trading/capital mandate.
- Do not mark `sub_fund = yes` merely because the row itself appears to be a fund vehicle, feeder, SPV, protected cell, venture arm, investment arm, crypto arm, subsidiary, brand, business unit, accelerator, incubator, ecosystem program, portfolio company, ordinary CVC type, or externally managed fund. The row must be the current parent/mother entity that has the child fund/vehicle/arm, unless the row itself also has its own current child sub-fund-like structure.
- A manager row is `sub_fund = no` when the only evidence is that it manages funds for others. A parent / holding / umbrella / platform / company row can be `sub_fund = yes` when it currently has sub-funds, fund vehicles, venture arms, investment arms, or comparable child structures under it.
- A normal closed fund, ordinary fund-manager status, `LastClosedFundName`, `PrimaryInvestorType`, or name terms such as Ventures, Capital, Labs, Crypto Fund, Fund I, or SPV are not enough for `sub_fund = yes`. Require source evidence of the current parent/sub-fund, parent/vehicle, or parent/investment-arm relationship.
- Historical sub-fund structures do not qualify. If the child fund/vehicle/arm is liquidated, wound down, closed, no longer investing, discontinued, or only supported by stale evidence with no current official/trusted confirmation, mark `sub_fund = no`.
- Use the same evidence standard as the other labels: official sources and trusted third-party databases can support `sub_fund = yes`; local PitchBook input data alone, ordinary news, and social media cannot.

Audit-driven boundary rules:
- An official OTC desk, block-trading desk, OTC portal, centralized RFQ flow, off-exchange trading, bilateral trading, or bilateral liquidity can support `otc_trading` when the entity itself, or a controlled child inherited by a parent row, currently provides the OTC service. Do not automatically infer `execution_services`; judge execution separately from explicit order placement, order handling, executable brokerage, RFQ execution, trade execution, matching/venue operation, or comparable executable transaction evidence.
- Algorithmic, quantitative, systematic, HFT/high-frequency, low-latency trading-engine, automated trading-strategy, or investor-operated/provided trading-bot / grid-bot / AI-bot evidence can support `algorithm_trading` only when it shows current operating capability for the investor row or one-way parent attribution from a controlled subsidiary / operating unit. Hard negative rule: do not infer `algorithm_trading` from market-maker status, proprietary-trading status, liquidity-provider language, "technology-driven trading firm" language, API/FIX/connectivity, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing/execution algorithms alone, brokerage/prime-brokerage/execution desks, or liquidity-access products. Judge `execution_services` separately under the execution rules above.
- Market-making, official market-maker, designated liquidity-provider, LP, principal liquidity, balance-sheet liquidity, or OTC bilateral/RFQ liquidity evidence can support `market_making` only when it shows the investor itself currently provides capital/liquidity as a market maker or LP, or when one-way parent attribution applies. Hard negative rule: do not infer `market_making` from generic liquidity-provider/deep-liquidity language, liquidity access, quotes/pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker status, proprietary-trading/HFT/quant status, AMM/DEX/pool operation without LP capital, protocol/token liquidity support that is not the investor's own ongoing LP/market-maker role, or third-party market-maker allocations.
- Execution services require current actual transaction capability: order placement, order handling, executable broker service, trade execution, matching engine, trading venue, exchange/CEX, ATS/MTF/ECN, DEX, swap, perp DEX, AMM, or on-chain trading protocol operation. Hard negative rule: do not infer `execution_services` from routing/smart routing alone, API/FIX/connectivity alone, liquidity access/aggregation alone, connecting to third-party liquidity/venues, external wallet-to-DEX links, custody/settlement/clearing/post-trade-only services, market making alone, OTC desk alone, or view-only wallet/portfolio/analytics tools.
- DEX, swap, AMM, liquidity-pool, or protocol-operated trading infrastructure can support `execution_services` when the investor itself operates the trading/swap/venue/protocol function. For `defi`, require current DeFi trading, DeFi LP/yield/staking/restaking, on-chain arbitrage/MEV/liquidation, DeFi market-making/liquidity provision, managed DeFi strategy, or DeFi protocol operation under the DeFi rules above.
- `sub_fund` requires evidence that the current investor row is the parent/mother entity that currently has the child structure. Current child sub-funds, feeder/master-feeder/umbrella compartments, protected cells, segregated portfolios, parallel funds, SPVs, fund platforms, fund-of-funds vehicles, venture arms, investment arms, crypto arms, dedicated strategy divisions, or specialized internal capital pools can support `sub_fund` when the parent/child relationship is explicit.
- Hard negative rule: do not infer `sub_fund` because the row itself is a fund vehicle, feeder, SPV, protected cell, venture arm, investment arm, crypto arm, subsidiary, brand, ordinary business unit, accelerator, incubator, ecosystem program, portfolio company, ordinary CVC type, externally managed vehicle, generic fund manager, ordinary closed fund, `LastClosedFundName`, `PrimaryInvestorType`, or name terms such as Ventures, Capital, Labs, Crypto Fund, Fund I, or SPV. Do not use specific sample entities as hard positives; apply only the parent/mother-entity rule and source-backed relationship rule.
- For associated people, founders, controlled affiliates, parent/group platforms, or branded operating platforms, mark a capability only when the source clearly attributes operating control, ownership, executive role, or brand/platform linkage to the investor row. If attribution is plausible but not clear, search once more and set `needs_manual_review = yes` if still ambiguous.
- Do not infer capabilities only from portfolio companies, investee product features, generic crypto exposure, exchange listings, maker/taker fee schedules, token allocations for third-party market makers, or educational content about a capability. For `defi`, portfolio/investment/support exposure alone is not enough; require current DeFi trading, DeFi protocol-use, managed DeFi strategy, liquidity/yield/staking/restaking deployment, on-chain arbitrage/MEV/liquidation, or DeFi protocol operation under the DeFi rules above.

## Verification

Verifier focus:
- global source and attribution failures: verify current official/trusted evidence, official-vs-database conflicts, stale/historical-only evidence, current status, controlled parent/subsidiary relationship, self-operated-vs-third-party services, and whether `needs_manual_review = yes` should be set instead of forcing a `yes`
- `otc_trading` false positives and false negatives under the current operating-capability standard: verify current direct OTC service, one-way parent inheritance from controlled subsidiaries/arms, and reject portfolio exposure, stale/historical OTC, liquidity-only language, broker-dealer/market-maker status alone, OTC access-only, settlement/custody-only, and on-chain RFQ/intent evidence
- `algorithm_trading` false positives and false negatives under the current operating-capability standard: verify current direct algorithmic/quantitative/systematic/HFT/automated trading capability, one-way parent inheritance from controlled subsidiaries/operating units, and reject portfolio exposure, stale/historical algorithm trading, market-maker status alone, proprietary-trading status alone, liquidity-provider language alone, "technology-driven trading firm" language alone, API/FIX/connectivity, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing/execution algorithms alone, and brokerage/execution/liquidity-access evidence that does not explicitly provide algorithm-trading service/agency capability
- `market_making` false positives and false negatives under the current operating-capability standard: verify current direct market-making or liquidity-provision service using the investor's own/controlled capital, one-way parent inheritance from controlled subsidiaries/operating units, official/designated market-maker or liquidity-provider roles, and OTC principal/balance-sheet liquidity. Reject portfolio exposure, stale/historical market making, generic liquidity-provider/deep-liquidity language, liquidity access, quotes/pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker status alone, proprietary-trading/HFT/quant status alone, passive fund investment, passive LP allocation, client portfolio allocation, AMM/DEX/pool operation without LP capital, protocol/token liquidity support that is not the investor's own ongoing LP/market-maker role, third-party market-maker allocations, and individual founder/advisor/executive association
- `execution_services` false positives and false negatives under the current operating-capability standard: verify current direct order placement, order handling, executable broker service, trade execution, matching engine, trading venue, exchange/CEX, ATS/MTF/ECN, DEX, swap, perp DEX, AMM, or on-chain trading protocol operation, plus one-way parent inheritance from controlled subsidiaries/operating units. Reject portfolio exposure, stale/historical execution, routing/smart routing alone, API/FIX/connectivity alone, liquidity access/aggregation alone, connecting to third-party liquidity/venues, white-label/embedded third-party execution, redirect-to-external-venue trading, wallet external-link trading, custody/settlement/clearing/post-trade-only services, market making alone, OTC desk alone, view-only wallet/portfolio/analytics tools, and individual founder/advisor/executive association
- `defi` false positives and false negatives under the current DeFi trading / DeFi protocol operation rules: verify current official/trusted-database evidence of DeFi trading, DeFi protocol-use, managed DeFi strategy, LP/yield/staking/restaking deployment, DeFi market-making/liquidity provision, on-chain arbitrage/MEV/liquidation, or DeFi protocol operation. Reject DeFi company portfolio exposure, token investment/SAFT/grants/accelerator/ecosystem support, DeFi-adjacent infrastructure exposure, CEX/broker customer DeFi access, unaffiliated affiliates, manager-only relationships without DeFi trading strategy evidence, uncontrolled funds, old news-only DeFi exposure, and stale/historical DeFi activity.
- `sub_fund` false positives and false negatives under the current parent/mother-entity structure standard: verify that the current investor row currently has a child sub-fund, fund vehicle, venture arm, investment arm, crypto arm, dedicated capital pool, or comparable sub-fund-like structure. Reject rows that are merely fund vehicles, feeders, SPVs, protected cells, venture arms, investment arms, crypto arms, subsidiaries, brands, accelerators/incubators, ecosystem programs, portfolio companies, externally managed vehicles, generic fund managers, ordinary closed funds, name-only matches, or stale/historical structures with no current official/trusted confirmation.
- skipped rows that should have been searched
- operating-company profiles incorrectly treated as pure VC/angel records

`verification_report.csv` header:

```csv
task_index,investor_id,investor_name,classifier_search_tier,worker_capability_labels,verifier_search_tier,verifier_capability_labels,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

## Long-Run Behavior

- use queue mode only; round-mode supervisor execution is disabled
- use `scripts/6_start_long_running_supervisor.py --foreground` inside screen/tmux, or run `scripts/5_run_queue_supervisor.py` directly
- use `scripts/7_check_longrun_status.py` as the canonical status entrypoint
- each status check must report heartbeat age, active workers, waiting/tail_retry/collect/deferred backlog counts, and current running batch row progress
- preserve the established two-stage long-tail handling:
  - first timeout parks the batch for one tail retry
  - second timeout becomes terminal `deferred_long_tail`
- completion requires a full gate before the supervisor writes `phase=completed`:
  - run full `scripts/3_collect_results.py --lint-only --repair-identity-drift-in-place --fail-on-identity-drift`
  - run `scripts/10_validate_final_outputs.py`
  - validate final row count against canonical input, currently 13,970 rows for the full Part5-to-Part6 batch set
  - validate task_index sequence, input order, classifier/results one-to-one alignment, no shell literals, no stale placeholders, and no deterministic skip-rule violations
