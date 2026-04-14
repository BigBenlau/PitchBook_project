#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART4_DIR = SCRIPT_DIR.parent
REPO_ROOT = PART4_DIR.parent

DEFAULT_MANIFEST = PART4_DIR / "input" / "batch_manifest.csv"
DEFAULT_TOKEN_MASTER = PART4_DIR / "output" / "token_master.csv"
DEFAULT_RUNS_DIR = PART4_DIR / "agent_runs" / "token_company_parallel"
DEFAULT_WORKERS = 5

RESULT_COLUMNS = [
    "token_id",
    "token_name",
    "token_symbol",
    "coingecko_slug",
    "cmc_slug",
    "token_href",
    "official_website",
    "token_type",
    "founder_people",
    "founder_status",
    "founder_evidence_spans",
    "related_companies",
    "related_company_status",
    "related_company_evidence_spans",
    "foundation_or_orgs",
    "foundation_status",
    "foundation_evidence_spans",
    "source_urls",
    "source_labels",
    "confidence",
    "needs_manual_review",
    "notes",
    "status",
]

VERIFICATION_COLUMNS = [
    "token_id",
    "token_name",
    "worker_founder_status",
    "worker_related_company_status",
    "worker_foundation_status",
    "verifier_founder_status",
    "verifier_related_company_status",
    "verifier_foundation_status",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_notes",
    "recommended_action",
    "corrected_result_row_json",
]

