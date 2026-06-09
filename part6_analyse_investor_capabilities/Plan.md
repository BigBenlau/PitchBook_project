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

The harness follows the existing multi-round control-plane shape established in part5:
1. consume fixed-size JSONL batches from `part5_to_part6/output/part6_batches/`
2. prepare isolated worker run directories from those batch files
3. run a classifier/router pass for every investor
4. write classifier decisions to `classifier_results.csv`
5. route each investor to `full`, `light`, or `skip_candidate`
6. run investor capability search workers
7. run round-end verifier review
8. merge verified clean rows into the global final outputs
9. regenerate `needs_manual_review.csv`
10. update checkpoint

Recommended defaults:
- `batch_size = 30`
- `workers = 5`
- queue-mode is the default unattended long-run path

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
  - weak crypto keyword inclusion only, with no operating-capability signal

Conservative rule:
- if uncertain between `skip_candidate` and `light`, use `light`
- `skip_candidate` rows must use `none` or `low` for both `crypto_native_likelihood` and `operating_capability_likelihood`; if either likelihood is `high`, `medium`, or `unclear`, route the row to `light` or `full` instead
- do not use `skip_candidate` when the row, website, aliases, related official docs, exact-domain probes, official portfolio/backer pages, or trusted third-party databases show any exchange, OTC, DEX, AMM, liquidity, market-making, routing, brokerage, quant, systematic trading, DeFi product, current DeFi investment/backing/support, feeder, umbrella, SPV, protected cell, parallel fund, fund-of-funds, proprietary-capital investment arm, balance-sheet venture arm, corporate venture arm, or dedicated parent-company crypto/Web3 investment branch signal

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
- `defi = yes` is a current DeFi exposure / investment / support / operation label. It is broader than direct operating capability.
- Mark `defi = yes` when official sources or trusted third-party databases show, as of the agent search time, at least one of these conditions:
  - the investor itself operates a DeFi or DeFi-adjacent protocol, product, service, or infrastructure;
  - the investor currently invests in, backs, grants, incubates, accelerates, provides ecosystem funding to, provides liquidity support to, or otherwise supports a DeFi or DeFi-adjacent company/protocol;
  - a controlled venture arm, controlled investment arm, controlled fund vehicle, current official public portfolio, or source-attributed parent-controlled investment activity connected to the investor row currently has DeFi or DeFi-adjacent exposure;
  - the investor participated in a private token round, SAFT, treasury round, grant, accelerator program, ecosystem support program, or similar primary investment/support arrangement for a DeFi or DeFi-adjacent company/protocol.
- DeFi and DeFi-adjacent companies/protocols include DEX, AMM, swap, lending, borrowing, credit, vault, yield, liquid staking, restaking, oracle, bridge, cross-chain messaging, L1/L2, wallet, custody, staking infrastructure, MEV infrastructure, RWA, NFT finance, perp DEX, derivatives protocol, prediction market, intent/RFQ protocol, DeFi liquidity management, and on-chain execution infrastructure.
- Current DeFi exposure is established from current official pages or trusted databases when there is no clear exit, portfolio removal, fund wind-down, bankruptcy/liquidation, product stop, pivot away from DeFi, or public statement that the investor no longer holds/supports the DeFi asset. If an official current portfolio is complete and omits an older news-only investment, prefer the official portfolio and do not mark `defi = yes` from the old news alone.
- Official sources include investor portfolio/investment pages, portfolio-company investor/backer pages, official announcements/blogs/press releases, official filings, and protocol/foundation grant or ecosystem pages. Trusted third-party databases can include RootData, Crunchbase, CB Insights, CoinCarp, AngelList, and similar investment databases. Do not use local PitchBook input data by itself as `defi = yes` evidence, and do not rely on ordinary news or social media alone when official/trusted-database evidence is unavailable.
- Mark `defi = no` when the only evidence is a crypto/Web3/blockchain name, thesis, vertical, or fund strategy; a historical DeFi investment that has clearly exited, stopped, wound down, been removed, pivoted away, or gone bankrupt; a secondary-market token holding; founder/advisor/executive employment or token ownership without disclosed investment/backing; or an unrelated/ungrounded affiliate relationship.
- For individual investors, require a disclosed investment/backing/grant/portfolio relationship to a DeFi or DeFi-adjacent company/protocol. Do not infer `defi = yes` merely from being a founder, advisor, executive, employee, or token holder.
- Set `needs_manual_review = yes` when entity identity, current holding status, official-vs-database conflict, DeFi-company classification, pivot/shutdown status, or investment-vs-token-holding attribution is ambiguous after targeted search.
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
- DEX, swap, AMM, liquidity-pool, or protocol-operated trading infrastructure can support `execution_services` when the investor itself operates the trading/swap/venue/protocol function; any current investment/support/operation exposure to the DeFi and DeFi-adjacent categories listed above can support `defi`.
- `sub_fund` requires evidence that the current investor row is the parent/mother entity that currently has the child structure. Current child sub-funds, feeder/master-feeder/umbrella compartments, protected cells, segregated portfolios, parallel funds, SPVs, fund platforms, fund-of-funds vehicles, venture arms, investment arms, crypto arms, dedicated strategy divisions, or specialized internal capital pools can support `sub_fund` when the parent/child relationship is explicit.
- Hard negative rule: do not infer `sub_fund` because the row itself is a fund vehicle, feeder, SPV, protected cell, venture arm, investment arm, crypto arm, subsidiary, brand, ordinary business unit, accelerator, incubator, ecosystem program, portfolio company, ordinary CVC type, externally managed vehicle, generic fund manager, ordinary closed fund, `LastClosedFundName`, `PrimaryInvestorType`, or name terms such as Ventures, Capital, Labs, Crypto Fund, Fund I, or SPV. Do not use specific sample entities as hard positives; apply only the parent/mother-entity rule and source-backed relationship rule.
- For associated people, founders, controlled affiliates, parent/group platforms, or branded operating platforms, mark a capability only when the source clearly attributes operating control, ownership, executive role, or brand/platform linkage to the investor row. If attribution is plausible but not clear, search once more and set `needs_manual_review = yes` if still ambiguous.
- Do not infer non-`defi` capabilities only from portfolio companies, investee product features, generic crypto exposure, exchange listings, maker/taker fee schedules, token allocations for third-party market makers, or educational content about a capability. For `defi`, current portfolio/investment/support exposure can support `yes` under the DeFi rules above.

