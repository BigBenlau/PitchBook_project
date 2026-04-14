# Part5 Agent Prompt Template

本文件是 part5 的 agent prompt 模版。每次 part5 skill 或 worker 運行前，必須先讀：

1. `part5_analyse_company_to_token/Plan.md`
2. 本文件

若本文件與 `Plan.md` 衝突，以 `Plan.md` 為準。

## Scope

任務目標：

- 先判斷公司類型與 crypto project 可能性。
- 將 classifier/router 決策寫入 `classifier_results.csv`。
- 只關注 fungible token project。
- 根據 `search_tier` 決定 full / light / skip_candidate 搜索深度。
- 找出公司對應的 zero / one / many crypto projects。
- 找出所有可靠映射到該公司或其 owned project 的 fungible token tickers。
- 每家公司固定輸出一行 CSV。

不做：

- NFT collection mapping，除非同時存在 fungible token。
- listing venue / listing date 深搜。
- 投資分析、估值分析、市場表現分析。
- 只因公司與 crypto 相關就推斷其有 token。

## Required Workflow

按以下順序執行，不要跳步：

1. 讀 `Plan.md`，以其中的 schema、classifier、verification、model policy 為準。
2. 讀公司 row，理解為什麼它出現在 `crypto_company.csv`。
3. 先做 company relevance classifier/router。
4. 填寫 `company_type`、`crypto_project_likelihood`、`search_tier`、`project_search_required`、`risk_flags`、`classifier_reason`。
5. 將 classifier/router 決策寫入 `classifier_results.csv`。
6. 如果 `search_tier = skip_candidate`，不要做 full/light search，直接輸出一行，`token_ticker = []`。
7. 如果 `search_tier = light`，按固定 light query playbook 做 bounded lightweight token-existence check。
8. 如果 `search_tier = full`，按固定 full query playbook 做 company -> project -> fungible token ticker mapping。
9. 找到多個 project 或多個 token 時，仍輸出一行，用 JSON list 記錄。
10. 若沒有可靠證據確認 fungible token，`token_ticker = []`，不要輸出 `no` 或 `unknown`。
11. 若資料衝突、品牌映射不穩、或不確定是否漏報/多報，設 `needs_manual_review = yes`。

## Stage 1: Classifier Rules

Classifier/router 需要回答：

- 這是什麼類型的公司？
- 它為什麼被 crypto / blockchain dataset 抽中？
- 它是否可能有 owned crypto project？
- 它應該使用哪個 search tier？

`classifier_results.csv` 欄位必須是：

```csv
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,search_tier,project_search_required,risk_flags,classifier_reason
```

`company_type` 只能使用以下值：

- `protocol_or_network`
- `dapp_or_product`
- `exchange_or_broker`
- `wallet_or_custody`
- `mining_or_validator`
- `infrastructure_or_data`
- `security_or_compliance`
- `service_provider`
- `investment_or_holdings`
- `media_or_education`
- `gaming_or_nft`
- `traditional_business`
- `unclear`

`crypto_project_likelihood` 只能使用：

- `high`
- `medium`
- `low`
- `none`
- `unclear`

`project_search_required` 只能使用：

- `yes`
- `no`

`search_tier` 只能使用：

- `full`
- `light`
- `skip_candidate`

設 `search_tier = full` 的情況：

- 公司經營 protocol、network、dapp、exchange、wallet、tokenized product 或 blockchain-native product。
- row 中提到 project、token、whitepaper、docs、protocol、chain、app、DAO、ecosystem。
- 公司名稱、alias、former name、legal name 或 website 暗示 project identity 可能不同於公司法定名稱。
- 你無法高置信度排除 project/token 可能性。

設 `search_tier = light` 的情況：

- 公司 crypto-adjacent 或低可能性，但仍有 enough signal 做 cheap token-existence check。
- service provider、infrastructure、media、mining、validator、custody、analytics、security、compliance、NFT、gaming、investment 類公司有一些 crypto/project context。
- 官方 domain、alias、former name 或 description 有 token/project-like terms，但不足以 justify full search。
- source context 薄、模糊、可能過時。

只有在明顯不相關時才設 `search_tier = skip_candidate`，例如：

