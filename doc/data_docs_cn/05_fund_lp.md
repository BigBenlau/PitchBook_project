# 基金與 LP 資料

本文件依主題整理正式 CSV，說明每個表的用途、關聯鍵與欄位分組。

## Fund.csv

**用途**：基金主表，記錄基金規模、募集狀態、偏好策略與乾粉資訊。

**主鍵**：`FundID`

**主要關聯鍵**：無明顯外鍵，或主要以本表欄位自身描述。

**可連接到**：可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 10909-00F | 此表主鍵，用於唯一識別單筆基金唯一識別碼。 | 可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | daef22ed9720487f6e71b56cf57835e11a7d8effc25b481d3dd2b7aad04ddf67 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 07/13/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundName` | 基金名稱 | TEXT(200) | Charterhouse Equity Partners IV | 記錄基金名稱。 | — |
| `FundFormerName` | 基金曾用名稱 | TEXT(500) | Bear Stearns Merchant Banking Partners II | 官方資料字典對此欄有說明；此欄主要記錄基金曾用名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundStatus` | 基金狀態 | TEXT(100) | Liquidated | 官方資料字典對此欄有說明；此欄主要記錄基金狀態。 | — |
| `FundCategory` | 基金類別 | TEXT(100) | Private Equity | 記錄基金類別，通常為金額或資本數值。 | — |
| `FundType` | 基金類型 | TEXT(100) | Buyout | 官方資料字典對此欄有說明；此欄主要記錄基金類型。 | — |
| `PreferredInvestmentTypes` | 偏好投資Types | TEXT | Acquisition Financing, Add-on, Buyout/LBO, Merger/Acquisition, PE Growth/Expansion | 官方資料字典對此欄有說明；此欄主要記錄偏好投資Types。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Vintage` | Vintage | INTEGER | 2005 | 記錄Vintage相關日期。 | — |
| `CloseDate` | 募集完成日期 | DATE | 12/31/2003 | 記錄募集完成日期相關日期。 | — |
| `OpenDate` | 開放日期 | DATE | 05/02/2003 | 記錄開放日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundSize` | 基金規模 | DECIMAL | 447.0 | 記錄基金規模，通常為金額或資本數值。 | — |
| `NativeFundSize` | 原幣基金規模 | DECIMAL | 447.0 | 記錄原幣基金規模，通常為金額或資本數值。 | — |
| `FundSizeGroup` | 基金規模群組 | TEXT(100) | 250M - 499M | 官方資料字典對此欄有說明；此欄主要記錄基金規模群組。 | — |
| `FundTargetSizeLow` | 基金目標規模Low | DECIMAL | 320 | 記錄基金目標規模Low，通常為金額或資本數值。 | — |
| `FundTargetSizeHigh` | 基金目標規模上限 | DECIMAL | 27288.66 | 記錄基金目標規模上限，通常為金額或資本數值。 | — |
| `FundTargetSize` | 基金目標規模 | TEXT(100) | > 320 | 官方資料字典對此欄有說明；此欄主要記錄基金目標規模。 | — |
| `PreferredInvestmentAmount` | 偏好投資金額 | TEXT(50) | 10.0 - 30.0 | 記錄偏好投資金額，通常為金額或資本數值。 | — |
| `PreferredDealSize` | 偏好交易規模 | TEXT(50) | 15.0 - 50.0 | 記錄偏好交易規模，通常為金額或資本數值。 | — |
| `PreferredCompanyValuation` | 偏好公司估值 | TEXT(50) | 250.0 - 1000.0 | 記錄偏好公司估值，通常為金額或資本數值。 | — |
| `PreferredEBITDA` | 偏好EBITDA | TEXT(50) | < 70.0 | 記錄偏好EBITDA，通常為金額或資本數值。 | — |
| `PreferredEBIT` | 偏好EBIT | TEXT(50) | 前 5000 行未見非空值 | 記錄偏好EBIT，通常為金額或資本數值。 | — |
| `PreferredRevenue` | 偏好營收 | TEXT(50) | 100.0 - 500.0 | 記錄偏好營收，通常為金額或資本數值。 | — |
| `DryPowder` | 乾粉資金 | TEXT | 0.0 | 依欄位名推定，此欄記錄乾粉資金。 | 推定欄位說明 |
| `DryPowderPercent` | 乾粉資金百分比 | DECIMAL | 0.0 | 依欄位名推定，此欄記錄乾粉資金百分比。 | 推定欄位說明 |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorWebsite` | 投資機構網站 | TEXT | Charterhouse Equity Partners (www.charterhouseequity.com) | 記錄投資機構網站。 | — |
| `Domiciles` | 註冊地 | TEXT | United States: Delaware | 記錄註冊地，通常為比例或比率。 | — |
| `FundLocation` | 基金地點 | TEXT(100) | Summit, NJ | 記錄基金地點相關地理資訊。 | — |
| `FundCity` | 基金城市 | TEXT(100) | Summit | 記錄基金城市相關地理資訊。 | — |
| `FundState_Province` | 基金州Province | TEXT(100) | New Jersey | 記錄基金州Province相關地理資訊。 | — |
| `FundCountry` | 基金國家 | TEXT(50) | United States | 記錄基金國家相關地理資訊。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PreferredIndustry` | 偏好產業 | TEXT | Business Products and Services (B2B), Consumer Products and Services (B2C), Energy, Financial Services, Healthcare,  ... | 官方資料字典對此欄有說明；此欄主要記錄偏好產業。 | — |
| `PreferredVerticals` | 偏好垂直領域 | TEXT | TMT | 官方資料字典對此欄有說明；此欄主要記錄偏好垂直領域。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundNo` | 基金序號 | TEXT | 5 | 官方資料字典對此欄有說明；此欄主要記錄基金序號。 | — |
| `FirstFund` | 首次基金 | TEXT | Yes (Ares Management) | 官方資料字典對此欄有說明；此欄主要記錄首次基金。 | — |
| `Investor` | 投資機構 | TEXT | Charterhouse Equity Partners | 官方資料字典對此欄有說明；此欄主要記錄投資機構。 | — |
| `NativeFundCurrency` | 原幣基金Currency | TEXT | USD | 官方資料字典對此欄有說明；此欄主要記錄原幣基金Currency。 | — |
| `FundAccessPoint` | 基金AccessPoint | TEXT(100) | Primary Fund | 官方資料字典對此欄有說明；此欄主要記錄基金AccessPoint。 | — |
| `SBICFund` | SBIC基金 | TEXT(50) | No | 記錄SBIC基金，通常為金額或資本數值。 | — |
| `TimeTakenToCloseFund` | 時間Taken關閉基金 | TEXT | 243 days | 官方資料字典對此欄有說明；此欄主要記錄時間Taken關閉基金。 | — |
| `FundFamily` | 基金家族 | TEXT | Charterhouse Equity Partners | 官方資料字典對此欄有說明；此欄主要記錄基金家族。 | — |
| `AdditionalNotes` | Additional備註 | TEXT | Charterhouse Equity Partners IV was a 2005 vintage buyout fund, managed by Charterhouse Equity Partners. The fund wa ... | 記錄Additional備註。 | — |
| `TotalFundInvestments` | 總基金投資 | INTEGER | 47 | 官方資料字典對此欄有說明；此欄主要記錄總基金投資。 | — |
| `TotalActiveFundInvestments` | 總現有基金投資 | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總現有基金投資。 | — |
| `PreferredGeography` | 偏好地理偏好 | TEXT | Midwest, Northeast, South, Southwest, United Kingdom, United States | 官方資料字典對此欄有說明；此欄主要記錄偏好地理偏好。 | — |
| `OtherInvestmentPreferences` | 其他投資Preferences | TEXT | Will lead on a deal | 官方資料字典對此欄有說明；此欄主要記錄其他投資Preferences。 | — |
| `PreferredInvestmentHorizon` | 偏好投資期限 | TEXT(50) | 3 - 7 | 記錄偏好投資期限，通常為金額或資本數值。 | — |


## FundCloseHistoryRelation.csv

**用途**：記錄基金歷次 closing / close 歷史。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`

