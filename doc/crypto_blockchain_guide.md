# Crypto / Blockchain 主題導讀

本文件說明如果要在這批 PitchBook 資料中定位與 `crypto`、`blockchain`、`web3` 相關的項目，應該從哪些表開始、優先看哪些欄位，以及後續如何沿著關聯表擴展到交易、投資機構、基金與服務機構。

## 核心結論

- 第一入口應該是 `Company.csv`，先建立一批疑似 crypto / blockchain 公司。
- 第二步接 `Deal.csv` 與 `DealInvestorRelation.csv`，看這些公司有哪些交易、由誰投資。
- 第三步接 `Investor.csv`、`InvestorInvestmentRelation.csv`、`Fund.csv`、`FundInvestmentRelation.csv`，辨識長期活躍於 crypto / blockchain 的投資方與基金。
- 若要補產業生態圈，再看 `ServiceProvider.csv` 與 `DealServiceProviderRelation.csv`。

## 建議入手順序

### 1. 先找公司種子集合

最重要的主表是：

- `Company.csv`
- `CompanyIndustryRelation.csv`
- `CompanyVerticalRelation.csv`
- `CompanySimilarRelation.csv`

其中最關鍵的是 `Company.csv`，因為它同時有產業分類欄位與自由文字欄位。

### 2. 用交易表擴展主題上下文

當你已經有一批疑似 crypto / blockchain 公司後，再看：

- `Deal.csv`
- `DealInvestorRelation.csv`

這兩張表可以回答：

- 這些公司有哪些融資、併購或退出事件
- 哪些 investor / fund 真的參與過這些公司
- 哪些 investor 是 lead investor

### 3. 再辨識投資方與基金

接下來看：

- `Investor.csv`
- `InvestorInvestmentRelation.csv`
- `Fund.csv`
- `FundInvestmentRelation.csv`

這一層用來回答：

- 哪些投資機構描述或偏好明顯偏向 crypto / blockchain
- 哪些投資機構實際投過多家 crypto / blockchain 公司
- 哪些基金的偏好或投資紀錄偏向這個主題

### 4. 最後補服務機構

如果要看生態系服務方，再補：

- `ServiceProvider.csv`
- `DealServiceProviderRelation.csv`

這適合找：

- 常服務 crypto / blockchain 交易的律所、顧問、審計機構

## 優先關注的 CSV 與欄位

### A. 公司層

#### `Company.csv`

優先欄位：

- `CompanyID`
- `CompanyName`
- `Description`
- `Keywords`
- `PrimaryIndustrySector`
- `PrimaryIndustryGroup`
- `PrimaryIndustryCode`
- `AllIndustries`
- `Verticals`
- `EmergingSpaces`

用途：

- `Description`、`Keywords`：最直接的自由文字訊號，適合搜 `crypto`、`blockchain`、`web3` 等關鍵字。
- `PrimaryIndustry*`、`AllIndustries`：主產業與全產業分類，用來確認這家公司是否被正式歸到相關賽道。
- `Verticals`、`EmergingSpaces`：補主題標籤，常比主產業更接近新領域標記。

#### `CompanyIndustryRelation.csv`

優先欄位：

- `CompanyID`
- `IndustrySector`
- `IndustryGroup`
- `IndustryCode`
- `IsPrimary`

用途：

- 補 `Company.csv` 中較粗的產業欄位。
- 當 `Description` 很模糊時，這張表通常更適合做正式分類過濾。

#### `CompanyVerticalRelation.csv`

優先欄位：

- `CompanyID`
- `Vertical`

用途：

- 補抓垂直主題標籤。
- 若 crypto / blockchain 被標成 vertical，這張表會比主表更乾淨。

#### `CompanySimilarRelation.csv`

優先欄位：

