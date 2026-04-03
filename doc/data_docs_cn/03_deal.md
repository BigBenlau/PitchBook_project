# 交易資料

本文件依主題整理正式 CSV，說明每個表的用途、關聯鍵與欄位分組。

## Deal.csv

**用途**：交易主表，記錄公司各輪融資、併購或退出事件的基本資訊。

**主鍵**：`DealID`

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；可連到 Deal.csv；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10810-18 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `DealNo` | 交易序號 | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄交易序號。 | — |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10505-89T | 此表主鍵，用於唯一識別單筆交易唯一識別碼。 | 可連到 Deal.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | f0adb536314b4621c444b81869246a8052c4034ffdfb5e3592f091184a703fd0 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 01/09/2026 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Eagle Pack Pet Foods | 記錄公司名稱。 | — |
| `CEOFirstName` | 執行長名 | TEXT(50) | John | 官方資料字典對此欄有說明；此欄主要記錄執行長名。 | — |
| `CEOLastName` | 執行長姓 | TEXT(100) | Hart | 官方資料字典對此欄有說明；此欄主要記錄執行長姓。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealStatus` | 交易狀態 | TEXT(50) | Completed | 記錄交易狀態，用來描述當前狀態或標記。 | — |
| `DealSizeStatus` | 交易規模狀態 | TEXT(50) | Actual | 官方資料字典對此欄有說明；此欄主要記錄交易規模狀態。 | — |
| `DealType` | 交易類型 | TEXT(50) | Buyout/LBO | 官方資料字典對此欄有說明；此欄主要記錄交易類型。 | — |
| `DealType2` | 交易Type2 | TEXT(50) | Secondary Buyout | 官方資料字典對此欄有說明；此欄主要記錄交易Type2。 | — |
| `DealType3` | 交易Type3 | TEXT(50) | Add-on | 官方資料字典對此欄有說明；此欄主要記錄交易Type3。 | — |
| `DealClass` | 交易類別 | TEXT(50) | Private Equity | 記錄交易類別，通常為金額或資本數值。 | — |
| `BusinessStatus` | 業務狀態 | TEXT(50) | Generating Revenue | 記錄業務狀態，用來描述當前狀態或標記。 | — |
| `FinancingStatus` | 融資狀態 | TEXT(50) | Private Equity-Backed | 記錄融資狀態，用來描述當前狀態或標記。 | — |
| `PostValuationStatus` | 投後估值狀態 | TEXT(50) | Estimated | 官方資料字典對此欄有說明；此欄主要記錄投後估值狀態。 | — |
| `TypeOfStock` | 類型Of股票 | TEXT | Preferred | 官方資料字典對此欄有說明；此欄主要記錄類型Of股票。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 10/01/2007 | 記錄交易完成日期相關日期。 | — |
| `AnnouncedDate` | 交易公告日期 | DATE | 01/29/2026 | 記錄交易公告日期相關日期。 | — |
| `OriginalRegistrationDate` | Original註冊日期 | DATE | 12/10/2004 | 記錄Original註冊日期相關日期。 | — |
| `CurrentRegistrationDate` | 當前註冊日期 | DATE | 12/10/2004 | 記錄當前註冊日期相關日期。 | — |
| `FiscalYear` | 財務年份 | INTEGER | 2004 | 記錄財務年份相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealSize` | 交易規模 | DECIMAL | 4.852 | 記錄交易規模，通常為金額或資本數值。 | — |
| `NativeAmountOfDeal` | 原幣交易金額 | DECIMAL | 4.852 | 記錄原幣交易金額，通常為金額或資本數值。 | — |
| `PercentAcquired` | 收購比例 | DECIMAL | 100.0 | 記錄收購比例，通常為比例或比率。 | — |
| `RaisedToDate` | 截至目前累計募集額 | DECIMAL | 266.5205 | 記錄截至目前累計募集額，通常為金額或資本數值。 | — |
| `TotalInvestedCapital` | 總投入資本 | DECIMAL | 3.009213 | 記錄總投入資本，通常為金額或資本數值。 | — |
| `TotalNewDebt` | 新增總債務 | DECIMAL | 1730.0 | 記錄新增總債務，通常為金額或資本數值。 | — |
| `Debts` | 債務 | TEXT | Revolving Credit - $293,29M (Syndicated, Floating); Term Loan B - $1,74B (Term Loan B, Syndicated Cov-lite, Floating) | 記錄債務，通常為金額或資本數值。 | — |
| `DebtRaisedInRound` | 本輪新增債務 | DECIMAL | 1730.0 | 記錄本輪新增債務，通常為金額或資本數值。 | — |
| `PremoneyValuation` | 投前估值 | DECIMAL | 167.168651 | 記錄投前估值，通常為金額或資本數值。 | — |
| `PostValuation` | 投後估值 | DECIMAL | 6.065 | 記錄投後估值，通常為金額或資本數值。 | — |
| `PricePerShare` | 每股價格 | DECIMAL | 6.55 | 官方資料字典對此欄有說明；此欄主要記錄每股價格。 | — |
| `ConversionRatio` | 轉換比率 | DECIMAL | 1 | 依欄位名推定，此欄記錄轉換比率。 | 推定欄位說明 |
| `NumberOfShares` | 數量Of股數 | LONG | 2100000 | 官方資料字典對此欄有說明；此欄主要記錄數量Of股數。 | — |
| `MarketCapEndOfFirstTradIngDay` | 上市首日收盤市值 | DECIMAL | 16.43 | 官方資料字典對此欄有說明；此欄主要記錄上市首日收盤市值。 | — |
| `Price1DayAfterOfferIng` | 發行後第 1 日價格 | DECIMAL | 17.17 | 官方資料字典對此欄有說明；此欄主要記錄發行後第 1 日價格。 | — |
| `Price5DaysAfterOfferIng` | 發行後第 5 日價格 | DECIMAL | 18.32 | 官方資料字典對此欄有說明；此欄主要記錄發行後第 5 日價格。 | — |
| `Price30DaysAfterOfferIng` | 發行後第 30 日價格 | DECIMAL | 18.15 | 官方資料字典對此欄有說明；此欄主要記錄發行後第 30 日價格。 | — |
| `ImpliedEV` | 隱含企業價值 | DECIMAL | 6.07 | 官方資料字典對此欄有說明；此欄主要記錄隱含企業價值。 | — |
| `Revenue` | 營收 | DECIMAL | 2.1 | 記錄營收，通常為金額或資本數值。 | — |
| `RevenueGrowthSinceLastDebtDeal` | 距上次債務交易以來的營收成長 | DECIMAL | -34.58182747 | 記錄距上次債務交易以來的營收成長，通常為比例或比率。 | — |
| `GrossProfit` | 毛利 | DECIMAL | 1903.6824386 | 官方資料字典對此欄有說明；此欄主要記錄毛利。 | — |
| `NetIncome` | 淨利 | DECIMAL | -68.0679751 | 官方資料字典對此欄有說明；此欄主要記錄淨利。 | — |
| `EBITDA` | EBITDA | DECIMAL | 2590.88698811 | 官方資料字典對此欄有說明；此欄主要記錄EBITDA。 | — |
| `TotalDebt` | 總債務 | DECIMAL | 13844.06112426 | 記錄總債務，通常為金額或資本數值。 | — |
| `Debt_EBITDA` | 債務EBITDA | DECIMAL | 5.04610568 | 記錄債務EBITDA，通常為金額或資本數值。 | — |
| `Debt_Equity` | 債務權益 | DECIMAL | 4.68891339 | 記錄債務權益，通常為金額或資本數值。 | — |
| `DealSize_EBITDA` | 交易規模EBITDA | DECIMAL | 1.49530907 | 官方資料字典對此欄有說明；此欄主要記錄交易規模EBITDA。 | — |
| `Valuation_EBITDA` | 估值EBITDA | DECIMAL | 5.99322271 | 官方資料字典對此欄有說明；此欄主要記錄估值EBITDA。 | — |
| `ImpliedEV_EBITDA` | 隱含EVEBITDA | DECIMAL | 0.98276491 | 官方資料字典對此欄有說明；此欄主要記錄隱含EVEBITDA。 | — |
| `ImpliedEV_EBIT` | 隱含EVEBIT | DECIMAL | 1.01381747 | 官方資料字典對此欄有說明；此欄主要記錄隱含EVEBIT。 | — |
| `Valuation_EBIT` | 估值EBIT | DECIMAL | 33.40007827 | 官方資料字典對此欄有說明；此欄主要記錄估值EBIT。 | — |
| `Valuation_NetIncome` | 估值淨收益 | DECIMAL | -228.12141419 | 官方資料字典對此欄有說明；此欄主要記錄估值淨收益。 | — |
| `DealSize_EBIT` | 交易規模EBIT | DECIMAL | 8.33331953 | 官方資料字典對此欄有說明；此欄主要記錄交易規模EBIT。 | — |
| `DealSize_NetIncome` | 交易規模淨收益 | DECIMAL | -56.91629284 | 官方資料字典對此欄有說明；此欄主要記錄交易規模淨收益。 | — |
| `DealSize_Revenue` | 交易規模營收 | DECIMAL | 0.73011353 | 官方資料字典對此欄有說明；此欄主要記錄交易規模營收。 | — |
| `Valuation_Revenue` | 估值營收 | DECIMAL | 2.57608132 | 官方資料字典對此欄有說明；此欄主要記錄估值營收。 | — |
| `ImpliedEV_Revenue` | 隱含EV營收 | DECIMAL | 0.525 | 官方資料字典對此欄有說明；此欄主要記錄隱含EV營收。 | — |
| `DealSize_CashFlow` | 交易規模現金現金流 | DECIMAL | 41.26429413 | 官方資料字典對此欄有說明；此欄主要記錄交易規模現金現金流。 | — |
| `Valuation_CashFlow` | 估值現金現金流 | DECIMAL | 165.38795242 | 官方資料字典對此欄有說明；此欄主要記錄估值現金現金流。 | — |
| `ImpliedEV_CashFlow` | 隱含EV現金現金流 | DECIMAL | 352.95589988 | 官方資料字典對此欄有說明；此欄主要記錄隱含EV現金現金流。 | — |
| `ImpliedEV_NetIncome` | 隱含EV淨收益 | DECIMAL | 1.01499894 | 官方資料字典對此欄有說明；此欄主要記錄隱含EV淨收益。 | — |
| `EBITDAMarginPercent` | EBITDA 利潤率 | DECIMAL | 42.98324035 | 記錄EBITDA 利潤率，通常為比例或比率。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SiteLocation` | 交易地點 | TEXT(100) | Tewksbury, MA | 官方資料字典對此欄有說明；此欄主要記錄交易地點。 | — |
| `CEOPhone` | 執行長電話 | TEXT(255) | +1 (636) 887-5628 | 官方資料字典對此欄有說明；此欄主要記錄執行長電話。 | — |
| `CEOEmail` | 執行長電子郵件 | TEXT(255) | robert@nautilusdt.com | 官方資料字典對此欄有說明；此欄主要記錄執行長電子郵件。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CEOPBId` | CEOPBId | TEXT(20) | 12564-46P | 官方資料字典對此欄有說明；此欄主要記錄CEOPBId。 | 通常可連到 Person.csv |
| `CEOMiddle` | 執行長中間名 | TEXT(100) | J. | 官方資料字典對此欄有說明；此欄主要記錄執行長中間名。 | — |
| `CEOPrefix` | 執行長前綴 | TEXT(50) | Mr. | 官方資料字典對此欄有說明；此欄主要記錄執行長前綴。 | — |
| `CEOSuffix` | 執行長後綴 | TEXT(50) | Ph.D | 官方資料字典對此欄有說明；此欄主要記錄執行長後綴。 | — |
| `CEO` | 執行長 | TEXT(500) | John Hart | 官方資料字典對此欄有說明；此欄主要記錄執行長。 | — |
| `CEOBiography` | 執行長簡歷 | TEXT | Mr. John Hart served as Chief Executive Officer at Eagle Pack. | 官方資料字典對此欄有說明；此欄主要記錄執行長簡歷。 | — |
| `CEOEducation` | 執行長教育背景 | TEXT | Lindenwood University, MBA (Master of Business Administration), 2005; University of Missouri, Columbia, Bachelor's, 1999 | 官方資料字典對此欄有說明；此欄主要記錄執行長教育背景。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorOwnership` | 投資機構持有 | DECIMAL | 25.25 | 記錄投資機構持有，通常為比例或比率。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `VCRound` | VC輪次 | TEXT(50) | 9th Round | 記錄VC輪次，通常為金額或資本數值。 | — |
| `VCRoundUp_Down_Flat` | VC 輪次變化方向 | TEXT(50) | Up Round | 官方資料字典對此欄有說明；此欄主要記錄VC 輪次變化方向。 | — |
| `StockSplit` | 股票拆分 | TEXT(50) | 4550:1 | 官方資料字典對此欄有說明；此欄主要記錄股票拆分。 | — |
| `DealSynopsis` | 交易摘要 | TEXT | The company was acquired by Wellness Pet Food via its financial sponsor L Catterton and Loft Growth Partners through ... | 官方資料字典對此欄有說明；此欄主要記錄交易摘要。 | — |
| `NativeCurrencyOfDeal` | 交易原幣幣別 | TEXT(50) | US Dollars (USD) | 官方資料字典對此欄有說明；此欄主要記錄交易原幣幣別。 | — |
| `TotalInvestedEquity` | 總投入股權資本 | DECIMAL | 3.009213 | 記錄總投入股權資本，通常為金額或資本數值。 | — |
| `AddOn` | 追加 | TEXT(10) | Yes | 官方資料字典對此欄有說明；此欄主要記錄追加。 | — |
| `AddOnSponsors` | 追加Sponsors | TEXT | L Catterton, Loft Growth Partners | 官方資料字典對此欄有說明；此欄主要記錄追加Sponsors。 | — |
| `AddOnPlatform` | 追加Platform | TEXT | Wellness Pet Company | 官方資料字典對此欄有說明；此欄主要記錄追加Platform。 | — |
| `ContingentPayout` | ContingentPayout | DECIMAL | 10.11013305 | 記錄ContingentPayout，通常為金額或資本數值。 | — |
| `Employees` | 員工數 | INTEGER | 82 | 官方資料字典對此欄有說明；此欄主要記錄員工數。 | — |
| `SeriesOfStock` | 股票系列 | TEXT | B | 依欄位名推定，此欄記錄股票系列。 | 推定欄位說明 |
| `TickerSymbol` | 股票代號 | TEXT(100) | SPSX | 官方資料字典對此欄有說明；此欄主要記錄股票代號。 | — |
| `Exchange` | 交易所 | TEXT(100) | NAS | 官方資料字典對此欄有說明；此欄主要記錄交易所。 | — |
| `FilIngRangeLow` | FilIng範圍Low | DECIMAL | 12.0 | 官方資料字典對此欄有說明；此欄主要記錄FilIng範圍Low。 | — |
| `FilIngRangeHigh` | FilIng範圍上限 | DECIMAL | 14.0 | 官方資料字典對此欄有說明；此欄主要記錄FilIng範圍上限。 | — |
| `Investors` | Investors | INTEGER | 3 | 官方資料字典對此欄有說明；此欄主要記錄Investors。 | — |
| `NewInvestors` | 新Investors | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄新Investors。 | — |
| `FollowOnInvestors` | 跟投Investors | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄跟投Investors。 | — |