- 傳統公司，只因弱 crypto keyword 被抽中。
- consulting、legal、accounting、recruitment、marketing、event、generic service provider，且沒有 owned project signal。
- investor、holding company、VC、accelerator，且沒有 owned crypto project signal。
- media、education、research company，且沒有 owned crypto project signal。
- mining、validator、custody、analytics、security、compliance company，且沒有 owned token/project signal。
- NFT-only / collectible-only / gaming asset company，且沒有 fungible token signal。

`project_search_required = yes` 用於 `full` 或 `light`。

`project_search_required = no` 只用於 `skip_candidate`。

`risk_flags` 必須是 JSON list string，例如 `["alias_or_former_name","token_keyword"]`。沒有 risk flag 時寫 `[]`。

保守規則：

- 不確定時，設 `search_tier = full`。
- token budget 有壓力但不能排除 project/token relevance 時，用 `light`，不要用 `skip_candidate`。
- `skip_candidate` 必須能用 `classifier_reason` 清楚解釋。

## Stage 2: Search Rules

若 `search_tier = full`：

- 可以自由搜索資料。
- 不限制為官網、CoinGecko、CoinMarketCap。
- 優先使用 primary sources，但可用可靠 secondary sources 做 discovery / corroboration。
- 搜索深度應按公司 ambiguity 和 project likelihood 調整。
- 但不要自由發散。先按固定 full query playbook 做，再按需要擴展。

若 `search_tier = light`：

- 保持 token usage 低。
- 先用 exact company name、alias、former name、normalized_domain。
- 優先官方 domain 和 exact-match major token data pages。
- 如果發現 plausible token / project signal，升級為 full search；若 round budget 不支持 full rerun，設 `needs_manual_review = yes`。
- 不要跳過 fixed light query playbook。

若 `search_tier = skip_candidate`：

- 不做 full/light search。
- 結果 row 的 `project_search_reason` 應來自 `classifier_reason`。

### Light Query Playbook

`search_tier = light` 時，固定按以下順序查。除非明確找到強 evidence，否則不要超出這個 playbook：

1. `exact-domain token probe`
   - 用 `normalized_domain` 或官網 host 查 token / ticker / coin / docs / whitepaper exact matches。
2. `company-name exact probe`
   - 用 `CompanyName` 查 token / ticker / coin / protocol exact matches。
3. `alias probe`
   - 對 `CompanyAlsoKnownAs` 中的主要 alias 做 exact token/project probes。
4. `former-name probe`
   - 對 `CompanyFormerName` 做 exact token/project probes。
5. `major token-page exact probe`
   - 在 CoinGecko / CoinMarketCap 做 exact project or token page match，並檢查 page 是否能映射回官方 domain / 官方 project。

Light tier hard rules:

- 在輸出 `token_ticker = []` 前，必做 `exact-domain token probe`。
- 若任何 probe 出現 plausible company -> project -> token signal，升級為 `full` 或設 `needs_manual_review = yes`。
- Light tier 的目的只是快速排除低機率 row，不是憑感覺結案。

### Full Query Playbook

`search_tier = full` 時，固定按 company -> project -> token 三段執行：

1. `company identity stage`
   - 確認 official domain、brand、alias、former name。
   - 至少找到一個 primary source 支持目前公司 / 品牌身份。
2. `project discovery stage`
   - 找公司對應的 protocol / app / platform / ecosystem / tokenized product 名稱。
   - 至少找到一個 primary source 支持 project identity。
3. `token confirmation stage`
   - 針對已確認的 project 查 fungible token name / ticker / token page。
   - 至少找到一個 primary source 支持 token identity；token data page 可作 corroboration，但不能替代 company/project mapping。

Full tier hard rules:

- 在輸出 `token_ticker = []` 前，必做 `exact-domain token probe`。
- 若只找到 token page，但不能映射回 official project / company，不可填入 `token_ticker`。
- 若 company / project / token 三段任一段 mapping 不穩，設 `needs_manual_review = yes`。

推薦來源順序：

1. 官方網站、docs、whitepaper、litepaper、blog、FAQ、governance forum、announcement。
2. CoinGecko、CoinMarketCap 或類似 token data pages。
3. Project docs、GitHub、explorer、exchange pages、audit docs、foundation pages。
4. 用可靠 secondary sources 幫助 disambiguation。

不能單獨作為 token evidence：

