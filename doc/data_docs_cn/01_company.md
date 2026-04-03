# 公司資料

本文件依主題整理正式 CSV，說明每個表的用途、關聯鍵與欄位分組。

## Company.csv

**用途**：公司主表，記錄公司的基本資料、融資狀態、聯絡資訊與最近財務摘要。

**主鍵**：`CompanyID`

**主要關聯鍵**：`ParentCompanyID`、`FirstFinancingDealID`、`LastFinancingDealID`

**可連接到**：可連到 Company.csv；通常表示母機構或母公司 ID；通常可連到 Person.csv；可連到 Deal.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10010-89 | 此表主鍵，用於唯一識別單筆公司唯一識別碼。 | 可連到 Company.csv |
| `ParentCompanyID` | 母公司識別碼 | TEXT(20) | 130527-46 | 官方資料字典對此欄有說明；此欄主要記錄母公司識別碼。 | 通常表示母機構或母公司 ID |
| `CikCode` | Cik代碼 | TEXT | 1054374 | 官方資料字典對此欄有說明；此欄主要記錄Cik代碼。 | — |
| `FirstFinancingDealID` | 首次融資交易識別碼 | TEXT(20) | 50895-64T | 官方資料字典對此欄有說明；此欄主要記錄首次融資交易識別碼。 | 可連到 Deal.csv |
| `LastFinancingDealID` | 最近融資交易識別碼 | TEXT(20) | 50864-41T | 官方資料字典對此欄有說明；此欄主要記錄最近融資交易識別碼。 | 可連到 Deal.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 257fd016fca0e9794e4ab6dc51121cc6f989cf4ecbca2cccea67572f5d8efe91 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 11/21/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Broadcom | 記錄公司名稱。 | — |
| `CompanyAlsoKnownAs` | 公司其他名稱 | TEXT | SOV, Standing Ovation | 官方資料字典對此欄有說明；此欄主要記錄公司其他名稱。 | — |
| `CompanyFormerName` | 公司曾用名稱 | TEXT | Sierra Well Service | 官方資料字典對此欄有說明；此欄主要記錄公司曾用名稱。 | — |
| `CompanyLegalName` | 公司法定名稱 | TEXT(255) | Broadcom Corp. | 官方資料字典對此欄有說明；此欄主要記錄公司法定名稱。 | — |
| `PrimaryContactFirstName` | 主要聯絡人名 | TEXT(200) | Yoshihiro | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人名。 | — |
| `PrimaryContactLastName` | 主要聯絡人姓 | TEXT(200) | Ogita | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人姓。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyFinancingStatus` | 公司融資狀態 | TEXT(50) | Formerly VC-backed | 記錄公司融資狀態，用來描述當前狀態或標記。 | — |
| `CompanyFinancingStatusDate` | 公司融資狀態日期 | DATE | 02/01/2016 | 記錄公司融資狀態日期相關日期。 | — |
| `BusinessStatus` | 業務狀態 | TEXT(50) | Profitable | 官方資料字典對此欄有說明；此欄主要記錄業務狀態。 | — |
| `BusinessStatusDate` | 業務狀態日期 | DATE | 04/17/1998 | 記錄業務狀態日期相關日期。 | — |
| `OwnershipStatus` | 持有狀態 | TEXT(50) | Acquired/Merged | 官方資料字典對此欄有說明；此欄主要記錄持有狀態。 | — |
| `OwnershipStatusDate` | 持有狀態日期 | DATE | 02/01/2016 | 記錄持有狀態日期相關日期。 | — |
| `Universe` | 覆蓋範圍 | TEXT(200) | Publicly Listed, Venture Capital | 記錄覆蓋範圍，用來描述當前狀態或標記。 | — |
| `FirstFinancingSizeStatus` | 首次融資規模狀態 | TEXT(50) | Actual | 官方資料字典對此欄有說明；此欄主要記錄首次融資規模狀態。 | — |
| `FirstFinancingValuationStatus` | 首次融資估值狀態 | TEXT(50) | Actual | 官方資料字典對此欄有說明；此欄主要記錄首次融資估值狀態。 | — |
| `FirstFinancingDealType` | 首次融資交易類型 | TEXT(50) | Early Stage VC | 官方資料字典對此欄有說明；此欄主要記錄首次融資交易類型。 | — |
| `FirstFinancingDealType2` | 首次融資交易Type2 | TEXT(50) | Seed Round | 官方資料字典對此欄有說明；此欄主要記錄首次融資交易Type2。 | — |
| `FirstFinancingDealType3` | 首次融資交易Type3 | TEXT(50) | Corporate Divestiture | 官方資料字典對此欄有說明；此欄主要記錄首次融資交易Type3。 | — |
| `FirstFinancingDealClass` | 首次融資交易類別 | TEXT(50) | Venture Capital | 記錄首次融資交易類別，通常為金額或資本數值。 | — |
| `FirstFinancingStatus` | 首次融資狀態 | TEXT(50) | Completed | 記錄首次融資狀態，用來描述當前狀態或標記。 | — |
| `LastKnownValuationDealType` | 最近名稱估值交易類型 | TEXT(50) | Merger/Acquisition | 記錄最近名稱估值交易類型，通常為金額或資本數值。 | — |
| `LastFinancingSizeStatus` | 最近融資規模狀態 | TEXT(50) | Actual | 官方資料字典對此欄有說明；此欄主要記錄最近融資規模狀態。 | — |
| `LastFinancingValuationStatus` | 最近融資估值狀態 | TEXT(50) | Estimated | 官方資料字典對此欄有說明；此欄主要記錄最近融資估值狀態。 | — |
| `LastFinancingDealType` | 最近融資交易類型 | TEXT(50) | Merger/Acquisition | 官方資料字典對此欄有說明；此欄主要記錄最近融資交易類型。 | — |
| `LastFinancingDealType2` | 最近融資交易Type2 | TEXT(50) | Seed Round | 官方資料字典對此欄有說明；此欄主要記錄最近融資交易Type2。 | — |
| `LastFinancingDealType3` | 最近融資交易Type3 | TEXT(50) | Add-on | 官方資料字典對此欄有說明；此欄主要記錄最近融資交易Type3。 | — |
| `LastFinancingDealClass` | 最近融資交易類別 | TEXT(50) | Corporate | 記錄最近融資交易類別，通常為金額或資本數值。 | — |
| `LastFinancingStatus` | 最近融資狀態 | TEXT(50) | Completed | 記錄最近融資狀態，用來描述當前狀態或標記。 | — |
| `FinancingStatusNote` | 融資狀態Note | TEXT | The company (NASDAQ: BRCM) was acquired by Avago Technologies (NASDAQ: AVGO) for $37 billion on February 1, 2016. As ... | 記錄融資狀態Note，用來描述當前狀態或標記。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `YearFounded` | 年份成立 | INTEGER | 1991 | 記錄年份成立相關日期。 | — |
| `FiscalPeriod` | 財務期間 | TEXT(10) | TTM 3Q2015 | 官方資料字典對此欄有說明；此欄主要記錄財務期間。 | — |
| `PeriodEndDate` | 期間結束日期 | DATE | 09/30/2015 | 記錄期間結束日期相關地理資訊。 | — |
| `FirstFinancingDate` | 首次融資日期 | DATE | 01/01/1995 | 記錄首次融資日期相關日期。 | — |
| `FirstFinancingDebtDate` | 首次融資債務日期 | DATE | 01/01/1995 | 記錄首次融資債務日期相關日期。 | — |
| `LastKnownValuationDate` | 最近名稱估值日期 | DATE | 02/01/2016 | 官方資料字典對此欄有說明；此欄主要記錄最近名稱估值日期。 | — |
| `LastFinancingDate` | 最近融資日期 | DATE | 02/01/2016 | 記錄最近融資日期相關日期。 | — |
| `LastFinancingDebtDate` | 最近融資債務日期 | DATE | 02/01/2016 | 記錄最近融資債務日期相關日期。 | — |
| `PitchBookCreatedDate` | PitchBookCreated日期 | DATE | 03/26/2021 | 記錄PitchBookCreated日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Revenue` | 營收 | DECIMAL | 8484.0 | 記錄營收，通常為金額或資本數值。 | — |
| `GrossProfit` | 毛利 | DECIMAL | 4546.0 | 官方資料字典對此欄有說明；此欄主要記錄毛利。 | — |
| `NetIncome` | 淨利 | DECIMAL | 1414.0 | 官方資料字典對此欄有說明；此欄主要記錄淨利。 | — |
| `EnterpriseValue` | 企業價值 | DECIMAL | 29709.57726 | 官方資料字典對此欄有說明；此欄主要記錄企業價值。 | — |
| `EBITDA` | EBITDA | DECIMAL | 1772.0 | 官方資料字典對此欄有說明；此欄主要記錄EBITDA。 | — |
| `EBIT` | EBIT | DECIMAL | 1466.0 | 官方資料字典對此欄有說明；此欄主要記錄EBIT。 | — |
| `NetDebt` | 淨負債 | DECIMAL | -1870.0 | 官方資料字典對此欄有說明；此欄主要記錄淨負債。 | — |
| `FirstFinancingSize` | 首次融資規模 | DECIMAL | 0.25070542 | 記錄首次融資規模，通常為金額或資本數值。 | — |
| `FirstFinancingValuation` | 首次融資估值 | DECIMAL | 3.535 | 記錄首次融資估值，通常為金額或資本數值。 | — |
| `FirstFinancingDebt` | 首次融資債務 | TEXT | Bonds - $105,00M (Senior Secured, Floating) | 官方資料字典對此欄有說明；此欄主要記錄首次融資債務。 | — |
| `FirstFinancingDebtSize` | 首次融資債務規模 | DECIMAL | 105.0 | 官方資料字典對此欄有說明；此欄主要記錄首次融資債務規模。 | — |
| `LastKnownValuation` | 最近名稱估值 | DECIMAL | 37000.0 | 官方資料字典對此欄有說明；此欄主要記錄最近名稱估值。 | — |
| `LastFinancingSize` | 最近融資規模 | DECIMAL | 37000.0 | 記錄最近融資規模，通常為金額或資本數值。 | — |
| `LastFinancingValuation` | 最近融資估值 | DECIMAL | 37000.0 | 官方資料字典對此欄有說明；此欄主要記錄最近融資估值。 | — |
| `LastFinancingDebt` | 最近融資債務 | TEXT | Revolving Credit; Term Loan (Senior Term Loan A) | 官方資料字典對此欄有說明；此欄主要記錄最近融資債務。 | — |
| `LastFinancingDebtSize` | 最近融資債務規模 | DECIMAL | 66.5 | 官方資料字典對此欄有說明；此欄主要記錄最近融資債務規模。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Website` | 網站 | TEXT | www.xyrosoft.com | 記錄網站。 | — |
| `HQLocation` | 總部地點 | TEXT(100) | Irvine, CA | 記錄總部地點相關地理資訊。 | — |
| `HQAddressLine1` | 總部地址第一行 | TEXT(100) | 5300 California Avenue | 官方資料字典對此欄有說明；此欄主要記錄總部地址第一行。 | — |
| `HQAddressLine2` | 總部地址第二行 | TEXT(100) | 999 Canada Place | 官方資料字典對此欄有說明；此欄主要記錄總部地址第二行。 | — |
| `HQCity` | 總部城市 | TEXT(100) | Irvine | 記錄總部城市相關地理資訊。 | — |
| `HQState_Province` | 總部州或省 | TEXT(100) | California | 記錄總部州或省相關地理資訊。 | — |
| `HQPostCode` | 總部郵遞區號 | TEXT(30) | 92617 | 官方資料字典對此欄有說明；此欄主要記錄總部郵遞區號。 | — |
| `HQCountry` | 總部國家 | TEXT(50) | United States | 記錄總部國家相關地理資訊。 | — |
| `HQPhone` | 總部電話 | TEXT(50) | +81 (0)36 447 1723 | 官方資料字典對此欄有說明；此欄主要記錄總部電話。 | — |
| `HQFax` | 總部傳真 | TEXT(255) | +60 (0)3 2283 4921 | 官方資料字典對此欄有說明；此欄主要記錄總部傳真。 | — |
| `HQEmail` | 總部電子郵件 | TEXT(100) | info@s-ovation.jp | 官方資料字典對此欄有說明；此欄主要記錄總部電子郵件。 | — |
| `HQGlobalRegion` | 總部全球Region | TEXT(100) | Americas | 官方資料字典對此欄有說明；此欄主要記錄總部全球Region。 | — |
| `HQGlobalSubRegion` | 總部全球SubRegion | TEXT(100) | North America | 官方資料字典對此欄有說明；此欄主要記錄總部全球SubRegion。 | — |
| `PrimaryContactEmail` | 主要聯絡人電子郵件 | TEXT(255) | ogita@s-ovation.jp | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人電子郵件。 | — |
| `PrimaryContactPhone` | 主要聯絡人電話 | TEXT(50) | +81 (0)36 447 1723 | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人電話。 | — |
| `FacebookProfileURL` | Facebook 連結 | TEXT(255) | https://www.facebook.com/xyrosoft | 官方資料字典對此欄有說明；此欄主要記錄Facebook 連結。 | — |
| `TwitterProfileURL` | Twitter 連結 | TEXT(255) | https://twitter.com/yaware_com | 官方資料字典對此欄有說明；此欄主要記錄Twitter 連結。 | — |
| `LinkedInProfileURL` | LinkedIn 連結 | TEXT(255) | https://www.linkedin.com/company/xyrosoft | 官方資料字典對此欄有說明；此欄主要記錄LinkedIn 連結。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryContactPBId` | 主要聯絡人 PitchBook 識別碼 | TEXT(20) | 114763-78P | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人 PitchBook 識別碼。 | 通常可連到 Person.csv |
| `PrimaryContact` | 主要聯絡人 | TEXT(255) | Yoshihiro Ogita | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人。 | — |
| `PrimaryContactTitle` | 主要聯絡人Title | TEXT | Founder & Chief Executive Officer | 官方資料字典對此欄有說明；此欄主要記錄主要聯絡人Title。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ParentCompany` | 母公司名稱 | TEXT(500) | Harlan Bakeries | 記錄母公司名稱。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PrimaryIndustrySector` | 主要產業部門 | TEXT(100) | Information Technology | 官方資料字典對此欄有說明；此欄主要記錄主要產業部門。 | — |
| `PrimaryIndustryGroup` | 主要產業群組 | TEXT(100) | Semiconductors | 官方資料字典對此欄有說明；此欄主要記錄主要產業群組。 | — |
| `PrimaryIndustryCode` | 主要產業代碼 | TEXT(100) | General Purpose Semiconductors | 官方資料字典對此欄有說明；此欄主要記錄主要產業代碼。 | — |
| `Verticals` | 垂直領域 | TEXT | Manufacturing, TMT | 官方資料字典對此欄有說明；此欄主要記錄垂直領域。 | — |
| `EmergingSpaces` | EmergingSpaces | TEXT(255) | Generative AI | 官方資料字典對此欄有說明；此欄主要記錄EmergingSpaces。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Description` | 描述 | TEXT | Manufacturer of semiconductors based in Irvine, California. The company designs, develops and supplies of of analog, ... | 官方資料字典對此欄有說明；此欄主要記錄描述。 | — |
| `Keywords` | 關鍵詞 | TEXT | ethernet communication, fabless semiconductor, semiconductors chips, semiconductors maker, semiconductors product, s ... | 官方資料字典對此欄有說明；此欄主要記錄關鍵詞。 | — |
| `TotalRaised` | 累計融資額 | DECIMAL | 66.36 | 記錄累計融資額，通常為金額或資本數值。 | — |
| `Employees` | 員工數 | INTEGER | 10650 | 官方資料字典對此欄有說明；此欄主要記錄員工數。 | — |
| `Exchange` | 交易所 | TEXT(50) | TAE | 官方資料字典對此欄有說明；此欄主要記錄交易所。 | — |
| `Ticker` | 股票代碼 | TEXT(100) | BEZQ | 官方資料字典對此欄有說明；此欄主要記錄股票代碼。 | — |
| `AllIndustries` | 全部Industries | TEXT | General Purpose Semiconductors, Production (Semiconductors) | 官方資料字典對此欄有說明；此欄主要記錄全部Industries。 | — |
| `AlternateOfficeCount` | Alternate辦公室Count | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄Alternate辦公室Count。 | — |
| `ActiveInvestors` | 現有Investors | INTEGER | 14 | 官方資料字典對此欄有說明；此欄主要記錄現有Investors。 | — |
| `FormerInvestors` | 曾用Investors | INTEGER | 4 | 官方資料字典對此欄有說明；此欄主要記錄曾用Investors。 | — |
| `ProfileDataSource` | 檔案Data來源 | TEXT(100) | PitchBook Research | 官方資料字典對此欄有說明；此欄主要記錄檔案Data來源。 | — |
| `PitchBookProfileLink` | PitchBook 頁面連結 | TEXT(255) | https://content.pitchbook.com/profiles/company/10010-89 | 官方資料字典對此欄有說明；此欄主要記錄PitchBook 頁面連結。 | — |


## CompanyAffiliateRelation.csv

**用途**：記錄公司的關聯實體資料。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`AffiliateID`

**可連接到**：可連到 Company.csv；關聯實體鍵，本批資料未提供單獨主表；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 57276-46 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `AffiliateID` | 關聯實體識別碼 | TEXT(20) | 98104-78 | 唯一識別碼，用於記錄關聯實體識別碼。 | 關聯實體鍵，本批資料未提供單獨主表 |
| `RowID` | 列唯一識別碼 | TEXT(255) | 5c69b36b6de6998c2f046a98df0c78c5ee8bfd85db535903478c01abbfda9a53 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 11/11/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AffiliateName` | 關聯實體名稱 | TEXT(255) | Primetech (Katowice) | 官方資料字典對此欄有說明；此欄主要記錄關聯實體名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `AffiliateType` | 關聯實體類型 | TEXT(100) | Sister | 官方資料字典對此欄有說明；此欄主要記錄關聯實體類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `YearFounded` | 年份成立 | INTEGER | 1961 | 官方資料字典對此欄有說明；此欄主要記錄年份成立。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `HQCity` | 總部城市 | TEXT(100) | Katowice | 記錄總部城市相關地理資訊。 | — |
| `HQState_Province` | 總部州或省 | TEXT(100) | Ohio | 記錄總部州或省相關地理資訊。 | — |
| `HQCountry` | 總部國家 | TEXT(50) | Poland | 記錄總部國家相關地理資訊。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Industry` | 產業 | TEXT(100) | Other Commercial Services | 官方資料字典對此欄有說明；此欄主要記錄產業。 | — |


## CompanyBoardSeatHeldRelation.csv

**用途**：記錄公司持有的董事席位。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`PersonID`

**可連接到**：可連到 Company.csv；可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10048-15 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `PersonID` | 人物唯一識別碼 | TEXT(20) | 11368-36P | 唯一識別碼，用於記錄人物唯一識別碼。 | 可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 7a6b5af00cf82eb2d2124df507585aa102a8cb2f530c39de0ef191bd51bd0289 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `PersonName` | 人員名稱 | TEXT(125) | Mary Petrovich | 官方資料字典對此欄有說明；此欄主要記錄人員名稱。 | — |
| `CompanyNameHeld` | 公司名稱持有 | TEXT(255) | AxleTech | 官方資料字典對此欄有說明；此欄主要記錄公司名稱持有。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `StartDate` | 開始日期 | DATE | 10/03/2005 | 記錄開始日期相關日期。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Location` | 地點 | TEXT(100) | Troy, MI | 記錄地點相關地理資訊。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `RoleOnBoard` | 角色董事會 | TEXT(255) | Chairman | 官方資料字典對此欄有說明；此欄主要記錄角色董事會。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Industry` | 產業 | TEXT(100) | Industrial Supplies and Parts | 官方資料字典對此欄有說明；此欄主要記錄產業。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyIDHeld` | 公司識別碼持有 | TEXT(20) | 10017-01 | 官方資料字典對此欄有說明；此欄主要記錄公司識別碼持有。 | 可連到 Company.csv |


