# 投資機構資料

本文件依主題整理正式 CSV，說明每個表的用途、關聯鍵與欄位分組。

## Investor.csv

**用途**：投資機構主表，記錄投資機構的基本資料、投資偏好、歷史活動與最近交易。

**主鍵**：`InvestorID`

**主要關聯鍵**：`ParentCompanyID`

**可連接到**：可連到 Investor.csv；通常表示母機構或母公司 ID；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10010-89 | 此表主鍵，用於唯一識別單筆投資機構唯一識別碼。 | 可連到 Investor.csv |
| `ParentCompanyID` | 母公司識別碼 | TEXT(20) | 52315-12 | 官方資料字典對此欄有說明；此欄主要記錄母公司識別碼。 | 通常表示母機構或母公司 ID |
| `CikCode` | Cik代碼 | TEXT | 1054374 | 官方資料字典對此欄有說明；此欄主要記錄Cik代碼。 | — |
| `RowID` | 列唯一識別碼 | TEXT(255) | 57baa46595de6ef2db46d7f8fa4e185fb543a1ce44ea8a48dbe98c85a78eed33 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 09/17/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorName` | 投資機構名稱 | TEXT(255) | Broadcom | 記錄投資機構名稱。 | — |
| `InvestorAlsoKnownAs` | 投資機構其他名稱 | TEXT(500) | Charterhouse | 官方資料字典對此欄有說明；此欄主要記錄投資機構其他名稱。 | — |
| `InvestorFormerName` | 投資機構曾用名稱 | TEXT | Seed Capital Company | 官方資料字典對此欄有說明；此欄主要記錄投資機構曾用名稱。 | — |
| `InvestorLegalName` | 投資機構法定名稱 | TEXT(255) | Broadcom Corp. | 官方資料字典對此欄有說明；此欄主要記錄投資機構法定名稱。 | — |
| `PrimaryContactFirstName` | 主要聯絡人名 | TEXT(200) | Trevor | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人名。 | — |
| `PrimaryContactLastName` | 主要聯絡人姓 | TEXT(200) | Pears | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人姓。 | — |
| `LastClosedFundName` | 最近已關閉基金名稱 | TEXT(200) | Charterhouse Equity Partners IV | 記錄最近已關閉基金名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorStatus` | 投資方狀態 | TEXT(50) | Acquired/Merged | 記錄投資方狀態，用來描述當前狀態或標記。 | — |
| `PrimaryInvestorType` | 主要投資機構類型 | TEXT(50) | Corporation | 官方資料字典對此欄有說明；此欄主要記錄主要投資機構類型。 | — |
| `OtherInvestorTypes` | 其他投資機構Types | TEXT | Growth/Expansion | 官方資料字典對此欄有說明；此欄主要記錄其他投資機構Types。 | — |
| `PreferredInvestmentTypes` | 偏好投資Types | TEXT | Merger/Acquisition | 官方資料字典對此欄有說明；此欄主要記錄偏好投資Types。 | — |
| `LastInvestmentSizeStatus` | 最近投資規模狀態 | TEXT(50) | Actual | 官方資料字典對此欄有說明；此欄主要記錄最近投資規模狀態。 | — |
| `LastInvestmentValuationStatus` | 最近投資估值狀態 | TEXT(50) | Actual | 官方資料字典對此欄有說明；此欄主要記錄最近投資估值狀態。 | — |
| `LastInvestmentType` | 最近投資類型 | TEXT(50) | Merger/Acquisition | 官方資料字典對此欄有說明；此欄主要記錄最近投資類型。 | — |
| `LastInvestmentType2` | 最近投資Type2 | TEXT(50) | Series D | 官方資料字典對此欄有說明；此欄主要記錄最近投資Type2。 | — |
| `LastInvestmentType3` | 最近投資Type3 | TEXT(50) | Add-on | 官方資料字典對此欄有說明；此欄主要記錄最近投資Type3。 | — |
| `LastInvestmentClass` | 最近投資類別 | TEXT(50) | Corporate | 官方資料字典對此欄有說明；此欄主要記錄最近投資類別。 | — |
| `LastInvestmentStatus` | 最近投資狀態 | TEXT(50) | Completed | 記錄最近投資狀態，用來描述當前狀態或標記。 | — |
| `LastClosedFundType` | 最近已關閉基金類型 | TEXT(50) | Buyout | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `YearFounded` | 年份成立 | INTEGER | 1991 | 記錄年份成立相關日期。 | — |
| `InvestmentProfessionalCountDate` | 投資ProfessionalCount日期 | DATE | 07/26/2019 | 記錄投資ProfessionalCount日期相關日期。 | — |
| `TotalInvestmentsInTheLast2Years` | 總投資TheLast2年份 | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總投資TheLast2年份。 | — |
| `TotalInvestmentsInTheLast5Years` | 總投資TheLast5年份 | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總投資TheLast5年份。 | — |
| `TotalFundsClosedInTheLast2Years` | 總Funds已關閉TheLast2年份 | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄總Funds已關閉TheLast2年份。 | — |
| `TotalFundsClosedInTheLast5Years` | 總Funds已關閉TheLast5年份 | INTEGER | 9 | 官方資料字典對此欄有說明；此欄主要記錄總Funds已關閉TheLast5年份。 | — |
| `LastInvestmentDate` | 最近投資日期 | DATE | 09/16/2023 | 記錄最近投資日期相關日期。 | — |
| `LastFinancingDebtDate` | 最近融資債務日期 | DATE | 09/16/2023 | 官方資料字典對此欄有說明；此欄主要記錄最近融資債務日期。 | — |
| `LastClosedFundVintage` | 最近已關閉基金Vintage | INTEGER | 2005 | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金Vintage。 | — |
| `LastClosedFundCloseDate` | 最近已關閉基金關閉日期 | DATE | 12/31/2003 | 記錄最近已關閉基金關閉日期相關日期。 | — |
| `LastClosedFundOpenDate` | 最近已關閉基金開放日期 | DATE | 05/02/2003 | 記錄最近已關閉基金開放日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AUM` | 管理資產規模 | DECIMAL | 67.01043936 | 記錄管理資產規模，通常為金額或資本數值。 | — |
| `DryPowder` | 乾粉資金 | DECIMAL | 9117.61640206 | 記錄乾粉資金，通常為金額或資本數值。 | — |
| `MedianRoundAmount` | 中位數輪次金額 | DECIMAL | 86.03 | 官方資料字典對此欄有說明；此欄主要記錄中位數輪次金額。 | — |
| `MedianValuation` | 中位數估值 | DECIMAL | 123.0 | 官方資料字典對此欄有說明；此欄主要記錄中位數估值。 | — |
| `MinFundSize` | 最小值基金規模 | DECIMAL | 152.0 | 官方資料字典對此欄有說明；此欄主要記錄最小值基金規模。 | — |
| `MaxFundSize` | Max基金規模 | DECIMAL | 1000.0 | 官方資料字典對此欄有說明；此欄主要記錄Max基金規模。 | — |
| `MedianFundSize` | 中位數基金規模 | DECIMAL | 291.25 | 官方資料字典對此欄有說明；此欄主要記錄中位數基金規模。 | — |
| `PreferredInvestmentAmount` | 偏好投資金額 | TEXT(50) | 40.0 - 150.0 | 記錄偏好投資金額，通常為金額或資本數值。 | — |
| `PreferredInvestmentAmountMin` | 偏好投資金額最小值 | DECIMAL | 40.0 | 記錄偏好投資金額最小值，通常為金額或資本數值。 | — |
| `PreferredInvestmentAmountMax` | 偏好投資金額Max | DECIMAL | 150.0 | 記錄偏好投資金額Max，通常為金額或資本數值。 | — |
| `PreferredDealSize` | 偏好交易規模 | TEXT(50) | 10.0 - 250.0 | 官方資料字典對此欄有說明；此欄主要記錄偏好交易規模。 | — |
| `PreferredDealSizeMin` | 偏好交易規模最小值 | DECIMAL | 10.0 | 官方資料字典對此欄有說明；此欄主要記錄偏好交易規模最小值。 | — |
| `PreferredDealSizeMax` | 偏好交易規模Max | DECIMAL | 250.0 | 官方資料字典對此欄有說明；此欄主要記錄偏好交易規模Max。 | — |
| `PreferredCompanyValuation` | 偏好公司估值 | TEXT(50) | 25.0 - 150.0 | 記錄偏好公司估值，通常為金額或資本數值。 | — |
| `PreferredCompanyValuationMin` | 偏好公司估值最小值 | DECIMAL | 25.0 | 官方資料字典對此欄有說明；此欄主要記錄偏好公司估值最小值。 | — |
| `PreferredCompanyValuationMax` | 偏好公司估值Max | DECIMAL | 150.0 | 官方資料字典對此欄有說明；此欄主要記錄偏好公司估值Max。 | — |
| `PreferredEBITDA` | 偏好EBITDA | TEXT(50) | > 2.0 | 記錄偏好EBITDA，通常為金額或資本數值。 | — |
| `PreferredEBITDAMin` | 偏好EBITDA最小值 | DECIMAL | 2.0 | 記錄偏好EBITDA最小值，通常為金額或資本數值。 | — |
| `PreferredEBITDAMax` | 偏好EBITDAMax | DECIMAL | 80.0 | 記錄偏好EBITDAMax，通常為金額或資本數值。 | — |
| `PreferredEBIT` | 偏好EBIT | TEXT(50) | 5.0 - 35.0 | 記錄偏好EBIT，通常為金額或資本數值。 | — |
| `PreferredEBITMin` | 偏好EBIT最小值 | DECIMAL | 5.0 | 記錄偏好EBIT最小值，通常為金額或資本數值。 | — |
| `PreferredEBITMax` | 偏好EBITMax | DECIMAL | 35.0 | 記錄偏好EBITMax，通常為金額或資本數值。 | — |
| `PreferredRevenue` | 偏好營收 | TEXT(50) | > 100.0 | 記錄偏好營收，通常為金額或資本數值。 | — |
| `PreferredRevenueMax` | 偏好營收Max | DECIMAL | 58.65799884 | 記錄偏好營收Max，通常為金額或資本數值。 | — |
| `PreferredRevenueMin` | 偏好營收最小值 | DECIMAL | 100.0 | 記錄偏好營收最小值，通常為金額或資本數值。 | — |
| `LastInvestmentSize` | 最近投資規模 | DECIMAL | 8.000023 | 官方資料字典對此欄有說明；此欄主要記錄最近投資規模。 | — |
| `LastInvestmentValuation` | 最近投資估值 | DECIMAL | 104.869303 | 官方資料字典對此欄有說明；此欄主要記錄最近投資估值。 | — |
| `LastFinancingDebtSize` | 最近融資債務規模 | DECIMAL | 85.0 | 記錄最近融資債務規模，通常為金額或資本數值。 | — |
| `LastFinancingDebt` | 最近融資債務 | TEXT | Revolving Credit; Term Loan (Term Loan) | 記錄最近融資債務，通常為金額或資本數值。 | — |
| `LastClosedFundSize` | 最近已關閉基金規模 | DECIMAL | 447.0 | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金規模。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Website` | 網站 | TEXT | us.gmocloud.com | 記錄網站。 | — |
| `HQLocation` | 總部地點 | TEXT(100) | Irvine, CA | 記錄總部地點相關地理資訊。 | — |
| `HQAddressLine1` | 總部地址第一行 | TEXT(100) | 5300 California Avenue | 官方資料字典對此欄有說明；此欄主要記錄總部地址第一行。 | — |
| `HQAddressLine2` | 總部地址第二行 | TEXT(100) | Suite 150 | 官方資料字典對此欄有說明；此欄主要記錄總部地址第二行。 | — |
| `HQCity` | 總部城市 | TEXT(100) | Irvine | 記錄總部城市相關地理資訊。 | — |
| `HQState_Province` | 總部州或省 | TEXT(100) | California | 記錄總部州或省相關地理資訊。 | — |
| `HQPostCode` | 總部郵遞區號 | TEXT(30) | 92617 | 官方資料字典對此欄有說明；此欄主要記錄總部郵遞區號。 | — |
| `HQCountry` | 總部國家 | TEXT(50) | United States | 記錄總部國家相關地理資訊。 | — |
| `HQPhone` | 總部電話 | TEXT(50) | +1 (212) 584-3200 | 官方資料字典對此欄有說明；此欄主要記錄總部電話。 | — |
| `HQFax` | 總部傳真 | TEXT(50) | +1 (212) 584-3233 | 官方資料字典對此欄有說明；此欄主要記錄總部傳真。 | — |
| `HQEmail` | 總部電子郵件 | TEXT(255) | contact@pearsfoundation.org.uk | 官方資料字典對此欄有說明；此欄主要記錄總部電子郵件。 | — |
| `HQGlobalRegion` | 總部全球Region | TEXT(100) | Americas | 記錄總部全球Region相關地理資訊。 | — |
| `HQGlobalSubRegion` | 總部全球SubRegion | TEXT(100) | North America | 官方資料字典對此欄有說明；此欄主要記錄總部全球SubRegion。 | — |
| `PrimaryContactEmail` | 主要聯絡人電子郵件 | TEXT(255) | tpears@pearsfoundation.org.uk | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人電子郵件。 | — |
| `PrimaryContactPhone` | 主要聯絡人電話 | TEXT(50) | +44 (0)20 7433 3333 | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人電話。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryContactPBId` | 主要聯絡人 PitchBook 識別碼 | TEXT(20) | 61626-43P | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人 PitchBook 識別碼。 | 通常可連到 Person.csv |
| `PrimaryContactMiddle` | 主要聯絡人中間名 | TEXT(200) | B. | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人中間名。 | — |
| `PrimaryContactPrefix` | 主要聯絡人前綴 | TEXT(50) | Mr. | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人前綴。 | — |
| `PrimaryContactSuffix` | 主要聯絡人後綴 | TEXT(50) | Ph.D | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人後綴。 | — |
| `PrimaryContact` | 主要聯絡人 | TEXT(255) | Trevor Pears | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人。 | — |
| `PrimaryContactTitle` | 主要聯絡人Title | TEXT | Co-Founder & Executive Chairman | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人Title。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ParentCompany` | 母公司名稱 | TEXT(255) | Ares Management | 記錄母公司名稱。 | — |
| `TotalExits` | 總Exits | INTEGER | 12 | 官方資料字典對此欄有說明；此欄主要記錄總Exits。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `TradeAssociations` | 交易Associations | TEXT | Principles for Responsible Investment (PRI) | 官方資料字典對此欄有說明；此欄主要記錄交易Associations。 | — |
| `PreferredIndustry` | 偏好產業 | TEXT | Semiconductors | 官方資料字典對此欄有說明；此欄主要記錄偏好產業。 | — |
| `PreferredVerticals` | 偏好垂直領域 | TEXT | TMT | 官方資料字典對此欄有說明；此欄主要記錄偏好垂直領域。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Description` | 描述 | TEXT | Broadcom was a designer, developer and global supplier of a broad range of analog and digital semiconductor connecti ... | 官方資料字典對此欄有說明；此欄主要記錄描述。 | — |
| `Exchange` | 交易所 | TEXT(10) | LON | 官方資料字典對此欄有說明；此欄主要記錄交易所。 | — |
| `Ticker` | 股票代碼 | TEXT(100) | STVG | 官方資料字典對此欄有說明；此欄主要記錄股票代碼。 | — |
| `InvestmentProfessionalCount` | 投資ProfessionalCount | INTEGER | 5 | 官方資料字典對此欄有說明；此欄主要記錄投資ProfessionalCount。 | — |
| `MostLikelyFundraisIng` | 最可能LikelyFundraisIng | TEXT(10) | No | 記錄最可能LikelyFundraisIng，用來描述當前狀態或標記。 | — |
| `AlternateOfficeCount` | Alternate辦公室Count | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄Alternate辦公室Count。 | — |
| `TotalActivePortfolio` | 總現有Portfolio | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總現有Portfolio。 | — |
| `TotalInvestments` | 總投資 | INTEGER | 63 | 官方資料字典對此欄有說明；此欄主要記錄總投資。 | — |
| `TotalInvestmentsInTheLast7Days` | 總投資TheLast7Days | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總投資TheLast7Days。 | — |
| `TotalInvestmentsInTheLast6Months` | 總投資TheLast6Months | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄總投資TheLast6Months。 | — |
| `TotalInvestmentsInTheLast12Months` | 總投資TheLast12Months | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總投資TheLast12Months。 | — |
| `TotalFundsOpen` | 總Funds開放 | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總Funds開放。 | — |
| `TotalFundsClosed` | 總Funds已關閉 | INTEGER | 5 | 官方資料字典對此欄有說明；此欄主要記錄總Funds已關閉。 | — |
| `TotalFundsClosedInTheLast6Months` | 總Funds已關閉TheLast6Months | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總Funds已關閉TheLast6Months。 | — |
| `TotalFundsClosedInTheLast12Months` | 總Funds已關閉TheLast12Months | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總Funds已關閉TheLast12Months。 | — |
| `PreferredInvestmentHorizon` | 偏好投資期限 | TEXT(50) | 3 - 5 | 記錄偏好投資期限，通常為金額或資本數值。 | — |
| `PreferredGeography` | 偏好地理偏好 | TEXT | North America, United States | 官方資料字典對此欄有說明；此欄主要記錄偏好地理偏好。 | — |
| `OtherInvestmentPreferences` | 其他投資Preferences | TEXT | Prefers majority stake | 官方資料字典對此欄有說明；此欄主要記錄其他投資Preferences。 | — |
| `LastInvestmentCompany` | 最近投資公司 | TEXT(255) | Elastics.cloud | 記錄最近投資公司。 | — |
| `PitchBookProfileLink` | PitchBook 頁面連結 | TEXT | https://content.pitchbook.com/profiles/investor/10010-89 | 官方資料字典對此欄有說明；此欄主要記錄PitchBook 頁面連結。 | — |


## InvestorAffiliateRelation.csv

**用途**：記錄投資機構的關聯實體資料。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`AffiliateID`

**可連接到**：可連到 Investor.csv；關聯實體鍵，本批資料未提供單獨主表；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 399415-78 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `AffiliateID` | 關聯實體識別碼 | TEXT(20) | 64287-19 | 唯一識別碼，用於記錄關聯實體識別碼。 | 關聯實體鍵，本批資料未提供單獨主表 |
| `RowID` | 列唯一識別碼 | TEXT(255) | d3dba987074d9efaf95981c1a373b064a82bbe0a3aee3947dfcd894f0d85965a | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AffiliateName` | 關聯實體名稱 | TEXT(255) | Meine Spielzeugkiste | 官方資料字典對此欄有說明；此欄主要記錄關聯實體名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AffiliateType` | 關聯實體類型 | TEXT(100) | Subsidiary | 官方資料字典對此欄有說明；此欄主要記錄關聯實體類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `YearFounded` | 年份成立 | INTEGER | 2012 | 官方資料字典對此欄有說明；此欄主要記錄年份成立。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `HQCity` | 總部城市 | TEXT(100) | Berlin | 記錄總部城市相關地理資訊。 | — |
| `HQState_Province` | 總部州或省 | TEXT(100) | New Brunswick | 記錄總部州或省相關地理資訊。 | — |
| `HQCountry` | 總部國家 | TEXT(50) | Germany | 記錄總部國家相關地理資訊。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Industry` | 產業 | TEXT(100) | Specialty Retail | 官方資料字典對此欄有說明；此欄主要記錄產業。 | — |


