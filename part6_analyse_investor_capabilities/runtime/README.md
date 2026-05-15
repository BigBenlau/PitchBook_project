# Part6 Runtime

This folder is the authoritative runtime strategy layer for the part6 investor capability harness.

Files:
- `ARCHITECTURE.md`: orchestration and ownership notes
- `policy.json`: timeout, retry, and escalation policy
- `worker_base_template.md`: canonical worker base instructions

The runtime harness follows the same operational pattern as the existing company harness:
- build batches
- prepare worker runs
- run queue or round supervisor
- collect verified outputs into global final tables