## CompanyBuySideRelation.csv

**用途**：記錄公司作為買方參與的交易。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`TargetCompanyID`、`DealID`、`LeadPartnerID`

**可連接到**：可連到 Company.csv；可連到 Deal.csv；通常可連到 Person.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10015-75 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `TargetCompanyID` | 目標公司識別碼 | TEXT(20) | 108291-43 | 唯一識別碼，用於記錄目標公司識別碼。 | 可連到 Company.csv |
| `DealID` | 交易唯一識別碼 | TEXT(20) | 45927-64T | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Deal.csv |
| `LeadPartnerID` | 主導合夥人識別碼 | TEXT(20) | 49750-84P | 官方資料字典對此欄有說明；此欄主要記錄主導合夥人識別碼。 | 通常可連到 Person.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 83fe3d9c7587c9393f5321af17f67482138f99a047f9187de32cad82435d540c | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `TargetCompanyName` | 目標公司名稱 | TEXT(255) | CKEY-FM | 記錄目標公司名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealType` | 交易類型 | TEXT(50) | Buyout/LBO (Add-on) | 官方資料字典對此欄有說明；此欄主要記錄交易類型。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealDate` | 交易完成日期 | DATE | 11/01/1997 | 記錄交易完成日期相關日期。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DealSize` | 交易規模 | DECIMAL | 119.999995 | 官方資料字典對此欄有說明；此欄主要記錄交易規模。 | — |

#### 人物與角色

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `LeadPartner` | 主導合夥人姓名 | TEXT(125) | Jonathan Blanshay | 官方資料字典對此欄有說明；此欄主要記錄主導合夥人姓名。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Industry` | 產業 | TEXT(100) | Broadcasting, Radio and Television | 官方資料字典對此欄有說明；此欄主要記錄產業。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyStage` | 公司階段 | TEXT(50) | Generating Revenue | 官方資料字典對此欄有說明；此欄主要記錄公司階段。 | — |


## CompanyCompetitorRelation.csv

**用途**：記錄公司的競爭對手。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`CompetitorID`

**可連接到**：可連到 Company.csv；通常可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10028-71 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `CompetitorID` | 競爭對手識別碼 | TEXT(20) | 44066-53 | 唯一識別碼，用於記錄競爭對手識別碼。 | 通常可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 78cab49f7e0c6117b16b1a5f70b03bcd5e11e44fe2f596f5d0613eb5d6587977 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 04/20/2023 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompetitorName` | 競爭對手名稱 | TEXT(255) | Credit Agricole | 官方資料字典對此欄有說明；此欄主要記錄競爭對手名稱。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompetitorDescription` | 競爭對手描述 | TEXT | Credit Agricole S.A. is majority-owned by a group of 39 mutually owned, regional French banks, and together, they fo ... | 官方資料字典對此欄有說明；此欄主要記錄競爭對手描述。 | — |
| `CompetitorPrimaryIndustrySector` | 競爭對手主要產業部門 | TEXT(100) | Financial Services | 官方資料字典對此欄有說明；此欄主要記錄競爭對手主要產業部門。 | — |
| `CompetitorPrimaryIndustryGroup` | 競爭對手主要產業群組 | TEXT(100) | Commercial Banks | 官方資料字典對此欄有說明；此欄主要記錄競爭對手主要產業群組。 | — |
| `CompetitorPrimaryIndustryCode` | 競爭對手主要產業代碼 | TEXT(100) | International Banks | 官方資料字典對此欄有說明；此欄主要記錄競爭對手主要產業代碼。 | — |
| `CompetitorAllIndustries` | 競爭對手全部Industries | TEXT | International Banks | 官方資料字典對此欄有說明；此欄主要記錄競爭對手全部Industries。 | — |
| `CompetitorVerticals` | 競爭對手垂直領域 | TEXT | AdTech, Marketing Tech, SaaS | 官方資料字典對此欄有說明；此欄主要記錄競爭對手垂直領域。 | — |


## CompanyEmployeeHistoryRelation.csv

**用途**：記錄公司的員工數歷史。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | ab513113081e6f7c6af1a611e400a5a00874a9965393617a25466596a57caee7 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Date` | 日期 | DATE | 12/31/1997 | 記錄日期相關日期。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `EmployeeCount` | 員工Count | INTEGER | 299 | 官方資料字典對此欄有說明；此欄主要記錄員工Count。 | — |


