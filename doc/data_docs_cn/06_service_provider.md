# 服務機構資料

本文件依主題整理正式 CSV，說明每個表的用途、關聯鍵與欄位分組。

## ServiceProvider.csv

**用途**：服務機構主表，記錄律所、會計師、顧問等服務提供方的資料與服務範圍。

**主鍵**：`ServiceProviderID`

**主要關聯鍵**：`LastDealLeadPartnersID`、`LastClosedFundLeadPartnersID`

**可連接到**：可連到 ServiceProvider.csv；通常可連到 Person.csv；識別碼欄位，可作為 join 線索；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10010-89 | 此表主鍵，用於唯一識別單筆服務機構唯一識別碼。 | 可連到 ServiceProvider.csv |
| `LastDealLeadPartnersID` | 最近交易主導合夥人識別碼 | TEXT | 36960-85P | 官方資料字典對此欄有說明；此欄主要記錄最近交易主導合夥人識別碼。 | 識別碼欄位，可作為 join 線索 |
| `LastClosedFundLeadPartnersID` | 最近已關閉基金主導合夥人識別碼 | TEXT | 195581-98P, 11984-05P, 11518-39P | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金主導合夥人識別碼。 | 識別碼欄位，可作為 join 線索 |
| `RowID` | 列唯一識別碼 | TEXT(255) | f34bae1e5cbb021e19f3c95670787cd492bbd359804ccf593751b26e9f7355b0 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 08/22/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderName` | 服務機構名稱 | TEXT(255) | Broadcom | 記錄服務機構名稱。 | — |
| `ServiceProviderFormerName` | 服務機構曾用名稱 | TEXT(500) | Charter One Bank F.S.B | 官方資料字典對此欄有說明；此欄主要記錄服務機構曾用名稱。 | — |
| `ServiceProviderLegalName` | 服務機構法定名稱 | TEXT(255) | Broadcom Corp. | 官方資料字典對此欄有說明；此欄主要記錄服務機構法定名稱。 | — |
| `ServiceProviderAlsoKnownAs` | 服務機構其他名稱 | TEXT(500) | CharterOne Bank | 官方資料字典對此欄有說明；此欄主要記錄服務機構其他名稱。 | — |
| `LastClosedFundName` | 最近已關閉基金名稱 | TEXT(100) | ACIS CLO 2017-7 | 記錄最近已關閉基金名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryServiceProviderType` | 主要服務機構類型 | TEXT(255) | Other Consultant Type | 官方資料字典對此欄有說明；此欄主要記錄主要服務機構類型。 | — |
| `OtherServiceProviderTypes` | 其他服務機構Types | TEXT | Mezzanine | 官方資料字典對此欄有說明；此欄主要記錄其他服務機構Types。 | — |
| `LastDealSizeStatus` | 最近交易規模狀態 | TEXT(50) | Actual | 記錄最近交易規模狀態，用來描述當前狀態或標記。 | — |
| `LastDealValuationStatus` | 最近交易估值狀態 | TEXT(50) | Estimated | 記錄最近交易估值狀態，用來描述當前狀態或標記。 | — |
| `LastDealType` | 最近交易類型 | TEXT(50) | Public Investment 2nd Offering | 官方資料字典對此欄有說明；此欄主要記錄最近交易類型。 | — |
| `LastDealType2` | 最近交易Type2 | TEXT(50) | Acquisition Financing | 官方資料字典對此欄有說明；此欄主要記錄最近交易Type2。 | — |
| `LastDealType3` | 最近交易Type3 | TEXT(50) | Public to Private | 官方資料字典對此欄有說明；此欄主要記錄最近交易Type3。 | — |
| `LastDealClass` | 最近交易類別 | TEXT(50) | Public Investment | 官方資料字典對此欄有說明；此欄主要記錄最近交易類別。 | — |
| `LastDealStatus` | 最近交易狀態 | TEXT(50) | Completed | 記錄最近交易狀態，用來描述當前狀態或標記。 | — |
| `LastClosedFundType` | 最近已關閉基金類型 | TEXT(100) | Collateralized Loan Obligation (CLO) | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `NumberOfFundsClosedInTheLast2Years` | 數量OfFunds已關閉TheLast2年份 | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄數量OfFunds已關閉TheLast2年份。 | — |
| `NumberOfFundsClosedInTheLast5Years` | 數量OfFunds已關閉TheLast5年份 | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄數量OfFunds已關閉TheLast5年份。 | — |
| `LastDealDate` | 最近交易日期 | DATE | 11/12/2024 | 記錄最近交易日期相關日期。 | — |
| `LastFinancingDebtDate` | 最近融資債務日期 | DATE | 11/12/2024 | 官方資料字典對此欄有說明；此欄主要記錄最近融資債務日期。 | — |
| `LastClosedFundVintage` | 最近已關閉基金Vintage | INTEGER | 2017 | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金Vintage。 | — |
| `LastClosedFundCloseDate` | 最近已關閉基金關閉日期 | DATE | 04/20/2017 | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金關閉日期。 | — |
| `LastClosedFundOpenDate` | 最近已關閉基金開放日期 | DATE | 07/19/2022 | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金開放日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `MinFundSize` | 最小值基金規模 | DECIMAL | 1.65 | 官方資料字典對此欄有說明；此欄主要記錄最小值基金規模。 | — |
| `MaxFundSize` | Max基金規模 | DECIMAL | 578.35 | 官方資料字典對此欄有說明；此欄主要記錄Max基金規模。 | — |
| `MedianFundSize` | 中位數基金規模 | DECIMAL | 405.5 | 官方資料字典對此欄有說明；此欄主要記錄中位數基金規模。 | — |
| `LastDealSize` | 最近交易規模 | DECIMAL | 143.75 | 官方資料字典對此欄有說明；此欄主要記錄最近交易規模。 | — |
| `LastDealValuation` | 最近交易估值 | DECIMAL | 43.13 | 官方資料字典對此欄有說明；此欄主要記錄最近交易估值。 | — |
| `LastFinancingDebtSize` | 最近融資債務規模 | DECIMAL | 16.0 | 記錄最近融資債務規模，通常為金額或資本數值。 | — |
| `LastFinancingDebt` | 最近融資債務 | TEXT | Term Loan - $16,00M (Term Loan) | 記錄最近融資債務，通常為金額或資本數值。 | — |
| `LastClosedFundSize` | 最近已關閉基金規模 | DECIMAL | 405.5 | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金規模。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Website` | 網站 | TEXT | www.charterone.com | 記錄網站。 | — |
| `HQLocation` | 總部地點 | TEXT(100) | Irvine, CA | 官方資料字典對此欄有說明；此欄主要記錄總部地點。 | — |
| `HQAddressLine1` | 總部地址第一行 | TEXT(100) | 5300 California Avenue | 官方資料字典對此欄有說明；此欄主要記錄總部地址第一行。 | — |
| `HQAddressLine2` | 總部地址第二行 | TEXT(100) | Charter One Bank Building | 官方資料字典對此欄有說明；此欄主要記錄總部地址第二行。 | — |
| `HQCity` | 總部城市 | TEXT(100) | Irvine | 記錄總部城市相關地理資訊。 | — |
| `HQState_Province` | 總部州或省 | TEXT(100) | California | 記錄總部州或省相關地理資訊。 | — |
| `HQPostCode` | 總部郵遞區號 | TEXT(30) | 92617 | 官方資料字典對此欄有說明；此欄主要記錄總部郵遞區號。 | — |
| `HQCountry` | 總部國家 | TEXT(50) | United States | 記錄總部國家相關地理資訊。 | — |
| `HQPhone` | 總部電話 | TEXT(50) | +1 (310) 201-4100 | 官方資料字典對此欄有說明；此欄主要記錄總部電話。 | — |
| `HQFax` | 總部傳真 | TEXT(50) | +1 (972) 637-9197 | 官方資料字典對此欄有說明；此欄主要記錄總部傳真。 | — |
| `HQEmail` | 總部電子郵件 | TEXT(255) | acof_ir@aresmgmt.com | 官方資料字典對此欄有說明；此欄主要記錄總部電子郵件。 | — |
| `HQGlobalRegion` | 總部全球Region | TEXT(100) | Americas | 記錄總部全球Region相關地理資訊。 | — |
| `HQGlobalSubRegion` | 總部全球SubRegion | TEXT(100) | North America | 官方資料字典對此欄有說明；此欄主要記錄總部全球SubRegion。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryContactPBId` | 主要聯絡人 PitchBook 識別碼 | TEXT(20) | 11506-06P | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人 PitchBook 識別碼。 | 通常可連到 Person.csv |
| `PrimaryContact` | 主要聯絡人 | TEXT(255) | David Kaplan | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人。 | — |
| `PrimaryContactTitle` | 主要聯絡人Title | TEXT | Co-Founder, Director & Partner | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人Title。 | — |
| `LastDealLeadPartners` | 最近交易主導合夥人 | TEXT | Aaron Handler | 官方資料字典對此欄有說明；此欄主要記錄最近交易主導合夥人。 | — |
| `LastClosedFundLeadPartners` | 最近已關閉基金主導合夥人 | TEXT | Byron Pavano JD, Geoffrey Rehnert JD, Marc Wolpow JD | 官方資料字典對此欄有說明；此欄主要記錄最近已關閉基金主導合夥人。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ParentCompany` | 母公司名稱 | TEXT(500) | Ares Management | 記錄母公司名稱。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Employees` | 員工數 | INTEGER | 84 | 官方資料字典對此欄有說明；此欄主要記錄員工數。 | — |
| `Description` | 描述 | TEXT | Charter One Financial was a commercial bank that provided consumer banking, indirect auto finance, commercial leasin ... | 官方資料字典對此欄有說明；此欄主要記錄描述。 | — |
| `ServicedCompanies` | ServicedCompanies | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄ServicedCompanies。 | — |
| `ServicedDeals` | ServicedDeals | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄ServicedDeals。 | — |
| `ServicedInvestors` | ServicedInvestors | INTEGER | 2 | 官方資料字典對此欄有說明；此欄主要記錄ServicedInvestors。 | — |
| `ServicedFunds` | ServicedFunds | INTEGER | 6 | 官方資料字典對此欄有說明；此欄主要記錄ServicedFunds。 | — |
| `ServicedLimitedPartners` | Serviced有限合夥人 | INTEGER | 3 | 官方資料字典對此欄有說明；此欄主要記錄Serviced有限合夥人。 | — |
| `NumberOfFundsOpen` | 數量OfFunds開放 | INTEGER | 3 | 官方資料字典對此欄有說明；此欄主要記錄數量OfFunds開放。 | — |
| `NumberOfFundsClosed` | 數量OfFunds已關閉 | INTEGER | 9 | 官方資料字典對此欄有說明；此欄主要記錄數量OfFunds已關閉。 | — |
| `NumberOfFundsClosedInTheLast6Months` | 數量OfFunds已關閉TheLast6Months | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄數量OfFunds已關閉TheLast6Months。 | — |
| `NumberOfFundsClosedInTheLast12Months` | 數量OfFunds已關閉TheLast12Months | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄數量OfFunds已關閉TheLast12Months。 | — |
| `PitchBookProfileLink` | PitchBook 頁面連結 | TEXT | https://content.pitchbook.com/profiles/advisor/10010-89 | 官方資料字典對此欄有說明；此欄主要記錄PitchBook 頁面連結。 | — |


