# Part6 Random-30 GPT-5.5 High Capability Audit

## 生成資訊

- generated_at_utc: 2026-06-08T09:51:54.871476+00:00
- generated_at_los_angeles: 2026-06-08T02:51:54.871700-07:00
- sample_seed: 20260608
- sample_size: 30
- subagent_model: gpt-5.5
- reasoning_effort: high
- execution_mode: max 5 concurrent fresh subagents; one investor per subagent; subagents only received the input row and search instructions, not the Part6 output rows.

## 讀寫檔案

- Read: `part5_to_part6/output/part6_investor_input.csv`
- Read: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/results.csv`
- Read: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/classifier_results.csv`
- Read: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/needs_manual_review.csv`
- Read for original rules: `part6_analyse_investor_capabilities/agent_prompt_template.md`, `part6_analyse_investor_capabilities/Plan.md`, `part6_analyse_investor_capabilities/runtime/worker_base_template.md`
- Wrote: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/audit_random30_gpt55_high.csv`
- Wrote: `part6_analyse_investor_capabilities/agent_runs/crypto_investor/audit_random30_gpt55_high/audit_random30_gpt55_high.md`

## 抽樣設計

本次是平衡抽查，不是對全量 13,970 records 的統計外推。樣本從 positive capability、searched negative、skip candidate、manual-focused 幾類中分層抽取，目的是同時檢查能力標籤漏標、誤標與分類器跳過風險。

| sample_stratum | count |
| --- | --- |
| manual_focused | 2 |
| positive_algorithm_trading | 2 |
| positive_fill | 7 |
| positive_manual_boost | 1 |
| positive_market_making | 2 |
| positive_otc_trading | 3 |
| positive_sub_fund | 3 |
| searched_negative_full | 3 |
| searched_negative_light | 3 |
| skip_candidate | 4 |

## 核心結論

- 六個能力完全一致: 14/30
- 至少一個能力不一致: 16/30
- 不一致且已在 `needs_manual_review.csv`: 3/16
- 不一致但不在 `needs_manual_review.csv`: 13/16
- classifier/routing concern: 1 sampled row

| capability | results_yes | audit_yes | mismatch_count | results_no_audit_yes | results_yes_audit_no |
| --- | --- | --- | --- | --- | --- |
| otc_trading | 6 | 7 | 1 | 1 | 0 |
| algorithm_trading | 4 | 7 | 5 | 4 | 1 |
| market_making | 3 | 6 | 3 | 3 | 0 |
| execution_services | 7 | 10 | 3 | 3 | 0 |
| defi | 8 | 11 | 3 | 3 | 0 |
| sub_fund | 4 | 7 | 5 | 4 | 1 |

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

## Classifier 對照觀察

抽查中只有以下 row 出現明確 routing concern：分類器判為 `skip_candidate` / `capability_search_required=no`，但獨立審核搜索到至少一個能力為 Yes。

| task | investor | classifier_search_tier | classifier_required | audit_labels | in_needs_manual_review | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 4883 | Vision Capital | skip_candidate | no | ["sub_fund"] | no | Private equity firm with no explicit crypto-native, trading, execution, DeFi, or fund-vehicle language in the row. |

其餘不一致大多發生在已被分類器送入 `full` 或 `light` 搜索的 records，較像能力判定邊界或 evidence interpretation 問題，而不是分類器跳過問題。

## 六個能力定義與邊界

以下定義以 Part6 原始提示詞/計劃中的規則為基礎重述：能力必須由 investor/entity 自身或可歸屬的 operating platform 證據支持；投資組合曝光、泛泛行業描述或普通基金資料不夠。

### otc_trading