- `CompanyID`
- `SimilarCompanyID`
- `SimilarCompanyName`
- `SimilarDescription`
- `SimilarPrimaryIndustrySector`
- `SimilarPrimaryIndustryGroup`
- `SimilarPrimaryIndustryCode`
- `SimilarAllIndustries`
- `SimilarVerticals`

用途：

- 當你已知少量典型 crypto 公司時，可以用這張表往外擴展相似公司。
- 適合做第二輪 candidate expansion，不適合當第一入口。

### B. 交易層

#### `Deal.csv`

優先欄位：

- `DealID`
- `CompanyID`
- `DealDate`
- `DealType`
- `DealType2`
- `DealType3`
- `DealClass`
- `DealSynopsis`
- `DealSize`
- `PostValuation`

用途：

- 用 `CompanyID` 接回已篩出的 crypto 公司。
- `DealSynopsis` 可以補自由文字語境，例如某輪融資是 wallet、exchange、mining infrastructure 還是 stablecoin 相關。
- `DealType*`、`DealClass` 幫你區分 VC、併購、加碼、退出等交易型態。

#### `DealInvestorRelation.csv`

優先欄位：

- `DealID`
- `InvestorID`
- `InvestorName`
- `IsLeadInvestor`
- `InvestorFundID`
- `InvestorFundName`
- `InvestorInvestmentAmount`

用途：

- 找出「哪些 investor / fund 真的投過這些 crypto 公司」。
- `IsLeadInvestor` 可以用來分辨陪跑投資方與主導投資方。

### C. 投資機構層

#### `Investor.csv`

優先欄位：

- `InvestorID`
- `InvestorName`
- `Description`
- `PrimaryInvestorType`
- `OtherInvestorTypes`
- `PreferredIndustry`
- `PreferredVerticals`
- `PreferredInvestmentTypes`
- `OtherInvestmentPreferences`

用途：

- `Description`：看 investor 是否明確自述專注 crypto / web3。
- `PreferredIndustry`、`PreferredVerticals`、`OtherInvestmentPreferences`：看策略偏好。
- 這張表適合找「主題型投資人」，但不能代替真實投資紀錄。

#### `InvestorInvestmentRelation.csv`

優先欄位：

- `InvestorID`
- `CompanyID`
- `DealID`
- `CompanyName`
- `DealDate`
- `DealType`
- `DealSize`
- `Industry`

用途：

- 驗證 investor 是否實際投過多家 crypto / blockchain 公司。
- 如果某 investor 在 `Investor.csv` 沒寫明 crypto 策略，但這張表中多次投到相關公司，就仍然應該視為重要對象。

### D. 基金層

#### `Fund.csv`

優先欄位：

- `FundID`
- `FundName`
- `FundType`
- `PreferredIndustry`
- `PreferredVerticals`
- `PreferredInvestmentTypes`
- `OtherInvestmentPreferences`

用途：

- 觀察基金策略層面的偏好。
- 適合找偏 crypto / blockchain 的 fund mandate。

#### `FundInvestmentRelation.csv`

優先欄位：

- `FundID`
- `CompanyID`
- `CompanyName`
- `DealID`
- `DealDate`
- `DealType`
- `DealSize`
- `PrimaryIndustryCode`

用途：

- 驗證基金是否實際投到相關公司。
- 與 `Fund.csv` 搭配，可以區分「基金自稱偏好」和「基金真的有投」。

### E. 服務機構層

#### `ServiceProvider.csv`

優先欄位：

- `ServiceProviderID`
- `ServiceProviderName`
- `Description`
- `PrimaryServiceProviderType`
- `OtherServiceProviderTypes`

用途：

- 找可能專注 crypto 交易、合規、審計、法律結構的服務機構。

#### `DealServiceProviderRelation.csv`

優先欄位：

- `DealID`
- `ServiceProviderID`
- `ServiceProviderName`
- `ServiceProvided`
- `ServiceToID`
- `ServiceToName`

用途：

- 看這些服務機構具體參與了哪些交易、服務了哪些對象。