**可連接到**：可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 10910-98F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 3d637ef3b036491678231390df1ba9aba65d005b455df6c81da74ad3b05757a0 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundCloseType` | 基金關閉類型 | TEXT | Final Close | 官方資料字典對此欄有說明；此欄主要記錄基金關閉類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundCloseDate` | 基金關閉日期 | DATE | 09/23/2003 | 記錄基金關閉日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Amount` | 金額 | TEXT | 1600.0 | 記錄金額，通常為金額或資本數值。 | — |


## FundInvestmentRelation.csv

**用途**：記錄基金的投資明細。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`CompanyID`、`DealID`、`ExitDealID`、`LeadPartnerID`

**可連接到**：可連到 Fund.csv；可連到 Company.csv；可連到 Deal.csv；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 10912-33F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10496-53 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 10263-43T | 唯一識別碼，用於記錄交易唯一識別碼。 | 可連到 Deal.csv |
| `ExitDealID` | 退出交易識別碼 | TEXT(20) | 85351-78T | 官方資料字典對此欄有說明；此欄主要記錄退出交易識別碼。 | 可連到 Deal.csv |
| `LeadPartnerID` | 主導合夥人識別碼 | TEXT(20) | 11357-92P | 唯一識別碼，用於記錄主導合夥人識別碼。 | 通常可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 729ec894358d9d66ab0123f1818381b6698f81ebf3f9d9ecf82239670a9b1af2 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Arrival Communications | 記錄公司名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestmentStatus` | 投資狀態 | TEXT(50) | Former Investment | 記錄投資狀態，用來描述當前狀態或標記。 | — |
| `DealType` | 交易類型 | TEXT(50) | Seed Round | 官方資料字典對此欄有說明；此欄主要記錄交易類型。 | — |
| `BusinessStatus` | 業務狀態 | TEXT(50) | Generating Revenue | 官方資料字典對此欄有說明；此欄主要記錄業務狀態。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 01/01/2000 | 記錄交易完成日期相關日期。 | — |
| `TargetCompanyExitDate` | 目標公司退出日期 | DATE | 03/21/2017 | 記錄目標公司退出日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealSize` | 交易規模 | DECIMAL | 12.5 | 官方資料字典對此欄有說明；此欄主要記錄交易規模。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LeadPartner` | 主導合夥人姓名 | TEXT | Thomas Dircks | 記錄主導合夥人姓名。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryIndustryCode` | 主要產業代碼 | TEXT(100) | Telecommunications Service Providers | 官方資料字典對此欄有說明；此欄主要記錄主要產業代碼。 | — |


## FundInvestorRelation.csv

**用途**：記錄基金關聯的投資機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`InvestorID`

**可連接到**：可連到 Fund.csv；可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 10909-00F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10011-79 | 唯一識別碼，用於記錄投資機構唯一識別碼。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 3c195f17bf1212489e8af62898ae9b1cf60a0738fc2e046806176e12a30c4ce9 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorName` | 投資機構名稱 | TEXT(255) | Charterhouse Equity Partners | 記錄投資機構名稱。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorWebsite` | 投資機構網站 | TEXT | www.charterhouseequity.com | 記錄投資機構網站。 | — |


## FundLPCommitmentRelation.csv

**用途**：記錄基金與 LP 的承諾出資。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`LimitedPartnerID`、`CommitmentID`

**可連接到**：可連到 Fund.csv；可連到 LimitedPartner.csv；承諾出資鍵，本批資料未提供單獨主表；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 12067-57F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 10019-17 | 唯一識別碼，用於記錄有限合夥人唯一識別碼。 | 可連到 LimitedPartner.csv |
| `CommitmentID` | 承諾出資識別碼 | TEXT(20) | 11298-70C | 官方資料字典對此欄有說明；此欄主要記錄承諾出資識別碼。 | 承諾出資鍵，本批資料未提供單獨主表 |
| `RowID` | 列唯一識別碼 | TEXT(255) | e47bffa6ef3c112fc782c77c032622a50fd19297f442478c563bf20cde0deaeb | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 11/02/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerName` | 有限合夥人名稱 | TEXT(255) | Apax Partners | 記錄有限合夥人名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerType` | 有限合夥人類型 | TEXT(100) | Direct Investment | 記錄有限合夥人類型，通常為比例或比率。 | — |
| `CommitmentStatus` | Commitment狀態 | TEXT(100) | Current | 記錄Commitment狀態，用來描述當前狀態或標記。 | — |
| `CommitmentType` | Commitment類型 | TEXT | Original | 官方資料字典對此欄有說明；此欄主要記錄Commitment類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CommitmentDate` | Commitment日期 | DATE | 04/21/2011 | 記錄Commitment日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Commitment` | 承諾出資額 | DECIMAL | 500.00 | 記錄承諾出資額，通常為金額或資本數值。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Comments` | 備註說明 | TEXT | Charles Wollmann | 官方資料字典對此欄有說明；此欄主要記錄備註說明。 | — |


