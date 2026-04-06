# Part3: `crypto_company.csv` 的 Project / Token / Listing 搜索方法

## 目標

對 `part2_build_crypto_candidate/output/crypto_company.csv` 中的每家公司，分開判斷 4 件事：

1. `IsCryptoRelatedCompany`
2. `HasCryptoProject`
3. `HasToken`
4. `ListedWhere` / `ListedWhen`

這 4 件事不能混在一起判斷。

特別是：

- `crypto 相關公司` 不等於 `有對應 crypto project`
- `crypto project` 不等於 `已發 token`
- `交易所` 不等於 `發過 token`
- 找不到證據不等於 `no`

因此 part3 的核心原則是：

- `yes` 必須有正證據
- `no` 也必須有反證或明確排除證據
- 否則一律標 `unknown`

---

## 第一部分：主表快篩應怎麼做

主表快篩的目標不是直接下最終結論，而是：

1. 估計這家公司值不值得進 agent
2. 產生後續搜索 query
3. 把明顯 relation 誤抓先降級

### 只用主表欄位做快篩

快篩時只看：

- `CompanyName`
- `Website`
- `Verticals`
- `Description`
- `Keywords`
- `MatchedColumns`

不把 `Relation_*` 內容當成最終判斷依據，只把它當成召回來源。

### 快篩規則

#### A. 高優先級，進 agent 或結構化外部查詢

滿足任一條件即可：

- `Verticals` 含 `Cryptocurrency/Blockchain`
- `Description` 或 `Keywords` 直接提到：
  - `crypto`
  - `blockchain`
  - `token`
  - `exchange`
  - `wallet`
  - `protocol`
  - `defi`
  - `dao`
  - `decentralized`
  - `smart contract`
- `Website` / `CompanyName` 和已知 crypto 品牌高度一致

這一層只代表：
- `IsCryptoRelatedCompany = likely_yes`

不代表：
- `HasCryptoProject = yes`
- `HasToken = yes`

#### B. 中優先級，先做快速外部比對

滿足任一條件：

- 主表沒有強 crypto 詞，但 `Keywords` 有弱相關詞
- `MatchedColumns` 同時包含主表欄位與 relation 欄位
- 公司看起來像金融、支付、保險、資料基礎設施，但是否鏈上不清楚

這一層先做結構化來源快查，不直接交 agent。

#### C. 低優先級，先標記為疑似誤抓

滿足全部條件：

- `MatchedColumns` 只來自 `Relation_*`
- 主表 `Verticals`、`Description`、`Keywords` 沒有直接 crypto 詞
- 公司主營明顯屬於非 crypto 類型，例如：
  - 通用 SaaS
  - 廣告技術
  - 車隊管理
  - VPN
  - 普通 AI 工具
  - 通用內容或 workspace 平台

這一層只代表：
- `AgentPriority = low`
- 不代表 `HasCryptoProject = no`

---

## 第二部分：重新定義 part3 的判斷口徑

### 1. `IsCryptoRelatedCompany`

定義：

- 公司是否明確在做 crypto / blockchain 相關業務

`yes` 的證據：

- 官方網站明確描述自己是 crypto / blockchain company
- 或 `Verticals` / 官方文案 / 結構化來源一致支持

`no` 的證據：

- 官方網站與主表都明確顯示是非 crypto 業務
- 且所有 crypto 信號只來自 relation 誤帶

否則：

- `unknown`

### 2. `HasCryptoProject`

定義：

- 公司是否對應一個具名的 crypto product / protocol / network / exchange / appchain / wallet ecosystem

這裡要明確指出：

- `exchange` 可以是一種 crypto project
- 但 `exchange` 本身不代表 `HasToken = yes`

`yes` 的證據：

- 官方網站或 docs 中有明確 project 名稱
- 或第三方結構化平台明確把該公司映射到某個 crypto project

`no` 的證據：

- 官方資訊明確說只是服務商 / 咨詢 / 傳統軟體，且沒有對應 crypto product

否則：

- `unknown`

### 3. `HasToken`

定義：

- 該 project 是否真的發行過可識別的 token / coin

`yes` 的證據：

- 官方 docs / whitepaper / blog 直接提 token
- CoinGecko / CoinMarketCap 有明確 token 頁
- 或有可驗證的 CEX / DEX 市場頁

`no` 的證據：

- 官方明確聲明沒有 native token
- 或官方 FAQ / docs 明確排除 token 設計

注意：

- 單純找不到 token，不得判 `no`
- 應標 `unknown`

### 4. `ListedWhere` / `ListedWhen`

只在 `HasToken = yes` 的前提下才查。

優先證據：

1. 交易所官方 announcement
2. 官方 blog / announcement
3. CoinGecko / CoinMarketCap market 頁
4. GeckoTerminal / DexScreener

