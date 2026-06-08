# Part6 Random-93 GPT-5.5 High Capability Audit

## 生成資訊

- generated_at_utc: 2026-06-08T14:13:21.237960+00:00
- generated_at_los_angeles: 2026-06-08T07:13:21.237960-07:00
- base_sample_seed: 20260608
- add60_sample_seed: 20260668
- sample_size: 93
- subagent_model: gpt-5.5
- reasoning_effort: high
- execution_mode: max 5 concurrent fresh subagents; one investor per subagent; subagents only received the input row and search instructions, not the Part6 output rows.
- note: rows 1-30 are the original audit batch; rows 31-90 are the additional random-60 batch; rows 91-93 are targeted additions requested for Jump Crypto, Jump Trading, and Wintermute.

## 讀寫檔案

- Read: `part5_to_part6/output/part6_investor_input.csv`
- Read: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/results.csv`
- Read: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/classifier_results.csv`
- Read: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/needs_manual_review.csv`
- Read for original rules: `part6_analyse_investor_capabilities/agent_prompt_template.md`
- Read for original rules: `part6_analyse_investor_capabilities/Plan.md`
- Read for original rules: `part6_analyse_investor_capabilities/runtime/worker_base_template.md`
- Wrote: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/audit_random30_gpt55_high.csv`
- Wrote: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/audit_random30_gpt55_high.md`
- Wrote: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/mismatch_analysis.md`
- Wrote: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/original_label_root_cause.md`
- Stored raw add60 outputs: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/raw_add60_agent_outputs`
- Stored raw targeted add3 outputs: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/raw_add3_agent_outputs`

## 抽樣設計

本次是 audit sample，不是對全量 13,970 records 的統計外推。前 90 家由原始 30 家與新增 60 家組成，新增樣本排除已抽中的 30 家，仍從 positive capability、searched negative、skip candidate、manual-focused 幾類中分層抽取。第 91-93 家是 user-requested targeted comparison：Jump Crypto、Jump Trading、Wintermute。目的仍是檢查能力標籤漏標、誤標與分類器跳過風險。

| sample_stratum | count |
| --- | --- |
| manual_focused | 6 |
| positive_algorithm_trading | 6 |
| positive_fill | 21 |
| positive_manual_boost | 3 |
| positive_market_making | 6 |
| positive_otc_trading | 9 |
| positive_sub_fund | 9 |
| searched_negative_full | 9 |
| searched_negative_light | 9 |
| skip_candidate | 12 |
| targeted_addition | 3 |

## 核心結論

- 六個能力完全一致: 43/93
- 至少一個能力不一致: 50/93
- 不一致且已在 `needs_manual_review.csv`: 8/50
- 不一致但不在 `needs_manual_review.csv`: 42/50
- classifier/routing concern: 3 sampled rows

| capability | results_yes | audit_yes | mismatch_count | results_no_audit_yes | results_yes_audit_no |
| --- | --- | --- | --- | --- | --- |
| otc_trading | 22 | 27 | 5 | 5 | 0 |
| algorithm_trading | 21 | 30 | 11 | 10 | 1 |
| market_making | 16 | 33 | 17 | 17 | 0 |
| execution_services | 24 | 42 | 18 | 18 | 0 |
| defi | 23 | 46 | 23 | 23 | 0 |
| sub_fund | 15 | 22 | 15 | 11 | 4 |

## 不一致公司與 Manual Review 狀態

下表直接回答不一致公司是否在 `needs_manual_review.csv`。

| task | investor | in_needs_manual_review | mismatched_capabilities | results_labels | audit_labels | classifier_search_tier | classifier_required | classifier_issue |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3298 | YAY Network | yes | execution_services | ["otc_trading", "defi"] | ["otc_trading", "execution_services", "defi"] | full | yes |  |
| 6538 | Belobaba Fund | no | sub_fund | ["otc_trading", "execution_services", "defi"] | ["otc_trading", "execution_services", "defi", "sub_fund"] | full | yes |  |
| 751 | Great South Gate Asset Management | no | sub_fund | ["algorithm_trading", "execution_services"] | ["algorithm_trading", "execution_services", "sub_fund"] | full | yes |  |
| 11089 | North Rock Digital | no | algorithm_trading | ["algorithm_trading"] | [] | full | yes |  |
| 4598 | RedLine Capital | no | sub_fund | ["algorithm_trading", "market_making"] | ["algorithm_trading", "market_making", "sub_fund"] | full | yes |  |
| 23 | Genblock Capital | no | defi | ["market_making"] | ["market_making", "defi"] | full | yes |  |
| 1942 | A+ Ventures | no | sub_fund | ["sub_fund"] | [] | full | yes |  |
| 10739 | MochiLab | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | full | yes |  |
| 1543 | BitGo | no | algorithm_trading\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services", "defi"] | full | yes |  |
| 9515 | Jesse Powell | no | algorithm_trading\|market_making | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | full | yes |  |
| 5778 | Ace Exchange | no | algorithm_trading | ["execution_services"] | ["algorithm_trading", "execution_services"] | full | yes |  |
| 12479 | SOMESING (Social/Platform Software) | no | defi | [] | ["defi"] | full | yes |  |
| 4 | Exnetwork Capital | no | otc_trading | [] | ["otc_trading"] | light | yes |  |
| 4883 | Vision Capital | no | sub_fund | [] | ["sub_fund"] | skip_candidate | no | skip_candidate_but_independent_audit_found_capability\|capability_search_required_no_but_independent_audit_found_capability |
| 3428 | Sentillia | yes | algorithm_trading | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services"] | full | yes |  |
| 4475 | OccamDAO | yes | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | full | yes |  |
| 4383 | MHC Digital Group | no | market_making\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 12087 | Samuel Bankman-Fried | no | execution_services | ["otc_trading", "algorithm_trading", "market_making", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 11292 | Pantronics Holdings | no | algorithm_trading\|defi\|sub_fund | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services", "defi", "sub_fund"] | full | yes |  |
| 10747 | Mohamed Jezri Mohideen | no | execution_services\|defi\|sub_fund | ["otc_trading", "algorithm_trading", "market_making"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"] | full | yes |  |
| 1071 | Jane Street | no | defi | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 101 | Amber Group | no | defi | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 4242 | Joseph Jones | no | execution_services\|sub_fund | ["sub_fund"] | ["execution_services"] | full | yes |  |
| 3891 | Coven | no | defi\|sub_fund | ["sub_fund"] | ["defi"] | full | yes |  |
| 12072 | Samara Alpha Management | no | market_making\|defi | ["algorithm_trading", "sub_fund"] | ["algorithm_trading", "market_making", "defi", "sub_fund"] | full | yes |  |
| 13058 | Tikhon Bernstam | no | sub_fund | ["sub_fund"] | [] | full | yes |  |
| 11229 | OrangeX | no | market_making | ["execution_services"] | ["market_making", "execution_services"] | full | yes |  |
| 6648 | BitFlyer | no | otc_trading\|algorithm_trading\|market_making | ["execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | full | yes |  |
| 3269 | UniLend Finance | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | full | yes |  |
| 1595 | Mow capital | no | algorithm_trading | ["market_making"] | ["algorithm_trading", "market_making"] | full | yes |  |
| 10194 | LTP (Singapore) | no | algorithm_trading\|market_making\|defi\|sub_fund | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"] | full | yes |  |
| 7 | LD Capital | no | market_making | ["sub_fund"] | ["market_making", "sub_fund"] | full | yes |  |
| 3039 | Mars Ecosystem | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | full | yes |  |
| 2410 | Kraken | no | algorithm_trading\|market_making\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 2517 | Terraform Labs | no | execution_services | ["defi"] | ["execution_services", "defi"] | full | yes |  |
| 9730 | Kain Warick | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | full | yes |  |
| 10561 | MetaStreet | no | execution_services | ["defi"] | ["execution_services", "defi"] | full | yes |  |
| 2819 | Chingari | yes | defi | [] | ["defi"] | full | yes |  |
| 8910 | Hawkwood Capital | no | sub_fund | [] | ["sub_fund"] | full | yes |  |
| 8182 | Ethan Francis | yes | execution_services\|defi | [] | ["execution_services", "defi"] | full | yes |  |
| 12187 | Sebastian Serrano | yes | otc_trading\|market_making\|execution_services\|defi | [] | ["otc_trading", "market_making", "execution_services", "defi"] | light | yes |  |
| 2297 | Charles Read | no | market_making\|defi | [] | ["market_making", "defi"] | light | yes |  |
| 365 | Sanctor Capital | no | defi\|sub_fund | [] | ["defi", "sub_fund"] | light | yes |  |
| 4104 | Gracy Chen | no | otc_trading\|algorithm_trading\|execution_services\|defi | [] | ["otc_trading", "algorithm_trading", "execution_services", "defi"] | light | yes |  |
| 2188 | Keisuke Honda | no | sub_fund | [] | ["sub_fund"] | skip_candidate | no | skip_candidate_but_independent_audit_found_capability\|capability_search_required_no_but_independent_audit_found_capability |
| 12543 | Sportzchain | no | execution_services\|defi | [] | ["execution_services", "defi"] | skip_candidate | no | skip_candidate_but_independent_audit_found_capability\|capability_search_required_no_but_independent_audit_found_capability |
| 46 | Alameda Research | yes | defi | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 112 | Bixin Ventures | yes | execution_services\|defi\|sub_fund | [] | ["execution_services", "defi", "sub_fund"] | full | yes |  |
| 94 | Jump Crypto | no | market_making\|execution_services\|defi | ["algorithm_trading"] | ["algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |
| 1030 | Jump Trading | no | otc_trading\|market_making\|execution_services\|defi | ["algorithm_trading"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | full | yes |  |

## Classifier 對照觀察

以下 row 出現明確 routing concern：分類器判為 `skip_candidate` 或 `capability_search_required=no`，但獨立審核搜索到至少一個能力為 Yes。

| task | investor | classifier_search_tier | classifier_required | audit_labels | in_needs_manual_review | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 4883 | Vision Capital | skip_candidate | no | ["sub_fund"] | no | Private equity firm with no explicit crypto-native, trading, execution, DeFi, or fund-vehicle language in the row. |
| 2188 | Keisuke Honda | skip_candidate | no | ["sub_fund"] | no | Generic angel investor profile with no crypto-native or operating-capability signal. |
| 12543 | Sportzchain | skip_candidate | no | ["execution_services", "defi"] | no | Blockchain-powered operating company with M&A posture and no explicit trading, execution, market-making, DeFi, or fund-structure signal. |

其餘不一致大多發生在已被分類器送入 `full` 或 `light` 搜索的 records，較像能力判定邊界、來源深度或 attribution interpretation 問題，而不是單純分類器跳過問題。

## 六個能力定義與邊界

以下定義以 Part6 原始提示詞/計劃中的規則為基礎重述：能力必須由 investor/entity 自身或可歸屬的 operating platform 證據支持；投資組合曝光、泛泛行業描述或普通基金資料不夠。

### otc_trading

- Rule: 只有在明確證據顯示該 investor/entity 自身提供或運營 OTC desk、block trading、大宗/雙邊場外交易、RFQ/場外流動性服務時標 Yes。
- Yes boundary: 官方或可靠資料明確描述 OTC desk、場外大宗撮合、block trade API、crypto-fiat/crypto-crypto OTC trading desk，即使透過可歸屬的關聯交易平台運營也可標 Yes。
- No boundary: 只投資交易所、只提到二級市場投資、只買賣 OTC-listed public companies、只有一般 token allocation/SAFT、顧問或投資人關係，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | OTC desk/liquidity service, HFT/quant algorithms, liquidity provision, API/FIX execution, and DeFi venture support are explicit. |
| YAY Network | Official OTC marketplace crosses OTC/execution boundary; farming/staking/NFT DeFi docs cross DeFi boundary. |
| Belobaba Fund | OTC trading desk; direct execution; master-feeder/PCC/feeder/SPV; DeFi-linked token ecosystem. |
| BitGo | OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit. |
| Jesse Powell | Founder/chairman linkage to Kraken used for OTC/API/market-structure/execution capability. |
| Exnetwork Capital | Explicit OTC Room/OTC desk evidence supports otc_trading. |
| Sentillia | Block trading supports OTC; API/FIX and mass quotes support execution/algorithmic capabilities. |
| MHC Digital Group | otc_trading crosses the threshold because MHC explicitly markets an institutional-grade OTC desk and official OTC trading terms. |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| Genblock Capital | Secondary-market investing does not prove OTC desk. |
| Nural Capital | Blockchain/DeFi investment exposure is not DeFi operation. |
| FiveT Group | Portfolio-company OTC/market-making/execution evidence is not FiveT's own capability. |
| Ace Exchange | Third-party OTC label without official OTC desk detail is insufficient. |
| RB Capital Partners (San Diego) | Trading OTC-listed securities is not an OTC desk/block trading service; private investment fund alone is not sub_fund. |
| DCU FinTech Innovation Center | Startup ecosystem/blockchain exposure is not DeFi operation or trading capability. |
| Vision Capital | Private company acquisitions are not OTC trading services. |
| BR Capital | otc_trading=no because I found no explicit OTC desk, block trading, or bilateral trading evidence for BR Capital. |

### algorithm_trading

- Rule: 只有在明確證據顯示 algorithmic、quantitative、systematic、HFT、low-latency、automated trading strategy，或明確 algorithmic execution/交易機器人能力時標 Yes。
- Yes boundary: 量化團隊、系統化策略、stat arb/CTA、HFT/低延遲交易、TWAP/VWAP、交易 bot、自動化策略，或交易平台明確提供可自動化交易能力並與 entity 運營身份相連時，標 Yes。
- No boundary: 泛泛 API、研究文章、教育內容、普通 hedge fund/VC 策略、DeFi AMM 曲線本身，或二級資料不能確認 entity 自身能力，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | OTC desk/liquidity service, HFT/quant algorithms, liquidity provision, API/FIX execution, and DeFi venture support are explicit. |
| Great South Gate Asset Management | Systematic strategy language supports algorithm_trading; brokerage/trade lifecycle supports execution_services; SPC/feeder supports sub_fund. |
| RedLine Capital | Explicit quantitative team and market maker services cross algorithm/market_making; six sub-funds cross sub_fund. |
| BitGo | OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit. |
| Ace Exchange | Official AI/grid trading robot supports algorithm_trading; exchange order-book supports execution_services. |
| Sentillia | Block trading supports OTC; API/FIX and mass quotes support execution/algorithmic capabilities. |
| Samuel Bankman-Fried | otc_trading crosses the threshold because public evidence explicitly says Bankman-Fried designed an automated OTC-trading system at Jane Street, and the FTX platform he controlled also operated an OTC portal for direct quote-based trades. |
| Pantronics Holdings | algorithm_trading crosses the threshold because the annual report explicitly identifies quantitative products and quantitative trading strategies including fee arbitrage and basis arbitrage. |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| Belobaba Fund | Education about algorithmic/HFT and market-making allocation do not prove those services. |
| North Rock Digital | Secondary strategy snippets without primary capability evidence are insufficient for algorithm_trading; managed hedge fund alone is not sub_fund. |
| MochiLab | AMM mechanics are not algorithmic/HFT trading service. |
| Petros Bozatzis | Board/advisor exposure to an exchange is not investor-itself execution or algorithmic trading capability. |
| Hdac Technology | Consensus algorithms and asset exchange modules are not algorithmic trading or execution_services under the strict trading-service definition. |
| OccamDAO | AMM mechanics are not algorithmic/HFT trading; staking/ISPO pools are not sub_fund. |
| MHC Digital Group | General mentions of algorithmic traders, HFT, dynamic spread adjustment, or arbitrage in MHC educational articles were not attributed to MHC's own trading capability, so algorithm_trading remains no. |
| Anand Gomes | algorithm_trading is no: API/automation and references to systematic users are not explicit evidence that Anand Gomes or Paradigm operates algorithmic, quantitative, systematic, HFT, or low-latency trading. |

### market_making

- Rule: 只有在明確證據顯示該 investor/entity 自身提供 market making、liquidity provision、token liquidity services，或運營 DeFi AMM/流動性池協議時標 Yes。
- Yes boundary: 明確聲稱為項目提供做市/流動性、運營 AMM/DEX liquidity pool、提供 protocol/token liquidity support，可標 Yes。
- No boundary: 交易所 maker/taker fee、使用外部 market makers、投資或合作對象有做市能力、tokenomics 裡預留 market-making allocation、一般 secondary-market trading，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | OTC desk/liquidity service, HFT/quant algorithms, liquidity provision, API/FIX execution, and DeFi venture support are explicit. |
| RedLine Capital | Explicit quantitative team and market maker services cross algorithm/market_making; six sub-funds cross sub_fund. |
| MochiLab | AMM/liquidity solution supports protocol-level market_making; decentralized exchange supports execution_services; DeFi-native product supports DeFi. |
| OccamDAO | DEX liquidity pools support market_making; DEX trading infrastructure supports execution_services; DeFi suite supports DeFi. |
| Samuel Bankman-Fried | market_making crosses the threshold because Alameda, under Bankman-Fried's ownership/control, was explicitly described as a primary market maker and liquidity provider on FTX. |
| Nonco | market_making crosses the threshold because Nonco explicitly markets Market Making and third-party sources state it operates as a market maker and provides liquidity. |
| Mohamed Jezri Mohideen | algorithm_trading crosses the threshold because Laser Digital explicitly describes quant-driven liquidity provision and systematic trading. |
| BR Capital | market_making=yes because BR Capital explicitly markets market-making and separately states on its official site that it provides liquidity through trading and staking activities in CeFi and DeFi. |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| YAY Network | Tokenomics market-making allocation is not YAY providing market making. |
| BitGo | Aggregating external liquidity providers/market makers is not self market_making. |
| Sentillia | Tools for market makers are not Deribit itself market-making. |
| Pantronics Holdings | market_making is not marked yes because the only explicit market making/liquidity provision language found is framed as future customized quantitative solutions, not an operated current capability. |
| Anand Gomes | market_making is no: Paradigm connects users with market makers/liquidity providers, but its FAQ explicitly says Paradigm is not a market-maker and does not trade for its own account. |
| Vilas Capital Management | market_making=no because there is no evidence Vilas Capital makes markets or provides liquidity. |
| Joseph Jones | Buying GOXBTC and operating a trading platform are not explicit market making or liquidity provision evidence. |
| Coven | market_making=no: no explicit Coven market making or liquidity provision evidence. |

### execution_services

- Rule: 只有在明確證據顯示 brokerage、prime brokerage、exchange/DEX execution venue、order routing、smart order routing、FIX/API execution、liquidity access 或交易執行平台/服務時標 Yes。
- Yes boundary: OTC/DEX/exchange 能讓客戶買賣/下單、API/FIX 交易接入、broker-facilitated allocations、order execution lifecycle、SOR/prime brokerage/liquidity access，標 Yes。
- No boundary: 投資顧問、上市/交易所關係介紹、普通資產管理交易、小微盤融資交易，或投資/顧問關係未證明 entity 運營交易執行服務，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | OTC desk/liquidity service, HFT/quant algorithms, liquidity provision, API/FIX execution, and DeFi venture support are explicit. |
| YAY Network | Official OTC marketplace crosses OTC/execution boundary; farming/staking/NFT DeFi docs cross DeFi boundary. |
| Belobaba Fund | OTC trading desk; direct execution; master-feeder/PCC/feeder/SPV; DeFi-linked token ecosystem. |
| Great South Gate Asset Management | Systematic strategy language supports algorithm_trading; brokerage/trade lifecycle supports execution_services; SPC/feeder supports sub_fund. |
| MochiLab | AMM/liquidity solution supports protocol-level market_making; decentralized exchange supports execution_services; DeFi-native product supports DeFi. |
| BitGo | OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit. |
| Jesse Powell | Founder/chairman linkage to Kraken used for OTC/API/market-structure/execution capability. |
| Ace Exchange | Official AI/grid trading robot supports algorithm_trading; exchange order-book supports execution_services. |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| RedLine Capital | Exchange-listing help and relationships are not execution_services. |
| FiveT Group | Portfolio-company OTC/market-making/execution evidence is not FiveT's own capability. |
| Eric Dadoun | DeFi access/yield interface is not brokerage/order-routing execution service. |
| SOMESING (Social/Platform Software) | Exchange listings and token migration are not execution_services. |
| Petros Bozatzis | Board/advisor exposure to an exchange is not investor-itself execution or algorithmic trading capability. |
| JobsOhio Ventures | Sidecar/co-investment capital is venture financing, not execution/trading; evergreen subsidiary status is not sub_fund. |
| Hdac Technology | Consensus algorithms and asset exchange modules are not algorithmic trading or execution_services under the strict trading-service definition. |
| BR Capital | execution_services=no because liquidity provision and trading activity are not enough without explicit execution, order routing, brokerage, prime brokerage, or liquidity-access services offered by BR Capital. |

### defi

- Rule: 只有在 investor/entity 自身運營、創立、專注、支持或明確市場化 DeFi-native protocol/product/capability 時標 Yes；僅投資 DeFi startup 不足以標 Yes。
- Yes boundary: DeFi protocol、DEX、staking/farming/yield、stablecoin DeFi product、DeFi governance/support specialization、個人 founder/operator 與 DeFi 產品直接相連，可標 Yes。
- No boundary: 投資組合或合作伙伴涉及 Web3/DeFi、研究/投資主題提到 DeFi、普通區塊鏈平台或消費 app 沒有 DeFi 產品，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | OTC desk/liquidity service, HFT/quant algorithms, liquidity provision, API/FIX execution, and DeFi venture support are explicit. |
| YAY Network | Official OTC marketplace crosses OTC/execution boundary; farming/staking/NFT DeFi docs cross DeFi boundary. |
| Belobaba Fund | OTC trading desk; direct execution; master-feeder/PCC/feeder/SPV; DeFi-linked token ecosystem. |
| Genblock Capital | Explicit market-making help crosses market_making; explicit DeFi focus crosses the audit DeFi specialization boundary. |
| Eric Dadoun | Founder/operator of DeFi-native product supports DeFi for an individual investor. |
| babybera | Official staking/farming/bond products support DeFi. |
| MochiLab | AMM/liquidity solution supports protocol-level market_making; decentralized exchange supports execution_services; DeFi-native product supports DeFi. |
| BitGo | OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit. |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| Great South Gate Asset Management | DeFi exposure is investment/research, not operated DeFi product. |
| A+ Ventures | Web3 incubation and funding token projects are not enough for DeFi or sub_fund. |
| Nural Capital | Blockchain/DeFi investment exposure is not DeFi operation. |
| NEOM Investment Fund | Web3 partnership/investment is not NIF-operated DeFi. |
| Jesse Powell | Kraken/Powell crypto exposure and staking are not DeFi operation; individual angel status is not sub_fund. |
| Kraynos Capital Management | DeFi investment focus/portfolio exposure is not DeFi operation; ordinary VC fund is not sub_fund. |
| DCU FinTech Innovation Center | Startup ecosystem/blockchain exposure is not DeFi operation or trading capability. |
| Exnetwork Capital | Portfolio exposure to market-making/DeFi companies is not Exnetwork's own capability. |

### sub_fund

- Rule: 只有在明確證據顯示 feeder、umbrella、parallel fund、SPV、series/sub-fund、fund platform、fund-of-funds、protected cell/PCC/SPC、或類似多層/子基金/投資載體結構時標 Yes。
- Yes boundary: 明確 fund of funds、SPV、feeder/master-feeder、protected cell、umbrella fund、parallel fund、series/sub-fund、由該 investor 設立的專門 LP/fund vehicle，標 Yes。
- No boundary: 普通單一基金、基金名稱、投資多家公司、多個 portfolio、普通 syndicate 或 incubator program，沒有明確 vehicle/feeder/SPV/FOF 結構時標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Belobaba Fund | OTC trading desk; direct execution; master-feeder/PCC/feeder/SPV; DeFi-linked token ecosystem. |
| Great South Gate Asset Management | Systematic strategy language supports algorithm_trading; brokerage/trade lifecycle supports execution_services; SPC/feeder supports sub_fund. |
| RedLine Capital | Explicit quantitative team and market maker services cross algorithm/market_making; six sub-funds cross sub_fund. |
| Nural Capital | Explicit crypto fund-of-funds supports sub_fund. |
| FiveT Group | Dedicated fund platform/fund-family structure supports sub_fund. |
| NEOM Investment Fund | Input Fund of Funds classification supports sub_fund under the current audit definition. |
| Vision Capital | Explicit feeder LP/master/fund-of-funds evidence supports sub_fund. |
| Pantronics Holdings | sub_fund crosses the threshold because the annual report explicitly names controlled sub-funds and segregated portfolio structures, including Sinohope Delta Neutral Quant Arbitrage Sub-fund. |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| Wintermute Ventures | Investing proprietary/own capital as a venture arm is not sub_fund. |
| North Rock Digital | Secondary strategy snippets without primary capability evidence are insufficient for algorithm_trading; managed hedge fund alone is not sub_fund. |
| A+ Ventures | Web3 incubation and funding token projects are not enough for DeFi or sub_fund. |
| Jesse Powell | Kraken/Powell crypto exposure and staking are not DeFi operation; individual angel status is not sub_fund. |
| Kraynos Capital Management | DeFi investment focus/portfolio exposure is not DeFi operation; ordinary VC fund is not sub_fund. |
| RB Capital Partners (San Diego) | Trading OTC-listed securities is not an OTC desk/block trading service; private investment fund alone is not sub_fund. |
| Kronos Investment Group | Ordinary real-estate funds and portfolio exposure are not sub_fund or DeFi/trading capabilities. |
| JobsOhio Ventures | Sidecar/co-investment capital is venture financing, not execution/trading; evergreen subsidiary status is not sub_fund. |

## Full 93-Company Sample

| order | task | investor | stratum | manual_review | exact_match | mismatches | results_labels | audit_labels | audit_confidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 133 | Wintermute Ventures | positive_otc_trading | yes | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | medium |
| 2 | 3298 | YAY Network | positive_otc_trading | yes | no | execution_services | ["otc_trading", "defi"] | ["otc_trading", "execution_services", "defi"] | high |
| 3 | 6538 | Belobaba Fund | positive_otc_trading | no | no | sub_fund | ["otc_trading", "execution_services", "defi"] | ["otc_trading", "execution_services", "defi", "sub_fund"] | medium |
| 4 | 751 | Great South Gate Asset Management | positive_algorithm_trading | no | no | sub_fund | ["algorithm_trading", "execution_services"] | ["algorithm_trading", "execution_services", "sub_fund"] | medium |
| 5 | 11089 | North Rock Digital | positive_algorithm_trading | no | no | algorithm_trading | ["algorithm_trading"] | [] | medium |
| 6 | 4598 | RedLine Capital | positive_market_making | no | no | sub_fund | ["algorithm_trading", "market_making"] | ["algorithm_trading", "market_making", "sub_fund"] | medium |
| 7 | 23 | Genblock Capital | positive_market_making | no | no | defi | ["market_making"] | ["market_making", "defi"] | medium |
| 8 | 1942 | A+ Ventures | positive_sub_fund | no | no | sub_fund | ["sub_fund"] | [] | medium |
| 9 | 2073 | Nural Capital | positive_sub_fund | no | yes |  | ["sub_fund"] | ["sub_fund"] | medium |
| 10 | 8381 | FiveT Group | positive_sub_fund | no | yes |  | ["sub_fund"] | ["sub_fund"] | high |
| 11 | 8146 | Eric Dadoun | positive_fill | no | yes |  | ["defi"] | ["defi"] | medium |
| 12 | 6434 | babybera | positive_fill | no | yes |  | ["defi"] | ["defi"] | high |
| 13 | 5242 | NEOM Investment Fund | positive_fill | no | yes |  | ["sub_fund"] | ["sub_fund"] | medium |
| 14 | 10739 | MochiLab | positive_fill | no | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | medium |
| 15 | 1543 | BitGo | positive_fill | no | no | algorithm_trading\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services", "defi"] | high |
| 16 | 9515 | Jesse Powell | positive_fill | no | no | algorithm_trading\|market_making | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | medium |
| 17 | 5778 | Ace Exchange | positive_fill | no | no | algorithm_trading | ["execution_services"] | ["algorithm_trading", "execution_services"] | medium |
| 18 | 1785 | Kraynos Capital Management | searched_negative_full | no | yes |  | [] | [] | medium |
| 19 | 12479 | SOMESING (Social/Platform Software) | searched_negative_full | no | no | defi | [] | ["defi"] | medium |
| 20 | 11790 | RB Capital Partners (San Diego) | searched_negative_full | no | yes |  | [] | [] | high |
| 21 | 13960 | Petros Bozatzis | searched_negative_light | no | yes |  | [] | [] | medium |
| 22 | 7706 | DCU FinTech Innovation Center | searched_negative_light | no | yes |  | [] | [] | high |
| 23 | 4 | Exnetwork Capital | searched_negative_light | no | no | otc_trading | [] | ["otc_trading"] | medium |
| 24 | 4883 | Vision Capital | skip_candidate | no | no | sub_fund | [] | ["sub_fund"] | medium |
| 25 | 9935 | Kronos Investment Group | skip_candidate | no | yes |  | [] | [] | high |
| 26 | 13894 | JobsOhio Ventures | skip_candidate | no | yes |  | [] | [] | high |
| 27 | 5054 | XTech Ventures | skip_candidate | no | yes |  | [] | [] | high |
| 28 | 3428 | Sentillia | manual_focused | yes | no | algorithm_trading | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services"] | high |
| 29 | 8917 | Hdac Technology | manual_focused | yes | yes |  | ["defi"] | ["defi"] | medium |
| 30 | 4475 | OccamDAO | positive_manual_boost | yes | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | medium |
| 31 | 4383 | MHC Digital Group | positive_otc_trading | no | no | market_making\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "market_making", "execution_services", "defi"] | medium |
| 32 | 12087 | Samuel Bankman-Fried | positive_otc_trading | no | no | execution_services | ["otc_trading", "algorithm_trading", "market_making", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 33 | 11292 | Pantronics Holdings | positive_otc_trading | no | no | algorithm_trading\|defi\|sub_fund | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services", "defi", "sub_fund"] | high |
| 34 | 6104 | Anand Gomes | positive_otc_trading | no | yes |  | ["otc_trading", "execution_services", "defi"] | ["otc_trading", "execution_services", "defi"] | high |
| 35 | 11080 | Nonco | positive_otc_trading | no | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 36 | 10747 | Mohamed Jezri Mohideen | positive_otc_trading | no | no | execution_services\|defi\|sub_fund | ["otc_trading", "algorithm_trading", "market_making"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"] | high |
| 37 | 173 | BR Capital | positive_algorithm_trading | no | yes |  | ["algorithm_trading", "market_making", "defi", "sub_fund"] | ["algorithm_trading", "market_making", "defi", "sub_fund"] | high |
| 38 | 13444 | Vilas Capital Management | positive_algorithm_trading | no | yes |  | ["algorithm_trading"] | ["algorithm_trading"] | medium |
| 39 | 409 | Caladan | positive_algorithm_trading | no | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 40 | 3914 | CyberX | positive_algorithm_trading | no | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 41 | 7352 | Consensus Technologies | positive_market_making | no | yes |  | ["algorithm_trading", "market_making", "execution_services"] | ["algorithm_trading", "market_making", "execution_services"] | medium |
| 42 | 1071 | Jane Street | positive_market_making | no | no | defi | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 43 | 101 | Amber Group | positive_market_making | no | no | defi | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 44 | 2348 | Enflux (Dubai) | positive_market_making | no | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 45 | 4242 | Joseph Jones | positive_sub_fund | no | no | execution_services\|sub_fund | ["sub_fund"] | ["execution_services"] | medium |
| 46 | 3891 | Coven | positive_sub_fund | no | no | defi\|sub_fund | ["sub_fund"] | ["defi"] | medium |
| 47 | 3837 | Chainview Capital | positive_sub_fund | no | yes |  | ["algorithm_trading", "sub_fund"] | ["algorithm_trading", "sub_fund"] | medium |
| 48 | 12072 | Samara Alpha Management | positive_sub_fund | no | no | market_making\|defi | ["algorithm_trading", "sub_fund"] | ["algorithm_trading", "market_making", "defi", "sub_fund"] | medium |
| 49 | 5073 | PROOF | positive_sub_fund | no | yes |  | ["sub_fund"] | ["sub_fund"] | high |
| 50 | 4969 | OurCrowd | positive_sub_fund | no | yes |  | ["sub_fund"] | ["sub_fund"] | high |
| 51 | 13058 | Tikhon Bernstam | positive_fill | no | no | sub_fund | ["sub_fund"] | [] | medium |
| 52 | 11229 | OrangeX | positive_fill | no | no | market_making | ["execution_services"] | ["market_making", "execution_services"] | medium |
| 53 | 7131 | Charlie Karaboga | positive_fill | no | yes |  | ["otc_trading", "execution_services", "defi"] | ["otc_trading", "execution_services", "defi"] | high |
| 54 | 6648 | BitFlyer | positive_fill | no | no | otc_trading\|algorithm_trading\|market_making | ["execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | high |
| 55 | 3269 | UniLend Finance | positive_fill | no | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | high |
| 56 | 5845 | AFM Ventures | positive_fill | no | yes |  | ["sub_fund"] | ["sub_fund"] | high |
| 57 | 1595 | Mow capital | positive_fill | no | no | algorithm_trading | ["market_making"] | ["algorithm_trading", "market_making"] | high |
| 58 | 10194 | LTP (Singapore) | positive_fill | no | no | algorithm_trading\|market_making\|defi\|sub_fund | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"] | high |
| 59 | 7 | LD Capital | positive_fill | no | no | market_making | ["sub_fund"] | ["market_making", "sub_fund"] | medium |
| 60 | 3039 | Mars Ecosystem | positive_fill | no | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | high |
| 61 | 2410 | Kraken | positive_fill | no | no | algorithm_trading\|market_making\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 62 | 2517 | Terraform Labs | positive_fill | no | no | execution_services | ["defi"] | ["execution_services", "defi"] | high |
| 63 | 9730 | Kain Warick | positive_fill | no | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | medium |
| 64 | 10561 | MetaStreet | positive_fill | no | no | execution_services | ["defi"] | ["execution_services", "defi"] | high |
| 65 | 2819 | Chingari | searched_negative_full | yes | no | defi | [] | ["defi"] | medium |
| 66 | 10327 | Marco Alberti | searched_negative_full | no | yes |  | [] | [] | medium |
| 67 | 8910 | Hawkwood Capital | searched_negative_full | no | no | sub_fund | [] | ["sub_fund"] | medium |
| 68 | 6023 | Almadraba Capital Holding | searched_negative_full | no | yes |  | [] | [] | medium |
| 69 | 8182 | Ethan Francis | searched_negative_full | yes | no | execution_services\|defi | [] | ["execution_services", "defi"] | medium |
| 70 | 12062 | Sam Blond | searched_negative_full | no | yes |  | [] | [] | medium |
| 71 | 12187 | Sebastian Serrano | searched_negative_light | yes | no | otc_trading\|market_making\|execution_services\|defi | [] | ["otc_trading", "market_making", "execution_services", "defi"] | medium |
| 72 | 2894 | Faze Banks | searched_negative_light | no | yes |  | [] | [] | medium |
| 73 | 2297 | Charles Read | searched_negative_light | no | no | market_making\|defi | [] | ["market_making", "defi"] | high |
| 74 | 2791 | Blockseed Ventures | searched_negative_light | no | yes |  | [] | [] | high |
| 75 | 365 | Sanctor Capital | searched_negative_light | no | no | defi\|sub_fund | [] | ["defi", "sub_fund"] | medium |
| 76 | 4104 | Gracy Chen | searched_negative_light | no | no | otc_trading\|algorithm_trading\|execution_services\|defi | [] | ["otc_trading", "algorithm_trading", "execution_services", "defi"] | medium |
| 77 | 2188 | Keisuke Honda | skip_candidate | no | no | sub_fund | [] | ["sub_fund"] | medium |
| 78 | 6999 | Capital | skip_candidate | no | yes |  | [] | [] | high |
| 79 | 9101 | Hyperion Ventures | skip_candidate | no | yes |  | [] | [] | high |
| 80 | 7725 | Decision Tree Capital | skip_candidate | no | yes |  | [] | [] | medium |
| 81 | 6852 | Brainforest | skip_candidate | no | yes |  | [] | [] | high |
| 82 | 12543 | Sportzchain | skip_candidate | no | no | execution_services\|defi | [] | ["execution_services", "defi"] | medium |
| 83 | 6545 | Ben Haun | skip_candidate | no | yes |  | [] | [] | medium |
| 84 | 6176 | Anton Generalov | skip_candidate | no | yes |  | [] | [] | medium |
| 85 | 46 | Alameda Research | manual_focused | yes | no | defi | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 86 | 112 | Bixin Ventures | manual_focused | yes | no | execution_services\|defi\|sub_fund | [] | ["execution_services", "defi", "sub_fund"] | medium |
| 87 | 1739 | Crypto Vietnam | manual_focused | yes | yes |  | [] | [] | medium |
| 88 | 7535 | Cyphermines | manual_focused | yes | yes |  | [] | [] | medium |
| 89 | 258 | 7 O'clock Capital | positive_manual_boost | yes | yes |  | ["defi"] | ["defi"] | medium |
| 90 | 3444 | VenturesLab | positive_manual_boost | yes | yes |  | ["sub_fund"] | ["sub_fund"] | medium |
| 91 | 94 | Jump Crypto | targeted_addition | no | no | market_making\|execution_services\|defi | ["algorithm_trading"] | ["algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 92 | 1030 | Jump Trading | targeted_addition | no | no | otc_trading\|market_making\|execution_services\|defi | ["algorithm_trading"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |
| 93 | 378 | Wintermute | targeted_addition | no | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | high |

## Mismatch Evidence Summaries

### 1. YAY Network - task 3298

- In `needs_manual_review.csv`: yes
- Results labels: `["otc_trading", "defi"]`
- Audit labels: `["otc_trading", "execution_services", "defi"]`
- Mismatched capabilities: `execution_services`
- Original evidence summary: YAY Network FAQ describes an investment syndicate with public, OTC, and NDA deals, while tokenomics docs show farming rewards, liquidity, and market-making token allocations.
- Audit evidence summary: YAY official/owned sources describe OTC deals, an OTC marketplace/portal for allocations, broker-facilitated transactions outside exchanges, and YAY Games DeFi/NFT/farming products. No algorithmic trading, market making, or sub-fund evidence found.
- Audit Yes boundary notes: Official OTC marketplace crosses OTC/execution boundary; farming/staking/NFT DeFi docs cross DeFi boundary.
- Audit No boundary notes: Tokenomics market-making allocation is not YAY providing market making.

### 2. Belobaba Fund - task 6538

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services", "defi"]`
- Audit labels: `["otc_trading", "execution_services", "defi", "sub_fund"]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: Belobaba's official site describes an OTC crypto-fiat platform with direct order execution and a KHAN PLUS product that is explicitly tied to the DeFi ecosystem with daily on-chain accrual and autocompounding.
- Audit evidence summary: Belobaba official OTC page describes an OTC crypto-fiat service/trading desk and direct large-scale transactions outside order books; legal and fund documents show exchange/custody services, protected cell/master-feeder/Delaware feeder/SPV structure, and DeFi-linked token/staking/liquidity features.
- Audit Yes boundary notes: OTC trading desk; direct execution; master-feeder/PCC/feeder/SPV; DeFi-linked token ecosystem.
- Audit No boundary notes: Education about algorithmic/HFT and market-making allocation do not prove those services.

### 3. Great South Gate Asset Management - task 751

- In `needs_manual_review.csv`: no
- Results labels: `["algorithm_trading", "execution_services"]`
- Audit labels: `["algorithm_trading", "execution_services", "sub_fund"]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: GSG describes digital asset alpha strategies that use systematic trading and says it offers prime brokerage liquidity and institutional services
- Audit evidence summary: GSG official materials market systematic/stat-arb/CTA digital asset strategies; job evidence describes private client brokerage and trade execution lifecycle; MAS and official site show offshore feeder/SPC/Cayman structures. No OTC, market-making, or DeFi operation found.
- Audit Yes boundary notes: Systematic strategy language supports algorithm_trading; brokerage/trade lifecycle supports execution_services; SPC/feeder supports sub_fund.
- Audit No boundary notes: DeFi exposure is investment/research, not operated DeFi product.

