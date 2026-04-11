# Part4 Pipeline Spec

## 目標

把 token 的 `founder_people`、`related_companies`、`foundation_or_orgs` 做成一條可執行、可擴展、可檢查的三層式 pipeline。

核心原則：

- 先 canonicalize token，再抽取 founder/company
- 主流程不做全量 agent 廣搜
- 模型不吃全文，只吃高信號文本
- `unknown` 優先於猜測
- 每條結果都必須能回溯到具體 evidence

---

## 當前項目結構

### 現有腳本

- [1_merge_coingecko_cmc_about.py](/Users/benlao/Downloads/STANFORD_20260201/part4/1_merge_coingecko_cmc_about.py)
  - 作用：合併 CoinGecko 與 CoinMarketCap 的 `about_text`
  - 狀態：已存在

- [4_extract_founder_companies.py](/Users/benlao/Downloads/STANFORD_20260201/part4/4_extract_founder_companies.py)
  - 作用：把 token 文本打包成批次抽取任務
  - 狀態：已存在，但目前仍偏向「整段文本直接抽取」

- [4_founder_company_prompt.txt](/Users/benlao/Downloads/STANFORD_20260201/part4/4_founder_company_prompt.txt)
  - 作用：定義 founder/company/org 抽取規則
  - 狀態：已存在

- [Plan.md](/Users/benlao/Downloads/STANFORD_20260201/part4/Plan.md)
  - 作用：總體策略與模型/工具選型
  - 狀態：已存在

### 建議新增步驟

以下步驟尚未完整落地，建議在 `part4/` 內新增相應腳本或模組：

- `collect_official_evidence`
  - 從官方網站定向抓取 founder/company 高信號段落

- `filter_candidate_sentences`
  - 從 `about_text` 和官方段落中切句並保留高信號句

- `build_review_queue`
  - 對低信心、衝突、特殊 token 自動打入 review queue

- `validate_extraction_results`
  - 對 founder/company/org 類別混淆、evidence 缺失、confidence 過高等問題做規則校驗

---

## Pipeline 概覽

整條線分成：

1. `Preparation`
2. `Layer 1: CG / CMC Candidate Sentences`
3. `Layer 2: Official Site Directed Evidence`
4. `Layer 3: Agent Fallback`
5. `Post-Processing and QA`

其中真正的三層抽取是 Layer 1 到 Layer 3。

---

## Preparation

### 目的

先把 token canonicalize，並準備好可被三層抽取共用的主表。

### 輸入

- `part4/output/coinmarketcap_list.csv`
- `part4/output/coingecko_all_crypto_list.csv`
- `part4/output/coingecko_about.csv`
- `part4/output/cmc_about_qa.csv`

### 現有腳本

- [1_merge_coingecko_cmc_about.py](/Users/benlao/Downloads/STANFORD_20260201/part4/1_merge_coingecko_cmc_about.py)

### 建議輸出

- `part4/output/token_master.csv`
- `part4/output/token_master_enriched.csv`
- `part4/output/coingecko_about_with_cmc_about.csv`

### 最低欄位要求

- `token_name`
- `token_symbol`
- `token_href`
- `coingecko_slug`
- `cmc_slug`
- `match_method`
- `match_confidence`
- `about_text`
- `cmc_about_text`
- `official_website`

### 匹配順序

1. `slug`
2. `symbol + normalized token_name`
3. `exact normalized name`

### Preparation 完成條件

- 每個 token 有穩定的 canonical key
- 每個 token 至少有一份可抽取文本
- 若有 CoinGecko `websites`，需補出 `official_website`

---

## Layer 1: CG / CMC Candidate Sentences

### 目的

用最低成本先解掉大部分 founder/company 明確的 token。

### 適用資料

- `about_text`
- `cmc_about_text`

### 模型輸入

不要輸入全文。

先本地切句，只保留包含以下 trigger 的句子：

