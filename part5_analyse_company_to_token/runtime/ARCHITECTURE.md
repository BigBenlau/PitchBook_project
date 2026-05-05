# Runtime Architecture

## Ownership
- Prepare layer: `scripts/2_prepare_worker_runs.py`
  - creates batch root directories
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
  - shared helper layer reused by queue mode
- Queue supervisor: `scripts/5_run_queue_supervisor.py`
  - active unattended backlog scheduler
  - owns live queue scheduling, slot filling, collect gating, and tail-retry flow
- Collector/lint: `scripts/3_collect_results.py`
  - validates active attempt outputs
  - merges authoritative final tables
  - never downgrades runtime states to legacy enums
- Shared schedule writer: `scripts/part5_schedule_io.py`
  - the canonical `schedule.csv` write path for runtime code
  - uses a schedule lock plus temp-file atomic replace
  - merges fieldnames and rows by `batch_file` so partial writes cannot shrink the live schedule

`scripts/4_manage_round_runtime.py` is not the sole owner of `schedule.csv`. Queue supervisor, round supervisor, and collector all write through `part5_schedule_io.py`.

## Canonical Runtime Files
- `runtime/policy.json`
  - machine-readable controller policy for statuses, failure types, timeouts, escalation, and cleanup
- `runtime/worker_base_template.md`
  - the only canonical worker base prompt
- `runtime/ARCHITECTURE.md`
  - human-readable runtime orchestration notes
- `agent_prompt_template.md`
  - operator-facing rules for the current part5 workflow
- `Plan.md`
  - end-to-end execution, schema, verification, and longrun behavior rules

## Schedule Model

Core batch statuses:
- `prepared`
- `running`
- `needs_rerun`
- `completed`
- `deferred_long_tail`

Queue-related fields used by the active queue-mode flow:
- `queue_state`
  - common values include `queued`, `running`, `ready_to_collect`, `collecting`, `tail_retry_pending`, `completed`, `deferred_long_tail`
- `collect_state`
  - `pending`, `running`, `done`, `skipped`, or `failed`
- `tail_retry_pending`
  - `yes` means the batch hit its first long-tail timeout and is parked for one later retry
- `tail_retry_count`
  - current policy is `DEFAULT_MAX_TAIL_RETRIES = 1`
- `completion_mode`
  - records how a batch operationally resolved, for example normal completion or terminal long-tail defer

Only the active attempt paths recorded in `schedule.csv` are authoritative for runtime, lint, verifier, and merge.

## Attempt Model
Every batch root contains:
- `tasks.jsonl`
- `base_worker_instructions.md`
- `attempts/attempt_0001/`
- `attempts/attempt_0002/`, ... as needed
- `active_attempt_lease.json`

Every rerun creates a new attempt directory. Older attempts stay on disk for debugging, but only the active attempt in `schedule.csv` is authoritative.

## Segment Model
- `batch` remains the immutable 30-company business unit.
- `round` remains metadata for grouping and reporting.
- Queue mode does not use round barriers to decide when to launch the next batch.
- Worker budget is a live worker-process budget, not a guaranteed batch count.
- Split recovery may consume multiple worker processes for one batch.
- A fresh worker normally owns the whole batch for one launch and then exits.
- Recovery mode may create a fresh continuation attempt over the unresolved suffix.
- `narrowed_suffix_only` remains a recovery-only mode.
- The controller maintains one active lease per batch. Workers should stop when their lease is no longer current.

## Prompt Ownership
- Base instructions describe research workflow and schema only.
- Attempt wrapper provides write scope, active CSV paths, continuation rules, and runtime constraints.
- Workers must obey the attempt wrapper for all file writes.

## Main-Agent Execution Order

Default entrypoint:
1. Run `scripts/2_prepare_worker_runs.py` for the desired batch window.
2. Run `scripts/6_start_long_running_supervisor.py`.
3. Prefer `systemd-run --user` for detached longruns. Fall back to `nohup` plus a new session only if `systemd-run` fails.
4. Use `--scheduler-mode queue` for backlog longruns unless the operator explicitly needs blocking round-mode behavior.
5. Use `scripts/7_check_longrun_status.py` as the authoritative status entrypoint.

