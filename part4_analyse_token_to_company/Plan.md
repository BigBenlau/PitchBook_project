# Part4: Token -> Founder / Related Company 高效率抽取方案

## 目標

對每個 token，盡可能快速且準確地產出這 3 類資訊：

1. `founder_people`
2. `related_companies`
3. `foundation_or_orgs`

其中：

- `founder_people` 只收明確被描述為 founder / co-founder / creator / inventor 的人
- `related_companies` 只收與 token 直接相關的公司主體，例如 issuer、developer、operator、parent company
- `foundation_or_orgs` 只收基金會、DAO、association、labs 等非公司組織

本段的核心不是「多抓資料」，而是：

- 先把 token 對到正確實體
- 再只抽有明確文字證據的 founder / company
- 不把模糊背景介紹、投資方、交易所、合作夥伴誤當成對應主體

---

## 最小正確資料流

最高效的做法不是直接把整段 token 頁面丟給模型，而是拆成 3 段：

1. `Token Canonicalization`
2. `Evidence Collection`
3. `Entity Extraction`

順序不能反。

### 1. Token Canonicalization

先建立 token 的 canonical key，再談 founder / company。

建議主鍵優先順序：

1. `cmc_slug`
2. `coingecko token_href -> slug`
3. `symbol + normalized token_name`

原因：

- `symbol` 重名很多，不能單獨用
- `name` 也會改名、縮寫、帶 wrapped / bridged 變體
- `slug` 是目前最穩定的聚合鍵

這一步的輸出至少要有：

- `token_name`
- `token_symbol`
- `coingecko_slug`
- `cmc_slug`
- `match_method`
- `match_confidence`

### 2. Evidence Collection

只抓對 founder / company 有用的來源，不抓整頁雜訊。

來源優先級：

1. 官方網站 / docs / whitepaper / about / team
2. CoinGecko `about_text`
3. CoinMarketCap `about_text`

理由很簡單：

- founder / issuer / foundation 最可靠的敘述通常在官方來源
- CG / CMC 很適合補 founder 段落，但常混入市場介紹、價格敘述、歷史背景
- 只靠 CG / CMC 可以做 baseline，但很難把 `related company` 做穩

### 3. Entity Extraction

不要直接讓模型從整篇文章自由總結。

先做一句一句的候選句篩選，只把含下列 trigger 的句子送去抽取：

- `founded by`
- `co-founded by`
- `created by`
- `invented by`
- `launched by`
- `issued by`
- `developed by`
- `operated by`
- `backed by`
- `maintained by`
- `foundation`
- `labs`
- `dao`
- `association`

然後才讓模型做兩件事：

1. 把句中實體分類到 `founder_people` / `related_companies` / `foundation_or_orgs`
2. 回傳短證據片段 `evidence_spans`

這會比直接餵整段 `about_text` 更快，也更不容易 hallucinate。

---

## 最推薦的實作口徑

### A. 用 CMC list 當 backbone

`part4/output/coinmarketcap_list.csv` 目前覆蓋面比 CoinGecko list 完整得多，應該作為主 token universe。

原因：

- CMC list 已有 `name`、`symbol`、`slug`
- 可直接組 detail URL
- ranking 與 slug 結構比較穩

CoinGecko 在這段應改成 enrichment source，而不是 backbone。

### B. CoinGecko 只負責補官方網站與補充 about

CoinGecko 的價值主要在：

- `token_href`
- `websites`
- `categories`
- `about_text`

其中最重要的是 `websites`，因為這能把後面的 founder / company 抽取導向官方來源。

### C. 先抽「候選證據句」，再進 LLM

推薦流程：

1. 從官方 / CG / CMC 文字中切句
2. 用 keyword/regex 把候選 founder/company 句過濾出來
3. 只把候選句送進 LLM
4. LLM 回傳結構化 JSON
5. 本地做去重、標準化、confidence 打分

這比「每個 token 丟兩大段 about_text 給模型」更省 token，也更穩。

### D. 不做全量 agent 廣搜，只做定向 fallback

agent 不應該成為主流程。

最合適的做法是：

1. `CG/CMC about` 先做 baseline
2. 官方網站只抓少量固定頁面
3. 只有 unresolved token 才進 agent

這樣的原因是：

