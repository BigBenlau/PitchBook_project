# Runtime Architecture

## Ownership

- Prepare layer: `scripts/2_prepare_worker_runs.py`
- Runtime controller: `scripts/4_manage_round_runtime.py`
- Round supervisor: `scripts/5_run_round_supervisor.py`
- Queue supervisor: `scripts/5_run_queue_supervisor.py`
- Collector/lint: `scripts/3_collect_results.py`
- Shared schedule writer: `scripts/part4_schedule_io.py`

Queue mode is the default unattended path for future part4 backlog runs.

## Canonical Runtime Files

- `runtime/policy.json`
- `runtime/worker_base_template.md`
- `runtime/ARCHITECTURE.md`
- `agent_prompt_template.md`
- `Plan.md`

## Schedule Model

Core statuses:

- `prepared`
- `running`
- `needs_rerun`
- `completed`
- `deferred_long_tail`

Queue fields:

- `queue_state`
- `collect_state`
- `tail_retry_pending`
- `tail_retry_count`
- `completion_mode`

Only the active attempt paths recorded in `schedule.csv` are authoritative.

## Attempt Model

Each batch root contains:

- `tasks.jsonl`
- `base_worker_instructions.md`
- `attempts/attempt_0001/`
- later attempts as needed
- `active_attempt_lease.json`

Every rerun creates a fresh attempt directory. Old attempts remain only for debugging.

## Main-Agent Execution Order

Default longrun path:

1. run `scripts/2_prepare_worker_runs.py`
2. run `scripts/6_start_long_running_supervisor.py --scheduler-mode queue`
3. use `scripts/7_check_longrun_status.py` for status

Manual round fallback:

1. `scripts/4_manage_round_runtime.py --prepare-launches`
2. spawn workers from the launch queue
3. `--mark-round-started`
4. `--watch-round`
5. rerun only affected batches when runtime actions are emitted
6. lint
7. verifier
8. collect

## Queue-Mode State Machine

Supervisor phases:

- `bootstrap`
- `fill_slots`
- `watch`
- `collect`
- `split_recovery`
- `tail_retry_pending`
- `completed`
- `failed`

Rules:

- queue mode keeps up to `--max-workers` live worker processes busy
- collect is batch-scoped and serialized
- first long-tail timeout parks the batch as `tail_retry_pending`
- second timeout becomes terminal `deferred_long_tail`

## Final Outputs

Only these are authoritative final outputs:

- `agent_runs/token_company/results.csv`
- `agent_runs/token_company/classifier_results.csv`
- `agent_runs/token_company/needs_manual_review.csv`

Run-local attempt files are intermediate artifacts only.
