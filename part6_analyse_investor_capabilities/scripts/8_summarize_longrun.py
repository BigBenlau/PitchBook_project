#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PART6_DIR = SCRIPT_DIR.parent
DEFAULT_LATEST_JOB_JSON = PART6_DIR / "agent_runs" / "crypto_investor_longrun_latest.json"
CAPABILITY_FLAG_COLUMNS = [
    "otc_trading",
    "algorithm_trading",
    "market_making",
    "execution_services",
    "defi",
    "sub_fund",
]
OUTPUT_COLUMNS = [
    "batch_file",
    "round_index",
    "status",
    "queue_state",
    "collect_state",
    "task_count",
    "classifier_rows",
    "result_rows",
    "ticker_count",
    "ticker_metric",
    "rows_with_capability_labels",
    "manual_confirm_count",
    "invalid_schema_count",
    "missing_result_rows",
    "missing_classifier_rows",
    "duplicate_result_task_indexes",
    "duplicate_classifier_task_indexes",
    "batch_runtime_seconds",
    "last_failure_type",
    "respawn_count",
    "tail_retry_count",
    "anomalies",
    "optimization_notes",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize a part6 longrun by batch. In the current part6 schema there is no "
            "ticker column; ticker_count therefore falls back to capability label assignment count."
        )
    )
    parser.add_argument("--latest-job-json", type=Path, default=DEFAULT_LATEST_JOB_JSON)
    parser.add_argument("--runs-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def parse_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes}m {secs}s"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))


def parse_json_list(value: str) -> tuple[list[Any], bool]:
    raw = str(value or "").strip()
    if not raw:
        return [], False
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [], True
    if isinstance(parsed, list):
        return parsed, False
    return [], True


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "1", "manual_confirm"}


def count_duplicates(values: list[str]) -> int:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return len(duplicates)


def effective_status(row: dict[str, str]) -> str:
    status = str(row.get("status") or "").strip()
    if status:
        return status
    if str(row.get("completion_mode") or "").strip() == "deferred_long_tail":
        return "deferred_long_tail"
    return "unknown"


def batch_duration_seconds(row: dict[str, str], now: datetime) -> int | None:
    started = parse_dt(row.get("started_at"))
    if started is None:
        return None
    end = (
        parse_dt(row.get("collected_at"))
        or parse_dt(row.get("deferred_at"))
        or parse_dt(row.get("last_progress_at"))
    )
    if end is None and effective_status(row) in {"running", "prepared"}:
        end = now
    if end is None:
        return None
    return int((end - started).total_seconds())