## InvestorCoInvestorRelation.csv

**用途**：記錄投資機構之間的共同投資關係。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`Co_InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `Co_InvestorID` | 共同投資機構識別碼 | TEXT(20) | 10134-73 | 唯一識別碼，用於記錄共同投資機構識別碼。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 1cd4d1ad896ce15b5dda044db68e567c42f05cb61e19de0d60b8e64e5d60a69b | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Co_InvestorName` | 共同投資機構名稱 | TEXT(255) | Bessemer Venture Partners | 記錄共同投資機構名稱。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `NumberOfInvestmentsWith` | 數量Of投資With | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄數量Of投資With。 | — |


## InvestorEntityTypeRelation.csv

**用途**：記錄投資機構的實體類型分類。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | f0da1140310c7ca38a77d9ef0a525b2e32fc36d8ca557308908288d1d7ebb001 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `EntityType` | 實體類型 | TEXT(255) | Investor | 官方資料字典對此欄有說明；此欄主要記錄實體類型。 | — |
| `IsPrimary` | Is主要 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Is主要。 | — |


## InvestorExitRelation.csv

**用途**：記錄投資機構的退出案例。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`CompanyID`、`DealID`

**可連接到**：可連到 Investor.csv；可連到 Company.csv；可連到 Deal.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10032-58 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10017-01 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10008-28T | 唯一識別碼，用於記錄交易唯一識別碼。 | 可連到 Deal.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 1252e71a71bd497ad249097f38e9b1c046cf47f0c56ef8d8ad265e9cc2cc1eda | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | AxleTech | 記錄公司名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ExitType` | 退出類型 | TEXT(100) | Buyout/LBO (Secondary) | 官方資料字典對此欄有說明；此欄主要記錄退出類型。 | — |
| `ExitStatus` | 退出狀態 | TEXT(50) | Completed | 記錄退出狀態，用來描述當前狀態或標記。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ExitDate` | 退出日期 | DATE | 10/03/2005 | 官方資料字典對此欄有說明；此欄主要記錄退出日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ExitSize` | 退出規模 | DECIMAL | 345.0 | 官方資料字典對此欄有說明；此欄主要記錄退出規模。 | — |


## InvestorFundRelation.csv

**用途**：記錄投資機構與其他主題之間的關聯資料。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`FundID`

**可連接到**：可連到 Investor.csv；可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10011-79 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 10909-00F | 唯一識別碼，用於記錄基金唯一識別碼。 | 可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | c5c9f0e9efec7be994ded70e83b334ba1905910b747ec300325a9beeb2e14688 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 05/30/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundName` | 基金名稱 | TEXT(255) | Charterhouse Equity Partners IV | 記錄基金名稱。 | — |


