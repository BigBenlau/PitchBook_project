#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parents[1]
DATA_DIR = ROOT / "data"
OUT_DIR = SCRIPT_DIR
DICT_FILE = DATA_DIR / "Stanford - Updated v1.5.xlsx"
MAX_SAMPLE_SCAN_ROWS = 5000

NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

PRIMARY_TABLES = {
    "Company": "Company.csv",
    "Deal": "Deal.csv",
    "Investor": "Investor.csv",
    "Fund": "Fund.csv",
    "LimitedPartner": "LimitedPartner.csv",
    "Person": "Person.csv",
    "ServiceProvider": "ServiceProvider.csv",
}

FILE_GROUPS = [
    ("01_company.md", "公司資料", lambda stem: stem == "Company" or stem.startswith("Company")),
    ("02_deal.md", "交易資料", lambda stem: stem == "Deal" or stem.startswith("Deal")),
    ("03_investor.md", "投資機構資料", lambda stem: stem == "Investor" or stem.startswith("Investor")),
    (
        "04_fund_lp.md",
        "基金與 LP 資料",
        lambda stem: stem in {"Fund", "LimitedPartner"} or stem.startswith("Fund") or stem.startswith("LP"),
    ),
    (
        "05_person_entity.md",
        "人物與泛實體資料",
        lambda stem: stem == "Person" or stem.startswith("Person") or stem.startswith("Entity"),
    ),
    (
        "06_service_provider.md",
        "服務機構資料",
        lambda stem: stem == "ServiceProvider" or stem.startswith("ServiceProvider"),
    ),
]

SHEET_NAME_ALIASES = {
    "InvestorInvestIndustryCodeRelat": "InvestorInvestIndustryCodeRelation",
    "InvestorInvestIndustrySectorCod": "InvestorInvestIndustrySectorCodeRelation",
}

FILE_DESCRIPTION_OVERRIDES = {
    "Company": "公司主表，記錄公司的基本資料、融資狀態、聯絡資訊與最近財務摘要。",
    "Deal": "交易主表，記錄公司各輪融資、併購或退出事件的基本資訊。",
    "Investor": "投資機構主表，記錄投資機構的基本資料、投資偏好、歷史活動與最近交易。",
    "Fund": "基金主表，記錄基金規模、募集狀態、偏好策略與乾粉資訊。",
    "LimitedPartner": "有限合夥人主表，記錄 LP 的基本資料、資產配置與出資偏好。",
    "Person": "人物主表，記錄個人基本資料、主要任職、聯絡方式與角色統計。",
    "ServiceProvider": "服務機構主表，記錄律所、會計師、顧問等服務提供方的資料與服務範圍。",
    "DealCapTableRelation": "記錄交易相關的股權結構與條款欄位。此表未在官方 Excel 中提供完整欄位字典，以下說明依欄位名推定。",
}

TYPE_OVERRIDES = {
    "DealCapTableRelation": {
        "DealID": "TEXT(20)",
        "CapTableID": "TEXT(20)",
        "SeriesOfStock": "TEXT",
        "NumberOfSharesAuthorized": "INTEGER",
        "ParValue": "DECIMAL",
        "DividendRatePercentage": "DECIMAL",
        "OriginalIssuePrice": "DECIMAL",
        "LiquidationPrice": "DECIMAL",
        "LiquidationPreferenceMultiple": "DECIMAL",
        "ConversionPrice": "DECIMAL",
        "PercentOwned": "DECIMAL",
        "TypeOfStock": "TEXT",
        "SharesSought": "INTEGER",
        "PriceperShare": "DECIMAL",
        "NumberOfSharesAcquired": "INTEGER",
        "ConversionRatio": "DECIMAL",
        "LiquidationPreferences": "TEXT",
        "ParticipatingVSNonParticipating": "TEXT",
        "DividendRights": "TEXT",
        "Cumulative_NonCumulative": "TEXT",
        "AntiDilutionProvisions": "TEXT",
        "RedemptionRights": "TEXT",
        "BoardVotingRights": "TEXT",
        "GeneralVotingRights": "TEXT",
        "RowID": "TEXT(255)",
        "LastUpdated": "DATE",
    }
}