## FundLimitedPartnerRelation.csv

**用途**：記錄基金與有限合夥人的關聯。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`LimitedPartnerID`

**可連接到**：可連到 Fund.csv；可連到 LimitedPartner.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 15898-96F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 10768-06 | 唯一識別碼，用於記錄有限合夥人唯一識別碼。 | 可連到 LimitedPartner.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 69eaada35b2756bb18e9c90031b15eb5af5baca031581a5299b0843c3f95cecc | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 03/28/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerName` | 有限合夥人名稱 | TEXT(255) | BlackRock | 記錄有限合夥人名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerType` | 有限合夥人類型 | TEXT(100) | Money Management Firm | 記錄有限合夥人類型，通常為比例或比率。 | — |


## FundReturnRelation.csv

**用途**：記錄基金回報時間序列。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`

**可連接到**：可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 11354-14F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | d1197ebd7a8c3f2cce9ecabc9ef807d9b16fce687fc3f31309771858e4e34886 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 01/21/2026 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AsOfYear` | Of年份 | INTEGER | 2021 | 記錄Of年份相關日期。 | — |
| `AsOfQuarter` | Of季度 | TEXT(20) | 4Q | 官方資料字典對此欄有說明；此欄主要記錄Of季度。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `IRR` | 內部報酬率 IRR | DECIMAL | 13.65 | 記錄內部報酬率 IRR，通常為比例或比率。 | — |
| `DPI` | DPI 倍數 | DECIMAL | 1.76417 | 記錄DPI 倍數，通常為金額或資本數值。 | — |
| `TVPI` | TVPI 倍數 | DECIMAL | 1.8376 | 記錄TVPI 倍數，通常為金額或資本數值。 | — |
| `RVPI` | RVPI 倍數 | DECIMAL | 0.07343 | 官方資料字典對此欄有說明；此欄主要記錄RVPI 倍數。 | — |
| `CalledDownPercentage` | 已提取下降百分比 | DECIMAL | 99.405 | 記錄已提取下降百分比，通常為金額或資本數值。 | — |
| `DryPowder` | 乾粉資金 | DECIMAL | 81.62571901 | 記錄乾粉資金，通常為金額或資本數值。 | — |
| `DryPowderPercentage` | 乾粉資金百分比 | DECIMAL | 0.595 | 記錄乾粉資金百分比，通常為金額或資本數值。 | — |
| `NAV` | 資產淨值 NAV | DECIMAL | 1001.50572254 | 官方資料字典對此欄有說明；此欄主要記錄資產淨值 NAV。 | — |
| `DistributedPlusNAV` | 已分配PlusNAV | DECIMAL | 25061.93160054 | 官方資料字典對此欄有說明；此欄主要記錄已分配PlusNAV。 | — |
| `IRRDifferenceFromBenchmark` | IRRDifferenceFromBenchmark | DECIMAL | 0.4 | 記錄IRRDifferenceFromBenchmark，通常為比例或比率。 | — |
| `DPIDifferenceFromBenchmark` | DPIDifferenceFromBenchmark | DECIMAL | 0.05273 | 記錄DPIDifferenceFromBenchmark，通常為比例或比率。 | — |
| `RVPIDifferenceFromBenchmark` | RVPIDifferenceFromBenchmark | DECIMAL | 0.027725 | 記錄RVPIDifferenceFromBenchmark，通常為比例或比率。 | — |
| `TVPIDifferenceFromBenchmark` | TVPIDifferenceFromBenchmark | DECIMAL | 0.029525 | 記錄TVPIDifferenceFromBenchmark，通常為比例或比率。 | — |
| `IRRBenchmark` | IRRBenchmark | DECIMAL | 13.25 | 記錄IRRBenchmark，通常為比例或比率。 | — |
| `DPIBenchmark` | DPIBenchmark | DECIMAL | 1.71144 | 官方資料字典對此欄有說明；此欄主要記錄DPIBenchmark。 | — |
| `TVPIBenchmark` | TVPIBenchmark | DECIMAL | 1.808075 | 官方資料字典對此欄有說明；此欄主要記錄TVPIBenchmark。 | — |
| `RVPIBenchmark` | RVPIBenchmark | DECIMAL | 0.045705 | 官方資料字典對此欄有說明；此欄主要記錄RVPIBenchmark。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `GainSinceInception` | 收益自Inception | DECIMAL | 11423.55731955 | 官方資料字典對此欄有說明；此欄主要記錄收益自Inception。 | — |
| `Contributed` | Contributed | DECIMAL | 13638.37428099 | 記錄Contributed，通常為金額或資本數值。 | — |
| `Distributed` | 已分配 | DECIMAL | 24060.425878 | 記錄已分配，通常為金額或資本數值。 | — |
| `Sources` | Sources | TEXT | Alaska Retirement Management Board, American International Group Retirement Plan, Florida State Board of Administrat ... | 官方資料字典對此欄有說明；此欄主要記錄Sources。 | — |
| `Quartile` | Quartile | TEXT(20) | 2 (Upper-Mid) | 官方資料字典對此欄有說明；此欄主要記錄Quartile。 | — |