- `CG/CMC` 便宜且快，適合先做第一輪召回
- 官方頁面對 founder / issuer / foundation 準確率最高
- agent 廣搜最慢，應只處理少量低信心或衝突樣本

### E. 官方來源只做定向抓取，不做泛搜索

若 CoinGecko `websites` 已提供官方站點，後續不應先走網頁廣搜。

優先抓以下頁面類型：

- `/about`
- `/team`
- `/foundation`
- `/docs`
- `/whitepaper`
- `/litepaper`

每個 token 最多抓 3 到 5 頁即可。

重點不是抓得多，而是抓 founder/company 高密度頁面。

### F. 嚴格區分 company / org / partner

以下不要直接算進 `related_companies`：

- 交易所 listing 平台
- 僅提供 custody / wallet / bridge 的平台
- 投資人或 portfolio fund
- 單純合作方

只有在文字明確說它是 issuer / operating company / developer / parent company 時，才進 `related_companies`。

### G. `unknown` 比猜測更重要

這段要接受大量空值。

如果文字沒有明確 founder / issuer / foundation：

- 不要猜
- 不要靠常識補
- 直接留空陣列

高 precision 比高 recall 更重要，因為這份表後續大概率會被拿去 join company / person 實體。

---

## 建議輸出欄位

除了你現在已有欄位，建議再加：

- `official_website`
- `source_priority`
- `source_urls`
- `match_method`
- `match_confidence`
- `evidence_source_labels`
- `needs_manual_review`

其中 `needs_manual_review = 1` 的條件可以是：

- 只有單一來源支持
- founder 與 company 來自不同來源且互相衝突
- 只命中 `symbol` fallback，沒有 slug match
- evidence 只提 project，沒提 token

---

## 最合適的輸入內容

這一段的核心不是把所有能抓到的文字都丟進模型，而是只輸入「最可能包含 founder / related company 的高信號文本」。

最合適的模型輸入應分 3 層。

### 第 1 層：CG / CMC 候選句

從這兩個欄位中切句：

- `about_text`
- `cmc_about_text`

但不要整段輸入。

先本地過濾，只保留含下列 trigger 的句子：

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

這一層最適合做第一輪抽取，原因是：

- 快
- 成本低
- 可以先把大量明顯 token 解掉

### 第 2 層：官方網站高信號段落

若第 1 層結果為空、低信心、或資訊不完整，才補官方來源。

官方來源最合適的輸入內容不是整頁全文，而是以下頁面的相關段落：

- about 頁中提到 project history / founding 的段落
- team 頁中提到 founder / co-founder 的段落
- foundation 頁中提到 foundation / association / DAO 的段落
- docs / whitepaper 中提到 issuer / developer / operating entity 的段落

這些段落應先本地抽出，再送模型，而不是直接把整頁 HTML 或整篇 whitepaper 丟進去。

### 第 3 層：agent fallback 的搜索輸入

只有少量 unresolved token 才值得進 agent。

這時最合適的 agent 輸入不是一句很泛的「幫我找 founder and company」，而是結構化 packet：

- token_name
- token_symbol
- cmc_slug
- coingecko_slug
- official_website
- 已收集到的 CG/CMC 候選句
- 已收集到的官方候選段落
- 明確問題：
  - founder_people 是誰
  - related_companies 是哪些 issuer / developer / operator / parent company
  - foundation_or_orgs 是哪些 foundation / DAO / association / labs
  - 僅接受有明確文字證據的答案

這樣 agent 不是從零開始搜，而是在既有證據上補缺口，速度會快很多。

---

## 最合適的模型與工具選型

這個問題其實分成 3 種不同工作：

1. 批量結構化抽取
2. pipeline 腳本開發與迭代
3. 少量 unresolved token 的 agent fallback

這 3 種工作不應該用同一個模型或同一種 agent 全包。

### 一、批量結構化抽取：最適合用「強結構化輸出模型」，不是 coding agent

這一層最重要的是：

- 能穩定輸出 JSON
- 指令遵循強
- 對短文本抽取 precision 高
- 成本和速度可控

最推薦順序：

1. `OpenAI GPT` 系列主模型 + Structured Outputs
2. `GLM-5` / `GLM-4.7`
3. `DeepSeek-V3.2`

#### 1. OpenAI GPT：最適合當主抽取模型

最合適用法：

- 對 `CG/CMC 候選句`
- 對 `官方網站高信號段落`
- 用 JSON schema 約束輸出