- 搜索結果 snippet。
- 沒有強證據補充的社交媒體貼文。
- 無 company/project mapping 的 token list。
- stock `Exchange` / `Ticker`。
- NFT collection symbol，除非它也是 fungible token ticker。
- 看起來像 ticker 但不能映射回該公司或 owned project 的字符串。

## Input Fields

你會收到以下字段：

- `task_index`
- `CompanyID`
- `CompanyName`
- `CompanyAlsoKnownAs`
- `CompanyFormerName`
- `CompanyLegalName`
- `Website`
- `normalized_domain`
- `ParentCompany`
- `Exchange`
- `Ticker`
- `HQLocation`
- `HQCountry`
- `Verticals`
- `EmergingSpaces`
- `Description`
- `Keywords`
- `MatchedKeywords`
- `MatchedColumns`
- `CryptoRelevanceContext`
- `SearchPolicy`
- `AgentTaskScope`

字段用途：

- company / brand / project disambiguation。
- 判斷公司類型與 project likelihood。
- 理解 row 為什麼被 crypto candidate pipeline 抽中。
- 找到官方 domain、project name、whitepaper、docs 或 token evidence。
- 避免把上市公司股票 ticker 誤判成 crypto token ticker。

不能只因為 `Verticals`、`Keywords`、`MatchedKeywords`、`MatchedColumns` 提到 crypto/blockchain/exchange，就直接填 token。

## Required Output Format

輸出必須是 CSV。若只處理一家公司，輸出 header 加一行資料；若處理多家公司，輸出一個 header，然後每家公司一行。

CSV 欄位必須按以下 v2 schema 順序輸出：

```csv
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,project_search_required,project_search_reason,project_name,project_url,status,completed_at,token_ticker,token_name,token_url,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review
```

字段規則：

- `company_type`: 必須使用 classifier allowed values。
- `crypto_project_likelihood`: `high` / `medium` / `low` / `none` / `unclear`。
- `project_search_required`: 必須與 classifier/router 結果一致，`full` / `light` 為 `yes`，`skip_candidate` 為 `no`。
- `project_search_reason`: 簡短說明 full/light search 結論，或 skip_candidate 的 final no-token 理由。
- `project_name`: JSON list string；沒有則 `[]`。
- `project_url`: JSON list string；沒有則 `[]`。
- `status`: 固定 `completed`。
- `completed_at`: ISO timestamp；不知道可留空。
- `token_ticker`: JSON list string；找到所有可靠 fungible tickers；沒有則 `[]`。
- `token_name`: JSON list string；沒有則 `[]`。
- `token_url`: JSON list string；沒有則 `[]`。
- `has_token_evidence`: 簡短證據摘要。
- `evidence_urls`: 多個 URL 用 `|` 分隔。
- `evidence_source_types`: 多個來源類型用 `|` 分隔，例如 `official_site|coingecko|coinmarketcap|whitepaper|docs|explorer|exchange|secondary_source`。
- `confidence`: `high` / `medium` / `low`。
- `needs_manual_review`: `yes` / `no`。

`confidence` 與 `needs_manual_review` 必須分開判斷：

- `high`: 公司 / project / token mapping 清楚，且有官方或強 primary evidence。
- `medium`: 證據足以合併結果，但不如 `high` 完整。
- `low`: 證據偏弱、偏薄，或覆蓋不足。
- 不可只因為 `confidence` 不是 `high`，就把 `needs_manual_review` 設為 `yes`。
- 若 mapping 穩定、沒有 source conflict、verifier 也接受，`medium` confidence 可以是 `needs_manual_review = no`。

CSV 安全規則：

- JSON list 欄位必須是合法 JSON list。
- 欄位含逗號、換行或雙引號時，必須按標準 CSV 規則加雙引號並轉義。
- 不要輸出 `CompanyID`、`CompanyName`、`has_token`、`raw_output` 這些舊欄位。
- 不要輸出 Markdown，不要輸出解釋段落，只輸出 CSV。

## Manual Review Rules

以下情況設 `needs_manual_review = yes`：

- classifier 不確定但仍跳過 project search。
- company-to-project mapping 模糊。
- token page 存在，但不能清楚映射回公司或 owned project。
- sources disagree。
- official site dead / unavailable / too thin。
- 公司有多品牌、former name、subsidiary、foundation、DAO，可能影響 mapping。
- NFT-only 或 gaming 相關，但可能同時存在 fungible token。
- worker 不能高置信度判斷是否漏報或多報 token。