- Rule: 只有在明確證據顯示該 investor/entity 自身提供或運營 OTC desk、block trading、大宗/雙邊場外交易、RFQ/場外流動性服務時標 Yes。
- Yes boundary: 官方或可靠資料明確描述 OTC desk、場外大宗撮合、block trade API、crypto-fiat/crypto-crypto OTC trading desk，即使是透過關聯交易平台運營也可標 Yes，但需能連回該 entity 或其可歸屬平台。
- No boundary: 只投資交易所、只提到二級市場投資、只買賣 OTC-listed public companies、只有一般 token allocation/SAFT，或只是顧問/投資人關係，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | 官方 OTC/liquidity 服務、block/derivatives/large-size execution 足以標 Yes。 |
| Belobaba Fund | 官方 OTC crypto-fiat trading desk 和直接大額場外交易，標 Yes。 |
| BitGo | 官方 OTC desk、block trading、prime/electronic trading 服務，標 Yes。 |
| Jesse Powell | Kraken 官方 OTC desk 可歸屬到其 co-founder/chairman 交換所關聯身份，審核標 Yes 但建議人工覆核。 |
| Sentillia | Deribit block trading API/大宗協議交易資料連回 Sentillia/Deribit，標 Yes。 |
| Exnetwork Capital | The OTC Room 與 Exnetwork/Eric Su 的可連接證據支持 OTC，標 Yes 但證據強度中等。 |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| Ace Exchange | 有交易所與 AI bot，但沒有明確 OTC desk/block/bilateral trading 服務。 |
| RB Capital Partners | 資料中的 OTC 是 OTC/Nasdaq/NYSE 小微盤公司/股票語境，不是 crypto OTC desk。 |
| OccamDAO | DEX/AMM 交易不是雙邊場外 OTC。 |
| Petros Bozatzis | 只是投資人/顧問/董事關係，不能把交易平台 OTC 能力歸屬到個人。 |

### algorithm_trading

- Rule: 只有在明確證據顯示 algorithmic、quantitative、systematic、HFT、low-latency、automated trading strategy，或明確的 algorithmic execution/交易機器人能力時標 Yes。
- Yes boundary: 量化團隊、系統化策略、stat arb/CTA、HFT/低延遲交易、TWAP/VWAP 等演算法執行，或交易所/平台明確提供可自動化交易能力並與 entity 運營身份相連時，標 Yes。
- No boundary: 泛泛而談 API、研究文章、教育內容、普通 hedge fund/VC 策略、DeFi AMM 曲線本身，或二級資料未能確認 entity 自身能力，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | 官方 high-frequency/quant/algorithmic trading 表述，標 Yes。 |
| Great South Gate Asset Management | systematic/stat-arb/CTA digital asset strategies，標 Yes。 |
| RedLine Capital | 自稱 quantitative team/quantitative transactions，標 Yes。 |
| BitGo | TWAP/VWAP 等 algorithmic execution 服務，標 Yes。 |
| Ace Exchange | 官方 AI/網格機器人自動低買高賣，標 Yes。 |
| Sentillia | Deribit low-latency/mass quote/API execution 能力支持 algorithmic trading，標 Yes。 |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| North Rock Digital | 二級資料的策略描述不足以證明自身 algorithmic/quant/HFT 能力，審核改為 No。 |
| OccamDAO | AMM/DEX 流動性機制不是 proprietary algorithmic/HFT trading。 |
| Belobaba Fund | 教育內容提到 algo/HFT 不等於其提供或運營 algorithmic trading。 |
| Kraynos Capital Management | DeFi/VC 投資主題沒有 algorithmic trading 證據。 |

### market_making

- Rule: 只有在明確證據顯示該 investor/entity 自身提供 market making、liquidity provision、token liquidity services，或運營 DeFi AMM/流動性池協議時標 Yes。
- Yes boundary: 明確聲稱為項目提供做市/流動性、運營 AMM/DEX liquidity pool、提供 protocol/token liquidity support，可標 Yes。
- No boundary: 交易所 maker/taker fee、使用外部 market makers、投資/合作對象有做市能力、tokenomics 裡預留 market-making allocation、或一般 secondary-market trading，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | 官方 liquidity provision/token liquidity 支持，標 Yes。 |
| RedLine Capital | 明確 market maker services for projects，標 Yes。 |
| Genblock Capital | 官方稱幫項目 bootstrapping liquidity and market making，標 Yes。 |
| MochiLab | AMM/liquidity solution/去中心化交易協議，標 Yes。 |
| OccamDAO | OccamX DEX liquidity provision/mining/fees，標 Yes。 |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| BitGo | 使用/聚合外部 LP 或 market makers，不等於 BitGo 自身做市。 |
| Ace Exchange | maker/taker/order book 是交易所費率/機制，不是其提供 market-making service。 |
| FiveT Group | Orbit Markets/partner/portfolio 能力不能歸屬到 FiveT 本身。 |
| Sentillia | 交易所提供給 market makers 的 mass quote/tooling 不等於 Sentillia 自身做市。 |
| YAY Network | tokenomics 中 market-making allocation 不等於 YAY 提供做市。 |