def summarize_batch(row: dict[str, str], now: datetime) -> dict[str, str]:
    task_count = int(str(row.get("task_count") or "0") or "0")
    classifier_rows = read_csv_rows(Path(row.get("classifier_results_csv") or ""))
    result_rows = read_csv_rows(Path(row.get("results_csv") or ""))
    result_task_indexes = [str(item.get("task_index") or "").strip() for item in result_rows]
    classifier_task_indexes = [str(item.get("task_index") or "").strip() for item in classifier_rows]

    ticker_values = [
        str(item.get("ticker") or "").strip()
        for item in result_rows
        if str(item.get("ticker") or "").strip()
    ]
    ticker_metric = "ticker_column"
    ticker_count = len(ticker_values)
    capability_label_assignments = 0
    rows_with_capability_labels = 0
    invalid_schema_count = 0
    manual_confirm_count = 0

    for item in result_rows:
        labels, labels_invalid = parse_json_list(str(item.get("capability_labels") or ""))
        _, other_flags_invalid = parse_json_list(str(item.get("other_flags") or ""))
        evidence_urls = str(item.get("evidence_urls") or "").strip()
        evidence_types = str(item.get("evidence_source_types") or "").strip()
        if labels_invalid or other_flags_invalid:
            invalid_schema_count += 1
        flagged_labels: list[str] = []
        for flag in CAPABILITY_FLAG_COLUMNS:
            value = str(item.get(flag) or "").strip().lower()
            if value and value not in {"yes", "no"}:
                invalid_schema_count += 1
                break
            if value == "yes":
                flagged_labels.append(flag)
        if sorted(str(label) for label in labels) != sorted(flagged_labels):
            invalid_schema_count += 1
        capability_label_assignments += len(labels)
        if labels:
            rows_with_capability_labels += 1
            if not evidence_urls and not evidence_types:
                invalid_schema_count += 1
        if truthy(str(item.get("needs_manual_review") or "")):
            manual_confirm_count += 1

    if ticker_count == 0:
        ticker_metric = "capability_label_assignments"
        ticker_count = capability_label_assignments

    duplicate_result_task_indexes = count_duplicates(result_task_indexes)
    duplicate_classifier_task_indexes = count_duplicates(classifier_task_indexes)
    missing_result_rows = max(0, task_count - len(result_rows))
    missing_classifier_rows = max(0, task_count - len(classifier_rows))

    anomalies: list[str] = []
    status = effective_status(row)
    collect_state = str(row.get("collect_state") or "").strip()
    queue_state = str(row.get("queue_state") or "").strip()
    if status not in {"completed", "deferred_long_tail"}:
        anomalies.append(f"not_resolved:{status}")
    if missing_result_rows:
        anomalies.append(f"missing_result_rows:{missing_result_rows}")
    if missing_classifier_rows:
        anomalies.append(f"missing_classifier_rows:{missing_classifier_rows}")
    if len(result_rows) != len(classifier_rows):
        anomalies.append("classifier_result_row_count_mismatch")
    if duplicate_result_task_indexes:
        anomalies.append(f"duplicate_result_task_indexes:{duplicate_result_task_indexes}")
    if duplicate_classifier_task_indexes:
        anomalies.append(f"duplicate_classifier_task_indexes:{duplicate_classifier_task_indexes}")
    if invalid_schema_count:
        anomalies.append(f"invalid_schema_rows:{invalid_schema_count}")
    if status == "completed" and collect_state not in {"done", "skipped"}:
        anomalies.append(f"collect_not_done:{collect_state or 'blank'}")
    last_failure_type = str(row.get("last_failure_type") or "").strip()
    if last_failure_type:
        anomalies.append(f"last_failure_type:{last_failure_type}")
    deferred_reason = str(row.get("deferred_reason") or "").strip()
    if deferred_reason:
        anomalies.append(f"deferred_reason:{deferred_reason}")

    optimization_notes: list[str] = []
    if status == "running" and not result_rows:
        optimization_notes.append("watch startup/no-row timeout")
    if missing_result_rows or missing_classifier_rows:
        optimization_notes.append("rerun or continue incomplete attempt")
    if manual_confirm_count:
        optimization_notes.append("review manual-confirm rows and refine evidence rules")
    if invalid_schema_count:
        optimization_notes.append("tighten schema validation before marking completed")
    if int(str(row.get("respawn_count") or "0") or "0") > 0:
        optimization_notes.append("review respawn failure pattern")
    if str(row.get("completion_mode") or "").strip() == "deferred_long_tail":
        optimization_notes.append("split long-tail batch or lower per-attempt scope")
    if not optimization_notes and status == "completed":
        optimization_notes.append("none")

    duration = batch_duration_seconds(row, now)
    return {
        "batch_file": Path(row.get("batch_file") or "").name,
        "round_index": str(row.get("round_index") or ""),
        "status": status,
        "queue_state": queue_state,
        "collect_state": collect_state,
        "task_count": str(task_count),
        "classifier_rows": str(len(classifier_rows)),
        "result_rows": str(len(result_rows)),
        "ticker_count": str(ticker_count),
        "ticker_metric": ticker_metric,
        "rows_with_capability_labels": str(rows_with_capability_labels),
        "manual_confirm_count": str(manual_confirm_count),
        "invalid_schema_count": str(invalid_schema_count),
        "missing_result_rows": str(missing_result_rows),
        "missing_classifier_rows": str(missing_classifier_rows),
        "duplicate_result_task_indexes": str(duplicate_result_task_indexes),
        "duplicate_classifier_task_indexes": str(duplicate_classifier_task_indexes),
        "batch_runtime_seconds": "" if duration is None else str(duration),
        "last_failure_type": last_failure_type,
        "respawn_count": str(row.get("respawn_count") or "0"),
        "tail_retry_count": str(row.get("tail_retry_count") or "0"),
        "anomalies": "; ".join(anomalies),
        "optimization_notes": "; ".join(optimization_notes),
    }


