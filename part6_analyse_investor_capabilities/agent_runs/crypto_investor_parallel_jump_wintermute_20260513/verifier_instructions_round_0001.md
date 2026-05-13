# Part6 Round-End Verifier

You are a fresh verifier subagent for part6 round 1.

You are not the worker that produced these rows. Re-check independently.

Exclusive write scope:
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513

Read first:
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/Plan.md
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_prompt_template.md

Round task ranges:
- part6_analyse_investor_capabilities/agent_task_batches/crypto_investor_jump_wintermute_20260513/batch_0001.jsonl: task_index 1 to 2

Input task files:
- part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/tasks.jsonl

Classifier result files:
- part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/attempts/attempt_0001/classifier_results.csv

Worker result files:
- part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/attempts/attempt_0001/results.csv

Task:
- Independently check whether each investor's `capability_labels` JSON list is correct.
- Read the classifier/router result for every row before judging the worker result.
- Check whether `search_tier` was too conservative for the row.
- Check whether any `skip_candidate` decision was unreasonable or should have been routed to `light` or `full`.
- Detect missing capability labels.
- Detect extra or unsupported capability labels.
- Detect wrong investor archetype or investor/business mapping.
- Detect `capability_search_required = no` rows that should have been searched.
- Focus on capability-positive rows, skipped-search rows, ambiguous brands, low/medium confidence rows, and mixed operating/investing profiles.
- If you detect a systematic issue pattern, report it explicitly for the main agent using one of these cause labels when applicable: `classification`, `search`, `evidence_interpretation`, `csv_formatting`, `prompt_ambiguity`, `run_harness`, `other`.

Search policy:
- Search freely.
- Use independent queries, not only worker evidence URLs.
- Prefer official and primary sources when available.
- Use secondary sources only for corroboration or disambiguation.

Write:
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/verification_report_round_0001.csv
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/verification_summary_round_0001.md

CSV header:
task_index,investor_id,investor_name,classifier_search_tier,worker_capability_labels,verifier_search_tier,verifier_capability_labels,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json

Every row in the round should appear in `verification_report.csv`. Use `verdict = pass` when the worker row is acceptable.

Allowed verdict values:
- pass
- suspected_missing_capability
- suspected_extra_capability
- wrong_archetype_or_mapping
- search_tier_too_conservative
- search_should_not_have_been_skipped
- insufficient_evidence

Allowed recommended_action values:
- accept_worker_row
- edit_row
- mark_manual_review
- rerun_investor
- rerun_batch
- update_prompt_or_process

Authoritative correction rule:
- If `recommended_action = edit_row`, fill `corrected_result_row_json` with a full JSON object using the exact result-row schema.
- The corrected JSON must contain all result columns, not only the edited fields.
- The collector will apply that corrected row directly if it passes validation.

`verification_summary.md` must include:
- checked row count
- pass count
- non-pass count
- suspected missing token count
- suspected extra token count
- wrong mapping count
- skipped-search concern count
- systematic causes found
- recommended process updates
- explicit feedback items for the main agent when a rerun, prompt change, or process change is recommended
