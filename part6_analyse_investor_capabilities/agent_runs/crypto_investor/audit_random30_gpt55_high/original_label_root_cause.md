# Part6 Random-90 Audit - Original Label Root Cause Analysis

## Scope

- generated_at_utc: 2026-06-08T11:27:55.260665+00:00
- This file analyzes why the original Part6 output likely missed or over-labeled each inconsistent company.
- The analysis is inferred from `results.csv`, `classifier_results.csv`, `needs_manual_review.csv`, and the independent GPT-5.5-high audit outputs.
- This is a root-cause inference, not a transcript of the original worker's hidden reasoning.

## Root-Cause Categories

- Narrow boundary interpretation: original worker found the source but interpreted the capability boundary too narrowly.
- Evidence not searched deeply enough: original worker found the main capability but did not search legal docs, fund filings, product docs, or related official pages.
- Attribution boundary: evidence belongs to a linked operating platform, group entity, or associated person, and original worker used a narrower attribution rule.
- Weak evidence over-inference: original worker inferred a capability from generic or secondary evidence that did not satisfy the stricter audit threshold.
- Classifier routing miss: classifier skipped or under-routed the row, so the worker had no chance to find the capability.

## Category Counts

| root_cause_inference | count |
| --- | --- |
| DeFi specialization or product evidence missed | 9 |
| OTC or related-platform evidence missed | 1 |
| algorithmic or automated execution detail missed or mapped narrowly | 5 |
| classifier routing miss | 3 |
| fund-structure evidence not carried into sub_fund | 9 |
| market-making or liquidity-provision signal missed | 2 |
| narrow DEX/AMM capability mapping | 10 |
| narrow OTC-to-execution boundary mapping | 4 |
| weak evidence over-inference or attribution too broad | 5 |

## Company-Level Analysis

### 1. YAY Network - 漏標 `execution_services`

- Task: 3298
- Original labels: `["otc_trading", "defi"]`
- Audit labels: `["otc_trading", "execution_services", "defi"]`
- Manual review: yes
- Likely root cause: narrow OTC-to-execution boundary mapping.

The original evidence summary was: YAY Network FAQ describes an investment syndicate with public, OTC, and NDA deals, while tokenomics docs show farming rewards, liquidity, and market-making token allocations.

The audit evidence summary was: YAY official/owned sources describe OTC deals, an OTC marketplace/portal for allocations, broker-facilitated transactions outside exchanges, and YAY Games DeFi/NFT/farming products. No algorithmic trading, market making, or sub-fund evidence found.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: Official OTC marketplace crosses OTC/execution boundary; farming/staking/NFT DeFi docs cross DeFi boundary.

### 2. Belobaba Fund - 漏標 `sub_fund`