## InvestorInvestDealRelation.csv

**用途**：按交易類型彙總投資機構的投資統計。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10026-64 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 5bf01541798f1440578b1b6f551ff1e75c79b4376b33974792c17608eacdfcb6 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 05/30/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealType` | 交易類型 | TEXT(50) | Grants | 官方資料字典對此欄有說明；此欄主要記錄交易類型。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `MedianSize` | 中位數規模 | DECIMAL | 0.11 | 官方資料字典對此欄有說明；此欄主要記錄中位數規模。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Deals` | Deals | INTEGER | 4556 | 官方資料字典對此欄有說明；此欄主要記錄Deals。 | — |
| `LastInvestment` | 最近投資 | DATE | 10/09/2023 | 記錄最近投資相關日期。 | — |


## InvestorInvestIndustryCodeRelation.csv

**用途**：按產業代碼彙總投資機構的投資統計。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 57660-04 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | d1f035638d00da9404e57dbaa25c05f2e5b58bc8682c7a0ef8fabe35334bbf23 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 03/05/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PercentageOfDeals` | 百分比OfDeals | DECIMAL | 31.25 | 記錄百分比OfDeals，通常為比例或比率。 | — |
| `MedianSize` | 中位數規模 | DECIMAL | 4.17020354 | 官方資料字典對此欄有說明；此欄主要記錄中位數規模。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `IndustrySector` | 產業部門 | TEXT(255) | Business Products and Services (B2B) | 官方資料字典對此欄有說明；此欄主要記錄產業部門。 | — |
| `IndustryGroup` | 產業群組 | TEXT(255) | Commercial Products | 官方資料字典對此欄有說明；此欄主要記錄產業群組。 | — |
| `IndustryCode` | 產業代碼 | TEXT(255) | Building Products | 官方資料字典對此欄有說明；此欄主要記錄產業代碼。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Deals` | Deals | INTEGER | 5 | 官方資料字典對此欄有說明；此欄主要記錄Deals。 | — |
| `LastInvestment` | 最近投資 | DATE | 10/12/2018 | 記錄最近投資相關日期。 | — |


