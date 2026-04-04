# PitchBook Crypto / Blockchain 判斷框架

## 1. 資料本質

這批 PitchBook 數據本質上是一套私募市場與成長型企業生態的實體-關係型商業資料庫，不是單一表，也不是單純財報或新聞資料。

核心主表有 7 類：

- `Company.csv`
- `Deal.csv`
- `Investor.csv`
- `Fund.csv`
- `LimitedPartner.csv`
- `Person.csv`
- `ServiceProvider.csv`

大量 relation 表再把這些主體連成一張市場網路。

---

## 2. 本輪結論

基於以下輸出檔：

- [ranking_by_file.csv](crypto_keyword_hit_rankings/ranking_by_file.csv)
- [ranking_by_column.csv](crypto_keyword_hit_rankings/ranking_by_column.csv)
- [ranking_by_file_column.csv](crypto_keyword_hit_rankings/ranking_by_file_column.csv)
- [crypto_blockchain_keyword_hits.csv](crypto_blockchain_keyword_hits.csv)

可以得到三個直接結論：

1. 能用來判斷主表元素是否與 crypto / blockchain 相關的欄位，主要集中在：
   - `Verticals` 類
   - `Description / Synopsis / Keywords` 類
   - 少量 `EmergingSpaces`
   - 少量 `PreferredVerticals`
2. `Name` / `Website` 類欄位命中很多，但噪音高，不應作主證據。
3. 最有價值的 relation 表集中在 `Company` 周邊，因為它們既有主題語義，也能接回主表。

---

## 3. 判斷優先順序

### 強信號

- `Verticals`
- `PreferredVerticals`
- `Description`
- `Keywords`
- `DealSynopsis`
- `EmergingSpaces`

這些欄位的命中值常直接包含：

- `Cryptocurrency/Blockchain`
- `uses blockchain`
- `cryptocurrency exchange`
- `crypto fund`
- `blockchain technology platform`

### 中信號

- `SimilarVerticals`
- `SimilarDescription`
- `CompetitorVerticals`
- `CompetitorDescription`

這些主要來自 relation 表，適合擴張候選池。

### 弱信號

- 各類 `*Name`
- 各類 `*Website`
- `Biography`
- `CEOBiography`

Ben 注記：所有 `Name / Website` 相關欄位原則上不作主判斷依據。

---

## 4. 主表中最值得看的欄位

### 4.1 Company

主表：[Company.csv](data/Company.csv)

優先欄位：

- `Verticals`
- `Description`
- `Keywords`
- `EmergingSpaces`

原因：

- `Verticals` 命中最強，常直接出現 `Cryptocurrency/Blockchain`
- `Description` / `Keywords` 常直接寫出 `bitcoin`, `cryptocurrency exchange`, `blockchain`
- `EmergingSpaces` 可補抓 `Blockchain Gaming`, `Blockchain Real Estate`, `NFTs`

結論：

`Company` 是判斷 crypto / blockchain 相關組織的第一入口。

### 4.2 Investor

主表：[Investor.csv](data/Investor.csv)

優先欄位：

- `PreferredVerticals`
- `Description`

原因：

- `PreferredVerticals` 直接反映投資偏好
- `Description` 會寫出 `invest in blockchain`, `focus on crypto`

結論：

適合判斷 `InvestorID` 是否偏 crypto 投資，但不如 `Company` 穩。

### 4.3 Deal

主表：[Deal.csv](data/Deal.csv)

優先欄位：

- `DealSynopsis`

原因：

- 可直接命中 `crypto fund`, `blockchain accelerator` 等事件描述

結論：

適合判斷 `DealID` 是否與 crypto / blockchain 事件相關，但它是交易信號，不是主體定義。

### 4.4 Fund

主表：[Fund.csv](data/Fund.csv)

優先欄位：

- `PreferredVerticals`

補充欄位：

- `FundName`

結論：

`PreferredVerticals` 有用；`FundName` 只作輔助。

### 4.5 Person

主表：[Person.csv](data/Person.csv)

可用欄位：

- `PrimaryCompanyVerticals`
- `Biography`

結論：

只能作 proxy。它更多反映人物所屬組織是否偏 crypto，而不是人物本身是否可定義為 crypto 主體。

---

## 5. Relation 表中最有價值的欄位

### 5.1 可接回 Company 的 relation

#### CompanyVerticalRelation

表：[CompanyVerticalRelation.csv](data/CompanyVerticalRelation.csv)

可用欄位：

- `Vertical`

連接方式：

- `CompanyID -> Company.CompanyID`

作用：

幾乎是 `Company.csv.Verticals` 的正規化版本，信號很強。

#### CompanySimilarRelation

表：[CompanySimilarRelation.csv](data/CompanySimilarRelation.csv)

