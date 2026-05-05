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
12. former name / rebrand continuity、token family sweep、secondary-only token linkage 是固定補查步驟，不可略過。
13. Worker 寫出的 batch-local `classifier_results.csv` / `results.csv` 只是中間產物，不是最終交付。
14. 通過 verifier / collector 驗證後，完成搜索的 rows 必須被匯入 `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`。
15. 所有 `needs_manual_review = yes` 的 rows 必須被匯入 `part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`。
16. 若使用者要求長時間無人值守地連續跑多個 batch window，主協調端應使用 `part5_analyse_company_to_token/scripts/6_start_long_running_supervisor.py` 啟動 detached supervisor，而不是手動逐輪串 `prepare -> launch -> mark-started -> watch`。
17. detached longrun 預設必須優先使用 `systemd-run --user` 啟動 supervisor；只有在 `systemd-run` 失敗時才 fallback 到 `nohup` 加新 session。當前 backlog 主路徑應優先使用 `--scheduler-mode queue` 啟動 `5_run_queue_supervisor.py`；`5_run_round_supervisor.py` 僅保留給 round-mode fallback 或前景阻塞式 round run。
18. longrun launcher 與 supervisor 必須把解析好的絕對 `codex` binary path 顯式傳入 worker launch，不要依賴 systemd service 的 PATH 來找到 `codex`。
19. 長跑模式會根據使用者指定的 batch-dir 或從 `agent_runs/crypto_company/results.csv` 找出下一個未完成 batch window，建立 run metadata，並將 `run_dir`、`pid`、`unit_name`、scheduler mode 與啟動參數寫入 `part5_analyse_company_to_token/agent_runs/crypto_company_longrun_latest.json`。
20. 當前 backlog 長跑的標準 execution path 是 queue-mode：batch-scoped prepare、持續 fill slots、serialized batch-scoped collect。round 仍保留在 `schedule.csv` 中做 grouping/reporting，但 queue-mode 不以 round barrier 決定何時啟下一個 batch。
21. queue-mode 的 `--max-workers` 代表 live worker process budget，不保證永遠等於同時處理的 batch 數。若某個 batch 進入 split recovery，它可能同時佔用多個 worker process。
22. 若使用者要求「檢查 longrun 狀態」或任何等價的長跑進度查詢，主協調端應優先執行 `part5_analyse_company_to_token/scripts/7_check_longrun_status.py`，用它來讀取 `crypto_company_longrun_latest.json`、`supervisor_state.json`、`schedule.csv` 與近期事件，而不是手動拼接多個檔案查詢。
23. 長跑狀態查詢時，若 `crypto_company_longrun_latest.json` 含有 `unit_name`，必須先查 `systemctl --user` 的 unit 狀態，再補 heartbeat 與 host-process 掃描；只有在 systemd 狀態不可用時，才退回到 heartbeat 與 `ps -ef | grep part5`。
24. 長跑狀態查詢的標準回報至少要包含：`status`、`phase`、`active_workers`、`round_summaries`。若當前 scheduler 是 queue mode，還應補 `slots`、`waiting_queue`、`tail_retry_queue`、`collect_queue`、`deferred_queue`。
25. 若 `7_check_longrun_status.py` 發現 `supervisor` 已不可見、`active_workers=0`，但只有 worker log heartbeat 還在跳，應將其視為 `orphaned_worker_activity`，而不是健康的 running supervisor。
26. 長跑 supervisor 的主路徑預設對每個 batch 套用 2 小時 wall-clock 上限，但 queue-mode 的 long-tail 規則是兩段式，不是第一次 timeout 就直接終態 defer。
27. 第一次 long-tail timeout 時，主協調端必須終止該 batch 的 active workers、保留當前 partial prefix，並把它停放為：
    - `status = needs_rerun`
    - `queue_state = tail_retry_pending`
    - `tail_retry_pending = yes`
    - `tail_retry_count += 1`