## 實際篩選時的關鍵字

不要只搜 `crypto` 和 `blockchain`。建議至少準備一組關鍵字清單：

- `crypto`
- `cryptocurrency`
- `blockchain`
- `web3`
- `bitcoin`
- `ethereum`
- `defi`
- `stablecoin`
- `wallet`
- `exchange`
- `custody`
- `mining`
- `token`
- `tokenization`
- `nft`
- `layer 1`
- `layer 2`
- `smart contract`
- `digital asset`
- `on-chain`

建議優先把這組字套用在：

- `Company.Description`
- `Company.Keywords`
- `Company.AllIndustries`
- `Company.Verticals`
- `Company.EmergingSpaces`
- `Investor.Description`
- `Investor.PreferredIndustry`
- `Investor.PreferredVerticals`
- `Investor.OtherInvestmentPreferences`
- `Fund.PreferredIndustry`
- `Fund.PreferredVerticals`
- `Fund.OtherInvestmentPreferences`
- `Deal.DealSynopsis`
- `ServiceProvider.Description`

## 推薦分析流程

### 路線 1：先找公司，再往外擴

最穩定的路線：

1. 在 `Company.csv` 用產業欄位與文字欄位篩出疑似 crypto / blockchain 公司。
2. 用 `CompanyIndustryRelation.csv`、`CompanyVerticalRelation.csv` 補分類。
3. 用 `Deal.csv` 看這些公司有哪些交易。
4. 用 `DealInvestorRelation.csv` 找投資方。
5. 再到 `Investor.csv` / `Fund.csv` 看這些投資方與基金是否呈現主題集中。

適合的 join：

- `Company.CompanyID -> Deal.CompanyID`
- `Deal.DealID -> DealInvestorRelation.DealID`
- `DealInvestorRelation.InvestorID -> Investor.InvestorID`
- `DealInvestorRelation.InvestorFundID -> Fund.FundID`

### 路線 2：先找投資人，再反查標的

如果你先關心「哪些基金或 VC 在投 crypto」，可以這樣做：

1. 在 `Investor.csv` / `Fund.csv` 用偏好與描述欄位先找主題型投資方。
2. 用 `InvestorInvestmentRelation.csv` / `FundInvestmentRelation.csv` 反查其投資公司。
3. 再回 `Company.csv` 驗證這些公司是否真的屬於 crypto / blockchain。

適合的 join：

- `Investor.InvestorID -> InvestorInvestmentRelation.InvestorID -> Company.CompanyID`
- `Fund.FundID -> FundInvestmentRelation.FundID -> Company.CompanyID`

## 優先級建議

如果你只想最快有結果，優先級如下：

1. `Company.csv`
2. `CompanyIndustryRelation.csv`
3. `CompanyVerticalRelation.csv`
4. `Deal.csv`
5. `DealInvestorRelation.csv`
6. `Investor.csv`
7. `InvestorInvestmentRelation.csv`
8. `Fund.csv`
9. `FundInvestmentRelation.csv`
10. `ServiceProvider.csv` / `DealServiceProviderRelation.csv`

## 實務上的注意事項

- 不要只靠自由文字欄位，否則誤報率會高。
- 也不要只靠產業分類欄位，否則漏報率會高。
- 正確做法是：`分類欄位` 和 `文字欄位` 交叉驗證。
- `Company` 應該是主體入口；不要一開始就從 `Deal` 或 `Investor` 直接找，會失去主題邊界。
- 若你最後要做清單，建議至少區分：
  - `核心 crypto / blockchain 公司`
  - `相關但不純粹的金融科技 / 基礎設施公司`
  - `投資機構`
  - `基金`
  - `服務機構`

## 一句話策略

先用 `Company.csv` 建立 crypto / blockchain 公司種子集合，再沿著 `Deal -> DealInvestorRelation -> Investor / Fund` 擴展，最後用 `ServiceProvider` 補生態圈。
