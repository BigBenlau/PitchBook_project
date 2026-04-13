# Part5 Worker Schedule

- workers_per_round: 1
- total_batches: 1
- total_rounds: 1

Use one round at a time. Start the listed workers in parallel, wait for all to finish, then start the fresh verifier for that same round.

Do not collect, merge, update checkpoint, or delete temporary run directories until the round verifier has written `verification_report.csv` and `verification_summary.md` and every non-pass row has a recorded action.

After worker results are complete, collect merged results and manual-review rows:

```bash
python part5_analyse_company_to_token/scripts/3_collect_results.py --runs-dir /Users/benlao/Downloads/STANFORD_20260201/part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2
```

## Round 1

### Worker 1 - batch_0001.jsonl

```text
Use a worker subagent for this part5 batch. Recommended model: gpt-5.4-mini, reasoning medium.

Read the worker instructions:
part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/instructions.md

Then execute the batch and write results only to:
part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/classifier_results.csv
part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/batch_0001/results.csv

```

### Round 1 Verifier

```text
Use a fresh verifier subagent for this part5 round. Recommended model: gpt-5.4-mini, reasoning high.

Read the verifier instructions:
part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/round_0001_verification/verifier_instructions.md

Then write:
part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/round_0001_verification/verification_report.csv
part5_analyse_company_to_token/agent_runs/crypto_company_batch_0001_v2/round_0001_verification/verification_summary.md

The round is not complete until every non-pass verifier row has a recorded recommended action.

```
