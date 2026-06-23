# Runtime Strategy Layer

This folder is the authoritative strategy layer for the Part5 formal company-to-token pipeline.

Files:
- `policy.json`: machine-readable controller policy for statuses, failure types, timeouts, escalation, and cleanup.
- `ARCHITECTURE.md`: human-readable architecture notes for queue-first unattended runs.
- `worker_base_template.md`: canonical worker base prompt used by prepare and controller layers.

Principles:
- Part5 has one formal token mapping rule: include a token only when the company is an officially recognized founding entity, co-founding entity, or original founding organization of the blockchain/protocol ecosystem.
- Final `results.csv` stores formal token mappings in `token_results`, a JSON object-list field placed at the end of the row.
- `token_symbol` is a compact JSON list derived from `token_results[*].token_symbol` for easier scanning.
- `scripts/2_prepare_worker_runs.py` creates batch roots, stable base instructions, and initial attempt skeletons.
- `scripts/4_manage_round_runtime.py` prepares launch queues, marks selected batches started, and watches startup/stall failures.
- `scripts/5_run_round_supervisor.py` remains the blocking round-mode supervisor and shared helper layer.
- `scripts/5_run_queue_supervisor.py` is the default unattended queue-mode scheduler.
- `scripts/3_collect_results.py` validates and merges completed batch outputs into final files.
- `scripts/part5_schedule_io.py` is the shared locked atomic `schedule.csv` writer.
- Every respawn creates a new attempt directory; old attempts are debugging artifacts only.