### 4. North Rock Digital - task 11089

- In `needs_manual_review.csv`: no
- Results labels: `["algorithm_trading"]`
- Audit labels: `[]`
- Mismatched capabilities: `algorithm_trading`
- Original evidence summary: Preqin and aVenture both profile North Rock Digital as a crypto hedge fund; Preqin explicitly notes systematic and opportunistic strategies, which support algorithm_trading, but there is no OTC, market-making, execution, DeFi, or sub-fund evidence.
- Audit evidence summary: SEC/Form D evidence identifies a pooled-investment hedge fund/adviser; secondary strategy language was not enough to prove algorithmic/systematic/HFT trading capability. No trading desk, market making, DeFi operation, execution service, or explicit feeder/SPV/sub-fund structure found.
- Audit No boundary notes: Secondary strategy snippets without primary capability evidence are insufficient for algorithm_trading; managed hedge fund alone is not sub_fund.

### 5. RedLine Capital - task 4598

- In `needs_manual_review.csv`: no
- Results labels: `["algorithm_trading", "market_making"]`
- Audit labels: `["algorithm_trading", "market_making", "sub_fund"]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: Current sources describe Redline Capital as a blockchain investment firm that runs a crypto quantitative fund and handles exchange liquidity and market making.
- Audit evidence summary: RedLine/Redline DAO materials describe six sub-funds, quantitative transaction expertise, and a professional quantitative team providing liquidity and market maker services. No OTC, execution/brokerage, or DeFi-operated product found.
- Audit Yes boundary notes: Explicit quantitative team and market maker services cross algorithm/market_making; six sub-funds cross sub_fund.
- Audit No boundary notes: Exchange-listing help and relationships are not execution_services.

### 6. Genblock Capital - task 23

- In `needs_manual_review.csv`: no
- Results labels: `["market_making"]`
- Audit labels: `["market_making", "defi"]`
- Mismatched capabilities: `defi`
- Original evidence summary: Genblock is an exclusive blockchain/crypto investor that explicitly helps portfolio projects with liquidity and market making.
- Audit evidence summary: Genblock official about page says it invests exclusively in blockchain/crypto with a focus on decentralized finance and helps portfolio projects with bootstrapping liquidity, token economics, and market making. No OTC, algorithmic trading, execution service, or sub-fund evidence found.
- Audit Yes boundary notes: Explicit market-making help crosses market_making; explicit DeFi focus crosses the audit DeFi specialization boundary.
- Audit No boundary notes: Secondary-market investing does not prove OTC desk.

### 7. A+ Ventures - task 1942

- In `needs_manual_review.csv`: no
- Results labels: `["sub_fund"]`
- Audit labels: `[]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: The official site says A+ Ventures is an independent VC fund manager and that it deploys capital through carefully structured SPVs, which is explicit sub-fund/SPV evidence.
- Audit evidence summary: A+ Ventures appears to be a Web3/blockchain VC/accelerator/business consulting firm. No explicit OTC, algorithmic, market-making, execution, DeFi-operated product, or sub-fund/feeder/SPV/fund-platform evidence found; primary-source availability was sparse.
- Audit No boundary notes: Web3 incubation and funding token projects are not enough for DeFi or sub_fund.