EXACT_FIELD_ZH = {
    "RowID": "列唯一識別碼",
    "LastUpdated": "最後更新日期",
    "CompanyID": "公司唯一識別碼",
    "DealID": "交易唯一識別碼",
    "InvestorID": "投資機構唯一識別碼",
    "FundID": "基金唯一識別碼",
    "LimitedPartnerID": "有限合夥人唯一識別碼",
    "PersonID": "人物唯一識別碼",
    "ServiceProviderID": "服務機構唯一識別碼",
    "EntityID": "泛實體唯一識別碼",
    "CompanyName": "公司名稱",
    "DealNo": "交易序號",
    "InvestorName": "投資機構名稱",
    "FundName": "基金名稱",
    "LimitedPartnerName": "有限合夥人名稱",
    "ServiceProviderName": "服務機構名稱",
    "FullName": "完整姓名",
    "FullTitle": "完整職稱",
    "PrimaryContact": "主要聯絡人",
    "PrimaryContactPBId": "主要聯絡人 PitchBook 識別碼",
    "ParentCompanyID": "母公司識別碼",
    "ParentCompany": "母公司名稱",
    "RepresentingID": "代表實體識別碼",
    "RepresentingName": "代表實體名稱",
    "LeadPartnerID": "主導合夥人識別碼",
    "LeadPartnerName": "主導合夥人姓名",
    "LeadPartner": "主導合夥人姓名",
    "DealDate": "交易完成日期",
    "AnnouncedDate": "交易公告日期",
    "CloseDate": "募集完成日期",
    "OpenDate": "開放日期",
    "StartDate": "開始日期",
    "EndDate": "結束日期",
    "PeriodEndDate": "期間結束日期",
    "FundCloseDate": "基金關閉日期",
    "CompanyFinancingStatus": "公司融資狀態",
    "InvestorStatus": "投資方狀態",
    "DealStatus": "交易狀態",
    "FundStatus": "基金狀態",
    "BusinessStatus": "業務狀態",
    "OwnershipStatus": "持有狀態",
    "DealSize": "交易規模",
    "FundSize": "基金規模",
    "TotalRaised": "累計融資額",
    "Revenue": "營收",
    "GrossProfit": "毛利",
    "NetIncome": "淨利",
    "EnterpriseValue": "企業價值",
    "EBITDA": "EBITDA",
    "EBIT": "EBIT",
    "NetDebt": "淨負債",
    "AUM": "管理資產規模",
    "DryPowder": "乾粉資金",
    "IRR": "內部報酬率 IRR",
    "DPI": "DPI 倍數",
    "TVPI": "TVPI 倍數",
    "RVPI": "RVPI 倍數",
    "NAV": "資產淨值 NAV",
    "Commitment": "承諾出資額",
    "CommitmentID": "承諾出資識別碼",
    "CapTableID": "股權結構識別碼",
    "FacilityID": "融資額度識別碼",
    "LenderID": "貸方識別碼",
    "BeneficiaryID": "受益方識別碼",
    "AffiliateID": "關聯實體識別碼",
    "SimilarCompanyID": "相似公司識別碼",
    "TargetCompanyID": "目標公司識別碼",
    "ExitDealID": "退出交易識別碼",
    "FirstFinancingDealID": "首次融資交易識別碼",
    "LastFinancingDealID": "最近融資交易識別碼",
    "HQAddressLine1": "總部地址第一行",
    "HQAddressLine2": "總部地址第二行",
    "HQCity": "總部城市",
    "HQState_Province": "總部州或省",
    "HQPostCode": "總部郵遞區號",
    "HQCountry": "總部國家",
    "HQPhone": "總部電話",
    "HQFax": "總部傳真",
    "HQEmail": "總部電子郵件",
    "HQLocation": "總部地點",
    "LinkedInProfileURL": "LinkedIn 連結",
    "TwitterProfileURL": "Twitter 連結",
    "FacebookProfileURL": "Facebook 連結",
    "PitchBookProfileLink": "PitchBook 頁面連結",
    "Description": "描述",
    "Keywords": "關鍵詞",
    "Comments": "備註說明",
    "FirstName": "名",
    "LastName": "姓",
    "MiddleName": "中間名",
    "CEOFirstName": "執行長名",
    "CEOLastName": "執行長姓",
    "CEOMiddle": "執行長中間名",
    "CEOPrefix": "執行長前綴",
    "CEOSuffix": "執行長後綴",
    "PostValuation": "投後估值",
    "PostValuationStatus": "投後估值狀態",
    "RaisedToDate": "截至目前累計募集額",
    "NativeAmountOfDeal": "原幣交易金額",
    "PercentAcquired": "收購比例",
    "TotalInvestedCapital": "總投入資本",
    "TotalInvestedEquity": "總投入股權資本",
    "DebtRaisedInRound": "本輪新增債務",
    "PricePerShare": "每股價格",
    "SeriesOfStock": "股票系列",
    "TickerSymbol": "股票代號",
    "MarketCapEndOfFirstTradIngDay": "上市首日收盤市值",
    "Price1DayAfterOfferIng": "發行後第 1 日價格",
    "Price5DaysAfterOfferIng": "發行後第 5 日價格",
    "Price30DaysAfterOfferIng": "發行後第 30 日價格",
    "ImpliedEV": "隱含企業價值",
    "RevenueGrowthSinceLastDebtDeal": "距上次債務交易以來的營收成長",
    "EBITDAMarginPercent": "EBITDA 利潤率",
    "NativeCurrencyOfDeal": "交易原幣幣別",
    "VCRoundUp_Down_Flat": "VC 輪次變化方向",
    "TotalNewDebt": "新增總債務",
    "SiteLocation": "交易地點",
}

