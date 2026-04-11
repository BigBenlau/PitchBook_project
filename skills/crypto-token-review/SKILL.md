---
name: crypto-token-review
description: Review company rows to map each company to zero, one, or multiple crypto projects and token tickers. Use when working in this repo with crypto company CSVs, preparing repeated agent tasks, or enforcing token/ticker evidence rules limited to official sites, CoinGecko, and CoinMarketCap.
---

# Crypto Token Review

## Overview

Use this skill for repeated token/ticker review in this repo. Keep the task narrow: map each company to project-token data, fill `token_ticker` only when supported, and use an empty JSON list (`[]`) for unresolved or no-token cases.

Because this skill is repo-local, pass its path explicitly when another agent should use it. In this repo the skill path is `skills/crypto-token-review`.

## Quick Start

For batch preparation, run:

```bash
python skills/crypto-token-review/scripts/build_agent_tasks.py
```

This reads `part4/project_review_queue.csv` by default and writes batch JSONL task files under `part4/agent_task_batches/`.

For one-off review, render `references/agent_task_prompt.md` with the company row and send the result to an agent together with the skill path.

## Workflow

1. Use the company row only as context.
2. Restrict evidence sources to:
   - official website under the official domain
   - CoinGecko
   - CoinMarketCap
3. Decide only these fields unless the caller explicitly asks for more:
   - `project_name`
   - `project_url`
   - `token_ticker`
   - `token_name`
   - `token_url`
   - `has_token_evidence`
   - `evidence_urls`
   - `evidence_source_types`
   - `confidence`
   - `needs_manual_review`
4. Return exactly one CSV row per company.
5. If no token is found, return `token_ticker`, `token_name`, and `token_url` as empty JSON lists: `[]`.
6. If multiple token tickers are confirmed for the company, record them in JSON lists in the same row.
7. Return CSV only, not prose.

## Decision Rules

- Do not treat `crypto`, `blockchain`, `exchange`, `Verticals`, or relation hits as token evidence.
- Do not treat missing evidence as a confirmed no-token result; use `token_ticker = []`.
- Fill `token_ticker` only when supported by official site, CoinGecko, or CoinMarketCap.
- Do not treat stock `Exchange` or stock `Ticker` as crypto token evidence.
- Prefer official site evidence over CoinGecko and CoinMarketCap if sources conflict.
- Mark `needs_manual_review = yes` when brand mapping is ambiguous or allowed sources conflict.
- Keep listing work out of scope unless the allowed sources themselves already expose the listing detail.

## Batch Mode

Use `scripts/build_agent_tasks.py` to generate agent-ready prompts in batches.

Default behavior:

- Input CSV: `part4/project_review_queue.csv`
- Prompt template: `skills/crypto-token-review/references/agent_task_prompt.md`
- Output directory: `part4/agent_task_batches/`
- Output files:
  - `manifest.csv`
  - `batch_0001.jsonl`, `batch_0002.jsonl`, ...

Each JSONL entry contains:

- company metadata
- allowed source policy
- task scope
- a fully rendered prompt ready to submit to an agent

Useful flags:

```bash
python skills/crypto-token-review/scripts/build_agent_tasks.py --limit 100
python skills/crypto-token-review/scripts/build_agent_tasks.py --offset 500 --limit 200
python skills/crypto-token-review/scripts/build_agent_tasks.py --company-id 103694-14 --company-id 103694-95
python skills/crypto-token-review/scripts/build_agent_tasks.py --only-unresolved
```

To prepare a Codex-native run directory for execution inside the current conversation, run:

```bash
python skills/crypto-token-review/scripts/submit_agent_tasks.py --batch-jsonl part4/agent_task_batches/crypto_company_first30/batch_0001.jsonl --run-dir part4/agent_runs/crypto_company_first30
```

This does not call any external API. It writes:

- `tasks.jsonl`
- `manifest.csv`
- `instructions.md`
- `results.jsonl`

Then use the current Codex conversation to execute the tasks in `tasks.jsonl` with worker agents and append one CSV-compatible row per company.

## Repo Context

When this skill is used in this repo, the canonical policy files are:

- `part5_analyse_company_to_token/Plan.md`
- `part5_analyse_company_to_token/agent_prompt_template.md`

Use them for project-specific wording changes. Use this skill as the reusable operating layer.

## Resources

- `scripts/build_agent_tasks.py`: Build JSONL task batches from the review queue CSV.
- `references/agent_task_prompt.md`: Deterministic prompt scaffold with placeholders used by the batch builder.
- `scripts/submit_agent_tasks.py`: Prepare a Codex-native run directory from a task batch.
- `scripts/backfill_agent_results.py`: Merge completed Codex worker JSON outputs back into a CSV.
