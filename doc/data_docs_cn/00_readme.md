# 資料集閱讀指南

本資料夾整理 `data/` 內的正式 PitchBook CSV 結構說明，協助快速理解有哪些表、每個表在做什麼、欄位如何分組，以及不同表之間如何連接。

## 使用原則

- 文件內容使用中文，檔名與欄位名保留英文。
- 依正式 CSV 的 header 與官方 Excel data dictionary 整理；為補充真實樣本值，會掃描每個 CSV 前 5000 行以抓取每欄第一個非空值。
- 所有 `_10.csv` 一律忽略，因為它們是 sample，不屬於正式資料集。
- 若官方 dictionary 未提供欄位說明，文件中會明確標記為「推定」。

## 正式資料表總覽

- 正式 CSV 總數：71
- 主表數量：7
- Relation 表數量：64

## 建議閱讀順序

1. 先看主表：`Company`、`Deal`、`Investor`、`Fund`、`LimitedPartner`、`Person`、`ServiceProvider`。
2. 再看各主題 relation 表，理解一對多與多對多的延伸資料。
3. 最後看 `08_relationships_and_joins.md` 與 `09_column_groups.md`，建立跨表視角。

## 主題文件

- `01_core_entity_row_counts_and_summary.md`：7 個核心對象主表的完整總覽，包含行數、欄位數與 relation 表覆蓋。
- `02_company.md`：公司主表與所有公司相關 relation 表。
- `03_deal.md`：交易主表與所有交易相關 relation 表。
- `04_investor.md`：投資機構主表與所有投資機構相關 relation 表。
- `05_fund_lp.md`：基金、LP 與出資/回報相關表。
- `06_person_entity.md`：人物表與 `Entity*Relation` 泛實體關係。
- `07_service_provider.md`：服務機構與相關關係表。
- `08_relationships_and_joins.md`：主鍵、外鍵與常見 join 路徑。
- `09_column_groups.md`：跨表同類欄位分組索引。

## 正式 CSV 一覽