WORD_MAP = {
    "Active": "現有",
    "Add": "追加",
    "Address": "地址",
    "Advisory": "顧問",
    "Affiliate": "關聯實體",
    "Affiliated": "關聯",
    "All": "全部",
    "Also": "其他",
    "Amount": "金額",
    "Announced": "公告",
    "As": "",
    "Asset": "資產",
    "Assets": "資產",
    "Available": "可用",
    "Average": "平均",
    "Before": "前",
    "Beneficiary": "受益方",
    "Biography": "簡歷",
    "Board": "董事會",
    "Bought": "買入",
    "Business": "業務",
    "Buy": "買方",
    "Called": "已提取",
    "Capital": "資本",
    "Cash": "現金",
    "Category": "類別",
    "CEO": "執行長",
    "Change": "變動",
    "City": "城市",
    "Class": "類別",
    "Close": "關閉",
    "Closed": "已關閉",
    "Code": "代碼",
    "Co": "共同",
    "Common": "普通",
    "Company": "公司",
    "Competitor": "競爭對手",
    "Concentration": "集中領域",
    "Contact": "聯絡人",
    "Continuing": "持續經營",
    "Conversion": "轉換",
    "Country": "國家",
    "Coupon": "票息",
    "Current": "當前",
    "Date": "日期",
    "Debt": "債務",
    "Deal": "交易",
    "Debts": "債務",
    "Degree": "學位",
    "Description": "描述",
    "Diluted": "稀釋後",
    "Direct": "直接",
    "Distrib": "分配",
    "Distributed": "已分配",
    "Domiciles": "註冊地",
    "Down": "下降",
    "Dry": "乾粉",
    "Earnings": "收益",
    "EBIT": "EBIT",
    "EBITDA": "EBITDA",
    "Education": "教育",
    "Email": "電子郵件",
    "Employee": "員工",
    "Employees": "員工數",
    "End": "結束",
    "Energy": "能源",
    "Entity": "實體",
    "Equities": "股票",
    "Equity": "權益",
    "Exchange": "交易所",
    "Exit": "退出",
    "Exiter": "退出方",
    "Expense": "費用",
    "Facility": "額度",
    "Family": "家族",
    "Fax": "傳真",
    "Financing": "融資",
    "Financial": "財務",
    "First": "首次",
    "Fiscal": "財務",
    "Fixed": "固定收益",
    "Flow": "現金流",
    "Follow": "跟投",
    "Former": "曾用",
    "Founded": "成立",
    "Fund": "基金",
    "Gain": "收益",
    "Gender": "性別",
    "General": "一般",
    "Geography": "地理偏好",
    "Global": "全球",
    "Gross": "毛",
    "Group": "群組",
    "Held": "持有",
    "Hedge": "對沖",
    "High": "上限",
    "Horizon": "期限",
    "HQ": "總部",
    "ID": "識別碼",
    "Implied": "隱含",
    "Income": "收益",
    "Industry": "產業",
    "Infrastructure": "基礎設施",
    "Institute": "學校",
    "Institution": "機構",
    "Interest": "利息",
    "In": "",
    "Investment": "投資",
    "Investments": "投資",
    "Investor": "投資機構",
    "IRR": "IRR",
    "Issue": "發行",
    "Known": "名稱",
    "Last": "最近",
    "Lead": "主導",
    "Legal": "法定",
    "Lender": "貸方",
    "Liabilities": "負債",
    "Limited": "有限",
    "Line": "行",
    "Link": "連結",
    "Linked": "連結",
    "LinkedIn": "LinkedIn",
    "Liquidation": "清算",
    "Location": "地點",
    "Loss": "損失",
    "LP": "LP",
    "Major": "主修",
    "Market": "市場",
    "Median": "中位數",
    "Middle": "中間名",
    "Min": "最小值",
    "Morningstar": "Morningstar",
    "Most": "最可能",
    "Multiple": "倍數",
    "Name": "名稱",
    "Native": "原幣",
    "NAV": "NAV",
    "Naics": "NAICS",
    "Net": "淨",
    "New": "新",
    "No": "序號",
    "Normalized": "標準化",
    "Non": "非",
    "Notes": "備註",
    "Number": "數量",
    "Office": "辦公室",
    "OID": "OID",
    "On": "",
    "Open": "開放",
    "Operating": "營運",
    "Operations": "營運",
    "Other": "其他",
    "Outstanding": "流通在外",
    "Owned": "持有",
    "Ownership": "持有",
    "Parent": "母",
    "Par": "面值",
    "Partner": "合夥人",
    "Partners": "合夥人",
    "Payments": "付款",
    "Percent": "百分比",
    "Percentage": "百分比",
    "Period": "期間",
    "Person": "人員",
    "Phone": "電話",
    "Policy": "政策",
    "Position": "職位",
    "Post": "郵遞",
    "PostCode": "郵遞區號",
    "Powder": "資金",
    "Preferred": "偏好",
    "Premoney": "投前",
    "Prefix": "前綴",
    "Preliminary": "初步",
    "Price": "價格",
    "Primary": "主要",
    "Private": "私募",
    "Profit": "利潤",
    "Profile": "檔案",
    "Provided": "提供",
    "Provider": "機構",
    "Public": "公開",
    "Quarter": "季度",
    "Quick": "速動",
    "Raised": "募集",
    "Range": "範圍",
    "Rate": "比率",
    "Ratio": "比率",
    "Real": "不動產",
    "RealEstate": "不動產",
    "Redeption": "贖回",
    "Redemption": "贖回",
    "Reference": "參考",
    "Regional": "區域",
    "Register": "註冊",
    "Registration": "註冊",
    "Relation": "關聯",
    "Remaining": "剩餘",
    "Reporter": "回報來源",
    "Reporting": "回報",
    "Representing": "代表",
    "Restated": "重述",
    "Return": "回報",
    "Revenue": "營收",
    "Rights": "權利",
    "Role": "角色",
    "Round": "輪次",
    "Row": "列",
    "RVPI": "RVPI",
    "SBIC": "SBIC",
    "Seat": "席位",
    "Sector": "部門",
    "Security": "擔保",
    "Seller": "出售方",
    "Sell": "賣方",
    "Service": "服務",
    "Share": "股份",
    "Shares": "股數",
    "Sic": "SIC",
    "Similarity": "相似度",
    "Similar": "相似",
    "Since": "自",
    "Size": "規模",
    "Sold": "出售",
    "Source": "來源",
    "Special": "特殊",
    "Split": "拆分",
    "Spread": "利差",
    "Stage": "階段",
    "Start": "開始",
    "State": "州",
    "Status": "狀態",
    "Still": "仍然",
    "Stock": "股票",
    "Stockholders": "股東",
    "SubRegion": "次區域",
    "Suffix": "後綴",
    "Synopsis": "摘要",
    "Target": "目標",
    "Tax": "稅",
    "Team": "團隊",
    "Tenor": "期限",
    "Ticker": "股票代碼",
    "Time": "時間",
    "To": "",
    "Total": "總",
    "Trade": "交易",
    "Tranche": "分批",
    "TVPI": "TVPI",
    "Twitter": "Twitter",
    "Type": "類型",
    "University": "大學",
    "Universe": "覆蓋範圍",
    "Up": "上升",
    "URL": "連結",
    "Valuation": "估值",
    "Value": "價值",
    "VC": "VC",
    "Vertical": "垂直領域",
    "Verticals": "垂直領域",
    "Vintage": "Vintage",
    "Voting": "投票",
    "Weighted": "加權",
    "Website": "網站",
    "Year": "年份",
    "Years": "年份",
    "YTM": "到期殖利率",
}


@dataclass
class ColumnDef:
    dtype: str
    comment: str
    sample: str
    inferred: bool = False


def col_to_num(col: str) -> int:
    n = 0
    for ch in col:
        if ch.isalpha():
            n = n * 26 + ord(ch.upper()) - 64
    return n


