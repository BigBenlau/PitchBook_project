# 7 個核心對象總覽

本文件彙整 PitchBook `data/` 中 7 個核心主表的規模、主鍵、relation 表覆蓋情況，以及每個主表主要能回答什麼問題。

說明：

- 行數統計為 `csv` 中的資料列數
- 不含第一行 header
- `直接相關 relation 表數` 的口徑是：該 relation 表中包含該核心主表的主鍵欄位
- 統計基於目前工作區中的現有檔案內容

## 核心主表總表

| 核心對象 | 主表 CSV | 主鍵 | 資料行數 | 欄位數 | 直接相關 relation 表數 |
| --- | --- | --- | ---: | ---: | ---: |
| 公司 | `Company.csv` | `CompanyID` | 723,639 | 100 | 25 |
| 交易 | `Deal.csv` | `DealID` | 2,074,146 | 95 | 14 |
| 投資機構 | `Investor.csv` | `InvestorID` | 354,664 | 111 | 21 |
| 基金 | `Fund.csv` | `FundID` | 127,927 | 48 | 13 |
| 有限合夥人 | `LimitedPartner.csv` | `LimitedPartnerID` | 25,835 | 105 | 6 |
| 人物 | `Person.csv` | `PersonID` | 1,746,938 | 42 | 11 |
| 服務機構 | `ServiceProvider.csv` | `ServiceProviderID` | 54,969 | 66 | 9 |

## 總體觀察

- `Deal.csv` 是最大主表，表示這批資料非常強調交易事件。
- `Person.csv` 也非常大，說明人物、職位、董事會與關聯角色是 PitchBook 的重要資訊層。
- `Company.csv`、`Investor.csv`、`Fund.csv` 構成市場主體與資本行為的核心骨架。
- `LimitedPartner.csv` 行數較小，但它是理解資金來源、基金募資與資本鏈條不可或缺的一層。
- relation 表的設計使這批資料更像「知識圖譜」或「實體-關係資料庫」，不是單一主表分析型資料。

## 各核心對象說明

### 1. 公司 Company

- 主表：`Company.csv`
- 主鍵：`CompanyID`
- 行數：723,639
- 欄位數：100
- 直接相關 relation 表數：25

可以了解的內容：

- 公司做什麼業務
- 所屬產業、vertical、emerging space
- 地點、聯絡資訊、基本財務摘要
- 融資狀態、首次融資、最近融資、估值
- 相關投資人、服務機構、相似公司、競爭對手

直接相關 relation 表：

- `CompanyAffiliateRelation.csv`
- `CompanyBoardSeatHeldRelation.csv`
- `CompanyBuySideRelation.csv`
- `CompanyCompetitorRelation.csv`
- `CompanyEmployeeHistoryRelation.csv`
- `CompanyEntityTypeRelation.csv`
- `CompanyFinancialRelation.csv`
- `CompanyIndustryRelation.csv`
- `CompanyInvestorRelation.csv`
- `CompanyLocationRelation.csv`
- `CompanyMorningstarCodeRelation.csv`
- `CompanyNaicsCodeRelation.csv`
- `CompanyPublicFinancialRelation.csv`
- `CompanyServiceProviderRelation.csv`
- `CompanySicCodeRelation.csv`
- `CompanySimilarRelation.csv`
- `CompanyVerticalRelation.csv`
- `FundInvestmentRelation.csv`
- `InvestorExitRelation.csv`
- `InvestorInvestmentRelation.csv`
- `LPDirectInvestmentRelation.csv`
- `PersonAffiliatedDealRelation.csv`
- `PersonBoardSeatRelation.csv`
- `ServiceProviderCompDealRelation.csv`
- `ServiceProviderCompanyRelation.csv`

### 2. 交易 Deal

- 主表：`Deal.csv`
- 主鍵：`DealID`
- 行數：2,074,146
- 欄位數：95
- 直接相關 relation 表數：14

可以了解的內容：

- 某家公司發生過哪些融資、併購、退出、債務交易
- 每筆交易的時間、類型、規模、估值與摘要
- 參與該交易的投資方、賣方、貸方、服務方

直接相關 relation 表：

- `CompanyBuySideRelation.csv`
- `DealCapTableRelation.csv`
- `DealDebtLenderRelation.csv`
- `DealDistribBeneficiaryRelation.csv`
- `DealInvestorRelation.csv`
- `DealSellerRelation.csv`
- `DealServiceProviderRelation.csv`
- `DealTrancheRelation.csv`
- `FundInvestmentRelation.csv`
- `InvestorExitRelation.csv`
- `InvestorInvestmentRelation.csv`
- `PersonAffiliatedDealRelation.csv`
- `ServiceProviderCompDealRelation.csv`
- `ServiceProviderInvestorRelation.csv`

### 3. 投資機構 Investor

- 主表：`Investor.csv`
- 主鍵：`InvestorID`
- 行數：354,664
- 欄位數：111
- 直接相關 relation 表數：21

可以了解的內容：

- 投資機構是什麼類型、偏好什麼賽道與交易
- 管理資產規模、乾粉、投資活動與最近投資
- 投過哪些公司、與哪些基金或 LP 有關聯
- 哪些 lead partner 屬於該機構

