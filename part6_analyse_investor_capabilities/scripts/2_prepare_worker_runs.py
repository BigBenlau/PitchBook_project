#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from part6_schema import CLASSIFIER_CSV_COLUMNS, RESULT_CSV_COLUMNS, VERIFICATION_CSV_COLUMNS


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART6_DIR.parent
RUNTIME_DIR = PART6_DIR / "runtime"
WORKER_BASE_TEMPLATE_PATH = RUNTIME_DIR / "worker_base_template.md"
DEFAULT_POLICY_PATH = RUNTIME_DIR / "policy.json"

DEFAULT_BATCH_DIR = REPO_ROOT / "part5_to_part6" / "output" / "part6_batches"
DEFAULT_RUNS_DIR = PART6_DIR / "agent_runs" / "crypto_investor_parallel"
DEFAULT_WORKERS = 5

SCHEDULE_COLUMNS = [
    "round_index",
    "worker_slot",
    "slot_id",
    "queue_order",
    "queue_state",
    "collect_state",
    "ready_to_collect_at",
    "collected_at",
    "last_collected_attempt_index",
    "collect_failure_reason",
    "batch_file",
    "task_count",
    "first_task_index",
    "last_task_index",
    "first_company",
    "last_company",
    "run_dir",
    "tasks_file",
    "base_instructions_file",
    "attempts_dir",
    "active_attempt",
    "attempt_index",
    "attempt_metadata_file",
    "current_attempt_mode",
    "classifier_results_csv",
    "results_csv",
    "instructions_file",
    "active_lease_file",
    "lease_id",
    "attempt_start_prefix_rows",
    "planned_rotate",
    "segment_target_rows",
    "segment_hard_cap_rows",
    "prepared_mode",
    "prepared_reason",
    "last_failure_type",
    "failure_counts_json",
    "consecutive_no_progress_attempts",
    "verifier_dir",
    "verification_report_csv",
    "verification_summary_md",
    "verifier_instructions_file",
    "status",
    "respawn_count",
    "last_rerun_reason",
    "last_rerun_at",
    "started_at",
    "first_row_at",
    "last_progress_at",
    "last_seen_classifier_rows",
    "last_seen_result_rows",
    "startup_failure_count",
    "stall_failure_count",
    "escalation_level",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare 5-worker Codex run directories from Part5-to-Part6 investor batch JSONL files.",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=DEFAULT_BATCH_DIR,
        help="Directory containing batch_XXXX.jsonl files.",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help="Directory where per-batch worker run folders will be created.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of parallel workers per round. Defaults to 5.",
    )
    parser.add_argument(
        "--start-batch",
        type=int,
        default=1,
        help="First batch number to include, e.g. 1 for batch_0001.jsonl.",
    )
    parser.add_argument(
        "--limit-batches",
        type=int,
        default=0,
        help="Maximum number of batches to prepare. 0 means all selected batches.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite tasks.jsonl, instructions.md, and empty results.csv files.",
    )
    return parser.parse_args()


