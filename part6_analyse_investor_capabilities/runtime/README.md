# Part6 Runtime

This folder is the authoritative runtime strategy layer for the Part6 investor
capability harness.

Canonical active input:

- `part5_to_part6/output/part6_batches/`

Canonical active final output:

- `part6_analyse_investor_capabilities/agent_runs/crypto_investor/`

Files:

- `ARCHITECTURE.md`: orchestration, ownership, and completion-gate notes.
- `policy.json`: timeout, retry, and escalation policy.
- `worker_base_template.md`: canonical worker base instructions.

The runtime harness follows this operational pattern:

1. build or verify formal Part5-to-Part6 batches;
2. prepare worker runs;
3. run the queue supervisor;
4. run independent verification and collection;
5. run final bridge and Part6 output validation.

Queue mode is the only supported active supervisor mode. Historical output
folders and branch-specific rerun folders are archive-only and must not be used
as active input or output.
