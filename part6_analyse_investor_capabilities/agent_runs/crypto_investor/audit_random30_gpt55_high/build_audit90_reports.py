#!/usr/bin/env python3
import ast
import csv
import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


CAPS = [
    "otc_trading",
    "algorithm_trading",
    "market_making",
    "execution_services",
    "defi",
    "sub_fund",
]

ROOT = Path(__file__).resolve().parents[4]
RUN_DIR = ROOT / "part6_analyse_investor_capabilities" / "agent_runs" / "crypto_investor"
AUDIT_DIR = RUN_DIR / "audit_random30_gpt55_high"
ADD60_TMP_DIR = Path("/tmp/part6_audit_add60_gpt55_high")
ADD3_TMP_DIR = Path("/tmp/part6_audit_add3_gpt55_high")
ADD60_OUTPUTS = AUDIT_DIR / "raw_add60_agent_outputs"
ADD60_METADATA = AUDIT_DIR / "add60_sample_metadata.json"
ADD3_OUTPUTS = AUDIT_DIR / "raw_add3_agent_outputs"
ADD3_METADATA = AUDIT_DIR / "add3_sample_metadata.json"
ADD60_TMP_OUTPUTS = ADD60_TMP_DIR / "agent_outputs"
ADD60_TMP_METADATA = ADD60_TMP_DIR / "sample_metadata.json"
ADD3_TMP_OUTPUTS = ADD3_TMP_DIR / "agent_outputs"
ADD3_TMP_METADATA = ADD3_TMP_DIR / "sample_metadata.json"

ORIGINAL_AUDIT_CSV = AUDIT_DIR / "audit_random30_gpt55_high.csv"
OUTPUT_CSV = AUDIT_DIR / "audit_random30_gpt55_high.csv"
OUTPUT_MD = AUDIT_DIR / "audit_random30_gpt55_high.md"
MISMATCH_MD = AUDIT_DIR / "mismatch_analysis.md"
ROOT_CAUSE_MD = AUDIT_DIR / "original_label_root_cause.md"

RESULTS_CSV = RUN_DIR / "results.csv"
CLASSIFIER_CSV = RUN_DIR / "classifier_results.csv"
MANUAL_CSV = RUN_DIR / "needs_manual_review.csv"
INPUT_CSV = ROOT / "part5_to_part6" / "output" / "part6_investor_input.csv"

BATCHES = [
    {
        "name": "add60",
        "metadata": ADD60_METADATA,
        "outputs": ADD60_OUTPUTS,
        "tmp_metadata": ADD60_TMP_METADATA,
        "tmp_outputs": ADD60_TMP_OUTPUTS,
        "metadata_copy": AUDIT_DIR / "add60_sample_metadata.json",
        "outputs_copy": AUDIT_DIR / "raw_add60_agent_outputs",
    },
    {
        "name": "targeted_add3",
        "metadata": ADD3_METADATA,
        "outputs": ADD3_OUTPUTS,
        "tmp_metadata": ADD3_TMP_METADATA,
        "tmp_outputs": ADD3_TMP_OUTPUTS,
        "metadata_copy": AUDIT_DIR / "add3_sample_metadata.json",
        "outputs_copy": AUDIT_DIR / "raw_add3_agent_outputs",
    },
]


def read_csv_by_task(path):
    with path.open(newline="", encoding="utf-8") as f:
        return {row["task_index"]: row for row in csv.DictReader(f)}


def read_csv_rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def norm_yes(value):
    return "yes" if str(value).strip().lower() == "yes" else "no"


def parse_jsonish_list(value):
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except Exception:
        try:
            parsed = ast.literal_eval(text)
        except Exception:
            return [x.strip() for x in text.split("|") if x.strip()]
    if isinstance(parsed, list):
        return [str(x) for x in parsed]
    return [str(parsed)]


def labels_from_caps(row, prefix=""):
    labels = []
    for cap in CAPS:
        key = f"{prefix}{cap}" if prefix else cap
        if norm_yes(row.get(key, "")) == "yes":
            labels.append(cap)
    return labels


def json_labels(labels):
    return json.dumps(labels, ensure_ascii=False)


def join_values(values):
    if values is None:
        return ""
    if isinstance(values, list):
        return "|".join(str(v) for v in values if str(v).strip())
    return str(values)


def loose_json_load(path):
    text = path.read_text(encoding="utf-8").strip()
    candidates = [text]
    try:
        candidates.append(text.encode("utf-8").decode("unicode_escape"))
    except Exception:
        pass
    if text.startswith('"') and text.endswith('"'):
        try:
            candidates.append(json.loads(text))
        except Exception:
            pass
    errors = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        try:
            value = json.loads(candidate)
            if isinstance(value, str):
                value = json.loads(value)
            return value
        except Exception as exc:
            errors.append(str(exc))
    raise ValueError(f"Could not parse {path}: {errors[:2]}")