## DealCapTableRelation.csv

**用途**：記錄交易相關的股權結構與條款欄位。此表未在官方 Excel 中提供完整欄位字典，以下說明依欄位名推定。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`CapTableID`

**可連接到**：可連到 Deal.csv；股權結構鍵，本批資料未提供單獨主表；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10151-11T | 依欄位名推定，此欄記錄交易唯一識別碼。 | 可連到 Deal.csv；推定欄位說明 |
| `CapTableID` | 股權結構識別碼 | TEXT(20) | 14386-15 | 依欄位名推定，此欄記錄股權結構識別碼。 | 股權結構鍵，本批資料未提供單獨主表；推定欄位說明 |
| `RowID` | 列唯一識別碼 | TEXT(255) | b70873ba95808bbabef3d142212e212f29a246df500d56086fbfdc6e4a95eba3 | 依欄位名推定，此欄記錄列唯一識別碼。 | 列級稽核鍵；推定欄位說明 |
| `LastUpdated` | 最後更新日期 | DATE | 05/30/2025 | 依欄位名推定，此欄記錄最後更新日期。 | 列級更新時間；推定欄位說明 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `TypeOfStock` | 類型Of股票 | TEXT | Participating Preferred | 依欄位名推定，此欄記錄類型Of股票。 | 推定欄位說明 |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `NumberOfSharesAuthorized` | 數量Of股數Authorized | INTEGER | 5750000 | 依欄位名推定，此欄記錄數量Of股數Authorized。 | 推定欄位說明 |
| `ParValue` | 面值價值 | DECIMAL | 0.001 | 依欄位名推定，此欄記錄面值價值。 | 推定欄位說明 |
| `DividendRatePercentage` | Dividend比率百分比 | DECIMAL | 8.0 | 依欄位名推定，此欄記錄Dividend比率百分比。 | 推定欄位說明 |
| `OriginalIssuePrice` | Original發行價格 | DECIMAL | 2.6087 | 依欄位名推定，此欄記錄Original發行價格。 | 推定欄位說明 |
| `LiquidationPrice` | 清算價格 | DECIMAL | 2.6087 | 依欄位名推定，此欄記錄清算價格。 | 推定欄位說明 |
| `LiquidationPreferenceMultiple` | 清算Preference倍數 | DECIMAL | 1.0 | 依欄位名推定，此欄記錄清算Preference倍數。 | 推定欄位說明 |
| `ConversionPrice` | 轉換價格 | DECIMAL | 2.6087 | 依欄位名推定，此欄記錄轉換價格。 | 推定欄位說明 |
| `PercentOwned` | 百分比持有 | DECIMAL | 33.33333333 | 依欄位名推定，此欄記錄百分比持有。 | 推定欄位說明 |
| `SharesSought` | 股數Sought | INTEGER | 562100 | 依欄位名推定，此欄記錄股數Sought。 | 推定欄位說明 |
| `PriceperShare` | Priceper股份 | DECIMAL | 2.6087 | 依欄位名推定，此欄記錄Priceper股份。 | 推定欄位說明 |
| `NumberOfSharesAcquired` | 數量Of股數Acquired | INTEGER | 5750000 | 依欄位名推定，此欄記錄數量Of股數Acquired。 | 推定欄位說明 |
| `ConversionRatio` | 轉換比率 | DECIMAL | 1 | 依欄位名推定，此欄記錄轉換比率。 | 推定欄位說明 |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SeriesOfStock` | 股票系列 | TEXT | B | 依欄位名推定，此欄記錄股票系列。 | 推定欄位說明 |
| `LiquidationPreferences` | 清算Preferences | TEXT | Senior | 依欄位名推定，此欄記錄清算Preferences。 | 推定欄位說明 |
| `ParticipatingVSNonParticipating` | ParticipatingVS非Participating | TEXT | Participating | 依欄位名推定，此欄記錄ParticipatingVS非Participating。 | 推定欄位說明 |
| `DividendRights` | Dividend權利 | TEXT | Yes | 依欄位名推定，此欄記錄Dividend權利。 | 推定欄位說明 |
| `Cumulative_NonCumulative` | Cumulative非Cumulative | TEXT | Non-Cumulative | 依欄位名推定，此欄記錄Cumulative非Cumulative。 | 推定欄位說明 |
| `AntiDilutionProvisions` | AntiDilutionProvisions | TEXT | Weighted Average | 依欄位名推定，此欄記錄AntiDilutionProvisions。 | 推定欄位說明 |
| `RedemptionRights` | 贖回權利 | TEXT | Yes | 依欄位名推定，此欄記錄贖回權利。 | 推定欄位說明 |
| `BoardVotingRights` | 董事會投票權利 | TEXT | No | 依欄位名推定，此欄記錄董事會投票權利。 | 推定欄位說明 |
| `GeneralVotingRights` | 一般投票權利 | TEXT | Yes | 依欄位名推定，此欄記錄一般投票權利。 | 推定欄位說明 |


## DealDebtLenderRelation.csv

**用途**：記錄交易中的債務貸方與借款條件。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`FacilityID`、`LenderID`

**可連接到**：可連到 Deal.csv；額度鍵，本批資料未提供單獨主表；貸方鍵，本批資料未提供單獨主表；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10417-96T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `FacilityID` | 融資額度識別碼 | TEXT(20) | 10518-40D | 唯一識別碼，用於記錄融資額度識別碼。 | 額度鍵，本批資料未提供單獨主表 |
| `LenderID` | 貸方識別碼 | TEXT(20) | 41330-17 | 唯一識別碼，用於記錄貸方識別碼。 | 貸方鍵，本批資料未提供單獨主表 |
| `RowID` | 列唯一識別碼 | TEXT(255) | 1291247c4bbbedf928483bde8c485f95d633d3d0bb6445ecc7da3cd8712f7b43 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 01/08/2026 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LenderName` | 貸方名稱 | TEXT(255) | Huntington Bancshares | 官方資料字典對此欄有說明；此欄主要記錄貸方名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LenderType` | 貸方類型 | TEXT(256) | Commercial Bank | 官方資料字典對此欄有說明；此欄主要記錄貸方類型。 | — |
| `DebtStatus` | 債務狀態 | TEXT(50) | Done | 記錄債務狀態，用來描述當前狀態或標記。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `MaturityDate` | Maturity日期 | DATE | 01/31/2012 | 官方資料字典對此欄有說明；此欄主要記錄Maturity日期。 | — |
| `IssueDate` | 發行日期 | DATE | 02/28/2006 | 記錄發行日期相關日期。 | — |
| `AsOfDate` | Of日期 | DATE | 12/01/2009 | 記錄Of日期相關日期。 | — |
| `RefResetFrequency` | RefResetFrequency | TEXT(256) | Quarterly | 官方資料字典對此欄有說明；此欄主要記錄RefResetFrequency。 | — |
| `Tenor` | 期限 | DECIMAL | 6.0 | 官方資料字典對此欄有說明；此欄主要記錄期限。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DebtRound` | 債務輪次 | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄債務輪次。 | — |
| `Fund1Amount` | Fund1金額 | DECIMAL | 13.3 | 記錄Fund1金額，通常為金額或資本數值。 | — |
| `Fund2Amount` | Fund2金額 | DECIMAL | 2.232 | 記錄Fund2金額，通常為金額或資本數值。 | — |
| `DebtAmount` | 債務金額 | DECIMAL | 0.6 | 記錄債務金額，通常為金額或資本數值。 | — |
| `LenderAmount` | 貸方金額 | DECIMAL | 0.6 | 記錄貸方金額，通常為金額或資本數值。 | — |
| `DebtProvided` | 債務提供 | TEXT(256) | Term Loan | 官方資料字典對此欄有說明；此欄主要記錄債務提供。 | — |
| `AdditionalDebtCharacteristics` | Additional債務Characteristics | TEXT(256) | Syndicated | 官方資料字典對此欄有說明；此欄主要記錄Additional債務Characteristics。 | — |
| `DebtInstruments` | 債務Instruments | TEXT(255) | Term Loan | 官方資料字典對此欄有說明；此欄主要記錄債務Instruments。 | — |
| `OID_Price` | OID價格 | DECIMAL | 90.0 | 官方資料字典對此欄有說明；此欄主要記錄OID價格。 | — |
| `PercentOfDebt` | 百分比Of債務 | DECIMAL | 100.0 | 記錄百分比Of債務，通常為比例或比率。 | — |
| `TotalNewDebt` | 新增總債務 | DECIMAL | 0.6 | 記錄新增總債務，通常為金額或資本數值。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Region` | Region | TEXT(255) | US | 官方資料字典對此欄有說明；此欄主要記錄Region。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LenderTitle` | 貸方Title | TEXT(255) | Syndication Agent | 官方資料字典對此欄有說明；此欄主要記錄貸方Title。 | — |
| `LeadPartner` | 主導合夥人姓名 | TEXT(255) | Noémie Renier | 官方資料字典對此欄有說明；此欄主要記錄主導合夥人姓名。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Fund1` | Fund1 | TEXT(255) | Rural Impulse Fund I | 官方資料字典對此欄有說明；此欄主要記錄Fund1。 | — |
| `Fund2` | Fund2 | TEXT(255) | SLR Senior Investment Corp BDC | 官方資料字典對此欄有說明；此欄主要記錄Fund2。 | — |
| `PIK` | PIK | DECIMAL | 550.0 | 記錄PIK，通常為金額或資本數值。 | — |
| `Spread_InterestRate` | 利差利息比率 | DECIMAL | 225 | 官方資料字典對此欄有說明；此欄主要記錄利差利息比率。 | — |
| `Seniority` | Seniority | TEXT(256) | Senior | 官方資料字典對此欄有說明；此欄主要記錄Seniority。 | — |
| `Security` | 擔保 | TEXT(256) | All Assets | 官方資料字典對此欄有說明；此欄主要記錄擔保。 | — |
| `Rate` | 比率 | TEXT(256) | Floating | 官方資料字典對此欄有說明；此欄主要記錄比率。 | — |
| `SpreadReference` | 利差參考 | TEXT(256) | LIBOR | 官方資料字典對此欄有說明；此欄主要記錄利差參考。 | — |
| `Options` | Options | TEXT(50) | Convertible | 官方資料字典對此欄有說明；此欄主要記錄Options。 | — |
| `Spread_Coupon` | 利差票息 | TEXT(255) | LIBOR + 225 | 官方資料字典對此欄有說明；此欄主要記錄利差票息。 | — |
| `Floor` | Floor | DECIMAL | 1 | 官方資料字典對此欄有說明；此欄主要記錄Floor。 | — |
| `PrimaryYTM` | 主要到期殖利率 | DECIMAL | 5.9587 | 官方資料字典對此欄有說明；此欄主要記錄主要到期殖利率。 | — |
| `LeadArranger` | 主導Arranger | TEXT(250) | Wachovia Bank | 官方資料字典對此欄有說明；此欄主要記錄主導Arranger。 | — |
| `TotalLenders` | 總Lenders | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總Lenders。 | — |
| `Cost` | Cost | DECIMAL | 3.586 | 官方資料字典對此欄有說明；此欄主要記錄Cost。 | — |


## DealDistribBeneficiaryRelation.csv

**用途**：記錄交易分配的受益方。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`BeneficiaryID`、`Fund1ID`、`Fund2ID`

**可連接到**：可連到 Deal.csv；受益方鍵，本批資料未提供單獨主表；通常可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10031-05T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `BeneficiaryID` | 受益方識別碼 | TEXT(20) | 10085-05 | 唯一識別碼，用於記錄受益方識別碼。 | 受益方鍵，本批資料未提供單獨主表 |
| `Fund1ID` | Fund1識別碼 | TEXT(20) | 10928-44F | 官方資料字典對此欄有說明；此欄主要記錄Fund1識別碼。 | 通常可連到 Fund.csv |
| `Fund2ID` | Fund2識別碼 | TEXT(20) | 12556-54F | 官方資料字典對此欄有說明；此欄主要記錄Fund2識別碼。 | 通常可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | be16c234928b4e33bc2e2668ef2a758020cc18102e5a04585c4ae697a82f941f | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 11/02/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `BeneficiaryName` | 受益方名稱 | TEXT(255) | Sentinel Capital Partners | 記錄受益方名稱。 | — |
| `Fund1Name` | Fund1名稱 | TEXT(200) | Sentinel Capital Partners II | 官方資料字典對此欄有說明；此欄主要記錄Fund1名稱。 | — |
| `Fund2Name` | Fund2名稱 | TEXT(200) | Veritas Capital Fund IV | 官方資料字典對此欄有說明；此欄主要記錄Fund2名稱。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `IRRPercentage` | IRR百分比 | TEXT | 58.0 | 官方資料字典對此欄有說明；此欄主要記錄IRR百分比。 | — |
| `ExitMultiple` | 退出倍數 | TEXT | 4.0 | 官方資料字典對此欄有說明；此欄主要記錄退出倍數。 | — |
| `Fund1Amount` | Fund1金額 | DECIMAL | 4.76 | 記錄Fund1金額，通常為金額或資本數值。 | — |
| `Fund2Amount` | Fund2金額 | DECIMAL | 17.4 | 記錄Fund2金額，通常為金額或資本數值。 | — |
| `PercentageOfCompanyStillHeld` | 百分比Of公司仍然持有 | DECIMAL | 0.0 | 官方資料字典對此欄有說明；此欄主要記錄百分比Of公司仍然持有。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Currency` | Currency | TEXT(100) | USD | 記錄Currency，通常為金額或資本數值。 | — |