適合原因：

- OpenAI 官方明確提供 `Structured Outputs`
- GPT 系列官方定位對 coding / agentic tasks 很強，且對 schema-following 很成熟
- 最適合做「高 precision 的 sentence / paragraph extraction」

結論：

- 若你追求「快而準」且最在意輸出穩定性，主抽取模型首選 `OpenAI GPT`

#### 2. GLM-5 / GLM-4.7：最適合中文工作流與 agent/tool use 較重的場景

最合適用法：

- 中文為主的抽取與規則化任務
- 需要長上下文、工具調用、JSON 輸出
- 需要較高性價比的中國區工作流

適合原因：

- 智譜官方把 `GLM-5` 明確定位為面向 Agentic Engineering 的基座模型
- `GLM-4.7` / `GLM-5` 都強調 coding、agent、function call、structured output、長程任務
- 對中文環境和本地 agent 工作流通常更友好

結論：

- 若你的系統在中文環境、需要工具調用且希望成本更可控，`GLM-5` 是很合適的替代主模型

#### 3. DeepSeek-V3.2：最適合成本敏感的 batch baseline

最合適用法：

- 大批量第一輪 baseline 抽取
- 對明確 trigger 句做低成本結構化抽取

適合原因：

- DeepSeek 官方明確強調 `V3.2` 面向 agents、支持 tool-use
- 長上下文與工具調用能力足夠支撐這類 sentence extraction pipeline

限制：

- 若你最在意輸出穩定和 schema adherence，通常仍應把它放在 cost-sensitive baseline，而不是最高置信主模型

結論：

- 最適合拿來做第一輪低成本召回，不是最終高置信裁決模型

### 二、pipeline 腳本開發：最適合用 Codex / Claude Code 這類 coding agent

這一層的任務是：

- 寫抓取腳本
- 寫候選句過濾器
- 寫 review queue 規則
- 跑測試與修 bug

這不是一般抽取模型最擅長的工作。

最推薦順序：

1. `Codex`
2. `Claude Code`
3. `GLM Coding / TRAE / MonkeyCode`

#### 1. Codex：最適合做本專案的工程主 agent

最合適用法：

- 改 `part4` 腳本
- 做資料流調整
- 補 CSV merge / filter / validation / review queue

適合原因：

- OpenAI 官方把 Codex定位為 agentic coding system / coding agent
- 官方材料明確強調它適合長程工程任務、多任務並行、程式修改、測試與迭代

結論：

- 如果你的目標是把這整個 founder/company pipeline 做成可跑的工程，`Codex` 最適合當主開發 agent

#### 2. Claude Code：最適合當第二選 coding agent

最合適用法：

- 補腳本
- 做規則重構
- 協助 debug / review / iterate

適合原因：

- Anthropic 官方把 Claude Code定位為 terminal 中的 agentic coding tool
- 很適合讀代碼、改文件、跑命令、做實作迭代

結論：

- 若你的主工作流本來就在 Claude Code 上，它很適合承擔工程建設工作
- 但它不應取代主抽取模型本身

#### 3. GLM Coding / TRAE / MonkeyCode：適合國內開發工作流

最合適用法：

- 若你的 IDE / agent 平台以智譜生態為主
- 需要 coding agent 與國內模型切換

結論：

- 可作為工程實作環境，但對這個任務本身，核心仍是「抽取模型 + 規則管線」，不是 IDE 平台

### 三、unresolved token 的 fallback 調查：最適合用「有工具的 research/coding agent」，但只處理少量高價值樣本

這一層不是主流程。

只有以下情況才值得進 agent：

- 前兩層都沒有 founder/company
- 官方與 CG/CMC 互相衝突
- token 很重要，不能接受空值

最合適工具：

1. `Codex` with web/search tooling
2. `Claude` with tool use / web search
3. `GLM-5` / `AutoGLM` 類 agent

#### 這一層的原則

- agent 不是拿來跑全量 token
- agent 只處理 review queue 中最難的少數樣本
- agent 輸入必須是 packet，不是 open-ended 任務

### 四、最終推薦配置

若你要追求「快而準」，最合適的整體搭配是：

#### 方案 A：效果優先

- 主抽取模型：`OpenAI GPT` + Structured Outputs
- 工程 agent：`Codex`
- fallback agent：`Codex` 或帶工具的 `Claude`