## CompanyEntityTypeRelation.csv

**用途**：記錄公司的實體類型分類。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | f0da1140310c7ca38a77d9ef0a525b2e32fc36d8ca557308908288d1d7ebb001 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `EntityType` | 實體類型 | TEXT(255) | Investor | 官方資料字典對此欄有說明；此欄主要記錄實體類型。 | — |
| `IsPrimary` | Is主要 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Is主要。 | — |


## CompanyFinancialRelation.csv

**用途**：記錄公司的財務資料。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10613-80 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 45da8bf966d92d28c729d6f130c1fbc3a65d990e0c9934abd05448b7cf324382 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FiscalPeriod` | 財務期間 | TEXT(10) | TTM 4Q2017 | 官方資料字典對此欄有說明；此欄主要記錄財務期間。 | — |
| `PeriodEndDate` | 期間結束日期 | DATE | 05/31/2017 | 記錄期間結束日期相關地理資訊。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Revenue` | 營收 | DECIMAL | 57.13536737 | 記錄營收相關地理資訊。 | — |
| `GrossProfit` | 毛利 | DECIMAL | 50.08439681 | 記錄毛利相關地理資訊。 | — |
| `NetIncome` | 淨利 | DECIMAL | 1213.0 | 記錄淨利相關地理資訊。 | — |
| `EnterpriseValue` | 企業價值 | DECIMAL | 28686.370953 | 記錄企業價值相關地理資訊。 | — |
| `EBITDA` | EBITDA | DECIMAL | 33.85719035 | 記錄EBITDA相關地理資訊。 | — |
| `EBIT` | EBIT | DECIMAL | 33.20247564 | 官方資料字典對此欄有說明；此欄主要記錄EBIT。 | — |
| `NetDebt` | 淨負債 | DECIMAL | 0.0 | 官方資料字典對此欄有說明；此欄主要記錄淨負債。 | — |


