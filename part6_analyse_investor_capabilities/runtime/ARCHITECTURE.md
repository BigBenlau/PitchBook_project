# Runtime Architecture

## Ownership

- Prepare layer: `scripts/2_prepare_worker_runs.py`
  - materializes per-batch run directories from
    `part5_to_part6/output/part6_batches`
  - writes `tasks.jsonl`
  - writes stable `base_worker_instructions.md`
  - creates `attempts/attempt_0001/` skeletons
- Runtime controller helpers: `scripts/4_manage_round_runtime.py`
  - prepares launch queues
  - marks selected batches started
  - watches startup and stall failures
  - creates new attempts for reruns
  - applies escalation policy from `runtime/policy.json`
- Queue supervisor: `scripts/5_run_queue_supervisor.py`
  - owns the unattended backlog scheduler
  - owns live queue scheduling, slot filling, collect gating, and tail-retry flow
  - is the only supported active supervisor mode
- Collector/lint: `scripts/3_collect_results.py`
  - validates active attempt outputs
  - merges authoritative final tables
  - writes `classifier_results.csv`, `results.csv`,
    `needs_manual_review.csv`, and collector checkpoint files
- Final output validator: `scripts/10_validate_final_outputs.py`
  - validates final row count, task order, classifier/results alignment,
    literal guards, placeholder guards, and deterministic skip-rule guards
- Shared schedule writer: `scripts/part6_schedule_io.py`
  - canonical locked atomic `schedule.csv` writer

## Canonical Runtime Files

- `runtime/policy.json`
- `runtime/worker_base_template.md`
- `runtime/ARCHITECTURE.md`
- `agent_prompt_template.md`
- `Plan.md`

## Schedule Model

Part6 is queue-only. `round_index` remains only as a queue-group identifier for
schedule grouping, launch queue filenames, and verifier artifacts. It is not a
progress metric, and runtime state must not publish a round-based current
progress field.

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

- `agent_runs/crypto_investor/classifier_results.csv`
- `agent_runs/crypto_investor/results.csv`
- `agent_runs/crypto_investor/needs_manual_review.csv`

Batch-local attempt artifacts and historical branch/rerun folders are
intermediate or archive-only.

Completion requires:

```bash
python3 part5_to_part6/scripts/2_verify_formal_bridge_outputs.py \
  --part6-reference-results-csv part6_analyse_investor_capabilities/agent_runs/crypto_investor/results.csv

python3 part6_analyse_investor_capabilities/scripts/10_validate_final_outputs.py \
  --batch-dir part5_to_part6/output/part6_batches \
  --final-dir part6_analyse_investor_capabilities/agent_runs/crypto_investor \
  --expected-row-count 10353
```
