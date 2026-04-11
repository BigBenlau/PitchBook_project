# Codex Run Instructions

This run directory is prepared for execution inside the current Codex conversation.

Run metadata:
- prepared_at: 2026-04-10T08:20:33+00:00
- run_dir: /Users/benlao/Downloads/STANFORD_20260201/part4/agent_runs/crypto_company_first30
- selected_tasks: 30
- skill_path: /Users/benlao/Downloads/STANFORD_20260201/skills/crypto-token-review

Files:
- tasks.jsonl: the task list to execute in Codex
- manifest.csv: task summary
- results.jsonl: append one JSON line per completed task

How to use in Codex:
1. Read `tasks.jsonl`.
2. For each task, spawn a worker agent in the current conversation.
3. Give the worker the task's `prompt` exactly as written.
4. Require the worker to return one compact JSON object that matches the task schema.
5. Append one line to `results.jsonl` with this structure:

{"task_index":1,"company_id":"...","company_name":"...","normalized_domain":"...","status":"completed","parsed_output":{...},"raw_output":"...","completed_at":"..."}

Result rules:
- `parsed_output` must be the JSON object returned by the worker
- `status` should be `completed` or `error`
- `raw_output` may keep the worker's original text for auditability
- `completed_at` should be an ISO timestamp

After results are written, run:

python skills/crypto-token-review/scripts/backfill_agent_results.py --input-csv part2_build_crypto_candidate/output/crypto_company.csv --run-dir /Users/benlao/Downloads/STANFORD_20260201/part4/agent_runs/crypto_company_first30