## CompanyIndustryRelation.csv

**用途**：記錄公司的產業分類。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | d3b1e0be4566d147e37286033657a49238d7c90e8c7ff746760185f63d8b9b5d | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 05/30/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `IsPrimary` | Is主要 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Is主要。 | — |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `IndustrySector` | 產業部門 | TEXT(100) | Information Technology | 官方資料字典對此欄有說明；此欄主要記錄產業部門。 | — |
| `IndustryGroup` | 產業群組 | TEXT(100) | Semiconductors | 官方資料字典對此欄有說明；此欄主要記錄產業群組。 | — |
| `IndustryCode` | 產業代碼 | TEXT(100) | Production (Semiconductors) | 官方資料字典對此欄有說明；此欄主要記錄產業代碼。 | — |


## CompanyInvestorRelation.csv

**用途**：記錄公司關聯的投資機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`InvestorID`

**可連接到**：可連到 Company.csv；可連到 Investor.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10203-85 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `InvestorID` | 投資機構唯一識別碼 | TEXT(20) | 11182-15 | 唯一識別碼，用於記錄投資機構唯一識別碼。 | 可連到 Investor.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | d66d3fdad4eeb2ce7f3f4ba84ffa3ebabe70a838e7174c0ad918110317efe537 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyName` | 公司名稱 | TEXT(255) | Jacobson Companies | 記錄公司名稱。 | — |
| `InvestorName` | 投資機構名稱 | TEXT(255) | LongueVue Capital | 官方資料字典對此欄有說明；此欄主要記錄投資機構名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorStatus` | 投資方狀態 | TEXT(50) | Former | 記錄投資方狀態，用來描述當前狀態或標記。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorWebsite` | 投資機構網站 | TEXT | www.lvcpartners.com | 記錄投資機構網站。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Holding` | Holding | TEXT(255) | Minority | 官方資料字典對此欄有說明；此欄主要記錄Holding。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `InvestorSince` | 投資機構自 | DATE | 03/01/2013 | 官方資料字典對此欄有說明；此欄主要記錄投資機構自。 | — |