可用欄位：

- `SimilarVerticals`
- `SimilarDescription`
- `SimilarCompanyName`

連接方式：

- `CompanyID` 連回來源公司
- `SimilarCompanyID` 連回相似公司

作用：

可從已知 crypto 公司向外擴張相似公司候選池。

#### CompanyCompetitorRelation

表：[CompanyCompetitorRelation.csv](data/CompanyCompetitorRelation.csv)

可用欄位：

- `CompetitorVerticals`
- `CompetitorDescription`
- `CompetitorName`

連接方式：

- `CompanyID` 連回來源公司
- `CompetitorID` 連回競爭對手公司

作用：

適合擴展 crypto company 鄰域。

### 5.2 可接回 Investor / Fund 的 relation

#### CompanyInvestorRelation

表：[CompanyInvestorRelation.csv](data/CompanyInvestorRelation.csv)

可用欄位：

- `InvestorName`
- `InvestorWebsite`

連接方式：

- `CompanyID -> Company`
- `InvestorID -> Investor`

作用：

可補充辨識某 crypto 公司背後的投資人，但只適合作輔助。

#### DealInvestorRelation

表：[DealInvestorRelation.csv](data/DealInvestorRelation.csv)

可用欄位：

- `InvestorName`
- `InvestorWebsite`
- `InvestorFundName`

連接方式：

- `DealID -> Deal`
- `InvestorID -> Investor`
- `InvestorFundID -> Fund`

作用：

適合把 crypto 交易事件接回投資人與基金，但名稱欄位仍只是弱信號。

#### InvestorInvestmentRelation

表：[InvestorInvestmentRelation.csv](data/InvestorInvestmentRelation.csv)

可用欄位：

- `CompanyName`

連接方式：

- `InvestorID -> Investor`
- `CompanyID -> Company`
- `DealID -> Deal`

作用：

可看 investor 是否反覆投到 crypto 命名公司，但單看 `CompanyName` 不夠穩。

### 5.3 可接回 Person 的 relation

#### PersonPositionRelation

表：[PersonPositionRelation.csv](data/PersonPositionRelation.csv)

可用欄位：

- `EntityName`

連接方式：

- `PersonID -> Person`
- `EntityID` 為 polymorphic key，不對應單一固定主表

作用：

能補充發現 crypto 組織名稱，但不適合做嚴格主判斷。

---

## 6. 最值得用的欄位清單

### 主表優先

- [Company.csv](data/Company.csv) `Verticals`
- [Company.csv](data/Company.csv) `Description`
- [Company.csv](data/Company.csv) `Keywords`
- [Company.csv](data/Company.csv) `EmergingSpaces`
- [Investor.csv](data/Investor.csv) `PreferredVerticals`
- [Investor.csv](data/Investor.csv) `Description`
- [Deal.csv](data/Deal.csv) `DealSynopsis`
- [Fund.csv](data/Fund.csv) `PreferredVerticals`

### Relation 表優先

- [CompanyVerticalRelation.csv](data/CompanyVerticalRelation.csv) `Vertical`
- [CompanySimilarRelation.csv](data/CompanySimilarRelation.csv) `SimilarVerticals`
- [CompanySimilarRelation.csv](data/CompanySimilarRelation.csv) `SimilarDescription`
- [CompanyCompetitorRelation.csv](data/CompanyCompetitorRelation.csv) `CompetitorVerticals`
- [CompanyCompetitorRelation.csv](data/CompanyCompetitorRelation.csv) `CompetitorDescription`

### 只作輔助

- 各類 `*Name`
- 各類 `*Website`
- [Person.csv](data/Person.csv) `Biography`
- [Deal.csv](data/Deal.csv) `CEOBiography`

---

## 7. 最小可行策略

如果只保留最有用、最穩的框架，可以簡化成兩類主表：

- `Company`
- `Investor`

優先檢查欄位：

- `*Verticals`
  - `Verticals`
  - `PreferredVerticals`
  - `SimilarVerticals`
  - `CompetitorVerticals`
- `*Description`
  - `Description`
  - `SimilarDescription`
  - `CompetitorDescription`
- `Keywords`
- `EmergingSpaces`
- `DealSynopsis`

判斷順序：

1. 先看主表自己的 `Verticals / PreferredVerticals / Description / Keywords / EmergingSpaces`
2. 再看 `Company` 周邊 relation 表的 `Vertical / SimilarVerticals / SimilarDescription / CompetitorVerticals / CompetitorDescription`
3. 最後才用 `Name / Website / Biography` 類欄位補抓候選

一句話總結：

最強信號是 `Verticals` 與 `Description`，最有用的 relation 表集中在 `Company` 周邊，`Name / Website` 只能作輔助，不宜當主證據。
