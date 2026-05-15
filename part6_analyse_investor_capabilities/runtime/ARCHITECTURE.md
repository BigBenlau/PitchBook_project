# Runtime Architecture

## Ownership

- Prepare layer: `scripts/2_prepare_worker_runs.py`
  - materializes per-batch run directories
  - writes `tasks.jsonl`
  - writes stable `base_worker_instructions.md`
  - creates `attempts/attempt_0001/` skeletons
- Runtime controller helpers: `scripts/4_manage_round_runtime.py`
  - prepares launch queues
  - marks selected batches started
  - watches startup and stall failures
  - creates new attempts for reruns
  - applies escalation policy from `runtime/policy.json`
- Round supervisor: `scripts/5_run_round_supervisor.py`
  - blocking round-mode scheduler
- Queue supervisor: `scripts/5_run_queue_supervisor.py`
  - unattended backlog scheduler
  - owns live queue scheduling, slot filling, collect gating, and tail-retry flow
- Collector/lint: `scripts/3_collect_results.py`
  - validates attempt outputs
  - merges authoritative final tables
- Shared schedule writer: `scripts/part6_schedule_io.py`
  - canonical locked atomic `schedule.csv` writer

## Canonical Runtime Files

- `runtime/policy.json`
- `runtime/worker_base_template.md`
- `runtime/ARCHITECTURE.md`
- `agent_prompt_template.md`
- `Plan.md`

## Schedule Model

Core batch statuses:
- `prepared`
- `running`
- `needs_rerun`
- `completed`
- `deferred_long_tail`

Queue-related fields:
- `queue_state`
- `collect_state`
- `tail_retry_pending`
- `tail_retry_count`
- `completion_mode`

## Attempt Model

Every batch root contains:
- `tasks.jsonl`
- `base_worker_instructions.md`
- `attempts/attempt_0001/`
- later attempts as needed
- `active_attempt_lease.json`

Only the active attempt recorded in `schedule.csv` is authoritative.

## Final Outputs

Only these files are authoritative final outputs:
- `agent_runs/crypto_investor/results.csv`
- `agent_runs/crypto_investor/needs_manual_review.csv`

Batch-local attempt artifacts are intermediate only.