| CSV | 類型 | 欄位數 | 用途摘要 |
| --- | --- | --- | --- |
| `Company.csv` | 主表 | 100 | 公司主表，記錄公司的基本資料、融資狀態、聯絡資訊與最近財務摘要。 |
| `CompanyAffiliateRelation.csv` | Relation | 11 | 記錄公司的關聯實體資料。 |
| `CompanyBoardSeatHeldRelation.csv` | Relation | 11 | 記錄公司持有的董事席位。 |
| `CompanyBuySideRelation.csv` | Relation | 13 | 記錄公司作為買方參與的交易。 |
| `CompanyCompetitorRelation.csv` | Relation | 11 | 記錄公司的競爭對手。 |
| `CompanyEmployeeHistoryRelation.csv` | Relation | 5 | 記錄公司的員工數歷史。 |
| `CompanyEntityTypeRelation.csv` | Relation | 5 | 記錄公司的實體類型分類。 |
| `CompanyFinancialRelation.csv` | Relation | 12 | 記錄公司的財務資料。 |
| `CompanyIndustryRelation.csv` | Relation | 7 | 記錄公司的產業分類。 |
| `CompanyInvestorRelation.csv` | Relation | 10 | 記錄公司關聯的投資機構。 |
| `CompanyLocationRelation.csv` | Relation | 14 | 記錄公司的地點與辦公室資訊。 |
| `CompanyMorningstarCodeRelation.csv` | Relation | 5 | 記錄公司的 Morningstar 分類代碼。 |
| `CompanyNaicsCodeRelation.csv` | Relation | 7 | 記錄公司的 NAICS 分類代碼。 |
| `CompanyPublicFinancialRelation.csv` | Relation | 54 | 記錄公司的公開財報欄位。 |
| `CompanyServiceProviderRelation.csv` | Relation | 7 | 記錄公司關聯的服務機構。 |
| `CompanySicCodeRelation.csv` | Relation | 5 | 記錄公司的 SIC 分類代碼。 |
| `CompanySimilarRelation.csv` | Relation | 21 | 記錄與公司相似的公司與相似度。 |
| `CompanyVerticalRelation.csv` | Relation | 4 | 記錄公司的垂直領域標籤。 |
| `Deal.csv` | 主表 | 95 | 交易主表，記錄公司各輪融資、併購或退出事件的基本資訊。 |
| `DealCapTableRelation.csv` | Relation | 26 | 記錄交易相關的股權結構與條款欄位。此表未在官方 Excel 中提供完整欄位字典，以下說明依欄位名推定。 |
| `DealDebtLenderRelation.csv` | Relation | 42 | 記錄交易中的債務貸方與借款條件。 |
| `DealDistribBeneficiaryRelation.csv` | Relation | 15 | 記錄交易分配的受益方。 |
| `DealInvestorRelation.csv` | Relation | 13 | 記錄交易關聯的投資機構。 |
| `DealSellerRelation.csv` | Relation | 13 | 記錄交易中的出售方或退出方。 |
| `DealServiceProviderRelation.csv` | Relation | 15 | 記錄交易關聯的服務機構。 |
| `DealTrancheRelation.csv` | Relation | 16 | 記錄交易的分批 tranche 資訊。 |
| `EntityAffiliateRelation.csv` | Relation | 12 | 記錄泛實體的關聯實體資料。 |
| `EntityBoardSeatHeldRelation.csv` | Relation | 11 | 記錄泛實體持有的董事席位。 |
| `EntityBoardTeamRelation.csv` | Relation | 14 | 記錄泛實體的團隊與董事會資料。 |
| `EntityLocationRelation.csv` | Relation | 14 | 記錄泛實體的地點與辦公室資訊。 |
| `Fund.csv` | 主表 | 48 | 基金主表，記錄基金規模、募集狀態、偏好策略與乾粉資訊。 |
| `FundCloseHistoryRelation.csv` | Relation | 6 | 記錄基金歷次 closing / close 歷史。 |
| `FundInvestmentRelation.csv` | Relation | 16 | 記錄基金的投資明細。 |
| `FundInvestorRelation.csv` | Relation | 6 | 記錄基金關聯的投資機構。 |
| `FundLPCommitmentRelation.csv` | Relation | 12 | 記錄基金與 LP 的承諾出資。 |
| `FundLimitedPartnerRelation.csv` | Relation | 6 | 記錄基金與有限合夥人的關聯。 |
| `FundReturnRelation.csv` | Relation | 27 | 記錄基金回報時間序列。 |
| `FundReturnReporterRelation.csv` | Relation | 26 | 記錄基金回報數據與回報來源。 |
| `FundServiceProviderRelation.csv` | Relation | 10 | 記錄基金關聯的服務機構。 |
| `FundTeamRelation.csv` | Relation | 11 | 記錄基金團隊資料。 |
| `Investor.csv` | 主表 | 111 | 投資機構主表，記錄投資機構的基本資料、投資偏好、歷史活動與最近交易。 |
| `InvestorAffiliateRelation.csv` | Relation | 11 | 記錄投資機構的關聯實體資料。 |
| `InvestorCoInvestorRelation.csv` | Relation | 6 | 記錄投資機構之間的共同投資關係。 |
| `InvestorEntityTypeRelation.csv` | Relation | 5 | 記錄投資機構的實體類型分類。 |
| `InvestorExitRelation.csv` | Relation | 10 | 記錄投資機構的退出案例。 |
| `InvestorFundRelation.csv` | Relation | 5 | 記錄投資機構與其他主題之間的關聯資料。 |
| `InvestorInvestDealRelation.csv` | Relation | 7 | 按交易類型彙總投資機構的投資統計。 |
| `InvestorInvestIndustryCodeRelation.csv` | Relation | 10 | 按產業代碼彙總投資機構的投資統計。 |
| `InvestorInvestIndustrySectorCodeRelation.csv` | Relation | 7 | 按產業部門彙總投資機構的投資統計。 |
| `InvestorInvestYearRelation.csv` | Relation | 7 | 按年份彙總投資機構的投資統計。 |
| `InvestorInvestmentRelation.csv` | Relation | 16 | 記錄投資機構的投資明細。 |
| `InvestorLeadPartnerRelation.csv` | Relation | 7 | 記錄投資機構與 lead partner 的關聯。 |
| `InvestorLimitedPartnerRelation.csv` | Relation | 11 | 記錄投資機構與有限合夥人的關聯。 |
| `InvestorLocationRelation.csv` | Relation | 14 | 記錄投資機構的地點與辦公室資訊。 |
| `InvestorServiceProviderRelation.csv` | Relation | 7 | 記錄投資機構關聯的服務機構。 |
| `LPDirectInvestmentRelation.csv` | Relation | 7 | 記錄 LP 的直接投資。 |
| `LPFundCommitmentRelation.csv` | Relation | 7 | 記錄 LP 對基金的承諾出資。 |
| `LimitedPartner.csv` | 主表 | 105 | 有限合夥人主表，記錄 LP 的基本資料、資產配置與出資偏好。 |
| `Person.csv` | 主表 | 42 | 人物主表，記錄個人基本資料、主要任職、聯絡方式與角色統計。 |
| `PersonAdvisoryRelation.csv` | Relation | 11 | 記錄人物的顧問角色。 |
| `PersonAffiliatedDealRelation.csv` | Relation | 11 | 記錄人物關聯的交易。 |
| `PersonAffiliatedFundRelation.csv` | Relation | 7 | 記錄人物關聯的基金。 |
| `PersonBoardSeatRelation.csv` | Relation | 12 | 記錄人物的董事席位。 |
| `PersonEducationRelation.csv` | Relation | 7 | 記錄人物教育背景。 |
| `PersonPositionRelation.csv` | Relation | 13 | 記錄人物任職經歷。 |
| `ServiceProvider.csv` | 主表 | 66 | 服務機構主表，記錄律所、會計師、顧問等服務提供方的資料與服務範圍。 |
| `ServiceProviderCompDealRelation.csv` | Relation | 10 | 記錄服務機構與公司/交易的服務關係。 |
| `ServiceProviderCompanyRelation.csv` | Relation | 7 | 記錄服務機構服務的公司。 |
| `ServiceProviderInvFundRelation.csv` | Relation | 8 | 記錄服務機構服務的投資機構與基金。 |
| `ServiceProviderInvestorRelation.csv` | Relation | 8 | 記錄服務機構關聯的投資機構。 |
| `ServiceProviderLPRelation.csv` | Relation | 6 | 記錄服務機構服務的 LP。 |