不要只因為 `confidence = medium` 或 `low` 就設 `needs_manual_review = yes`。

Verifier 規則：

- 若 verifier 與原結果一致，`needs_manual_review` 應為 `no`，除非仍有未解決的 mapping / source ambiguity。
- 若 verifier 能補上 token，且修正後 mapping 清楚、sources 不衝突，`needs_manual_review` 應為 `no`。
- 只有 verifier 仍認為不確定、或要求 `mark_manual_review` 時，才保留 `needs_manual_review = yes`。

## Input Template

```text
task_index: {task_index}
CompanyID: {CompanyID}
CompanyName: {CompanyName}
CompanyAlsoKnownAs: {CompanyAlsoKnownAs}
CompanyFormerName: {CompanyFormerName}
CompanyLegalName: {CompanyLegalName}
Website: {Website}
normalized_domain: {normalized_domain}
ParentCompany: {ParentCompany}
Exchange: {Exchange}
Ticker: {Ticker}
HQLocation: {HQLocation}
HQCountry: {HQCountry}
Verticals: {Verticals}
EmergingSpaces: {EmergingSpaces}
Description: {Description}
Keywords: {Keywords}
MatchedKeywords: {MatchedKeywords}
MatchedColumns: {MatchedColumns}
CryptoRelevanceContext: {CryptoRelevanceContext}
SearchPolicy: {SearchPolicy}
AgentTaskScope: {AgentTaskScope}
```

## Output Template

```csv
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,project_search_required,project_search_reason,project_name,project_url,status,completed_at,token_ticker,token_name,token_url,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review
{task_index},{CompanyID},{CompanyName},{normalized_domain},protocol_or_network,high,yes,"company appears to operate a protocol or blockchain-native product","[""Example Protocol""]","[""https://example.com""]",completed,{completed_at},"[""TOKEN""]","[""Example Token""]","[""https://www.coingecko.com/en/coins/example""]","official docs and token data page map the project to TOKEN","https://example.com/|https://www.coingecko.com/en/coins/example","official_site|coingecko",high,no
```

## Round-End Verifier Prompt

每個 round 結束前，主 agent 必須重新 spawn verifier subagent。verifier 不要重用原 worker。

Verifier 需要讀：

- `part5_analyse_company_to_token/Plan.md`
- 本輪 input tasks
- 本輪 `classifier_results.csv`
- 本輪 worker `results.csv`
- worker evidence URLs

Verifier 任務：

- 先讀 classifier/router 結果，再判斷 worker 結果。
- 檢查 `search_tier` 是否過度保守。
- 檢查 `skip_candidate` 是否合理，是否應該改成 `light` 或 `full`。
- 重新檢查每家公司 `token_ticker` list 是否漏報。
- 重新檢查是否多報、不相關 ticker、stock ticker、NFT-only symbol、chain name、product code。
- 檢查 `project_search_required = no` 的 row 是否真的應該跳過深搜。
- 檢查多 project / 多 token 是否正確放在同一行 JSON list。
- 發現錯誤時，指出原因與建議動作。

Verifier 輸出 `verification_report.csv`：

```csv
task_index,company_id,company_name,classifier_search_tier,worker_token_ticker,verifier_search_tier,verifier_token_ticker,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

允許 `verdict`：

- `pass`
- `suspected_missing_token`
- `suspected_extra_token`
- `wrong_project_mapping`
- `non_fungible_or_stock_ticker`
- `search_tier_too_conservative`
- `search_should_not_have_been_skipped`
- `insufficient_evidence`

允許 `recommended_action`：

- `accept_worker_row`
- `edit_row`
- `mark_manual_review`
- `rerun_company`
- `rerun_batch`
- `update_prompt_or_process`

`edit_row` 規則：

- 若 `recommended_action = edit_row`，必須填 `corrected_result_row_json`。
- `corrected_result_row_json` 必須是一個完整 JSON object，欄位使用 result CSV 的完整 schema，不可只填局部 patch。
- harness collector 會把這個 corrected row 視為 authoritative correction 套用。

Verifier 同時輸出 `verification_summary.md`，說明：

- checked row count
- pass count
- non-pass count
- suspected missing token count
- suspected extra token count
- wrong mapping count
- skipped-search concern count
- systematic causes found
- recommended process updates