適合：

- 最重視 precision
- 最重視 JSON 輸出穩定性
- 願意接受較高模型成本

#### 方案 B：平衡速度 / 成本 / 中文環境

- 主抽取模型：`GLM-5` 或 `GLM-4.7`
- 工程 agent：`Codex` 或 `Claude Code`
- fallback agent：`GLM-5 agent` / `Codex`

適合：

- 中文工作流較重
- 希望工具調用與長上下文更自然
- 成本比純 OpenAI 方案更可控

#### 方案 C：成本優先

- 第一輪 baseline：`DeepSeek-V3.2`
- 第二輪高置信複核：`OpenAI GPT` 或 `GLM-5`
- 工程 agent：`Codex` 或 `Claude Code`

適合：

- token 數量大
- 先要低成本跑出 baseline
- 再只對高價值或低信心樣本做升級判斷

### 五、對當前問題的最直接建議

若只看你現在這個任務，我的建議是：

1. `主抽取模型`：優先 `OpenAI GPT`，次選 `GLM-5`
2. `batch baseline`：若成本敏感，可先用 `DeepSeek-V3.2`
3. `工程實作 agent`：優先 `Codex`，次選 `Claude Code`
4. `fallback 調查 agent`：只在 unresolved token 上使用 `Codex` / `Claude` / `GLM agent`

一句話總結：

- 抽取任務不要用 coding agent 當主模型
- 工程開發任務不要用普通抽取模型硬做
- agent 只處理少量高難樣本，不能放進主流程

---

## 建議 pipeline

### Step 1. 建 token backbone

輸入：

- `part4/output/coinmarketcap_list.csv`

輸出：

- `token_master.csv`

內容至少包含：

- `token_name`
- `token_symbol`
- `cmc_slug`
- `cmc_rank`

### Step 2. 補 CoinGecko 對應

輸入：

- `token_master.csv`
- `part4/output/coingecko_all_crypto_list.csv`

匹配順序：

1. slug
2. symbol + normalized name
3. exact normalized name

輸出：

- `token_master_enriched.csv`

新增欄位：

- `coingecko_slug`
- `token_href`
- `match_method`
- `match_confidence`

### Step 3. 收集 founder/company 相關文本

每個 token 只保留以下來源：

1. 官方 about / team / docs / whitepaper 中與 founder/company 有關的段落
2. CoinGecko `about_text`
3. CMC `about_text`

輸出：

- `token_evidence_text.csv`

### Step 4. 先做本地候選句抽取

從 `token_evidence_text.csv` 切出候選句，輸出：

- `token_evidence_sentences.csv`

每列包含：

- `token_id`
- `source`
- `sentence`
- `trigger_keyword`

這一步是整個流程最重要的成本控制點。

原則是：

- 模型不看全文
- 模型只看高信號句
- 官方長文先抽段，再抽句

### Step 5. LLM 只做 sentence-level extraction

模型輸入只看候選句，不看整篇全文。

模型輸出：

- `founder_people`
- `related_companies`
- `foundation_or_orgs`
- `evidence_spans`
- `confidence`
- `notes`

輸出：

- `founder_company_extracted.csv`

### Step 6. 官方定向補抓

對於 Step 5 後仍然 unresolved 的 token，才執行官方網站定向補抓。

優先順序：

1. `official_website/about`
2. `official_website/team`
3. `official_website/foundation`
4. `official_website/docs`
5. `official_website/whitepaper`

若補抓後仍無明確證據，再考慮 agent。

### Step 7. agent fallback

只對下列 token 使用 agent：

- `founder_people`、`related_companies`、`foundation_or_orgs` 全空
- 或來源互相衝突
- 或 token 非常重要，不能接受空值

agent 的任務應限制為：

- 只確認 founder/company/org
- 必須帶明確文字證據
- 不做泛化總結

### Step 8. 自動打 review queue

低信心、單來源、或衝突資料自動進：

- `founder_company_review_queue.csv`

---

## 目前 part4 的主要問題

這段目前的核心問題不是 sample 數量少。

`coingecko_all_crypto_list.csv`、`coingecko_about.csv`、`cmc_about_qa.csv` 目前行數較少，是因為這些文件本來就只是測試樣本；這是正常的，不代表 pipeline 無法擴展。

真正的結構性問題主要有 3 個：

