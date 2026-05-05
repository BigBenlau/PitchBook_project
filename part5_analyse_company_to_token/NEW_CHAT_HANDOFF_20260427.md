# Part5 New Chat Handoff

## Use This As The First Prompt In A New Chat

```text
Read /home/benl66/pitchbook/part5_analyse_company_to_token/NEW_CHAT_HANDOFF_20260427.md first, then continue the part5 longrun work from the current active run. Follow the rules in that handoff exactly. Before making changes, re-check the current longrun status with the fixed status entrypoint.
```

## Goal

Continue the `part5_analyse_company_to_token` longrun workflow with the current queue-first operational model, without falling back to older broken round-era assumptions.

The authoritative final outputs are:
- `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`

All searched results must eventually be merged into `results.csv`.  
All `needs_manual_review=yes` companies must be present in `needs_manual_review.csv`.

## Read These Files First

Read these files in this order:

1. `/home/benl66/pitchbook/part5_analyse_company_to_token/Plan.md`
2. `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_prompt_template.md`
3. `/home/benl66/pitchbook/part5_analyse_company_to_token/runtime/README.md`
4. `/home/benl66/pitchbook/part5_analyse_company_to_token/runtime/ARCHITECTURE.md`
5. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/5_run_queue_supervisor.py`
6. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/5_run_round_supervisor.py`
7. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/6_start_long_running_supervisor.py`
8. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/7_check_longrun_status.py`
9. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/3_collect_results.py`
10. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/4_manage_round_runtime.py`
11. `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/part5_schedule_io.py`

Do not reuse stale historical run directories as the main source of truth unless you are doing explicit forensics.

## Current Runtime Model

Current production backlog runs use:
- `scripts/6_start_long_running_supervisor.py`
- `--scheduler-mode queue`
- detached launch through `systemd-run --user` when available
- fallback to `nohup` plus a new session only if `systemd-run` fails

Round mode still exists, but it is a fallback path for blocking or debugging runs. It is not the current unattended backlog default.

## Where To Find The Current Active Run

Latest job metadata:
- `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_runs/crypto_company_longrun_latest.json`

Do not hard-code an old run directory or old unit name from a previous chat. Always discover the current active run from that metadata file and then confirm it with the status entrypoint.

## Status Checking Rules

Use:
- `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/7_check_longrun_status.py`

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

This is the current intended unattended backlog behavior. Do not revert it.

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
  - `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_runs/crypto_company/long_tail_batches_pending.csv`

Terminal `deferred_long_tail` means:
- the batch is not complete
- it is operationally resolved for the current run
- it must be listed as unfinished backlog in final summaries
- it must be excluded from collect scope

## Schedule Safety Rules

All runtime-side `schedule.csv` writes must go through:
- `/home/benl66/pitchbook/part5_analyse_company_to_token/scripts/part5_schedule_io.py`

This shared writer is required because it:
- takes a schedule lock
- writes through a temp file and atomic replace
- merges fieldnames safely
- prevents partial row updates from truncating the live schedule

Do not add or restore direct raw `open(..., "w")` schedule rewrite paths.

## Final Outputs

Only these are authoritative final outputs:
- `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- `/home/benl66/pitchbook/part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`

All run-local batch and attempt files are intermediate.

## What The New Agent Should Do First

1. Read the files listed in **Read These Files First**
2. Run the status entrypoint:

```bash
python3 /home/benl66/pitchbook/part5_analyse_company_to_token/scripts/7_check_longrun_status.py --json
```

3. Confirm:
- `unit_name`
- `MainPID`
- `scheduler_mode`
- `phase`
- `run_dir`
- current queue state if queue mode is active

4. Before changing code, reconcile:
- `systemd` unit state
- `supervisor_state.json`
- `schedule.csv`
- recent `supervisor_events.log`

5. If control-plane state is inconsistent:
- fix the control-plane divergence first
- preserve final-output rules
- preserve current queue-mode long-tail semantics
- preserve the shared locked schedule write path

## What Not To Assume

Do not assume:
- an old run directory from a previous chat is still the active run
- `deferred_long_tail` always means first-time timeout
- round barriers control queue-mode launch order
- `4_manage_round_runtime.py` is the only writer of `schedule.csv`
- transient systemd units remaining `not-found` after successful completion implies failure

## Use This Exact User Prompt In A New Chat

```text
Read /home/benl66/pitchbook/part5_analyse_company_to_token/NEW_CHAT_HANDOFF_20260427.md first, then continue the part5 longrun work from the current active run. Preserve the current final-output rules, queue-mode long-tail rules, and systemd-based supervisor flow. Before changing code, re-check the current longrun status with the status entrypoint.
```
