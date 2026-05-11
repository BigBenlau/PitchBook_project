# Runtime Strategy Layer

This folder is the authoritative strategy layer for the part5 multi-round harness.

Files:
- `policy.json`: machine-readable controller policy for statuses, failure types, timeouts, escalation, and cleanup.
- `ARCHITECTURE.md`: human-readable architecture notes for the queue-first runtime used for unattended backlog reruns, with round mode retained as fallback.
- `worker_base_template.md`: canonical worker base prompt used by both prepare and controller layers.

Principles:
- `scripts/2_prepare_worker_runs.py` creates batch roots, stable base instructions, and initial attempt skeletons.
- `scripts/4_manage_round_runtime.py` prepares launch queues and marks selected batches started; it is not the only writer of `schedule.csv`.
- `scripts/5_run_round_supervisor.py` remains the blocking round-mode supervisor and shared helper layer.
- `scripts/5_run_queue_supervisor.py` is the default unattended queue-mode scheduler used when a new backlog longrun or rerun is launched.
- `scripts/3_collect_results.py` validates and merges completed batch outputs into the global final files; queue-mode collect is batch-scoped and serialized.
- `scripts/part5_schedule_io.py` is the shared `schedule.csv` write path. All runtime writers must use its locked atomic write flow instead of rewriting the CSV directly.
- Every respawn creates a new attempt directory; old attempts remain for debugging only.
- Unattended longrun semantics for future backlog reruns are queue-first:
  - `scripts/6_start_long_running_supervisor.py` launches detached runs and supports `--scheduler-mode round|queue`.
  - launch backlog reruns with `--scheduler-mode queue`.
  - queue mode keeps up to `--max-workers` live worker processes busy, not a fixed batch count, because split recovery can consume multiple worker processes for one batch.
  - first long-tail timeout parks the batch as `tail_retry_pending`; it gets one more retry only after the normal waiting queue and collect queue are both empty.
  - second long-tail timeout becomes terminal `deferred_long_tail`.
