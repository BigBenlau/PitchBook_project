# Runtime Strategy Layer

This folder is the authoritative strategy layer for the part4 token-to-company multi-round harness.

Files:

- `policy.json`: runtime statuses, failure types, timeouts, escalation, and cleanup rules
- `ARCHITECTURE.md`: queue-first orchestration notes
- `worker_base_template.md`: canonical base worker prompt used by prepare/runtime layers

Principles:

- `scripts/2_prepare_worker_runs.py` creates batch roots, stable base instructions, and initial attempt skeletons
- `scripts/4_manage_round_runtime.py` prepares launch queues and manages rerun attempts
- `scripts/5_run_queue_supervisor.py` is the default unattended queue-mode scheduler
- `scripts/5_run_round_supervisor.py` remains the blocking round-mode fallback
- `scripts/3_collect_results.py` validates active attempt outputs and merges authoritative final tables
- `scripts/part4_schedule_io.py` is the canonical locked write path for `schedule.csv`
- every rerun creates a new attempt directory; only the active attempt recorded in `schedule.csv` is authoritative