- `founder`
- `co-founder`
- `founded by`
- `created by`
- `invented by`
- `launched by`
- `issued by`
- `developed by`
- `operated by`
- `maintained by`
- `foundation`
- `labs`
- `dao`
- `association`
- `issuer`
- `parent company`

### 建議新增步驟

- `filter_candidate_sentences`

### 模型建議

- 效果優先：`OpenAI GPT` + Structured Outputs
- 平衡方案：`GLM-5`
- 成本優先 baseline：`DeepSeek-V3.2`

### 預期輸出

- `part4/output/token_evidence_sentences_layer1.csv`
- `part4/output/founder_company_layer1.csv`

每列至少包含：

- `token_id`
- `source`
- `sentence`
- `trigger_keyword`
- `founder_people`
- `related_companies`
- `foundation_or_orgs`
- `evidence_spans`
- `confidence`
- `notes`

### Layer 1 升級到 Layer 2 的條件

符合任一條件就升級：

- `founder_people`、`related_companies`、`foundation_or_orgs` 全空
- 只有單一弱句支持
- `confidence = low`
- 抽到的是 partner / contributor / exchange，但不像 issuer / operator / founder
- evidence 提到 project，但沒有清楚指向 token 或其直接主體

### Layer 1 校驗

- `founder_people` 不得含公司或基金會名稱
- `related_companies` 不得直接收 exchange / partner / investor
- `foundation_or_orgs` 不得混入 `Inc.` / `Ltd.` / `LLC`
- 每條非空結果都要至少有一條 `evidence_span`

---

## Layer 2: Official Site Directed Evidence

### 目的

對 Layer 1 unresolved 的 token，從官方站點補更高 precision 的 founder/company 證據。

### 適用資料

- `official_website`
- CoinGecko `websites`
- 官方站點中的定向頁面

### 官方抓取範圍

每個 token 最多抓 3 到 5 頁，優先順序：

1. `/about`
2. `/team`
3. `/foundation`
4. `/docs`
5. `/whitepaper`
6. `/litepaper`

### 輸入內容

不是整頁 HTML，也不是整篇 whitepaper。

而是先本地抽出以下高信號段落：

- project history / founding 段落
- founder / co-founder 個人介紹段落
- foundation / DAO / association 說明段落
- issuer / developer / operating entity 說明段落

### 建議新增步驟

- `collect_official_evidence`
- `filter_candidate_sentences`

### 模型建議

- 主模型仍以 `OpenAI GPT` 或 `GLM-5` 為主
- 若 Layer 1 用的是低成本模型，Layer 2 建議升級到高 precision 模型

### 預期輸出

- `part4/output/token_official_evidence.csv`
- `part4/output/token_evidence_sentences_layer2.csv`
- `part4/output/founder_company_layer2.csv`

### Layer 2 升級到 Layer 3 的條件

符合任一條件就升級：

- 官方頁仍找不到 founder/company/org
- 官方與 CG/CMC 結論衝突
- wrapped / bridged / staked token，主體歸屬不清
- token 很重要，不能接受空值
- 有 founder 但沒有可確認的 direct company / org，或反之

### Layer 2 校驗

- `high confidence` 必須有官方來源支持
- 只有 `CG/CMC` 支持的結果最高只能到 `medium`
- 若官方文本只描述 ecosystem / community，不得直接推出 issuer/company

---

## Layer 3: Agent Fallback

### 目的

只處理少量高價值、低信心、或多來源衝突的 token。

### 原則

- 不跑全量
- 不做 open-ended 廣搜
- 只處理 review queue 中的 unresolved token

### agent 輸入

必須使用結構化 packet，而不是一句泛問題。

最低輸入字段：

- `token_name`
- `token_symbol`
- `cmc_slug`
- `coingecko_slug`
- `official_website`
- `CG/CMC 候選句`
- `官方候選段落`
- `Layer 1 / Layer 2 中間結果`
- 明確問題：
  - `founder_people` 是誰
  - `related_companies` 是哪些 issuer / developer / operator / parent company
  - `foundation_or_orgs` 是哪些 foundation / DAO / association / labs
  - 只接受有明確文字證據的答案