def write_summary_md(
    path: Path,
    *,
    run_dir: Path,
    job: dict[str, Any],
    state: dict[str, Any],
    rows: list[dict[str, str]],
    summary_rows: list[dict[str, str]],
    now: datetime,
) -> None:
    launched = parse_dt(job.get("launched_at"))
    completed_at = parse_dt(state.get("completed_at")) or parse_dt(state.get("updated_at"))
    all_done = all(item["status"] in {"completed", "deferred_long_tail"} for item in summary_rows)
    runtime_end = completed_at if all_done and completed_at is not None else now
    elapsed = int((runtime_end - launched).total_seconds()) if launched else None
    status_counts = {
        status: sum(1 for item in summary_rows if item["status"] == status)
        for status in sorted({item["status"] for item in summary_rows})
    }
    total_result_rows = sum(int(item["result_rows"]) for item in summary_rows)
    total_classifier_rows = sum(int(item["classifier_rows"]) for item in summary_rows)
    total_ticker_count = sum(int(item["ticker_count"]) for item in summary_rows)
    total_manual = sum(int(item["manual_confirm_count"]) for item in summary_rows)
    total_anomaly_batches = sum(1 for item in summary_rows if item["anomalies"])

    lines = [
        "# Part6 Longrun Summary",
        "",
        f"- run_dir: {run_dir}",
        f"- launched_at: {job.get('launched_at') or ''}",
        f"- state_updated_at: {state.get('updated_at') or ''}",
        f"- complete: {'yes' if all_done else 'no'}",
        f"- elapsed: {fmt_duration(elapsed)}",
        f"- scheduled_batches: {len(rows)}",
        f"- status_counts: {json.dumps(status_counts, sort_keys=True)}",
        f"- classifier_rows: {total_classifier_rows}",
        f"- result_rows: {total_result_rows}",
        "- ticker_count: uses ticker column when present; otherwise uses capability label assignment count.",
        f"- ticker_count_total: {total_ticker_count}",
        f"- manual_confirm_total: {total_manual}",
        f"- anomaly_batches: {total_anomaly_batches}",
        "",
        "## Batch Summary",
        "",
        "| batch | status | rows | ticker_count | manual_confirm | anomalies | optimization_notes |",
        "| --- | --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in summary_rows:
        rows_text = f"{item['result_rows']}/{item['task_count']}"
        anomalies = item["anomalies"] or ""
        notes = item["optimization_notes"] or ""
        lines.append(
            "| "
            + " | ".join(
                [
                    item["batch_file"],
                    item["status"],
                    rows_text,
                    item["ticker_count"],
                    item["manual_confirm_count"],
                    anomalies.replace("|", "/"),
                    notes.replace("|", "/"),
                ]
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    job = load_json(args.latest_job_json.resolve())
    if args.runs_dir is not None:
        run_dir = args.runs_dir.resolve()
    elif job.get("runs_dir"):
        run_dir = Path(str(job["runs_dir"])).resolve()
    else:
        raise SystemExit("Unable to resolve runs_dir.")

    schedule_path = run_dir / "schedule.csv"
    rows = read_csv_rows(schedule_path)
    if not rows:
        raise SystemExit(f"Schedule has no rows: {schedule_path}")
    state = load_json(run_dir / "supervisor_state.json")
    now = datetime.now(timezone.utc)
    summary_rows = [summarize_batch(row, now) for row in rows]

    output_dir = (args.output_dir.resolve() if args.output_dir else run_dir)
    csv_path = output_dir / "longrun_batch_summary.csv"
    md_path = output_dir / "longrun_summary.md"
    if not args.no_write:
        output_dir.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(summary_rows)
        write_summary_md(
            md_path,
            run_dir=run_dir,
            job=job,
            state=state,
            rows=rows,
            summary_rows=summary_rows,
            now=now,
        )

    launched = parse_dt(job.get("launched_at"))
    elapsed = int((now - launched).total_seconds()) if launched else None
    status_counts = {
        status: sum(1 for item in summary_rows if item["status"] == status)
        for status in sorted({item["status"] for item in summary_rows})
    }
    print(f"runs_dir: {run_dir}")
    print(f"status_counts: {json.dumps(status_counts, sort_keys=True)}")
    print(f"elapsed_so_far: {fmt_duration(elapsed)}")
    print(f"result_rows: {sum(int(item['result_rows']) for item in summary_rows)}")
    print(f"ticker_count_total: {sum(int(item['ticker_count']) for item in summary_rows)}")
    print(f"manual_confirm_total: {sum(int(item['manual_confirm_count']) for item in summary_rows)}")
    print(f"anomaly_batches: {sum(1 for item in summary_rows if item['anomalies'])}")
    if not args.no_write:
        print(f"batch_summary_csv: {csv_path}")
        print(f"summary_md: {md_path}")


if __name__ == "__main__":
    main()