def find_agent_json(sample_order, task_index, outputs_dir):
    expected = outputs_dir / f"{int(sample_order):03d}_task_{task_index}.json"
    if expected.exists():
        return expected
    matches = sorted(outputs_dir.glob(f"*task_{task_index}.json"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"No agent output for sample_order={sample_order} task={task_index}")


def materialize_batch(batch):
    if batch["tmp_metadata"].exists():
        shutil.copy2(batch["tmp_metadata"], batch["metadata"])
    if batch["tmp_outputs"].exists():
        batch["outputs"].mkdir(parents=True, exist_ok=True)
        for src in sorted(batch["tmp_outputs"].glob("*.json")):
            shutil.copy2(src, batch["outputs"] / src.name)
    if not batch["metadata"].exists():
        return []
    return json.loads(batch["metadata"].read_text(encoding="utf-8"))


def classifier_issue_note(classifier_row, audit_labels):
    issues = []
    tier = classifier_row.get("search_tier", "")
    required = classifier_row.get("capability_search_required", "")
    if audit_labels:
        if tier == "skip_candidate":
            issues.append("skip_candidate_but_independent_audit_found_capability")
        if norm_yes(required) == "no":
            issues.append("capability_search_required_no_but_independent_audit_found_capability")
    return "|".join(issues)


def build_added_row(meta, audit, results_by_task, classifier_by_task, manual_tasks, input_by_task):
    task = str(meta["task_index"])
    res = results_by_task[task]
    clf = classifier_by_task.get(task, {})
    inp = input_by_task.get(task, {})

    audit_caps = {cap: norm_yes(audit.get("capabilities", {}).get(cap, "no")) for cap in CAPS}
    original_caps = {cap: norm_yes(res.get(cap, "no")) for cap in CAPS}
    original_labels = labels_from_caps(res)
    audit_labels = [cap for cap in CAPS if audit_caps[cap] == "yes"]
    mismatches = [cap for cap in CAPS if original_caps[cap] != audit_caps[cap]]

    row = {
        "sample_order": str(meta["sample_order"]),
        "task_index": task,
        "investor_id": res.get("investor_id", meta.get("investor_id", "")),
        "investor_name": res.get("investor_name", meta.get("investor_name", "")),
        "sample_stratum": meta.get("stratum", ""),
        "primary_investor_type": res.get("primary_investor_type", inp.get("PrimaryInvestorType", "")),
        "normalized_domain": res.get("normalized_domain", inp.get("normalized_domain", "")),
        "in_needs_manual_review": "yes" if task in manual_tasks else "no",
        "capability_exact_match": "yes" if not mismatches else "no",
        "mismatched_capabilities": "|".join(mismatches),
        "original_capability_labels": json_labels(original_labels),
        "audit_capability_labels": json_labels(audit_labels),
        "results_confidence": res.get("confidence", ""),
        "audit_confidence": audit.get("confidence", ""),
        "results_needs_manual_review": res.get("needs_manual_review", "yes" if task in manual_tasks else "no"),
        "audit_recommended_manual_review": audit.get("recommended_manual_review", ""),
        "classifier_search_tier": clf.get("search_tier", res.get("search_tier", "")),
        "classifier_capability_search_required": clf.get("capability_search_required", res.get("capability_search_required", "")),
        "classifier_investor_archetype": clf.get("investor_archetype", res.get("investor_archetype", "")),
        "classifier_crypto_native_likelihood": clf.get("crypto_native_likelihood", res.get("crypto_native_likelihood", "")),
        "classifier_operating_capability_likelihood": clf.get("operating_capability_likelihood", res.get("operating_capability_likelihood", "")),
        "classifier_risk_flags": clf.get("risk_flags", ""),
        "classifier_reason": clf.get("classifier_reason", res.get("capability_search_reason", "")),
        "classifier_issue_note": classifier_issue_note(clf, audit_labels),
        "input_other_investor_types": inp.get("OtherInvestorTypes", ""),
        "input_description": inp.get("Description", ""),
        "results_evidence_summary": res.get("evidence_summary", ""),
        "audit_evidence_urls": join_values(audit.get("evidence_urls", [])),
        "audit_evidence_source_types": join_values(audit.get("evidence_source_types", [])),
        "audit_evidence_summary": audit.get("evidence_summary", ""),
        "audit_yes_boundaries": join_values(audit.get("yes_boundaries", [])),
        "audit_no_boundaries": join_values(audit.get("no_boundaries", [])),
    }
    for cap in CAPS:
        row[f"original_{cap}"] = original_caps[cap]
        row[f"audit_{cap}"] = audit_caps[cap]
        row[f"mismatch_{cap}"] = "yes" if original_caps[cap] != audit_caps[cap] else "no"
    return row


def ordered_row(row, fieldnames):
    return {field: row.get(field, "") for field in fieldnames}


def cap_stats(rows):
    stats = {}
    for cap in CAPS:
        results_yes = sum(1 for row in rows if row[f"original_{cap}"] == "yes")
        audit_yes = sum(1 for row in rows if row[f"audit_{cap}"] == "yes")
        mismatches = [row for row in rows if row[f"mismatch_{cap}"] == "yes"]
        under = sum(1 for row in mismatches if row[f"original_{cap}"] == "no" and row[f"audit_{cap}"] == "yes")
        over = sum(1 for row in mismatches if row[f"original_{cap}"] == "yes" and row[f"audit_{cap}"] == "no")
        stats[cap] = {
            "results_yes": results_yes,
            "audit_yes": audit_yes,
            "mismatch_count": len(mismatches),
            "results_no_audit_yes": under,
            "results_yes_audit_no": over,
        }
    return stats


def mismatch_rows(rows):
    return [row for row in rows if row["capability_exact_match"] == "no"]


def md_table(headers, rows):
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        escaped = []
        for cell in row:
            text = str(cell).replace("\n", " ").replace("|", "\\|")
            escaped.append(text)
        out.append("| " + " | ".join(escaped) + " |")
    return "\n".join(out)


def mismatch_direction(row, cap):
    if row[f"original_{cap}"] == "no" and row[f"audit_{cap}"] == "yes":
        return "漏標"
    if row[f"original_{cap}"] == "yes" and row[f"audit_{cap}"] == "no":
        return "多標"
    return ""


def summarize_root_cause(row):
    text = " ".join([
        row.get("classifier_issue_note", ""),
        row.get("classifier_search_tier", ""),
        row.get("results_evidence_summary", ""),
        row.get("audit_evidence_summary", ""),
        row.get("audit_yes_boundaries", ""),
        row.get("audit_no_boundaries", ""),
    ]).lower()
    mismatches = row["mismatched_capabilities"].split("|") if row["mismatched_capabilities"] else []
    if row.get("classifier_issue_note"):
        return "classifier routing miss"
    if any(row[f"original_{cap}"] == "yes" and row[f"audit_{cap}"] == "no" for cap in mismatches):
        return "weak evidence over-inference or attribution too broad"
    if "sub_fund" in mismatches:
        return "fund-structure evidence not carried into sub_fund"
    if "execution_services" in mismatches and row.get("audit_otc_trading") == "yes":
        return "narrow OTC-to-execution boundary mapping"
    if ("market_making" in mismatches or "execution_services" in mismatches) and (
        "dex" in text or "amm" in text or "liquidity pool" in text or "swap" in text
    ):
        return "narrow DEX/AMM capability mapping"
    if "defi" in mismatches:
        return "DeFi specialization or product evidence missed"
    if "algorithm_trading" in mismatches:
        return "algorithmic or automated execution detail missed or mapped narrowly"
    if "market_making" in mismatches:
        return "market-making or liquidity-provision signal missed"
    if "otc_trading" in mismatches:
        return "OTC or related-platform evidence missed"
    if "affiliate" in text or "attributable" in text or "founder" in text or "co-founder" in text or "platform" in text or "group" in text:
        return "attribution boundary or related-platform evidence"
    return "evidence depth or capability-boundary interpretation"


def cap_display(cap):
    return cap


DEFINITIONS = {
    "otc_trading": {
        "rule": "只有在明確證據顯示該 investor/entity 自身提供或運營 OTC desk、block trading、大宗/雙邊場外交易、RFQ/場外流動性服務時標 Yes。",
        "yes": "官方或可靠資料明確描述 OTC desk、場外大宗撮合、block trade API、crypto-fiat/crypto-crypto OTC trading desk，即使透過可歸屬的關聯交易平台運營也可標 Yes。",
        "no": "只投資交易所、只提到二級市場投資、只買賣 OTC-listed public companies、只有一般 token allocation/SAFT、顧問或投資人關係，標 No。",
    },
    "algorithm_trading": {
        "rule": "只有在明確證據顯示 algorithmic、quantitative、systematic、HFT、low-latency、automated trading strategy，或明確 algorithmic execution/交易機器人能力時標 Yes。",
        "yes": "量化團隊、系統化策略、stat arb/CTA、HFT/低延遲交易、TWAP/VWAP、交易 bot、自動化策略，或交易平台明確提供可自動化交易能力並與 entity 運營身份相連時，標 Yes。",
        "no": "泛泛 API、研究文章、教育內容、普通 hedge fund/VC 策略、DeFi AMM 曲線本身，或二級資料不能確認 entity 自身能力，標 No。",
    },
    "market_making": {
        "rule": "只有在明確證據顯示該 investor/entity 自身提供 market making、liquidity provision、token liquidity services，或運營 DeFi AMM/流動性池協議時標 Yes。",
        "yes": "明確聲稱為項目提供做市/流動性、運營 AMM/DEX liquidity pool、提供 protocol/token liquidity support，可標 Yes。",
        "no": "交易所 maker/taker fee、使用外部 market makers、投資或合作對象有做市能力、tokenomics 裡預留 market-making allocation、一般 secondary-market trading，標 No。",
    },
    "execution_services": {
        "rule": "只有在明確證據顯示 brokerage、prime brokerage、exchange/DEX execution venue、order routing、smart order routing、FIX/API execution、liquidity access 或交易執行平台/服務時標 Yes。",
        "yes": "OTC/DEX/exchange 能讓客戶買賣/下單、API/FIX 交易接入、broker-facilitated allocations、order execution lifecycle、SOR/prime brokerage/liquidity access，標 Yes。",
        "no": "投資顧問、上市/交易所關係介紹、普通資產管理交易、小微盤融資交易，或投資/顧問關係未證明 entity 運營交易執行服務，標 No。",
    },
    "defi": {
        "rule": "只有在 investor/entity 自身運營、創立、專注、支持或明確市場化 DeFi-native protocol/product/capability 時標 Yes；僅投資 DeFi startup 不足以標 Yes。",
        "yes": "DeFi protocol、DEX、staking/farming/yield、stablecoin DeFi product、DeFi governance/support specialization、個人 founder/operator 與 DeFi 產品直接相連，可標 Yes。",
        "no": "投資組合或合作伙伴涉及 Web3/DeFi、研究/投資主題提到 DeFi、普通區塊鏈平台或消費 app 沒有 DeFi 產品，標 No。",
    },
    "sub_fund": {
        "rule": "只有在明確證據顯示 feeder、umbrella、parallel fund、SPV、series/sub-fund、fund platform、fund-of-funds、protected cell/PCC/SPC、或類似多層/子基金/投資載體結構時標 Yes。",
        "yes": "明確 fund of funds、SPV、feeder/master-feeder、protected cell、umbrella fund、parallel fund、series/sub-fund、由該 investor 設立的專門 LP/fund vehicle，標 Yes。",
        "no": "普通單一基金、基金名稱、投資多家公司、多個 portfolio、普通 syndicate 或 incubator program，沒有明確 vehicle/feeder/SPV/FOF 結構時標 No。",
    },
}


CAP_KEYWORDS = {
    "otc_trading": ["otc", "block", "bilateral", "off-platform", "rfq", "over-the-counter"],
    "algorithm_trading": ["algorithm", "quant", "systematic", "automated", "bot", "twap", "vwap", "low-latency", "hft", "api/fix", "mass quote"],
    "market_making": ["market mak", "liquidity provision", "liquidity provider", "liquidity pool", "token liquidity", "amm", "maker/taker"],
    "execution_services": ["execution", "broker", "order", "routing", "exchange", "dex", "trading venue", "api", "fix", "liquidity access", "buy/sell", "swap"],
    "defi": ["defi", "decentralized finance", "open finance", "staking", "farming", "yield", "dao", "dex", "protocol", "stablecoin"],
    "sub_fund": ["sub_fund", "sub-fund", "sub fund", "spv", "feeder", "fund of funds", "fund-of-funds", "umbrella", "parallel", "series", "pcc", "spc", "master", "protected cell"],
}


def split_boundary_notes(text):
    notes = []
    for chunk in str(text or "").split("|"):
        chunk = chunk.strip()
        if not chunk:
            continue
        notes.append(chunk)
    return notes


def best_boundary_note(row, cap, yes=True):
    source = row["audit_yes_boundaries"] if yes else row["audit_no_boundaries"]
    notes = split_boundary_notes(source)
    if not notes:
        return ""
    expected = f"{cap}={'yes' if yes else 'no'}"
    for note in notes:
        if note.lower().startswith(expected):
            return note
    lowered_keywords = CAP_KEYWORDS[cap]
    for note in notes:
        low = note.lower()
        if any(keyword in low for keyword in lowered_keywords):
            return note
    return ""


def boundary_examples(rows, cap, yes=True, limit=8):
    selected = []
    key = f"audit_{cap}"
    for row in rows:
        if row[key] == ("yes" if yes else "no"):
            note = best_boundary_note(row, cap, yes=yes)
            if note:
                selected.append((row["investor_name"], note))
        if len(selected) >= limit:
            break
    return selected


def build_main_md(rows, stats, generated_utc, generated_la):
    mismatches = mismatch_rows(rows)
    classifier_concerns = [row for row in rows if row.get("classifier_issue_note")]
    stratum_counts = Counter(row["sample_stratum"] for row in rows)
    sample_size = len(rows)
    lines = []
    lines.append(f"# Part6 Random-{sample_size} GPT-5.5 High Capability Audit")
    lines.append("")
    lines.append("## 生成資訊")
    lines.append("")
    lines.append(f"- generated_at_utc: {generated_utc}")
    lines.append(f"- generated_at_los_angeles: {generated_la}")
    lines.append("- base_sample_seed: 20260608")
    lines.append("- add60_sample_seed: 20260668")
    lines.append(f"- sample_size: {sample_size}")
    lines.append("- subagent_model: gpt-5.5")
    lines.append("- reasoning_effort: high")
    lines.append("- execution_mode: max 5 concurrent fresh subagents; one investor per subagent; subagents only received the input row and search instructions, not the Part6 output rows.")
    lines.append("- note: rows 1-30 are the original audit batch; rows 31-90 are the additional random-60 batch; rows 91-93 are targeted additions requested for Jump Crypto, Jump Trading, and Wintermute.")
    lines.append("")
    lines.append("## 讀寫檔案")
    lines.append("")
    for label, path in [
        ("Read", INPUT_CSV),
        ("Read", RESULTS_CSV),
        ("Read", CLASSIFIER_CSV),
        ("Read", MANUAL_CSV),
        ("Read for original rules", ROOT / "part6_analyse_investor_capabilities" / "agent_prompt_template.md"),
        ("Read for original rules", ROOT / "part6_analyse_investor_capabilities" / "Plan.md"),
        ("Read for original rules", ROOT / "part6_analyse_investor_capabilities" / "runtime" / "worker_base_template.md"),
        ("Wrote", OUTPUT_CSV),
        ("Wrote", OUTPUT_MD),
        ("Wrote", MISMATCH_MD),
        ("Wrote", ROOT_CAUSE_MD),
        ("Stored raw add60 outputs", ADD60_OUTPUTS),
        ("Stored raw targeted add3 outputs", ADD3_OUTPUTS),
    ]:
        lines.append(f"- {label}: `{path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}`")
    lines.append("")
    lines.append("## 抽樣設計")
    lines.append("")
    lines.append(f"本次是 audit sample，不是對全量 13,970 records 的統計外推。前 90 家由原始 30 家與新增 60 家組成，新增樣本排除已抽中的 30 家，仍從 positive capability、searched negative、skip candidate、manual-focused 幾類中分層抽取。第 91-93 家是 user-requested targeted comparison：Jump Crypto、Jump Trading、Wintermute。目的仍是檢查能力標籤漏標、誤標與分類器跳過風險。")
    lines.append("")
    lines.append(md_table(["sample_stratum", "count"], sorted(stratum_counts.items())))
    lines.append("")
    lines.append("## 核心結論")
    lines.append("")
    lines.append(f"- 六個能力完全一致: {sum(1 for row in rows if row['capability_exact_match'] == 'yes')}/{len(rows)}")
    lines.append(f"- 至少一個能力不一致: {len(mismatches)}/{len(rows)}")
    lines.append(f"- 不一致且已在 `needs_manual_review.csv`: {sum(1 for row in mismatches if row['in_needs_manual_review'] == 'yes')}/{len(mismatches)}")
    lines.append(f"- 不一致但不在 `needs_manual_review.csv`: {sum(1 for row in mismatches if row['in_needs_manual_review'] == 'no')}/{len(mismatches)}")
    lines.append(f"- classifier/routing concern: {len(classifier_concerns)} sampled rows")
    lines.append("")
    lines.append(md_table(
        ["capability", "results_yes", "audit_yes", "mismatch_count", "results_no_audit_yes", "results_yes_audit_no"],
        [
            [cap, s["results_yes"], s["audit_yes"], s["mismatch_count"], s["results_no_audit_yes"], s["results_yes_audit_no"]]
            for cap, s in stats.items()
        ],
    ))
    lines.append("")
    lines.append("## 不一致公司與 Manual Review 狀態")
    lines.append("")
    lines.append("下表直接回答不一致公司是否在 `needs_manual_review.csv`。")
    lines.append("")
    lines.append(md_table(
        ["task", "investor", "in_needs_manual_review", "mismatched_capabilities", "results_labels", "audit_labels", "classifier_search_tier", "classifier_required", "classifier_issue"],
        [
            [
                row["task_index"],
                row["investor_name"],
                row["in_needs_manual_review"],
                row["mismatched_capabilities"],
                row["original_capability_labels"],
                row["audit_capability_labels"],
                row["classifier_search_tier"],
                row["classifier_capability_search_required"],
                row["classifier_issue_note"],
            ]
            for row in mismatches
        ],
    ))
    lines.append("")
    lines.append("## Classifier 對照觀察")
    lines.append("")
    if classifier_concerns:
        lines.append("以下 row 出現明確 routing concern：分類器判為 `skip_candidate` 或 `capability_search_required=no`，但獨立審核搜索到至少一個能力為 Yes。")
        lines.append("")
        lines.append(md_table(
            ["task", "investor", "classifier_search_tier", "classifier_required", "audit_labels", "in_needs_manual_review", "reason"],
            [
                [
                    row["task_index"],
                    row["investor_name"],
                    row["classifier_search_tier"],
                    row["classifier_capability_search_required"],
                    row["audit_capability_labels"],
                    row["in_needs_manual_review"],
                    row["classifier_reason"],
                ]
                for row in classifier_concerns
            ],
        ))
    else:
        lines.append(f"本次 {sample_size} 家樣本沒有發現明確 classifier/routing concern。")
    lines.append("")
    lines.append("其餘不一致大多發生在已被分類器送入 `full` 或 `light` 搜索的 records，較像能力判定邊界、來源深度或 attribution interpretation 問題，而不是單純分類器跳過問題。")
    lines.append("")
    lines.append("## 六個能力定義與邊界")
    lines.append("")
    lines.append("以下定義以 Part6 原始提示詞/計劃中的規則為基礎重述：能力必須由 investor/entity 自身或可歸屬的 operating platform 證據支持；投資組合曝光、泛泛行業描述或普通基金資料不夠。")
    for cap in CAPS:
        d = DEFINITIONS[cap]
        lines.append("")
        lines.append(f"### {cap}")
        lines.append("")
        lines.append(f"- Rule: {d['rule']}")
        lines.append(f"- Yes boundary: {d['yes']}")
        lines.append(f"- No boundary: {d['no']}")
        yes_examples = boundary_examples(rows, cap, yes=True, limit=8)
        no_examples = boundary_examples(rows, cap, yes=False, limit=8)
        if yes_examples:
            lines.append("")
            lines.append("Yes boundary examples from this audit:")
            lines.append("")
            lines.append(md_table(["investor", "why_yes"], yes_examples))
        if no_examples:
            lines.append("")
            lines.append("No / near-miss boundary examples from this audit:")
            lines.append("")
            lines.append(md_table(["investor", "why_no"], no_examples))
    lines.append("")
    lines.append(f"## Full {sample_size}-Company Sample")
    lines.append("")
    lines.append(md_table(
        ["order", "task", "investor", "stratum", "manual_review", "exact_match", "mismatches", "results_labels", "audit_labels", "audit_confidence"],
        [
            [
                row["sample_order"],
                row["task_index"],
                row["investor_name"],
                row["sample_stratum"],
                row["in_needs_manual_review"],
                row["capability_exact_match"],
                row["mismatched_capabilities"],
                row["original_capability_labels"],
                row["audit_capability_labels"],
                row["audit_confidence"],
            ]
            for row in rows
        ],
    ))
    lines.append("")
    lines.append("## Mismatch Evidence Summaries")
    lines.append("")
    for i, row in enumerate(mismatches, 1):
        lines.append(f"### {i}. {row['investor_name']} - task {row['task_index']}")
        lines.append("")
        lines.append(f"- In `needs_manual_review.csv`: {row['in_needs_manual_review']}")
        lines.append(f"- Results labels: `{row['original_capability_labels']}`")
        lines.append(f"- Audit labels: `{row['audit_capability_labels']}`")
        lines.append(f"- Mismatched capabilities: `{row['mismatched_capabilities']}`")
        lines.append(f"- Original evidence summary: {row['results_evidence_summary']}")
        lines.append(f"- Audit evidence summary: {row['audit_evidence_summary']}")
        if row["audit_yes_boundaries"]:
            lines.append(f"- Audit Yes boundary notes: {row['audit_yes_boundaries']}")
        if row["audit_no_boundaries"]:
            lines.append(f"- Audit No boundary notes: {row['audit_no_boundaries']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_mismatch_md(rows, generated_utc):
    mismatches = mismatch_rows(rows)
    sample_size = len(rows)
    cap_mismatch_total = sum(1 for row in rows for cap in CAPS if row[f"mismatch_{cap}"] == "yes")
    under = sum(1 for row in rows for cap in CAPS if row[f"original_{cap}"] == "no" and row[f"audit_{cap}"] == "yes")
    over = sum(1 for row in rows for cap in CAPS if row[f"original_{cap}"] == "yes" and row[f"audit_{cap}"] == "no")
    classifier_concerns = [row for row in rows if row.get("classifier_issue_note")]
    lines = []
    lines.append(f"# Part6 Random-{sample_size} Audit - Mismatch Analysis")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- generated_at_utc: {generated_utc}")
    lines.append(f"- Mismatch companies: {len(mismatches)}/{len(rows)}")
    lines.append(f"- Capability-level mismatches: {cap_mismatch_total}")
    lines.append(f"- Results.csv likely under-labeled capabilities in the audit comparison: {under} capability decisions")
    lines.append(f"- Results.csv likely over-labeled capabilities in the audit comparison: {over} capability decisions")
    lines.append(f"- Mismatch companies already in `needs_manual_review.csv`: {sum(1 for row in mismatches if row['in_needs_manual_review'] == 'yes')}")
    lines.append(f"- Mismatch companies not in `needs_manual_review.csv`: {sum(1 for row in mismatches if row['in_needs_manual_review'] == 'no')}")
    lines.append(f"- Clear classifier routing concern: {len(classifier_concerns)} rows")
    lines.append("")
    lines.append("This file explains why each row was judged inconsistent. The comparison scope is only the six investor capability flags: `otc_trading`, `algorithm_trading`, `market_making`, `execution_services`, `defi`, and `sub_fund`.")
    lines.append("")
    for i, row in enumerate(mismatches, 1):
        mism_caps = row["mismatched_capabilities"].split("|") if row["mismatched_capabilities"] else []
        directions = ", ".join(f"{mismatch_direction(row, cap)} `{cap}`" for cap in mism_caps)
        lines.append(f"## {i}. {row['investor_name']} - task {row['task_index']}")
        lines.append("")
        lines.append(f"- In `needs_manual_review.csv`: {row['in_needs_manual_review']}")
        lines.append(f"- Results labels: `{row['original_capability_labels']}`")
        lines.append(f"- Audit labels: `{row['audit_capability_labels']}`")
        lines.append(f"- Mismatched capability decisions: {directions}")
        if row["classifier_issue_note"]:
            lines.append(f"- Classifier issue: `{row['classifier_issue_note']}`")
        lines.append("")
        lines.append(f"The inconsistency is `{row['mismatched_capabilities']}`. Original results evidence says: {row['results_evidence_summary']}")
        lines.append("")
        lines.append(f"The independent audit judged differently because: {row['audit_evidence_summary']}")
        if row["audit_yes_boundaries"]:
            lines.append("")
            lines.append(f"Audit Yes boundary notes: {row['audit_yes_boundaries']}")
        if row["audit_no_boundaries"]:
            lines.append("")
            lines.append(f"Audit No / near-miss notes: {row['audit_no_boundaries']}")
        lines.append("")
        lines.append(f"Interpretation: this looks like {summarize_root_cause(row)}. The row should be reviewed if that boundary is not intended by the final Part6 policy.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def build_root_cause_md(rows, generated_utc):
    mismatches = mismatch_rows(rows)
    sample_size = len(rows)
    category_counts = Counter(summarize_root_cause(row) for row in mismatches)
    lines = []
    lines.append(f"# Part6 Random-{sample_size} Audit - Original Label Root Cause Analysis")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append(f"- generated_at_utc: {generated_utc}")
    lines.append("- This file analyzes why the original Part6 output likely missed or over-labeled each inconsistent company.")
    lines.append("- The analysis is inferred from `results.csv`, `classifier_results.csv`, `needs_manual_review.csv`, and the independent GPT-5.5-high audit outputs.")
    lines.append("- This is a root-cause inference, not a transcript of the original worker's hidden reasoning.")
    lines.append("")
    lines.append("## Root-Cause Categories")
    lines.append("")
    lines.append("- Narrow boundary interpretation: original worker found the source but interpreted the capability boundary too narrowly.")
    lines.append("- Evidence not searched deeply enough: original worker found the main capability but did not search legal docs, fund filings, product docs, or related official pages.")
    lines.append("- Attribution boundary: evidence belongs to a linked operating platform, group entity, or associated person, and original worker used a narrower attribution rule.")
    lines.append("- Weak evidence over-inference: original worker inferred a capability from generic or secondary evidence that did not satisfy the stricter audit threshold.")
    lines.append("- Classifier routing miss: classifier skipped or under-routed the row, so the worker had no chance to find the capability.")
    lines.append("")
    lines.append("## Category Counts")
    lines.append("")
    lines.append(md_table(["root_cause_inference", "count"], sorted(category_counts.items())))
    lines.append("")
    lines.append("## Company-Level Analysis")
    lines.append("")
    for i, row in enumerate(mismatches, 1):
        mism_caps = row["mismatched_capabilities"].split("|") if row["mismatched_capabilities"] else []
        directions = ", ".join(f"{mismatch_direction(row, cap)} `{cap}`" for cap in mism_caps)
        root = summarize_root_cause(row)
        lines.append(f"### {i}. {row['investor_name']} - {directions}")
        lines.append("")
        lines.append(f"- Task: {row['task_index']}")
        lines.append(f"- Original labels: `{row['original_capability_labels']}`")
        lines.append(f"- Audit labels: `{row['audit_capability_labels']}`")
        lines.append(f"- Manual review: {row['in_needs_manual_review']}")
        lines.append(f"- Likely root cause: {root}.")
        lines.append("")
        if row["classifier_issue_note"]:
            lines.append(f"The classifier routed this row as `{row['classifier_search_tier']}` with `capability_search_required={row['classifier_capability_search_required']}`. Because the independent audit found `{row['audit_capability_labels']}`, the miss likely began before the capability worker searched the row.")
            lines.append("")
        lines.append(f"The original evidence summary was: {row['results_evidence_summary']}")
        lines.append("")
        lines.append(f"The audit evidence summary was: {row['audit_evidence_summary']}")
        lines.append("")
        for cap in mism_caps:
            direction = mismatch_direction(row, cap)
            if direction == "漏標":
                note = best_boundary_note(row, cap, yes=True) or row["audit_yes_boundaries"] or row["audit_evidence_summary"]
                lines.append(f"For `{cap}`, the original output likely missed a positive signal. The audit-side boundary note was: {note}")
            elif direction == "多標":
                note = best_boundary_note(row, cap, yes=False) or row["audit_no_boundaries"] or row["audit_evidence_summary"]
                lines.append(f"For `{cap}`, the original output likely over-inferred from weak, generic, stale, or too-broad attribution evidence. The audit-side exclusion note was: {note}")
        lines.append("")
    lines.append("## Practical Fixes Suggested By The Root Causes")
    lines.append("")
    lines.append("1. Add a worker checklist: if `otc_trading=yes`, explicitly test whether the same evidence also implies `execution_services=yes`.")
    lines.append("2. Add a DEX/AMM rule: if the entity operates a DEX, swap venue, or cross-chain trading product, test `execution_services=yes`; if it operates AMM/liquidity pools/liquidity mining, test `market_making=yes`.")
    lines.append("3. Add a fund-structure search step for asset managers and PE/VC firms: search legal docs, filings, terms pages, and fund names for feeder, SPC, PCC, SPV, umbrella, series, master, and fund-of-funds.")
    lines.append("4. Tighten `algorithm_trading` evidence standards for hedge funds: secondary strategy snippets should not be enough unless they explicitly say algorithmic, quantitative, systematic, HFT, low-latency, automated, TWAP/VWAP, bot, or similar.")
    lines.append("5. Add an attribution flag for individuals and affiliated operators: platform capabilities attributed to a founder/chairman, group entity, or associated operator should usually set `needs_manual_review=yes`.")
    lines.append("6. Revisit `skip_candidate` for traditional fund managers: even non-crypto PE/family-office records can have `sub_fund` structures, so skip logic should not exclude fund-vehicle checks solely because crypto/operating signals are low.")
    return "\n".join(lines).rstrip() + "\n"


def main():
    existing_rows = read_csv_rows(ORIGINAL_AUDIT_CSV)
    fieldnames = list(existing_rows[0].keys())
    base_rows = [row for row in existing_rows if int(row["sample_order"]) <= 30]

    results_by_task = read_csv_by_task(RESULTS_CSV)
    classifier_by_task = read_csv_by_task(CLASSIFIER_CSV)
    manual_tasks = set(read_csv_by_task(MANUAL_CSV))
    input_by_task = read_csv_by_task(INPUT_CSV)

    batch_items = []
    for batch in BATCHES:
        for meta in materialize_batch(batch):
            batch_items.append((batch, meta))

    added_rows = []
    for batch, meta in batch_items:
        audit_path = find_agent_json(meta["sample_order"], meta["task_index"], batch["outputs"])
        audit = loose_json_load(audit_path)
        added_rows.append(build_added_row(meta, audit, results_by_task, classifier_by_task, manual_tasks, input_by_task))

    rows = base_rows + [ordered_row(row, fieldnames) for row in added_rows]
    rows.sort(key=lambda row: int(row["sample_order"]))

    expected_count = len(base_rows) + len(batch_items)
    if len(rows) != expected_count:
        raise SystemExit(f"Expected {expected_count} rows, got {len(rows)}")
    orders = [int(row["sample_order"]) for row in rows]
    if orders != list(range(1, expected_count + 1)):
        raise SystemExit(f"Sample orders are not 1..{expected_count}: {orders[:5]} ... {orders[-5:]}")
    tasks = [row["task_index"] for row in rows]
    if len(set(tasks)) != expected_count:
        raise SystemExit("Duplicate task_index in merged audit rows")

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    generated_utc_dt = datetime.now(timezone.utc)
    generated_utc = generated_utc_dt.isoformat()
    generated_la = generated_utc_dt.astimezone(ZoneInfo("America/Los_Angeles")).isoformat()
    stats = cap_stats(rows)

    OUTPUT_MD.write_text(build_main_md(rows, stats, generated_utc, generated_la), encoding="utf-8")
    MISMATCH_MD.write_text(build_mismatch_md(rows, generated_utc), encoding="utf-8")
    ROOT_CAUSE_MD.write_text(build_root_cause_md(rows, generated_utc), encoding="utf-8")

    mismatches = mismatch_rows(rows)
    print(json.dumps({
        "rows": len(rows),
        "mismatch_companies": len(mismatches),
        "exact_matches": sum(1 for row in rows if row["capability_exact_match"] == "yes"),
        "manual_review_mismatches": sum(1 for row in mismatches if row["in_needs_manual_review"] == "yes"),
        "non_manual_review_mismatches": sum(1 for row in mismatches if row["in_needs_manual_review"] == "no"),
        "classifier_concerns": sum(1 for row in rows if row.get("classifier_issue_note")),
        "capability_stats": stats,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