### execution_services

- Rule: 只有在明確證據顯示 brokerage、prime brokerage、exchange/DEX execution venue、order routing、smart order routing、FIX/API execution、liquidity access 或交易執行平台/服務時標 Yes。
- Yes boundary: OTC/DEX/exchange 能讓客戶買賣/下單、API/FIX 交易接入、broker-facilitated allocations、order execution lifecycle、SOR/prime brokerage/liquidity access，標 Yes。
- No boundary: 投資顧問、上市/交易所關係介紹、普通資產管理交易、投資自身股票或小微盤融資交易、或投資/顧問關係未證明 entity 運營交易執行服務，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | NODE/API/FIX/direct liquidity access，標 Yes。 |
| YAY Network | OTC marketplace/portal 和 broker-facilitated allocations，標 Yes。 |
| Great South Gate Asset Management | private client brokerage 和 trade execution lifecycle，標 Yes。 |
| BitGo | prime brokerage/electronic trading/SOR/order execution，標 Yes。 |
| Ace Exchange | order-book exchange/matching/market-limit order trading platform，標 Yes。 |
| OccamDAO | DEX/cross-chain buy-sell-trade infrastructure，標 Yes。 |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| RedLine Capital | exchange-listing help/relationships 不是 execution/order routing service。 |
| Petros Bozatzis | 顧問或投資人身份不能把交易平台 execution 能力歸屬到個人。 |
| RB Capital Partners | 小微盤融資/股票交易資料不是客戶交易執行服務。 |
| babybera | farming/staking/bond UI 屬 DeFi app，不是 brokerage/order routing。 |
| FiveT Group | portfolio/partner 的 structured-solutions access 不是 FiveT 自身 execution service。 |

### defi

- Rule: 只有在 investor/entity 自身運營、創立、專注、支持或明確市場化 DeFi-native protocol/product/capability 時標 Yes；僅投資 DeFi startup 不足以標 Yes。
- Yes boundary: DeFi protocol、DEX、staking/farming/yield、stablecoin DeFi product、DeFi governance/support specialization、個人 founder/operator 與 DeFi 產品直接相連，可標 Yes。
- No boundary: 投資組合或合作伙伴涉及 Web3/DeFi、研究/投資主題提到 DeFi、普通區塊鏈平台或消費 app 沒有 DeFi 產品，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Wintermute Ventures | 官方稱早期 DeFi investor 並提供 DeFi/governance expertise，標 Yes。 |
| YAY Network | YAY Games farming/staking/NFT marketplace DeFi 產品，標 Yes。 |
| babybera | 官方 DeFi farms/staking/bonds/harvest/wallet connect，標 Yes。 |
| Eric Dadoun | DeZy founder/operator，產品把存款部署到 decentralized protocols，標 Yes。 |
| SOMESING | 與 Delio 的 SSX crypto deposit/DeFi-focused 產品證據，標 Yes。 |
| OccamDAO | DAO-governed DeFi ecosystem、DEX、launchpad，標 Yes。 |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| Kraynos Capital Management | 投資於 DeFi/區塊鏈公司不等於自身運營 DeFi 能力。 |
| NEOM Investment Fund | Animoca/Web3 partnership 是投資/合作曝光，不是 DeFi 產品。 |
| FiveT Group | portfolio/personnel 或 partner exposure 不是 FiveT 自身 DeFi。 |
| Exnetwork Capital | crypto/Web3 VC 和投資組合曝光沒有證明其自身 DeFi 產品。 |
| Great South Gate Asset Management | DeFi 只是投資/研究語境，不是運營產品。 |

### sub_fund

- Rule: 只有在明確證據顯示 sub-fund、feeder、umbrella、parallel fund、SPV、fund platform、fund-of-funds、protected cell/series fund 等結構時標 Yes。
- Yes boundary: master-feeder、Delaware feeder/SPV、SPC/PCC/protected cell、fund-of-funds、umbrella/sub-fund、multi-fund platform 或輸入資料明確標為 Fund of Funds 並未被搜索否定時，可標 Yes。
- No boundary: 普通 closed fund、ordinary hedge fund/VC fund、LastClosedFundName 非空、evergreen/co-investment vehicle、加速器/孵化器/戰略投資部門，沒有 feeder/SPV/FOF/umbrella 等結構證據，標 No。