## DealInvestorRelation.csv

**用途**：記錄交易關聯的投資機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`InvestorID`、`InvestorFundID`、`LeadPartnerID`

**可連接到**：可連到 Deal.csv；可連到 Investor.csv；通常可連到 Fund.csv；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10306-99T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10059-49 | 唯一識別碼，用於記錄投資機構唯一識別碼。 | 可連到 Investor.csv |
| `InvestorFundID` | 投資機構基金識別碼 | TEXT(20) | 10936-27F | 唯一識別碼，用於記錄投資機構基金識別碼。 | 通常可連到 Fund.csv |
| `LeadPartnerID` | 主導合夥人識別碼 | TEXT(20) | 39525-58P | 唯一識別碼，用於記錄主導合夥人識別碼。 | 通常可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 93777bf587512d34a73cf0527eb648a750c0f9b2e659709d115e53dc8afdea15 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 07/26/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorName` | 投資機構名稱 | TEXT(255) | Stockwell Capital | 記錄投資機構名稱。 | — |
| `InvestorFundName` | 投資機構基金名稱 | TEXT(255) | Bain Capital Fund IX | 官方資料字典對此欄有說明；此欄主要記錄投資機構基金名稱。 | — |
| `LeadPartnerName` | 主導合夥人姓名 | TEXT(125) | Andrew Hollod | 官方資料字典對此欄有說明；此欄主要記錄主導合夥人姓名。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorStatus` | 投資方狀態 | TEXT(50) | New Investor | 記錄投資方狀態，用來描述當前狀態或標記。 | — |
| `IsLeadInvestor` | Is主導投資機構 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Is主導投資機構。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorInvestmentAmount` | 投資機構投資金額 | DECIMAL | 0.4136775 | 官方資料字典對此欄有說明；此欄主要記錄投資機構投資金額。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorWebsite` | 投資機構網站 | TEXT | www.stockwellcapital.com | 記錄投資機構網站。 | — |