def ensure_dir(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_dir():
        raise SystemExit(f"{label} is not a directory: {resolved}")
    return resolved


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def load_policy(path: Path = DEFAULT_POLICY_PATH) -> dict:
    with path.open("r", encoding="utf-8") as infile:
        return json.load(infile)


def load_segment_policy(path: Path = DEFAULT_POLICY_PATH) -> dict[str, int]:
    raw = load_policy(path).get("segment_policy") or {}
    target_rows = int(raw.get("target_rows_per_attempt", 12))
    hard_cap_rows = int(raw.get("hard_cap_rows_per_attempt", 15))
    if target_rows <= 0:
        target_rows = 12
    if hard_cap_rows < target_rows:
        hard_cap_rows = target_rows
    return {
        "target_rows_per_attempt": target_rows,
        "hard_cap_rows_per_attempt": hard_cap_rows,
    }


def make_lease_id(worker_slot: int, attempt_index: int) -> str:
    timestamp = now_utc().strftime("%Y%m%dT%H%M%S%fZ")
    return f"slot{worker_slot:02d}-attempt{attempt_index:04d}-{timestamp}"


def attempt_metadata_path(attempt_dir: Path) -> Path:
    return attempt_dir / "attempt_metadata.json"


def active_lease_path(run_dir: Path) -> Path:
    return run_dir / "active_attempt_lease.json"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def batch_number(path: Path) -> int:
    stem = path.stem
    try:
        return int(stem.split("_", 1)[1])
    except (IndexError, ValueError):
        raise SystemExit(f"Unexpected batch file name: {path.name}") from None


def load_tasks(path: Path) -> list[dict]:
    tasks: list[dict] = []
    with path.open("r", encoding="utf-8") as infile:
        for line in infile:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def count_result_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        return sum(1 for _ in reader)


def results_has_data(path: Path) -> bool:
    return count_result_rows(path) > 0


def write_results_header(path: Path, force: bool) -> None:
    if path.exists() and results_has_data(path) and not force:
        return
    if path.exists() and not force:
        return
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(RESULT_CSV_COLUMNS)


def write_classifier_header(path: Path, force: bool) -> None:
    if path.exists() and results_has_data(path) and not force:
        return
    if path.exists() and not force:
        return
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(CLASSIFIER_CSV_COLUMNS)


def write_verification_header(path: Path, force: bool) -> None:
    if path.exists() and results_has_data(path) and not force:
        return
    if path.exists() and not force:
        return
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(VERIFICATION_CSV_COLUMNS)


def build_initial_attempt_instructions(
    *,
    base_instruction_text: str,
    attempt_dir: Path,
    tasks_path: Path,
    active_lease_file: Path,
    lease_id: str,
    segment_target_rows: int,
    segment_hard_cap_rows: int,
) -> str:
    return (
        "# Attempt Runtime Wrapper\n\n"
        "- attempt_mode: fresh_full_batch\n"
        f"- attempt_dir: {attempt_dir}\n"
        f"- authoritative write scope: {attempt_dir}\n"
        f"- authoritative classifier CSV: {attempt_dir / 'classifier_results.csv'}\n"
        f"- authoritative results CSV: {attempt_dir / 'results.csv'}\n"
        f"- authoritative tasks file: {tasks_path}\n"
        f"- active lease file: {active_lease_file}\n"
        f"- required lease_id: {lease_id}\n"
        "- Ignore older attempt directories and older CSV locations.\n"
        "- This is the default full-batch attempt. Start from the first task and write rows in order.\n"
        "- Own the entire batch in this single fresh worker and continue until the batch is complete or an explicit blocker is reached.\n"
        "- Do not proactively hand off or segment the batch in this normal mode.\n"
        "- Recovery-only segment settings exist for later reruns, but they do not apply to this initial full-batch attempt.\n"
        "- Write incrementally. Append rows as soon as each investor is completed.\n"
        "- The harness watches startup no-row and partial-stall conditions. Lack of row growth may cause this attempt to be terminated.\n\n"
        "--- BEGIN BASE INSTRUCTIONS ---\n\n"
        f"{base_instruction_text.rstrip()}\n\n"
        "--- END BASE INSTRUCTIONS ---\n"
    )


def load_worker_base_template() -> str:
    return WORKER_BASE_TEMPLATE_PATH.read_text(encoding="utf-8")


def render_worker_base_instructions(
    *,
    batch_file: Path,
    run_dir: Path,
    tasks: list[dict],
    round_index: int,
    worker_slot: int,
) -> str:
    first = tasks[0]
    last = tasks[-1]
    mapping = {
        "WORKER_SLOT": str(worker_slot),
        "ROUND_INDEX": str(round_index),
        "RUN_DIR": str(run_dir),
        "RUNTIME_ARCHITECTURE": str(RUNTIME_DIR / "ARCHITECTURE.md"),
        "RUNTIME_POLICY": str(RUNTIME_DIR / "policy.json"),
        "PLAN_MD": str(PART6_DIR / "Plan.md"),
        "BATCH_FILE": str(batch_file),
        "TASKS_FILE": str(run_dir / "tasks.jsonl"),
        "PROMPT_TEMPLATE": str(PART6_DIR / "agent_prompt_template.md"),
        "BATCH_FILE_NAME": batch_file.name,
        "TASK_COUNT": str(len(tasks)),
        "FIRST_TASK_INDEX": str(first.get("task_index", "")),
        "FIRST_COMPANY": str(first.get("investor_name", "")),
        "LAST_TASK_INDEX": str(last.get("task_index", "")),
        "LAST_COMPANY": str(last.get("investor_name", "")),
        "CLASSIFIER_CSV_HEADER": ",".join(CLASSIFIER_CSV_COLUMNS),
        "RESULT_CSV_HEADER": ",".join(RESULT_CSV_COLUMNS),
    }
    rendered = load_worker_base_template()
    for key, value in mapping.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    search_guarantee_markers = [str(batch_file), str(run_dir)]
    full_search_rerun = any(
        "full_search_rerun" in marker or "skip_rule_full_rerun" in marker
        for marker in search_guarantee_markers
    )
    if full_search_rerun:
        rendered = (
            f"{rendered.rstrip()}\n\n"
            "Full-search rerun override for prior skip-rule violations:\n"
            "- This rerun exists because prior rows used `search_tier = skip_candidate` despite non-low likelihood signals.\n"
            "- Every investor in this batch must use `search_tier = full` and `capability_search_required = yes`.\n"
            "- Do not use `search_tier = skip_candidate` or `search_tier = light` for any row in this rerun batch.\n"
            "- A no-capability conclusion is allowed only after full current-source search with non-empty absolute HTTP(S) `evidence_urls` and valid `evidence_source_types`.\n"
            "- If no reliable current official/trusted source exists after real search, keep all capabilities `no`, set `confidence = low`, `needs_manual_review = yes`, leave evidence fields blank, and add `identity_unresolved` or `no_reliable_external_match` to `other_flags`.\n"
            "- Copy `task_index`, `investor_id`, `investor_name`, `normalized_domain`, and `primary_investor_type` exactly from `tasks.jsonl`.\n"
        )
    elif any("rerun_manual_fallbacks" in marker for marker in search_guarantee_markers):
        rendered = (
            f"{rendered.rstrip()}\n\n"
            "Search-guarantee override for previously manual-fallback batches:\n"
            "- This rerun window exists to guarantee actual search coverage. Do not use `search_tier = skip_candidate` in this rerun batch.\n"
            "- Every investor in this batch must receive at least `light` search, so `capability_search_required` must be `yes` for every investor.\n"
            "- A no-capability conclusion is allowed only after real search using current official/exact-match sources, with non-empty `evidence_urls` and `evidence_source_types`.\n"
            "- If no reliable current official/trusted source exists after real search, keep all capabilities `no`, set `confidence = low`, `needs_manual_review = yes`, leave evidence fields blank, and add `identity_unresolved` or `no_reliable_external_match` to `other_flags`.\n"
            "- Do not close a row as no-capability only from investor-type heuristics; perform the bounded or full search first, then conclude `capability_labels = []` if appropriate.\n"
        )
    return rendered


def build_worker_instructions(
    batch_file: Path,
    run_dir: Path,
    tasks: list[dict],
    round_index: int,
    worker_slot: int,
) -> str:
    return render_worker_base_instructions(
        batch_file=batch_file,
        run_dir=run_dir,
        tasks=tasks,
        round_index=round_index,
        worker_slot=worker_slot,
    )


def build_verifier_instructions(
    round_index: int,
    round_rows: list[dict[str, str]],
    verifier_dir: Path,
    verification_report: Path,
    verification_summary: Path,
) -> str:
    result_paths = "\n".join(f"- {row['results_csv']}" for row in round_rows)
    classifier_paths = "\n".join(f"- {row['classifier_results_csv']}" for row in round_rows)
    task_paths = "\n".join(f"- {row['tasks_file']}" for row in round_rows)
    task_ranges = "\n".join(
        f"- {row['batch_file']}: task_index {row['first_task_index']} to {row['last_task_index']}"
        for row in round_rows
    )
    return f"""# Part6 Round-End Verifier

You are a fresh verifier subagent for part6 round {round_index}.

You are not the worker that produced these rows. Re-check independently.

Exclusive write scope:
- {verifier_dir}

Read first:
- {PART6_DIR / "Plan.md"}
- {PART6_DIR / "agent_prompt_template.md"}

Round task ranges:
{task_ranges}

Input task files:
{task_paths}

Classifier result files:
{classifier_paths}

Worker result files:
{result_paths}

Task:
- Independently check whether each investor's `capability_labels` JSON list is correct.
- Read the classifier/router result for every row before judging the worker result.
- Check whether `search_tier` was too conservative for the row.
- Check whether any `skip_candidate` decision was unreasonable or should have been routed to `light` or `full`.
- Detect missing capability labels.
- Detect extra or unsupported capability labels.
- Detect wrong investor archetype or investor/business mapping.
- Detect `capability_search_required = no` rows that should have been searched.
- Focus on capability-positive rows, skipped-search rows, ambiguous brands, low/medium confidence rows, and mixed operating/investing profiles.
- Apply the global source hierarchy from `Plan.md` and `agent_prompt_template.md`: current official source > current official portfolio/backer page > trusted third-party database > stale database / ordinary news / social media / local PitchBook input. Ordinary news, social media, and local PitchBook are search/disambiguation context only, not direct `yes` evidence. If entity identity, current status, parent/control relationship, official-vs-database conflict, self-operated-vs-third-party service, or source attribution remains unclear after one extra pass, recommend `needs_manual_review = yes`.
- For parent/control attribution, accept only wholly owned subsidiaries, controlled subsidiaries, controlled operating divisions, controlled business units, controlled brands/platforms, or official group entities. Reject portfolio companies, minority investments, LP investments, partners, ecosystem members, unaffiliated affiliates, ordinary clients, and service providers as controlled subsidiaries/operating units.
- For `otc_trading`, use the current operating-capability definition from `Plan.md` and `agent_prompt_template.md`. Verify current direct OTC service and one-way parent inheritance from controlled subsidiaries/arms. Reject portfolio exposure, stale/historical OTC, liquidity-only language, broker-dealer/market-maker status alone, OTC access-only, settlement/custody-only, DEX RFQ, intent/on-chain RFQ, on-chain block trade, and individual founder/advisor/executive association as `otc_trading = yes` evidence.
- For `algorithm_trading`, use the current operating-capability definition from `Plan.md` and `agent_prompt_template.md`. Verify current direct algorithmic/quantitative/systematic/HFT/automated trading capability and one-way parent inheritance from controlled subsidiaries/operating units. Reject portfolio exposure, stale/historical algorithm trading, market-maker status alone, proprietary-trading status alone, liquidity-provider language alone, "technology-driven trading firm" language alone, API/FIX/connectivity, low-latency access alone, smart order routing alone, TWAP/VWAP alone, routing/execution algorithms alone, brokerage/execution/liquidity-access evidence without explicit algorithm-trading service/agency capability, and individual founder/advisor/executive association as `algorithm_trading = yes` evidence.
- For `market_making`, use the current operating-capability definition from `Plan.md` and `agent_prompt_template.md`. Verify current direct market-making or liquidity-provision service using the investor's own/controlled capital, one-way parent inheritance from controlled subsidiaries/operating units, official/designated market-maker or liquidity-provider roles, LP roles, and OTC principal/balance-sheet liquidity. Reject portfolio exposure, stale/historical market making, generic liquidity-provider/deep-liquidity language, liquidity access, quotes/pricing only, routing/matching/execution venue operation, exchange/broker/prime-broker status alone, proprietary-trading/HFT/quant status alone, passive fund investment, passive LP allocation, client portfolio allocation, AMM/DEX/pool operation without LP capital, protocol/token liquidity support that is not the investor's own ongoing LP/market-maker role, third-party market-maker allocations, and individual founder/advisor/executive association as `market_making = yes` evidence.
- For `execution_services`, use the current operating-capability definition from `Plan.md` and `agent_prompt_template.md`. Verify current direct order placement, order handling, executable broker service, trade execution, matching engine, trading venue, exchange/CEX, ATS/MTF/ECN, DEX, swap, perp DEX, AMM, or on-chain trading protocol operation, plus one-way parent inheritance from controlled subsidiaries/operating units. Reject portfolio exposure, stale/historical execution, routing/smart routing alone, API/FIX/connectivity alone, liquidity access/aggregation alone, connecting to third-party liquidity/venues, white-label/embedded third-party execution, redirect-to-external-venue trading, wallet external-link trading, custody/settlement/clearing/post-trade-only services, market making alone, OTC desk alone, view-only wallet/portfolio/analytics tools, and individual founder/advisor/executive association as `execution_services = yes` evidence.
- For `defi`, use the current DeFi trading / DeFi protocol operation definition from `Plan.md` and `agent_prompt_template.md`. Verify both false positives and false negatives using current official sources or trusted third-party databases. Current DeFi protocol operation, DeFi trading, LP/yield/staking/restaking deployment, DeFi market-making/liquidity provision, on-chain arbitrage/MEV/liquidation, managed DeFi strategy, or one-way parent attribution from a controlled child can support `defi = yes`. Reject DeFi company portfolio exposure, token investment/SAFT/grants/accelerator/ecosystem support, DeFi-adjacent infrastructure exposure, CEX/broker customer DeFi access, unaffiliated affiliates, uncontrolled funds, and stale/historical DeFi activity unless the source also shows current DeFi trading/protocol-use/operation by the investor row, its managed fund vehicle, or a controlled child.
- For `sub_fund`, use the current parent/mother-entity structure definition from `Plan.md` and `agent_prompt_template.md`. Verify that the current investor row currently owns, controls, contains, or has under it a child sub-fund, fund vehicle, venture arm, investment arm, crypto arm, dedicated capital pool, dedicated investment/trading branch, or comparable sub-fund-like structure. Reject rows that are merely fund vehicles, feeders, SPVs, protected cells, venture arms, investment arms, crypto arms, subsidiaries, brands, ordinary business units, accelerators/incubators, ecosystem programs, portfolio companies, ordinary CVC types, externally managed vehicles, generic fund managers, ordinary closed funds, name-only matches, `LastClosedFundName`/`PrimaryInvestorType` matches, specific sample-entity analogies, or stale/historical structures with no current official/trusted confirmation.
- If you detect a systematic issue pattern, report it explicitly for the main agent using one of these cause labels when applicable: `classification`, `search`, `evidence_interpretation`, `csv_formatting`, `prompt_ambiguity`, `run_harness`, `other`.

Search policy:
- Search freely.
- Use independent queries, not only worker evidence URLs.
- Prefer official and primary sources when available.
- Use secondary sources only for corroboration or disambiguation.

Write:
- {verification_report}
- {verification_summary}

CSV header:
{",".join(VERIFICATION_CSV_COLUMNS)}

Every row in the round should appear in `verification_report.csv`. Use `verdict = pass` when the worker row is acceptable.

Allowed verdict values:
- pass
- suspected_missing_capability
- suspected_extra_capability
- wrong_archetype_or_mapping
- search_tier_too_conservative
- search_should_not_have_been_skipped
- insufficient_evidence

Hard schema rule: do not use any other verdict token. In particular, `fail`,
`failed`, `error`, `needs_fix`, and free-text verdicts are invalid and will
stop collection at the verifier gate. If the worker row needs an edit, choose
the closest allowed non-pass verdict above and set `recommended_action =
edit_row`.

Allowed recommended_action values:
- accept_worker_row
- edit_row
- mark_manual_review
- rerun_investor
- rerun_batch
- update_prompt_or_process

Authoritative correction rule:
- If `recommended_action = edit_row`, fill `corrected_result_row_json` with a full JSON object using the exact result-row schema.
- The corrected JSON must contain all result columns, not only the edited fields.
- The collector will apply that corrected row directly if it passes validation.
- If a searched worker row found no reliable current official/trusted source
  and all capabilities are `no`, do not use `rerun_investor` just because
  evidence fields are blank. Use `mark_manual_review` or `edit_row` so the row
  has `confidence = low`, `needs_manual_review = yes`, and an `other_flags`
  marker such as `identity_unresolved` or `no_reliable_external_match`.

`verification_summary.md` must include:
- checked row count
- pass count
- non-pass count
- suspected missing capability count
- suspected extra capability count
- wrong mapping count
- skipped-search concern count
- systematic causes found
- recommended process updates
- explicit feedback items for the main agent when a rerun, prompt change, or process change is recommended
"""


def build_worker_spawn_prompt(row: dict[str, str]) -> str:
    attempt_mode = str(row.get("prepared_mode") or "fresh_full_batch")
    if attempt_mode == "narrowed_suffix_only":
        ownership_note = "- This is a narrowed recovery segment. Respect the wrapper lease check and recovery cap."
    elif attempt_mode == "continue_from_prefix":
        ownership_note = "- This is a recovery attempt with a preserved prefix. Own the remaining suffix in one fresh worker and do not proactively hand off mid-batch."
    else:
        ownership_note = "- This is the normal full-batch attempt. Own the whole batch in one fresh worker and exit after this single attempt finishes."
    return f"""Use a fresh worker subagent for exactly one part6 batch attempt. Do not reuse a finished worker context for a later attempt or a later batch. Required model: gpt-5.5, reasoning xhigh.

Startup requirement:
- Read only the batch-specific instructions and inputs first.
- Use the capability definitions in the generated instructions, `Plan.md`, and `agent_prompt_template.md` for this run. Do not rely on old results, old audit definitions, or memory from previous part6 runs.
- Process the earliest pending investor immediately and write the first classifier/result rows early.
- Do not begin with repo-wide file scans, `manifest.csv` sweeps, `verification_findings.csv` lookups, or broad exploration of other batches.
- {ownership_note}

Read the worker instructions:
{row["instructions_file"]}

Then execute the batch and write results only to:
{row["classifier_results_csv"]}
{row["results_csv"]}
"""


def build_verifier_spawn_prompt(row: dict[str, str]) -> str:
    return f"""Use a fresh verifier subagent for this part6 queue group. Required model: gpt-5.5, reasoning xhigh.

Read the verifier instructions:
{row["verifier_instructions_file"]}

Then write:
{row["verification_report_csv"]}
{row["verification_summary_md"]}

The queue group is not complete until every non-pass verifier row has a recorded recommended action.
"""


def write_rounds_markdown(path: Path, schedule_rows: list[dict[str, str]], workers: int) -> None:
    lines = [
        "# Part6 Queue Worker Schedule",
        "",
        f"- queue_workers: {workers}",
        f"- total_batches: {len(schedule_rows)}",
        f"- queue_groups: {((len(schedule_rows) - 1) // workers + 1) if schedule_rows else 0}",
        "- scheduler_mode: queue_only",
        "- required_model: gpt-5.5",
        "- required_reasoning_effort: xhigh",
        "",
        "Default entrypoint is the queue supervisor. It owns slot filling, watch, per-batch lint/collect, tail retry, and the final completion gate. Round-mode execution is disabled.",
        "",
        "Default mode is one fresh worker per batch. Recovery may create a fresh continuation worker for the unresolved suffix, but only after a failure or explicit rerun decision.",
        "",
        "Do not collect, merge, update checkpoint, or delete temporary run directories until verifier artifacts are complete and every non-pass row has a recorded action.",
        "",
        "Preferred command:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/5_run_queue_supervisor.py --runs-dir {path.parent} --final-dir part6_analyse_investor_capabilities/agent_runs/crypto_investor --start-round-index 1 --round-count <QUEUE_GROUP_COUNT> --max-workers {workers} --partial-stall-timeout-seconds 480",
        "```",
        "",
        "The supervisor blocks until the requested queue groups complete, all completed batches have collected, and the final completion gate passes.",
        "",
        "Manual recovery helpers still use `round-index` as a queue-group identifier for legacy file naming only. Do not treat it as progress:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/4_manage_round_runtime.py --runs-dir {path.parent} --round-index <ROUND_INDEX> --prepare-launches",
        "```",
        "",
        "Spawn workers from `launch_queue_round_XXXX.md`, then immediately mark that queue group as started:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/4_manage_round_runtime.py --runs-dir {path.parent} --round-index <ROUND_INDEX> --mark-round-started",
        "```",
        "",
        "While a queue group is running, use the runtime controller instead of raw watcher commands. It detects both startup no-row failures and partial stalls and writes `runtime_actions_round_XXXX.csv` with kill+respawn recommendations:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/4_manage_round_runtime.py --runs-dir {path.parent} --round-index <ROUND_INDEX> --watch-round --startup-no-row-timeout-seconds 480 --partial-stall-timeout-seconds 480",
        "```",
        "",
        "If the runtime controller emits actions, rerun `--prepare-launches` for that same round and respawn only the affected batches or recovery attempts. Each new attempt must use a fresh worker and the previous worker should be considered closed.",
        "",
        "Before starting the fresh verifier, run the local lint pass against the active attempt outputs. Any immutable identity drift must be fixed before verifier starts:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/3_collect_results.py --runs-dir {path.parent} --lint-only --repair-identity-drift-in-place --fail-on-identity-drift",
        "```",
        "",
        "If lint or the runtime controller marks any `needs_rerun` rows in `schedule.csv` or writes a rerun artifact CSV, rerun those batches with fresh workers before starting the verifier.",
        "",
        "Completion gate:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/3_collect_results.py --runs-dir {path.parent} --lint-only --repair-identity-drift-in-place --fail-on-identity-drift",
        f"python part6_analyse_investor_capabilities/scripts/10_validate_final_outputs.py --schedule-csv {path.parent / 'schedule.csv'} --final-dir part6_analyse_investor_capabilities/agent_runs/crypto_investor",
        "```",
        "",
        "After worker results are complete, collect merged results and manual-review rows:",
        "",
        "```bash",
        f"python part6_analyse_investor_capabilities/scripts/3_collect_results.py --runs-dir {path.parent} --cleanup-run-artifacts",
        "```",
        "",
    ]
    current_round = ""
    last_round_row: dict[str, str] | None = None
    for row in schedule_rows:
        if row["round_index"] != current_round:
            if last_round_row is not None:
                lines.extend(
                    [
                        f"### Round {current_round} Verifier",
                        "",
                        "```text",
                        build_verifier_spawn_prompt(last_round_row),
                        "```",
                        "",
                    ]
                )
            current_round = row["round_index"]
            lines.extend([f"## Round {current_round}", ""])
        lines.extend(
            [
                f"### Worker {row['worker_slot']} - {Path(row['batch_file']).name}",
                "",
                "```text",
                build_worker_spawn_prompt(row),
                "```",
                "",
            ]
        )
        last_round_row = row
    if last_round_row is not None:
        lines.extend(
            [
                f"### Round {current_round} Verifier",
                "",
                "```text",
                build_verifier_spawn_prompt(last_round_row),
                "```",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_schedule_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=SCHEDULE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def prepare_round_verification(
    runs_dir: Path,
    round_index: int,
    round_rows: list[dict[str, str]],
    force: bool,
) -> dict[str, str]:
    verifier_dir = runs_dir
    verification_report = runs_dir / f"verification_report_round_{round_index:04d}.csv"
    verification_summary = runs_dir / f"verification_summary_round_{round_index:04d}.md"
    verifier_instructions = runs_dir / f"verifier_instructions_round_{round_index:04d}.md"

    write_verification_header(verification_report, force=force)

    if force or not verification_summary.exists():
        verification_summary.write_text(
            "\n".join(
                [
                    f"# Round {round_index} Verification Summary",
                    "",
                    "- status: pending",
                    "- checked row count:",
                    "- pass count:",
                    "- non-pass count:",
                    "- suspected missing capability count:",
                    "- suspected extra capability count:",
                    "- wrong mapping count:",
                    "- skipped-search concern count:",
                    "- systematic causes found:",
                    "- recommended process updates:",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    if force or not verifier_instructions.exists():
        verifier_instructions.write_text(
            build_verifier_instructions(
                round_index,
                round_rows,
                verifier_dir,
                verification_report,
                verification_summary,
            ),
            encoding="utf-8",
        )

    return {
        "verifier_dir": relative_path(verifier_dir),
        "verification_report_csv": relative_path(verification_report),
        "verification_summary_md": relative_path(verification_summary),
        "verifier_instructions_file": relative_path(verifier_instructions),
    }


def prepare_run(
    batch_file: Path,
    tasks: list[dict],
    runs_dir: Path,
    round_index: int,
    worker_slot: int,
    force: bool,
) -> dict[str, str]:
    run_dir = runs_dir / batch_file.stem
    run_dir.mkdir(parents=True, exist_ok=True)

    tasks_path = run_dir / "tasks.jsonl"
    if force or not tasks_path.exists():
        shutil.copyfile(batch_file, tasks_path)

    base_instructions_file = run_dir / "base_worker_instructions.md"
    base_instruction_text = build_worker_instructions(batch_file, run_dir, tasks, round_index, worker_slot)
    base_instructions_file.write_text(base_instruction_text, encoding="utf-8")

    attempts_dir = run_dir / "attempts"
    attempts_dir.mkdir(parents=True, exist_ok=True)
    active_attempt = attempts_dir / "attempt_0001"
    active_attempt.mkdir(parents=True, exist_ok=True)
    segment_policy = load_segment_policy()
    lease_id = make_lease_id(worker_slot, 1)
    active_lease_file = active_lease_path(run_dir)

    classifier_results_csv = active_attempt / "classifier_results.csv"
    write_classifier_header(classifier_results_csv, force=force)

    results_csv = active_attempt / "results.csv"
    write_results_header(results_csv, force=force)

    instructions_file = active_attempt / "worker_instructions.md"
    metadata_file = attempt_metadata_path(active_attempt)
    write_json(
        metadata_file,
        {
            "attempt_index": 1,
            "attempt_mode": "fresh_full_batch",
            "lease_id": lease_id,
            "attempt_start_prefix_rows": 0,
            "segment_target_rows": segment_policy["target_rows_per_attempt"],
            "segment_hard_cap_rows": segment_policy["hard_cap_rows_per_attempt"],
            "updated_at": now_utc().isoformat(),
        },
    )
    write_json(
        active_lease_file,
        {
            "lease_id": lease_id,
            "attempt_index": 1,
            "active_attempt": str(active_attempt),
            "attempt_start_prefix_rows": 0,
            "segment_target_rows": segment_policy["target_rows_per_attempt"],
            "segment_hard_cap_rows": segment_policy["hard_cap_rows_per_attempt"],
            "updated_at": now_utc().isoformat(),
        },
    )
    if force or not instructions_file.exists():
        instructions_file.write_text(
            build_initial_attempt_instructions(
                base_instruction_text=base_instruction_text,
                attempt_dir=active_attempt,
                tasks_path=tasks_path,
                active_lease_file=active_lease_file,
                lease_id=lease_id,
                segment_target_rows=segment_policy["target_rows_per_attempt"],
                segment_hard_cap_rows=segment_policy["hard_cap_rows_per_attempt"],
            ),
            encoding="utf-8",
        )

    first = tasks[0]
    last = tasks[-1]
    result_rows = count_result_rows(results_csv)
    classifier_rows = count_result_rows(classifier_results_csv)
    if result_rows >= len(tasks) and classifier_rows >= len(tasks):
        status = "completed"
        prepared_mode = ""
        prepared_reason = ""
        queue_state = "ready_to_collect"
    else:
        status = "prepared"
        prepared_mode = "continue_from_prefix" if max(result_rows, classifier_rows) > 0 else "fresh_full_batch"
        prepared_reason = "initial_prepare"
        queue_state = "queued"

    failure_counts_json = json.dumps(
        {
            "startup_no_row": 0,
            "header_only_timeout": 0,
            "partial_stall": 0,
            "row_count_mismatch": 0,
            "schema_error": 0,
            "verifier_forced_rerun": 0,
            "agent_unresponsive": 0,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    return {
        "round_index": str(round_index),
        "worker_slot": str(worker_slot),
        "slot_id": "",
        "queue_order": str(batch_number(batch_file)),
        "queue_state": queue_state,
        "collect_state": "pending",
        "ready_to_collect_at": iso_now() if status == "completed" else "",
        "collected_at": "",
        "last_collected_attempt_index": "",
        "collect_failure_reason": "",
        "batch_file": relative_path(batch_file),
        "task_count": str(len(tasks)),
        "first_task_index": str(first.get("task_index", "")),
        "last_task_index": str(last.get("task_index", "")),
        "first_company": str(first.get("investor_name", "")),
        "last_company": str(last.get("investor_name", "")),
        "run_dir": relative_path(run_dir),
        "tasks_file": relative_path(tasks_path),
        "base_instructions_file": relative_path(base_instructions_file),
        "attempts_dir": relative_path(attempts_dir),
        "active_attempt": relative_path(active_attempt),
        "attempt_index": "1",
        "attempt_metadata_file": relative_path(metadata_file),
        "current_attempt_mode": "fresh_full_batch",
        "classifier_results_csv": relative_path(classifier_results_csv),
        "results_csv": relative_path(results_csv),
        "instructions_file": relative_path(instructions_file),
        "active_lease_file": relative_path(active_lease_file),
        "lease_id": lease_id,
        "attempt_start_prefix_rows": "0",
        "planned_rotate": "",
        "segment_target_rows": str(segment_policy["target_rows_per_attempt"]),
        "segment_hard_cap_rows": str(segment_policy["hard_cap_rows_per_attempt"]),
        "prepared_mode": prepared_mode,
        "prepared_reason": prepared_reason,
        "last_failure_type": "",
        "failure_counts_json": failure_counts_json,
        "consecutive_no_progress_attempts": "0",
        "status": status,
        "respawn_count": "0",
        "last_rerun_reason": "",
        "last_rerun_at": "",
        "started_at": "",
        "first_row_at": "",
        "last_progress_at": "",
        "last_seen_classifier_rows": str(classifier_rows),
        "last_seen_result_rows": str(result_rows),
        "startup_failure_count": "0",
        "stall_failure_count": "0",
        "escalation_level": "0",
    }


def main() -> None:
    args = parse_args()
    if args.workers <= 0:
        raise SystemExit("--workers must be greater than 0.")
    if args.start_batch <= 0:
        raise SystemExit("--start-batch must be greater than 0.")
    if args.limit_batches < 0:
        raise SystemExit("--limit-batches must be 0 or greater.")

    batch_dir = ensure_dir(args.batch_dir, "Batch directory")
    runs_dir = args.runs_dir.resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)

    batch_files = [
        path
        for path in sorted(batch_dir.glob("batch_*.jsonl"), key=batch_number)
        if batch_number(path) >= args.start_batch
    ]
    if args.limit_batches:
        batch_files = batch_files[: args.limit_batches]
    if not batch_files:
        raise SystemExit("No batch files selected.")

    schedule_rows: list[dict[str, str]] = []
    for index, batch_file in enumerate(batch_files):
        tasks = load_tasks(batch_file)
        if not tasks:
            raise SystemExit(f"Batch file has no tasks: {batch_file}")
        round_index = index // args.workers + 1
        worker_slot = index % args.workers + 1
        schedule_rows.append(
            prepare_run(
                batch_file=batch_file.resolve(),
                tasks=tasks,
                runs_dir=runs_dir,
                round_index=round_index,
                worker_slot=worker_slot,
                force=args.force,
            )
        )

    rows_by_round: dict[int, list[dict[str, str]]] = {}
    for row in schedule_rows:
        rows_by_round.setdefault(int(row["round_index"]), []).append(row)

    for round_index, round_rows in rows_by_round.items():
        verifier_paths = prepare_round_verification(
            runs_dir=runs_dir,
            round_index=round_index,
            round_rows=round_rows,
            force=args.force,
        )
        for row in round_rows:
            row.update(verifier_paths)

    schedule_csv = runs_dir / "schedule.csv"
    rounds_md = runs_dir / "schedule_rounds.md"
    write_schedule_csv(schedule_csv, schedule_rows)
    write_rounds_markdown(rounds_md, schedule_rows, args.workers)

    print(f"Batch directory: {batch_dir}")
    print(f"Runs directory: {runs_dir}")
    print(f"Workers per round: {args.workers}")
    print(f"Batches scheduled: {len(schedule_rows)}")
    print(f"Rounds: {(len(schedule_rows) - 1) // args.workers + 1}")
    print(f"Schedule CSV: {schedule_csv}")
    print(f"Schedule markdown: {rounds_md}")


if __name__ == "__main__":
    main()