## InvestorInvestIndustrySectorCodeRelation.csv

**用途**：按產業部門彙總投資機構的投資統計。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10565-92 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | a5f9577ceeaafabcf03348770140e9a4d1dbd71e902a3c84359f5a4f146dcf42 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `MedianSize` | 中位數規模 | DECIMAL | 65.81277357 | 官方資料字典對此欄有說明；此欄主要記錄中位數規模。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Industry` | 產業 | TEXT(255) | Healthcare | 官方資料字典對此欄有說明；此欄主要記錄產業。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Deals` | Deals | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄Deals。 | — |
| `LastInvestment` | 最近投資 | DATE | 05/03/2024 | 記錄最近投資相關日期。 | — |


## InvestorInvestYearRelation.csv

**用途**：按年份彙總投資機構的投資統計。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 529617-97 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | fdb89b2b8a7d82a39aa34f6c4bf4c1718e7e44db4c4c1690cc235b2aaa362544 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 04/16/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Year` | 年份 | INTEGER | 2024 | 記錄年份相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `MedianSize` | 中位數規模 | DECIMAL | 65.98305775 | 官方資料字典對此欄有說明；此欄主要記錄中位數規模。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Deals` | Deals | INTEGER | 3 | 官方資料字典對此欄有說明；此欄主要記錄Deals。 | — |
| `LastInvestment` | 最近投資 | DATE | 07/01/2024 | 記錄最近投資相關日期。 | — |