- Task: 6538
- Original labels: `["otc_trading", "execution_services", "defi"]`
- Audit labels: `["otc_trading", "execution_services", "defi", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Belobaba's official site describes an OTC crypto-fiat platform with direct order execution and a KHAN PLUS product that is explicitly tied to the DeFi ecosystem with daily on-chain accrual and autocompounding.

The audit evidence summary was: Belobaba official OTC page describes an OTC crypto-fiat service/trading desk and direct large-scale transactions outside order books; legal and fund documents show exchange/custody services, protected cell/master-feeder/Delaware feeder/SPV structure, and DeFi-linked token/staking/liquidity features.

For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: OTC trading desk; direct execution; master-feeder/PCC/feeder/SPV; DeFi-linked token ecosystem.

### 3. Great South Gate Asset Management - 漏標 `sub_fund`

- Task: 751
- Original labels: `["algorithm_trading", "execution_services"]`
- Audit labels: `["algorithm_trading", "execution_services", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: GSG describes digital asset alpha strategies that use systematic trading and says it offers prime brokerage liquidity and institutional services

The audit evidence summary was: GSG official materials market systematic/stat-arb/CTA digital asset strategies; job evidence describes private client brokerage and trade execution lifecycle; MAS and official site show offshore feeder/SPC/Cayman structures. No OTC, market-making, or DeFi operation found.

For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: Systematic strategy language supports algorithm_trading; brokerage/trade lifecycle supports execution_services; SPC/feeder supports sub_fund.

### 4. North Rock Digital - 多標 `algorithm_trading`

- Task: 11089
- Original labels: `["algorithm_trading"]`
- Audit labels: `[]`
- Manual review: no
- Likely root cause: weak evidence over-inference or attribution too broad.

The original evidence summary was: Preqin and aVenture both profile North Rock Digital as a crypto hedge fund; Preqin explicitly notes systematic and opportunistic strategies, which support algorithm_trading, but there is no OTC, market-making, execution, DeFi, or sub-fund evidence.

The audit evidence summary was: SEC/Form D evidence identifies a pooled-investment hedge fund/adviser; secondary strategy language was not enough to prove algorithmic/systematic/HFT trading capability. No trading desk, market making, DeFi operation, execution service, or explicit feeder/SPV/sub-fund structure found.

For `algorithm_trading`, the original output likely over-inferred from weak, generic, stale, or too-broad attribution evidence. The audit-side exclusion note was: Secondary strategy snippets without primary capability evidence are insufficient for algorithm_trading; managed hedge fund alone is not sub_fund.

### 5. RedLine Capital - 漏標 `sub_fund`

- Task: 4598
- Original labels: `["algorithm_trading", "market_making"]`
- Audit labels: `["algorithm_trading", "market_making", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Current sources describe Redline Capital as a blockchain investment firm that runs a crypto quantitative fund and handles exchange liquidity and market making.

The audit evidence summary was: RedLine/Redline DAO materials describe six sub-funds, quantitative transaction expertise, and a professional quantitative team providing liquidity and market maker services. No OTC, execution/brokerage, or DeFi-operated product found.

For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: Explicit quantitative team and market maker services cross algorithm/market_making; six sub-funds cross sub_fund.

### 6. Genblock Capital - 漏標 `defi`

- Task: 23
- Original labels: `["market_making"]`
- Audit labels: `["market_making", "defi"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: Genblock is an exclusive blockchain/crypto investor that explicitly helps portfolio projects with liquidity and market making.

The audit evidence summary was: Genblock official about page says it invests exclusively in blockchain/crypto with a focus on decentralized finance and helps portfolio projects with bootstrapping liquidity, token economics, and market making. No OTC, algorithmic trading, execution service, or sub-fund evidence found.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: Explicit market-making help crosses market_making; explicit DeFi focus crosses the audit DeFi specialization boundary.

### 7. A+ Ventures - 多標 `sub_fund`

- Task: 1942
- Original labels: `["sub_fund"]`
- Audit labels: `[]`
- Manual review: no
- Likely root cause: weak evidence over-inference or attribution too broad.

The original evidence summary was: The official site says A+ Ventures is an independent VC fund manager and that it deploys capital through carefully structured SPVs, which is explicit sub-fund/SPV evidence.

The audit evidence summary was: A+ Ventures appears to be a Web3/blockchain VC/accelerator/business consulting firm. No explicit OTC, algorithmic, market-making, execution, DeFi-operated product, or sub-fund/feeder/SPV/fund-platform evidence found; primary-source availability was sparse.

For `sub_fund`, the original output likely over-inferred from weak, generic, stale, or too-broad attribution evidence. The audit-side exclusion note was: Web3 incubation and funding token projects are not enough for DeFi or sub_fund.

### 8. MochiLab - 漏標 `market_making`, 漏標 `execution_services`

- Task: 10739
- Original labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: LinkedIn describes MochiLab as an incubator of future innovative DeFi and NFT projects; a press release tied to the team describes the project as community-driven and aimed at DeFi/NFT infrastructure.

The audit evidence summary was: MochiLab incubated/created Mochi.Market, a multi-chain decentralized NFT exchange with AMM, staking, lending, fractionalization, and cross-chain swaps. This supports protocol-level market_making, execution_services, and DeFi. No OTC, algorithmic trading, or sub-fund evidence found.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: AMM/liquidity solution supports protocol-level market_making; decentralized exchange supports execution_services; DeFi-native product supports DeFi.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: AMM/liquidity solution supports protocol-level market_making; decentralized exchange supports execution_services; DeFi-native product supports DeFi.

### 9. BitGo - 漏標 `algorithm_trading`, 漏標 `defi`

- Task: 1543
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: BitGo markets prime brokerage and OTC trading, including trading, financing, collateral management, settlement, and electronic execution from regulated custody.

The audit evidence summary was: BitGo official materials advertise OTC/block trading, prime brokerage/electronic trading/API/UI execution, smart order routing, algorithmic pass-through execution such as TWAP/VWAP, and institutional DeFi access through custody/wallet integrations. No self market-making or sub-fund structure found.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit.

### 10. Jesse Powell - 漏標 `algorithm_trading`, 漏標 `market_making`

- Task: 9515
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Manual review: no
- Likely root cause: algorithmic or automated execution detail missed or mapped narrowly.

The original evidence summary was: Kraken’s official site and press release say it is a crypto exchange with exchange trading, OTC trading, futures, and API access; Powell co-founded the exchange and is chairman.

The audit evidence summary was: Official Kraken sources tie Jesse Powell to Kraken and show OTC desk, API/FIX low-latency/automated trading access, token liquidity support, and execution services. No DeFi-native protocol operation or sub-fund evidence found for Powell.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: Founder/chairman linkage to Kraken used for OTC/API/market-structure/execution capability.
For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: Founder/chairman linkage to Kraken used for OTC/API/market-structure/execution capability.

### 11. Ace Exchange - 漏標 `algorithm_trading`

- Task: 5778
- Original labels: `["execution_services"]`
- Audit labels: `["algorithm_trading", "execution_services"]`
- Manual review: no
- Likely root cause: algorithmic or automated execution detail missed or mapped narrowly.

The original evidence summary was: ACE Exchange's help center says it is a fiat-to-crypto exchange and user-friendly trading platform with compliance and security features.

The audit evidence summary was: ACE official materials describe an order-book exchange and AI/grid trading robot described as a quantitative strategy. No official OTC desk, market making, DeFi operation, or sub-fund evidence found.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: Official AI/grid trading robot supports algorithm_trading; exchange order-book supports execution_services.

### 12. SOMESING (Social/Platform Software) - 漏標 `defi`

- Task: 12479
- Original labels: `[]`
- Audit labels: `["defi"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: SOMESING is a blockchain singing app and ecosystem, not a trading or fund-vehicle business.

The audit evidence summary was: SOMESING official site shows blockchain content/token platform; 2021 reports and Delio guide describe SSX crypto deposit/yield product with Delio. No trading desk, algorithmic trading, market making, execution, or sub-fund evidence found.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: Co-launched/marketed SSX deposit/yield product with DeFi/open-finance provider supports DeFi.

### 13. Exnetwork Capital - 漏標 `otc_trading`

- Task: 4
- Original labels: `[]`
- Audit labels: `["otc_trading"]`
- Manual review: no
- Likely root cause: OTC or related-platform evidence missed.

The original evidence summary was: Row describes a crypto VC focused on blockchain and cryptocurrency; no explicit operating capability evidence was found.

The audit evidence summary was: Exnetwork is a blockchain fund/incubator; ExNetwork-owned Medium and third-party article tie Exnetwork/Eric Su to The OTC Room/major crypto OTC trading desk. No algorithmic, market-making, execution, DeFi operation, or sub-fund evidence found.

For `otc_trading`, the original output likely missed a positive signal. The audit-side boundary note was: Explicit OTC Room/OTC desk evidence supports otc_trading.

### 14. Vision Capital - 漏標 `sub_fund`

- Task: 4883
- Original labels: `[]`
- Audit labels: `["sub_fund"]`
- Manual review: no
- Likely root cause: classifier routing miss.

The classifier routed this row as `skip_candidate` with `capability_search_required=no`. Because the independent audit found `["sub_fund"]`, the miss likely began before the capability worker searched the row.

The original evidence summary was: No search performed; routed as skip_candidate based on the input row only.

The audit evidence summary was: Vision Capital is a private equity/direct portfolio acquisition group. SEC/private fund/Gazette evidence ties Vision Capital fund entities to feeder/master/fund-of-funds structures, supporting sub_fund. No trading, execution, market-making, or DeFi operation found.

For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: Explicit feeder LP/master/fund-of-funds evidence supports sub_fund.

### 15. Sentillia - 漏標 `algorithm_trading`

- Task: 3428
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services"]`
- Manual review: yes
- Likely root cause: algorithmic or automated execution detail missed or mapped narrowly.

The original evidence summary was: Deribit support docs and the Sentillia profile identify the entity as a crypto futures/options exchange with low-latency trading and OTC RFQ functionality, conflicting with the VC-style task-row description.

The audit evidence summary was: Primary sources identify Sentillia B.V. as Deribit. Deribit docs show derivatives/spot trading venue, API/FIX execution, block trading for large off-book negotiated trades, and low-latency/mass-quote functionality. No self market-making, DeFi operation, or sub-fund evidence found.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: Block trading supports OTC; API/FIX and mass quotes support execution/algorithmic capabilities.

### 16. OccamDAO - 漏標 `market_making`, 漏標 `execution_services`

- Task: 4475
- Original labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Manual review: yes
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: Official site and docs describe Occam as a DeFi launchpad/DEX/DAO platform.

The audit evidence summary was: OccamDAO/Occam.fi materials describe DAO-governed DeFi ecosystem services including launchpad, DEX, DAO, incubator, OccamX DEX liquidity provision/mining/fees, and cross-chain trading. No OTC, algorithmic trading, or sub-fund evidence found.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: DEX liquidity pools support market_making; DEX trading infrastructure supports execution_services; DeFi suite supports DeFi.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: DEX liquidity pools support market_making; DEX trading infrastructure supports execution_services; DeFi suite supports DeFi.

### 17. MHC Digital Group - 漏標 `market_making`, 漏標 `defi`

- Task: 4383
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: Official site and OTC page describe institutional OTC execution, custody, settlement, and post-trade support; that is sufficient for OTC trading and execution-services capability.

The audit evidence summary was: MHC Digital Group's official site markets MHC Markets as an institutional OTC desk for buying, selling, swapping, custody, secure execution, fast settlement, AUD/USD on/off ramps, aggregated global liquidity, and multiple liquidity venues. Its official trading terms are OTC trading terms for fiat and digital asset pairs and other OTC services. Its funds-management pages state that MHC actively manages liquid digital-asset exposure across sectors including DeFi, and its Digital Asset Fund is actively managed around themes including DeFi. An official MHC market-making guide presents MHC Digital Group as an institutional-grade partner for projects seeking compliant digital-asset liquidity solutions in the context of selecting a crypto market-making partner. I found no explicit MHC algorithmic/quantitative/HFT trading desk evidence and no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because MHC explicitly markets an institutional-grade OTC desk and official OTC trading terms.|execution_services crosses the threshold because MHC explicitly markets secure execution, optimized execution, liquidity venue aggregation, fast settlement, on/off ramps, and liquidity access through its OTC platform.|market_making crosses the threshold because MHC's official market-making guide identifies MHC Digital Group as a partner for digital-asset liquidity solutions in the context of choosing a market-making partner.|defi crosses the threshold because MHC itself markets actively managed fund exposure to DeFi themes and DeFi tokens, not merely portfolio-company investments.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because MHC explicitly markets an institutional-grade OTC desk and official OTC trading terms.|execution_services crosses the threshold because MHC explicitly markets secure execution, optimized execution, liquidity venue aggregation, fast settlement, on/off ramps, and liquidity access through its OTC platform.|market_making crosses the threshold because MHC's official market-making guide identifies MHC Digital Group as a partner for digital-asset liquidity solutions in the context of choosing a market-making partner.|defi crosses the threshold because MHC itself markets actively managed fund exposure to DeFi themes and DeFi tokens, not merely portfolio-company investments.

### 18. Samuel Bankman-Fried - 漏標 `execution_services`

- Task: 12087
- Original labels: `["otc_trading", "algorithm_trading", "market_making", "defi"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow OTC-to-execution boundary mapping.

The original evidence summary was: SEC and CFTC filings describe FTX as a crypto asset trading platform and Alameda as a primary market maker; the task row describes an automated OTC trading system, and the Serum site describes a DEX and DeFi ecosystem.

The audit evidence summary was: The CFTC amended complaint states that Bankman-Fried owned, operated, or controlled FTX and Alameda; Alameda used proprietary algorithmic quantitative programs and high-frequency arbitrage, and operated as a primary market maker/liquidity provider on FTX. The same filing describes FTX as a centralized digital asset exchange with an order book, matching engine, API, and OTC portal for direct quote-based spot trades. An Economic Club transcript states Bankman-Fried designed Jane Street's automated OTC-trading system. Serum documentation describes Serum as a decentralized finance protocol with an on-chain order book and matching engine, and SFOX reports Project Serum was founded by Sam Bankman-Fried and FTX members. No evidence found for sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds capability.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because public evidence explicitly says Bankman-Fried designed an automated OTC-trading system at Jane Street, and the FTX platform he controlled also operated an OTC portal for direct quote-based trades.|algorithm_trading crosses the threshold because Alameda, under Bankman-Fried's ownership/control, used proprietary algorithmic quantitative programs and high-frequency arbitrage trading.|market_making crosses the threshold because Alameda, under Bankman-Fried's ownership/control, was explicitly described as a primary market maker and liquidity provider on FTX.|execution_services crosses the threshold because FTX, controlled by Bankman-Fried, operated exchange infrastructure including an electronic order book, matching engine, API access, and OTC portal.|defi crosses the threshold because Bankman-Fried is publicly tied to founding Project Serum, and Serum's own docs describe it as a DeFi protocol/ecosystem with decentralized order-book and matching infrastructure.

### 19. Pantronics Holdings - 漏標 `algorithm_trading`, 漏標 `defi`, 漏標 `sub_fund`

- Task: 11292
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services", "defi", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Former Pantronics Holdings / Huobi Tech now New Huo Technology; news coverage says it launched a crypto OTC service and also offers virtual asset management, custody, trust, and brokerage-related services.

The audit evidence summary was: HKEX filings show Pantronics Holdings changed name to Huobi Technology Holdings, later Sinohope Technology. Sinohope's 2025 annual report explicitly describes OTC virtual asset trading with corporate and individual customers, client execution of large trades, crypto exchange services, automated crypto asset trading services, quantitative products using fee and basis arbitrage, and controlled sub-funds including Sinohope Delta Neutral Quant Arbitrage Sub-fund. A company-distributed announcement says New Huo Tech launched DeFi and metaverse thematic investment services via its licensed asset manager. No source found shows the entity currently operates market making or liquidity provision; the annual report discusses market making and liquidity provision only as future/customized solution targets.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because the annual report explicitly states the Group provides over-the-counter virtual asset trading business.|algorithm_trading crosses the threshold because the annual report explicitly identifies quantitative products and quantitative trading strategies including fee arbitrage and basis arbitrage.|execution_services crosses the threshold because the annual report says OTC clients execute large trades through the Group's services and describes crypto exchange and automated crypto asset trading services through a proprietary platform.|defi crosses the threshold because the company announcement explicitly markets DeFi thematic investment services, not merely passive investments in DeFi startups.|sub_fund crosses the threshold because the annual report explicitly names controlled sub-funds and segregated portfolio structures, including Sinohope Delta Neutral Quant Arbitrage Sub-fund.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because the annual report explicitly states the Group provides over-the-counter virtual asset trading business.|algorithm_trading crosses the threshold because the annual report explicitly identifies quantitative products and quantitative trading strategies including fee arbitrage and basis arbitrage.|execution_services crosses the threshold because the annual report says OTC clients execute large trades through the Group's services and describes crypto exchange and automated crypto asset trading services through a proprietary platform.|defi crosses the threshold because the company announcement explicitly markets DeFi thematic investment services, not merely passive investments in DeFi startups.|sub_fund crosses the threshold because the annual report explicitly names controlled sub-funds and segregated portfolio structures, including Sinohope Delta Neutral Quant Arbitrage Sub-fund.
For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because the annual report explicitly states the Group provides over-the-counter virtual asset trading business.|algorithm_trading crosses the threshold because the annual report explicitly identifies quantitative products and quantitative trading strategies including fee arbitrage and basis arbitrage.|execution_services crosses the threshold because the annual report says OTC clients execute large trades through the Group's services and describes crypto exchange and automated crypto asset trading services through a proprietary platform.|defi crosses the threshold because the company announcement explicitly markets DeFi thematic investment services, not merely passive investments in DeFi startups.|sub_fund crosses the threshold because the annual report explicitly names controlled sub-funds and segregated portfolio structures, including Sinohope Delta Neutral Quant Arbitrage Sub-fund.

### 20. Mohamed Jezri Mohideen - 漏標 `execution_services`, 漏標 `defi`, 漏標 `sub_fund`

- Task: 10747
- Original labels: `["otc_trading", "algorithm_trading", "market_making"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Laser Digital bio says he led flow trading and systematic trading while company news describes market making liquidity provision and an OTC crypto options license

The audit evidence summary was: Laser Digital official materials state that Jez Mohideen co-founded Laser Digital and serves as Co-founder and CEO. Laser Digital's trading page explicitly lists OTC, token market making, quant-driven liquidity provision, systematic trading experience, live executable two-way price streams, FIX/WebSocket connectivity, and post-trade settlement. Its asset-management page says the Carry Fund uses an internal institutional-grade execution platform to access diversified liquidity, while its Bitcoin Diversified Yield Fund deploys market-neutral arbitrage and DeFi strategies and is offered in tokenised and traditional fund formats. Laser's DeFi-enabled Ethereum Adoption Fund page describes built-in DeFi mechanisms and a compliant DeFi market-access vehicle. Laser also states funds are segregated portfolios within Laser Digital Funds SPC and describes Tokenised LCF exposure to Laser Digital Carry Fund SP, a Cayman Segregated Portfolio. KAIO documentation supports fund-platform evidence, describing KAIO as a tokenized-funds and institutional DeFi platform with native fund lifecycle support.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Laser Digital's own trading page labels the service 'OTC' and describes executable two-way crypto and FX price streams.|algorithm_trading crosses the threshold because Laser Digital explicitly describes quant-driven liquidity provision and systematic trading.|market_making crosses the threshold because Laser Digital explicitly markets token market making and liquidity provision for token projects.|execution_services crosses the threshold because Laser Digital describes live executable price streams, FIX/WebSocket connectivity, post-trade settlement, and an internal institutional-grade execution platform to access diversified liquidity.|defi crosses the threshold because Laser Digital markets DeFi-enabled funds and fund strategies with built-in DeFi mechanisms, DeFi strategies, and compliant DeFi market access.|sub_fund crosses the threshold because Laser Digital's funds are described as segregated portfolios/SPC structures and KAIO is explicitly a tokenized-funds platform with fund lifecycle infrastructure.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Laser Digital's own trading page labels the service 'OTC' and describes executable two-way crypto and FX price streams.|algorithm_trading crosses the threshold because Laser Digital explicitly describes quant-driven liquidity provision and systematic trading.|market_making crosses the threshold because Laser Digital explicitly markets token market making and liquidity provision for token projects.|execution_services crosses the threshold because Laser Digital describes live executable price streams, FIX/WebSocket connectivity, post-trade settlement, and an internal institutional-grade execution platform to access diversified liquidity.|defi crosses the threshold because Laser Digital markets DeFi-enabled funds and fund strategies with built-in DeFi mechanisms, DeFi strategies, and compliant DeFi market access.|sub_fund crosses the threshold because Laser Digital's funds are described as segregated portfolios/SPC structures and KAIO is explicitly a tokenized-funds platform with fund lifecycle infrastructure.
For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Laser Digital's own trading page labels the service 'OTC' and describes executable two-way crypto and FX price streams.|algorithm_trading crosses the threshold because Laser Digital explicitly describes quant-driven liquidity provision and systematic trading.|market_making crosses the threshold because Laser Digital explicitly markets token market making and liquidity provision for token projects.|execution_services crosses the threshold because Laser Digital describes live executable price streams, FIX/WebSocket connectivity, post-trade settlement, and an internal institutional-grade execution platform to access diversified liquidity.|defi crosses the threshold because Laser Digital markets DeFi-enabled funds and fund strategies with built-in DeFi mechanisms, DeFi strategies, and compliant DeFi market access.|sub_fund crosses the threshold because Laser Digital's funds are described as segregated portfolios/SPC structures and KAIO is explicitly a tokenized-funds platform with fund lifecycle infrastructure.

### 21. Jane Street - 漏標 `defi`

- Task: 1071
- Original labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: Official pages describe Jane Street as a research-driven trading firm, a global liquidity provider, one of the world's largest market makers, and a firm that provides direct OTC trading and execution for clients, including crypto token trading.

The audit evidence summary was: Jane Street's official materials identify it as a global liquidity provider and trading firm using sophisticated quantitative analysis, models, strategies, and systems, and as one of the world's largest market makers. Its client offering states that it is a leading market maker and liquidity provider, active in bilateral/off-exchange markets, provides direct OTC bond trading with clients, offers electronic trading infrastructure including smart-order-router/FIX access, and provides wholesale market making. A FINRA Rule 606 report for Jane Street Execution Services confirms routing of customer orders via smart order routers/algos. DeFi is supported by Clearpool's announcement of a DeFi lending protocol pool in partnership with Jane Street and The TRADE's report that Jane Street joined the DeFi Pyth Network as a crypto market data contributor. No public evidence found for a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds capability.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Jane Street's official client offering explicitly says it is active in bilateral, off-exchange markets and provides direct OTC trading with clients.|algorithm_trading=yes because official materials explicitly describe quantitative analysis, models, algorithms, trading systems, machine learning, and quantitative trading.|market_making=yes because official materials explicitly call Jane Street a leading market maker and one of the world's largest market makers.|execution_services=yes because official materials describe client execution, execution-quality services, smart-order-router/FIX access, proprietary liquidity access, and Jane Street Execution Services as a broker-dealer; FINRA reports confirm customer order routing.|defi=yes because Jane Street itself participated in a Clearpool DeFi lending protocol pool and joined Pyth Network as a contributor to a DeFi data network, which goes beyond merely funding DeFi startups.

### 22. Amber Group - 漏標 `defi`

- Task: 101
- Original labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: Amber Group describes itself as a global digital financial services firm and explicitly lists algorithmic trading, market making, OTC trading, and execution services.

The audit evidence summary was: Amber Group's official pages explicitly market OTC trading, 24/7 execution services, VWAP/TWAP and customized advanced order execution, automated strategies, market-making/liquidity provision, and DeFi products/DeFi market integration. Its official support article describes Algorithmic Trading/Execution using automated pre-programmed instructions and aggregated execution across centralized and decentralized venues. Its asset-management page also describes algorithm research, low-latency high-throughput trading infrastructure, systematic models, and automated institutional order execution. No explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence was found in the reviewed public evidence.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Amber Group's official digital wealth page has an explicit OTC Trading section and says clients can contact its OTC trading team.|algorithm_trading=yes because official materials explicitly describe automated strategies, algorithmic trading, algorithm research, systematic models, and VWAP/TWAP/advanced order execution.|market_making=yes because Amber Group's official liquidity provision page says it is a primary liquidity provider and cites sophisticated market making expertise and daily market-making volumes.|execution_services=yes because official materials explicitly market 24/7 trading execution services, advanced order execution, aggregated execution, and access to global market liquidity.|defi=yes because Amber Group itself explicitly markets DeFi Yield Enhanced Products and execution/liquidity across decentralized venues or CeFi and DeFi markets, not merely portfolio investment in DeFi startups.

### 23. Joseph Jones - 漏標 `execution_services`, 多標 `sub_fund`

- Task: 4242
- Original labels: `["sub_fund"]`
- Audit labels: `["execution_services"]`
- Manual review: no
- Likely root cause: weak evidence over-inference or attribution too broad.

The original evidence summary was: HMC INQ's official pages identify Jones as founding partner, describe him as a DreamHost co-founder and Bitcoin investor, and say Harvey's Angels investments use a simple SPV structure and process.

The audit evidence summary was: Official HMC INQ and FlyCoin materials identify Joseph/Josh Jones as an entrepreneur, HMC INQ founding partner, Bitcoin investor, and founder of Bitcoin Builder, with FlyCoin also describing him as Owner, Chairman, and CTO of FLOAT Alaska. Coindesk reported that Bitcoin Builder, founded by Josh Jones, allowed Mt. Gox customers to trade account funds for bitcoin and that about 14,500 BTC of trades had executed. Bitcoinist reported Bitcoin Builder relaunched as a Bitcoin Exchange Aggregator pulling best prices from multiple exchanges, offering buy/sell bitcoin trading and feeless trade executions, plus lending and shorting. This supports execution_services via an explicitly founder-operated trading/exchange aggregation platform. I found no explicit OTC desk/block/bilateral trading, algorithmic/quant/systematic/HFT trading, market making/liquidity provision, DeFi-native capability, or sub-fund/feeder/umbrella/SPV/fund-platform/fund-of-funds evidence attributable to Jones or his controlled platforms.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services crosses the threshold because Bitcoin Builder is explicitly attributed to Josh Jones as founder/CEO and is described as an exchange/trading platform and exchange aggregator enabling buy/sell trading, trade executions, and aggregation of order books from multiple major exchanges.
For `sub_fund`, the original output likely over-inferred from weak, generic, stale, or too-broad attribution evidence. The audit-side exclusion note was: Bitcoin Builder's exchange and aggregator activity is not explicit OTC desk, block trading, or bilateral trading evidence.|References to automated bitcoin buying on Mt. Gox and exchange aggregation do not explicitly establish algorithmic, quantitative, systematic, HFT, or low-latency trading.|Buying GOXBTC and operating a trading platform are not explicit market making or liquidity provision evidence.|FlyCoin and Bitcoin Builder are crypto-related, but the evidence describes centralized rewards, exchange, and aggregation services, not DeFi-native products or DeFi specialization.|HMC INQ is described as a venture fund/incubator supporting Harvey Mudd startups, but there is no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

### 24. Coven - 漏標 `defi`, 多標 `sub_fund`

- Task: 3891
- Original labels: `["sub_fund"]`
- Audit labels: `["defi"]`
- Manual review: no
- Likely root cause: weak evidence over-inference or attribution too broad.

The original evidence summary was: Mesh retrospective describes Coven as a decentralized venture investing platform and DAO.

The audit evidence summary was: ConsenSys Mesh describes Coven as an incubated project that built a decentralized venture investing platform, used token staking for sourcing, diligence, approval, and economics, and operated as a DAO before being sunset. Monerium's press release describes Coven as a ConsenSys Formation and open co-venturing initiative. USPTO trademark materials similarly describe Coven as a decentralized venture investing platform. I found no investor-level evidence that Coven itself offered OTC/block trading, algorithmic trading, market making/liquidity provision, execution/order routing/brokerage, prime brokerage, or liquidity access services. Alkemi was a portfolio/backed company with prime-brokerage and liquidity infrastructure, but that does not transfer execution or trading capabilities to Coven.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because Coven itself operated a decentralized, DAO-like venture investing platform using token staking and on-chain/Web3 investment primitives; this is investor-level DeFi-native capability, not merely a portfolio investment.
For `sub_fund`, the original output likely over-inferred from weak, generic, stale, or too-broad attribution evidence. The audit-side exclusion note was: otc_trading=no: no explicit Coven OTC desk, block trading, or bilateral trading service evidence.|algorithm_trading=no: no explicit Coven algorithmic, quantitative, systematic, HFT, or low-latency trading evidence.|market_making=no: no explicit Coven market making or liquidity provision evidence.|execution_services=no: no explicit Coven execution, smart order routing, order routing, brokerage, prime brokerage, or liquidity access service evidence; Alkemi's capabilities are portfolio-company evidence only.|sub_fund=no: no explicit Coven sub-fund, feeder, umbrella, parallel fund, SPV, or fund-of-funds evidence; broad venture fund/trademark language and a decentralized venture investing platform are not enough under the boundary rule.

### 25. Samara Alpha Management - 漏標 `market_making`, 漏標 `defi`

- Task: 12072
- Original labels: `["algorithm_trading", "sub_fund"]`
- Audit labels: `["algorithm_trading", "market_making", "defi", "sub_fund"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: Samara Alpha Management describes digital asset opportunities, market-neutral alpha, and beta-neutral strategies such as algorithmic trading on its official site; the SEC adviser record confirms the firm identity.

The audit evidence summary was: Samara Alpha's official site describes institutional-grade diversified digital asset funds and manager selection. Its Opportunities page markets Market-neutral Alpha as access to digital asset managers using strategies including market-making and proprietary algorithmic trading. It also describes a hedge fund seeding platform and a Boreal Market-Neutral DeFi strategy, while its strategy article explicitly describes Samara Alpha as using a fund-of-funds structure with monthly liquidity. I found no explicit evidence that Samara Alpha itself operates an OTC desk, bilateral/block trading service, brokerage, prime brokerage, order-routing, or execution-services platform.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: algorithm_trading=yes because Samara Alpha's official Market-neutral Alpha product explicitly includes exposure to proprietary algorithmic trading strategies.|market_making=yes because Samara Alpha's official Market-neutral Alpha product explicitly includes exposure to market-making strategies.|defi=yes because Samara Alpha explicitly markets DeFi product exposure through Boreal Market-Neutral DeFi and discusses DeFi strategies within its digital asset strategy offering.|sub_fund=yes because Samara Alpha explicitly describes a fund-of-funds structure and a hedge fund seeding platform.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: algorithm_trading=yes because Samara Alpha's official Market-neutral Alpha product explicitly includes exposure to proprietary algorithmic trading strategies.|market_making=yes because Samara Alpha's official Market-neutral Alpha product explicitly includes exposure to market-making strategies.|defi=yes because Samara Alpha explicitly markets DeFi product exposure through Boreal Market-Neutral DeFi and discusses DeFi strategies within its digital asset strategy offering.|sub_fund=yes because Samara Alpha explicitly describes a fund-of-funds structure and a hedge fund seeding platform.

### 26. Tikhon Bernstam - 多標 `sub_fund`

- Task: 13058
- Original labels: `["sub_fund"]`
- Audit labels: `[]`
- Manual review: no
- Likely root cause: weak evidence over-inference or attribution too broad.

The original evidence summary was: Uncommon Capital lists Bernstam as managing partner. Kando identifies Tikhon Bernstam AngelList Fund LP, and Fortune describes a Bernstam AngelList syndicate, which supports sub_fund/fund-platform capability beyond the local fund-name field. Forbes shows Web3/Rye exposure, but searches did not show OTC, algorithmic trading, market making, execution services, or DeFi-native operations by Bernstam.

The audit evidence summary was: Uncommon Capital's official site identifies Tikhon Bernstam as Managing Partner of an early-stage software venture investor and describes operational support in product, data, marketing, people, and engineering, but not trading, brokerage, market making, OTC, algorithmic trading, or DeFi products. SEC Form D evidence for Crystal Towers Capital, L.P. shows Bernstam as managing member of the general partner of a pooled venture capital fund; TechCrunch reports related Crystal Towers affiliate filings, but not an explicit feeder, SPV, umbrella, parallel fund, fund platform, or fund-of-funds structure. Secured Finance is a DeFi protocol/platform and lists Bernstam among investors, but portfolio investment alone does not confer DeFi capability to him as an investor. Rye evidence shows Bernstam as a founder of a Web3/e-commerce API company with checkout and crypto reward features, not a DeFi-native investment capability or financial trading/execution service.

For `sub_fund`, the original output likely over-inferred from weak, generic, stale, or too-broad attribution evidence. The audit-side exclusion note was: Secured Finance is a DeFi company, but Bernstam appears only as an investor in the available evidence; funding a DeFi startup alone is insufficient for defi=yes.|Rye has Web3, token, stablecoin reward, and checkout API evidence, but it is e-commerce infrastructure rather than OTC trading, algorithmic trading, market making, financial execution services, or a DeFi-native investor capability.|Crystal Towers and the AngelList fund references show venture/angel fund activity, but standard pooled venture funds and affiliated fund filings are insufficient for sub_fund=yes without explicit feeder, SPV, umbrella, parallel fund, fund platform, or fund-of-funds evidence.|Uncommon Capital mentions fintech/frontier-tech investing and operational help, but does not explicitly market trading desks, order routing, brokerage, liquidity access, market making, or quantitative/systematic trading.

### 27. OrangeX - 漏標 `market_making`

- Task: 11229
- Original labels: `["execution_services"]`
- Audit labels: `["market_making", "execution_services"]`
- Manual review: no
- Likely root cause: market-making or liquidity-provision signal missed.

The original evidence summary was: OrangeX's official pages describe a professional crypto trading platform with spot, perpetual, and copy trading and emphasize liquidity and trading execution.

The audit evidence summary was: OrangeX is an operating centralized crypto trading platform/exchange. Official materials describe spot trading, perpetual trading, order books, market and limit orders, order placement, and API-based account/product trading. Its official site also markets excellent liquidity supported by 50+ market-making teams, trusted partners, and a robust order book. I found no explicit OrangeX OTC desk/block/bilateral trading service, no explicit algorithmic/quant/systematic/HFT offering by OrangeX, no DeFi-native product operated by OrangeX, and no fund/sub-fund/feeder/SPV evidence.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services=yes because OrangeX officially operates spot and perpetual trading venues where users place buy/sell orders, use order books, and access trading via web/app/API.|market_making=yes because OrangeX's official site explicitly describes liquidity supported by 50+ market-making teams and a robust/extensive order book, satisfying explicit market-making/liquidity evidence for its operating exchange platform.

### 28. BitFlyer - 漏標 `otc_trading`, 漏標 `algorithm_trading`, 漏標 `market_making`

- Task: 6648
- Original labels: `["execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Manual review: no
- Likely root cause: algorithmic or automated execution detail missed or mapped narrowly.

The original evidence summary was: Official bitFlyer site describes a crypto marketplace, bitFlyer Lightning for sophisticated traders, API/web-interface execution of complex order types, and access to global BTC/JPY liquidity; no OTC desk, proprietary market making, DeFi, or sub-fund evidence was found.

The audit evidence summary was: bitFlyer official documents describe over-the-counter crypto asset derivatives as negotiated transactions between the customer and bitFlyer, Inc. as counterparty. Official trading disclosures state that bitFlyer's proprietary trading department and group companies may place orders to provide liquidity to Exchange and bitFlyer Lightning order books and that the proprietary trading department uses algorithm-based automated order placement. bitFlyer also operates customer trading venues, acts as intermediary on its exchange platform, executes user orders, offers bitFlyer Lightning, and provides HTTP/private APIs for placing and cancelling orders. DeFi evidence found was educational guidance and token/glossary content, not a DeFi-native product operated by bitFlyer. The Blockchain Angel Fund is described as an in-house seed-stage fund, with no sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

For `otc_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because official documents explicitly call bitFlyer's crypto derivative trades over-the-counter negotiated transactions with bitFlyer, Inc. as counterparty.|algorithm_trading crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department uses algorithm-based automated order placement.|market_making crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department/group companies place orders to provide liquidity to Exchange and bitFlyer Lightning order books.|execution_services crosses the threshold because bitFlyer operates exchange/trading platforms, executes user orders, acts as intermediary on the exchange platform, and provides APIs for order submission and cancellation.
For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because official documents explicitly call bitFlyer's crypto derivative trades over-the-counter negotiated transactions with bitFlyer, Inc. as counterparty.|algorithm_trading crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department uses algorithm-based automated order placement.|market_making crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department/group companies place orders to provide liquidity to Exchange and bitFlyer Lightning order books.|execution_services crosses the threshold because bitFlyer operates exchange/trading platforms, executes user orders, acts as intermediary on the exchange platform, and provides APIs for order submission and cancellation.
For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because official documents explicitly call bitFlyer's crypto derivative trades over-the-counter negotiated transactions with bitFlyer, Inc. as counterparty.|algorithm_trading crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department uses algorithm-based automated order placement.|market_making crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department/group companies place orders to provide liquidity to Exchange and bitFlyer Lightning order books.|execution_services crosses the threshold because bitFlyer operates exchange/trading platforms, executes user orders, acts as intermediary on the exchange platform, and provides APIs for order submission and cancellation.

### 29. UniLend Finance - 漏標 `market_making`, 漏標 `execution_services`

- Task: 3269
- Original labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: UniLend is a permissionless DeFi platform for spot trading and lending/borrowing, which is enough to mark defi=yes.

The audit evidence summary was: UniLend's official site and docs describe UniLend as a permissionless decentralized finance protocol for lending and borrowing ERC20 assets, with official documentation also describing spot trading services, decentralized trading functionality, trading pairs, and liquidity pools where liquidity providers receive fees. Official V2 documentation describes dual-asset lending pools, borrowing, lending, liquidation, and flashloan functions. I found no explicit evidence that UniLend operates an OTC desk, block or bilateral trading service, algorithmic/quantitative/HFT trading, or any sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because UniLend itself officially operates and markets a DeFi-native permissionless lending and borrowing protocol.|execution_services=yes because UniLend's official docs explicitly describe spot trading services, decentralized trading functionality, and in-platform trading pairs, which meets the DEX/exchange/swap venue execution-services boundary.|market_making=yes because UniLend's official docs describe liquidity pools and liquidity provision with fees within the UniLend protocol, meeting the AMM/liquidity-pool liquidity provision threshold for an operated DeFi protocol.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because UniLend itself officially operates and markets a DeFi-native permissionless lending and borrowing protocol.|execution_services=yes because UniLend's official docs explicitly describe spot trading services, decentralized trading functionality, and in-platform trading pairs, which meets the DEX/exchange/swap venue execution-services boundary.|market_making=yes because UniLend's official docs describe liquidity pools and liquidity provision with fees within the UniLend protocol, meeting the AMM/liquidity-pool liquidity provision threshold for an operated DeFi protocol.

### 30. Mow capital - 漏標 `algorithm_trading`

- Task: 1595
- Original labels: `["market_making"]`
- Audit labels: `["algorithm_trading", "market_making"]`
- Manual review: no
- Likely root cause: algorithmic or automated execution detail missed or mapped narrowly.

The original evidence summary was: Official site states that Mow Capital is a quantitative trading firm and liquidity provider active in major crypto markets and a high-frequency trader across leading exchanges.

The audit evidence summary was: Mow Capital's official site says it is a quantitative trading firm and liquidity provider active in leading crypto markets, has a high frequency trading section, trades major coins on major exchanges, and describes itself as a top market maker. The site also describes crypto investing, but does not show OTC desk/block trading, client execution or brokerage services, DeFi-native operations/products, or sub-fund/feeder/SPV/fund-platform structure.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: algorithm_trading=yes because the official site explicitly calls Mow Capital a quantitative trading firm and separately describes high frequency trading.|market_making=yes because the official site explicitly calls Mow Capital a liquidity provider and a top market maker.

### 31. LTP (Singapore) - 漏標 `algorithm_trading`, 漏標 `market_making`, 漏標 `defi`, 漏標 `sub_fund`

- Task: 10194
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Official pages describe a global institutional prime brokerage with OTC trading and execution clearing settlement custody lending and financing services; this supports otc_trading and execution_services only.

The audit evidence summary was: LTP's official materials describe it as an institutional digital-asset prime broker offering trade execution, clearing, settlement, custody, financing, liquidity access, Smart Order Routing, cross-exchange execution, ultra-low-latency connectivity, market data, DMA, and infrastructure for HFT/quantitative traders. LTP announced its own OTC trading platform with custom RFQs and block trade workflows. Official product updates describe access to centralized and decentralized exchanges, OTC venues, direct market access, automated execution, customized algorithmic trading, and tailored liquidity streams. LTP materials also identify Liquidity Fintech Investment Limited as investment manager of Liquidity Investment SPC, and an SEC Form D identifies Crypto Quant Fund SP as a segregated portfolio of Liquidity Investment SPC.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because LTP officially launched an Over-the-Counter trading platform with custom RFQs and block trade workflows, and other official materials describe regulated OTC block trading.|algorithm_trading=yes because official product and FAQ pages explicitly reference customized algorithmic trading, quantitative traders, high-frequency traders, ultra-low-latency access, DMA, and low-latency market data.|market_making=yes because LTP officially markets liquidity distribution, deep liquidity pools, tight spreads, tailored liquidity streams, and OTC infrastructure serving liquidity takers and market makers, which crosses the liquidity-provision threshold.|execution_services=yes because LTP explicitly offers prime brokerage, trade execution, Smart Order Routing, cross-exchange execution, DMA, liquidity access, and brokerage-style clearing/settlement services.|defi=yes because LTP itself markets infrastructure that gives institutions access to decentralized exchanges and integrates CeFi and DeFi liquidity, not merely investments in DeFi companies.|sub_fund=yes because official and SEC evidence show LTP-affiliated investment management for Liquidity Investment SPC and a named Crypto Quant Fund SP, a segregated portfolio of that SPC.
For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because LTP officially launched an Over-the-Counter trading platform with custom RFQs and block trade workflows, and other official materials describe regulated OTC block trading.|algorithm_trading=yes because official product and FAQ pages explicitly reference customized algorithmic trading, quantitative traders, high-frequency traders, ultra-low-latency access, DMA, and low-latency market data.|market_making=yes because LTP officially markets liquidity distribution, deep liquidity pools, tight spreads, tailored liquidity streams, and OTC infrastructure serving liquidity takers and market makers, which crosses the liquidity-provision threshold.|execution_services=yes because LTP explicitly offers prime brokerage, trade execution, Smart Order Routing, cross-exchange execution, DMA, liquidity access, and brokerage-style clearing/settlement services.|defi=yes because LTP itself markets infrastructure that gives institutions access to decentralized exchanges and integrates CeFi and DeFi liquidity, not merely investments in DeFi companies.|sub_fund=yes because official and SEC evidence show LTP-affiliated investment management for Liquidity Investment SPC and a named Crypto Quant Fund SP, a segregated portfolio of that SPC.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because LTP officially launched an Over-the-Counter trading platform with custom RFQs and block trade workflows, and other official materials describe regulated OTC block trading.|algorithm_trading=yes because official product and FAQ pages explicitly reference customized algorithmic trading, quantitative traders, high-frequency traders, ultra-low-latency access, DMA, and low-latency market data.|market_making=yes because LTP officially markets liquidity distribution, deep liquidity pools, tight spreads, tailored liquidity streams, and OTC infrastructure serving liquidity takers and market makers, which crosses the liquidity-provision threshold.|execution_services=yes because LTP explicitly offers prime brokerage, trade execution, Smart Order Routing, cross-exchange execution, DMA, liquidity access, and brokerage-style clearing/settlement services.|defi=yes because LTP itself markets infrastructure that gives institutions access to decentralized exchanges and integrates CeFi and DeFi liquidity, not merely investments in DeFi companies.|sub_fund=yes because official and SEC evidence show LTP-affiliated investment management for Liquidity Investment SPC and a named Crypto Quant Fund SP, a segregated portfolio of that SPC.
For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because LTP officially launched an Over-the-Counter trading platform with custom RFQs and block trade workflows, and other official materials describe regulated OTC block trading.|algorithm_trading=yes because official product and FAQ pages explicitly reference customized algorithmic trading, quantitative traders, high-frequency traders, ultra-low-latency access, DMA, and low-latency market data.|market_making=yes because LTP officially markets liquidity distribution, deep liquidity pools, tight spreads, tailored liquidity streams, and OTC infrastructure serving liquidity takers and market makers, which crosses the liquidity-provision threshold.|execution_services=yes because LTP explicitly offers prime brokerage, trade execution, Smart Order Routing, cross-exchange execution, DMA, liquidity access, and brokerage-style clearing/settlement services.|defi=yes because LTP itself markets infrastructure that gives institutions access to decentralized exchanges and integrates CeFi and DeFi liquidity, not merely investments in DeFi companies.|sub_fund=yes because official and SEC evidence show LTP-affiliated investment management for Liquidity Investment SPC and a named Crypto Quant Fund SP, a segregated portfolio of that SPC.

### 32. LD Capital - 漏標 `market_making`

- Task: 7
- Original labels: `["sub_fund"]`
- Audit labels: `["market_making", "sub_fund"]`
- Manual review: no
- Likely root cause: market-making or liquidity-provision signal missed.

The original evidence summary was: Official site says LD Capital is a crypto fund trading primary and secondary markets with multiple sub-funds, so sub_fund is warranted.

The audit evidence summary was: LD Capital's official site describes it as a crypto fund investing and trading in primary and secondary markets and explicitly states that its sub-funds include Beco Fund, FoF, hedge fund, Meta Fund, etc. A post by LD Capital says LD Capital, Antalpha Ventures, and Highblock jointly established a Hong Kong ETF liquidity fund designed to provide market-making services to Hong Kong ETFs. I found no explicit evidence that LD Capital itself offers OTC/block/bilateral trading, algorithmic/systematic/HFT trading, execution/order-routing/brokerage services, or a DeFi-native operating product beyond investing in DeFi portfolio companies.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: market_making=yes because LD Capital's own announcement says a jointly established ETF liquidity fund is designed to provide market-making services to Hong Kong ETFs.|sub_fund=yes because LD Capital's official site explicitly says its sub-funds include Beco Fund, FoF, hedge fund, Meta Fund, etc.

### 33. Mars Ecosystem - 漏標 `market_making`, 漏標 `execution_services`

- Task: 3039
- Original labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: Mars docs describe a decentralized stablecoin ecosystem with Mars Swap, Mars Stableswap, and Mars Money Market, which is explicit DeFi-native operation.

The audit evidence summary was: Mars Ecosystem's official documentation describes it as a decentralized stablecoin ecosystem made up of Mars Treasury, Mars Stablecoin, and Mars DeFi protocols. Its Mars DeFi protocols include Mars Swap and Mars StableSwap; Mars Swap is explicitly described as a Uniswap-type AMM DEX that incentivizes liquidity provision and USDm transactions, and the Mars Treasury uses assets to provide liquidity for USDm on Mars Swap. The same documentation states users trade on Mars DeFi protocols and pay transaction fees. I found no attributable evidence that Mars Ecosystem operates an OTC desk/block trading service, algorithmic/quant/HFT trading operation, or any sub-fund/feeder/umbrella/SPV/fund-of-funds structure.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because Mars Ecosystem itself officially operates/markets Mars DeFi protocols as part of its own decentralized stablecoin ecosystem.|market_making=yes because Mars Swap is explicitly an AMM DEX and the Mars Treasury provides liquidity for USDm on Mars Swap, satisfying the AMM/liquidity-pool operated-by-entity threshold.|execution_services=yes because Mars Ecosystem operates swap/DEX venues, Mars Swap and Mars StableSwap, where users trade and execute transactions on the protocol.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because Mars Ecosystem itself officially operates/markets Mars DeFi protocols as part of its own decentralized stablecoin ecosystem.|market_making=yes because Mars Swap is explicitly an AMM DEX and the Mars Treasury provides liquidity for USDm on Mars Swap, satisfying the AMM/liquidity-pool operated-by-entity threshold.|execution_services=yes because Mars Ecosystem operates swap/DEX venues, Mars Swap and Mars StableSwap, where users trade and execute transactions on the protocol.

### 34. Kraken - 漏標 `algorithm_trading`, 漏標 `market_making`, 漏標 `defi`

- Task: 2410
- Original labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: Official Kraken OTC pages say traders can execute orders off the open exchange and access deeper liquidity, tighter spreads, and OTC trading from Kraken Custody, Kraken Pro, and chat.

The audit evidence summary was: Kraken explicitly operates an OTC desk for off-exchange orders, RFQ/block trading, and execution/settlement services. Kraken Prime markets Prime Execution, multi-venue liquidity access, and smart order routing, while Kraken Institutional markets ultra-low-latency APIs, HFT support, deep liquidity, and market-maker-oriented products. Kraken's API pages explicitly support automated trading and advanced strategies. Kraken Wallet and DeFi Earn are Kraken/Payward products providing DeFi position management, decentralized-app interaction, and onchain DeFi vault exposure. I found no qualifying Kraken sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence attributable to Kraken as the investor.

For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Kraken's own OTC desk executes orders off the open exchange and supports RFQ and large block trading.|algorithm_trading=yes because Kraken markets automated API-based trading, low-latency infrastructure, FIX/WebSocket/REST APIs, and HFT/high-frequency strategy support through its own platform.|market_making=yes because Kraken's operated OTC/Prime/institutional platform provides deep and multi-venue liquidity, executable quotes, and products specifically for market makers.|execution_services=yes because Kraken explicitly offers execution and settlement services, Prime Execution, smart order routing, and liquidity access.|defi=yes because Kraken operates Kraken Wallet and DeFi Earn, which explicitly support DeFi positions, decentralized-app interaction, and onchain DeFi vault exposure.
For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Kraken's own OTC desk executes orders off the open exchange and supports RFQ and large block trading.|algorithm_trading=yes because Kraken markets automated API-based trading, low-latency infrastructure, FIX/WebSocket/REST APIs, and HFT/high-frequency strategy support through its own platform.|market_making=yes because Kraken's operated OTC/Prime/institutional platform provides deep and multi-venue liquidity, executable quotes, and products specifically for market makers.|execution_services=yes because Kraken explicitly offers execution and settlement services, Prime Execution, smart order routing, and liquidity access.|defi=yes because Kraken operates Kraken Wallet and DeFi Earn, which explicitly support DeFi positions, decentralized-app interaction, and onchain DeFi vault exposure.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Kraken's own OTC desk executes orders off the open exchange and supports RFQ and large block trading.|algorithm_trading=yes because Kraken markets automated API-based trading, low-latency infrastructure, FIX/WebSocket/REST APIs, and HFT/high-frequency strategy support through its own platform.|market_making=yes because Kraken's operated OTC/Prime/institutional platform provides deep and multi-venue liquidity, executable quotes, and products specifically for market makers.|execution_services=yes because Kraken explicitly offers execution and settlement services, Prime Execution, smart order routing, and liquidity access.|defi=yes because Kraken operates Kraken Wallet and DeFi Earn, which explicitly support DeFi positions, decentralized-app interaction, and onchain DeFi vault exposure.

### 35. Terraform Labs - 漏標 `execution_services`

- Task: 2517
- Original labels: `["defi"]`
- Audit labels: `["execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: Terra documentation describes an open-source blockchain with decentralized applications, an unparalleled DeFi experience, and algorithmic stablecoin mechanics, which fits the DeFi label.

The audit evidence summary was: Terra official docs describe Terra as an open-source blockchain hosting decentralized applications and providing a DeFi experience. The SEC amended complaint states that Terraform developed and marketed the Terraform blockchain and related protocols, launched Anchor Protocol, launched and maintained Mirror Protocol, controlled websites related to Mirror, and made mAssets available through a Terraform-controlled site where users could create, trade, or buy mAssets. The complaint also says Terraform created, offered, sold, and effected mAsset transactions through Mirror Protocol. No public evidence found in the reviewed sources supports OTC/block trading, algorithmic trading, market making/liquidity provision by Terraform itself, or any sub-fund/feeder/umbrella/SPV/fund platform capability.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because Terraform itself developed and marketed DeFi-native blockchain/protocol products, including Terra, Anchor Protocol, and Mirror Protocol, rather than merely investing in DeFi companies.|execution_services=yes because Terraform-controlled Mirror Protocol/web interfaces enabled users to create, trade, or buy mAssets and the SEC complaint says Terraform effected transactions through Mirror Protocol, crossing the DEX/trading venue execution threshold.

### 36. Kain Warick - 漏標 `market_making`, 漏標 `execution_services`

- Task: 9730
- Original labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: Synthetix describes itself as the first decentralized perpetual futures protocol, and official blog posts identify Kain Warwick as founder.

The audit evidence summary was: Public evidence appears to identify the input investor as Kain Warwick, with the input/CB Insights spelling variant Kain Warick. Official Infinex material identifies Kain Warwick as Infinex Founder and describes Infinex features for cross-chain swaps and access to DeFi/onchain protocols. Official Synthetix material identifies Kain Warwick as Founder of Synthetix, and Synthetix docs describe Synthetix as a DeFi derivatives liquidity protocol with liquidity providers, market makers, and a community market-making vault backing perps markets. No public evidence found for OTC/block/bilateral trading, algorithmic/quant/systematic/HFT trading, or sub-fund/feeder/SPV/fund-platform capability for the individual investor.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because official Synthetix and Infinex sources tie Kain Warwick to founder roles in DeFi/onchain protocols, not merely passive startup funding.|execution_services=yes because Infinex officially offers swap/bridge functionality and access to onchain protocols, and Synthetix is a trading/perps platform; exchange/swap venues meet the execution-services threshold.|market_making=yes because Synthetix official docs explicitly describe market makers/liquidity providers and a community-operated market-making vault backing perps markets, attributable through Kain Warwick's founder/co-founder/advisory relationship.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because official Synthetix and Infinex sources tie Kain Warwick to founder roles in DeFi/onchain protocols, not merely passive startup funding.|execution_services=yes because Infinex officially offers swap/bridge functionality and access to onchain protocols, and Synthetix is a trading/perps platform; exchange/swap venues meet the execution-services threshold.|market_making=yes because Synthetix official docs explicitly describe market makers/liquidity providers and a community-operated market-making vault backing perps markets, attributable through Kain Warwick's founder/co-founder/advisory relationship.

### 37. MetaStreet - 漏標 `execution_services`

- Task: 10561
- Original labels: `["defi"]`
- Audit labels: `["execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: MetaStreet's official site describes Yield Pass, Borrow, and a DeFi ecosystem; protocol docs describe permissionless pools for NFT collateral, fixed-duration loans, and liquidity routing.

The audit evidence summary was: MetaStreet's official site and docs describe a DeFi-oriented protocol/product suite for yield, borrowing, lending pools, Liquid Credit Tokens, and NFT/object collateral. The docs state that MetaStreet/Permian Labs develops DeFi primitives, that the ATM is a permissionless lending protocol, that borrowers accept aggregated loan offers, and that the Borrow interface lets holders use NFT/object collateral to take loans. Its technical docs also describe liquidity sourcing and tick routing by the MetaStreet SDK. No public evidence found for OTC/block trading, algorithmic or HFT trading, market making as a trading/AMM operator, or sub-fund/feeder/SPV/fund platform activity.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because MetaStreet itself operates and markets DeFi-native lending/yield infrastructure, including a permissionless lending protocol and composable ERC-20 credit tokens.|execution_services=yes because MetaStreet provides explicit liquidity access and routing for loan execution: borrowers accept aggregated offers through its Borrow interface, liquidity is sourced from ticks, and the MetaStreet SDK performs tick routing.

### 38. Chingari - 漏標 `defi`

- Task: 2819
- Original labels: `[]`
- Audit labels: `["defi"]`
- Manual review: yes
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: Chingari’s public site shows a short-video/live-audio app with live streaming and on-chain users; the blog also documents investor rounds, confirming the row is really describing an operating platform.

The audit evidence summary was: Chingari/GARI Network publicly markets and operates a Web3/on-chain creator economy with GARI token usage, on-chain users, GARI staking, DAO governance, NFT marketplace features, and wallet infrastructure. The key-features page states GARI holders can stake and earn yield and vote on proposals, while Chingari Wallet markets Web3 wallet, NFT, and staking services. I found no explicit evidence that Chingari itself provides OTC/block trading, algorithmic or quantitative trading, market making/liquidity provision, brokerage/order routing/liquidity access, or any sub-fund/feeder/umbrella/parallel fund/SPV/fund platform capability.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: defi crosses the threshold because Chingari itself, through GARI Network and Chingari Wallet, operates and markets DeFi-native staking/yield, DAO governance, token, NFT, and Web3 wallet capabilities rather than merely investing in DeFi companies.

### 39. Hawkwood Capital - 漏標 `sub_fund`

- Task: 8910
- Original labels: `[]`
- Audit labels: `["sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Current official/site and registry evidence identifies Hawkwood Capital LLP as an FCA-authorised boutique fund manager/adviser and active UK LLP. The current sources reviewed did not evidence OTC desks, algorithmic/systematic trading, market making/liquidity provision, execution services, DeFi-native activity, or current feeder/umbrella/parallel/SPV/fund-of-funds structure.

The audit evidence summary was: Hawkwood's official site describes the firm as an FCA-regulated boutique fund manager managing differentiated funds and also as a corporate advisory/capital-raising business. The Hawkwood Commodities Fund prospectus names Hawkwood Capital LLP as investment adviser to both the Fund and the Master Fund and contains explicit master/feeder-fund structure language. A Hawkwood Deep Value Fund application form also references the Fund, Master Fund, Investment Manager, and Administrator. I found no evidence that Hawkwood itself operates an OTC/block/bilateral trading desk, algorithmic/systematic/HFT trading platform, market-making or liquidity-provision business, order-execution/routing/prime brokerage service, or DeFi-native product/capability.

For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: sub_fund=yes because official Hawkwood fund documentation explicitly references a Fund/Master Fund structure and feeder-fund language, with Hawkwood Capital LLP appointed to provide investment advisory services to the Fund and Master Fund.

### 40. Ethan Francis - 漏標 `execution_services`, 漏標 `defi`

- Task: 8182
- Original labels: `[]`
- Audit labels: `["execution_services", "defi"]`
- Manual review: yes
- Likely root cause: narrow DEX/AMM capability mapping.

The original evidence summary was: 6DOS confirms the task-row biography of Ethan Francis as Founder and CEO of a B2B SaaS company. Current crypto sources show an Ethan Francis associated with Particle Network and a Web3 AI angel round, but the same-person link and investor capability boundary remain ambiguous. No evidence supports marking the investor record for OTC, algorithmic trading, market making, execution services, DeFi-native operation, or sub-fund structures.

The audit evidence summary was: The local input identifies Ethan Francis as an individual angel and Founder/CEO of 6DOS; 6DOS is described publicly as a relationship/SaaS software company and does not evidence trading, market making, DeFi, or fund-structure capabilities. Public Assisterr funding coverage identifies an angel named Ethan Francis as Head of Developer Relationships at Particle Network, and a secondary Particle profile identifies Ethan Francis as COO. Particle official documentation says UniversalX, built by Particle Network, is a non-custodial chain-agnostic trading platform that lets users trade tokens across chains, routes balances, and executes trades through Universal Accounts. Particle documentation also lists UniversalX under DeFi & Trading integrations. Because the capability attribution for this individual depends on the public Particle operating role matching this investor, manual review is recommended.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services=yes because Particle's official UniversalX documentation describes a non-custodial trading platform that routes user balances across chains and executes trades, which crosses the execution/trading venue threshold when attributed through Ethan Francis's reported COO/executive role.|defi=yes because Particle/UniversalX is an onchain, non-custodial Web3 trading product listed by Particle documentation under DeFi & Trading, and the public profile ties Ethan Francis to Particle in an executive operating role.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services=yes because Particle's official UniversalX documentation describes a non-custodial trading platform that routes user balances across chains and executes trades, which crosses the execution/trading venue threshold when attributed through Ethan Francis's reported COO/executive role.|defi=yes because Particle/UniversalX is an onchain, non-custodial Web3 trading product listed by Particle documentation under DeFi & Trading, and the public profile ties Ethan Francis to Particle in an executive operating role.

### 41. Sebastian Serrano - 漏標 `otc_trading`, 漏標 `market_making`, 漏標 `execution_services`, 漏標 `defi`

- Task: 12187
- Original labels: `[]`
- Audit labels: `["otc_trading", "market_making", "execution_services", "defi"]`
- Manual review: yes
- Likely root cause: narrow OTC-to-execution boundary mapping.

The original evidence summary was: Ripio’s official site identifies Sebastian Serrano as co-founder/CEO and advertises crypto exchange, OTC desk, crypto-as-a-service, DeFi access, and liquidity-provider services. Those capabilities belong to the company, so they are not mapped directly onto the individual investor row.

The audit evidence summary was: Official Ripio materials identify Sebastian Serrano as Co-founder & CEO of Ripio and managing partner at Ripio Ventures. Ripio's institutional and OTC pages describe an OTC desk for high-volume crypto/fiat trades, private-book trading, immediate liquidity, execution of large transactions, and crypto trading/custody. Ripio Select says it is focused on providing liquidity to institutional and high-net-worth clients. Ripio's DeFi page describes the Ripio DeFi feature enabling users to deposit and withdraw funds in Compound, Aave, and Yearn from Ripio Wallet. I found no explicit algorithmic, quantitative, systematic, HFT, low-latency trading evidence, and no feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

For `otc_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Ripio explicitly markets an OTC desk and OTC service for high-volume crypto/fiat trades.|market_making crosses the threshold because Ripio Select explicitly says the service is focused on providing liquidity, and the OTC materials describe immediate liquidity for institutional trading.|execution_services crosses the threshold because Ripio describes executing large transactions, private-book OTC trading, crypto trading/custody, and direct purchase/sale transactions through its OTC desk.|defi crosses the threshold because Ripio itself operates and markets Ripio DeFi, including access to DeFi protocols and deposits/withdrawals through Compound, Aave, and Yearn.
For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Ripio explicitly markets an OTC desk and OTC service for high-volume crypto/fiat trades.|market_making crosses the threshold because Ripio Select explicitly says the service is focused on providing liquidity, and the OTC materials describe immediate liquidity for institutional trading.|execution_services crosses the threshold because Ripio describes executing large transactions, private-book OTC trading, crypto trading/custody, and direct purchase/sale transactions through its OTC desk.|defi crosses the threshold because Ripio itself operates and markets Ripio DeFi, including access to DeFi protocols and deposits/withdrawals through Compound, Aave, and Yearn.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Ripio explicitly markets an OTC desk and OTC service for high-volume crypto/fiat trades.|market_making crosses the threshold because Ripio Select explicitly says the service is focused on providing liquidity, and the OTC materials describe immediate liquidity for institutional trading.|execution_services crosses the threshold because Ripio describes executing large transactions, private-book OTC trading, crypto trading/custody, and direct purchase/sale transactions through its OTC desk.|defi crosses the threshold because Ripio itself operates and markets Ripio DeFi, including access to DeFi protocols and deposits/withdrawals through Compound, Aave, and Yearn.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading crosses the threshold because Ripio explicitly markets an OTC desk and OTC service for high-volume crypto/fiat trades.|market_making crosses the threshold because Ripio Select explicitly says the service is focused on providing liquidity, and the OTC materials describe immediate liquidity for institutional trading.|execution_services crosses the threshold because Ripio describes executing large transactions, private-book OTC trading, crypto trading/custody, and direct purchase/sale transactions through its OTC desk.|defi crosses the threshold because Ripio itself operates and markets Ripio DeFi, including access to DeFi protocols and deposits/withdrawals through Compound, Aave, and Yearn.

### 42. Charles Read - 漏標 `market_making`, 漏標 `defi`

- Task: 2297
- Original labels: `[]`
- Audit labels: `["market_making", "defi"]`
- Manual review: no
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: LinkedIn, Coinspeaker, and Signal profiles tie Charles Read to Rarestone Capital and other blockchain advisory roles, indicating a crypto-native angel/investor profile but no trading or execution desk.

The audit evidence summary was: Rarestone's official team page identifies Charles Read as Founding Partner and says he heads strategy and go-to-market for the portfolio and Labs team. Rarestone Labs officially markets DeFi-relevant token economics/protocol design expertise and explicitly offers liquidity providing strategies for on-chain launches, including LP incentive campaigns and concentrated liquidity. Noir's profile further supports that Charles founded Rarestone, a blockchain venture firm. No evidence found for OTC/block/bilateral trading, algorithmic/quant/systematic/HFT trading, execution/order-routing/brokerage services, or sub-fund/feeder/umbrella/SPV/fund-of-funds activity.

For `market_making`, the original output likely missed a positive signal. The audit-side boundary note was: market_making=yes because Rarestone Labs explicitly markets liquidity providing strategies for on-chain launches, including LP incentive campaigns and concentrated liquidity, and Charles is explicitly tied to leading the Labs team.|defi=yes because Rarestone Labs explicitly markets DeFi-native protocol/token economics capability, stating its team has been at the forefront since the emergence of DeFi, and Charles is a founding partner tied to Labs leadership.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: market_making=yes because Rarestone Labs explicitly markets liquidity providing strategies for on-chain launches, including LP incentive campaigns and concentrated liquidity, and Charles is explicitly tied to leading the Labs team.|defi=yes because Rarestone Labs explicitly markets DeFi-native protocol/token economics capability, stating its team has been at the forefront since the emergence of DeFi, and Charles is a founding partner tied to Labs leadership.

### 43. Sanctor Capital - 漏標 `defi`, 漏標 `sub_fund`

- Task: 365
- Original labels: `[]`
- Audit labels: `["defi", "sub_fund"]`
- Manual review: no
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Official site shows a thesis-driven investment fund with pre-accelerator support and web3 mentorship.

The audit evidence summary was: Sanctor's official venture page describes the firm as a thesis-driven investment fund deploying capital across gaming, infrastructure, and DeFi in web3 at pre-seed and seed stages, which supports DeFi specialization/product exposure. A SEC Form D identifies Sanctor Capital Management, LLC as issuer manager for a pooled investment fund issuer named Sanctor Powerus I - Sanctor Master Series LLC, supporting a series/SPV-style fund vehicle. I found no explicit evidence that Sanctor itself operates OTC/block trading, algorithmic or quantitative trading, market making/liquidity provision, execution, routing, brokerage, prime brokerage, or liquidity-access services.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because Sanctor's own official site explicitly markets DeFi as one of the web3 areas where its investment fund deploys capital, not merely because of a portfolio-company investment.|sub_fund=yes because the SEC filing ties Sanctor Capital Management to a pooled investment issuer using a Master Series LLC structure, indicating a series/SPV-style vehicle rather than only a standard closed fund.
For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: defi=yes because Sanctor's own official site explicitly markets DeFi as one of the web3 areas where its investment fund deploys capital, not merely because of a portfolio-company investment.|sub_fund=yes because the SEC filing ties Sanctor Capital Management to a pooled investment issuer using a Master Series LLC structure, indicating a series/SPV-style vehicle rather than only a standard closed fund.

### 44. Gracy Chen - 漏標 `otc_trading`, 漏標 `algorithm_trading`, 漏標 `execution_services`, 漏標 `defi`

- Task: 4104
- Original labels: `[]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services", "defi"]`
- Manual review: no
- Likely root cause: narrow OTC-to-execution boundary mapping.

The original evidence summary was: Bitget's official about page and CEO announcement identify Gracy Chen as CEO and an early investor in Bitget Wallet; no separate trading or execution desk is claimed for the individual investor.

The audit evidence summary was: Official Bitget materials identify Gracy Chen as CEO, and a Bitget-issued PR says she became CEO in May 2024 after serving as Managing Director. Bitget operates an OTC product for over-the-counter fiat/crypto and crypto/fiat trading, with large-order trading, professional execution, deeper liquidity, and competitive quotes. Bitget also markets algorithm-driven bot copy trading and trading bots that execute preset buy/sell actions continuously. Bitget API documentation supports programmatic trading for spot, futures, copy trading, market makers, quantitative trading, and third-party platforms sharing Bitget liquidity. Bitget Onchain and Bitget Wallet documentation show on-chain token trading, DApp access, DeFi support, swaps, bridges, and multi-chain Web3 functionality. I found no explicit evidence that Gracy Chen or Bitget operates a market-making desk/liquidity pool as principal, and no sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

For `otc_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Bitget explicitly operates Bitget OTC, described as an over-the-counter trading platform for digital assets with large-order trading and professional execution.|algorithm_trading=yes because Bitget explicitly describes bot copy trading/trading bots as algorithm-driven, automated tools executing preset buy and sell actions continuously.|execution_services=yes because Bitget is an exchange platform with spot/futures trading, OTC professional execution, APIs for programmatic order placement, and liquidity access.|defi=yes because Bitget operates/markets Bitget Onchain and Bitget Wallet features for on-chain trading, DApp access, DeFi, swaps, bridges, and multi-chain Web3 use; Gracy Chen is explicitly CEO of Bitget.
For `algorithm_trading`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Bitget explicitly operates Bitget OTC, described as an over-the-counter trading platform for digital assets with large-order trading and professional execution.|algorithm_trading=yes because Bitget explicitly describes bot copy trading/trading bots as algorithm-driven, automated tools executing preset buy and sell actions continuously.|execution_services=yes because Bitget is an exchange platform with spot/futures trading, OTC professional execution, APIs for programmatic order placement, and liquidity access.|defi=yes because Bitget operates/markets Bitget Onchain and Bitget Wallet features for on-chain trading, DApp access, DeFi, swaps, bridges, and multi-chain Web3 use; Gracy Chen is explicitly CEO of Bitget.
For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Bitget explicitly operates Bitget OTC, described as an over-the-counter trading platform for digital assets with large-order trading and professional execution.|algorithm_trading=yes because Bitget explicitly describes bot copy trading/trading bots as algorithm-driven, automated tools executing preset buy and sell actions continuously.|execution_services=yes because Bitget is an exchange platform with spot/futures trading, OTC professional execution, APIs for programmatic order placement, and liquidity access.|defi=yes because Bitget operates/markets Bitget Onchain and Bitget Wallet features for on-chain trading, DApp access, DeFi, swaps, bridges, and multi-chain Web3 use; Gracy Chen is explicitly CEO of Bitget.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because Bitget explicitly operates Bitget OTC, described as an over-the-counter trading platform for digital assets with large-order trading and professional execution.|algorithm_trading=yes because Bitget explicitly describes bot copy trading/trading bots as algorithm-driven, automated tools executing preset buy and sell actions continuously.|execution_services=yes because Bitget is an exchange platform with spot/futures trading, OTC professional execution, APIs for programmatic order placement, and liquidity access.|defi=yes because Bitget operates/markets Bitget Onchain and Bitget Wallet features for on-chain trading, DApp access, DeFi, swaps, bridges, and multi-chain Web3 use; Gracy Chen is explicitly CEO of Bitget.

### 45. Keisuke Honda - 漏標 `sub_fund`

- Task: 2188
- Original labels: `[]`
- Audit labels: `["sub_fund"]`
- Manual review: no
- Likely root cause: classifier routing miss.

The classifier routed this row as `skip_candidate` with `capability_search_required=no`. Because the independent audit found `["sub_fund"]`, the miss likely began before the capability worker searched the row.

The original evidence summary was: Skipped: generic angel investor with no meaningful crypto-native signal.

The audit evidence summary was: Keisuke Honda's official site describes him as investing globally in startups and lists KSK Angel Fund and Dreamers Fund. X&'s official site describes a multi-fund investment platform with five funds and X&KSK associated with Keisuke Honda. A company press release identifies Honda as Co-Founder & General Partner of X&KSK and describes X&KSK I as an investment limited partnership. FinCity's profile names Honda as founder and states X& provides services for individuals establishing venture funds, including capital anchoring and fund management. No public evidence found that Honda or his attributable platforms operate OTC/block trading, algorithmic trading, market making, trading execution/order routing/brokerage, or DeFi-native products.

For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: sub_fund crosses the threshold because public sources explicitly connect Honda as founder/co-founder/general partner to X&KSK/X&, and a profile describes X& as providing venture-fund establishment, capital anchoring, and fund-management services, while the official X& site describes a multi-fund platform.

### 46. Sportzchain - 漏標 `execution_services`, 漏標 `defi`

- Task: 12543
- Original labels: `[]`
- Audit labels: `["execution_services", "defi"]`
- Manual review: no
- Likely root cause: classifier routing miss.

The classifier routed this row as `skip_candidate` with `capability_search_required=no`. Because the independent audit found `["execution_services", "defi"]`, the miss likely began before the capability worker searched the row.

The original evidence summary was: Skipped capability search; batch record only.

The audit evidence summary was: Sportzchain's official FAQ describes an operated fan-token platform where $SPN enables users to buy and sell sports/fan tokens, and says fans can buy and sell those tokens on Sportzchain's platform. Its official about page describes a web3 sports app, sports tokens, NFTs, GameFi, watch-to-earn, staking rewards, a planned proprietary exchange for trading sports tokens, and DeFi programs. Its official token page markets $SPN staking rewards. CoinMarketCap similarly describes Sportzchain as an engage-to-earn webDapp with buying sports tokens, staking APY, NFTs, GameFi, and fan-token redemption. I found no explicit evidence for OTC/block trading, algorithmic/quant/systematic trading, market making/liquidity provision, or sub-fund/feeder/SPV/fund-platform activity.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services crosses the threshold because Sportzchain itself operates or markets a token platform/venue where users can buy and sell sports/fan tokens; exchange or swap venues can support execution_services under the boundary rule.|defi crosses the threshold because Sportzchain itself markets DeFi-native/token product exposure including $SPN staking rewards and explicitly references DeFi programs on its official site.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services crosses the threshold because Sportzchain itself operates or markets a token platform/venue where users can buy and sell sports/fan tokens; exchange or swap venues can support execution_services under the boundary rule.|defi crosses the threshold because Sportzchain itself markets DeFi-native/token product exposure including $SPN staking rewards and explicitly references DeFi programs on its official site.

### 47. Alameda Research - 漏標 `defi`

- Task: 46
- Original labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Manual review: yes
- Likely root cause: DeFi specialization or product evidence missed.

The original evidence summary was: Historical sources and the court record describe Alameda as a quantitative trading firm, liquidity provider, and market maker with OTC activity; because the entity is defunct and the evidence base is historical, manual review is warranted.

The audit evidence summary was: Alameda crosses the OTC, algorithmic trading, market making, execution services, and DeFi thresholds. Public sources describe Alameda as operating an OTC desk and providing OTC liquidity, with an Alameda Head of OTC desk quoted on connecting to global clients and providing pricing. The SEC complaint states Alameda was often the Binance.US OTC Desk's only counterparty from May 2020 to February 2022. A transcribed Alameda pitch deck says Alameda provided exchange liquidity and serviced OTC trades 24/7, used algorithmic machine-learning-driven automatic trading systems, quoted buy and sell prices for market making, and used execution strategies. A profile reproducing Alameda's first-person description also references market-neutral algorithms, execution strategies, automated trading systems, OTC quoting, and market-making partnerships. Blockworks reports a Maple Finance loan product designed to provide institutional exposure to Alameda's DeFi trading yields, indicating Alameda's own DeFi-related trading/yield activity rather than only portfolio investment. I found no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: otc_trading=yes because sources explicitly identify Alameda's OTC desk/OTC business, OTC quotes, OTC liquidity provision, and counterparty role for Binance.US OTC trades.|algorithm_trading=yes because Alameda's materials explicitly cite algorithmic, machine-learning-driven automatic trading systems, market-neutral algorithms, quantitative strategies, and sophisticated automated trading systems.|market_making=yes because Alameda's materials explicitly describe market making, quoting buy and sell prices, market-making partnerships, and providing liquidity on exchanges.|execution_services=yes because Alameda's first-person profile explicitly cites execution strategies and its OTC client-facing quote/pricing/liquidity workflow supports execution of large crypto trades.|defi=yes because Blockworks describes institutional exposure to Alameda's DeFi trading yields from Alameda's own trading activities, not merely Alameda funding DeFi startups.

### 48. Bixin Ventures - 漏標 `execution_services`, 漏標 `defi`, 漏標 `sub_fund`

- Task: 112
- Original labels: `[]`
- Audit labels: `["execution_services", "defi", "sub_fund"]`
- Manual review: yes
- Likely root cause: fund-structure evidence not carried into sub_fund.

The original evidence summary was: Bixin Ventures presents itself as a venture investor in open-finance infrastructure, and its parent Bixin Group operates wallet and liquidity-provider businesses.

The audit evidence summary was: Bixin Ventures' official site identifies it as an investor in crypto networks and open financial systems and ties it to Bixin Group's operating crypto infrastructure. Bixin.com support documentation describes an exchange and off-platform system with explicit order placement and trade execution through liquidity providers, supporting execution_services for the attributable Bixin operating platform. Bixin Ventures announced a $100M proprietary fund for open finance/decentralized infrastructure, and reporting explicitly describes the fund as focused on scaling DeFi. Bixin Ventures/Bixin Global also announced a proprietary fund of funds, satisfying sub_fund. I did not find sufficient evidence that Bixin Ventures itself operates OTC trading, algorithmic trading, or market making.

For `execution_services`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services=yes because Bixin.com documentation explicitly describes exchange and off-platform trade execution, order placement, and execution through liquidity providers on the attributable Bixin operating platform.|defi=yes because Bixin Ventures explicitly launched capital focused on open finance through permissionless decentralized networks, with reporting describing the purpose as scaling decentralized finance.|sub_fund=yes because Bixin Ventures/Bixin Global explicitly announced a proprietary fund of funds.
For `defi`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services=yes because Bixin.com documentation explicitly describes exchange and off-platform trade execution, order placement, and execution through liquidity providers on the attributable Bixin operating platform.|defi=yes because Bixin Ventures explicitly launched capital focused on open finance through permissionless decentralized networks, with reporting describing the purpose as scaling decentralized finance.|sub_fund=yes because Bixin Ventures/Bixin Global explicitly announced a proprietary fund of funds.
For `sub_fund`, the original output likely missed a positive signal. The audit-side boundary note was: execution_services=yes because Bixin.com documentation explicitly describes exchange and off-platform trade execution, order placement, and execution through liquidity providers on the attributable Bixin operating platform.|defi=yes because Bixin Ventures explicitly launched capital focused on open finance through permissionless decentralized networks, with reporting describing the purpose as scaling decentralized finance.|sub_fund=yes because Bixin Ventures/Bixin Global explicitly announced a proprietary fund of funds.

## Practical Fixes Suggested By The Root Causes

1. Add a worker checklist: if `otc_trading=yes`, explicitly test whether the same evidence also implies `execution_services=yes`.
2. Add a DEX/AMM rule: if the entity operates a DEX, swap venue, or cross-chain trading product, test `execution_services=yes`; if it operates AMM/liquidity pools/liquidity mining, test `market_making=yes`.
3. Add a fund-structure search step for asset managers and PE/VC firms: search legal docs, filings, terms pages, and fund names for feeder, SPC, PCC, SPV, umbrella, series, master, and fund-of-funds.
4. Tighten `algorithm_trading` evidence standards for hedge funds: secondary strategy snippets should not be enough unless they explicitly say algorithmic, quantitative, systematic, HFT, low-latency, automated, TWAP/VWAP, bot, or similar.
5. Add an attribution flag for individuals and affiliated operators: platform capabilities attributed to a founder/chairman, group entity, or associated operator should usually set `needs_manual_review=yes`.
6. Revisit `skip_candidate` for traditional fund managers: even non-crypto PE/family-office records can have `sub_fund` structures, so skip logic should not exclude fund-vehicle checks solely because crypto/operating signals are low.
