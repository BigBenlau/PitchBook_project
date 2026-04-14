# Part4 Pipeline Spec

## 目標

Part4 的目標不是「抽到一些 founder/company/org 就算完成」。

新的目標是：

- 每個 token 都先 canonicalize
- 每個 token 都生成全域穩定主鍵 `token_id`
- 每個 token 都先經過 `token_type` router
- 每個 token 的三個 target 都必須跑完：
  - `founder_people`
  - `related_companies`
  - `foundation_or_orgs`
- 每個 target 都要有 field-level completeness state
- 沒有任何 token 可以因為 trigger 沒打中、batch id 錯誤、或 partial output 而被靜默漏掉

---

## 一、輸入改造

### 原則

Part4 的 preparation input 必須改成：

- CoinGecko token list 和 CoinMarketCap token list 的並集

不要再把單一來源的列表當成唯一主表。

### Preparation 輸入

- CoinGecko token list
- CoinMarketCap token list
- CoinGecko about / metadata
- CoinMarketCap about / metadata
- website metadata

### Preparation 輸出

- `output/token_master.csv`

### `token_master.csv` 最低欄位

- `token_id`
- `token_name`
- `token_symbol`
- `token_href`
- `coingecko_slug`
- `cmc_slug`
- `official_website`
- `token_type`
- `routing_reason`
- `cg_about_text`
- `cmc_about_text`

---

## 二、全域穩定主鍵

### 必須新增 `token_id`

Preparation 階段就生成：

- `token_id`

它是整條線唯一 merge key。

### 規則

- 優先使用已對齊的 `coingecko_slug + cmc_slug`
- 若只有單邊 slug，就用該 slug + normalized `token_name` + `token_symbol`
- 若只有名稱與 symbol，仍要生成 deterministic key

### 禁止事項

- 不要用 batch-local `row_index` 當最終主鍵
- 不要讓 verifier / collector 依賴 batch-local 序號合併

---

## 三、入口新增 token_type router

### 目的

不同 token 類型的 founder / company / foundation 證據不一樣，不能走同一套規則。

### 建議類型

- `base_asset`
- `protocol_token`
- `exchange_token`
- `fiat_stablecoin`
- `wrapped_or_bridged`
- `liquid_staking_or_receipt`
- `synthetic_or_fund`
- `meme_or_community`
- `unknown`

### Router 影響

router 不是 metadata；它直接決定：

- official evidence 的抓取優先順序
- 哪些 target 比較可能是 `not_applicable`
- 哪些 token 必須更嚴格 review
- Layer 3 fallback 的優先級

### 例子

- `wrapped_or_bridged`：
  不得直接繼承 underlying token 的 founder/company/foundation

- `liquid_staking_or_receipt`：
  優先找 operator / issuer / DAO / foundation，不優先找 underlying chain founders

- `fiat_stablecoin`：
  優先找 issuing entity、trust、consortium、operator、foundation

---

## 四、輸出檔案簡化

目前輸出檔案太多，應合併。

### 最終輸出只保留

- `agent_runs/token_company/token_master.csv`
- `agent_runs/token_company/token_entity_results.csv`
- `agent_runs/token_company/token_entity_review_queue.csv`
- `agent_runs/token_company/verification_findings.csv`
- `agent_runs/token_company/checkpoint.json`

### batch-local 檔案縮減為

- `prepared_batch.csv`
- `official_evidence.csv`
- `entity_sentences.csv`
- `token_entity_results.csv`
- `layer3_packet.jsonl` 只有 unresolved token 才有
- `verification/verification_report.csv`
- `verification/verification_summary.md`

### 不再保留

- 分離的 `founder_company_extracted.csv`
- 分離的 `founder_company_validated.csv`
- 分離的 batch-local review queue

除非只是 debug 暫存，否則不該成為主 contract。

---

## 五、結果 schema 簡化

### 一個 token 一行

`token_entity_results.csv` 建議欄位：

```csv
token_id,token_name,token_symbol,coingecko_slug,cmc_slug,token_href,official_website,token_type,founder_people,founder_status,founder_evidence_spans,related_companies,related_company_status,related_company_evidence_spans,foundation_or_orgs,foundation_status,foundation_evidence_spans,source_urls,source_labels,confidence,needs_manual_review,notes,status
```

### 取消不必要欄位

以下欄位不該進 final merged outputs：

- `row_index`
- `batch_id`
- `trigger_keyword`
- `cmc_match_method` 細節列
- `sentence_risk_flags` 細節列
- `suggested_confidence_cap`
- 多個重複 debug 欄位

這些可以留在 verifier findings 或 batch-local debug artefacts，不應污染最終主表。

---

## 六、completeness contract 改成 field-level

### 核心變更

不要再用 row-level completion。

要改成：

- `founder_status`
- `related_company_status`
- `foundation_status`

### 允許值

- `supported`
- `unresolved`
- `not_applicable`

### 規則