## FundReturnReporterRelation.csv

**用途**：記錄基金回報數據與回報來源。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`SourceID`、`CommitmentID`

**可連接到**：可連到 Fund.csv；來源鍵，本批資料未提供單獨主表；承諾出資鍵，本批資料未提供單獨主表；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 11340-64F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `SourceID` | 來源識別碼 | TEXT(20) | 11604-43 | 官方資料字典對此欄有說明；此欄主要記錄來源識別碼。 | 來源鍵，本批資料未提供單獨主表 |
| `CommitmentID` | 承諾出資識別碼 | TEXT(20) | 14269-33C | 官方資料字典對此欄有說明；此欄主要記錄承諾出資識別碼。 | 承諾出資鍵，本批資料未提供單獨主表 |
| `RowID` | 列唯一識別碼 | TEXT(255) | fb2adfa441e1ce2e10c273c72ed675d998c3c071fe2270c6b392e2447821828b | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 06/28/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SourceType` | 來源類型 | TEXT | LP | 官方資料字典對此欄有說明；此欄主要記錄來源類型。 | — |
| `CommitmentType` | Commitment類型 | TEXT | Original | 官方資料字典對此欄有說明；此欄主要記錄Commitment類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ReportingPeriod` | 回報期間 | TEXT(20) | 3Q2022 | 官方資料字典對此欄有說明；此欄主要記錄回報期間。 | — |
| `AsOfYear` | Of年份 | INTEGER | 2022 | 記錄Of年份相關日期。 | — |
| `AsOfQuarter` | Of季度 | TEXT(20) | 3Q | 官方資料字典對此欄有說明；此欄主要記錄Of季度。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `NAV` | 資產淨值 NAV | DECIMAL | 0.184446 | 官方資料字典對此欄有說明；此欄主要記錄資產淨值 NAV。 | — |
| `IRR` | 內部報酬率 IRR | DECIMAL | 4.19 | 記錄內部報酬率 IRR，通常為比例或比率。 | — |
| `DPI` | DPI 倍數 | DECIMAL | 1.54 | 記錄DPI 倍數，通常為金額或資本數值。 | — |
| `TVPI` | TVPI 倍數 | DECIMAL | 1.55 | 記錄TVPI 倍數，通常為金額或資本數值。 | — |
| `RVPI` | RVPI 倍數 | DECIMAL | 0.01 | 官方資料字典對此欄有說明；此欄主要記錄RVPI 倍數。 | — |
| `NativeNAV` | 原幣NAV | DECIMAL | 0.184446 | 官方資料字典對此欄有說明；此欄主要記錄原幣NAV。 | — |
| `NativeDryPowder` | 原幣乾粉資金 | DECIMAL | 0.680441 | 記錄原幣乾粉資金，通常為金額或資本數值。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Distributed` | 已分配 | DECIMAL | 22.025473 | 記錄已分配，通常為金額或資本數值。 | — |
| `Contributed` | Contributed | DECIMAL | 14.319559 | 記錄Contributed，通常為金額或資本數值。 | — |
| `NativeCommitted` | 原幣Committed | DECIMAL | 15.0 | 記錄原幣Committed，通常為金額或資本數值。 | — |
| `NativeContributed` | 原幣Contributed | DECIMAL | 14.319559 | 記錄原幣Contributed，通常為金額或資本數值。 | — |
| `NativeDistributed` | 原幣已分配 | DECIMAL | 22.025473 | 記錄原幣已分配，通常為金額或資本數值。 | — |
| `NativeCurrency` | 原幣Currency | TEXT(10) | USD | 官方資料字典對此欄有說明；此欄主要記錄原幣Currency。 | — |
| `Source` | 來源 | TEXT | Seattle City Employees' Retirement System | 官方資料字典對此欄有說明；此欄主要記錄來源。 | — |
| `IndividualLPCommitted` | IndividualLPCommitted | DECIMAL | 15.0 | 記錄IndividualLPCommitted，通常為金額或資本數值。 | — |
| `ReportingCurrency` | 回報Currency | TEXT(10) | USD | 官方資料字典對此欄有說明；此欄主要記錄回報Currency。 | — |


## FundServiceProviderRelation.csv

**用途**：記錄基金關聯的服務機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`ServiceProviderID`、`ServiceToID`

**可連接到**：可連到 Fund.csv；可連到 ServiceProvider.csv；服務對象鍵，可能對應公司、基金、投資機構等；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 22469-50F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10076-68 | 唯一識別碼，用於記錄服務機構唯一識別碼。 | 可連到 ServiceProvider.csv |
| `ServiceToID` | 服務識別碼 | TEXT(50) | 224162-56 | 唯一識別碼，用於記錄服務識別碼。 | 服務對象鍵，可能對應公司、基金、投資機構等 |
| `RowID` | 列唯一識別碼 | TEXT(255) | 8763799c4d05c5d5301cd1730279443f9de8eed0ebde1e5a6d76c7ac37cb6bf8 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 03/28/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderName` | 服務機構名稱 | TEXT(255) | Hogan Lovells | 記錄服務機構名稱。 | — |
| `ServiceToName` | 服務名稱 | TEXT(255) | SC Lowy | 記錄服務名稱。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceTo` | 服務 | TEXT(255) | Investor | 官方資料字典對此欄有說明；此欄主要記錄服務。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(50) | Legal Advisor | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |
| `Comments` | 備註說明 | TEXT | Contact: James Wood | 官方資料字典對此欄有說明；此欄主要記錄備註說明。 | — |


## FundTeamRelation.csv

**用途**：記錄基金團隊資料。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`FundID`、`PersonID`

**可連接到**：可連到 Fund.csv；可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 10909-00F | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Fund.csv |
| `PersonID` | 人物唯一識別碼 | TEXT(20) | 11357-92P | 唯一識別碼，用於記錄人物唯一識別碼。 | 可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | b890f20aa74dd3c0fa03b927dbf3ece152819004cbbcf1f9e50fd19dfd9ebc0e | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 07/11/2024 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FullName` | 完整姓名 | TEXT(125) | Thomas Dircks | 官方資料字典對此欄有說明；此欄主要記錄完整姓名。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `IsCurrent` | Is當前 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Is當前。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Location` | 地點 | TEXT | Summit, NJ | 記錄地點相關地理資訊。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FullTitle` | 完整職稱 | TEXT | Managing Director | 官方資料字典對此欄有說明；此欄主要記錄完整職稱。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AffiliatedDeals` | 關聯Deals | INTEGER | 21 | 官方資料字典對此欄有說明；此欄主要記錄關聯Deals。 | — |
| `AffiliatedFunds` | 關聯Funds | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄關聯Funds。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ActiveBoardSeats` | 現有董事會Seats | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄現有董事會Seats。 | — |