### 8. MochiLab - task 10739

- In `needs_manual_review.csv`: no
- Results labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|execution_services`
- Original evidence summary: LinkedIn describes MochiLab as an incubator of future innovative DeFi and NFT projects; a press release tied to the team describes the project as community-driven and aimed at DeFi/NFT infrastructure.
- Audit evidence summary: MochiLab incubated/created Mochi.Market, a multi-chain decentralized NFT exchange with AMM, staking, lending, fractionalization, and cross-chain swaps. This supports protocol-level market_making, execution_services, and DeFi. No OTC, algorithmic trading, or sub-fund evidence found.
- Audit Yes boundary notes: AMM/liquidity solution supports protocol-level market_making; decentralized exchange supports execution_services; DeFi-native product supports DeFi.
- Audit No boundary notes: AMM mechanics are not algorithmic/HFT trading service.

### 9. BitGo - task 1543

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services", "defi"]`
- Mismatched capabilities: `algorithm_trading|defi`
- Original evidence summary: BitGo markets prime brokerage and OTC trading, including trading, financing, collateral management, settlement, and electronic execution from regulated custody.
- Audit evidence summary: BitGo official materials advertise OTC/block trading, prime brokerage/electronic trading/API/UI execution, smart order routing, algorithmic pass-through execution such as TWAP/VWAP, and institutional DeFi access through custody/wallet integrations. No self market-making or sub-fund structure found.
- Audit Yes boundary notes: OTC desk, TWAP/VWAP algorithmic execution, prime brokerage/electronic execution, and institutional DeFi access are explicit.
- Audit No boundary notes: Aggregating external liquidity providers/market makers is not self market_making.

