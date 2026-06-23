# Runtime Architecture

## Ownership

- Prepare layer: `scripts/2_prepare_worker_runs.py`
  - creates batch root directories
  - writes `tasks.jsonl`
  - writes stable `base_worker_instructions.md`
  - creates initial attempt skeletons
- Runtime controller: `scripts/4_manage_round_runtime.py`
  - prepares launch queues
  - marks selected batches started
  - watches startup and stall failures
  - creates recovery attempts according to `runtime/policy.json`
- Round supervisor: `scripts/5_run_round_supervisor.py`
  - blocking round-mode scheduler
  - shared helper layer reused by queue mode
- Queue supervisor: `scripts/5_run_queue_supervisor.py`
  - default unattended scheduler
  - owns queue scheduling, slot filling, collect gating, and tail-retry flow
- Collector/lint: `scripts/3_collect_results.py`
  - validates active attempt outputs
  - merges authoritative final tables
- Shared schedule writer: `scripts/part5_schedule_io.py`
  - locked atomic writer for all live `schedule.csv` updates

## Formal Result Contract

Part5 final output has one formal token mapping field and one compact derived symbol field:

- `token_results`: JSON object-list string of founding-entity token mappings.
- `token_symbol`: JSON list string derived from `token_results[*].token_symbol`.

No active runtime path should emit additional rule-specific token columns. Workers, verifier, collector, and supervisor must all use the same schema from `scripts/result_schema.py`.

## Main Execution Order

Default queue-mode path:

1. Build batch inputs with `scripts/1_build_company_token_batches.py`.
2. Prepare worker run skeletons with `scripts/2_prepare_worker_runs.py`.
3. Start a detached longrun with `scripts/6_start_long_running_supervisor.py --scheduler-mode queue`.
4. Queue supervisor keeps up to `--max-workers` active worker processes busy.
5. Runtime controller handles startup failures, partial stalls, continuation attempts, narrowed suffix attempts, and split recovery.
6. Collector validates and merges completed batch outputs.
7. Status checks use `scripts/7_check_longrun_status.py`.

Round mode remains available only as a foreground fallback.

## Schedule And Attempt Model

Core statuses:

- `prepared`
- `running`
- `needs_rerun`
- `completed`
- `deferred_long_tail`

Every batch root contains:

- `tasks.jsonl`
- `base_worker_instructions.md`
- `attempts/attempt_0001/`
- later `attempts/attempt_XXXX/` as needed
- `active_attempt_lease.json`

Only the active attempt paths recorded in `schedule.csv` are authoritative for runtime, lint, verifier, and merge.

## Queue Behavior

- Queue mode does not use round barriers to launch later batches.
- Worker budget is a live process budget, not a fixed batch count.
- Split recovery may consume multiple worker processes for one batch.
- Collect is batch-scoped and serialized.
- Terminal `deferred_long_tail` batches are excluded from collect scope and recorded for later repair.

## Status Reporting

Use `scripts/7_check_longrun_status.py`.

Status reporting should inspect:

- latest longrun metadata
- supervisor state
- registry
- schedule
- recent events
- active host processes

## Final Outputs

Authoritative final outputs live under `agent_runs/crypto_company/`:

- `results.csv`
- `results_with_ticker.csv`
- `results_without_ticker.csv`
- `needs_manual_review.csv`
- `classifier_results.csv`

Run-local batch and attempt files are intermediate artifacts.
