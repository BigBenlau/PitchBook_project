# Part5 New Chat Handoff

## Current Checkout Status

- This checkout is already fully merged through all planned batches.
- `agent_runs/crypto_company/results.csv` contains `17837` completed result rows.
- `agent_runs/crypto_company/classifier_results.csv` contains `17837` classifier rows.
- `agent_task_batches/crypto_company/` contains `595` batch files covering `17837` tasks.
- `agent_runs/crypto_company/checkpoint.json` should indicate completion through batch `595`, with `next_batch_to_process = 596` as the completion sentinel.
- No active detached longrun should be assumed from this checkout alone. Background-run metadata files may be absent because ordinary backlog work is already complete.

## Use This As The First Prompt In A New Chat

```text
Read /home/benl66/PitchBook_project/part5_analyse_company_to_token/NEW_CHAT_HANDOFF_20260427.md first, then inspect the current final outputs and checkpoint state. Treat this checkout as already fully merged through all planned batches. Only continue into a new longrun or rerun path if the user explicitly asks for additional reruns, audits, or manual-review follow-up, and re-check longrun status first if a detached run is expected to exist.
```

## Goal

Use the queue-first runtime model only when additional reruns or audits must be launched. Do not fall back to older broken round-era assumptions, but also do not assume there is an active backlog run to continue.

The authoritative final outputs are:
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`

All searched results have already been merged into `results.csv` for the planned `595` batches in this checkout.  
All `needs_manual_review=yes` companies should be present in `needs_manual_review.csv`.

## Read These Files First

Read these files in this order:

1. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/Plan.md`
2. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_prompt_template.md`
3. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/runtime/README.md`
4. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/runtime/ARCHITECTURE.md`
5. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/5_run_queue_supervisor.py`
6. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/5_run_round_supervisor.py`
7. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/6_start_long_running_supervisor.py`
8. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/7_check_longrun_status.py`
9. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/3_collect_results.py`
10. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/4_manage_round_runtime.py`
11. `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/part5_schedule_io.py`

Do not reuse stale historical run directories as the main source of truth unless you are doing explicit forensics.

## Current Runtime Model

If a new backlog rerun is needed, use:
- `scripts/6_start_long_running_supervisor.py`
- `--scheduler-mode queue`
- detached launch through `systemd-run --user` when available
- fallback to `nohup` plus a new session only if `systemd-run` fails

Round mode still exists, but it is a fallback path for blocking or debugging runs. It is not the default unattended backlog path.

## Where To Find A Detached Run If One Exists

Latest job metadata:
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_runs/crypto_company_longrun_latest.json`

Do not hard-code an old run directory or old unit name from a previous chat. If the user expects a detached rerun to be active, discover it from that metadata file and then confirm it with the status entrypoint. If the metadata file is absent and final outputs already cover all planned batches, treat the checkout as complete rather than assuming a broken active run.

## Status Checking Rules

Use:
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/7_check_longrun_status.py`

Status checking must:
- prefer `systemctl --user show <unit_name>` if latest metadata includes `unit_name`
- then inspect `supervisor_state.json`, `schedule.csv`, registry, recent events, and host processes
- report queue-specific state when the scheduler is queue mode

Minimum summary for a healthy status report:
- `status`
- `phase`
- `scheduler_mode`
- `active_workers`
- `round_summaries`
- if queue mode is active: `slots`, `waiting_queue`, `tail_retry_queue`, `collect_queue`, `deferred_queue`

If `supervisor` is not visible, `active_workers=0`, and only worker log heartbeat remains, treat that as `orphaned_worker_activity`, not a healthy running supervisor.

## Queue-Mode Semantics

This is the intended unattended backlog behavior for any future rerun or backfill. Do not revert it.

### Primary queue

Ordinary runnable work is:
- `status=prepared`
- or `status=needs_rerun`
- with `tail_retry_pending` not set

Queue mode keeps filling slots until the worker-process budget is consumed. `--max-workers` is a live worker-process budget, not a guaranteed batch count, because split recovery can consume more than one worker process for one batch.

### Collect

Collect is:
- batch-scoped
- serialized
- allowed to merge one completed batch before same-round peers finish

Completed batches do not need to wait for a round barrier before lint/collect.

### Long-tail rule

Per-batch wall-clock budget in longrun mode is currently:
- `7200s`

First timeout:
- terminate active workers
- preserve the current partial prefix
- do not mark terminal `deferred_long_tail` yet
- instead park the batch as:
  - `status=needs_rerun`
  - `queue_state=tail_retry_pending`
  - `tail_retry_pending=yes`
  - `tail_retry_count += 1`

Parked tail-retry work:
- does not return to the normal waiting queue immediately
- may relaunch only after the ordinary `waiting_queue` is empty and the `collect_queue` is empty

Current policy:
- `max_tail_retries = 1`

Second timeout after the parked retry:
- mark terminal `deferred_long_tail`
- preserve current partial state
- write backlog visibility to:
  - `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_runs/crypto_company/long_tail_batches_pending.csv`

Terminal `deferred_long_tail` means:
- the batch is not complete
- it is operationally resolved for the current run
- it must be listed as unfinished backlog in final summaries
- it must be excluded from collect scope

## Schedule Safety Rules

All runtime-side `schedule.csv` writes must go through:
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/part5_schedule_io.py`

This shared writer is required because it:
- takes a schedule lock
- writes through a temp file and atomic replace
- merges fieldnames safely
- prevents partial row updates from truncating the live schedule

Do not add or restore direct raw `open(..., "w")` schedule rewrite paths.

## Final Outputs

Only these are authoritative final outputs:
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- `/home/benl66/PitchBook_project/part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`

All run-local batch and attempt files are intermediate.

## What The New Agent Should Do First

1. Read the files listed in **Read These Files First**
2. Confirm whether all planned batches are already merged by checking `results.csv`, `classifier_results.csv`, `input_companies.csv`, and `checkpoint.json`.
3. Only if the user expects a detached rerun or background job, run the status entrypoint:

```bash
python3 /home/benl66/PitchBook_project/part5_analyse_company_to_token/scripts/7_check_longrun_status.py --json
```

4. Confirm:
- `unit_name`
- `MainPID`
- `scheduler_mode`
- `phase`
- `run_dir`
- current queue state if queue mode is active

5. Before changing code, reconcile:
- `systemd` unit state
- `supervisor_state.json`
- `schedule.csv`
- recent `supervisor_events.log`

6. If control-plane state is inconsistent:
- fix the control-plane divergence first
- preserve final-output rules
- preserve current queue-mode long-tail semantics
- preserve the shared locked schedule write path

If there is no active detached run and final outputs already cover all planned batches, treat the ordinary backlog workflow as complete. Any further execution should be an explicit targeted rerun, audit, or manual-review follow-up rather than a blind resume.

## What Not To Assume

Do not assume:
- an old run directory from a previous chat is still the active run
- `deferred_long_tail` always means first-time timeout
- round barriers control queue-mode launch order
- `4_manage_round_runtime.py` is the only writer of `schedule.csv`
- transient systemd units remaining `not-found` after successful completion implies failure

## Use This Exact User Prompt In A New Chat

```text
Read /home/benl66/PitchBook_project/part5_analyse_company_to_token/NEW_CHAT_HANDOFF_20260427.md first, then inspect the current final outputs and checkpoint state. Treat this checkout as already fully merged through all planned batches. Only launch or continue a detached longrun if the user explicitly asks for reruns or audits, and re-check longrun status first if such a run is expected to exist.
```