## LPDirectInvestmentRelation.csv

**用途**：記錄 LP 的直接投資。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`LimitedPartnerID`、`CompanyID`

**可連接到**：可連到 LimitedPartner.csv；可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 10474-93 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 LimitedPartner.csv |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10397-08 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 0c556d6c8d4b9889eb07fd700c711c6fbb7e06945caf5ab36dbf1f4d66d68d2e | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 03/07/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT | Laureate Education | 記錄公司名稱。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 07/20/2007 | 記錄交易完成日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealSize` | 交易規模 | DECIMAL | 2100.0 | 記錄交易規模，通常為金額或資本數值。 | — |


## LPFundCommitmentRelation.csv

**用途**：記錄 LP 對基金的承諾出資。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`LimitedPartnerID`、`FundID`

**可連接到**：可連到 LimitedPartner.csv；可連到 Fund.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 10019-17 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 LimitedPartner.csv |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 12067-57F | 唯一識別碼，用於記錄基金唯一識別碼。 | 可連到 Fund.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 5d957c6c87653a7e0a63a2e19379b9ae5fa56e9de5a497241da8fe05dfa9e989 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundName` | 基金名稱 | TEXT(255) | Bridges Social Entrepreneurs Fund | 記錄基金名稱。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CommitmentDate` | Commitment日期 | DATE | 04/21/2011 | 記錄Commitment日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Commitment` | 承諾出資額 | DECIMAL | 500.0 | 記錄承諾出資額，通常為金額或資本數值。 | — |


## LimitedPartner.csv

**用途**：有限合夥人主表，記錄 LP 的基本資料、資產配置與出資偏好。

**主鍵**：`LimitedPartnerID`

**主要關聯鍵**：無明顯外鍵，或主要以本表欄位自身描述。