## CompanyLocationRelation.csv

**用途**：記錄公司的地點與辦公室資訊。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10011-25 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
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


## CompanyMorningstarCodeRelation.csv

**用途**：記錄公司的 Morningstar 分類代碼。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 104372-56 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 737d9a26c22f932502934616ad054f607ac0c3fd1bc798c32d1d48a2bd7753bf | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 11/02/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `MorningstarCode` | Morningstar代碼 | TEXT(100) | 20525040 | 官方資料字典對此欄有說明；此欄主要記錄Morningstar代碼。 | — |
| `MorningstarDescription` | Morningstar描述 | TEXT(200) | Packaged Foods | 官方資料字典對此欄有說明；此欄主要記錄Morningstar描述。 | — |


## CompanyNaicsCodeRelation.csv

**用途**：記錄公司的 NAICS 分類代碼。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | e3b5de08d1325067f854fc8ca85618010220c1279442d97be5c2075ea8014894 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 05/30/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `NaicsSectorCode` | NAICS部門代碼 | TEXT(20) | 33 | 記錄NAICS部門代碼相關地理資訊。 | — |
| `NaicsSectorDescription` | NAICS部門描述 | TEXT(255) | Manufacturing | 記錄NAICS部門描述相關地理資訊。 | — |
| `NaicsIndustryCode` | NAICS產業代碼 | TEXT(20) | 334413 | 記錄NAICS產業代碼相關地理資訊。 | — |
| `NaicsIndustryDescription` | NAICS產業描述 | TEXT(255) | Semiconductor and Related Device Manufacturing | 記錄NAICS產業描述相關地理資訊。 | — |