## ServiceProviderCompDealRelation.csv

**用途**：記錄服務機構與公司/交易的服務關係。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`ServiceProviderID`、`CompanyID`、`DealID`

**可連接到**：可連到 ServiceProvider.csv；可連到 Company.csv；可連到 Deal.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10231-12 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 ServiceProvider.csv |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 310354-66 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 310335-58T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `DealNo` | 交易序號 | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄交易序號。 | — |
| `RowID` | 列唯一識別碼 | TEXT(255) | 7e9389637ad8d45e410ea1908732780e96458c8d1b1d85b987641a75d50e7453 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 01/31/2026 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Versant Media Group | 記錄公司名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealType` | 交易類型 | TEXT(255) | Debt - Spinoff | 官方資料字典對此欄有說明；此欄主要記錄交易類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 10/23/2025 | 記錄交易完成日期相關日期。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(255) | Manager | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |


## ServiceProviderCompanyRelation.csv

**用途**：記錄服務機構服務的公司。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`ServiceProviderID`、`CompanyID`

**可連接到**：可連到 ServiceProvider.csv；可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10011-61 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 ServiceProvider.csv |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10802-80 | 唯一識別碼，用於記錄公司唯一識別碼。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 9a32b793ad44d5786c46914d55845ca2d0228a2bdffd35adae1e1a92f6b87cc6 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Lyondell | 記錄公司名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceType` | 服務類型 | TEXT(255) | General Service | 官方資料字典對此欄有說明；此欄主要記錄服務類型。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(255) | Debt Financing | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |


## ServiceProviderInvFundRelation.csv

**用途**：記錄服務機構服務的投資機構與基金。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`ServiceProviderID`、`FundID`、`InvestorID`

**可連接到**：可連到 ServiceProvider.csv；可連到 Fund.csv；可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 41708-17 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 ServiceProvider.csv |
| `FundID` | 基金唯一識別碼 | TEXT(20) | 20711-35F | 唯一識別碼，用於記錄基金唯一識別碼。 | 可連到 Fund.csv |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 153506-71 | 唯一識別碼，用於記錄投資機構唯一識別碼。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 856436a87c946a3fd26955a40eb182233f1ce0c54f3cbc15c39c501e36ae1ea2 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FundName` | 基金名稱 | TEXT(255) | Emerging India Credit Opportunities Fund I | 記錄基金名稱。 | — |
| `InvestorName` | 投資機構名稱 | TEXT(255) | Investec India | 記錄投資機構名稱。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(255) | Legal Advisor | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |


## ServiceProviderInvestorRelation.csv

**用途**：記錄服務機構關聯的投資機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`ServiceProviderID`、`InvestorID`、`DealID`

**可連接到**：可連到 ServiceProvider.csv；可連到 Investor.csv；可連到 Deal.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10011-61 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 ServiceProvider.csv |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 10011-61 | 唯一識別碼，用於記錄投資機構唯一識別碼。 | 可連到 Investor.csv |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 244277-56T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | f107512a0e8e1cf5a3fc6d9defca72fb682d1728f7adc39f2cc725471044d733 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorName` | 投資機構名稱 | TEXT(255) | Ares Private Equity Group | 記錄投資機構名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceType` | 服務類型 | TEXT(255) | General Service | 官方資料字典對此欄有說明；此欄主要記錄服務類型。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(255) | Advisor: General | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |


## ServiceProviderLPRelation.csv

**用途**：記錄服務機構服務的 LP。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`ServiceProviderID`、`LimitedPartnerID`

**可連接到**：可連到 ServiceProvider.csv；可連到 LimitedPartner.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 10011-70 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 ServiceProvider.csv |
| `LimitedPartnerID` | 有限合夥人唯一識別碼 | TEXT(20) | 99837-10 | 唯一識別碼，用於記錄有限合夥人唯一識別碼。 | 可連到 LimitedPartner.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 4bf2373219c47e05c6e90722f2d0ea9199d2a54b1eed347248bf0c424add4d71 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LimitedPartnerName` | 有限合夥人名稱 | TEXT(255) | City of Palm Beach Gardens Police Officers' Pension Fund | 記錄有限合夥人名稱。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(255) | Investment Manager | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |
