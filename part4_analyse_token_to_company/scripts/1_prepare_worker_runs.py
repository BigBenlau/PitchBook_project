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
DEFAULT_RUNS_DIR = PART4_DIR / "agent_runs" / "token_company_parallel"
DEFAULT_WORKERS = 5

EXTRACTED_CSV_COLUMNS = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "confidence",
    "evidence_spans",
    "notes",
    "status",
    "error",
]

VALIDATED_CSV_COLUMNS = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "confidence",
    "evidence_spans",
    "notes",
    "status",
    "error",
    "source_labels",
    "cmc_match_methods",
    "sentence_risk_flags",
    "validation_issues",
    "suggested_confidence_cap",
    "needs_manual_review",
]

REVIEW_QUEUE_COLUMNS = [
    "row_index",
    "token_name",
    "token_symbol",
    "token_href",
    "slug",
    "confidence",
    "review_priority",
    "review_reason",
    "source_labels",
    "cmc_match_methods",
    "sentence_risk_flags",
    "validation_issues",
    "founder_people",
    "related_companies",
    "foundation_or_orgs",
    "evidence_spans",
    "notes",
]

VERIFICATION_CSV_COLUMNS = [
    "row_index",
    "token_name",
    "worker_founder_people",
    "worker_related_companies",
    "worker_foundation_or_orgs",
    "verifier_founder_people",
    "verifier_related_companies",
    "verifier_foundation_or_orgs",
    "verdict",
    "error_type",
    "error_reason",
    "evidence_notes",
    "recommended_action",
]

SCHEDULE_COLUMNS = [
    "round_index",
    "worker_slot",
    "batch_id",
    "batch_file",
    "task_count",
    "start_row",
    "end_row",
    "first_token",
    "last_token",
    "run_dir",
    "merged_input_csv",
    "official_evidence_csv",
    "token_evidence_sentences_csv",
    "founder_company_tasks_jsonl",
    "codex_batch_dir",
    "extracted_results_csv",
    "validated_results_csv",
    "review_queue_csv",
    "agent_packet_jsonl",
    "instructions_file",
    "verifier_dir",
    "verification_report_csv",
    "verification_summary_md",
    "verifier_instructions_file",
    "status",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Part4 batch worker run directories with harness schedule and verifier slots.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
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
        reader = csv.DictReader(infile)
        rows = list(reader)
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
    return f"""# Part4 Worker Run

You are processing `{batch_id}` in the Part4 token-to-company harness.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Exclusive write scope:
- {run_dir}

Read first:
- {PART4_DIR / "Plan.md"}
- {PART4_DIR / "pipeline.md"}
- {PART4_DIR / "4_founder_company_prompt.txt"}
- {run_dir / "merged_input.csv"}

Task range:
- batch_id: {batch_id}
- task_count: {task_count}
- first_token: {first_token or "-"}
- last_token: {last_token or "-"}

Required workflow:
1. Run Layer 2 official evidence collection into `official_evidence.csv`.
2. Run candidate sentence filtering into `token_evidence_sentences.csv`.
3. Run extraction task building into `founder_company_tasks.jsonl` and `codex_batches/`.
4. Complete `founder_company_extracted.csv` with exactly one row per input row.
5. Run validation into `founder_company_validated.csv`.
6. Run review queue build into `founder_company_review_queue.csv`.
7. If unresolved rows remain, write `agent_packet.jsonl` for Layer 3 fallback.
8. Spawn a fresh verifier and produce `verification_report.csv` and `verification_summary.md`.

Worker output rules:
- Keep JSON arrays valid in `founder_people`, `related_companies`, `foundation_or_orgs`, and `evidence_spans`.
- Use only explicit source evidence from CG, CMC, and collected official paragraphs.
- `confidence` must be one of `high`, `medium`, `low`.
- `status` should be `completed` for finished rows or `pending_agent` when fallback is still required.
- Do not leave missing rows. Every input row must have a corresponding result row.
"""


def build_verifier_instructions(run_dir: Path, batch_id: str) -> str:
    return f"""# Part4 Verifier Run

You are the fresh verifier for `{batch_id}` in the Part4 token-to-company harness.

Read:
- {PART4_DIR / "Plan.md"}
- {PART4_DIR / "pipeline.md"}
- {run_dir / "merged_input.csv"}
- {run_dir / "token_evidence_sentences.csv"}
- {run_dir / "founder_company_validated.csv"}
- {run_dir / "founder_company_review_queue.csv"}

Verifier goals:
- detect missing founders / related companies / orgs
- detect over-reported entities
- detect wrong entity typing
- flag weak-evidence rows that should remain in review
- flag rows that should escalate to Layer 3 fallback

Required CSV header for `verification_report.csv`:
{",".join(VERIFICATION_CSV_COLUMNS)}
"""


def main() -> None:
    args = parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be at least 1.")

    manifest_path = ensure_file(args.manifest, "Batch manifest")
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
        batch_path = ensure_file(Path(str(row.get("batch_path") or "").strip()), f"Batch CSV for {batch_id}")
        task_count = int(str(row.get("row_count") or "0").strip() or 0)
        round_index = index // args.workers + 1
        worker_slot = index % args.workers + 1

        run_dir = runs_dir / batch_id
        verifier_dir = run_dir / "verification"
        merged_input_csv = run_dir / "merged_input.csv"
        official_evidence_csv = run_dir / "official_evidence.csv"
        token_evidence_sentences_csv = run_dir / "token_evidence_sentences.csv"
        founder_company_tasks_jsonl = run_dir / "founder_company_tasks.jsonl"
        codex_batch_dir = run_dir / "codex_batches"
        extracted_results_csv = run_dir / "founder_company_extracted.csv"
        validated_results_csv = run_dir / "founder_company_validated.csv"
        review_queue_csv = run_dir / "founder_company_review_queue.csv"
        agent_packet_jsonl = run_dir / "agent_packet.jsonl"
        instructions_file = run_dir / "instructions.md"
        verification_report_csv = verifier_dir / "verification_report.csv"
        verification_summary_md = verifier_dir / "verification_summary.md"
        verifier_instructions_file = verifier_dir / "verifier_instructions.md"

        run_dir.mkdir(parents=True, exist_ok=True)
        verifier_dir.mkdir(parents=True, exist_ok=True)
        copy_batch_input(batch_path, merged_input_csv, force=args.force)
        write_header(extracted_results_csv, EXTRACTED_CSV_COLUMNS, args.force)
        write_header(validated_results_csv, VALIDATED_CSV_COLUMNS, args.force)
        write_header(review_queue_csv, REVIEW_QUEUE_COLUMNS, args.force)
        write_header(verification_report_csv, VERIFICATION_CSV_COLUMNS, args.force)

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
                "first_token": first_token,
                "last_token": last_token,
                "run_dir": relative_path(run_dir),
                "merged_input_csv": relative_path(merged_input_csv),
                "official_evidence_csv": relative_path(official_evidence_csv),
                "token_evidence_sentences_csv": relative_path(token_evidence_sentences_csv),
                "founder_company_tasks_jsonl": relative_path(founder_company_tasks_jsonl),
                "codex_batch_dir": relative_path(codex_batch_dir),
                "extracted_results_csv": relative_path(extracted_results_csv),
                "validated_results_csv": relative_path(validated_results_csv),
                "review_queue_csv": relative_path(review_queue_csv),
                "agent_packet_jsonl": relative_path(agent_packet_jsonl),
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