28. `tail_retry_pending` batch 不得插回 primary waiting queue。只有在 ordinary `waiting_queue` 與 `collect_queue` 都清空後，才允許它做那次唯一的 tail retry。
29. 目前政策 `max_tail_retries = 1`。同一個 batch 若在 parked tail retry 後再次超時，才正式標記為 terminal `deferred_long_tail`，寫入 `part5_analyse_company_to_token/agent_runs/crypto_company/long_tail_batches_pending.csv`。
30. terminal `deferred_long_tail` 代表「這個 batch 在本次主 longrun 內仍未完成，需要之後單獨 rerun」，不是「已完成研究」。在最終總結裡，主協調端必須明確列出這些未完成 batch。
31. queue-mode collect 是 batch-scoped 且 serialized。已完成 batch 可以先 lint/collect 並匯入全域 final outputs，不必等待同 round 其他 batch；但 terminal `deferred_long_tail` batch 必須排除在 collect scope 外。
32. 所有 runtime-side `schedule.csv` 寫入都必須走 `part5_analyse_company_to_token/scripts/part5_schedule_io.py` 的 locked atomic write 路徑，不得直接用裸 `open(..., "w")` 重寫 live schedule。
33. 中間 run 目錄可能會在匯入全域最終結果後刪除，所以 row schema、identity fields、evidence 欄位必須一次寫對，不能依賴本地 attempt 目錄長期保存。

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

`company_type` 只能使用以下 allowed values：

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

不要自創更細的 taxonomy，例如 `defi_protocol`、`nft_marketplace`、`gaming_platform`、`crypto_brokerage_platform`。這些都必須折疊回 allowed values。

設 `search_tier = full` 的情況：

- 公司經營 protocol、network、dapp、exchange、wallet、tokenized product 或 blockchain-native product。
- row 中提到 project、token、whitepaper、docs、protocol、chain、app、DAO、ecosystem。
- gaming / NFT row 只要出現 explicit token language，例如 token、ticker、airdrop、staking、battle pass、reward token、governance token、season pass token，就不要設為 `skip_candidate`。
- 公司名稱、alias、former name、legal name 或 website 暗示 project identity 可能不同於公司法定名稱。
- 你無法高置信度排除 project/token 可能性。

設 `search_tier = light` 的情況：

- 公司 crypto-adjacent 或低可能性，但仍有 enough signal 做 cheap token-existence check。
- service provider、infrastructure、media、mining、validator、custody、analytics、security、compliance、NFT、gaming、investment 類公司有一些 crypto/project context。
- 官方 domain、alias、former name 或 description 有 token/project-like terms，但不足以 justify full search。
- source context 薄、模糊、可能過時。
- 公司雖然更偏 infrastructure / validator / node / relayer / builder / MEV tooling，但已明確是 crypto-native product 或 protocol-facing operations。

只有在明顯不相關時才設 `search_tier = skip_candidate`，例如：

- 傳統公司，只因弱 crypto keyword 被抽中。
- consulting、legal、accounting、recruitment、marketing、event、generic service provider，且沒有 owned project signal。
- investor、holding company、VC、accelerator，且沒有 owned crypto project signal。
- media、education、research company，且沒有 owned crypto project signal。
- mining、validator、custody、analytics、security、compliance company，且沒有 owned token/project signal。
- NFT-only / collectible-only / gaming asset company，且沒有 fungible token signal。

`skip_candidate` hard stop：

- 若 row 內有 explicit token language，不可設為 `skip_candidate`。
- 若 current brand / domain 與 project identity 不穩、former name 影響 mapping、或存在 token rename / migration signal，不可設為 `skip_candidate`。
- 若是 blockchain / NFT gaming company 且有 live ecosystem / reward / tokenized engagement 語言，至少設為 `light`，通常應設為 `full`。
- 若是 crypto-native infrastructure / validator / node / relayer / builder / MEV / rollup / chain tooling 公司，且官網或 docs 顯示它在運營鏈上產品或 protocol-facing infra，不可設為 `skip_candidate`；至少設為 `light`。