### agent / 工具建議

- 工程與研究都在同一環境：`Codex` with web/search tooling
- 第二選：`Claude` with tool use / web search
- 中文與國內 agent 工作流：`GLM-5 agent` / `AutoGLM`

### 預期輸出

- `part4/output/founder_company_layer3.csv`
- `part4/output/agent_review_notes.csv`

### Layer 3 結束條件

符合以下其一即可結束：

- 得到帶 evidence 的 founder/company/org 結果
- 經多來源檢查後仍無法確認，標記為 `unknown`

### Layer 3 校驗

- agent 結論不得覆蓋現有證據，除非帶來更強來源
- 所有最終新增結果都必須附 evidence 與 source URL

---

## Post-Processing and QA

### 目的

把三層結果合併為最終主表，並建立 review queue。

### 最終輸出

- `part4/output/founder_company_extracted.csv`
- `part4/output/founder_company_review_queue.csv`

### 合併優先級

1. 官方來源支持的 Layer 2
2. 經 agent 補強且有明確 evidence 的 Layer 3
3. 只有 CG/CMC 支持的 Layer 1

### review queue 進入條件

- 多來源衝突
- 只有單一來源支持
- `confidence = low`
- wrapped / bridged / staked token
- meme / community token
- founder / company / org 類別容易混淆

### QA 規則

1. 每條非空結果都必須有 `evidence_span`
2. `high confidence` 必須有官方來源，或至少雙來源一致
3. company / org / person 三類不得混填
4. `related_companies` 只收 issuer / developer / operator / parent company
5. 找不到明確證據時，一律保留空陣列，不補常識

---

## 推薦實作順序

### Phase 1

先把現有腳本整理為可重跑的 baseline：

1. 修正 [4_extract_founder_companies.py](/Users/benlao/Downloads/STANFORD_20260201/part4/4_extract_founder_companies.py) 中的舊檔名與舊提示路徑
2. 確保 [1_merge_coingecko_cmc_about.py](/Users/benlao/Downloads/STANFORD_20260201/part4/1_merge_coingecko_cmc_about.py) 的輸出表能穩定生成
3. 新增 `filter_candidate_sentences`

### Phase 2

把主流程改成真正的 Layer 1：

1. `merge`
2. `candidate sentence filter`
3. `sentence-level extraction`
4. `rule-based validation`

### Phase 3

補 Layer 2 與 Layer 3：

1. `collect_official_evidence`
2. 官方段落抽取
3. unresolved token 才進 agent
4. 自動生成 review queue

---

## 目前已觀察到的兩個實際缺口

### 缺口 1：現有抽取腳本仍以整段文本為主

[4_extract_founder_companies.py](/Users/benlao/Downloads/STANFORD_20260201/part4/4_extract_founder_companies.py) 目前仍把 `about_text` / `cmc_about_text` 整段打進 task。

這與 `Plan.md` 的三層設計不一致，因為它還沒有：

- candidate sentence filter
- sentence-level extraction
- layer-based escalation

### 缺口 2：輸入與輸出主表尚未完整落地

目前 `part4/output/` 下已看到的是 batch 文件與 batch result，但還沒有完整可重跑的：

- `coingecko_about_with_cmc_about.csv`
- `token_master.csv`
- `token_master_enriched.csv`
- `founder_company_review_queue.csv`

這代表 pipeline 還沒有完全落成為「從原始輸入到最終輸出可重跑的一條線」。

---

## 執行判定摘要

一句話版：

- 先用 `CG/CMC 候選句` 快速解大部分 token
- 再用 `官方定向抓取` 提高 precision
- 只有少量 unresolved token 才進 agent
- 最後用 `validation + review queue` 保證主表品質
