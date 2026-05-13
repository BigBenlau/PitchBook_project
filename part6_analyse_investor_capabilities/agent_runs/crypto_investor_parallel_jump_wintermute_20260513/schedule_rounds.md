# Part5 Worker Schedule

- workers_per_round: 1
- total_batches: 1
- total_rounds: 1

Default entrypoint is the blocking supervisor. It owns the fixed runtime flow `prepare -> launch -> mark-started -> watch -> lint -> next round` and should not exit until all requested rounds finish.

Default mode is one fresh worker per batch. Recovery may create a fresh continuation worker for the unresolved suffix, but only after a failure or explicit rerun decision.

Do not collect, merge, update checkpoint, or delete temporary run directories until the round verifier has written `verification_report.csv` and `verification_summary.md` and every non-pass row has a recorded action.

Preferred command:

```bash
python part6_analyse_investor_capabilities/scripts/5_run_round_supervisor.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513 --start-round-index <ROUND_INDEX> --round-count <ROUND_COUNT>
```

The supervisor blocks until the requested rounds complete and lint clean. Use the manual steps below only as fallback or for debugging:

Before spawning workers for a round, build the launch queue with the runtime controller. It upgrades batches into isolated attempts and chooses the right recovery mode/model for reruns:

```bash
python part6_analyse_investor_capabilities/scripts/4_manage_round_runtime.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513 --round-index <ROUND_INDEX> --prepare-launches
```

Spawn workers from `launch_queue_round_XXXX.md`, then immediately mark that round as started:

```bash
python part6_analyse_investor_capabilities/scripts/4_manage_round_runtime.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513 --round-index <ROUND_INDEX> --mark-round-started
```

While the round is running, use the runtime controller instead of raw watcher commands. It detects both startup no-row failures and partial stalls and writes `runtime_actions_round_XXXX.csv` with kill+respawn recommendations:

```bash
python part6_analyse_investor_capabilities/scripts/4_manage_round_runtime.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513 --round-index <ROUND_INDEX> --watch-round --startup-no-row-timeout-seconds 480 --partial-stall-timeout-seconds 240
```

If the runtime controller emits actions, rerun `--prepare-launches` for that same round and respawn only the affected batches or recovery attempts. Each new attempt must use a fresh worker and the previous worker should be considered closed.

Before starting the fresh verifier, run the local lint pass against the active attempt outputs. Any immutable identity drift must be fixed before verifier starts:

```bash
python part6_analyse_investor_capabilities/scripts/3_collect_results.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513 --lint-only --repair-identity-drift-in-place --fail-on-identity-drift
```

If lint or the runtime controller marks any `needs_rerun` rows in `schedule.csv` or writes a rerun artifact CSV, rerun those batches with fresh workers before starting the verifier.

After worker results are complete, collect merged results and manual-review rows:

```bash
python part6_analyse_investor_capabilities/scripts/3_collect_results.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513 --cleanup-run-artifacts
```

## Round 1

### Worker 1 - batch_0001.jsonl

```text
Use a fresh worker subagent for exactly one part6 batch attempt. Do not reuse a finished worker context for a later attempt or a later batch. Recommended model: gpt-5.4-mini, reasoning medium.

Startup requirement:
- Read only the batch-specific instructions and inputs first.
- Process the earliest pending investor immediately and write the first classifier/result rows early.
- Do not begin with repo-wide file scans, `manifest.csv` sweeps, `verification_findings.csv` lookups, or broad exploration of other batches.
- - This is the normal full-batch attempt. Own the whole batch in one fresh worker and exit after this single attempt finishes.

Read the worker instructions:
part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/attempts/attempt_0001/worker_instructions.md

Then execute the batch and write results only to:
part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/attempts/attempt_0001/classifier_results.csv
part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/attempts/attempt_0001/results.csv

```

### Round 1 Verifier

```text
Use a fresh verifier subagent for this part6 round. Recommended model: gpt-5.4-mini, reasoning high.

Read the verifier instructions:
part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/verifier_instructions_round_0001.md

Then write:
part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/verification_report_round_0001.csv
part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/verification_summary_round_0001.md

The round is not complete until every non-pass verifier row has a recorded recommended action.

```