## InvestorInvestmentRelation.csv

**用途**：記錄投資機構的投資明細。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`CompanyID`、`DealID`、`ExitDealID`、`LeadPartnerID`

**可連接到**：可連到 Investor.csv；可連到 Company.csv；可連到 Deal.csv；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10012-69 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 61086-88 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 33368-23T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `ExitDealID` | 退出交易識別碼 | TEXT(20) | 98708-41T | 唯一識別碼，用於記錄退出交易識別碼。 | 可連到 Deal.csv |
| `LeadPartnerID` | 主導合夥人識別碼 | TEXT(20) | 11514-97P | 唯一識別碼，用於記錄主導合夥人識別碼。 | 通常可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | a869e3975a2922be2c734dc49fb9e9777b1613a2f324f9c70811e911035ef824 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 03/07/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Torres Unidas Management | 記錄公司名稱。 | — |
| `LeadPartnerName` | 主導合夥人姓名 | TEXT(125) | Ross Jones | 官方資料字典對此欄有說明；此欄主要記錄主導合夥人姓名。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealType` | 交易類型 | TEXT(20) | Buyout/LBO | 記錄交易類型，通常為金額或資本數值。 | — |
| `BusinessStatus` | 業務狀態 | TEXT(50) | Generating Revenue | 官方資料字典對此欄有說明；此欄主要記錄業務狀態。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 09/01/2012 | 記錄交易完成日期相關日期。 | — |
| `TargetCompanyExitDate` | 目標公司退出日期 | DATE | 12/14/2017 | 記錄目標公司退出日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealSize` | 交易規模 | DECIMAL | 2.297267 | 記錄交易規模，通常為金額或資本數值。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CoInvestors` | 共同Investors | INTEGER | 8 | 官方資料字典對此欄有說明；此欄主要記錄共同Investors。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Industry` | 產業 | TEXT(100) | Telecommunications Service Providers | 官方資料字典對此欄有說明；此欄主要記錄產業。 | — |