SCHEDULE_COLUMNS = [
    "round_index",
    "worker_slot",
    "batch_id",
    "batch_file",
    "task_count",
    "start_row",
    "end_row",
    "start_token_id",
    "end_token_id",
    "run_dir",
    "token_master_csv",
    "prepared_batch_csv",
    "official_evidence_csv",
    "entity_sentences_csv",
    "token_entity_results_csv",
    "layer3_packet_jsonl",
    "instructions_file",
    "verifier_dir",
    "verification_report_csv",
    "verification_summary_md",
    "verifier_instructions_file",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Part4 batch worker run directories under the new token_id-based harness."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--token-master-csv", type=Path, default=DEFAULT_TOKEN_MASTER)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--start-batch", type=int, default=1)
    parser.add_argument("--limit-batches", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def ensure_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise SystemExit(f"{label} does not exist: {resolved}")
    if not resolved.is_file():
        raise SystemExit(f"{label} is not a file: {resolved}")
    return resolved


def relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(resolved)


def batch_number(batch_id: str) -> int:
    try:
        return int(batch_id.split("_", 1)[1])
    except (IndexError, ValueError):
        raise SystemExit(f"Unexpected batch_id: {batch_id}") from None


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        rows = list(csv.DictReader(infile))
    if not rows:
        raise SystemExit(f"Manifest has no rows: {path}")
    return rows


def write_header(path: Path, fieldnames: list[str], force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(fieldnames)


def copy_batch_input(batch_path: Path, destination: Path, force: bool) -> None:
    if destination.exists() and not force:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(batch_path, destination)


def batch_tokens(batch_path: Path) -> tuple[str, str]:
    with batch_path.open("r", encoding="utf-8-sig", newline="") as infile:
        rows = list(csv.DictReader(infile))
    if not rows:
        return "", ""
    return (
        str(rows[0].get("token_name") or "").strip(),
        str(rows[-1].get("token_name") or "").strip(),
    )


def build_worker_instructions(run_dir: Path, batch_id: str, task_count: int, first_token: str, last_token: str) -> str:
    prompt_path = PART4_DIR / "scripts" / "4_founder_company_prompt.txt"
    return f"""# Part4 Worker Run

You are processing `{batch_id}` in the Part4 token-to-company harness.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Exclusive write scope:
- {run_dir}

Read first:
- {PART4_DIR / "Plan.md"}
- {PART4_DIR / "pipeline.md"}
- {prompt_path}
- {run_dir / "prepared_batch.csv"}

Task range:
- batch_id: {batch_id}
- task_count: {task_count}
- first_token: {first_token or "-"}
- last_token: {last_token or "-"}

Required workflow:
1. Treat `prepared_batch.csv` as the immutable source of truth. Each token is keyed by `token_id`.
2. Collect official/company evidence into `official_evidence.csv` before using CG/CMC founder text.
3. Build target-aware evidence sentences into `entity_sentences.csv`.
4. Produce exactly one row per input token in `token_entity_results.csv`.
5. Evaluate all three targets for every token:
   - `founder_people` + `founder_status`
   - `related_companies` + `related_company_status`
   - `foundation_or_orgs` + `foundation_status`
6. Allowed field statuses: `supported`, `unresolved`, `not_applicable`.
7. If any target remains unresolved, keep the row in `token_entity_results.csv`, set `status=pending_layer3`, and add the token to `layer3_packet.jsonl`.
8. Spawn a fresh verifier and produce `verification_report.csv` and `verification_summary.md`.

Hard rules:
- No token may be dropped because evidence sentences are thin or absent.
- Official/company evidence has priority for `related_companies` and `foundation_or_orgs`.
- CG/CMC founder text is supplemental, not the first authority for company/foundation claims.
- `needs_manual_review` must be `0` or `1`.
- `confidence` must be one of `high`, `medium`, `low`.
- `status` must be `completed` or `pending_layer3`.
- `founder_people`, `related_companies`, `foundation_or_orgs`, `*_evidence_spans`, `source_urls`, `source_labels` must be valid JSON arrays.
"""


def build_verifier_instructions(run_dir: Path, batch_id: str) -> str:
    return f"""# Part4 Verifier Run

You are the fresh verifier for `{batch_id}` in the Part4 token-to-company harness.

Read:
- {PART4_DIR / "Plan.md"}
- {PART4_DIR / "pipeline.md"}
- {run_dir / "prepared_batch.csv"}
- {run_dir / "official_evidence.csv"}
- {run_dir / "entity_sentences.csv"}
- {run_dir / "token_entity_results.csv"}

Verifier responsibilities:
- confirm every `token_id` in `prepared_batch.csv` has exactly one result row
- check whether `token_type` routing is reasonable
- check whether `related_company_status` and `foundation_status` were derived from official/company evidence first
- detect tokens that should have escalated to Layer 3
- emit authoritative row corrections when the worker row is wrong

Required CSV header for `verification_report.csv`:
{",".join(VERIFICATION_COLUMNS)}

If `recommended_action = edit_row`, `corrected_result_row_json` must contain a full replacement row using the result schema.
"""


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1.")

    manifest_path = ensure_file(args.manifest, "Batch manifest")
    token_master_csv = ensure_file(args.token_master_csv, "Token master CSV")
    runs_dir = args.runs_dir.resolve()
    runs_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = load_manifest(manifest_path)
    selected_rows = [
        row
        for row in manifest_rows
        if batch_number(str(row.get("batch_id") or "").strip()) >= args.start_batch
    ]
    if args.limit_batches > 0:
        selected_rows = selected_rows[: args.limit_batches]
    if not selected_rows:
        raise SystemExit("No batches selected.")

    schedule_rows: list[dict[str, str]] = []
    for index, row in enumerate(selected_rows):
        batch_id = str(row.get("batch_id") or "").strip()
        batch_path = ensure_file(REPO_ROOT / str(row.get("batch_path") or "").strip(), f"Batch CSV for {batch_id}")
        task_count = int(str(row.get("row_count") or "0").strip() or 0)
        round_index = index // args.workers + 1
        worker_slot = index % args.workers + 1

        run_dir = runs_dir / batch_id
        verifier_dir = run_dir / "verification"
        prepared_batch_csv = run_dir / "prepared_batch.csv"
        official_evidence_csv = run_dir / "official_evidence.csv"
        entity_sentences_csv = run_dir / "entity_sentences.csv"
        token_entity_results_csv = run_dir / "token_entity_results.csv"
        layer3_packet_jsonl = run_dir / "layer3_packet.jsonl"
        instructions_file = run_dir / "instructions.md"
        verification_report_csv = verifier_dir / "verification_report.csv"
        verification_summary_md = verifier_dir / "verification_summary.md"
        verifier_instructions_file = verifier_dir / "verifier_instructions.md"

        run_dir.mkdir(parents=True, exist_ok=True)
        verifier_dir.mkdir(parents=True, exist_ok=True)
        copy_batch_input(batch_path, prepared_batch_csv, force=args.force)
        write_header(token_entity_results_csv, RESULT_COLUMNS, args.force)
        write_header(verification_report_csv, VERIFICATION_COLUMNS, args.force)

        first_token, last_token = batch_tokens(batch_path)
        instructions_file.write_text(
            build_worker_instructions(run_dir, batch_id, task_count, first_token, last_token),
            encoding="utf-8",
        )
        verifier_instructions_file.write_text(
            build_verifier_instructions(run_dir, batch_id),
            encoding="utf-8",
        )

        schedule_rows.append(
            {
                "round_index": str(round_index),
                "worker_slot": str(worker_slot),
                "batch_id": batch_id,
                "batch_file": relative_path(batch_path),
                "task_count": str(task_count),
                "start_row": str(row.get("start_row") or ""),
                "end_row": str(row.get("end_row") or ""),
                "start_token_id": str(row.get("start_token_id") or ""),
                "end_token_id": str(row.get("end_token_id") or ""),
                "run_dir": relative_path(run_dir),
                "token_master_csv": relative_path(token_master_csv),
                "prepared_batch_csv": relative_path(prepared_batch_csv),
                "official_evidence_csv": relative_path(official_evidence_csv),
                "entity_sentences_csv": relative_path(entity_sentences_csv),
                "token_entity_results_csv": relative_path(token_entity_results_csv),
                "layer3_packet_jsonl": relative_path(layer3_packet_jsonl),
                "instructions_file": relative_path(instructions_file),
                "verifier_dir": relative_path(verifier_dir),
                "verification_report_csv": relative_path(verification_report_csv),
                "verification_summary_md": relative_path(verification_summary_md),
                "verifier_instructions_file": relative_path(verifier_instructions_file),
                "status": "pending",
            }
        )

    schedule_csv = runs_dir / "schedule.csv"
    with schedule_csv.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=SCHEDULE_COLUMNS)
        writer.writeheader()
        writer.writerows(schedule_rows)

    print(f"Prepared {len(schedule_rows)} batch worker runs.", flush=True)
    print(f"Runs directory: {runs_dir}", flush=True)
    print(f"Schedule CSV: {schedule_csv}", flush=True)


if __name__ == "__main__":
    main()
