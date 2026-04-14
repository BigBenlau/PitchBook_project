#!/usr/bin/env python3
"""
Run the current 3-layer sample pipeline with persisted intermediate files.

This runner is sample-oriented: it uses existing manual extraction results when
available, and marks rows without extraction output as pending agent fallback.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
INPUT_DIR = PROJECT_DIR / "input"
TMP_DIR = PROJECT_DIR / "tmp"
OUTPUT_DIR = PROJECT_DIR / "output"
FULL_INPUT = TMP_DIR / "full" / "coingecko_about_with_cmc_about.csv"
BATCH_DIR = INPUT_DIR / "batches"
MANIFEST = INPUT_DIR / "batch_manifest.csv"
EXISTING_RESULT_FILES = [
    OUTPUT_DIR / "batch_results" / "batch_0001_results.csv",
    OUTPUT_DIR / "batch_results" / "batch_0002_results.csv",
]
CONSOLIDATED_RESULTS = OUTPUT_DIR / "final" / "founder_company_extracted_sample.csv"
VALIDATED_RESULTS = OUTPUT_DIR / "final" / "founder_company_validated_sample.csv"
REVIEW_QUEUE = OUTPUT_DIR / "final" / "founder_company_review_queue_sample.csv"
AGENT_PACKET = OUTPUT_DIR / "agent_packets" / "sample_pending_agent.jsonl"
RESULT_FIELDNAMES = [
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


def run_command(args: list[str]) -> None:
    subprocess.run(args, check=True, cwd=PROJECT_DIR.parent)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as infile:
        return list(csv.DictReader(infile))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prepare_batch_tmp_dirs() -> None:
    manifest_rows = read_csv(MANIFEST)
    for manifest_row in manifest_rows:
        batch_id = str(manifest_row.get("batch_id") or "").strip()
        batch_path = Path(str(manifest_row.get("batch_path") or "").strip())
        if not batch_id or not batch_path.is_file():
            continue
        batch_tmp = TMP_DIR / batch_id
        batch_output = OUTPUT_DIR / "batch_results" / batch_id
        batch_tmp.mkdir(parents=True, exist_ok=True)
        batch_output.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(batch_path, batch_tmp / "merged_input.csv")


def run_layer2_official_for_batches() -> None:
    manifest_rows = read_csv(MANIFEST)
    for manifest_row in manifest_rows:
        batch_id = str(manifest_row.get("batch_id") or "").strip()
        if not batch_id:
            continue
        batch_tmp = TMP_DIR / batch_id
        run_command(
            [
                "python3",
                "part4_analyse_token_to_company/2_layer2_official_evidence/1_collect_official_evidence.py",
                "--input-csv",
                str(batch_tmp / "merged_input.csv"),
                "--output-csv",
                str(batch_tmp / "official_evidence.csv"),
                "--max-pages",
                "1",
                "--max-paragraphs",
                "3",
            ]
        )


def run_layer1_for_batches() -> None:
    manifest_rows = read_csv(MANIFEST)
    for manifest_row in manifest_rows:
        batch_id = str(manifest_row.get("batch_id") or "").strip()
        if not batch_id:
            continue
        batch_tmp = TMP_DIR / batch_id
        run_command(
            [
                "python3",
                "part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/2_filter_candidate_sentences.py",
                "--merged-csv",
                str(batch_tmp / "merged_input.csv"),
                "--official-evidence-csv",
                str(batch_tmp / "official_evidence.csv"),
                "--output-csv",
                str(batch_tmp / "token_evidence_sentences.csv"),
            ]
        )
        run_command(
            [
                "python3",
                "part4_analyse_token_to_company/1_layer1_cg_cmc_baseline/3_extract_founder_companies.py",
                "--input-csv",
                str(batch_tmp / "token_evidence_sentences.csv"),
                "--tasks-jsonl",
                str(batch_tmp / "founder_company_tasks.jsonl"),
                "--batch-dir",
                str(batch_tmp / "codex_batches"),
                "--result-template",
                str(batch_tmp / "founder_company_extracted.csv"),
                "--batch-size",
                "10",
            ]
        )


def load_existing_results() -> dict[str, dict[str, str]]:
    by_row_index: dict[str, dict[str, str]] = {}
    for path in EXISTING_RESULT_FILES:
        for row in read_csv(path):
            row_index = str(row.get("row_index") or "").strip()
            if row_index:
                by_row_index[row_index] = row
    return by_row_index


def build_placeholder(row_index: int, row: dict[str, str]) -> dict[str, str]:
    return {
        "row_index": str(row_index),
        "token_name": str(row.get("token_name") or "").strip(),
        "token_symbol": str(row.get("token_symbol") or "").strip(),
        "token_href": str(row.get("token_href") or "").strip(),
        "slug": str(row.get("slug") or "").strip(),
        "founder_people": "[]",
        "related_companies": "[]",
        "foundation_or_orgs": "[]",
        "confidence": "low",
        "evidence_spans": "[]",
        "notes": "No extraction result exists for this sample row; requires agent fallback or manual review.",
        "status": "pending_agent",
        "error": "",
    }


def consolidate_results() -> None:
    merged_rows = read_csv(FULL_INPUT)
    existing_results = load_existing_results()
    output_rows: list[dict[str, str]] = []
    pending_packets: list[dict[str, object]] = []

    for row_index, row in enumerate(merged_rows, start=1):
        row_key = str(row_index)
        if row_key in existing_results:
            output_rows.append({field: str(existing_results[row_key].get(field) or "") for field in RESULT_FIELDNAMES})
            continue
        placeholder = build_placeholder(row_index, row)
        output_rows.append(placeholder)
        pending_packets.append(
            {
                "row_index": row_index,
                "token_name": placeholder["token_name"],
                "token_symbol": placeholder["token_symbol"],
                "token_href": placeholder["token_href"],
                "slug": placeholder["slug"],
                "reason": "missing_extraction_result_in_sample_run",
            }
        )

    write_csv(CONSOLIDATED_RESULTS, RESULT_FIELDNAMES, output_rows)
    AGENT_PACKET.parent.mkdir(parents=True, exist_ok=True)
    with AGENT_PACKET.open("w", encoding="utf-8") as outfile:
        for packet in pending_packets:
            outfile.write(json.dumps(packet, ensure_ascii=False) + "\n")


def validate_and_review() -> None:
    run_command(
        [
            "python3",
            "part4_analyse_token_to_company/3_layer3_review_agent/1_validate_extraction_results.py",
            "--results-csv",
            str(CONSOLIDATED_RESULTS),
            "--sentences-csv",
            str(OUTPUT_DIR / "token_evidence_sentences.csv"),
            "--output-csv",
            str(VALIDATED_RESULTS),
        ]
    )
    run_command(
        [
            "python3",
            "part4_analyse_token_to_company/3_layer3_review_agent/2_build_review_queue.py",
            "--input-csv",
            str(VALIDATED_RESULTS),
            "--output-csv",
            str(REVIEW_QUEUE),
        ]
    )


def main() -> None:
    if not FULL_INPUT.is_file():
        raise SystemExit(f"Missing full input: {FULL_INPUT}")
    if not MANIFEST.is_file():
        raise SystemExit(f"Missing batch manifest: {MANIFEST}")

    prepare_batch_tmp_dirs()
    run_layer2_official_for_batches()
    run_layer1_for_batches()
    consolidate_results()
    validate_and_review()
    print(f"Consolidated sample results: {CONSOLIDATED_RESULTS}", flush=True)
    print(f"Validated sample results: {VALIDATED_RESULTS}", flush=True)
    print(f"Review queue: {REVIEW_QUEUE}", flush=True)
    print(f"Pending agent packet: {AGENT_PACKET}", flush=True)


if __name__ == "__main__":
    main()