def load_shared_strings(zip_file: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zip_file.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    out = []
    for si in root.findall("a:si", NS):
        text = "".join(t.text or "" for t in si.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"))
        out.append(text)
    return out


def read_sheet_rows(zip_file: ZipFile, target: str, shared: list[str], max_cols: int = 8) -> list[list[str]]:
    root = ET.fromstring(zip_file.read("xl/" + target))
    rows: list[list[str]] = []
    for row in root.findall(".//a:sheetData/a:row", NS):
        vals = [""] * max_cols
        for cell in row.findall("a:c", NS):
            ref = cell.attrib.get("r", "")
            match = re.match(r"([A-Z]+)", ref)
            if not match:
                continue
            idx = col_to_num(match.group(1)) - 1
            if idx >= max_cols:
                continue
            val_node = cell.find("a:v", NS)
            if val_node is None:
                value = ""
            elif cell.attrib.get("t") == "s":
                value = shared[int(val_node.text)]
            else:
                value = val_node.text or ""
            vals[idx] = value.strip()
        rows.append(vals)
    return rows


def load_dictionary() -> tuple[dict[str, dict[str, ColumnDef]], dict[str, str]]:
    definitions: dict[str, dict[str, ColumnDef]] = {}
    descriptions: dict[str, str] = {}
    with ZipFile(DICT_FILE) as zip_file:
        workbook = ET.fromstring(zip_file.read("xl/workbook.xml"))
        rels = ET.fromstring(zip_file.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        shared = load_shared_strings(zip_file)
        for sheet in workbook.find("a:sheets", NS):
            raw_name = sheet.attrib["name"]
            sheet_name = SHEET_NAME_ALIASES.get(raw_name, raw_name)
            target = rel_map[sheet.attrib[REL_NS]]
            rows = read_sheet_rows(zip_file, target, shared)
            if sheet_name == "Summary":
                for row in rows:
                    name = row[0].strip()
                    desc = row[1].strip()
                    if name and desc and name not in {"File Name", "Delivery Method", "Host", "Login", "File Format"}:
                        descriptions[name] = desc
                continue
            if sheet_name in {"TrackingChanges"}:
                continue
            defs: dict[str, ColumnDef] = {}
            for row in rows:
                idx = row[0].strip()
                col_name = row[1].strip()
                if idx.isdigit() and col_name:
                    defs[col_name] = ColumnDef(dtype=row[2].strip(), comment=row[3].strip(), sample=row[4].strip())
            definitions[sheet_name] = defs
    return definitions, descriptions


def clean_sample_value(value: str, limit: int = 120) -> str:
    text = " ".join(value.split())
    text = text.replace("|", "\\|")
    if len(text) > limit:
        return text[: limit - 4] + " ..."
    return text


def load_csv_headers_and_samples() -> tuple[dict[str, list[str]], dict[str, dict[str, str]]]:
    headers: dict[str, list[str]] = {}
    samples: dict[str, dict[str, str]] = {}
    for csv_path in sorted(DATA_DIR.glob("*.csv")):
        if csv_path.name.endswith("_10.csv"):
            continue
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            file_headers = reader.fieldnames or []
            headers[csv_path.name] = file_headers
            sample_map = {column: "" for column in file_headers}
            remaining = set(file_headers)
            for row_idx, row in enumerate(reader, start=1):
                for column in tuple(remaining):
                    value = (row.get(column) or "").strip()
                    if value:
                        sample_map[column] = clean_sample_value(value)
                        remaining.remove(column)
                if not remaining or row_idx >= MAX_SAMPLE_SCAN_ROWS:
                    break
            samples[csv_path.name] = sample_map
    return headers, samples


def infer_type(column: str) -> str:
    if column == "LastUpdated" or "Date" in column:
        return "DATE"
    if column.endswith("Year") or column in {"Vintage", "DealNo"} or column.endswith("Count"):
        return "INTEGER"
    numeric_keywords = [
        "Amount",
        "Size",
        "Value",
        "Valuation",
        "Revenue",
        "Profit",
        "Income",
        "Debt",
        "EBIT",
        "EBITDA",
        "AUM",
        "IRR",
        "DPI",
        "TVPI",
        "RVPI",
        "NAV",
        "Price",
        "Ratio",
        "Percent",
        "Percentage",
        "Shares",
        "Capital",
        "Commitment",
        "Multiple",
    ]
    if any(keyword in column for keyword in numeric_keywords):
        return "DECIMAL"
    return "TEXT"


def split_identifier(name: str) -> list[str]:
    cleaned = name.replace("_", " ")
    cleaned = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", cleaned)
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", cleaned)
    return [token for token in cleaned.split() if token]


def prettify_zh(text: str) -> str:
    text = text.replace("  ", " ").strip()
    text = text.replace(" 、", "、").replace("（ ", "（").replace(" ）", "）")
    return text


def field_zh(column: str) -> str:
    if column in EXACT_FIELD_ZH:
        return EXACT_FIELD_ZH[column]
    suffix_rules = [
        ("FirstName", "名"),
        ("LastName", "姓"),
        ("MiddleName", "中間名"),
        ("Prefix", "前綴"),
        ("Suffix", "後綴"),
        ("Phone", "電話"),
        ("Email", "電子郵件"),
        ("Biography", "簡歷"),
        ("Education", "教育背景"),
    ]
    for suffix, zh_suffix in suffix_rules:
        if column.endswith(suffix) and column != suffix:
            prefix = column[: -len(suffix)]
            prefix_label = field_zh(prefix) if prefix else ""
            return prettify_zh(f"{prefix_label}{zh_suffix}")
    tokens = split_identifier(column)
    translated = []
    for token in tokens:
        translated.append(WORD_MAP.get(token, token))
    result = "".join(token for token in translated if token)
    return prettify_zh(result or column)


def translate_description(text: str) -> str:
    clean = " ".join(text.split())
    if not clean:
        return ""
    replacements = [
        ("General information on ", "記錄"),
        (" relationship.", "之間的關聯資料。"),
        (" relationships.", "之間的關聯資料。"),
        (" companies.", "公司的基本資料。"),
        (" deals.", "交易的基本資料。"),
        (" investors.", "投資機構的基本資料。"),
        (" funds.", "基金的基本資料。"),
        (" people.", "人物的基本資料。"),
        (" service providers.", "服務機構的基本資料。"),
        (" limited partners.", "有限合夥人的基本資料。"),
    ]
    out = clean
    for src, dst in replacements:
        out = out.replace(src, dst)
    if out != clean:
        return out
    return f"官方摘要指出，此表用於記錄{clean.lower()}。"


def summarize_comment(column: str, col_def: ColumnDef) -> str:
    comment = " ".join(col_def.comment.split())
    label = field_zh(column)
    if not comment:
        if col_def.inferred:
            return f"依欄位名推定，此欄記錄{label}。"
        return f"官方資料字典未提供更多說明；此欄記錄{label}。"
    if "Primary key" in comment:
        return f"此表主鍵，用於唯一識別單筆{label}。"
    if "Unique identifier" in comment and "Relates to" in comment:
        return f"唯一識別碼，可用於關聯其他主表或關聯表中的對應記錄。"
    if "Unique identifier" in comment:
        return f"唯一識別碼，用於記錄{label}。"
    if comment.startswith("Name of"):
        return f"記錄{label}。"
    if comment.startswith("Date") or " Date " in f" {comment} " or "Year " in comment or column.endswith("Year"):
        return f"記錄{label}相關日期。"
    if "website" in comment.lower():
        return f"記錄{label}。"
    if "status" in comment.lower():
        return f"記錄{label}，用來描述當前狀態或標記。"
    if "amount" in comment.lower() or "capital" in comment.lower():
        return f"記錄{label}，通常為金額或資本數值。"
    if "percentage" in comment.lower() or "ratio" in comment.lower():
        return f"記錄{label}，通常為比例或比率。"
    if "city" in comment.lower() or "country" in comment.lower() or "state" in comment.lower():
        return f"記錄{label}相關地理資訊。"
    if "Blank or null" in comment:
        return f"記錄{label}；若未提供資料則可能為空值。"
    return f"官方資料字典對此欄有說明；此欄主要記錄{label}。"


def infer_column_def(file_stem: str, column: str) -> ColumnDef:
    dtype = TYPE_OVERRIDES.get(file_stem, {}).get(column, infer_type(column))
    return ColumnDef(dtype=dtype, comment="", sample="", inferred=True)


def get_column_defs(file_stem: str, headers: list[str], dictionary: dict[str, dict[str, ColumnDef]]) -> dict[str, ColumnDef]:
    official = dictionary.get(file_stem, {})
    defs: dict[str, ColumnDef] = {}
    for column in headers:
        defs[column] = official.get(column) or infer_column_def(file_stem, column)
    return defs


def infer_file_description(file_stem: str, descriptions: dict[str, str]) -> str:
    subject_map = {
        "Company": "公司",
        "Deal": "交易",
        "Investor": "投資機構",
        "Fund": "基金",
        "LimitedPartner": "有限合夥人",
        "LP": "LP",
        "Person": "人物",
        "Entity": "泛實體",
        "ServiceProvider": "服務機構",
    }

    def relation_desc(subject: str, relation_key: str) -> str | None:
        mapping = {
            "Affiliate": f"記錄{subject}的關聯實體資料。",
            "BoardSeatHeld": f"記錄{subject}持有的董事席位。",
            "BuySide": f"記錄{subject}作為買方參與的交易。",
            "Competitor": f"記錄{subject}的競爭對手。",
            "EmployeeHistory": f"記錄{subject}的員工數歷史。",
            "EntityType": f"記錄{subject}的實體類型分類。",
            "Financial": f"記錄{subject}的財務資料。",
            "PublicFinancial": f"記錄{subject}的公開財報欄位。",
            "Industry": f"記錄{subject}的產業分類。",
            "Investor": f"記錄{subject}關聯的投資機構。",
            "Location": f"記錄{subject}的地點與辦公室資訊。",
            "MorningstarCode": f"記錄{subject}的 Morningstar 分類代碼。",
            "NaicsCode": f"記錄{subject}的 NAICS 分類代碼。",
            "ServiceProvider": f"記錄{subject}關聯的服務機構。",
            "SicCode": f"記錄{subject}的 SIC 分類代碼。",
            "Similar": f"記錄與{subject}相似的公司與相似度。",
            "Vertical": f"記錄{subject}的垂直領域標籤。",
            "DebtLender": "記錄交易中的債務貸方與借款條件。",
            "DistribBeneficiary": "記錄交易分配的受益方。",
            "Seller": "記錄交易中的出售方或退出方。",
            "Tranche": "記錄交易的分批 tranche 資訊。",
            "CoInvestor": "記錄投資機構之間的共同投資關係。",
            "Exit": "記錄投資機構的退出案例。",
            "InvestDeal": "按交易類型彙總投資機構的投資統計。",
            "InvestIndustryCode": "按產業代碼彙總投資機構的投資統計。",
            "InvestIndustrySectorCode": "按產業部門彙總投資機構的投資統計。",
            "InvestYear": "按年份彙總投資機構的投資統計。",
            "Investment": f"記錄{subject}的投資明細。",
            "LeadPartner": "記錄投資機構與 lead partner 的關聯。",
            "LimitedPartner": f"記錄{subject}與有限合夥人的關聯。",
            "CloseHistory": "記錄基金歷次 closing / close 歷史。",
            "LPCommitment": "記錄基金與 LP 的承諾出資。",
            "Return": "記錄基金回報時間序列。",
            "ReturnReporter": "記錄基金回報數據與回報來源。",
            "Team": f"記錄{subject}團隊資料。",
            "DirectInvestment": "記錄 LP 的直接投資。",
            "FundCommitment": "記錄 LP 對基金的承諾出資。",
            "Company": "記錄服務機構服務的公司。",
            "CompDeal": "記錄服務機構與公司/交易的服務關係。",
            "InvFund": "記錄服務機構服務的投資機構與基金。",
            "LP": "記錄服務機構服務的 LP。",
            "Advisory": "記錄人物的顧問角色。",
            "AffiliatedDeal": "記錄人物關聯的交易。",
            "AffiliatedFund": "記錄人物關聯的基金。",
            "BoardSeat": "記錄人物的董事席位。",
            "Education": "記錄人物教育背景。",
            "Position": "記錄人物任職經歷。",
            "BoardTeam": "記錄泛實體的團隊與董事會資料。",
        }
        return mapping.get(relation_key)

    if file_stem in FILE_DESCRIPTION_OVERRIDES:
        return FILE_DESCRIPTION_OVERRIDES[file_stem]
    if file_stem in descriptions:
        return translate_description(descriptions[file_stem])
    if file_stem.endswith("Relation"):
        base = file_stem[:-8]
        for subject_key, subject_label in sorted(subject_map.items(), key=lambda item: len(item[0]), reverse=True):
            if base.startswith(subject_key):
                relation_key = base[len(subject_key) :]
                if relation_key:
                    return relation_desc(subject_label, relation_key) or f"記錄{subject_label}與其他主題之間的關聯資料。"
    return f"記錄{file_stem}相關資料。"


def relation_note(column: str) -> str:
    mapping = {
        "CompanyID": "可連到 Company.csv",
        "TargetCompanyID": "可連到 Company.csv",
        "ParentCompanyID": "通常表示母機構或母公司 ID",
        "SimilarCompanyID": "可連到 Company.csv",
        "CompetitorID": "通常可連到 Company.csv",
        "CompanyIDHeld": "可連到 Company.csv",
        "InvestorID": "可連到 Investor.csv",
        "Co_InvestorID": "可連到 Investor.csv",
        "FundID": "可連到 Fund.csv",
        "InvestorFundID": "通常可連到 Fund.csv",
        "Fund1ID": "通常可連到 Fund.csv",
        "Fund2ID": "通常可連到 Fund.csv",
        "Seller_ExiterFundID": "通常可連到 Fund.csv",
        "LimitedPartnerID": "可連到 LimitedPartner.csv",
        "PersonID": "可連到 Person.csv",
        "LeadPartnerID": "通常可連到 Person.csv",
        "PrimaryContactPBId": "通常可連到 Person.csv",
        "CEOPBId": "通常可連到 Person.csv",
        "DealID": "可連到 Deal.csv",
        "ExitDealID": "可連到 Deal.csv",
        "FirstFinancingDealID": "可連到 Deal.csv",
        "LastFinancingDealID": "可連到 Deal.csv",
        "ServiceProviderID": "可連到 ServiceProvider.csv",
        "EntityID": "泛實體鍵，可對應 Company / Investor / ServiceProvider 等主表",
        "RepresentingID": "代表實體鍵，可能連到 Investor / Fund / 其他機構",
        "AffiliateID": "關聯實體鍵，本批資料未提供單獨主表",
        "BeneficiaryID": "受益方鍵，本批資料未提供單獨主表",
        "LenderID": "貸方鍵，本批資料未提供單獨主表",
        "FacilityID": "額度鍵，本批資料未提供單獨主表",
        "CommitmentID": "承諾出資鍵，本批資料未提供單獨主表",
        "CapTableID": "股權結構鍵，本批資料未提供單獨主表",
        "SourceID": "來源鍵，本批資料未提供單獨主表",
        "Seller_ExiterID": "退出方鍵，可能對應投資機構、基金或其他持有人",
        "ServiceToID": "服務對象鍵，可能對應公司、基金、投資機構等",
    }
    if column in mapping:
        return mapping[column]
    if column == "RowID":
        return "列級稽核鍵"
    if column == "LastUpdated":
        return "列級更新時間"
    if column.endswith("ID"):
        return "識別碼欄位，可作為 join 線索"
    return ""


def category_for_column(column: str) -> str:
    if column in {"RaisedToDate"}:
        return "金額與估值"
    if column == "RowID" or column == "LastUpdated" or column.endswith("ID") or column in {"DealNo", "CikCode"}:
        return "識別與稽核"
    if any(key in column for key in ["Name", "AlsoKnownAs", "FormerName", "LegalName"]):
        return "名稱與別名"
    if any(key in column for key in ["Status", "Type", "Class", "Category", "IsPrimary", "IsCurrent", "IsLead", "IsOnBoard", "Universe"]):
        return "狀態與分類"
    if any(key in column for key in ["Date", "Year", "Quarter", "Vintage", "Period", "Frequency", "Tenor"]):
        return "時間"
    if any(
        key in column
        for key in [
            "Amount",
            "Size",
            "Valuation",
            "Revenue",
            "Profit",
            "Income",
            "EBIT",
            "EBITDA",
            "Debt",
            "EV",
            "NAV",
            "IRR",
            "DPI",
            "TVPI",
            "RVPI",
            "Price",
            "Capital",
            "Commitment",
            "AUM",
            "DryPowder",
            "Shares",
            "MarketCap",
            "Multiple",
            "Ratio",
            "Percent",
            "Percentage",
            "Value",
        ]
    ):
        return "金額與估值"
    if any(
        key in column
        for key in [
            "HQ",
            "Address",
            "Location",
            "City",
            "State",
            "Province",
            "PostCode",
            "Country",
            "Phone",
            "Fax",
            "Email",
            "Region",
            "Website",
            "URL",
            "Domiciles",
        ]
    ):
        return "地點與聯絡"
    if any(
        key in column
        for key in [
            "Person",
            "CEO",
            "LeadPartner",
            "PrimaryContact",
            "FullTitle",
            "Title",
            "Position",
            "RoleOnBoard",
            "Advisory",
            "Prefix",
            "Suffix",
            "Biography",
            "Education",
            "Degree",
            "Major",
            "Gender",
        ]
    ):
        return "人物與角色"
    if any(
        key in column
        for key in [
            "Holding",
            "Percent",
            "Representing",
            "ParentCompany",
            "Affiliate",
            "Similar",
            "Competitor",
            "InvestorOwnership",
            "ServiceTo",
            "CoInvestor",
            "Co_Investor",
            "Partial_Full",
            "Acquired",
            "Exit",
        ]
    ):
        return "關係與持有"
    if any(key in column for key in ["Industry", "Vertical", "Naics", "Sic", "Morningstar", "TradeAssociations", "EmergingSpaces"]):
        return "產業與標籤"
    if any(key in column for key in ["Description", "Keywords", "Comments", "Note", "Policy", "Synopsis", "Sources"]):
        return "文字描述"
    return "文字描述"


def group_columns(headers: Iterable[str]) -> dict[str, list[str]]:
    ordered = [
        "識別與稽核",
        "名稱與別名",
        "狀態與分類",
        "時間",
        "金額與估值",
        "地點與聯絡",
        "人物與角色",
        "關係與持有",
        "產業與標籤",
        "文字描述",
    ]
    groups: dict[str, list[str]] = {name: [] for name in ordered}
    for column in headers:
        groups[category_for_column(column)].append(column)
    return {name: cols for name, cols in groups.items() if cols}


def primary_key_text(file_stem: str, headers: list[str], defs: dict[str, ColumnDef]) -> str:
    keys = [col for col, col_def in defs.items() if "Primary key" in col_def.comment]
    if keys:
        return "、".join(f"`{key}`" for key in keys)
    guessed = f"{file_stem}ID"
    if guessed in headers and not file_stem.endswith("Relation"):
        return f"`{guessed}`"
    return "此表未明示獨立業務主鍵，實務上多以關聯鍵組合搭配 `RowID` 表示一列。"


def foreign_keys_text(headers: list[str], file_stem: str) -> str:
    keys = [col for col in headers if col.endswith("ID") and col not in {"RowID", f"{file_stem}ID"}]
    if not keys:
        return "無明顯外鍵，或主要以本表欄位自身描述。"
    return "、".join(f"`{key}`" for key in keys)


def relation_targets_text(headers: list[str]) -> str:
    notes = []
    seen = set()
    for column in headers:
        note = relation_note(column)
        if not note or note in seen:
            continue
        seen.add(note)
        notes.append(note)
    return "；".join(notes) if notes else "以本表欄位說明為主。"


def render_column_table(
    file_stem: str,
    columns: list[str],
    defs: dict[str, ColumnDef],
    samples: dict[str, str],
) -> str:
    lines = [
        "| 欄位名 | 中文含義 | 類型 | 真實樣本值 | 官方說明摘要 | 關聯/備註 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for column in columns:
        col_def = defs[column]
        notes = relation_note(column)
        if col_def.inferred:
            notes = f"{notes}；推定欄位說明".strip("；")
        sample_value = samples.get(column) or f"前 {MAX_SAMPLE_SCAN_ROWS} 行未見非空值"
        lines.append(
            "| `{}` | {} | {} | {} | {} | {} |".format(
                column,
                field_zh(column),
                col_def.dtype or "未提供",
                sample_value,
                summarize_comment(column, col_def),
                notes or "—",
            )
        )
    return "\n".join(lines)


def render_file_section(
    file_name: str,
    headers: list[str],
    samples: dict[str, str],
    dictionary: dict[str, dict[str, ColumnDef]],
    descriptions: dict[str, str],
) -> str:
    file_stem = Path(file_name).stem
    defs = get_column_defs(file_stem, headers, dictionary)
    description = infer_file_description(file_stem, descriptions)
    groups = group_columns(headers)
    parts = [
        f"## {file_name}",
        "",
        f"**用途**：{description}",
        "",
        f"**主鍵**：{primary_key_text(file_stem, headers, defs)}",
        "",
        f"**主要關聯鍵**：{foreign_keys_text(headers, file_stem)}",
        "",
        f"**可連接到**：{relation_targets_text(headers)}",
        "",
        "### 欄位分組",
        "",
    ]
    for group_name, columns in groups.items():
        parts.extend([f"#### {group_name}", "", render_column_table(file_stem, columns, defs, samples), ""])
    return "\n".join(parts).strip() + "\n"


def render_readme(headers: dict[str, list[str]], descriptions: dict[str, str]) -> str:
    formal_files = list(headers)
    primary_files = [name for name in formal_files if not name.endswith("Relation.csv")]
    relation_files = [name for name in formal_files if name.endswith("Relation.csv")]
    sections = [
        "# 資料集閱讀指南",
        "",
        "本資料夾整理 `data/` 內的正式 PitchBook CSV 結構說明，協助快速理解有哪些表、每個表在做什麼、欄位如何分組，以及不同表之間如何連接。",
        "",
        "## 使用原則",
        "",
        "- 文件內容使用中文，檔名與欄位名保留英文。",
        f"- 依正式 CSV 的 header 與官方 Excel data dictionary 整理；為補充真實樣本值，會掃描每個 CSV 前 {MAX_SAMPLE_SCAN_ROWS} 行以抓取每欄第一個非空值。",
        "- 所有 `_10.csv` 一律忽略，因為它們是 sample，不屬於正式資料集。",
        "- 若官方 dictionary 未提供欄位說明，文件中會明確標記為「推定」。",
        "",
        "## 正式資料表總覽",
        "",
        f"- 正式 CSV 總數：{len(formal_files)}",
        f"- 主表數量：{len(primary_files)}",
        f"- Relation 表數量：{len(relation_files)}",
        "",
        "## 建議閱讀順序",
        "",
        "1. 先看主表：`Company`、`Deal`、`Investor`、`Fund`、`LimitedPartner`、`Person`、`ServiceProvider`。",
        "2. 再看各主題 relation 表，理解一對多與多對多的延伸資料。",
        "3. 最後看 `07_relationships_and_joins.md` 與 `08_column_groups.md`，建立跨表視角。",
        "",
        "## 主題文件",
        "",
        "- `01_company.md`：公司主表與所有公司相關 relation 表。",
        "- `02_deal.md`：交易主表與所有交易相關 relation 表。",
        "- `03_investor.md`：投資機構主表與所有投資機構相關 relation 表。",
        "- `04_fund_lp.md`：基金、LP 與出資/回報相關表。",
        "- `05_person_entity.md`：人物表與 `Entity*Relation` 泛實體關係。",
        "- `06_service_provider.md`：服務機構與相關關係表。",
        "- `07_relationships_and_joins.md`：主鍵、外鍵與常見 join 路徑。",
        "- `08_column_groups.md`：跨表同類欄位分組索引。",
        "",
        "## 正式 CSV 一覽",
        "",
        "| CSV | 類型 | 欄位數 | 用途摘要 |",
        "| --- | --- | --- | --- |",
    ]
    for file_name in formal_files:
        stem = Path(file_name).stem
        file_type = "主表" if not file_name.endswith("Relation.csv") else "Relation"
        description = infer_file_description(stem, descriptions)
        sections.append(f"| `{file_name}` | {file_type} | {len(headers[file_name])} | {description} |")
    return "\n".join(sections) + "\n"


def render_group_doc(
    title: str,
    file_names: list[str],
    headers: dict[str, list[str]],
    samples: dict[str, dict[str, str]],
    dictionary: dict[str, dict[str, ColumnDef]],
    descriptions: dict[str, str],
) -> str:
    parts = [
        f"# {title}",
        "",
        "本文件依主題整理正式 CSV，說明每個表的用途、關聯鍵與欄位分組。",
        "",
    ]
    for file_name in file_names:
        parts.append(render_file_section(file_name, headers[file_name], samples[file_name], dictionary, descriptions))
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def render_relationships_doc(headers: dict[str, list[str]]) -> str:
    all_files = list(headers)
    relation_files = [name for name in all_files if name.endswith("Relation.csv")]
    relation_groups = [
        ("Company 類", lambda name: name.startswith("Company")),
        ("Deal 類", lambda name: name.startswith("Deal")),
        ("Investor 類", lambda name: name.startswith("Investor")),
        ("Fund 類", lambda name: name.startswith("Fund")),
        ("LP / LimitedPartner 類", lambda name: name.startswith("LP") or name.startswith("LimitedPartner")),
        ("Person 類", lambda name: name.startswith("Person")),
        ("Entity 類", lambda name: name.startswith("Entity")),
        ("ServiceProvider 類", lambda name: name.startswith("ServiceProvider")),
    ]
    lines = [
        "# 跨表關聯與 Join 指南",
        "",
        "本文件只依據正式 CSV 的欄位名與官方 data dictionary 整理可見的 join 線索，不依賴實際資料值。",
        "",
        "## 主實體表",
        "",
        "| 主表 | 主鍵 | 角色 |",
        "| --- | --- | --- |",
        "| `Company.csv` | `CompanyID` | 公司主體、被投企業、目標公司等核心實體。 |",
        "| `Deal.csv` | `DealID` | 融資、併購、退出等交易事件。 |",
        "| `Investor.csv` | `InvestorID` | 投資機構。 |",
        "| `Fund.csv` | `FundID` | 基金載體。 |",
        "| `LimitedPartner.csv` | `LimitedPartnerID` | LP / 出資方。 |",
        "| `Person.csv` | `PersonID` | 人員、合夥人、董事、聯絡人。 |",
        "| `ServiceProvider.csv` | `ServiceProviderID` | 服務機構，例如律所、顧問、會計師。 |",
        "",
        "## 常見外鍵規則",
        "",
        "- `CompanyID` 幾乎都連到 `Company.csv`。",
        "- `DealID` 幾乎都連到 `Deal.csv`。",
        "- `InvestorID` 幾乎都連到 `Investor.csv`。",
        "- `FundID` 幾乎都連到 `Fund.csv`。",
        "- `LimitedPartnerID` 幾乎都連到 `LimitedPartner.csv`。",
        "- `PersonID`、`LeadPartnerID`、`PrimaryContactPBId`、`CEOPBId` 常可連到 `Person.csv`。",
        "- `EntityID` 是 polymorphic key，通常可對應 `Company / Investor / ServiceProvider` 等多種主表。",
        "- `RepresentingID` 也是半泛型鍵，常代表董事席位或職務所屬的外部機構。",
        "",
        "## Relation 表與主表連法",
        "",
    ]
    covered = set()
    for group_title, matcher in relation_groups:
        group_files = [file_name for file_name in relation_files if matcher(Path(file_name).stem)]
        if not group_files:
            continue
        group_files.sort()
        covered.update(group_files)
        lines.extend(
            [
                f"### {group_title}",
                "",
                "| Relation 表 | 可見主鍵/外鍵 | 主要 join 方向 |",
                "| --- | --- | --- |",
            ]
        )
        for file_name in group_files:
            keys = [col for col in headers[file_name] if col.endswith("ID")]
            join_note = relation_targets_text(headers[file_name])
            lines.append(f"| `{file_name}` | {', '.join(f'`{key}`' for key in keys) or '—'} | {join_note} |")
        lines.append("")
    remaining = [file_name for file_name in relation_files if file_name not in covered]
    if remaining:
        remaining.sort()
        lines.extend(
            [
                "### 其他",
                "",
                "| Relation 表 | 可見主鍵/外鍵 | 主要 join 方向 |",
                "| --- | --- | --- |",
            ]
        )
        for file_name in remaining:
            keys = [col for col in headers[file_name] if col.endswith("ID")]
            join_note = relation_targets_text(headers[file_name])
            lines.append(f"| `{file_name}` | {', '.join(f'`{key}`' for key in keys) or '—'} | {join_note} |")
    lines.extend(
        [
            "",
            "## 常用 Join 路徑",
            "",
            "1. 公司看所有交易：`Company.CompanyID -> Deal.CompanyID`。",
            "2. 交易看投資方：`Deal.DealID -> DealInvestorRelation.DealID -> Investor.InvestorID`。",
            "3. 投資機構看被投公司：`Investor.InvestorID -> InvestorInvestmentRelation.InvestorID -> Company.CompanyID`。",
            "4. 基金看投資標的：`Fund.FundID -> FundInvestmentRelation.FundID -> Company.CompanyID`。",
            "5. LP 看出資基金：`LimitedPartner.LimitedPartnerID -> LPFundCommitmentRelation.LimitedPartnerID -> Fund.FundID`。",
            "6. 人員看任職實體：`Person.PersonID -> PersonPositionRelation.PersonID -> EntityID`，再依 `EntityID` 去對應主表。",
            "",
            "## `EntityID` 與 `RepresentingID` 的理解",
            "",
            "- `EntityID`：泛實體 ID，不保證只對應單一主表。常見於 `Entity*Relation` 與人物任職/顧問資料。",
            "- `RepresentingID`：代表某位董事、顧問或高管背後所屬機構的 ID，通常不是人物本身。",
            "- 使用這兩類欄位時，應先根據所在表的語境判斷其指向的是公司、投資機構、基金或其他機構。",
            "",
            "## 核心關聯圖",
            "",
            "```mermaid",
            "graph TD",
            "  Company[Company.csv] --> Deal[Deal.csv]",
            "  Deal --> DIR[DealInvestorRelation.csv]",
            "  DIR --> Investor[Investor.csv]",
            "  Investor --> IIR[InvestorInvestmentRelation.csv]",
            "  IIR --> Company",
            "  Fund[Fund.csv] --> FIR[FundInvestmentRelation.csv]",
            "  FIR --> Company",
            "  LP[LimitedPartner.csv] --> LPF[LPFundCommitmentRelation.csv]",
            "  LPF --> Fund",
            "  Person[Person.csv] --> PPR[PersonPositionRelation.csv]",
            "  PPR --> Entity[EntityID / polymorphic]",
            "  ServiceProvider[ServiceProvider.csv] --> DSP[DealServiceProviderRelation.csv]",
            "  DSP --> Deal",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def render_column_groups_doc(headers: dict[str, list[str]]) -> str:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for file_name, cols in headers.items():
        for column in cols:
            grouped[category_for_column(column)][column].append(file_name)
    order = [
        "識別與稽核",
        "名稱與別名",
        "狀態與分類",
        "時間",
        "金額與估值",
        "地點與聯絡",
        "人物與角色",
        "關係與持有",
        "產業與標籤",
        "文字描述",
    ]
    lines = [
        "# 跨表欄位分組索引",
        "",
        "本文件把不同 CSV 中的同類欄位放在一起，方便橫向理解欄位家族與命名規律。",
        "",
    ]
    for category in order:
        lines.extend([f"## {category}", "", "| 欄位名 | 中文含義 | 出現於哪些表 |", "| --- | --- | --- |"])
        for column in sorted(grouped[category]):
            files = "、".join(f"`{name}`" for name in grouped[category][column])
            lines.append(f"| `{column}` | {field_zh(column)} | {files} |")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def main() -> None:
    dictionary, descriptions = load_dictionary()
    headers, samples = load_csv_headers_and_samples()
    OUT_DIR.mkdir(exist_ok=True)

    write_text(OUT_DIR / "00_readme.md", render_readme(headers, descriptions))

    covered = set()
    for file_name, title, matcher in FILE_GROUPS:
        group_files = [csv_name for csv_name in headers if matcher(Path(csv_name).stem)]
        group_files.sort()
        covered.update(group_files)
        write_text(OUT_DIR / file_name, render_group_doc(title, group_files, headers, samples, dictionary, descriptions))

    remaining = [name for name in headers if name not in covered]
    if remaining:
        raise SystemExit(f"未覆蓋的正式 CSV：{remaining}")

    write_text(OUT_DIR / "07_relationships_and_joins.md", render_relationships_doc(headers))
    write_text(OUT_DIR / "08_column_groups.md", render_column_groups_doc(headers))

    print(f"Generated {len(list(OUT_DIR.glob('*.md')))} markdown files in {OUT_DIR}")


if __name__ == "__main__":
    main()