## CompanyPublicFinancialRelation.csv

**用途**：記錄公司的公開財報欄位。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 55089-28 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 4953abc4663c1bf46dd5d97a6076c59ae9ced99ddcf27ad0408ffcfcdad98700 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 08/02/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FiscalPeriodType` | 財務期間類型 | TEXT(10) | TTM | 記錄財務期間類型相關地理資訊。 | — |

#### 時間

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `FiscalPeriod` | 財務期間 | DATE | 03/31/2023 | 記錄財務期間相關地理資訊。 | — |
| `CashAndCashEquivalentsBeginningOfPeriod` | 現金And現金EquivalentsBeginningOf期間 | DECIMAL | 1483.61447593 | 記錄現金And現金EquivalentsBeginningOf期間相關地理資訊。 | — |
| `CashAndCashEquivalentsEndOfPeriod` | 現金And現金Equivalents結束Of期間 | DECIMAL | 1322.60781271 | 記錄現金And現金Equivalents結束Of期間相關地理資訊。 | — |

#### 金額與估值

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `TotalRevenue` | 總營收 | DECIMAL | 14365.19498744 | 記錄總營收，通常為比例或比率。 | — |
| `GrossProfit` | 毛利 | DECIMAL | 4990.06706268 | 官方資料字典對此欄有說明；此欄主要記錄毛利。 | — |
| `TotalOperatingProfit_Loss` | 總營運利潤損失 | DECIMAL | 672.55017643 | 官方資料字典對此欄有說明；此欄主要記錄總營運利潤損失。 | — |
| `EarningsBeforeInterestTaxDepreciationAmortization_EBITDA` | 收益前利息稅DepreciationAmortizationEBITDA | DECIMAL | 1436.60377821 | 官方資料字典對此欄有說明；此欄主要記錄收益前利息稅DepreciationAmortizationEBITDA。 | — |
| `EarningsBeforeInterestandTax_EBIT` | 收益前Interestand稅EBIT | DECIMAL | 740.2145515 | 官方資料字典對此欄有說明；此欄主要記錄收益前Interestand稅EBIT。 | — |
| `NetIncomeFromContinuingOperations` | 淨收益From持續經營營運 | DECIMAL | 438.85524402 | 記錄淨收益From持續經營營運，通常為比例或比率。 | — |
| `NetIncomeAvailabletoCommonStockholders` | 淨收益Availableto普通股東 | DECIMAL | 437.53085233 | 官方資料字典對此欄有說明；此欄主要記錄淨收益Availableto普通股東。 | — |
| `NormalizedIncome` | 標準化收益 | DECIMAL | 400.6886837 | 記錄標準化收益，通常為比例或比率。 | — |
| `DilutedWeightedAverageSharesOutstanding` | 稀釋後加權平均股數流通在外 | DECIMAL | 2033900000.0 | 官方資料字典對此欄有說明；此欄主要記錄稀釋後加權平均股數流通在外。 | — |
| `TotalDebt` | 總債務 | DECIMAL | 4493.32441663 | 記錄總債務，通常為金額或資本數值。 | — |
| `WorkingCapital` | Working資本 | DECIMAL | -682.91595461 | 官方資料字典對此欄有說明；此欄主要記錄Working資本。 | — |
| `CapitalExpenditure_Calc` | 資本ExpenditureCalc | DECIMAL | 493.99809772 | 記錄資本ExpenditureCalc，通常為金額或資本數值。 | — |
| `EBITDAMargin` | EBITDAMargin | DECIMAL | 10.00058669 | 記錄EBITDAMargin，通常為比例或比率。 | — |
| `RevenuePercentGrowth` | 營收百分比Growth | DECIMAL | 9.61130353 | 官方資料字典對此欄有說明；此欄主要記錄營收百分比Growth。 | — |
| `NetIncomeAvailableToCommonStockholdersSequentialPercentGrowth` | 淨收益可用普通股東Sequential百分比Growth | DECIMAL | -42.09275086 | 官方資料字典對此欄有說明；此欄主要記錄淨收益可用普通股東Sequential百分比Growth。 | — |
| `CurrentRatio` | 當前比率 | DECIMAL | 0.79626072 | 記錄當前比率，通常為比例或比率。 | — |
| `QuickRatio` | 速動比率 | DECIMAL | 0.46755838 | 記錄速動比率，通常為比例或比率。 | — |
| `DebtToEquity` | 債務權益 | DECIMAL | 1.18770516 | 記錄債務權益，通常為金額或資本數值。 | — |
| `TotalDebtToEquity` | 總債務權益 | DECIMAL | 1.35332736 | 記錄總債務權益，通常為比例或比率。 | — |
| `NormalizedReturnOnInvestedCapital` | 標準化回報Invested資本 | DECIMAL | 6.57343714 | 記錄標準化回報Invested資本，通常為金額或資本數值。 | — |
| `EnterpriseValue` | 企業價值 | DECIMAL | 7322.381516 | 官方資料字典對此欄有說明；此欄主要記錄企業價值。 | — |
| `EnterpriseValueToRevenue` | Enterprise價值營收 | DECIMAL | 0.50680869 | 記錄Enterprise價值營收，通常為比例或比率。 | — |
| `EnterpriseValueToEBIT` | Enterprise價值EBIT | DECIMAL | 13.89213074 | 記錄Enterprise價值EBIT，通常為比例或比率。 | — |
| `EnterpriseValueToEBITDA` | Enterprise價值EBITDA | DECIMAL | 6.23281624 | 記錄Enterprise價值EBITDA，通常為比例或比率。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `DilutedEPSfromContinuingOperations` | 稀釋後EPSfrom持續經營營運 | DECIMAL | 0.21551465 | 記錄稀釋後EPSfrom持續經營營運，通常為比例或比率。 | — |
| `NormalizedDilutedEPS` | 標準化稀釋後EPS | DECIMAL | 0.19745476 | 記錄標準化稀釋後EPS，通常為比例或比率。 | — |
| `TotalCurrentAssets` | 總當前資產 | DECIMAL | 2668.99507107 | 官方資料字典對此欄有說明；此欄主要記錄總當前資產。 | — |
| `NetPropertyPlantandEquipment` | 淨PropertyPlantandEquipment | DECIMAL | 6444.84902614 | 記錄淨PropertyPlantandEquipment，通常為比例或比率。 | — |
| `TotalNonCurrentAssets` | 總非當前資產 | DECIMAL | 8598.74662618 | 官方資料字典對此欄有說明；此欄主要記錄總非當前資產。 | — |
| `TotalAssets` | 總資產 | DECIMAL | 11267.74169725 | 官方資料字典對此欄有說明；此欄主要記錄總資產。 | — |
| `TotalCurrentLiabilities` | 總當前負債 | DECIMAL | 3351.91102568 | 官方資料字典對此欄有說明；此欄主要記錄總當前負債。 | — |
| `TotalNonCurrentLiabilities` | 總非當前負債 | DECIMAL | 4595.62557342 | 官方資料字典對此欄有說明；此欄主要記錄總非當前負債。 | — |
| `TotalLiabilities` | 總負債 | DECIMAL | 7947.5365991 | 官方資料字典對此欄有說明；此欄主要記錄總負債。 | — |
| `TotalEquity` | 總權益 | DECIMAL | 3320.20509816 | 官方資料字典對此欄有說明；此欄主要記錄總權益。 | — |
| `EquityAttributabletoParentStockholders` | 權益Attributableto母股東 | DECIMAL | 3314.75564186 | 官方資料字典對此欄有說明；此欄主要記錄權益Attributableto母股東。 | — |
| `CashFlowFromOperatingActivitiesIndirect` | 現金現金流From營運ActivitiesIndirect | DECIMAL | 1239.99181293 | 官方資料字典對此欄有說明；此欄主要記錄現金現金流From營運ActivitiesIndirect。 | — |
| `CashFlowFromInvestingActivities` | 現金現金流FromInvestingActivities | DECIMAL | -621.98249399 | 記錄現金現金流FromInvestingActivities，通常為金額或資本數值。 | — |
| `CashFlowFromFinancingActivities` | 現金現金流From融資Activities | DECIMAL | -775.13033223 | 官方資料字典對此欄有說明；此欄主要記錄現金現金流From融資Activities。 | — |
| `ChangeinCash` | Changein現金 | DECIMAL | -157.12101329 | 記錄Changein現金相關地理資訊。 | — |
| `IssuanceOf__PaymentsForCommonStockNet` | IssuanceOf付款For普通股票淨 | DECIMAL | -0.12039924 | 官方資料字典對此欄有說明；此欄主要記錄IssuanceOf付款For普通股票淨。 | — |
| `TotalAssetTurnover` | 總資產Turnover | DECIMAL | 1.25290233 | 記錄總資產Turnover，通常為比例或比率。 | — |
| `NormalizedReturnOnEquity` | 標準化回報權益 | DECIMAL | 11.446339 | 記錄標準化回報權益，通常為比例或比率。 | — |
| `NormalizedReturnOnAssets` | 標準化回報資產 | DECIMAL | 3.49472309 | 記錄標準化回報資產，通常為比例或比率。 | — |
| `Preliminary` | 初步 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄初步。 | — |
| `Original` | Original | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Original。 | — |
| `Restated` | 重述 | TEXT(10) | Yes | 官方資料字典對此欄有說明；此欄主要記錄重述。 | — |
| `Calculated` | Calculated | TEXT(10) | Yes | 官方資料字典對此欄有說明；此欄主要記錄Calculated。 | — |


## CompanyServiceProviderRelation.csv

**用途**：記錄公司關聯的服務機構。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`ServiceProviderID`

**可連接到**：可連到 Company.csv；可連到 ServiceProvider.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10040-05 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `ServiceProviderID` | 服務機構唯一識別碼 | TEXT(20) | 55674-19 | 唯一識別碼，用於記錄服務機構唯一識別碼。 | 可連到 ServiceProvider.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | d9c699fc9058aa6fc963f26c9d9ddfb9bb35deda8dd958ac3fc03cb4a14148ed | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 02/24/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderName` | 服務機構名稱 | TEXT(255) | Sager Company | 官方資料字典對此欄有說明；此欄主要記錄服務機構名稱。 | — |

#### 狀態與分類

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProviderType` | 服務機構類型 | TEXT(255) | Recruiting Firm | 官方資料字典對此欄有說明；此欄主要記錄服務機構類型。 | — |

#### 文字描述

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `ServiceProvided` | 服務提供 | TEXT(50) | Advisor: General | 官方資料字典對此欄有說明；此欄主要記錄服務提供。 | — |


## CompanySicCodeRelation.csv

**用途**：記錄公司的 SIC 分類代碼。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10011-16 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | 98013ef1725cee76314737fbeccb3f95c19ed115b2fb150e625cf5517ed57cc5 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 05/19/2023 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SicCode` | SIC代碼 | TEXT(40) | 2899 | 官方資料字典對此欄有說明；此欄主要記錄SIC代碼。 | — |
| `SicDescription` | SIC描述 | TEXT(255) | Chemicals and Chemical Preparations, Not Elsewhere Classified | 官方資料字典對此欄有說明；此欄主要記錄SIC描述。 | — |


## CompanySimilarRelation.csv

**用途**：記錄與公司相似的公司與相似度。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`、`SimilarCompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 104373-55 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `SimilarCompanyID` | 相似公司識別碼 | TEXT(20) | 529121-71 | 唯一識別碼，用於記錄相似公司識別碼。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | a60f5bdcd9bdac47de3d2c0a8f12bb6716f8e5c76a454e81f2187c90a55d7780 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 09/13/2025 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 名稱與別名

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SimilarCompanyName` | 相似公司名稱 | TEXT(255) | Power RFP | 官方資料字典對此欄有說明；此欄主要記錄相似公司名稱。 | — |

#### 地點與聯絡

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SimilarCompanyHQLocation` | 相似公司總部地點 | TEXT(100) | Vancouver, Canada | 記錄相似公司總部地點相關地理資訊。 | — |
| `SimilarCompanyHQAddressLine1` | 相似公司總部地址Line1 | TEXT(100) | 30, Saemunan-ro 3-gil | 官方資料字典對此欄有說明；此欄主要記錄相似公司總部地址Line1。 | — |
| `SimilarCompanyHQAddressLine2` | 相似公司總部地址Line2 | TEXT(100) | Naesu-dong, Daewoo Building, Jongno-gu | 官方資料字典對此欄有說明；此欄主要記錄相似公司總部地址Line2。 | — |
| `SimilarCompanyHQCity` | 相似公司總部城市 | TEXT(100) | Vancouver | 記錄相似公司總部城市相關地理資訊。 | — |
| `SimilarCompanyHQState_Province` | 相似公司總部州Province | TEXT(100) | British Columbia | 記錄相似公司總部州Province相關地理資訊。 | — |
| `SimilarCompanyHQPostCode` | 相似公司總部郵遞代碼 | TEXT(30) | 4440 | 官方資料字典對此欄有說明；此欄主要記錄相似公司總部郵遞代碼。 | — |
| `SimilarCompanyHQCountry` | 相似公司總部國家 | TEXT(50) | Canada | 記錄相似公司總部國家相關地理資訊。 | — |