直接相關 relation 表：

- `CompanyInvestorRelation.csv`
- `DealInvestorRelation.csv`
- `DealTrancheRelation.csv`
- `FundInvestorRelation.csv`
- `InvestorAffiliateRelation.csv`
- `InvestorCoInvestorRelation.csv`
- `InvestorEntityTypeRelation.csv`
- `InvestorExitRelation.csv`
- `InvestorFundRelation.csv`
- `InvestorInvestDealRelation.csv`
- `InvestorInvestIndustryCodeRelation.csv`
- `InvestorInvestIndustrySectorCodeRelation.csv`
- `InvestorInvestYearRelation.csv`
- `InvestorInvestmentRelation.csv`
- `InvestorLeadPartnerRelation.csv`
- `InvestorLimitedPartnerRelation.csv`
- `InvestorLocationRelation.csv`
- `InvestorServiceProviderRelation.csv`
- `PersonAffiliatedFundRelation.csv`
- `ServiceProviderInvFundRelation.csv`
- `ServiceProviderInvestorRelation.csv`

### 4. 基金 Fund

- 主表：`Fund.csv`
- 主鍵：`FundID`
- 行數：127,927
- 欄位數：48
- 直接相關 relation 表數：13

可以了解的內容：

- 基金規模、狀態、vintage、類型與策略偏好
- 投過哪些公司
- 關聯哪些 investor、LP、服務機構與團隊成員
- 基金回報、close history 與回報來源

直接相關 relation 表：

- `FundCloseHistoryRelation.csv`
- `FundInvestmentRelation.csv`
- `FundInvestorRelation.csv`
- `FundLPCommitmentRelation.csv`
- `FundLimitedPartnerRelation.csv`
- `FundReturnRelation.csv`
- `FundReturnReporterRelation.csv`
- `FundServiceProviderRelation.csv`
- `FundTeamRelation.csv`
- `InvestorFundRelation.csv`
- `LPFundCommitmentRelation.csv`
- `PersonAffiliatedFundRelation.csv`
- `ServiceProviderInvFundRelation.csv`

### 5. 有限合夥人 LimitedPartner

- 主表：`LimitedPartner.csv`
- 主鍵：`LimitedPartnerID`
- 行數：25,835
- 欄位數：105
- 直接相關 relation 表數：6

可以了解的內容：

- LP 的基本資料、資產配置與偏好
- 對基金的承諾出資
- 是否做 direct investment
- 與 investor、服務機構的關聯

直接相關 relation 表：

- `FundLPCommitmentRelation.csv`
- `FundLimitedPartnerRelation.csv`
- `InvestorLimitedPartnerRelation.csv`
- `LPDirectInvestmentRelation.csv`
- `LPFundCommitmentRelation.csv`
- `ServiceProviderLPRelation.csv`

### 6. 人物 Person

- 主表：`Person.csv`
- 主鍵：`PersonID`
- 行數：1,746,938
- 欄位數：42
- 直接相關 relation 表數：11

可以了解的內容：

- 個人的基本資料與主要任職
- 任職經歷、教育背景、董事席位、顧問角色
- 與 deal、fund、company 的人員層關聯

直接相關 relation 表：

- `CompanyBoardSeatHeldRelation.csv`
- `EntityBoardSeatHeldRelation.csv`
- `EntityBoardTeamRelation.csv`
- `FundTeamRelation.csv`
- `InvestorLeadPartnerRelation.csv`
- `PersonAdvisoryRelation.csv`
- `PersonAffiliatedDealRelation.csv`
- `PersonAffiliatedFundRelation.csv`
- `PersonBoardSeatRelation.csv`
- `PersonEducationRelation.csv`
- `PersonPositionRelation.csv`

### 7. 服務機構 ServiceProvider

- 主表：`ServiceProvider.csv`
- 主鍵：`ServiceProviderID`
- 行數：54,969
- 欄位數：66
- 直接相關 relation 表數：9

可以了解的內容：

- 服務機構的類型、描述、服務範圍
- 服務過哪些公司、交易、投資機構、基金、LP
- 常出現在什麼類型的交易場景

直接相關 relation 表：

- `CompanyServiceProviderRelation.csv`
- `DealServiceProviderRelation.csv`
- `FundServiceProviderRelation.csv`
- `InvestorServiceProviderRelation.csv`
- `ServiceProviderCompDealRelation.csv`
- `ServiceProviderCompanyRelation.csv`
- `ServiceProviderInvFundRelation.csv`
- `ServiceProviderInvestorRelation.csv`
- `ServiceProviderLPRelation.csv`

## 如何使用這頁總覽

- 如果你要先理解市場主體，先看 `Company.csv`、`Investor.csv`、`Fund.csv`
- 如果你要先理解事件流，先看 `Deal.csv`
- 如果你要理解資本來源，先看 `Fund.csv` 與 `LimitedPartner.csv`
- 如果你要做人脈、董事會、lead partner 分析，先看 `Person.csv`
- 如果你要補充中介機構與生態服務網路，先看 `ServiceProvider.csv`