## InvestorLeadPartnerRelation.csv

**用途**：記錄投資機構與 lead partner 的關聯。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`PersonID`

**可連接到**：可連到 Investor.csv；可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10074-61 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `PersonID` | 人物唯一識別碼 | TEXT(20) | 15227-83P | 唯一識別碼，用於記錄人物唯一識別碼。 | 可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 89c9bfef317f33c1b050143f2f384ccf2d1a5bd9d74640dbdef81fb84974a2e5 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/01/2026 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FullName` | 完整姓名 | TEXT(125) | Cary Davis | 官方資料字典對此欄有說明；此欄主要記錄完整姓名。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Location` | 地點 | TEXT(100) | New York, NY | 記錄地點相關地理資訊。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AllDeals` | 全部Deals | INTEGER | 35 | 官方資料字典對此欄有說明；此欄主要記錄全部Deals。 | — |


## InvestorLimitedPartnerRelation.csv

**用途**：記錄投資機構與有限合夥人的關聯。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`LimitedPartnerID`

**可連接到**：可連到 Investor.csv；可連到 LimitedPartner.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10013-32 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 52030-90 | 唯一識別碼，用於記錄有限合夥人唯一識別碼。 | 可連到 LimitedPartner.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | ee197e1af0cdad5476b17f16d1574880fa681f3811814a4aa5e8cebae534153e | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 09/13/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerName` | 有限合夥人名稱 | TEXT(255) | Bowling Green State University Endowment | 記錄有限合夥人名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Type` | 類型 | TEXT(100) | Endowment | 記錄類型，通常為比例或比率。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LastCommitmentDate` | 最近Commitment日期 | DATE | 03/03/2025 | 記錄最近Commitment日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CommitmentsTo` | Commitments | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄Commitments。 | — |
| `TotalCommitments` | 總Commitments | INTEGER | 40 | 官方資料字典對此欄有說明；此欄主要記錄總Commitments。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerLocation` | 有限合夥人地點 | TEXT(100) | Bowling Green, OH | 記錄有限合夥人地點相關地理資訊。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LastCommitedFund` | 最近Commited基金 | TEXT(255) | ICG Strategic Equity Fund V | 官方資料字典對此欄有說明；此欄主要記錄最近Commited基金。 | — |


## InvestorLocationRelation.csv

**用途**：記錄投資機構的地點與辦公室資訊。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`