#### 關係與持有

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `SimilarityRank` | 相似度Rank | INTEGER | 1 | 官方資料字典對此欄有說明；此欄主要記錄相似度Rank。 | — |
| `SimilarityScore` | 相似度Score | DECIMAL | 95.56 | 官方資料字典對此欄有說明；此欄主要記錄相似度Score。 | — |
| `IsCompetitor` | Is競爭對手 | TEXT(10) | No | 官方資料字典對此欄有說明；此欄主要記錄Is競爭對手。 | — |
| `SimilarDescription` | 相似描述 | TEXT | Developer of a procurement management platform designed for small businesses and professionals to organize and coord ... | 官方資料字典對此欄有說明；此欄主要記錄相似描述。 | — |
| `SimilarPrimaryIndustrySector` | 相似主要產業部門 | TEXT(100) | Information Technology | 官方資料字典對此欄有說明；此欄主要記錄相似主要產業部門。 | — |
| `SimilarPrimaryIndustryGroup` | 相似主要產業群組 | TEXT(100) | Software | 官方資料字典對此欄有說明；此欄主要記錄相似主要產業群組。 | — |
| `SimilarPrimaryIndustryCode` | 相似主要產業代碼 | TEXT(100) | Business/Productivity Software | 官方資料字典對此欄有說明；此欄主要記錄相似主要產業代碼。 | — |
| `SimilarAllIndustries` | 相似全部Industries | TEXT | Business/Productivity Software, Financial Software | 官方資料字典對此欄有說明；此欄主要記錄相似全部Industries。 | — |
| `SimilarVerticals` | 相似垂直領域 | TEXT | FinTech, SaaS | 官方資料字典對此欄有說明；此欄主要記錄相似垂直領域。 | — |


## CompanyVerticalRelation.csv

**用途**：記錄公司的垂直領域標籤。

**主鍵**：此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。

**主要關聯鍵**：`CompanyID`

**可連接到**：可連到 Company.csv；列級稽核鍵；列級更新時間

### 欄位分組

#### 識別與稽核

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `CompanyID` | 公司唯一識別碼 | TEXT(20) | 10010-89 | 唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。 | 可連到 Company.csv |
| `RowID` | 列唯一識別碼 | TEXT(255) | c565072cccf77d7a228dae9919eff35fc494397e2cd2b7776e90233293197729 | 唯一識別碼，用於記錄列唯一識別碼。 | 列級稽核鍵 |
| `LastUpdated` | 最後更新日期 | DATE | 05/30/2022 | 記錄最後更新日期相關日期。 | 列級更新時間 |

#### 產業與標籤

| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |
| --- | --- | --- | --- | --- | --- |
| `Vertical` | 垂直領域 | TEXT(255) | Manufacturing | 官方資料字典對此欄有說明；此欄主要記錄垂直領域。 | — |