### 10. Jesse Powell - task 9515

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Mismatched capabilities: `algorithm_trading|market_making`
- Original evidence summary: Kraken’s official site and press release say it is a crypto exchange with exchange trading, OTC trading, futures, and API access; Powell co-founded the exchange and is chairman.
- Audit evidence summary: Official Kraken sources tie Jesse Powell to Kraken and show OTC desk, API/FIX low-latency/automated trading access, token liquidity support, and execution services. No DeFi-native protocol operation or sub-fund evidence found for Powell.
- Audit Yes boundary notes: Founder/chairman linkage to Kraken used for OTC/API/market-structure/execution capability.
- Audit No boundary notes: Kraken/Powell crypto exposure and staking are not DeFi operation; individual angel status is not sub_fund.

### 11. Ace Exchange - task 5778

- In `needs_manual_review.csv`: no
- Results labels: `["execution_services"]`
- Audit labels: `["algorithm_trading", "execution_services"]`
- Mismatched capabilities: `algorithm_trading`
- Original evidence summary: ACE Exchange's help center says it is a fiat-to-crypto exchange and user-friendly trading platform with compliance and security features.
- Audit evidence summary: ACE official materials describe an order-book exchange and AI/grid trading robot described as a quantitative strategy. No official OTC desk, market making, DeFi operation, or sub-fund evidence found.
- Audit Yes boundary notes: Official AI/grid trading robot supports algorithm_trading; exchange order-book supports execution_services.
- Audit No boundary notes: Third-party OTC label without official OTC desk detail is insufficient.

### 12. SOMESING (Social/Platform Software) - task 12479

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["defi"]`
- Mismatched capabilities: `defi`
- Original evidence summary: SOMESING is a blockchain singing app and ecosystem, not a trading or fund-vehicle business.
- Audit evidence summary: SOMESING official site shows blockchain content/token platform; 2021 reports and Delio guide describe SSX crypto deposit/yield product with Delio. No trading desk, algorithmic trading, market making, execution, or sub-fund evidence found.
- Audit Yes boundary notes: Co-launched/marketed SSX deposit/yield product with DeFi/open-finance provider supports DeFi.
- Audit No boundary notes: Exchange listings and token migration are not execution_services.

### 13. Exnetwork Capital - task 4

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["otc_trading"]`
- Mismatched capabilities: `otc_trading`
- Original evidence summary: Row describes a crypto VC focused on blockchain and cryptocurrency; no explicit operating capability evidence was found.
- Audit evidence summary: Exnetwork is a blockchain fund/incubator; ExNetwork-owned Medium and third-party article tie Exnetwork/Eric Su to The OTC Room/major crypto OTC trading desk. No algorithmic, market-making, execution, DeFi operation, or sub-fund evidence found.
- Audit Yes boundary notes: Explicit OTC Room/OTC desk evidence supports otc_trading.
- Audit No boundary notes: Portfolio exposure to market-making/DeFi companies is not Exnetwork's own capability.

### 14. Vision Capital - task 4883

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["sub_fund"]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: No search performed; routed as skip_candidate based on the input row only.
- Audit evidence summary: Vision Capital is a private equity/direct portfolio acquisition group. SEC/private fund/Gazette evidence ties Vision Capital fund entities to feeder/master/fund-of-funds structures, supporting sub_fund. No trading, execution, market-making, or DeFi operation found.
- Audit Yes boundary notes: Explicit feeder LP/master/fund-of-funds evidence supports sub_fund.
- Audit No boundary notes: Private company acquisitions are not OTC trading services.

### 15. Sentillia - task 3428

- In `needs_manual_review.csv`: yes
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services"]`
- Mismatched capabilities: `algorithm_trading`
- Original evidence summary: Deribit support docs and the Sentillia profile identify the entity as a crypto futures/options exchange with low-latency trading and OTC RFQ functionality, conflicting with the VC-style task-row description.
- Audit evidence summary: Primary sources identify Sentillia B.V. as Deribit. Deribit docs show derivatives/spot trading venue, API/FIX execution, block trading for large off-book negotiated trades, and low-latency/mass-quote functionality. No self market-making, DeFi operation, or sub-fund evidence found.
- Audit Yes boundary notes: Block trading supports OTC; API/FIX and mass quotes support execution/algorithmic capabilities.
- Audit No boundary notes: Tools for market makers are not Deribit itself market-making.

### 16. OccamDAO - task 4475

- In `needs_manual_review.csv`: yes
- Results labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|execution_services`
- Original evidence summary: Official site and docs describe Occam as a DeFi launchpad/DEX/DAO platform.
- Audit evidence summary: OccamDAO/Occam.fi materials describe DAO-governed DeFi ecosystem services including launchpad, DEX, DAO, incubator, OccamX DEX liquidity provision/mining/fees, and cross-chain trading. No OTC, algorithmic trading, or sub-fund evidence found.
- Audit Yes boundary notes: DEX liquidity pools support market_making; DEX trading infrastructure supports execution_services; DeFi suite supports DeFi.
- Audit No boundary notes: AMM mechanics are not algorithmic/HFT trading; staking/ISPO pools are not sub_fund.

### 17. MHC Digital Group - task 4383

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|defi`
- Original evidence summary: Official site and OTC page describe institutional OTC execution, custody, settlement, and post-trade support; that is sufficient for OTC trading and execution-services capability.
- Audit evidence summary: MHC Digital Group's official site markets MHC Markets as an institutional OTC desk for buying, selling, swapping, custody, secure execution, fast settlement, AUD/USD on/off ramps, aggregated global liquidity, and multiple liquidity venues. Its official trading terms are OTC trading terms for fiat and digital asset pairs and other OTC services. Its funds-management pages state that MHC actively manages liquid digital-asset exposure across sectors including DeFi, and its Digital Asset Fund is actively managed around themes including DeFi. An official MHC market-making guide presents MHC Digital Group as an institutional-grade partner for projects seeking compliant digital-asset liquidity solutions in the context of selecting a crypto market-making partner. I found no explicit MHC algorithmic/quantitative/HFT trading desk evidence and no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.
- Audit Yes boundary notes: otc_trading crosses the threshold because MHC explicitly markets an institutional-grade OTC desk and official OTC trading terms.|execution_services crosses the threshold because MHC explicitly markets secure execution, optimized execution, liquidity venue aggregation, fast settlement, on/off ramps, and liquidity access through its OTC platform.|market_making crosses the threshold because MHC's official market-making guide identifies MHC Digital Group as a partner for digital-asset liquidity solutions in the context of choosing a market-making partner.|defi crosses the threshold because MHC itself markets actively managed fund exposure to DeFi themes and DeFi tokens, not merely portfolio-company investments.
- Audit No boundary notes: General mentions of algorithmic traders, HFT, dynamic spread adjustment, or arbitrage in MHC educational articles were not attributed to MHC's own trading capability, so algorithm_trading remains no.|MHC manages two funds and a registered digital asset fund, but ordinary fund management and multiple funds are not explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.|Deep liquidity and liquidity-provider infrastructure alone would be insufficient for market_making without the official market-making partner context.

### 18. Samuel Bankman-Fried - task 12087

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "algorithm_trading", "market_making", "defi"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `execution_services`
- Original evidence summary: SEC and CFTC filings describe FTX as a crypto asset trading platform and Alameda as a primary market maker; the task row describes an automated OTC trading system, and the Serum site describes a DEX and DeFi ecosystem.
- Audit evidence summary: The CFTC amended complaint states that Bankman-Fried owned, operated, or controlled FTX and Alameda; Alameda used proprietary algorithmic quantitative programs and high-frequency arbitrage, and operated as a primary market maker/liquidity provider on FTX. The same filing describes FTX as a centralized digital asset exchange with an order book, matching engine, API, and OTC portal for direct quote-based spot trades. An Economic Club transcript states Bankman-Fried designed Jane Street's automated OTC-trading system. Serum documentation describes Serum as a decentralized finance protocol with an on-chain order book and matching engine, and SFOX reports Project Serum was founded by Sam Bankman-Fried and FTX members. No evidence found for sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds capability.
- Audit Yes boundary notes: otc_trading crosses the threshold because public evidence explicitly says Bankman-Fried designed an automated OTC-trading system at Jane Street, and the FTX platform he controlled also operated an OTC portal for direct quote-based trades.|algorithm_trading crosses the threshold because Alameda, under Bankman-Fried's ownership/control, used proprietary algorithmic quantitative programs and high-frequency arbitrage trading.|market_making crosses the threshold because Alameda, under Bankman-Fried's ownership/control, was explicitly described as a primary market maker and liquidity provider on FTX.|execution_services crosses the threshold because FTX, controlled by Bankman-Fried, operated exchange infrastructure including an electronic order book, matching engine, API access, and OTC portal.|defi crosses the threshold because Bankman-Fried is publicly tied to founding Project Serum, and Serum's own docs describe it as a DeFi protocol/ecosystem with decentralized order-book and matching infrastructure.
- Audit No boundary notes: No sub_fund classification: evidence of Alameda/FTX entities, trading firms, and investment activity is not explicit evidence of a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds.|Portfolio or investment relationships alone were not used to infer DeFi capability; the DeFi yes decision relies on Bankman-Fried's founder/control relationship to Serum/FTX/Alameda-related operating platforms.

### 19. Pantronics Holdings - task 11292

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services", "defi", "sub_fund"]`
- Mismatched capabilities: `algorithm_trading|defi|sub_fund`
- Original evidence summary: Former Pantronics Holdings / Huobi Tech now New Huo Technology; news coverage says it launched a crypto OTC service and also offers virtual asset management, custody, trust, and brokerage-related services.
- Audit evidence summary: HKEX filings show Pantronics Holdings changed name to Huobi Technology Holdings, later Sinohope Technology. Sinohope's 2025 annual report explicitly describes OTC virtual asset trading with corporate and individual customers, client execution of large trades, crypto exchange services, automated crypto asset trading services, quantitative products using fee and basis arbitrage, and controlled sub-funds including Sinohope Delta Neutral Quant Arbitrage Sub-fund. A company-distributed announcement says New Huo Tech launched DeFi and metaverse thematic investment services via its licensed asset manager. No source found shows the entity currently operates market making or liquidity provision; the annual report discusses market making and liquidity provision only as future/customized solution targets.
- Audit Yes boundary notes: otc_trading crosses the threshold because the annual report explicitly states the Group provides over-the-counter virtual asset trading business.|algorithm_trading crosses the threshold because the annual report explicitly identifies quantitative products and quantitative trading strategies including fee arbitrage and basis arbitrage.|execution_services crosses the threshold because the annual report says OTC clients execute large trades through the Group's services and describes crypto exchange and automated crypto asset trading services through a proprietary platform.|defi crosses the threshold because the company announcement explicitly markets DeFi thematic investment services, not merely passive investments in DeFi startups.|sub_fund crosses the threshold because the annual report explicitly names controlled sub-funds and segregated portfolio structures, including Sinohope Delta Neutral Quant Arbitrage Sub-fund.
- Audit No boundary notes: market_making is not marked yes because the only explicit market making/liquidity provision language found is framed as future customized quantitative solutions, not an operated current capability.|References to liquidity providers and exchange liquidity do not prove Sinohope itself is a market maker or liquidity provider.

### 20. Mohamed Jezri Mohideen - task 10747

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "algorithm_trading", "market_making"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"]`
- Mismatched capabilities: `execution_services|defi|sub_fund`
- Original evidence summary: Laser Digital bio says he led flow trading and systematic trading while company news describes market making liquidity provision and an OTC crypto options license
- Audit evidence summary: Laser Digital official materials state that Jez Mohideen co-founded Laser Digital and serves as Co-founder and CEO. Laser Digital's trading page explicitly lists OTC, token market making, quant-driven liquidity provision, systematic trading experience, live executable two-way price streams, FIX/WebSocket connectivity, and post-trade settlement. Its asset-management page says the Carry Fund uses an internal institutional-grade execution platform to access diversified liquidity, while its Bitcoin Diversified Yield Fund deploys market-neutral arbitrage and DeFi strategies and is offered in tokenised and traditional fund formats. Laser's DeFi-enabled Ethereum Adoption Fund page describes built-in DeFi mechanisms and a compliant DeFi market-access vehicle. Laser also states funds are segregated portfolios within Laser Digital Funds SPC and describes Tokenised LCF exposure to Laser Digital Carry Fund SP, a Cayman Segregated Portfolio. KAIO documentation supports fund-platform evidence, describing KAIO as a tokenized-funds and institutional DeFi platform with native fund lifecycle support.
- Audit Yes boundary notes: otc_trading crosses the threshold because Laser Digital's own trading page labels the service 'OTC' and describes executable two-way crypto and FX price streams.|algorithm_trading crosses the threshold because Laser Digital explicitly describes quant-driven liquidity provision and systematic trading.|market_making crosses the threshold because Laser Digital explicitly markets token market making and liquidity provision for token projects.|execution_services crosses the threshold because Laser Digital describes live executable price streams, FIX/WebSocket connectivity, post-trade settlement, and an internal institutional-grade execution platform to access diversified liquidity.|defi crosses the threshold because Laser Digital markets DeFi-enabled funds and fund strategies with built-in DeFi mechanisms, DeFi strategies, and compliant DeFi market access.|sub_fund crosses the threshold because Laser Digital's funds are described as segregated portfolios/SPC structures and KAIO is explicitly a tokenized-funds platform with fund lifecycle infrastructure.
- Audit No boundary notes: The Vana angel investment was not used to infer any capabilities.|Portfolio-company or partner capabilities were not counted unless Laser Digital's own product pages or KAIO's own documentation described the capability in connection with Laser/KAIO platform operations.|Nomura's broader institutional trading history was not treated as sufficient by itself; the yes decisions rely on Laser Digital operating-platform evidence tied to Mohideen's co-founder/CEO role.