**可連接到**：可連到 LimitedPartner.csv；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 10931-95 | 此表主鍵，用於唯一識別單筆有限合夥人唯一識別碼。 | 可連到 LimitedPartner.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 98f29abf2299317d94616e9c199ded3eb962a1b816182ee6bed768be66ef4ef9 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 01/31/2026 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerName` | 有限合夥人名稱 | TEXT(255) | Rio Tinto | 記錄有限合夥人名稱。 | — |
| `LimitedPartnerFormerName` | 有限合夥人曾用名稱 | TEXT(500) | RTZ Corporation, Rio Tinto Company | 官方資料字典對此欄有說明；此欄主要記錄有限合夥人曾用名稱。 | — |
| `LimitedPartnerLegalName` | 有限合夥人法定名稱 | TEXT(255) | Rio Tinto plc | 官方資料字典對此欄有說明；此欄主要記錄有限合夥人法定名稱。 | — |
| `LimitedPartnerAlsoKnownAs` | 有限合夥人其他名稱 | TEXT(255) | Sodena | 官方資料字典對此欄有說明；此欄主要記錄有限合夥人其他名稱。 | — |
| `PrimaryContactFirstName` | 主要聯絡人名 | TEXT(200) | Peter | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人名。 | — |
| `PrimaryContactLastName` | 主要聯絡人姓 | TEXT(200) | Cunningham | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人姓。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerType` | 有限合夥人類型 | TEXT(50) | Corporation | 記錄有限合夥人類型，通常為比例或比率。 | — |
| `PreferredFundType` | 偏好基金類型 | TEXT | Debt - General | 官方資料字典對此欄有說明；此欄主要記錄偏好基金類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `YearFounded` | 年份成立 | INTEGER | 1872 | 記錄年份成立相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AUM` | 管理資產規模 | DECIMAL | 134.0 | 記錄管理資產規模，通常為金額或資本數值。 | — |
| `SoldSecondaryCommitments` | 出售SecondaryCommitments | TEXT(5) | No | 官方資料字典對此欄有說明；此欄主要記錄出售SecondaryCommitments。 | — |
| `BoughtSecondaryCommitments` | 買入SecondaryCommitments | TEXT(5) | No | 官方資料字典對此欄有說明；此欄主要記錄買入SecondaryCommitments。 | — |
| `TotalCommitments` | 總Commitments | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄總Commitments。 | — |
| `TotalActiveCommitments` | 總現有Commitments | INTEGER | 1 | 記錄總現有Commitments，通常為金額或資本數值。 | — |
| `TotalCommitmentsInDebtFunds` | 總Commitments債務Funds | INTEGER | 1 | 記錄總Commitments債務Funds，通常為金額或資本數值。 | — |
| `TotalCommitmentsInPEFunds` | 總CommitmentsPEFunds | INTEGER | 16 | 記錄總CommitmentsPEFunds，通常為金額或資本數值。 | — |
| `TotalCommitmentsInREFunds` | 總CommitmentsREFunds | INTEGER | 2 | 記錄總CommitmentsREFunds，通常為金額或資本數值。 | — |
| `TotalCommitmentsInVCFunds` | 總CommitmentsVCFunds | INTEGER | 3 | 記錄總CommitmentsVCFunds，通常為金額或資本數值。 | — |
| `TotalCommitmentsInFOFsAnd2nd` | 總CommitmentsFOFsAnd2nd | INTEGER | 1 | 記錄總CommitmentsFOFsAnd2nd，通常為金額或資本數值。 | — |
| `TotalCommitmentsInInfrastructure` | 總Commitments基礎設施 | INTEGER | 1 | 記錄總Commitments基礎設施，通常為金額或資本數值。 | — |
| `TotalCommitmentsInEnergyFunds` | 總Commitments能源Funds | INTEGER | 1 | 記錄總Commitments能源Funds，通常為金額或資本數值。 | — |
| `TotalCommitmentsInOtherFunds` | 總Commitments其他Funds | INTEGER | 1 | 記錄總Commitments其他Funds，通常為金額或資本數值。 | — |
| `AllocationToAlternativeInvestmentsPercent` | AllocationAlternative投資百分比 | DECIMAL | 1.7 | 記錄AllocationAlternative投資百分比，通常為金額或資本數值。 | — |
| `PrivateEquityPercent` | 私募權益百分比 | DECIMAL | 76.5 | 記錄私募權益百分比，通常為金額或資本數值。 | — |
| `RealEstatePercent` | 不動產Estate百分比 | DECIMAL | 0.6 | 記錄不動產Estate百分比，通常為金額或資本數值。 | — |
| `SpecialOpportunitiesPercent` | 特殊Opportunities百分比 | DECIMAL | 60.0 | 記錄特殊Opportunities百分比，通常為金額或資本數值。 | — |
| `HedgeFundsPercent` | 對沖Funds百分比 | DECIMAL | 2.8 | 記錄對沖Funds百分比，通常為金額或資本數值。 | — |
| `EquitiesPercent` | 股票百分比 | DECIMAL | 91.6 | 記錄股票百分比，通常為金額或資本數值。 | — |
| `FixedIncome` | 固定收益收益 | DECIMAL | 2394.2762383 | 記錄固定收益收益，通常為金額或資本數值。 | — |
| `FixedIncomePercent` | 固定收益收益百分比 | DECIMAL | 8.4 | 記錄固定收益收益百分比，通常為金額或資本數值。 | — |
| `CashPercent` | 現金百分比 | DECIMAL | 0.6 | 記錄現金百分比，通常為金額或資本數值。 | — |
| `PreferredCommitmentSize` | 偏好Commitment規模 | TEXT(50) | 2.34113908 - 5.8528477 | 官方資料字典對此欄有說明；此欄主要記錄偏好Commitment規模。 | — |
| `PreferredCommitmentSizeMin` | 偏好Commitment規模最小值 | DECIMAL | 2.34113908 | 官方資料字典對此欄有說明；此欄主要記錄偏好Commitment規模最小值。 | — |
| `PreferredCommitmentSizeMax` | 偏好Commitment規模Max | DECIMAL | 5.8528477 | 官方資料字典對此欄有說明；此欄主要記錄偏好Commitment規模Max。 | — |
| `PreferredDirectInvestmentSize` | 偏好直接投資規模 | TEXT(50) | 1.24019881 - 6.20099406 | 官方資料字典對此欄有說明；此欄主要記錄偏好直接投資規模。 | — |
| `PreferredDirectInvestmentSizeMin` | 偏好直接投資規模最小值 | DECIMAL | 1.24019881 | 官方資料字典對此欄有說明；此欄主要記錄偏好直接投資規模最小值。 | — |
| `PreferredDirectInvestmentSizeMax` | 偏好直接投資規模Max | DECIMAL | 6.20099406 | 官方資料字典對此欄有說明；此欄主要記錄偏好直接投資規模Max。 | — |
| `TargetAlternativesPercentMin` | 目標Alternatives百分比最小值 | DECIMAL | 9.4 | 記錄目標Alternatives百分比最小值，通常為比例或比率。 | — |
| `TargetAlternativesPercentMax` | 目標Alternatives百分比Max | DECIMAL | 10.0 | 記錄目標Alternatives百分比Max，通常為比例或比率。 | — |
| `TargetPrivateEquityPercentMin` | 目標私募權益百分比最小值 | DECIMAL | 100.0 | 記錄目標私募權益百分比最小值，通常為比例或比率。 | — |
| `TargetPrivateEquityPercentMax` | 目標私募權益百分比Max | DECIMAL | 100.0 | 記錄目標私募權益百分比Max，通常為比例或比率。 | — |
| `TargetRealEstatePercentMin` | 目標不動產Estate百分比最小值 | DECIMAL | 30.0 | 記錄目標不動產Estate百分比最小值，通常為比例或比率。 | — |
| `TargetRealEstatePercentMax` | 目標不動產Estate百分比Max | DECIMAL | 40.0 | 記錄目標不動產Estate百分比Max，通常為比例或比率。 | — |
| `TargetSpecialOpportunitiesPercentMin` | 目標特殊Opportunities百分比最小值 | DECIMAL | 0.0 | 記錄目標特殊Opportunities百分比最小值，通常為比例或比率。 | — |
| `TargetSpecialOpportunitiesPercentMax` | 目標特殊Opportunities百分比Max | DECIMAL | 0.0 | 記錄目標特殊Opportunities百分比Max，通常為比例或比率。 | — |
| `TargetHedgeFundsPercentMin` | 目標對沖Funds百分比最小值 | DECIMAL | 20.0 | 記錄目標對沖Funds百分比最小值，通常為比例或比率。 | — |
| `TargetHedgeFundsPercentMax` | 目標對沖Funds百分比Max | DECIMAL | 20.0 | 記錄目標對沖Funds百分比Max，通常為比例或比率。 | — |
| `TargetEquitiesPercentMin` | 目標股票百分比最小值 | DECIMAL | 42.0 | 記錄目標股票百分比最小值，通常為比例或比率。 | — |
| `TargetEquitiesPercentMax` | 目標股票百分比Max | DECIMAL | 42.0 | 記錄目標股票百分比Max，通常為比例或比率。 | — |
| `TargetFixedIncomeMin` | 目標固定收益收益最小值 | DECIMAL | 1460.62771133 | 官方資料字典對此欄有說明；此欄主要記錄目標固定收益收益最小值。 | — |
| `TargetFixedIncomePercentMin` | 目標固定收益收益百分比最小值 | DECIMAL | 30.0 | 記錄目標固定收益收益百分比最小值，通常為比例或比率。 | — |
| `TargetFixedIncomeMax` | 目標固定收益收益Max | DECIMAL | 1460.62771133 | 記錄目標固定收益收益Max，通常為比例或比率。 | — |
| `TargetFixedIncomePercentMax` | 目標固定收益收益百分比Max | DECIMAL | 30.0 | 記錄目標固定收益收益百分比Max，通常為比例或比率。 | — |
| `TargetCashPercentMin` | 目標現金百分比最小值 | DECIMAL | 0.0 | 記錄目標現金百分比最小值，通常為比例或比率。 | — |
| `TargetCashPercentMax` | 目標現金百分比Max | DECIMAL | 0.0 | 記錄目標現金百分比Max，通常為比例或比率。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Website` | 網站 | TEXT | www.riotinto.com | 記錄網站。 | — |
| `HQLocation` | 總部地點 | TEXT(100) | London, United Kingdom | 官方資料字典對此欄有說明；此欄主要記錄總部地點。 | — |
| `HQAddressLine1` | 總部地址第一行 | TEXT(100) | 6 Saint James's Square | 官方資料字典對此欄有說明；此欄主要記錄總部地址第一行。 | — |
| `HQAddressLine2` | 總部地址第二行 | TEXT(100) | 1st Floor Right | 官方資料字典對此欄有說明；此欄主要記錄總部地址第二行。 | — |
| `HQCity` | 總部城市 | TEXT(100) | London | 記錄總部城市相關地理資訊。 | — |
| `HQState_Province` | 總部州或省 | TEXT(100) | England | 記錄總部州或省相關地理資訊。 | — |
| `HQPostCode` | 總部郵遞區號 | TEXT(30) | SW1Y 4AD | 官方資料字典對此欄有說明；此欄主要記錄總部郵遞區號。 | — |
| `HQCountry` | 總部國家 | TEXT(50) | United Kingdom | 記錄總部國家相關地理資訊。 | — |
| `HQPhone` | 總部電話 | TEXT(50) | +44 (0)20 7781 2000 | 官方資料字典對此欄有說明；此欄主要記錄總部電話。 | — |
| `HQFax` | 總部傳真 | TEXT(50) | +34 84 842 1943 | 官方資料字典對此欄有說明；此欄主要記錄總部傳真。 | — |
| `HQEmail` | 總部電子郵件 | TEXT(255) | info@riotinto.com | 官方資料字典對此欄有說明；此欄主要記錄總部電子郵件。 | — |
| `HQGlobalRegion` | 總部全球Region | TEXT(100) | Europe | 記錄總部全球Region相關地理資訊。 | — |
| `HQGlobalSubRegion` | 總部全球SubRegion | TEXT(100) | Western Europe | 官方資料字典對此欄有說明；此欄主要記錄總部全球SubRegion。 | — |
| `PrimaryContactEmail` | 主要聯絡人電子郵件 | TEXT(255) | peter.cunningham@riotinto.com | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人電子郵件。 | — |
| `PrimaryContactPhone` | 主要聯絡人電話 | TEXT(50) | +44 (0)20 7781 2000 | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人電話。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryContactPBId` | 主要聯絡人 PitchBook 識別碼 | TEXT(20) | 250929-01P | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人 PitchBook 識別碼。 | 通常可連到 Person.csv |
| `PrimaryContactMiddle` | 主要聯絡人中間名 | TEXT(200) | Arriaga | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人中間名。 | — |
| `PrimaryContactPrefix` | 主要聯絡人前綴 | TEXT(50) | Mr. | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人前綴。 | — |
| `PrimaryContactSuffix` | 主要聯絡人後綴 | TEXT(50) | Ph.D | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人後綴。 | — |
| `PrimaryContact` | 主要聯絡人 | TEXT(255) | Peter Cunningham | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人。 | — |
| `PrimaryContactTitle` | 主要聯絡人Title | TEXT | Chief Financial Officer, Board Member, Member of Executive Committee & Executive Director | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人Title。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Description` | 描述 | TEXT | Rio Tinto is a corporation based in London, United Kingdom. Established in 1873, the firm is a global mining group t ... | 官方資料字典對此欄有說明；此欄主要記錄描述。 | — |
| `DirectInvestments` | 直接投資 | INTEGER | 118 | 官方資料字典對此欄有說明；此欄主要記錄直接投資。 | — |
| `OpenToFirstTimeFunds` | 開放首次時間Funds | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄開放首次時間Funds。 | — |
| `AllocationToAlternativeInvestments` | AllocationAlternative投資 | DECIMAL | 3071.33281923 | 記錄AllocationAlternative投資，通常為金額或資本數值。 | — |
| `PrivateEquity` | 私募權益 | DECIMAL | 1156.773714 | 記錄私募權益，通常為金額或資本數值。 | — |
| `RealEstate` | 不動產Estate | DECIMAL | 9.122439 | 記錄不動產Estate，通常為金額或資本數值。 | — |
| `SpecialOpportunities` | 特殊Opportunities | DECIMAL | 300 | 記錄特殊Opportunities，通常為金額或資本數值。 | — |
| `HedgeFunds` | 對沖Funds | DECIMAL | 42.43868 | 記錄對沖Funds，通常為金額或資本數值。 | — |
| `Equities` | 股票 | DECIMAL | 26221.01642476 | 記錄股票，通常為金額或資本數值。 | — |
| `Cash` | 現金 | DECIMAL | 675.704878 | 記錄現金，通常為金額或資本數值。 | — |
| `PolicyDescription` | 政策描述 | TEXT | Rio Tinto is currently investing in private equity. Investments in private equity include debt strategies. The compa ... | 官方資料字典對此欄有說明；此欄主要記錄政策描述。 | — |
| `PreferredGeography` | 偏好地理偏好 | TEXT | Australia, New South Wales, Oceania | 官方資料字典對此欄有說明；此欄主要記錄偏好地理偏好。 | — |
| `TargetAlternativesMin` | 目標Alternatives最小值 | DECIMAL | 1512.38337943 | 官方資料字典對此欄有說明；此欄主要記錄目標Alternatives最小值。 | — |
| `TargetAlternativesMax` | 目標AlternativesMax | DECIMAL | 94.51842637 | 官方資料字典對此欄有說明；此欄主要記錄目標AlternativesMax。 | — |
| `TargetPrivateEquityMin` | 目標私募權益最小值 | DECIMAL | 1300 | 官方資料字典對此欄有說明；此欄主要記錄目標私募權益最小值。 | — |
| `TargetPrivateEquityMax` | 目標私募權益Max | DECIMAL | 217.71875019 | 官方資料字典對此欄有說明；此欄主要記錄目標私募權益Max。 | — |
| `TargetRealEstateMin` | 目標不動產Estate最小值 | DECIMAL | 283.5552791 | 記錄目標不動產Estate最小值相關地理資訊。 | — |
| `TargetRealEstateMax` | 目標不動產EstateMax | DECIMAL | 378.07370547 | 記錄目標不動產EstateMax相關地理資訊。 | — |
| `TargetSpecialOpportunitiesMin` | 目標特殊Opportunities最小值 | DECIMAL | 0 | 官方資料字典對此欄有說明；此欄主要記錄目標特殊Opportunities最小值。 | — |
| `TargetSpecialOpportunitiesMax` | 目標特殊OpportunitiesMax | DECIMAL | 0 | 官方資料字典對此欄有說明；此欄主要記錄目標特殊OpportunitiesMax。 | — |
| `TargetHedgeFundsMin` | 目標對沖Funds最小值 | DECIMAL | 374.6 | 官方資料字典對此欄有說明；此欄主要記錄目標對沖Funds最小值。 | — |
| `TargetHedgeFundsMax` | 目標對沖FundsMax | DECIMAL | 374.6 | 官方資料字典對此欄有說明；此欄主要記錄目標對沖FundsMax。 | — |
| `TargetEquitiesMin` | 目標股票最小值 | DECIMAL | 2044.87879587 | 官方資料字典對此欄有說明；此欄主要記錄目標股票最小值。 | — |
| `TargetEquitiesMax` | 目標股票Max | DECIMAL | 2044.87879587 | 記錄目標股票Max，通常為比例或比率。 | — |
| `TargetCashMin` | 目標現金最小值 | DECIMAL | 0 | 官方資料字典對此欄有說明；此欄主要記錄目標現金最小值。 | — |
| `TargetCashMax` | 目標現金Max | DECIMAL | 0 | 官方資料字典對此欄有說明；此欄主要記錄目標現金Max。 | — |