Yes boundary examples from this audit:

| investor | why_yes |
| --- | --- |
| Belobaba Fund | PCC/protected cell/master-feeder/Delaware feeder/SPV，標 Yes。 |
| Great South Gate Asset Management | SPC/offshore feeder/Cayman platform，標 Yes。 |
| RedLine Capital | 自身材料稱 six sub-funds，標 Yes。 |
| Nural Capital | crypto fund-of-funds 資料，標 Yes。 |
| FiveT Group | fund platform/fund-family/Hy24 infrastructure fund structure，標 Yes。 |
| Vision Capital | master-fund/fund-of-funds/feeder LP evidence，標 Yes。 |

No / near-miss boundary examples from this audit:

| investor | why_no |
| --- | --- |
| A+ Ventures | 二級資料稀疏，沒有 feeder/SPV/umbrella/fund-of-funds 結構證據。 |
| North Rock Digital | ordinary hedge fund/managed fund 不等於 sub_fund。 |
| Kraynos Capital Management | 普通 VC/private fund filing 不足以標 sub_fund。 |
| JobsOhio Ventures | evergreen co-investment fund/subsidiary 不是 feeder/SPV/FOF。 |
| XTech Ventures | 普通 VC funds/incubation office 不是 sub_fund。 |
| Wintermute Ventures | 戰略投資部門使用自有/自營資本，不是 sub-fund/feeder。 |

## 全部30條 Sample 結果

| order | task | investor | stratum | manual_review | match | mismatch | results_labels | audit_labels | audit_confidence | audit_manual |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 133 | Wintermute Ventures | positive_otc_trading | yes | yes |  | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"] | medium | yes |
| 2 | 3298 | YAY Network | positive_otc_trading | yes | no | execution_services | ["otc_trading", "defi"] | ["otc_trading", "execution_services", "defi"] | high | no |
| 3 | 6538 | Belobaba Fund | positive_otc_trading | no | no | sub_fund | ["otc_trading", "execution_services", "defi"] | ["otc_trading", "execution_services", "defi", "sub_fund"] | medium | yes |
| 4 | 751 | Great South Gate Asset Management | positive_algorithm_trading | no | no | sub_fund | ["algorithm_trading", "execution_services"] | ["algorithm_trading", "execution_services", "sub_fund"] | medium | no |
| 5 | 11089 | North Rock Digital | positive_algorithm_trading | no | no | algorithm_trading | ["algorithm_trading"] | [] | medium | yes |
| 6 | 4598 | RedLine Capital | positive_market_making | no | no | sub_fund | ["algorithm_trading", "market_making"] | ["algorithm_trading", "market_making", "sub_fund"] | medium | no |
| 7 | 23 | Genblock Capital | positive_market_making | no | no | defi | ["market_making"] | ["market_making", "defi"] | medium | yes |
| 8 | 1942 | A+ Ventures | positive_sub_fund | no | no | sub_fund | ["sub_fund"] | [] | medium | yes |
| 9 | 2073 | Nural Capital | positive_sub_fund | no | yes |  | ["sub_fund"] | ["sub_fund"] | medium | no |
| 10 | 8381 | FiveT Group | positive_sub_fund | no | yes |  | ["sub_fund"] | ["sub_fund"] | high | no |
| 11 | 8146 | Eric Dadoun | positive_fill | no | yes |  | ["defi"] | ["defi"] | medium | no |
| 12 | 6434 | babybera | positive_fill | no | yes |  | ["defi"] | ["defi"] | high | no |
| 13 | 5242 | NEOM Investment Fund | positive_fill | no | yes |  | ["sub_fund"] | ["sub_fund"] | medium | yes |
| 14 | 10739 | MochiLab | positive_fill | no | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | medium | yes |
| 15 | 1543 | BitGo | positive_fill | no | no | algorithm_trading\|defi | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services", "defi"] | high | no |
| 16 | 9515 | Jesse Powell | positive_fill | no | no | algorithm_trading\|market_making | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "market_making", "execution_services"] | medium | yes |
| 17 | 5778 | Ace Exchange | positive_fill | no | no | algorithm_trading | ["execution_services"] | ["algorithm_trading", "execution_services"] | medium | yes |
| 18 | 1785 | Kraynos Capital Management | searched_negative_full | no | yes |  | [] | [] | medium | no |
| 19 | 12479 | SOMESING (Social/Platform Software) | searched_negative_full | no | no | defi | [] | ["defi"] | medium | yes |
| 20 | 11790 | RB Capital Partners (San Diego) | searched_negative_full | no | yes |  | [] | [] | high | no |
| 21 | 13960 | Petros Bozatzis | searched_negative_light | no | yes |  | [] | [] | medium | no |
| 22 | 7706 | DCU FinTech Innovation Center | searched_negative_light | no | yes |  | [] | [] | high | no |
| 23 | 4 | Exnetwork Capital | searched_negative_light | no | no | otc_trading | [] | ["otc_trading"] | medium | yes |
| 24 | 4883 | Vision Capital | skip_candidate | no | no | sub_fund | [] | ["sub_fund"] | medium | no |
| 25 | 9935 | Kronos Investment Group | skip_candidate | no | yes |  | [] | [] | high | no |
| 26 | 13894 | JobsOhio Ventures | skip_candidate | no | yes |  | [] | [] | high | no |
| 27 | 5054 | XTech Ventures | skip_candidate | no | yes |  | [] | [] | high | no |
| 28 | 3428 | Sentillia | manual_focused | yes | no | algorithm_trading | ["otc_trading", "execution_services"] | ["otc_trading", "algorithm_trading", "execution_services"] | high | yes |
| 29 | 8917 | Hdac Technology | manual_focused | yes | yes |  | ["defi"] | ["defi"] | medium | yes |
| 30 | 4475 | OccamDAO | positive_manual_boost | yes | no | market_making\|execution_services | ["defi"] | ["market_making", "execution_services", "defi"] | medium | yes |