## DealSellerRelation.csv

**用途**：記錄交易中的出售方或退出方。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`Seller_ExiterID`、`Seller_ExiterFundID`

**可連接到**：可連到 Deal.csv；退出方鍵，可能對應投資機構、基金或其他持有人；通常可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10009-54T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `Seller_ExiterID` | 出售方退出方識別碼 | TEXT(20) | 10027-27 | 唯一識別碼，用於記錄出售方退出方識別碼。 | 退出方鍵，可能對應投資機構、基金或其他持有人 |
| `Seller_ExiterFundID` | 出售方退出方基金識別碼 | TEXT(20) | 11462-23F | 唯一識別碼，用於記錄出售方退出方基金識別碼。 | 通常可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 046b4cd9400985570062d37a0a9bf6088099170fc279f97a49c1a918dbd91a99 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 11/02/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Seller_ExiterName` | 出售方退出方名稱 | TEXT(255) | Perfectis Private Equity | 記錄出售方退出方名稱。 | — |
| `Seller_ExiterFundName` | 出售方退出方基金名稱 | TEXT(255) | VS&A Communications Partners II | 記錄出售方退出方基金名稱。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PercentOfCompanySold` | 百分比Of公司出售 | DECIMAL | 100.0 | 官方資料字典對此欄有說明；此欄主要記錄百分比Of公司出售。 | — |
| `PercentOfCompanyStillHeld` | 百分比Of公司仍然持有 | DECIMAL | 0.0 | 官方資料字典對此欄有說明；此欄主要記錄百分比Of公司仍然持有。 | — |
| `EntryAmount` | Entry金額 | DECIMAL | 33.10574585 | 記錄Entry金額，通常為金額或資本數值。 | — |
| `ExitAmount` | 退出金額 | DECIMAL | 16.0 | 記錄退出金額，通常為金額或資本數值。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Partial_Full` | PartialFull | TEXT(20) | Full | 官方資料字典對此欄有說明；此欄主要記錄PartialFull。 | — |
| `TimeToExit` | 時間退出 | DECIMAL | 3.85 | 官方資料字典對此欄有說明；此欄主要記錄時間退出。 | — |


## DealServiceProviderRelation.csv

**用途**：記錄交易關聯的服務機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`ServiceProviderID`、`ServiceToID`、`LeadPartnerID`

**可連接到**：可連到 Deal.csv；可連到 ServiceProvider.csv；服務對象鍵，可能對應公司、基金、投資機構等；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10043-02T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10119-43 | 唯一識別碼，用於記錄服務機構唯一識別碼。 | 可連到 ServiceProvider.csv |
| `ServiceToID` | 服務識別碼 | TEXT(20) | 10082-89 | 唯一識別碼，用於記錄服務識別碼。 | 服務對象鍵，可能對應公司、基金、投資機構等 |
| `DealNo` | 交易序號 | INTEGER | 6 | 官方資料字典對此欄有說明；此欄主要記錄交易序號。 | — |
| `LeadPartnerID` | 主導合夥人識別碼 | TEXT(20) | 126830-17P | 唯一識別碼，用於記錄主導合夥人識別碼。 | 通常可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 1c064effdea71f70b9c64ba010a78b3f2d98f8d15cfedced99d1534604c35f28 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderName` | 服務機構名稱 | TEXT(255) | Eckert Seamans Cherin & Mellott | 記錄服務機構名稱。 | — |
| `ServiceToName` | 服務名稱 | TEXT(255) | Citadel Broadcasting | 官方資料字典對此欄有說明；此欄主要記錄服務名稱。 | — |
| `LeadPartnerName` | 主導合夥人姓名 | TEXT(125) | Grant Edwards | 官方資料字典對此欄有說明；此欄主要記錄主導合夥人姓名。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderType` | 服務機構類型 | TEXT(50) | Law Firm | 官方資料字典對此欄有說明；此欄主要記錄服務機構類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 04/26/2001 | 記錄交易完成日期相關日期。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(50) | Legal Advisor | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |
| `BuySide_SellSide` | 買方Side賣方Side | TEXT(200) | Sell-side | 官方資料字典對此欄有說明；此欄主要記錄買方Side賣方Side。 | — |
| `Comments` | 備註說明 | TEXT | Lead Partner: Grant Edwards | 官方資料字典對此欄有說明；此欄主要記錄備註說明。 | — |


## DealTrancheRelation.csv

**用途**：記錄交易的分批 tranche 資訊。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`DealID`、`InvestorID`

**可連接到**：可連到 Deal.csv；可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10100-71T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10267-84 | 唯一識別碼，用於記錄投資機構唯一識別碼。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | b2493b48a7efa287fd2462b009d4399efd84571b0ebd9169f3e4ff1a8a5e8b51 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FinancingType` | 融資類型 | TEXT(50) | Later Stage VC | 官方資料字典對此欄有說明；此欄主要記錄融資類型。 | — |
| `StockType` | 股票類型 | TEXT(50) | Common | 官方資料字典對此欄有說明；此欄主要記錄股票類型。 | — |
| `StockSeriesType` | 股票Series類型 | TEXT(10) | A | 官方資料字典對此欄有說明；此欄主要記錄股票Series類型。 | — |
| `ConversionStatus` | 轉換狀態 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄轉換狀態。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `TrancheDate` | 分批日期 | DATE | 07/28/2004 | 官方資料字典對此欄有說明；此欄主要記錄分批日期。 | — |
| `ConversionDate` | 轉換日期 | DATE | 04/24/2007 | 官方資料字典對此欄有說明；此欄主要記錄轉換日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Amount` | 金額 | DECIMAL | 2.0 | 記錄金額，通常為金額或資本數值。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Investor` | 投資機構 | TEXT(255) | Enhanced Healthcare Partners | 官方資料字典對此欄有說明；此欄主要記錄投資機構。 | — |
| `Investor2` | Investor2 | TEXT(255) | Reliant Star Capital | 官方資料字典對此欄有說明；此欄主要記錄Investor2。 | — |
| `InvestorID2` | 投資機構ID2 | TEXT(20) | 50939-92 | 唯一識別碼，用於記錄投資機構ID2。 | — |
| `Investor3` | Investor3 | TEXT(255) | Mark Fountain | 官方資料字典對此欄有說明；此欄主要記錄Investor3。 | — |
| `InvestorID3` | 投資機構ID3 | TEXT(20) | 1261484-02 | 唯一識別碼，用於記錄投資機構ID3。 | — |