Manual round-mode fallback:
1. Run `scripts/4_manage_round_runtime.py --prepare-launches --round-index N`.
2. Spawn workers strictly from `launch_queue_round_XXXX.md`.
3. Run `scripts/4_manage_round_runtime.py --mark-round-started --round-index N`.
4. Periodically run `scripts/4_manage_round_runtime.py --watch-round --round-index N`.
5. If runtime actions are emitted, rerun `--prepare-launches` and relaunch only affected batches or recovery attempts.
6. Once the round is complete, run verifier/lint for that round.
7. If verifier/lint finds real errors, prepare fresh rerun workers only for those batches.
8. Run `scripts/3_collect_results.py` for authoritative merge after the round is verifier-clean.

## Queue-Mode State Machine

Launcher state:
- `prepare_window`
  - choose the next batch window or use the explicit backlog batch dir
- `launch_supervisor`
  - start `5_run_queue_supervisor.py` through `systemd-run --user` when available

Queue supervisor phases:
- `bootstrap`
  - load schedule, registry, launcher metadata, and target rounds
- `fill_slots`
  - prepare selected batches and keep up to `--max-workers` live worker processes busy
- `watch`
  - poll runtime state, registry, logs, and split-recovery state
- `collect`
  - run serialized batch-scoped lint and collect for `ready_to_collect` batches
- `split_recovery`
  - reconcile split shard launches and merges
- `tail_retry_pending`
  - parked-first-timeout state while waiting for primary queue and collect queue to drain
- `completed`
  - no open primary queue work, no tail retry work, no active workers, and no collect backlog remain
- `failed`
  - uncaught exception or explicit fatal exit

Queue selection rules:
- Primary waiting work is ordinary `prepared` or `needs_rerun` work with `tail_retry_pending` not set.
- Parked tail-retry work is excluded from the primary waiting queue.
- Tail retry becomes launchable only when the primary waiting queue is empty and the collect queue is empty.
- With current policy, the first long-tail timeout parks the batch as:
  - `status=needs_rerun`
  - `queue_state=tail_retry_pending`
  - `tail_retry_pending=yes`
  - `tail_retry_count += 1`
- With `DEFAULT_MAX_TAIL_RETRIES = 1`, the second long-tail timeout becomes terminal `deferred_long_tail`.

Collect rules:
- Collect is batch-scoped, not round-barrier scoped.
- Collect stays serialized even in queue mode.
- Completed batches can merge into the global final outputs before same-round peers finish.
- Terminal `deferred_long_tail` batches are excluded from collect scope.

## Round-Mode State Machine

Round mode remains available for fallback and foreground blocking runs.

Round supervisor phases:
- `prepare`
- `launch`
- `mark_started`
- `watch`
- `lint`
- `collect`
- `next_round`
- `completed`
- `failed`

Round mode still treats `deferred_long_tail` as operationally resolved for the current round so the run can keep advancing, but queue mode is the active unattended backlog path.

## Status Reporting

Use `scripts/7_check_longrun_status.py`.

Status reporting should:
- first inspect `crypto_company_longrun_latest.json`
- if `unit_name` exists, query `systemctl --user show <unit_name>`
- then inspect `supervisor_state.json`, `schedule.csv`, registry, and host processes
- in queue mode, include:
  - `slots`
  - `waiting_queue`
  - `tail_retry_queue`
  - `collect_queue`
  - `deferred_queue`

## Final Outputs

Only these files are authoritative final outputs:
- `agent_runs/crypto_company/results.csv`
- `agent_runs/crypto_company/needs_manual_review.csv`

Run-local batch and attempt files are intermediate artifacts.

## Failure Classes That Matter

Control-plane failures:
- supervisor exits or stops updating state
- stale or orphan worker processes remain alive
- schedule and state snapshots diverge

Mitigations currently in place:
- detached longruns should be launched through `6_start_long_running_supervisor.py`
- prefer `systemd-run --user`
- fall back to `nohup` only when systemd launch fails
- write terminal failures into `supervisor_events.log` and `supervisor_state.json`
- route all runtime-side `schedule.csv` writes through `part5_schedule_io.py`

## Long-Tail Split Recovery
- The supervisor does not close long-tail batches by fabricating manual-review filler rows.
- After repeated runtime or lint failure loops on the same batch, the supervisor may promote that batch into `split_batch_2x15` recovery.
- `split_batch_2x15` keeps the business unit as one 30-company batch, but launches 2 fresh shard workers under the same active attempt.
- Each shard writes authoritative shard CSVs and must either finish real searched rows or stop on a real blocker.
- The supervisor merges the 2 shard outputs back into the batch-level active attempt only after both shards fully cover their assigned task windows and preserve original task order.