### 21. Jane Street - task 1071

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `defi`
- Original evidence summary: Official pages describe Jane Street as a research-driven trading firm, a global liquidity provider, one of the world's largest market makers, and a firm that provides direct OTC trading and execution for clients, including crypto token trading.
- Audit evidence summary: Jane Street's official materials identify it as a global liquidity provider and trading firm using sophisticated quantitative analysis, models, strategies, and systems, and as one of the world's largest market makers. Its client offering states that it is a leading market maker and liquidity provider, active in bilateral/off-exchange markets, provides direct OTC bond trading with clients, offers electronic trading infrastructure including smart-order-router/FIX access, and provides wholesale market making. A FINRA Rule 606 report for Jane Street Execution Services confirms routing of customer orders via smart order routers/algos. DeFi is supported by Clearpool's announcement of a DeFi lending protocol pool in partnership with Jane Street and The TRADE's report that Jane Street joined the DeFi Pyth Network as a crypto market data contributor. No public evidence found for a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds capability.
- Audit Yes boundary notes: otc_trading=yes because Jane Street's official client offering explicitly says it is active in bilateral, off-exchange markets and provides direct OTC trading with clients.|algorithm_trading=yes because official materials explicitly describe quantitative analysis, models, algorithms, trading systems, machine learning, and quantitative trading.|market_making=yes because official materials explicitly call Jane Street a leading market maker and one of the world's largest market makers.|execution_services=yes because official materials describe client execution, execution-quality services, smart-order-router/FIX access, proprietary liquidity access, and Jane Street Execution Services as a broker-dealer; FINRA reports confirm customer order routing.|defi=yes because Jane Street itself participated in a Clearpool DeFi lending protocol pool and joined Pyth Network as a contributor to a DeFi data network, which goes beyond merely funding DeFi startups.
- Audit No boundary notes: sub_fund=no because Jane Street is evidenced as a trading firm, liquidity provider, market maker, and broker-dealer platform, but the researched sources do not show a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.

### 22. Amber Group - task 101

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `defi`
- Original evidence summary: Amber Group describes itself as a global digital financial services firm and explicitly lists algorithmic trading, market making, OTC trading, and execution services.
- Audit evidence summary: Amber Group's official pages explicitly market OTC trading, 24/7 execution services, VWAP/TWAP and customized advanced order execution, automated strategies, market-making/liquidity provision, and DeFi products/DeFi market integration. Its official support article describes Algorithmic Trading/Execution using automated pre-programmed instructions and aggregated execution across centralized and decentralized venues. Its asset-management page also describes algorithm research, low-latency high-throughput trading infrastructure, systematic models, and automated institutional order execution. No explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence was found in the reviewed public evidence.
- Audit Yes boundary notes: otc_trading=yes because Amber Group's official digital wealth page has an explicit OTC Trading section and says clients can contact its OTC trading team.|algorithm_trading=yes because official materials explicitly describe automated strategies, algorithmic trading, algorithm research, systematic models, and VWAP/TWAP/advanced order execution.|market_making=yes because Amber Group's official liquidity provision page says it is a primary liquidity provider and cites sophisticated market making expertise and daily market-making volumes.|execution_services=yes because official materials explicitly market 24/7 trading execution services, advanced order execution, aggregated execution, and access to global market liquidity.|defi=yes because Amber Group itself explicitly markets DeFi Yield Enhanced Products and execution/liquidity across decentralized venues or CeFi and DeFi markets, not merely portfolio investment in DeFi startups.
- Audit No boundary notes: sub_fund=no because references to strategic funds, Amber Eco Fund, investment products, and audited funds are not explicit evidence of a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.|DeFi startup investment language alone was not treated as sufficient; the DeFi yes decision rests on Amber Group's own marketed DeFi products and decentralized-venue execution/liquidity capabilities.

### 23. Joseph Jones - task 4242

- In `needs_manual_review.csv`: no
- Results labels: `["sub_fund"]`
- Audit labels: `["execution_services"]`
- Mismatched capabilities: `execution_services|sub_fund`
- Original evidence summary: HMC INQ's official pages identify Jones as founding partner, describe him as a DreamHost co-founder and Bitcoin investor, and say Harvey's Angels investments use a simple SPV structure and process.
- Audit evidence summary: Official HMC INQ and FlyCoin materials identify Joseph/Josh Jones as an entrepreneur, HMC INQ founding partner, Bitcoin investor, and founder of Bitcoin Builder, with FlyCoin also describing him as Owner, Chairman, and CTO of FLOAT Alaska. Coindesk reported that Bitcoin Builder, founded by Josh Jones, allowed Mt. Gox customers to trade account funds for bitcoin and that about 14,500 BTC of trades had executed. Bitcoinist reported Bitcoin Builder relaunched as a Bitcoin Exchange Aggregator pulling best prices from multiple exchanges, offering buy/sell bitcoin trading and feeless trade executions, plus lending and shorting. This supports execution_services via an explicitly founder-operated trading/exchange aggregation platform. I found no explicit OTC desk/block/bilateral trading, algorithmic/quant/systematic/HFT trading, market making/liquidity provision, DeFi-native capability, or sub-fund/feeder/umbrella/SPV/fund-platform/fund-of-funds evidence attributable to Jones or his controlled platforms.
- Audit Yes boundary notes: execution_services crosses the threshold because Bitcoin Builder is explicitly attributed to Josh Jones as founder/CEO and is described as an exchange/trading platform and exchange aggregator enabling buy/sell trading, trade executions, and aggregation of order books from multiple major exchanges.
- Audit No boundary notes: Bitcoin Builder's exchange and aggregator activity is not explicit OTC desk, block trading, or bilateral trading evidence.|References to automated bitcoin buying on Mt. Gox and exchange aggregation do not explicitly establish algorithmic, quantitative, systematic, HFT, or low-latency trading.|Buying GOXBTC and operating a trading platform are not explicit market making or liquidity provision evidence.|FlyCoin and Bitcoin Builder are crypto-related, but the evidence describes centralized rewards, exchange, and aggregation services, not DeFi-native products or DeFi specialization.|HMC INQ is described as a venture fund/incubator supporting Harvey Mudd startups, but there is no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

### 24. Coven - task 3891

- In `needs_manual_review.csv`: no
- Results labels: `["sub_fund"]`
- Audit labels: `["defi"]`
- Mismatched capabilities: `defi|sub_fund`
- Original evidence summary: Mesh retrospective describes Coven as a decentralized venture investing platform and DAO.
- Audit evidence summary: ConsenSys Mesh describes Coven as an incubated project that built a decentralized venture investing platform, used token staking for sourcing, diligence, approval, and economics, and operated as a DAO before being sunset. Monerium's press release describes Coven as a ConsenSys Formation and open co-venturing initiative. USPTO trademark materials similarly describe Coven as a decentralized venture investing platform. I found no investor-level evidence that Coven itself offered OTC/block trading, algorithmic trading, market making/liquidity provision, execution/order routing/brokerage, prime brokerage, or liquidity access services. Alkemi was a portfolio/backed company with prime-brokerage and liquidity infrastructure, but that does not transfer execution or trading capabilities to Coven.
- Audit Yes boundary notes: defi=yes because Coven itself operated a decentralized, DAO-like venture investing platform using token staking and on-chain/Web3 investment primitives; this is investor-level DeFi-native capability, not merely a portfolio investment.
- Audit No boundary notes: otc_trading=no: no explicit Coven OTC desk, block trading, or bilateral trading service evidence.|algorithm_trading=no: no explicit Coven algorithmic, quantitative, systematic, HFT, or low-latency trading evidence.|market_making=no: no explicit Coven market making or liquidity provision evidence.|execution_services=no: no explicit Coven execution, smart order routing, order routing, brokerage, prime brokerage, or liquidity access service evidence; Alkemi's capabilities are portfolio-company evidence only.|sub_fund=no: no explicit Coven sub-fund, feeder, umbrella, parallel fund, SPV, or fund-of-funds evidence; broad venture fund/trademark language and a decentralized venture investing platform are not enough under the boundary rule.

### 25. Samara Alpha Management - task 12072

- In `needs_manual_review.csv`: no
- Results labels: `["algorithm_trading", "sub_fund"]`
- Audit labels: `["algorithm_trading", "market_making", "defi", "sub_fund"]`
- Mismatched capabilities: `market_making|defi`
- Original evidence summary: Samara Alpha Management describes digital asset opportunities, market-neutral alpha, and beta-neutral strategies such as algorithmic trading on its official site; the SEC adviser record confirms the firm identity.
- Audit evidence summary: Samara Alpha's official site describes institutional-grade diversified digital asset funds and manager selection. Its Opportunities page markets Market-neutral Alpha as access to digital asset managers using strategies including market-making and proprietary algorithmic trading. It also describes a hedge fund seeding platform and a Boreal Market-Neutral DeFi strategy, while its strategy article explicitly describes Samara Alpha as using a fund-of-funds structure with monthly liquidity. I found no explicit evidence that Samara Alpha itself operates an OTC desk, bilateral/block trading service, brokerage, prime brokerage, order-routing, or execution-services platform.
- Audit Yes boundary notes: algorithm_trading=yes because Samara Alpha's official Market-neutral Alpha product explicitly includes exposure to proprietary algorithmic trading strategies.|market_making=yes because Samara Alpha's official Market-neutral Alpha product explicitly includes exposure to market-making strategies.|defi=yes because Samara Alpha explicitly markets DeFi product exposure through Boreal Market-Neutral DeFi and discusses DeFi strategies within its digital asset strategy offering.|sub_fund=yes because Samara Alpha explicitly describes a fund-of-funds structure and a hedge fund seeding platform.
- Audit No boundary notes: otc_trading=no because the only OTC reference found was generic discussion of institutional investors with OTC access, not an explicit Samara Alpha OTC desk, block trading, or bilateral trading capability.|execution_services=no because references to execution efficiency or capacity do not show Samara Alpha offering execution, smart order routing, brokerage, prime brokerage, or liquidity-access services.|Underlying managers and seeded managers were not treated as proof that Samara Alpha directly operates those trading venues or desks; yes decisions are limited to Samara Alpha's officially marketed strategy exposure and fund platform.

### 26. Tikhon Bernstam - task 13058