若只有交易市場但沒有日期：

- `ListedWhere` 可以填
- `ListedWhen` 標空
- 不是 `no`

---

## 第三部分：agent 應該去哪裡查

agent 的來源優先順序固定如下：

1. 官方網站首頁
2. 官方產品頁 / protocol 頁
3. 官方 docs / litepaper / whitepaper
4. 官方 blog / announcement / Medium
5. CoinGecko
6. CoinMarketCap
7. DefiLlama
8. GeckoTerminal
9. DexScreener
10. 交易所官方 listing announcement

使用原則：

- 官方來源優先於第三方
- 結構化平台優先於泛搜索結果
- 第三方媒體只能作補充，不能單獨支撐 `yes`

---

## 第四部分：如何快速判斷，減少 agent 耗時

### 快速方法 1：先分任務，不要一次問完所有問題

對每家公司，判斷順序固定為：

1. 這是不是 crypto 相關公司？
2. 它有沒有明確對應的 crypto project？
3. 這個 project 有沒有 token？
4. 只有第 3 步是 `yes`，才去查 listing

這能避免把大量時間浪費在沒有 token 的公司上。

### 快速方法 2：先用域名，不先用自然語言大搜

先從 `Website` 生成精準查詢：

- `site:{domain} token`
- `site:{domain} ticker`
- `site:{domain} listing`
- `site:{domain} whitepaper`
- `site:{domain} docs`

域名通常比公司名更穩，能減少重名與噪音。

### 快速方法 3：先查結構化平台

對高優先級公司，先查：

- CoinGecko
- CoinMarketCap
- DefiLlama
- GeckoTerminal
- DexScreener

這一步常能直接回答：

- 有沒有 token
- token ticker 是什麼
- 有沒有 market

只有查不到時再交 agent 深搜官方頁。

### 快速方法 4：關係欄位命中不進直接深查

若公司只因 `Relation_*` 命中進來：

- 先只做低成本快篩
- 不直接交 agent

這能砍掉大部分誤抓樣本。

### 快速方法 5：對「交易所」單獨處理

若公司明顯是 exchange：

- 可較快判 `IsCryptoRelatedCompany = yes`
- 可較快判 `HasCryptoProject = yes`，project 類型為 exchange product
- 但 `HasToken` 必須單獨查

不能再像前一版那樣用「它是交易所」去暗示它有 token 或沒有 token。

---

## 第五部分：輸出結構必須帶證據

part3 最終每一列都必須帶可檢查證據。

建議輸出欄位：

- `CompanyID`
- `CompanyName`
- `Website`
- `AgentPriority`
- `IsCryptoRelatedCompany`
- `IsCryptoRelatedCompanyEvidence`
- `HasCryptoProject`
- `ProjectName`
- `HasCryptoProjectEvidence`
- `HasToken`
- `TokenTicker`
- `HasTokenEvidence`
- `ListedWhere`
- `ListedWhen`
- `ListingEvidence`
- `EvidenceURLs`
- `EvidenceSourceTypes`
- `Confidence`
- `NeedsManualReview`

其中：

- `EvidenceURLs`
  - 用 `|` 串接多個來源
- `EvidenceSourceTypes`
  - 例如 `official_site|coingecko|coinmarketcap|exchange_announcement`

### 證據要求

- 任何 `yes` 都必須有 URL
- 任何 `no` 都必須有 URL 或官方明確表述
- 如果做不到，就標 `unknown`

這是 part3 必須執行的硬規則。

---

## 第六部分：修正前 20 間試跑的口徑

### Zebpay

前一版問題：

- 把它作為 crypto 相關公司是合理的
- 但不能因為是交易所，就直接當作「沒有 token」

修正後應該是：

- `IsCryptoRelatedCompany = yes`
- `HasCryptoProject = yes`
- `ProjectName = ZebPay`
- `HasToken = unknown`

除非找到官方或結構化來源明確說沒有 native token，才可寫 `no`

### Zikto / Insureum

前一版可保留，但仍需統一成證據驅動格式：

- `HasToken = yes`
- `TokenTicker = ISR`
- `ListedWhere` 與 `ListedWhen` 都必須附來源 URL

### Streembit

前一版判斷方向合理，但仍需按新格式拆成：

- `IsCryptoRelatedCompany`
- `HasCryptoProject`
- `HasToken`
- `Listing`

不能只用一句 `needs agent` 概括。

---

## 本輪輸出調整

本輪不再沿用舊版 part3 的簡化判斷法。

後續 part3 應改成：

1. 先做主表快篩，只決定優先級，不直接把 absence 當 `no`
2. 再做結構化來源快查
3. 最後才交 agent 深查
4. 所有最終 `yes / no / unknown` 都要帶證據與 URL
