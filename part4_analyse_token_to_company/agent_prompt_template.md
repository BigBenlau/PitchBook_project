# Part4 Agent Prompt Template

每次 part4 worker / verifier / main-agent 協調前，必須先讀：

1. `part4_analyse_token_to_company/Plan.md`
2. 本文件

若本文件與 `Plan.md` 衝突，以 `Plan.md` 為準。

## Scope

任務目標：

- 先判斷 token 類型與 company linkage 可能性
- 先寫 `classifier_results.csv`
- 再做 token -> project -> responsible entity mapping
- 每個 token 固定輸出一行

不做：

- 行情、投資、價格分析
- listing history
- 無根據地把 token 直接映射到公司或其他實體

## Required Workflow

1. 讀 `Plan.md`
2. 讀當前 token row
3. 先做 classifier/router
4. 寫 `token_origin_type`、`entity_link_likelihood`、`search_tier`、`entity_search_required`、`risk_flags`、`classifier_reason`
5. 先把 classifier row 寫成結構化 JSON，再用 `scripts/part4_safe_csv_append.py` 寫入 `classifier_results.csv`
6. 若 `search_tier = skip_candidate`，直接輸出一行 no-entity 結果
7. 若 `search_tier = light`，做 bounded check
8. 若 `search_tier = full`，做完整 token -> project -> company research
9. 搜索開始時，必須先訪問 token row 中可用的 canonical CG / CMC slug page
10. 若 `from_cg = 1` 或 `cg_url` 存在，必須直接訪問 `cg_url`
11. 若 `from_cmc = 1` 或 `cmc_url` 存在，必須直接訪問 `cmc_url`
12. 若同時屬於 CG 與 CMC，2 個頁面都必須訪問
13. 所有 entity / project 類欄位都用 JSON list string
14. 只有 issuer / operator / steward / legal counterparty 類主體才可映射為 entity
15. 不可把僅僅提到 token 的 advocacy group、社群組織、歷史基金會自動記為 mapped entity
16. 有衝突或 unresolved ambiguity 時才設 `needs_manual_review = yes`

## Classifier Header

```csv
task_index,canonical_slug,token_symbol,token_name,token_origin_type,entity_link_likelihood,search_tier,entity_search_required,risk_flags,classifier_reason
```

Allowed `token_origin_type`：

- `layer1_or_l2`
- `protocol_or_app`
- `exchange_token`
- `stablecoin`
- `wrapped_or_bridged_asset`
- `liquid_staking_or_restaking`
- `asset_backed_or_rwa`
- `meme_or_community`
- `governance_or_utility`
- `unclear`

Allowed `entity_link_likelihood`：

- `high`
- `medium`
- `low`
- `none`
- `unclear`

Allowed `search_tier`：

- `full`
- `light`
- `skip_candidate`

`entity_search_required`：

- `yes` for `full` / `light`
- `no` only for `skip_candidate`

## Search Rules

`full` search：

- 先直接打開 token row 提供的 `cg_url` / `cmc_url` canonical page
- 確認 token identity
- 確認 project identity
- 確認 issuer / foundation / operator / legal entity
- 只在 evidence 可支持其為 responsible entity 時才記錄
- 優先官方 sources，但可用可靠 secondary sources 做 corroboration

`light` search：

- 先直接打開 token row 提供的 `cg_url` / `cmc_url` canonical page
- 查官方站、docs、foundation、issuer 頁
- 若發現 plausible responsible-entity signal，立刻升級為 `full`

`skip_candidate`：

- 只用於明顯噪音、重複、無法 justify company search 的 row

## CSV Write Rules

- 不可直接手改 CSV 文字
- 不可用 shell `echo` / heredoc 直接拼接 CSV 行
- classifier/result row 都必須先整理成 JSON object
- 再用 `python3 part4_analyse_token_to_company/scripts/part4_safe_csv_append.py` 寫入對應 CSV
- 一律帶 `--tasks-file`，讓 immutable identity fields 以 `tasks.jsonl` 為準
- 若 wrapper 提供 `attempt_metadata.json`，一律同時帶 `--attempt-metadata`，避免 recovery attempt 覆寫已保留 prefix rows
- 預設用 `--upsert-key task_index`

Canonical token page rule：

- 如果 row 有 `cg_url`，不可跳過 CoinGecko slug page
- 如果 row 有 `cmc_url`，不可跳過 CoinMarketCap slug page
- 如果 2 個都存在，必須兩個都訪問，不能只看其中一個
- 不可只用搜尋引擎摘要或二手站替代這些 canonical token pages

## Result Header

```csv
task_index,canonical_slug,token_symbol,token_name,token_origin_type,entity_link_likelihood,entity_search_required,entity_search_reason,project_name,project_url,mapped_entity_name,mapped_entity_legal_name,mapped_entity_type,mapped_entity_url,mapped_entity_country,entity_relation_type,status,completed_at,has_entity_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review
```

規則：

- `task_index`、`canonical_slug`、`token_symbol`、`token_name` 是 immutable identity fields
- `status` 必須是 `completed`
- `project_name` / `project_url` / `mapped_entity_*` / `entity_relation_type` 必須是 JSON list string
- `evidence_urls` 必須是 `|` 分隔的絕對 HTTP(S) URL
- `evidence_source_types` 必須是 `|` 分隔的小寫 labels
- `has_entity_evidence` 不能空白
- `confidence` 只能是 `high` / `medium` / `low`
- `needs_manual_review` 只能是 `yes` / `no`

若找不到可穩定映射的 entity：

- `mapped_entity_name = []`
- 其他 mapped entity list 欄位也設為 `[]`
- `entity_search_reason` 要明確說明為何沒有可靠 entity mapping

Allowed `mapped_entity_type`：

- `company`
- `foundation`
- `issuer`
- `association`
- `trust`
- `dao_legal_wrapper`
- `nonprofit`
- `government_entity`
- `other_legal_entity`
- `unclear`

## Verifier Header

```csv
task_index,canonical_slug,token_symbol,token_name,classifier_search_tier,worker_mapped_entity_name,verifier_search_tier,verifier_mapped_entity_name,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

Verifier 必須重點檢查：

- worker 是否漏掉 entity
- worker 是否多報 entity
- project mapping 是否錯
- entity mapping 是否錯
- `skip_candidate` 是否太保守

## Runtime Rules

- batch-local `classifier_results.csv` / `results.csv` 只是中間產物
- merge authority 在 `agent_runs/token_company/`
- 若要長時間無人值守，必須用 `scripts/6_start_long_running_supervisor.py --scheduler-mode queue`
- 長跑狀態查詢用 `scripts/7_check_longrun_status.py`
- 所有 runtime-side `schedule.csv` 寫入都必須走 `scripts/part4_schedule_io.py`
