#!/usr/bin/env python3
"""
Prepare a small sample Part4 run under the new token_id-based harness.

This script does not perform live official-site crawling or agent extraction.
It prepares:
- token_master.csv
- batch_manifest.csv
- one or more prepared batch CSVs
- worker/verifier scaffolding under agent_runs/
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PART3_OUTPUT_DIR = SCRIPT_DIR.parent / "part3_find_token_list_at_cg_and_cmc" / "output"
DEFAULT_SAMPLE_DIR = SCRIPT_DIR / "agent_runs" / "token_company_sample"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare a sample Part4 worker scaffold.")
    parser.add_argument(
        "--coingecko-csv",
        type=Path,
        default=PART3_OUTPUT_DIR / "coingecko_about.csv",
    )
    parser.add_argument(
        "--cmc-csv",
        type=Path,
        default=PART3_OUTPUT_DIR / "cmc_about_qa.csv",
    )
    parser.add_argument("--sample-dir", type=Path, default=DEFAULT_SAMPLE_DIR)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sample_dir = args.sample_dir.resolve()
    sample_dir.mkdir(parents=True, exist_ok=True)

    token_master_csv = sample_dir / "token_master.csv"
    batch_dir = sample_dir / "input" / "batches"
    manifest_csv = sample_dir / "input" / "batch_manifest.csv"
    runs_dir = sample_dir / "runs"

    subprocess.run(
        [
            "python3",
            str(SCRIPT_DIR / "scripts" / "0_prepare_input_batches.py"),
            "--coingecko-csv",
            str(args.coingecko_csv.resolve()),
            "--cmc-csv",
            str(args.cmc_csv.resolve()),
            "--token-master-csv",
            str(token_master_csv),
            "--batch-dir",
            str(batch_dir),
            "--manifest",
            str(manifest_csv),
            "--batch-size",
            str(args.batch_size),
            "--overwrite",
        ],
        check=True,
    )

    worker_cmd = [
        "python3",
        str(SCRIPT_DIR / "scripts" / "1_prepare_worker_runs.py"),
        "--manifest",
        str(manifest_csv),
        "--token-master-csv",
        str(token_master_csv),
        "--runs-dir",
        str(runs_dir),
        "--workers",
        str(args.workers),
    ]
    if args.force:
        worker_cmd.append("--force")
    subprocess.run(worker_cmd, check=True)

    print(f"Sample token master: {token_master_csv}", flush=True)
    print(f"Sample batch manifest: {manifest_csv}", flush=True)
    print(f"Sample runs dir: {runs_dir}", flush=True)


if __name__ == "__main__":
    main()