`project_search_required = yes` 用於 `full` 或 `light`。

`project_search_required = no` 只用於 `skip_candidate`。

`risk_flags` 必須是 JSON list string，例如 `["alias_or_former_name","token_keyword"]`。沒有 risk flag 時寫 `[]`。

優先使用的 `risk_flags` 例子：

- `alias_or_former_name`
- `token_keyword`
- `protocol_keyword`
- `nft_or_gaming`
- `brand_project_mismatch`
- `live_site_conflict`
- `token_migration`
- `legacy_ticker_conflict`

保守規則：

- 不確定時，設 `search_tier = full`。
- token budget 有壓力但不能排除 project/token relevance 時，用 `light`，不要用 `skip_candidate`。
- `skip_candidate` 必須能用 `classifier_reason` 清楚解釋。

## Stage 2: Search Rules

Worker identity rules:

- 只讀取自己被分配的 `tasks.jsonl` / batch JSONL。
- `task_index`、`company_id`、`company_name`、`normalized_domain` 是 immutable identity fields。
- 這 4 個欄位必須逐字沿用 input/task row，不可依據 live site、docs、alias、former name、brand、project 名稱或 token page 改寫。
- 若研究發現 live identity 與 input row 不一致，應把衝突寫進 evidence / risk flags / manual review 判斷，而不是改 immutable identity 欄位。
- 輸出前必須逐行對照 `tasks.jsonl`，確認 row order 與 immutable identity fields 完全一致。

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
- 如果發現 plausible token / project signal，必須在同一輪升級為 full search。
- 不要把 `needs_manual_review = yes` 當成 full search 的替代品。
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
- 若任何 probe 出現 plausible company -> project -> token signal，必須升級為 `full`。
- 若 probe 顯示 gaming / NFT row 有 live tokenized ecosystem 語言，不可維持 `skip_candidate` 或低置信 no-token 結論。
- Light tier 的目的只是快速排除低機率 row，不是憑感覺結案。
- 若 official docs、FAQ、reward pages、staking pages、tokenomics pages、或 protocol docs 已出現 fungible token / rewards / staking / governance 語言，light-tier no-token 結論只算 provisional，必須升級為 `full`。

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
- 若 company / project / token 三段任一段 mapping 在補查後仍不穩，設 `needs_manual_review = yes`。
- 若 current official docs 與 older official launch materials 在 ticker naming 上衝突，優先 current official docs 的 active ticker；older ticker 視為 legacy naming，不當作主 ticker 輸出。
- 遇到 token rename / migration / legacy ticker conflict 時，加入對應 `risk_flags`；若 current official ticker 加上一個 current corroborating source 已足夠穩定，可 `needs_manual_review = no`。
- 若 live site identity 與 dataset description、former name、brand、project 名稱發生衝突，加入 `brand_project_mismatch` 或 `live_site_conflict`；只有在補查後仍不能穩定解釋時才保留 `needs_manual_review = yes`。

### Mandatory High-Frequency Follow-Up Rules

以下三類是 verifier 高頻抓到的漏查，現在視為固定規則，不可跳過：

1. `former-name continuity sweep`
   - 在任何 `skip_candidate`、light-tier no-token、或 searched no-token 結論前，必查 `CompanyFormerName`、主要 alias、rebrand 名稱。
   - 若 former name / rebrand 指向已發幣 project，不可直接結案為 no-token。
   - 若 current brand 與 legacy token naming 衝突，優先 current active ticker，legacy ticker 當作 lineage evidence。

2. `token-family sweep`
   - 只要 row 或官方材料出現 governance、staking、wrapper、liquid-staked、bridge、reward token、protocol rewards、tokenomics、airdrop points conversion 這類語言，必查是否存在多個 fungible tokens。
   - 不可因為已找到第一個 ticker 就停止；必須確認是否還有同一 project/token family 下的其他 fungible ticker。

3. `secondary-only linkage sweep`
   - 若 token 只出現在 CoinGecko、CoinMarketCap、explorer、Blockspot、CoinStats、secondary article 等 secondary token pages，而 official company/project mapping 不夠穩，必再做一次 company -> project linkage pass。
   - 補查後若仍只有 secondary-only mapping：
     - 可以保留 token，但通常應 `needs_manual_review = yes`
     - 或保留 `token_ticker = []`
   - 不可把 secondary-only token page 當成 clean high-confidence positive row。

### Resolution Pass Before Manual Review

除非遇到明確 blocker，否則在把 row 設為 `needs_manual_review = yes` 之前，必做一次補查：

1. `current-official pass`
   - 補查 current official site、docs、blog、FAQ、announcement、foundation page、GitHub、explorer。
   - 優先確認 current brand、current project name、current active ticker。
2. `identity-resolution pass`
   - 用 alias、former name、legal name、parent / subsidiary / acquired brand 再查一次。
   - 目標是解開 rebrand、brand/domain mismatch、legacy project naming。
3. `token-data corroboration pass`
   - 用已確認的 project 名稱做 exact CoinGecko / CoinMarketCap / explorer / exchange / docs page corroboration。
   - 如果 row 是 no-token 候選，確認是否只是 tokenized asset / rewards language，而不是 company-owned fungible token。
4. `negative-resolution pass`
   - 對 no-token row，至少確認 current official materials 沒有明示 fungible token，且 major token-page exact probe 沒有穩定映射。

只有在補查後仍存在未解決的 mapping ambiguity、ticker conflict、owned-project uncertainty、或 evidence gap，才設 `needs_manual_review = yes`。

補查後通常可直接設 `needs_manual_review = no` 的情況：

- full search + 補查後仍找不到 company-owned fungible token，即使公司帶有 web3 / tokenized assets / gaming / NFT 語言。
- current official docs 已明確解決 rename / migration，且至少有一個 current corroborating source 支持 active ticker。
- brand / domain mismatch 可用 rebrand、former name、acquisition、subsidiary 關係穩定解釋。
- official site 很薄，但 current docs / foundation / explorer / token data page 足以穩定完成 mapping。
- 平台發行的是 tokenized assets、points、rewards units、NFT collection，而不是 company-owned fungible token。

補查後通常仍需 `needs_manual_review = yes` 的情況：

- former name / rebrand 能找到 token，但 current active ticker 仍衝突。
- token family 中至少一個 ticker 只靠 thin secondary evidence。
- official site 與 token pages 對主體公司 / foundation / token issuer 的 identity 仍對不起來。

推薦來源順序：

1. 官方網站、docs、whitepaper、litepaper、blog、FAQ、governance forum、announcement。
2. CoinGecko、CoinMarketCap 或類似 token data pages。
3. Project docs、GitHub、explorer、exchange pages、audit docs、foundation pages。
4. 用可靠 secondary sources 幫助 disambiguation。

不能單獨作為 token evidence：

- 搜索結果 snippet。
- 沒有強證據補充的社交媒體貼文。
- 無 company/project mapping 的 token list。
- 只有 legacy / archived / old launch material、但缺少 current official corroboration 的 token naming。
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

- `task_index`: 直接沿用 input/task row，不可重排、重編或借用其他 task。
- `company_id`: 直接沿用 PitchBook `CompanyID`；不可因為查到 foundation、DAO、token issuer、parent/subsidiary 或其他關聯實體就改寫。
- `company_name`: 直接沿用 input/task row；研究可用 alias / former name / project brand 輔助判斷，但不可把輸出主體改成其他名稱。
- `normalized_domain`: 直接沿用 input/task row；不可改成 token site、docs host、campaign domain、app domain 或其他 secondary host。
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
- `evidence_urls`: 多個 URL 用 `|` 分隔，且必須是絕對 `http://` 或 `https://` URL。
- `evidence_source_types`: 多個來源類型用 `|` 分隔，例如 `official_site|official_docs|coingecko|coinmarketcap|whitepaper|docs|explorer|exchange|secondary_source`。
- `confidence`: `high` / `medium` / `low`。
- `needs_manual_review`: `yes` / `no`。
- `risk_flags` 在 classifier CSV 中必須是 JSON list string，例如 `["alias_or_former_name","token_keyword"]`；不可寫 `none`、`former_name`、`a|b`。

`confidence` 與 `needs_manual_review` 必須分開判斷：

- `high`: 公司 / project / token mapping 清楚，且有官方或強 primary evidence。
- `medium`: 證據足以合併結果，但不如 `high` 完整。
- `low`: 證據偏弱、偏薄，或覆蓋不足。
- `confidence` 只能是 `high` / `medium` / `low`，不可寫 `0.92`、`high?`、`med` 之類非 enum 值。
- 不可只因為 `confidence` 不是 `high`，就把 `needs_manual_review` 設為 `yes`。
- 若 mapping 穩定、沒有 source conflict、verifier 也接受，`medium` confidence 可以是 `needs_manual_review = no`。
- 若 token-positive row 主要依賴 secondary source 或 legacy material，必須再補 current official corroboration；補不到時可以保留 token，但 `needs_manual_review = yes`。
- 若 no-token row 已完成 full search + resolution pass，且沒有 plausible owned fungible token 殘留，`low` confidence 也可以是 `needs_manual_review = no`。
- `has_token_evidence` 不可留空。對 searched rows，不可只寫 bare `yes` 或 `no`，要簡短說明 positive 或 negative finding。
- 若 `project_search_required = yes`，`evidence_urls` 與 `evidence_source_types` 都必須非空。
- 若 `token_ticker != []`，`evidence_urls` 與 `evidence_source_types` 都必須足以支撐 company/project -> token mapping。

CSV 安全規則：

- JSON list 欄位必須是合法 JSON list。
- 欄位含逗號、換行或雙引號時，必須按標準 CSV 規則加雙引號並轉義。
- 不可改寫 immutable identity 欄位；identity conflict 應進 evidence、risk flags、project_search_reason 或 `needs_manual_review`，而不是改 `company_id`、`company_name`、`normalized_domain`。
- 不要輸出 `CompanyID`、`CompanyName`、`has_token`、`raw_output` 這些舊欄位。
- 不要輸出 Markdown，不要輸出解釋段落，只輸出 CSV。

## Manual Review Rules

以下情況在完成 resolution pass 後仍存在時，才設 `needs_manual_review = yes`：

- classifier 不確定但仍跳過 project search。
- company-to-project mapping 模糊。
- token page 存在，但不能清楚映射回公司或 owned project。
- sources disagree。
- current official docs 與 older official token materials / launch materials 對 ticker naming 不一致。
- live site identity 與 dataset description、former name、brand、project 名稱不一致。
- official site dead / unavailable / too thin。
- 公司有多品牌、former name、subsidiary、foundation、DAO，可能影響 mapping。
- NFT-only 或 gaming 相關，但可能同時存在 fungible token。
- worker 不能高置信度判斷是否漏報或多報 token。

不要只因為 `confidence = medium` 或 `low` 就設 `needs_manual_review = yes`。

以下情況通常不需要 `needs_manual_review = yes`：

- 已做 full search + resolution pass，結論是沒有 company-owned fungible token。
- only issue 是公司帶有 web3 / tokenized assets / gaming / NFT 語言，但沒有可靠 ticker。
- former name、alias、brand/domain mismatch 已被 current sources 穩定解開。
- rename / migration case 已能用 current official ticker + current corroboration 穩定定案。

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