### 1. 目前 extraction 太依賴長文 about

現在 `4_extract_founder_companies.py` 是把整段 CG / CMC about 直接塞進任務。

問題是：

- token 成本高
- 雜訊多
- 容易把 partner / ecosystem / exchange 混進 related company

### 2. 缺官方來源

如果你的目標是「對應 founder and related company」，
那官方網站通常比 CG / CMC 更值得優先抓。

只靠聚合站可以先做 baseline，但很難做成高準確率主表。

### 3. agent 使用位置太前

如果在 baseline 不足時，立刻改成 agent 廣搜，會有 3 個問題：

- 耗時長
- 成本高
- 結果口徑不穩

更合理的做法是先做：

1. `CG/CMC` 候選句抽取
2. 官方定向補抓
3. 最後才 agent fallback

---

## 最有效率的版本

如果你現在要在「快」和「準」之間取最優解，建議直接用下面這版：

1. `CMC list` 當 token backbone
2. `CoinGecko` 補 `official website + about_text`
3. `CG/CMC about` 先抽候選句
4. LLM 先做第一輪 sentence-level extraction
5. unresolved token 再去官方網站定向補抓
6. 只有少量 unresolved / conflict token 才進 agent
7. 最後再做 review queue

這版的優點：

- 比全量人工查快很多
- 比直接全文丟模型準很多
- 對後續 join founder person / related company entity 最友善

---

## 最合適的檢查方案

這部分不要只靠人工 spot check，也不要只看模型信心。

最合適的是做「規則檢查 + 分層抽樣檢查 + 少量人工 review」。

### A. 規則檢查

先做本地自動檢查，攔掉格式錯與明顯誤判。

至少要檢查：

1. `founder_people` 不應包含公司名、基金會名、DAO 名
2. `related_companies` 不應包含 exchange 名、VC 名、一般 partner，除非文字明確寫 issuer / operator / developer / parent company
3. `foundation_or_orgs` 不應混入 Inc. / Ltd. / LLC 類公司
4. 每個抽取結果都必須至少有一條 `evidence_span`
5. `high confidence` 必須有官方來源，或至少 `CG + CMC` 一致
6. 只有單一來源支持的結果，最高只能到 `medium`

### B. 分層抽樣檢查

人工檢查不要隨機亂抽，應按風險分層抽樣：

1. `high confidence`
2. `medium confidence`
3. `low confidence`
4. `needs_manual_review = 1`
5. 只有 `CG/CMC` 支持但沒有官方來源
6. 只有官方來源支持但 `CG/CMC` 為空

每層都抽樣，這樣你才能知道哪一層最容易錯。

### C. 以錯誤類型為中心做回看

人工檢查時，優先看這幾類錯：

1. 把 partner / investor 誤當 related company
2. 把 foundation / DAO 誤當 company
3. 把 contributor / early developer 誤當 founder
4. 把 project 層級名字和 token 層級名字混在一起
5. 把 wrapped / bridged token 的上游資產團隊誤當成該 token 的 founder/company

這幾類錯比單純漏抓更傷，因為會污染後續 join。

### D. review queue 的最合適進入條件

以下情況最適合進 review queue：

- 多來源衝突
- 只抓到 company，抓不到 founder，但 evidence 很弱
- 只抓到 founder，抓不到 issuer / foundation
- 只有單一 about 來源支持
- wrapped / bridged / staked 類 token
- meme / community token
- rebrand 後名稱與主體不穩定的 token

### E. 最後的品質衡量

這段最適合看的不是單純 `coverage`，而是：

1. `precision`
2. `official-source-supported rate`
3. `fallback-to-agent rate`
4. `manual-review rate`

你真正想要的是：

- precision 高
- 官方支持率高
- agent fallback 比例低
- manual review 比例可控

而不是盲目追求全部 token 都有 founder/company 結果。

## 本輪建議

本輪先不要再擴 prompt，先做這 4 件事：

1. 把 `CMC -> CoinGecko` 的 canonical mapping 表做穩
2. 把 `CG/CMC about -> 候選句` 的本地過濾加上去
3. 在 evidence collection 裡加入 `official_website` 的定向補抓
4. 為抽取結果加上 `review queue` 規則

只要這 4 步做完，`part4` 就會從「樣本型抽取」變成一個兼顧速度、準確率與成本的穩定流程。