- In `needs_manual_review.csv`: no
- Results labels: `["sub_fund"]`
- Audit labels: `[]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: Uncommon Capital lists Bernstam as managing partner. Kando identifies Tikhon Bernstam AngelList Fund LP, and Fortune describes a Bernstam AngelList syndicate, which supports sub_fund/fund-platform capability beyond the local fund-name field. Forbes shows Web3/Rye exposure, but searches did not show OTC, algorithmic trading, market making, execution services, or DeFi-native operations by Bernstam.
- Audit evidence summary: Uncommon Capital's official site identifies Tikhon Bernstam as Managing Partner of an early-stage software venture investor and describes operational support in product, data, marketing, people, and engineering, but not trading, brokerage, market making, OTC, algorithmic trading, or DeFi products. SEC Form D evidence for Crystal Towers Capital, L.P. shows Bernstam as managing member of the general partner of a pooled venture capital fund; TechCrunch reports related Crystal Towers affiliate filings, but not an explicit feeder, SPV, umbrella, parallel fund, fund platform, or fund-of-funds structure. Secured Finance is a DeFi protocol/platform and lists Bernstam among investors, but portfolio investment alone does not confer DeFi capability to him as an investor. Rye evidence shows Bernstam as a founder of a Web3/e-commerce API company with checkout and crypto reward features, not a DeFi-native investment capability or financial trading/execution service.
- Audit No boundary notes: Secured Finance is a DeFi company, but Bernstam appears only as an investor in the available evidence; funding a DeFi startup alone is insufficient for defi=yes.|Rye has Web3, token, stablecoin reward, and checkout API evidence, but it is e-commerce infrastructure rather than OTC trading, algorithmic trading, market making, financial execution services, or a DeFi-native investor capability.|Crystal Towers and the AngelList fund references show venture/angel fund activity, but standard pooled venture funds and affiliated fund filings are insufficient for sub_fund=yes without explicit feeder, SPV, umbrella, parallel fund, fund platform, or fund-of-funds evidence.|Uncommon Capital mentions fintech/frontier-tech investing and operational help, but does not explicitly market trading desks, order routing, brokerage, liquidity access, market making, or quantitative/systematic trading.

### 27. OrangeX - task 11229

- In `needs_manual_review.csv`: no
- Results labels: `["execution_services"]`
- Audit labels: `["market_making", "execution_services"]`
- Mismatched capabilities: `market_making`
- Original evidence summary: OrangeX's official pages describe a professional crypto trading platform with spot, perpetual, and copy trading and emphasize liquidity and trading execution.
- Audit evidence summary: OrangeX is an operating centralized crypto trading platform/exchange. Official materials describe spot trading, perpetual trading, order books, market and limit orders, order placement, and API-based account/product trading. Its official site also markets excellent liquidity supported by 50+ market-making teams, trusted partners, and a robust order book. I found no explicit OrangeX OTC desk/block/bilateral trading service, no explicit algorithmic/quant/systematic/HFT offering by OrangeX, no DeFi-native product operated by OrangeX, and no fund/sub-fund/feeder/SPV evidence.
- Audit Yes boundary notes: execution_services=yes because OrangeX officially operates spot and perpetual trading venues where users place buy/sell orders, use order books, and access trading via web/app/API.|market_making=yes because OrangeX's official site explicitly describes liquidity supported by 50+ market-making teams and a robust/extensive order book, satisfying explicit market-making/liquidity evidence for its operating exchange platform.
- Audit No boundary notes: No OTC evidence: ordinary spot/perpetual exchange trading and deep liquidity are not explicit OTC desk, block trading, or bilateral trading services.|No algorithmic trading evidence: API access, order types, an arbitrage dashboard, conditional orders, and trailing orders do not explicitly show OrangeX operates or markets algorithmic, quantitative, systematic, HFT, or low-latency trading capability.|No DeFi evidence: OrangeX Earn, Dual Asset Earn, listings, and centralized exchange trading are not DeFi-native capability; search results for OrangeDX appear to concern a different similarly named project.|No sub_fund evidence: no public evidence found of a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds.

### 28. BitFlyer - task 6648

- In `needs_manual_review.csv`: no
- Results labels: `["execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Mismatched capabilities: `otc_trading|algorithm_trading|market_making`
- Original evidence summary: Official bitFlyer site describes a crypto marketplace, bitFlyer Lightning for sophisticated traders, API/web-interface execution of complex order types, and access to global BTC/JPY liquidity; no OTC desk, proprietary market making, DeFi, or sub-fund evidence was found.
- Audit evidence summary: bitFlyer official documents describe over-the-counter crypto asset derivatives as negotiated transactions between the customer and bitFlyer, Inc. as counterparty. Official trading disclosures state that bitFlyer's proprietary trading department and group companies may place orders to provide liquidity to Exchange and bitFlyer Lightning order books and that the proprietary trading department uses algorithm-based automated order placement. bitFlyer also operates customer trading venues, acts as intermediary on its exchange platform, executes user orders, offers bitFlyer Lightning, and provides HTTP/private APIs for placing and cancelling orders. DeFi evidence found was educational guidance and token/glossary content, not a DeFi-native product operated by bitFlyer. The Blockchain Angel Fund is described as an in-house seed-stage fund, with no sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.
- Audit Yes boundary notes: otc_trading crosses the threshold because official documents explicitly call bitFlyer's crypto derivative trades over-the-counter negotiated transactions with bitFlyer, Inc. as counterparty.|algorithm_trading crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department uses algorithm-based automated order placement.|market_making crosses the threshold because official documents explicitly state that bitFlyer's proprietary trading department/group companies place orders to provide liquidity to Exchange and bitFlyer Lightning order books.|execution_services crosses the threshold because bitFlyer operates exchange/trading platforms, executes user orders, acts as intermediary on the exchange platform, and provides APIs for order submission and cancellation.
- Audit No boundary notes: DeFi pages explain DeFi and how to access it using a crypto exchange and wallet, but they do not show bitFlyer itself operating or marketing a DeFi-native product.|The Blockchain Angel Fund is a standard in-house seed-stage investment fund; the evidence does not describe a feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.|A market maker program FAQ for one ETH/BTC pair says there is no current market maker program for that pair, but separate official disclosures still show bitFlyer's own liquidity-provision activity.

### 29. UniLend Finance - task 3269

- In `needs_manual_review.csv`: no
- Results labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|execution_services`
- Original evidence summary: UniLend is a permissionless DeFi platform for spot trading and lending/borrowing, which is enough to mark defi=yes.
- Audit evidence summary: UniLend's official site and docs describe UniLend as a permissionless decentralized finance protocol for lending and borrowing ERC20 assets, with official documentation also describing spot trading services, decentralized trading functionality, trading pairs, and liquidity pools where liquidity providers receive fees. Official V2 documentation describes dual-asset lending pools, borrowing, lending, liquidation, and flashloan functions. I found no explicit evidence that UniLend operates an OTC desk, block or bilateral trading service, algorithmic/quantitative/HFT trading, or any sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.
- Audit Yes boundary notes: defi=yes because UniLend itself officially operates and markets a DeFi-native permissionless lending and borrowing protocol.|execution_services=yes because UniLend's official docs explicitly describe spot trading services, decentralized trading functionality, and in-platform trading pairs, which meets the DEX/exchange/swap venue execution-services boundary.|market_making=yes because UniLend's official docs describe liquidity pools and liquidity provision with fees within the UniLend protocol, meeting the AMM/liquidity-pool liquidity provision threshold for an operated DeFi protocol.
- Audit No boundary notes: otc_trading=no because spot trading and DEX-style trading functionality are not explicit OTC desk, block trading, or bilateral trading evidence.|algorithm_trading=no because smart contracts, governance, liquidations, and intent-driven transaction infrastructure are not explicit algorithmic, quantitative, systematic, HFT, or low-latency trading evidence.|sub_fund=no because UniLend is described as a DeFi protocol/company, not as a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds.

### 30. Mow capital - task 1595

- In `needs_manual_review.csv`: no
- Results labels: `["market_making"]`
- Audit labels: `["algorithm_trading", "market_making"]`
- Mismatched capabilities: `algorithm_trading`
- Original evidence summary: Official site states that Mow Capital is a quantitative trading firm and liquidity provider active in major crypto markets and a high-frequency trader across leading exchanges.
- Audit evidence summary: Mow Capital's official site says it is a quantitative trading firm and liquidity provider active in leading crypto markets, has a high frequency trading section, trades major coins on major exchanges, and describes itself as a top market maker. The site also describes crypto investing, but does not show OTC desk/block trading, client execution or brokerage services, DeFi-native operations/products, or sub-fund/feeder/SPV/fund-platform structure.
- Audit Yes boundary notes: algorithm_trading=yes because the official site explicitly calls Mow Capital a quantitative trading firm and separately describes high frequency trading.|market_making=yes because the official site explicitly calls Mow Capital a liquidity provider and a top market maker.
- Audit No boundary notes: otc_trading=no because no explicit OTC desk, block trading, or bilateral trading evidence was found.|execution_services=no because trading on exchanges and providing liquidity are not the same as explicit client execution, order routing, brokerage, prime brokerage, or liquidity access services.|defi=no because portfolio exposure to crypto or DeFi-related companies is insufficient without evidence that Mow Capital itself operates or markets DeFi-native capability or product exposure.|sub_fund=no because no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence was found.

### 31. LTP (Singapore) - task 10194

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi", "sub_fund"]`
- Mismatched capabilities: `algorithm_trading|market_making|defi|sub_fund`
- Original evidence summary: Official pages describe a global institutional prime brokerage with OTC trading and execution clearing settlement custody lending and financing services; this supports otc_trading and execution_services only.
- Audit evidence summary: LTP's official materials describe it as an institutional digital-asset prime broker offering trade execution, clearing, settlement, custody, financing, liquidity access, Smart Order Routing, cross-exchange execution, ultra-low-latency connectivity, market data, DMA, and infrastructure for HFT/quantitative traders. LTP announced its own OTC trading platform with custom RFQs and block trade workflows. Official product updates describe access to centralized and decentralized exchanges, OTC venues, direct market access, automated execution, customized algorithmic trading, and tailored liquidity streams. LTP materials also identify Liquidity Fintech Investment Limited as investment manager of Liquidity Investment SPC, and an SEC Form D identifies Crypto Quant Fund SP as a segregated portfolio of Liquidity Investment SPC.
- Audit Yes boundary notes: otc_trading=yes because LTP officially launched an Over-the-Counter trading platform with custom RFQs and block trade workflows, and other official materials describe regulated OTC block trading.|algorithm_trading=yes because official product and FAQ pages explicitly reference customized algorithmic trading, quantitative traders, high-frequency traders, ultra-low-latency access, DMA, and low-latency market data.|market_making=yes because LTP officially markets liquidity distribution, deep liquidity pools, tight spreads, tailored liquidity streams, and OTC infrastructure serving liquidity takers and market makers, which crosses the liquidity-provision threshold.|execution_services=yes because LTP explicitly offers prime brokerage, trade execution, Smart Order Routing, cross-exchange execution, DMA, liquidity access, and brokerage-style clearing/settlement services.|defi=yes because LTP itself markets infrastructure that gives institutions access to decentralized exchanges and integrates CeFi and DeFi liquidity, not merely investments in DeFi companies.|sub_fund=yes because official and SEC evidence show LTP-affiliated investment management for Liquidity Investment SPC and a named Crypto Quant Fund SP, a segregated portfolio of that SPC.
- Audit No boundary notes: Portfolio-company evidence, including Cycle Network, was not used to attribute capabilities.|Partner capabilities from Finery Markets, DV Chain, Wincent, CyantArb, or Kronos were not independently attributed to LTP except where LTP's own official materials describe LTP's platform or role.|Generic asset-management language alone would not satisfy sub_fund; the sub_fund decision relies on explicit SPC and segregated-portfolio evidence.

### 32. LD Capital - task 7

- In `needs_manual_review.csv`: no
- Results labels: `["sub_fund"]`
- Audit labels: `["market_making", "sub_fund"]`
- Mismatched capabilities: `market_making`
- Original evidence summary: Official site says LD Capital is a crypto fund trading primary and secondary markets with multiple sub-funds, so sub_fund is warranted.
- Audit evidence summary: LD Capital's official site describes it as a crypto fund investing and trading in primary and secondary markets and explicitly states that its sub-funds include Beco Fund, FoF, hedge fund, Meta Fund, etc. A post by LD Capital says LD Capital, Antalpha Ventures, and Highblock jointly established a Hong Kong ETF liquidity fund designed to provide market-making services to Hong Kong ETFs. I found no explicit evidence that LD Capital itself offers OTC/block/bilateral trading, algorithmic/systematic/HFT trading, execution/order-routing/brokerage services, or a DeFi-native operating product beyond investing in DeFi portfolio companies.
- Audit Yes boundary notes: market_making=yes because LD Capital's own announcement says a jointly established ETF liquidity fund is designed to provide market-making services to Hong Kong ETFs.|sub_fund=yes because LD Capital's official site explicitly says its sub-funds include Beco Fund, FoF, hedge fund, Meta Fund, etc.
- Audit No boundary notes: Primary and secondary market trading language is not explicit OTC desk, block trading, or bilateral trading evidence.|Highblock's quantitative trading expertise in the joint ETF liquidity fund announcement was not attributed directly to LD Capital as LD Capital's own algorithmic trading capability.|The ETF liquidity fund evidence supports market-making, but it does not explicitly describe LD Capital providing execution, smart order routing, brokerage, prime brokerage, or order-routing services.|LD Capital markets DeFi investments and has DeFi portfolio exposure, but funding or listing DeFi startups alone is insufficient for defi=yes under the rule.

### 33. Mars Ecosystem - task 3039

- In `needs_manual_review.csv`: no
- Results labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|execution_services`
- Original evidence summary: Mars docs describe a decentralized stablecoin ecosystem with Mars Swap, Mars Stableswap, and Mars Money Market, which is explicit DeFi-native operation.
- Audit evidence summary: Mars Ecosystem's official documentation describes it as a decentralized stablecoin ecosystem made up of Mars Treasury, Mars Stablecoin, and Mars DeFi protocols. Its Mars DeFi protocols include Mars Swap and Mars StableSwap; Mars Swap is explicitly described as a Uniswap-type AMM DEX that incentivizes liquidity provision and USDm transactions, and the Mars Treasury uses assets to provide liquidity for USDm on Mars Swap. The same documentation states users trade on Mars DeFi protocols and pay transaction fees. I found no attributable evidence that Mars Ecosystem operates an OTC desk/block trading service, algorithmic/quant/HFT trading operation, or any sub-fund/feeder/umbrella/SPV/fund-of-funds structure.
- Audit Yes boundary notes: defi=yes because Mars Ecosystem itself officially operates/markets Mars DeFi protocols as part of its own decentralized stablecoin ecosystem.|market_making=yes because Mars Swap is explicitly an AMM DEX and the Mars Treasury provides liquidity for USDm on Mars Swap, satisfying the AMM/liquidity-pool operated-by-entity threshold.|execution_services=yes because Mars Ecosystem operates swap/DEX venues, Mars Swap and Mars StableSwap, where users trade and execute transactions on the protocol.
- Audit No boundary notes: otc_trading=no because there is no explicit Mars Ecosystem OTC desk, block trading, or bilateral trading evidence; similarly named MarsBase OTC results are not attributable to Mars Ecosystem.|algorithm_trading=no because an automated market-maker DEX is not evidence of Mars Ecosystem running algorithmic, quantitative, systematic, HFT, or low-latency trading strategies.|sub_fund=no because the evidence describes a token/stablecoin/DeFi protocol ecosystem, not a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds.

### 34. Kraken - task 2410

- In `needs_manual_review.csv`: no
- Results labels: `["otc_trading", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `algorithm_trading|market_making|defi`
- Original evidence summary: Official Kraken OTC pages say traders can execute orders off the open exchange and access deeper liquidity, tighter spreads, and OTC trading from Kraken Custody, Kraken Pro, and chat.
- Audit evidence summary: Kraken explicitly operates an OTC desk for off-exchange orders, RFQ/block trading, and execution/settlement services. Kraken Prime markets Prime Execution, multi-venue liquidity access, and smart order routing, while Kraken Institutional markets ultra-low-latency APIs, HFT support, deep liquidity, and market-maker-oriented products. Kraken's API pages explicitly support automated trading and advanced strategies. Kraken Wallet and DeFi Earn are Kraken/Payward products providing DeFi position management, decentralized-app interaction, and onchain DeFi vault exposure. I found no qualifying Kraken sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence attributable to Kraken as the investor.
- Audit Yes boundary notes: otc_trading=yes because Kraken's own OTC desk executes orders off the open exchange and supports RFQ and large block trading.|algorithm_trading=yes because Kraken markets automated API-based trading, low-latency infrastructure, FIX/WebSocket/REST APIs, and HFT/high-frequency strategy support through its own platform.|market_making=yes because Kraken's operated OTC/Prime/institutional platform provides deep and multi-venue liquidity, executable quotes, and products specifically for market makers.|execution_services=yes because Kraken explicitly offers execution and settlement services, Prime Execution, smart order routing, and liquidity access.|defi=yes because Kraken operates Kraken Wallet and DeFi Earn, which explicitly support DeFi positions, decentralized-app interaction, and onchain DeFi vault exposure.
- Audit No boundary notes: Kraken Ventures or ordinary investment activity was not treated as sub_fund evidence.|Third-party or externally marketed SPV references involving access to Payward/Kraken equity were not treated as a Kraken-operated sub-fund or feeder structure.|Educational content about DeFi, LP tokens, or AMMs was not needed to establish DeFi; the yes decision relies on Kraken-operated Wallet and DeFi Earn products.

### 35. Terraform Labs - task 2517

- In `needs_manual_review.csv`: no
- Results labels: `["defi"]`
- Audit labels: `["execution_services", "defi"]`
- Mismatched capabilities: `execution_services`
- Original evidence summary: Terra documentation describes an open-source blockchain with decentralized applications, an unparalleled DeFi experience, and algorithmic stablecoin mechanics, which fits the DeFi label.
- Audit evidence summary: Terra official docs describe Terra as an open-source blockchain hosting decentralized applications and providing a DeFi experience. The SEC amended complaint states that Terraform developed and marketed the Terraform blockchain and related protocols, launched Anchor Protocol, launched and maintained Mirror Protocol, controlled websites related to Mirror, and made mAssets available through a Terraform-controlled site where users could create, trade, or buy mAssets. The complaint also says Terraform created, offered, sold, and effected mAsset transactions through Mirror Protocol. No public evidence found in the reviewed sources supports OTC/block trading, algorithmic trading, market making/liquidity provision by Terraform itself, or any sub-fund/feeder/umbrella/SPV/fund platform capability.
- Audit Yes boundary notes: defi=yes because Terraform itself developed and marketed DeFi-native blockchain/protocol products, including Terra, Anchor Protocol, and Mirror Protocol, rather than merely investing in DeFi companies.|execution_services=yes because Terraform-controlled Mirror Protocol/web interfaces enabled users to create, trade, or buy mAssets and the SEC complaint says Terraform effected transactions through Mirror Protocol, crossing the DEX/trading venue execution threshold.
- Audit No boundary notes: otc_trading=no because there was no explicit Terraform OTC desk, block trading, or bilateral trading service evidence.|algorithm_trading=no because references to algorithmic stablecoin mechanics are not evidence of algorithmic, quantitative, systematic, HFT, or low-latency trading capability.|market_making=no because references to liquidity, UST peg support, or third-party market activity do not show Terraform itself explicitly offering market making or liquidity provision services.|sub_fund=no because there was no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.

### 36. Kain Warick - task 9730

- In `needs_manual_review.csv`: no
- Results labels: `["defi"]`
- Audit labels: `["market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|execution_services`
- Original evidence summary: Synthetix describes itself as the first decentralized perpetual futures protocol, and official blog posts identify Kain Warwick as founder.
- Audit evidence summary: Public evidence appears to identify the input investor as Kain Warwick, with the input/CB Insights spelling variant Kain Warick. Official Infinex material identifies Kain Warwick as Infinex Founder and describes Infinex features for cross-chain swaps and access to DeFi/onchain protocols. Official Synthetix material identifies Kain Warwick as Founder of Synthetix, and Synthetix docs describe Synthetix as a DeFi derivatives liquidity protocol with liquidity providers, market makers, and a community market-making vault backing perps markets. No public evidence found for OTC/block/bilateral trading, algorithmic/quant/systematic/HFT trading, or sub-fund/feeder/SPV/fund-platform capability for the individual investor.
- Audit Yes boundary notes: defi=yes because official Synthetix and Infinex sources tie Kain Warwick to founder roles in DeFi/onchain protocols, not merely passive startup funding.|execution_services=yes because Infinex officially offers swap/bridge functionality and access to onchain protocols, and Synthetix is a trading/perps platform; exchange/swap venues meet the execution-services threshold.|market_making=yes because Synthetix official docs explicitly describe market makers/liquidity providers and a community-operated market-making vault backing perps markets, attributable through Kain Warwick's founder/co-founder/advisory relationship.
- Audit No boundary notes: Layer3 angel investment alone was not used to infer DeFi capability.|No explicit OTC desk, block trading, or bilateral trading evidence was found.|No explicit algorithmic, quantitative, systematic, HFT, or low-latency trading evidence was found.|No explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence was found.

### 37. MetaStreet - task 10561

- In `needs_manual_review.csv`: no
- Results labels: `["defi"]`
- Audit labels: `["execution_services", "defi"]`
- Mismatched capabilities: `execution_services`
- Original evidence summary: MetaStreet's official site describes Yield Pass, Borrow, and a DeFi ecosystem; protocol docs describe permissionless pools for NFT collateral, fixed-duration loans, and liquidity routing.
- Audit evidence summary: MetaStreet's official site and docs describe a DeFi-oriented protocol/product suite for yield, borrowing, lending pools, Liquid Credit Tokens, and NFT/object collateral. The docs state that MetaStreet/Permian Labs develops DeFi primitives, that the ATM is a permissionless lending protocol, that borrowers accept aggregated loan offers, and that the Borrow interface lets holders use NFT/object collateral to take loans. Its technical docs also describe liquidity sourcing and tick routing by the MetaStreet SDK. No public evidence found for OTC/block trading, algorithmic or HFT trading, market making as a trading/AMM operator, or sub-fund/feeder/SPV/fund platform activity.
- Audit Yes boundary notes: defi=yes because MetaStreet itself operates and markets DeFi-native lending/yield infrastructure, including a permissionless lending protocol and composable ERC-20 credit tokens.|execution_services=yes because MetaStreet provides explicit liquidity access and routing for loan execution: borrowers accept aggregated offers through its Borrow interface, liquidity is sourced from ticks, and the MetaStreet SDK performs tick routing.
- Audit No boundary notes: otc_trading=no: no explicit OTC desk, block trading, or bilateral trading service evidence.|algorithm_trading=no: the tick routing algorithm is for assembling DeFi loans, not algorithmic, quantitative, systematic, HFT, or low-latency trading.|market_making=no: MetaStreet operates lending/liquidity infrastructure, but I did not find explicit evidence that MetaStreet itself provides two-sided market making or operates an AMM/liquidity pool as market maker.|sub_fund=no: no evidence of a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds.

### 38. Chingari - task 2819

- In `needs_manual_review.csv`: yes
- Results labels: `[]`
- Audit labels: `["defi"]`
- Mismatched capabilities: `defi`
- Original evidence summary: Chingari’s public site shows a short-video/live-audio app with live streaming and on-chain users; the blog also documents investor rounds, confirming the row is really describing an operating platform.
- Audit evidence summary: Chingari/GARI Network publicly markets and operates a Web3/on-chain creator economy with GARI token usage, on-chain users, GARI staking, DAO governance, NFT marketplace features, and wallet infrastructure. The key-features page states GARI holders can stake and earn yield and vote on proposals, while Chingari Wallet markets Web3 wallet, NFT, and staking services. I found no explicit evidence that Chingari itself provides OTC/block trading, algorithmic or quantitative trading, market making/liquidity provision, brokerage/order routing/liquidity access, or any sub-fund/feeder/umbrella/parallel fund/SPV/fund platform capability.
- Audit Yes boundary notes: defi crosses the threshold because Chingari itself, through GARI Network and Chingari Wallet, operates and markets DeFi-native staking/yield, DAO governance, token, NFT, and Web3 wallet capabilities rather than merely investing in DeFi companies.
- Audit No boundary notes: External exchange listings and 'Buy GARI' links are not Chingari-operated execution, brokerage, order routing, OTC, or market-making services.|The official roadmap mentions DEX integration, but that is not enough to classify execution_services without clear current Chingari-operated swap/execution capability.|Wallet and NFT marketplace features, including NFT trading support, do not establish securities/crypto execution services under the Part6 execution-services rule.|No evidence found for algorithmic, quantitative, systematic, HFT, or low-latency trading by Chingari.|No evidence found for sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds activity.

### 39. Hawkwood Capital - task 8910

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["sub_fund"]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: Current official/site and registry evidence identifies Hawkwood Capital LLP as an FCA-authorised boutique fund manager/adviser and active UK LLP. The current sources reviewed did not evidence OTC desks, algorithmic/systematic trading, market making/liquidity provision, execution services, DeFi-native activity, or current feeder/umbrella/parallel/SPV/fund-of-funds structure.
- Audit evidence summary: Hawkwood's official site describes the firm as an FCA-regulated boutique fund manager managing differentiated funds and also as a corporate advisory/capital-raising business. The Hawkwood Commodities Fund prospectus names Hawkwood Capital LLP as investment adviser to both the Fund and the Master Fund and contains explicit master/feeder-fund structure language. A Hawkwood Deep Value Fund application form also references the Fund, Master Fund, Investment Manager, and Administrator. I found no evidence that Hawkwood itself operates an OTC/block/bilateral trading desk, algorithmic/systematic/HFT trading platform, market-making or liquidity-provision business, order-execution/routing/prime brokerage service, or DeFi-native product/capability.
- Audit Yes boundary notes: sub_fund=yes because official Hawkwood fund documentation explicitly references a Fund/Master Fund structure and feeder-fund language, with Hawkwood Capital LLP appointed to provide investment advisory services to the Fund and Master Fund.
- Audit No boundary notes: Hawkwood's official pages use corporate finance broker/advisory and capital-raising language, but this is not explicit trading execution, order routing, prime brokerage, or liquidity-access evidence for execution_services.|Fund management, hedge fund promotion, investment advice, corporate advisory, and capital raising do not establish OTC trading, algorithmic trading, market making, or DeFi capabilities under the Part6 thresholds.|Any portfolio-company or transaction exposure, including fintech or token-company context from the input row, was not treated as Hawkwood's own DeFi capability.

### 40. Ethan Francis - task 8182

- In `needs_manual_review.csv`: yes
- Results labels: `[]`
- Audit labels: `["execution_services", "defi"]`
- Mismatched capabilities: `execution_services|defi`
- Original evidence summary: 6DOS confirms the task-row biography of Ethan Francis as Founder and CEO of a B2B SaaS company. Current crypto sources show an Ethan Francis associated with Particle Network and a Web3 AI angel round, but the same-person link and investor capability boundary remain ambiguous. No evidence supports marking the investor record for OTC, algorithmic trading, market making, execution services, DeFi-native operation, or sub-fund structures.
- Audit evidence summary: The local input identifies Ethan Francis as an individual angel and Founder/CEO of 6DOS; 6DOS is described publicly as a relationship/SaaS software company and does not evidence trading, market making, DeFi, or fund-structure capabilities. Public Assisterr funding coverage identifies an angel named Ethan Francis as Head of Developer Relationships at Particle Network, and a secondary Particle profile identifies Ethan Francis as COO. Particle official documentation says UniversalX, built by Particle Network, is a non-custodial chain-agnostic trading platform that lets users trade tokens across chains, routes balances, and executes trades through Universal Accounts. Particle documentation also lists UniversalX under DeFi & Trading integrations. Because the capability attribution for this individual depends on the public Particle operating role matching this investor, manual review is recommended.
- Audit Yes boundary notes: execution_services=yes because Particle's official UniversalX documentation describes a non-custodial trading platform that routes user balances across chains and executes trades, which crosses the execution/trading venue threshold when attributed through Ethan Francis's reported COO/executive role.|defi=yes because Particle/UniversalX is an onchain, non-custodial Web3 trading product listed by Particle documentation under DeFi & Trading, and the public profile ties Ethan Francis to Particle in an executive operating role.
- Audit No boundary notes: Assisterr is only portfolio/investment evidence and does not itself confer DeFi capability to Ethan Francis.|6DOS official materials show a SaaS relationship/networking company, not OTC trading, algorithmic trading, market making, execution services, DeFi specialization, or sub-fund activity.|Particle references to Universal Liquidity, solvers, and cross-chain routing support execution/liquidity access, but they do not explicitly show Ethan Francis or Particle operating an OTC desk, algorithmic/HFT strategy, market-making desk, AMM liquidity pool, or fund/sub-fund/SPV platform.

### 41. Sebastian Serrano - task 12187

- In `needs_manual_review.csv`: yes
- Results labels: `[]`
- Audit labels: `["otc_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `otc_trading|market_making|execution_services|defi`
- Original evidence summary: Ripio’s official site identifies Sebastian Serrano as co-founder/CEO and advertises crypto exchange, OTC desk, crypto-as-a-service, DeFi access, and liquidity-provider services. Those capabilities belong to the company, so they are not mapped directly onto the individual investor row.
- Audit evidence summary: Official Ripio materials identify Sebastian Serrano as Co-founder & CEO of Ripio and managing partner at Ripio Ventures. Ripio's institutional and OTC pages describe an OTC desk for high-volume crypto/fiat trades, private-book trading, immediate liquidity, execution of large transactions, and crypto trading/custody. Ripio Select says it is focused on providing liquidity to institutional and high-net-worth clients. Ripio's DeFi page describes the Ripio DeFi feature enabling users to deposit and withdraw funds in Compound, Aave, and Yearn from Ripio Wallet. I found no explicit algorithmic, quantitative, systematic, HFT, low-latency trading evidence, and no feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.
- Audit Yes boundary notes: otc_trading crosses the threshold because Ripio explicitly markets an OTC desk and OTC service for high-volume crypto/fiat trades.|market_making crosses the threshold because Ripio Select explicitly says the service is focused on providing liquidity, and the OTC materials describe immediate liquidity for institutional trading.|execution_services crosses the threshold because Ripio describes executing large transactions, private-book OTC trading, crypto trading/custody, and direct purchase/sale transactions through its OTC desk.|defi crosses the threshold because Ripio itself operates and markets Ripio DeFi, including access to DeFi protocols and deposits/withdrawals through Compound, Aave, and Yearn.
- Audit No boundary notes: Trading API or automated-trading references were not enough for algorithm_trading because I found no explicit algorithmic, quantitative, systematic, HFT, or low-latency trading claim.|Ripio Ventures' Web3 and DeFi investing focus was not used by itself to infer DeFi capability; the DeFi yes decision relies on Ripio's operated DeFi product.|No sub_fund evidence was found; ordinary venture investing, managing partner status, or a venture platform is insufficient without explicit SPV, feeder, umbrella, parallel fund, fund platform, or fund-of-funds language.|Maker/taker fee schedules and exchange-user terminology were not used by themselves to infer market_making; the market_making yes decision relies on explicit liquidity-provision language.

### 42. Charles Read - task 2297

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["market_making", "defi"]`
- Mismatched capabilities: `market_making|defi`
- Original evidence summary: LinkedIn, Coinspeaker, and Signal profiles tie Charles Read to Rarestone Capital and other blockchain advisory roles, indicating a crypto-native angel/investor profile but no trading or execution desk.
- Audit evidence summary: Rarestone's official team page identifies Charles Read as Founding Partner and says he heads strategy and go-to-market for the portfolio and Labs team. Rarestone Labs officially markets DeFi-relevant token economics/protocol design expertise and explicitly offers liquidity providing strategies for on-chain launches, including LP incentive campaigns and concentrated liquidity. Noir's profile further supports that Charles founded Rarestone, a blockchain venture firm. No evidence found for OTC/block/bilateral trading, algorithmic/quant/systematic/HFT trading, execution/order-routing/brokerage services, or sub-fund/feeder/umbrella/SPV/fund-of-funds activity.
- Audit Yes boundary notes: market_making=yes because Rarestone Labs explicitly markets liquidity providing strategies for on-chain launches, including LP incentive campaigns and concentrated liquidity, and Charles is explicitly tied to leading the Labs team.|defi=yes because Rarestone Labs explicitly markets DeFi-native protocol/token economics capability, stating its team has been at the forefront since the emergence of DeFi, and Charles is a founding partner tied to Labs leadership.
- Audit No boundary notes: Rarestone says it trades and invests its own capital, but there is no explicit OTC desk, block trading, or bilateral trading evidence.|References to traders, market exposure, and on-chain participation do not establish algorithmic, quantitative, systematic, HFT, or low-latency trading.|Warm introductions to exchanges and market makers are not execution services, smart order routing, brokerage, prime brokerage, or liquidity-access services operated by Charles or Rarestone.|Standard fund/AUM descriptions and venture investing do not establish a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds.

### 43. Sanctor Capital - task 365

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["defi", "sub_fund"]`
- Mismatched capabilities: `defi|sub_fund`
- Original evidence summary: Official site shows a thesis-driven investment fund with pre-accelerator support and web3 mentorship.
- Audit evidence summary: Sanctor's official venture page describes the firm as a thesis-driven investment fund deploying capital across gaming, infrastructure, and DeFi in web3 at pre-seed and seed stages, which supports DeFi specialization/product exposure. A SEC Form D identifies Sanctor Capital Management, LLC as issuer manager for a pooled investment fund issuer named Sanctor Powerus I - Sanctor Master Series LLC, supporting a series/SPV-style fund vehicle. I found no explicit evidence that Sanctor itself operates OTC/block trading, algorithmic or quantitative trading, market making/liquidity provision, execution, routing, brokerage, prime brokerage, or liquidity-access services.
- Audit Yes boundary notes: defi=yes because Sanctor's own official site explicitly markets DeFi as one of the web3 areas where its investment fund deploys capital, not merely because of a portfolio-company investment.|sub_fund=yes because the SEC filing ties Sanctor Capital Management to a pooled investment issuer using a Master Series LLC structure, indicating a series/SPV-style vehicle rather than only a standard closed fund.
- Audit No boundary notes: Crypto/web3 venture investing and tokenomics guidance do not establish OTC trading, algorithmic trading, market making, or execution-services capability without explicit trading desk, systematic trading, liquidity provision, order-routing, brokerage, or prime-brokerage evidence.|Portfolio exposure to blockchain or DeFi companies was not treated as evidence of trading or market-structure capabilities operated by Sanctor itself.

### 44. Gracy Chen - task 4104

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["otc_trading", "algorithm_trading", "execution_services", "defi"]`
- Mismatched capabilities: `otc_trading|algorithm_trading|execution_services|defi`
- Original evidence summary: Bitget's official about page and CEO announcement identify Gracy Chen as CEO and an early investor in Bitget Wallet; no separate trading or execution desk is claimed for the individual investor.
- Audit evidence summary: Official Bitget materials identify Gracy Chen as CEO, and a Bitget-issued PR says she became CEO in May 2024 after serving as Managing Director. Bitget operates an OTC product for over-the-counter fiat/crypto and crypto/fiat trading, with large-order trading, professional execution, deeper liquidity, and competitive quotes. Bitget also markets algorithm-driven bot copy trading and trading bots that execute preset buy/sell actions continuously. Bitget API documentation supports programmatic trading for spot, futures, copy trading, market makers, quantitative trading, and third-party platforms sharing Bitget liquidity. Bitget Onchain and Bitget Wallet documentation show on-chain token trading, DApp access, DeFi support, swaps, bridges, and multi-chain Web3 functionality. I found no explicit evidence that Gracy Chen or Bitget operates a market-making desk/liquidity pool as principal, and no sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.
- Audit Yes boundary notes: otc_trading=yes because Bitget explicitly operates Bitget OTC, described as an over-the-counter trading platform for digital assets with large-order trading and professional execution.|algorithm_trading=yes because Bitget explicitly describes bot copy trading/trading bots as algorithm-driven, automated tools executing preset buy and sell actions continuously.|execution_services=yes because Bitget is an exchange platform with spot/futures trading, OTC professional execution, APIs for programmatic order placement, and liquidity access.|defi=yes because Bitget operates/markets Bitget Onchain and Bitget Wallet features for on-chain trading, DApp access, DeFi, swaps, bridges, and multi-chain Web3 use; Gracy Chen is explicitly CEO of Bitget.
- Audit No boundary notes: Bitget has a market maker incentive/liquidity program and serves external market makers, but that is not explicit evidence that Gracy Chen or Bitget itself provides market making as principal or operates an AMM/liquidity pool.|Portfolio/startup investing and Gracy Chen's early investment in Bitget Wallet alone would not confer capabilities, but the CEO role at Bitget makes operating-platform attribution relevant.|No evidence found for sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds activity.

### 45. Keisuke Honda - task 2188

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["sub_fund"]`
- Mismatched capabilities: `sub_fund`
- Original evidence summary: Skipped: generic angel investor with no meaningful crypto-native signal.
- Audit evidence summary: Keisuke Honda's official site describes him as investing globally in startups and lists KSK Angel Fund and Dreamers Fund. X&'s official site describes a multi-fund investment platform with five funds and X&KSK associated with Keisuke Honda. A company press release identifies Honda as Co-Founder & General Partner of X&KSK and describes X&KSK I as an investment limited partnership. FinCity's profile names Honda as founder and states X& provides services for individuals establishing venture funds, including capital anchoring and fund management. No public evidence found that Honda or his attributable platforms operate OTC/block trading, algorithmic trading, market making, trading execution/order routing/brokerage, or DeFi-native products.
- Audit Yes boundary notes: sub_fund crosses the threshold because public sources explicitly connect Honda as founder/co-founder/general partner to X&KSK/X&, and a profile describes X& as providing venture-fund establishment, capital anchoring, and fund-management services, while the official X& site describes a multi-fund platform.
- Audit No boundary notes: Blockchain, crypto, Web3, NFT, Celo, Alchemy, and Staked exposure appears to be investment or portfolio exposure, not Honda operating or marketing a DeFi-native capability.|X&/Sanbo references AI-powered investment analysis, private-market investment management, and financial transaction management, but not algorithmic trading, HFT, execution, order routing, brokerage, prime brokerage, OTC trading, or liquidity access.|Standard VC funds such as KSK Angel Fund, Dreamers Fund, and X&KSK I alone would not be enough for sub_fund; the yes determination relies on the explicit fund-establishment/fund-management platform evidence.

### 46. Sportzchain - task 12543

- In `needs_manual_review.csv`: no
- Results labels: `[]`
- Audit labels: `["execution_services", "defi"]`
- Mismatched capabilities: `execution_services|defi`
- Original evidence summary: Skipped capability search; batch record only.
- Audit evidence summary: Sportzchain's official FAQ describes an operated fan-token platform where $SPN enables users to buy and sell sports/fan tokens, and says fans can buy and sell those tokens on Sportzchain's platform. Its official about page describes a web3 sports app, sports tokens, NFTs, GameFi, watch-to-earn, staking rewards, a planned proprietary exchange for trading sports tokens, and DeFi programs. Its official token page markets $SPN staking rewards. CoinMarketCap similarly describes Sportzchain as an engage-to-earn webDapp with buying sports tokens, staking APY, NFTs, GameFi, and fan-token redemption. I found no explicit evidence for OTC/block trading, algorithmic/quant/systematic trading, market making/liquidity provision, or sub-fund/feeder/SPV/fund-platform activity.
- Audit Yes boundary notes: execution_services crosses the threshold because Sportzchain itself operates or markets a token platform/venue where users can buy and sell sports/fan tokens; exchange or swap venues can support execution_services under the boundary rule.|defi crosses the threshold because Sportzchain itself markets DeFi-native/token product exposure including $SPN staking rewards and explicitly references DeFi programs on its official site.
- Audit No boundary notes: The evidence mentions token trading and external exchange listings, but not an OTC desk, block trading, or bilateral trading by Sportzchain.|The evidence mentions blockchain, web3, fan tokens, and staking, but not algorithmic, quantitative, systematic, HFT, or low-latency trading.|The evidence mentions tokenomics liquidity allocation and buy/burn language, but not explicit market making, liquidity provision, AMM operation, or liquidity pools operated by Sportzchain.|The evidence shows a company token platform and investor/partner references, but no sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.

### 47. Alameda Research - task 46

- In `needs_manual_review.csv`: yes
- Results labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `defi`
- Original evidence summary: Historical sources and the court record describe Alameda as a quantitative trading firm, liquidity provider, and market maker with OTC activity; because the entity is defunct and the evidence base is historical, manual review is warranted.
- Audit evidence summary: Alameda crosses the OTC, algorithmic trading, market making, execution services, and DeFi thresholds. Public sources describe Alameda as operating an OTC desk and providing OTC liquidity, with an Alameda Head of OTC desk quoted on connecting to global clients and providing pricing. The SEC complaint states Alameda was often the Binance.US OTC Desk's only counterparty from May 2020 to February 2022. A transcribed Alameda pitch deck says Alameda provided exchange liquidity and serviced OTC trades 24/7, used algorithmic machine-learning-driven automatic trading systems, quoted buy and sell prices for market making, and used execution strategies. A profile reproducing Alameda's first-person description also references market-neutral algorithms, execution strategies, automated trading systems, OTC quoting, and market-making partnerships. Blockworks reports a Maple Finance loan product designed to provide institutional exposure to Alameda's DeFi trading yields, indicating Alameda's own DeFi-related trading/yield activity rather than only portfolio investment. I found no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence.
- Audit Yes boundary notes: otc_trading=yes because sources explicitly identify Alameda's OTC desk/OTC business, OTC quotes, OTC liquidity provision, and counterparty role for Binance.US OTC trades.|algorithm_trading=yes because Alameda's materials explicitly cite algorithmic, machine-learning-driven automatic trading systems, market-neutral algorithms, quantitative strategies, and sophisticated automated trading systems.|market_making=yes because Alameda's materials explicitly describe market making, quoting buy and sell prices, market-making partnerships, and providing liquidity on exchanges.|execution_services=yes because Alameda's first-person profile explicitly cites execution strategies and its OTC client-facing quote/pricing/liquidity workflow supports execution of large crypto trades.|defi=yes because Blockworks describes institutional exposure to Alameda's DeFi trading yields from Alameda's own trading activities, not merely Alameda funding DeFi startups.
- Audit No boundary notes: sub_fund=no because fixed-rate loans, syndicated loans, or possible separate loan series are not explicit sub-funds, feeders, umbrella funds, parallel funds, SPVs, fund platforms, or fund-of-funds.|Portfolio investments in DeFi projects were not used by themselves to justify defi=yes; the yes decision relies on Alameda's own DeFi trading-yield activity.

### 48. Bixin Ventures - task 112

- In `needs_manual_review.csv`: yes
- Results labels: `[]`
- Audit labels: `["execution_services", "defi", "sub_fund"]`
- Mismatched capabilities: `execution_services|defi|sub_fund`
- Original evidence summary: Bixin Ventures presents itself as a venture investor in open-finance infrastructure, and its parent Bixin Group operates wallet and liquidity-provider businesses.
- Audit evidence summary: Bixin Ventures' official site identifies it as an investor in crypto networks and open financial systems and ties it to Bixin Group's operating crypto infrastructure. Bixin.com support documentation describes an exchange and off-platform system with explicit order placement and trade execution through liquidity providers, supporting execution_services for the attributable Bixin operating platform. Bixin Ventures announced a $100M proprietary fund for open finance/decentralized infrastructure, and reporting explicitly describes the fund as focused on scaling DeFi. Bixin Ventures/Bixin Global also announced a proprietary fund of funds, satisfying sub_fund. I did not find sufficient evidence that Bixin Ventures itself operates OTC trading, algorithmic trading, or market making.
- Audit Yes boundary notes: execution_services=yes because Bixin.com documentation explicitly describes exchange and off-platform trade execution, order placement, and execution through liquidity providers on the attributable Bixin operating platform.|defi=yes because Bixin Ventures explicitly launched capital focused on open finance through permissionless decentralized networks, with reporting describing the purpose as scaling decentralized finance.|sub_fund=yes because Bixin Ventures/Bixin Global explicitly announced a proprietary fund of funds.
- Audit No boundary notes: otc_trading=no because the evidence mentions OTC lending and off-platform trading without an order book, but I did not find explicit OTC desk, block trading, or bilateral OTC trading operated by Bixin Ventures.|algorithm_trading=no because references to quant funds, arbitrage, CTA, and trend strategies relate to external funds or personnel history, not Bixin Ventures operating algorithmic, quantitative, systematic, HFT, or low-latency trading.|market_making=no because Bixin.com documents independent third-party market makers/liquidity providers and the fund-of-funds supports liquidity providers, but that is not enough to show Bixin Ventures itself provides market making.

### 49. Jump Crypto - task 94

- In `needs_manual_review.csv`: no
- Results labels: `["algorithm_trading"]`
- Audit labels: `["algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `market_making|execution_services|defi`
- Original evidence summary: Jump Crypto describes itself as the crypto division of Jump Trading Group and frames its work around active participation in crypto markets and trading intelligence.
- Audit evidence summary: Jump Crypto's official materials describe it as an active crypto market participant, liquidity provider, and builder of DeFi/onchain market infrastructure. Its PropAMM article describes BisonFi as Jump Crypto's own PropAMM, with an offchain pricing engine, onchain execution program, executable bids/offers, continuous repricing, and market-making logic. Jump Trading's official pages also support the attributable operating-platform context: the parent trades digital assets and uses high-frequency/stat-arb strategies plus ML-driven low-latency trading systems. I found no explicit Jump Crypto OTC desk, block/bilateral trading service, or sub-fund/feeder/SPV/fund-platform evidence.
- Audit Yes boundary notes: algorithm_trading=yes because official Jump Crypto PropAMM materials describe continuous offchain pricing models, frequent oracle updates, proprietary logic, and executable onchain liquidity; Jump Trading's official trading pages also explicitly reference high-frequency and stat-arb strategies across digital assets.|market_making=yes because Jump Crypto explicitly says it is an active market participant and liquidity provider on Serum, and its PropAMM article describes market-making logic in its own BisonFi system.|execution_services=yes because BisonFi/PropAMM is described as an onchain execution program providing executable bids and offers where user swaps settle directly against onchain liquidity.|defi=yes because Jump Crypto's official materials explicitly frame its work around DeFi, onchain AMMs, Serum, Pyth, Wormhole, and permissionless market-structure infrastructure, not merely passive investments.
- Audit No boundary notes: otc_trading=no because active trading, liquidity provision, and direct onchain execution evidence did not include an explicit OTC desk, block trading, or bilateral trading service for Jump Crypto.|sub_fund=no because the official site states Jump Crypto does not operate business lines accepting external investor funds, and no sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds evidence was found.|Portfolio investments in DEXs, AMMs, wallets, exchanges, and DeFi protocols were not used by themselves to infer capabilities.

### 50. Jump Trading - task 1030

- In `needs_manual_review.csv`: no
- Results labels: `["algorithm_trading"]`
- Audit labels: `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`
- Mismatched capabilities: `otc_trading|market_making|execution_services|defi`
- Original evidence summary: Official site describes Jump Trading as a global trading firm and its technology stack supporting research trading and data efforts which directly supports algorithmic trading
- Audit evidence summary: Jump Trading's official trading page says its strategies span high-frequency and stat-arb trading across asset classes, supporting algorithm_trading. Jump Crypto, identified as the crypto division of Jump Trading Group, is described in a company press release as active in trading and market-making activities, and its official materials describe DeFi development, Solana DeFi trading, Pyth/Wormhole/Firedancer infrastructure, and active crypto market participation. Jump Liquidity materials describe a Jump Trading-created business providing clients direct access to Jump principal liquidity, enhanced access to liquidity, and customizable direct counterparty liquidity. Risk.net explicitly reports that Jump Trading launched a bilateral business. No evidence found for a sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds capability; Jump Crypto also states it does not accept external investor funds.
- Audit Yes boundary notes: algorithm_trading=yes because the official Jump Trading site explicitly describes high-frequency trading strategies.|market_making=yes because Jump Crypto is explicitly described as participating in market-making activities, and Jump Liquidity is described as created by Jump Trading, one of the world's leading market makers.|execution_services=yes because Jump Liquidity is explicitly described as providing direct/enhanced access to Jump principal liquidity and customizable liquidity streams to clients/counterparties.|otc_trading=yes because Risk.net explicitly describes Jump Trading launching a bilateral business, satisfying the bilateral trading threshold.|defi=yes because Jump Crypto is a clearly attributable Jump Trading Group division, and official/company materials explicitly describe DeFi development and trading on Solana DeFi, not merely passive funding of DeFi startups.
- Audit No boundary notes: sub_fund=no because evidence showed operating trading, liquidity, crypto infrastructure, and venture/investment activity, but no explicit sub-fund, feeder, umbrella, parallel fund, SPV, fund platform, or fund-of-funds structure.|Portfolio investments in DEXs, AMMs, wallets, and crypto infrastructure were not used by themselves to infer capabilities; DeFi was marked yes only due to Jump Crypto's own stated DeFi activity and infrastructure role.
