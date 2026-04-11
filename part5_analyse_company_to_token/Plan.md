# Part3: `crypto_company.csv` 的 Project / Token / Listing 搜索方法

## 目標

對 `part2_build_crypto_candidate/output/crypto_company.csv` 中的每家公司，分開判斷 4 件事：

1. `IsCryptoRelatedCompany`
2. `HasCryptoProject`
3. `HasToken`
4. `ListedWhere` / `ListedWhen`
5. 是不是交易所(CEX, DEX)
6. Associate with exchange

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

本輪實際執行重點先收斂到：

- `HasToken`
- `TokenTicker`

---

## 第一部分：所有 company 都直接進 agent

本版不再做「先內部快篩、再決定哪些 company 進 agent」。

改成：

1. `crypto_company.csv` 中所有提供的 company，一律交給 agent
2. agent 的核心任務是查：
   - 這家公司 / 對應 project 有沒有 token
   - 如果有，`TokenTicker` 是什麼
3. 主表欄位只用來提供 agent 搜索上下文，不再用來做內部初判

### 主表欄位的用途

仍然可以把下列欄位傳給 agent，幫助它降低重名與品牌混淆：

- `CompanyName`
- `Website`
- `Verticals`
- `Description`
- `Keywords`
- `MatchedColumns`

但這些欄位只作為：

- query 提示
- 官方域名定位
- 品牌名稱 disambiguation

不再作為：

- `HasToken = yes/no`
- `TokenTicker = xxx`
- `IsCryptoRelatedCompany = yes/no`

的內部判斷依據。

### 這樣改的目的

- 避免內部規則把 absence 當成 `no`
- 避免 relation 誤抓時被本地規則放大
- 把所有 token / ticker 判斷統一交給同一套外部證據口徑

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

`no` 的證據：

- 官方明確聲明沒有 native token
- 或官方 FAQ / docs 明確排除 token 設計

注意：

- 單純找不到 token，不得判 `no`
- 應標 `unknown`

### 4. `ListedWhere` / `ListedWhen`

只在 `HasToken = yes` 的前提下才查。

但要注意：

- 這不是本輪最小可行版本的主目標
- 若 agent 被限制只看官網、CoinGecko、CoinMarketCap，則 listing 證據通常不完整
- 因此本輪可允許 `ListedWhere` / `ListedWhen` 大量留空或標 `unknown`

優先證據：

1. 交易所官方 announcement
2. 官方 blog / announcement
3. CoinGecko / CoinMarketCap market 頁
4. GeckoTerminal / DexScreener

若只有交易市場但沒有日期：

- `ListedWhere` 可以填
- `ListedWhen` 標空
- 不是 `no`

若後續要把 listing 做成高置信度欄位，應重新放開來源白名單。

---

## 第三部分：agent 應該去哪裡查

本版對 agent 設白名單，只允許看 3 類來源：

1. 官方網站
2. CoinGecko
3. CoinMarketCap

其中「官方網站」可包含同一官方域名下的：

- 首頁
- product / protocol 頁
- docs / litepaper / whitepaper
- blog / announcement

但不擴散到其他第三方網站。

使用原則：

- 官方來源優先於第三方
- 只看這 3 類來源，不做泛搜索擴散
- CoinGecko / CoinMarketCap 用來補強 token 名稱與 ticker
- 若 3 類來源都沒有足夠證據，結論應標 `unknown`

### 來源限制是否足夠

若本輪目標只是：

- 判斷 `HasToken`
- 找 `TokenTicker`

那麼只看官網、CoinGecko、CoinMarketCap，對大多數主流或中等知名項目通常足夠。

但要明確限制：

- 對非常早期、已下架、冷門、已改名、只在鏈上存在而沒有完整聚合頁的項目，這 3 類來源可能不夠
- 對 `HasToken = no` 的結論尤其不夠穩，因為「查不到」不能推出 `no`
- 對 `ListedWhere` / `ListedWhen` 幾乎不夠，因為這通常需要交易所公告或市場頁補證

因此本版可以成立的前提是：

- 重點任務縮到 `HasToken` 與 `TokenTicker`
- `unknown` 接受率要高
- 不要求只靠這 3 類來源完成強證據的 listing 判斷

---

## 第四部分：如何限制 agent 耗時

既然所有 company 都要進 agent，節流方式不再是「先內部判斷」，而是「限制 agent 的任務範圍與網址數量」。

### 方法 1：每家公司只回答兩個核心問題

agent 只需要回答：

1. 有沒有 token
2. token ticker 是什麼

不要在同一輪要求 agent 同時做：

- 全面公司分類
- project taxonomy
- listing 深搜
- 歷史更名追蹤

這樣可以明顯減少單家公司耗時。

### 方法 2：每家公司只看 3 類來源

固定來源：

- 官方網站
- CoinGecko
- CoinMarketCap

不再讓 agent 自行擴散到：

- DefiLlama
- GeckoTerminal
- DexScreener
- 新聞
- 第三方媒體
- 論壇 / 社媒

### 方法 3：先官方，再兩個聚合站

推薦固定順序：

1. 用 `Website` 鎖定官方域名與品牌名
2. 在官方域名下看是否明確提到 token / ticker
3. 再看 CoinGecko 是否有對應 token 頁
4. 最後看 CoinMarketCap 是否有對應 token 頁

### 方法 4：為 agent 設結果上限

每家公司最多產出以下結論之一：

- `HasToken = yes`, `TokenTicker = ...`
- `HasToken = unknown`, `TokenTicker =`
- `HasToken = no`

其中：

- 只有官方或兩個聚合站提供正證據時，才寫 `yes`
- 只有官方明確否認 token 時，才寫 `no`
- 其餘全部寫 `unknown`

### 方法 5：交易所仍然不能被特殊簡化

即使公司明顯是 exchange：

- 也不能因為是交易所，就推定有 token
- 也不能因為 3 個來源暫時沒找到，就推定沒有 token

交易所在本版仍按同一套證據規則處理。

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
  - 例如 `official_site|coingecko|coinmarketcap`

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

本輪不再沿用舊版 part3 的「先內部快篩，再決定是否進 agent」流程。

後續 part3 應改成：

1. 所有提供的 company 一律交 agent
2. agent 只查官網、CoinGecko、CoinMarketCap
3. agent 的主要輸出先聚焦在 `HasToken` 與 `TokenTicker`
4. 所有最終 `yes / no / unknown` 都要帶證據與 URL
5. 若 3 類來源不足以支持結論，一律標 `unknown`

對應的顯式 prompt 模版見：

- `part4/agent_prompt_template.md`