- founder 找到了，不代表 row 就完成
- company 沒找到，必須明確標 `unresolved` 或 `not_applicable`
- foundation 沒跑到，不可默默留空

### 例子

某 token：

- `founder_status = supported`
- `related_company_status = unresolved`
- `foundation_status = unresolved`

這個 token 仍然必須升級，不可直接視為完成。

---

## 七、流程重排：先 official/company，再 founder 補充

這是本次最重要的流程調整。

### 新順序

1. Preparation: union of CG + CMC lists
2. Generate `token_id`
3. Run `token_type` router
4. Batch from `token_master.csv`
5. Collect official/company evidence first
6. Extract official company/foundation/operator/issuer sentences
7. Add CG/CMC founder-history sentences as supplemental evidence
8. Run field-level extraction
9. Run field-level completeness gate
10. Build Layer 3 packet only for unresolved fields
11. Fresh verifier
12. Collector merge

### 為什麼

當前流程容易先從 CG/CMC 抓 founder，再回頭補 official evidence。

這會造成：

- founder 抽得比較完整
- related_company / foundation 常常缺失
- partial row 被過早接受

對 `related_companies`、`foundation_or_orgs`，官方 evidence 幾乎總是比 CG/CMC about 更重要。

---

## 八、official evidence 優先級

對 company/foundation 類 target，先抓：

1. homepage 中的 about / company / legal / team / foundation / governance link
2. docs 子網域
3. whitepaper / litepaper / faq
4. blog / announcements

不要只依賴固定 suffix。

### 特別需要抓的頁面

- `/about`
- `/team`
- `/foundation`
- `/governance`
- `/company`
- `/legal`
- `/terms`
- `/docs`
- whitepaper PDF

---

## 九、sentence extraction 也要 target-aware

不能再用單一 trigger list。

### founder triggers

- `founder`
- `co-founder`
- `created by`
- `invented by`
- `launched by`

### related-company triggers

- `issuer`
- `issuing entity`
- `operator`
- `operated by`
- `developed by`
- `maintained by`
- `parent company`
- `trust company`
- `legal entity`

### foundation/org triggers

- `foundation`
- `dao`
- `association`
- `labs`
- `governed by`
- `stewarded by`

### hard rule

如果 founder triggers 一條都沒中：

- token 仍然要保留
- company/foundation target 仍然要跑
- unresolved field 仍然要進 completeness gate

---

## 十、Layer 3 fallback 要變成真正閉環

Layer 3 不應只是 `pending_agent` 狀態。

### Layer 3 packet 必須帶

- `token_id`
- `token_type`
- `token_name`
- `token_symbol`
- `official_website`
- official company/foundation evidence
- CG/CMC founder evidence
- 目前三個 field 的 status
- 明確 unresolved fields

### Layer 3 輸出

Layer 3 必須回傳完整 replacement row：

- 不是 comment
- 不是只補一個 founder 名字
- 而是完整 `token_entity_results` row

---

## 十一、verifier 要做什麼

Verifier 不只檢查對不對，還要檢查是否完整跑完。

### verifier 應檢查

- founder 是否漏報
- related_company 是否漏報
- foundation 是否漏報
- entity type 是否錯
- `token_type` routing 是否錯
- 是否有 field 根本沒跑到
- 是否有 token 應該升級但沒升級

### verifier output

`verification_report.csv` 建議欄位：

```csv
token_id,token_name,worker_founder_status,worker_related_company_status,worker_foundation_status,verifier_founder_status,verifier_related_company_status,verifier_foundation_status,verdict,error_type,error_reason,evidence_notes,recommended_action,corrected_result_row_json
```

如果 `recommended_action = edit_row`：

- `corrected_result_row_json` 必填
- collector 可直接 authoritative 套用

---

## 十二、review queue 進入條件要改

不是只有 low confidence 或有 issues 才進 queue。

### 新規則

任一條件成立就進 queue：

- `founder_status = unresolved`
- `related_company_status = unresolved`
- `foundation_status = unresolved`
- `token_type` 是 wrapped / bridged / liquid staking / synthetic
- official company/foundation evidence 缺失
- verifier 要求 escalation

---

## 十三、Collector 必須保證不靜默漏 token

Collector 需要新增硬規則：

1. `token_master.csv` 裡的每個 `token_id` 都必須在 merged outputs 出現
2. 每個 `token_id` 只能有一條最終 row
3. empty arrays 若沒有對應 field status，直接報錯
4. unresolved verifier edit 不可 merge
5. batch-local failure 不可讓 token 靜默消失

---

## 十四、一句話總結新的 Part4

新的 Part4 不是：

- 先看 about text
- 抽一輪 founder/company/org
- 有抽到就算完成

而是：

- 用 CG + CMC 並集建立 `token_master`
- 先生成 `token_id`
- 先做 `token_type` routing
- 先抓 official/company evidence
- 再補 founder 歷史 evidence
- 對三個 target 做 field-level completeness
- unresolved 就升級
- verifier 與 collector 保證沒有 token 被靜默漏掉