**可連接到**：可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10011-25 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 5738d185aaf1a29dbed1996f050b83cc09df8fc1360fe068ac44ff305cd4c0ff | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LocationName` | 地點名稱 | TEXT(100) | Richardson | 記錄地點名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LocationType` | 地點類型 | TEXT(100) | Primary HQ | 官方資料字典對此欄有說明；此欄主要記錄地點類型。 | — |
| `LocationStatus` | 地點狀態 | TEXT(100) | Current | 記錄地點狀態，用來描述當前狀態或標記。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Address1` | Address1 | TEXT(100) | 3101 East George Bush Highway | 官方資料字典對此欄有說明；此欄主要記錄Address1。 | — |
| `Address2` | Address2 | TEXT(100) | Suite 200 | 官方資料字典對此欄有說明；此欄主要記錄Address2。 | — |
| `City` | 城市 | TEXT(100) | Richardson | 記錄城市相關地理資訊。 | — |
| `State` | 州 | TEXT(100) | Texas | 記錄州相關地理資訊。 | — |
| `PostCode` | 郵遞代碼 | TEXT(30) | 75082 | 官方資料字典對此欄有說明；此欄主要記錄郵遞代碼。 | — |
| `Country` | 國家 | TEXT(50) | United States | 記錄國家相關地理資訊。 | — |
| `OfficePhone` | 辦公室電話 | TEXT(50) | +1 (972) 578-2000 | 官方資料字典對此欄有說明；此欄主要記錄辦公室電話。 | — |
| `OfficeFax` | 辦公室傳真 | TEXT(50) | +1 (972) 424-7493 | 官方資料字典對此欄有說明；此欄主要記錄辦公室傳真。 | — |


## InvestorServiceProviderRelation.csv

**用途**：記錄投資機構關聯的服務機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`InvestorID`、`ServiceProviderID`

**可連接到**：可連到 Investor.csv；可連到 ServiceProvider.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10019-71 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Investor.csv |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10302-40 | 唯一識別碼，用於記錄服務機構唯一識別碼。 | 可連到 ServiceProvider.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 54f4886fa219d03734b0de4494ebb6ebbf906c6e3711cf4d661217161bd524ff | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderName` | 服務機構名稱 | TEXT(255) | Bartlit Beck | 官方資料字典對此欄有說明；此欄主要記錄服務機構名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderType` | 服務機構類型 | TEXT(255) | Law Firm | 官方資料字典對此欄有說明；此欄主要記錄服務機構類型。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(50) | Legal Advisor | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |
