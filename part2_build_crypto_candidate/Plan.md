# `1_find_crypto_company_and_investor.py` 實作計畫

## Summary

在 `part2_build_crypto_candidate/` 中拆成兩個腳本，參考 `part1_summarize_crypto_keyword_hits` 的風格與資料流，完成兩個階段：

1. `1_find_crypto_company_and_investor.py`
   先把指定 relation 表中的 `*Verticals` 與 `*Description` 類欄位聚合回對應主表，生成：
   - `company_new.csv`
   - `investor_new.csv`
2. `2_filter_crypto_company_and_investor.py`
   再在這兩份 `_new.csv` 的指定欄位中搜尋關鍵詞，提取所有命中主體，生成：
   - `crypto_company.csv`
   - `crypto_investor.csv`

關鍵詞固定使用程式內的常量 list，不做 CLI 參數化。預設常量為：
- `"crypto"`
- `"blockchain"`
- `"web3"`

匹配規則固定為：
- 忽略大小寫
- 子字串命中即可
- 任一指定欄位命中即保留整列

## Relation 聚合設計

### Company 主表

主表來源：
- `data/Company.csv`

要聚合回 `Company.csv` 的 relation 表與欄位：

1. `data/CompanyVerticalRelation.csv`
- key: `CompanyID`
- source column: `Vertical`
- target new column: `Relation_Verticals`

2. `data/CompanySimilarRelation.csv`
- key: `CompanyID`
- source column: `SimilarVerticals`
- target new column: `Relation_SimilarVerticals`

3. `data/CompanySimilarRelation.csv`
- key: `CompanyID`
- source column: `SimilarDescription`
- target new column: `Relation_SimilarDescriptions`

4. `data/CompanyCompetitorRelation.csv`
- key: `CompanyID`
- source column: `CompetitorVerticals`
- target new column: `Relation_CompetitorVerticals`

5. `data/CompanyCompetitorRelation.csv`
- key: `CompanyID`
- source column: `CompetitorDescription`
- target new column: `Relation_CompetitorDescriptions`

聚合規則：
- 以 `CompanyID` 為唯一 key
- 空值跳過
- 同一主體同一來源欄位的值去重
- 保留首次出現順序
- 多值以 ` | ` 串接成單一欄位字串

生成的 `company_new.csv` 會保留 `Company.csv` 所有原始欄位，並新增以上 5 個 relation 聚合欄位。

### Investor 主表

主表來源：
- `data/Investor.csv`

這版不聚合 investor relation 表回主表，原因是資料集中不存在與 `CompanyVerticalRelation` / `CompanySimilarRelation` / `CompanyCompetitorRelation` 對稱的 investor relation 表，可穩定提供 `PreferredVerticals`、`Description` 類補充欄位。

因此：
- `investor_new.csv` 保留 `Investor.csv` 全部原始欄位
- 不新增 relation 聚合欄位

## 關鍵詞搜尋設計

### 關鍵詞常量

腳本內使用一個常量 list，例如：

```python
KEYWORDS = ["crypto", "blockchain", "web3"]
```

處理規則：
- 啟動時統一轉小寫
- 去重
- 後續只從這個常量讀取關鍵詞
- 不提供 `--keywords` CLI 參數

### 搜尋欄位

`company_new.csv` 中要搜尋的欄位：
- `Verticals`
- `Description`
- `Keywords`
- `Relation_Verticals`
- `Relation_SimilarVerticals`
- `Relation_SimilarDescriptions`
- `Relation_CompetitorVerticals`
- `Relation_CompetitorDescriptions`

`investor_new.csv` 中要搜尋的欄位：
- `PreferredVerticals`
- `Description`

### 命中規則

- 任一指定欄位命中任一關鍵詞，即該主體命中
- 同一列即使多欄、多關鍵詞同時命中，也只輸出一次
- 結果表額外新增：
  - `MatchedKeywords`
  - `MatchedColumns`

欄位內容規則：
- `MatchedKeywords`: 命中的唯一關鍵詞，以 `|` 串接
- `MatchedColumns`: 命中的欄位名，以 `|` 串接

## 輸出內容

兩個腳本共用輸出目錄：
- `part2_build_crypto_candidate/output/`

輸出 4 個 CSV：

1. `part2_build_crypto_candidate/output/company_new.csv`
- 內容：`Company.csv` 全部原始欄位
- 加上：
  - `Relation_Verticals`
  - `Relation_SimilarVerticals`
  - `Relation_SimilarDescriptions`
  - `Relation_CompetitorVerticals`
  - `Relation_CompetitorDescriptions`

2. `part2_build_crypto_candidate/output/investor_new.csv`
- 內容：`Investor.csv` 全部原始欄位
- 不新增 relation 聚合欄位

3. `part2_build_crypto_candidate/output/crypto_company.csv`
- 內容：`company_new.csv` 的全部欄位
- 外加：
  - `MatchedKeywords`
  - `MatchedColumns`

4. `part2_build_crypto_candidate/output/crypto_investor.csv`
- 內容：`investor_new.csv` 的全部欄位
- 外加：
  - `MatchedKeywords`
  - `MatchedColumns`

## Implementation Notes

- 兩個腳本都採 `csv.DictReader` / `csv.DictWriter`，保持與 `part1` 一致
- `1_find_crypto_company_and_investor.py`
  - 只負責 merge，不做關鍵詞篩選
  - 讀 `data/` 與指定 relation 表，生成 `company_new.csv`、`investor_new.csv`
- `2_filter_crypto_company_and_investor.py`
  - 只負責讀 `output/` 下的 `_new.csv`
  - 生成 `crypto_company.csv`、`crypto_investor.csv`
- 路徑風格沿用 `part1`：
  - `SCRIPT_DIR = Path(__file__).resolve().parent`
  - `--data-dir`
  - `--output-dir`
- 不提供 `--keywords` 參數，關鍵詞只從 `KEYWORDS` 常量讀取
- 執行過程打印 log，至少包括：
  - 正在讀哪個主表
  - 正在聚合哪個 relation 表
  - 每個 relation 表聚合完成後影響的主體數
  - `_new.csv` 寫出完成
  - 關鍵詞搜尋完成與命中列數
- 若主表、relation 表或必要欄位不存在，直接報錯退出，不做靜默跳過

## Assumptions

- 這版的核心目標是建立可直接搜尋的候選主表，不做更進一步的 AI 判斷
- `Investor` 僅依靠主表欄位搜尋，是因為 schema 中沒有與 `Company` 對稱的 relation 補充表可安全聚合
- 關鍵詞雖然預設為 `crypto`, `blockchain`, `web3`，但實作上以單一常量 list 管理，方便後續直接修改