## Verification

Verifier focus:
- global source and attribution failures: verify current official/trusted evidence, official-vs-database conflicts, stale/historical-only evidence, current status, controlled parent/subsidiary relationship, self-operated-vs-third-party services, and whether `needs_manual_review = yes` should be set instead of forcing a `yes`
- `otc_trading` false positives and false negatives under the current operating-capability standard: verify current direct OTC service, one-way parent inheritance from controlled subsidiaries/arms, and reject portfolio exposure, stale/historical OTC, liquidity-only language, broker-dealer/market-maker status alone, OTC access-only, settlement/custody-only, and on-chain RFQ/intent evidence
- `algorithm_trading` false positives and false negatives under the current operating-capability standard: verify current direct algorithmic/quantitative/systematic/HFT/automated trading capability, one-way parent inheritance from controlled subsidiaries/operating units, and reject portfolio exposure, stale/historical algorithm trading, market-maker status alone, proprietary-trading status alone, liquidity-provider language alone, "technology-driven trading firm" language alone, API/FIX/connectivity, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing/execution algorithms alone, and brokerage/execution/liquidity-access evidence that does not explicitly provide algorithm-trading service/agency capability
- `market_making` false positives and false negatives under the current operating-capability standard: verify current direct market-making or liquidity-provision service using the investor's own/controlled capital, one-way parent inheritance from controlled subsidiaries/operating units, official/designated market-maker or liquidity-provider roles, and OTC principal/balance-sheet liquidity. Reject portfolio exposure, stale/historical market making, generic liquidity-provider/deep-liquidity language, liquidity access, quotes/pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker status alone, proprietary-trading/HFT/quant status alone, passive fund investment, passive LP allocation, client portfolio allocation, AMM/DEX/pool operation without LP capital, protocol/token liquidity support that is not the investor's own ongoing LP/market-maker role, third-party market-maker allocations, and individual founder/advisor/executive association
- `execution_services` false positives and false negatives under the current operating-capability standard: verify current direct order placement, order handling, executable broker service, trade execution, matching engine, trading venue, exchange/CEX, ATS/MTF/ECN, DEX, swap, perp DEX, AMM, or on-chain trading protocol operation, plus one-way parent inheritance from controlled subsidiaries/operating units. Reject portfolio exposure, stale/historical execution, routing/smart routing alone, API/FIX/connectivity alone, liquidity access/aggregation alone, connecting to third-party liquidity/venues, white-label/embedded third-party execution, redirect-to-external-venue trading, wallet external-link trading, custody/settlement/clearing/post-trade-only services, market making alone, OTC desk alone, view-only wallet/portfolio/analytics tools, and individual founder/advisor/executive association
- `defi` false positives and false negatives under the broad current DeFi exposure rules: verify current official/trusted-database investment, backing, grant, accelerator, ecosystem support, controlled fund vehicle, controlled venture/investment arm, parent-controlled investment activity, current official public portfolio, or direct operation; do not apply the old operating-only DeFi standard, but reject unaffiliated affiliates, manager-only relationships, uncontrolled funds, old news-only investments omitted by current official portfolios, and stale/historical exposure
- `sub_fund` false positives and false negatives under the current parent/mother-entity structure standard: verify that the current investor row currently has a child sub-fund, fund vehicle, venture arm, investment arm, crypto arm, dedicated capital pool, or comparable sub-fund-like structure. Reject rows that are merely fund vehicles, feeders, SPVs, protected cells, venture arms, investment arms, crypto arms, subsidiaries, brands, accelerators/incubators, ecosystem programs, portfolio companies, externally managed vehicles, generic fund managers, ordinary closed funds, name-only matches, or stale/historical structures with no current official/trusted confirmation.
- skipped rows that should have been searched
- operating-company profiles incorrectly treated as pure VC/angel records

`verification_report.csv` header:

```csv
task_index,investor_id,investor_name,classifier_search_tier,worker_capability_labels,verifier_search_tier,verifier_capability_labels,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

## Long-Run Behavior

- prefer `scripts/6_start_long_running_supervisor.py` for detached backlog runs
- prefer queue mode for unattended work
- use `scripts/7_check_longrun_status.py` as the canonical status entrypoint
- preserve the established two-stage long-tail handling:
  - first timeout parks the batch for one tail retry
  - second timeout becomes terminal `deferred_long_tail`