## 不一致 Evidence Summaries

### 3298 - YAY Network

- in_needs_manual_review: yes
- mismatched_capabilities: execution_services
- results_labels: ["otc_trading", "defi"]
- audit_labels: ["otc_trading", "execution_services", "defi"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: YAY official/owned sources describe OTC deals, an OTC marketplace/portal for allocations, broker-facilitated transactions outside exchanges, and YAY Games DeFi/NFT/farming products. No algorithmic trading, market making, or sub-fund evidence found.
- audit_evidence_urls: https://faq.yay.network/|https://yay-network.medium.com/yay-network-otc-deals-62fe1a1e0282|https://yay-network.medium.com/yay-network-x-fuel-network-token-sale-via-the-official-broker-marsbase-f0ab7863618f|https://docs.yay.games/|https://docs.yay.games/products/farming|https://docs.yay.games/products/loot-nft-marketplace

### 6538 - Belobaba Fund

- in_needs_manual_review: no
- mismatched_capabilities: sub_fund
- results_labels: ["otc_trading", "execution_services", "defi"]
- audit_labels: ["otc_trading", "execution_services", "defi", "sub_fund"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: Belobaba official OTC page describes an OTC crypto-fiat service/trading desk and direct large-scale transactions outside order books; legal and fund documents show exchange/custody services, protected cell/master-feeder/Delaware feeder/SPV structure, and DeFi-linked token/staking/liquidity features.
- audit_evidence_urls: https://belobaba.io/otc|https://belobaba.io/legal-disclaimer|https://belobabafund.com/wp-content/uploads/2022/04/factsheet-belobaba-v3.pdf|https://www.fsc.gi/regulated-entity/belobaba-fund-limited-27983|https://belobaba.io/crypto-regulated-global-banking/wp-content/uploads/2025/02/BELOBABA-GKHAN-TOKENOMICS.pdf

### 751 - Great South Gate Asset Management

- in_needs_manual_review: no
- mismatched_capabilities: sub_fund
- results_labels: ["algorithm_trading", "execution_services"]
- audit_labels: ["algorithm_trading", "execution_services", "sub_fund"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: GSG official materials market systematic/stat-arb/CTA digital asset strategies; job evidence describes private client brokerage and trade execution lifecycle; MAS and official site show offshore feeder/SPC/Cayman structures. No OTC, market-making, or DeFi operation found.
- audit_evidence_urls: https://www.gsgasset.com/|https://www.cake.me/companies/great-south-gate-gsg/jobs/operations-analyst-gsg-pathfinder?locale=en|https://eservices.mas.gov.sg/cisnetportal/jsp/list.jsp?d-49653-o=2&d-49653-p=130&d-49653-s=2&fundmanagername=%2F1000&fundname=&subfundname=aberdeen+standard|https://www.bvifsc.vg/regulated-entities/gsg-investment-management-limited

### 11089 - North Rock Digital

- in_needs_manual_review: no
- mismatched_capabilities: algorithm_trading
- results_labels: ["algorithm_trading"]
- audit_labels: []
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: SEC/Form D evidence identifies a pooled-investment hedge fund/adviser; secondary strategy language was not enough to prove algorithmic/systematic/HFT trading capability. No trading desk, market making, DeFi operation, execution service, or explicit feeder/SPV/sub-fund structure found.
- audit_evidence_urls: https://adviserinfo.sec.gov/firm/summary/318416|https://www.sec.gov/Archives/edgar/data/1900322/000190032224000001/xslFormDX01/primary_doc.xml|https://www.preqin.com/data/profile/fund-manager/north-rock-digital/459333|https://www.rcmalternatives.com/fund/north-rock-digital-lp-north-rock-digital-lp/|https://lei.bloomberg.com/leis/view/254900OQ9M5KS7V02I41

### 4598 - RedLine Capital

- in_needs_manual_review: no
- mismatched_capabilities: sub_fund
- results_labels: ["algorithm_trading", "market_making"]
- audit_labels: ["algorithm_trading", "market_making", "sub_fund"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: RedLine/Redline DAO materials describe six sub-funds, quantitative transaction expertise, and a professional quantitative team providing liquidity and market maker services. No OTC, execution/brokerage, or DeFi-operated product found.
- audit_evidence_urls: https://www.nasdaq.com/press-release/redline-capital-upgraded-its-brand-and-rebrands-as-redline-dao-2021-09-20|https://medium.com/redline-dao/redline-dao-road-ahead-is-long-and-hard-persist-success-is-in-card-911a22dc929e|https://www.redlinedao.com/Team

### 23 - Genblock Capital

- in_needs_manual_review: no
- mismatched_capabilities: defi
- results_labels: ["market_making"]
- audit_labels: ["market_making", "defi"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: Genblock official about page says it invests exclusively in blockchain/crypto with a focus on decentralized finance and helps portfolio projects with bootstrapping liquidity, token economics, and market making. No OTC, algorithmic trading, execution service, or sub-fund evidence found.
- audit_evidence_urls: https://genblock.capital/about/|https://genblock.capital/portfolio/

### 1942 - A+ Ventures

- in_needs_manual_review: no
- mismatched_capabilities: sub_fund
- results_labels: ["sub_fund"]
- audit_labels: []
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: A+ Ventures appears to be a Web3/blockchain VC/accelerator/business consulting firm. No explicit OTC, algorithmic, market-making, execution, DeFi-operated product, or sub-fund/feeder/SPV/fund-platform evidence found; primary-source availability was sparse.
- audit_evidence_urls: https://lt.linkedin.com/company/aplusventures|https://www.crunchbase.com/organization/a-ventures-a2c5|https://unicorn-nest.com/funds/a-ventures-2/|https://herbertus.co/a-plus-ventures/

### 10739 - MochiLab

- in_needs_manual_review: no
- mismatched_capabilities: market_making|execution_services
- results_labels: ["defi"]
- audit_labels: ["market_making", "execution_services", "defi"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: MochiLab incubated/created Mochi.Market, a multi-chain decentralized NFT exchange with AMM, staking, lending, fractionalization, and cross-chain swaps. This supports protocol-level market_making, execution_services, and DeFi. No OTC, algorithmic trading, or sub-fund evidence found.
- audit_evidence_urls: https://www.businesswire.com/news/home/20210416005543/en/Multi-Chain-Decentralized-NFT-Exchange-Mochi.Market-Announces-Partnership-with-Plasm-Network|https://www.newsbtc.com/press-releases/mochi-market-finalizes-seed-round-preps-for-ido-fair-launch-for-its-multi-chain-nft-decentralized-exchange-protocol/|https://medium.com/astar-network/multi-chain-nft-exchange-mochi-market-builds-on-plasm-network-edb36400a701|https://www.linkedin.com/company/mochilaborg

### 1543 - BitGo

- in_needs_manual_review: no
- mismatched_capabilities: algorithm_trading|defi
- results_labels: ["otc_trading", "execution_services"]
- audit_labels: ["otc_trading", "algorithm_trading", "execution_services", "defi"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: BitGo official materials advertise OTC/block trading, prime brokerage/electronic trading/API/UI execution, smart order routing, algorithmic pass-through execution such as TWAP/VWAP, and institutional DeFi access through custody/wallet integrations. No self market-making or sub-fund structure found.
- audit_evidence_urls: https://www.bitgo.com/products/trading/|https://www.bitgo.com/products/prime/|https://www.bitgo.com/resources/blog/bitgo-unveils-secure-all-in-one-otc-trading-desk/|https://www.bitgo.com/asset-listings-process/|https://www.bitgo.com/solutions/walletconnect/|https://www.bitgo.com/resources/blog/bitgo-integrates-narval-to-deliver-institutional-defi-access-from-qualified-custody/

### 9515 - Jesse Powell

- in_needs_manual_review: no
- mismatched_capabilities: algorithm_trading|market_making
- results_labels: ["otc_trading", "execution_services"]
- audit_labels: ["otc_trading", "algorithm_trading", "market_making", "execution_services"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: Official Kraken sources tie Jesse Powell to Kraken and show OTC desk, API/FIX low-latency/automated trading access, token liquidity support, and execution services. No DeFi-native protocol operation or sub-fund evidence found for Powell.
- audit_evidence_urls: https://www.kraken.com/press/releases/kraken-announces-leadership-succession-plan|https://www.kraken.com/en-ca/features/otc-exchange/bitcoin|https://docs.kraken.com/api/|https://docs.kraken.com/api/docs/guides/fix-intro/|https://www.kraken.com/institutions/kraken-360|https://www.kraken.com/institutions/protocols

### 5778 - Ace Exchange

- in_needs_manual_review: no
- mismatched_capabilities: algorithm_trading
- results_labels: ["execution_services"]
- audit_labels: ["algorithm_trading", "execution_services"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: ACE official materials describe an order-book exchange and AI/grid trading robot described as a quantitative strategy. No official OTC desk, market making, DeFi operation, or sub-fund evidence found.
- audit_evidence_urls: https://helpcenter.ace.io/hc/en-us/articles/360018350432-ACE-Trading-Guide|https://helpcenter.ace.io/hc/zh-tw/articles/12247136526873-24H%E4%B8%8D%E9%96%93%E6%96%B7-%E7%84%A1%E8%A6%96%E6%BC%B2%E8%B7%8C-AI%E6%A9%9F%E5%99%A8%E4%BA%BA%E8%87%AA%E5%8B%95%E4%BD%8E%E8%B2%B7%E9%AB%98%E8%B3%A3%E5%B9%AB%E4%BD%A0%E5%A5%97%E5%88%A9|https://helpcenter.ace.io/hc/en-us/articles/21703684987929-ACE-Exchange-Terms-of-Use|https://helpcenter.ace.io/hc/zh-tw/articles/360018099112-%E9%97%9C%E6%96%BCACE|https://earning.tw/ace-exchange-introduce/

### 12479 - SOMESING (Social/Platform Software)

- in_needs_manual_review: no
- mismatched_capabilities: defi
- results_labels: []
- audit_labels: ["defi"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: SOMESING official site shows blockchain content/token platform; 2021 reports and Delio guide describe SSX crypto deposit/yield product with Delio. No trading desk, algorithmic trading, market making, execution, or sub-fund evidence found.
- audit_evidence_urls: https://somesing.io/about-us|https://www.mk.co.kr/news/economy/9884474|https://medium.com/delio-global/delio-somesing-token-ssx-deposit-guide-c439b90f320|https://singlovers.medium.com/official-statement-regarding-the-delisting-of-ssx-cb47dbc862b3

### 4 - Exnetwork Capital

- in_needs_manual_review: no
- mismatched_capabilities: otc_trading
- results_labels: []
- audit_labels: ["otc_trading"]
- classifier_search_tier: light
- classifier_required: yes
- audit_evidence_summary: Exnetwork is a blockchain fund/incubator; ExNetwork-owned Medium and third-party article tie Exnetwork/Eric Su to The OTC Room/major crypto OTC trading desk. No algorithmic, market-making, execution, DeFi operation, or sub-fund evidence found.
- audit_evidence_urls: https://exnetworkcapital.com/home/|https://www.linkedin.com/company/exnetwork/|https://medium.com/exnetwork/otc-room-adds-a-trc-payment-alternative-e595b7d0b319|https://dailycoin.com/smart-exchange-ecosystem-unizen-doubles-down-on-its-advisory-board/|https://www.rootdata.com/Investors/detail/Exnetwork%20Capital?k=NzI2

### 4883 - Vision Capital

- in_needs_manual_review: no
- mismatched_capabilities: sub_fund
- results_labels: []
- audit_labels: ["sub_fund"]
- classifier_search_tier: skip_candidate
- classifier_required: no
- classifier_issue: skip_candidate_but_independent_audit_found_capability|capability_search_required_no_but_independent_audit_found_capability
- audit_evidence_summary: Vision Capital is a private equity/direct portfolio acquisition group. SEC/private fund/Gazette evidence ties Vision Capital fund entities to feeder/master/fund-of-funds structures, supporting sub_fund. No trading, execution, market-making, or DeFi operation found.
- audit_evidence_urls: https://www.visioncapital.com/|https://www.visioncapital.com/terms-and-conditions/|https://find-and-update.company-information.service.gov.uk/company/02737865|https://reports.adviserinfo.sec.gov/reports/ADV/161143/PDF/161143.pdf|https://privatefunddata.com/private-funds/vcl-partners-i-lp/|https://www.companiesintheuk.co.uk/gazette/publication/2015-12-23

### 3428 - Sentillia

- in_needs_manual_review: yes
- mismatched_capabilities: algorithm_trading
- results_labels: ["otc_trading", "execution_services"]
- audit_labels: ["otc_trading", "algorithm_trading", "execution_services"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: Primary sources identify Sentillia B.V. as Deribit. Deribit docs show derivatives/spot trading venue, API/FIX execution, block trading for large off-book negotiated trades, and low-latency/mass-quote functionality. No self market-making, DeFi operation, or sub-fund evidence found.
- audit_evidence_urls: https://www.sec.gov/Archives/edgar/data/1679788/000167978826000054/coin-20260331.htm|https://support.deribit.com/hc/en-us/articles/25944687804957-About-Us|https://docs.deribit.com/|https://docs.deribit.com/articles/block-trading-api|https://docs.deribit.com/articles/mass-quotes-specifications|https://www.mccaa.org.mt/section/content?contentId=13224

### 4475 - OccamDAO

- in_needs_manual_review: yes
- mismatched_capabilities: market_making|execution_services
- results_labels: ["defi"]
- audit_labels: ["market_making", "execution_services", "defi"]
- classifier_search_tier: full
- classifier_required: yes
- audit_evidence_summary: OccamDAO/Occam.fi materials describe DAO-governed DeFi ecosystem services including launchpad, DEX, DAO, incubator, OccamX DEX liquidity provision/mining/fees, and cross-chain trading. No OTC, algorithmic trading, or sub-fund evidence found.
- audit_evidence_urls: https://occam.fi/|https://medium.com/occam-finance/occamdao-expands-to-the-cosmos-ecosystem-9dc47310e3bc|https://medium.com/occam-finance/ocx-distribution-staking-5c9d66e1e2ba|https://medium.com/occam-finance/occam-fi-and-everscale-collaborate-to-launch-cardano-cross-chain-bridge-d97f79ca8eca

## 注意事項

- 本報告只審核六個 investor capability flags 與分類器 routing，不把 confidence、evidence_summary 文字差異本身視為不一致。
- 個人投資者與其 founded/chaired operating platform 的能力歸屬屬高風險邊界；本次對 Jesse Powell 等案例保留 audit_manual=yes。
- 對 sub_fund，普通基金存在本身不足以標 Yes；需看到 feeder/SPV/umbrella/fund-of-funds/protected-cell/series 等結構。
