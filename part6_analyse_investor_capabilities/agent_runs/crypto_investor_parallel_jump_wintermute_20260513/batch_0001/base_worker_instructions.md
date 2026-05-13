# Part6 Worker Run

You are Worker 1 in round 1 for the part6 investor capability review.

This execution segment must run in a fresh worker context. Do not rely on memory from any previous batch or previous segment.

You are not alone in the codebase. Do not revert or overwrite edits made by others.

Batch root context:
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001

Runtime strategy references:
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/runtime/ARCHITECTURE.md
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/runtime/policy.json

The attempt runtime wrapper provides the only authoritative write scope and output file paths. Do not invent alternate write targets.

Read:
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/Plan.md
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_task_batches/crypto_investor_jump_wintermute_20260513/batch_0001.jsonl
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_runs/crypto_investor_parallel_jump_wintermute_20260513/batch_0001/tasks.jsonl
- /Users/benlao/Downloads/STANFORD_20260201/part6_analyse_investor_capabilities/agent_prompt_template.md

Task range:
- batch_file: batch_0001.jsonl
- task_count: 2
- first_task_index: 1
- first_investor: Wintermute Ventures
- last_task_index: 2
- last_investor: Jump Crypto

Method:
- Read `Plan.md` and `agent_prompt_template.md` once, then apply that workflow to each JSONL `input_row`.
- `task_index`, `investor_id`, `investor_name`, and `normalized_domain` are immutable identity fields. Copy them exactly from `tasks.jsonl`.
- For every investor, first classify archetype, crypto-native likelihood, operating-capability likelihood, search tier, capability_search_required, risk flags, and classifier reason.
- Write one classifier row per investor to the active attempt `classifier_results.csv`.
- Write incrementally. As soon as one investor is done, append both classifier and result rows.
- Use `search_tier = full`, `light`, or `skip_candidate` according to `Plan.md`.
- Use `capability_search_required = yes` for `full` and `light`; use `no` only for `skip_candidate`.
- If `search_tier = skip_candidate`, still write one completed result row with all six capability flags set to `no`, `capability_labels = []`, and a clear `capability_search_reason`.
- If `search_tier = light`, run the bounded local-first plus web-confirmation playbook.
- If `search_tier = full`, search freely, prioritizing official and primary sources.
- Do not mark `defi = yes` merely because the investor funds DeFi companies. The label requires evidence that the investor itself operates, specializes in, or explicitly markets DeFi-native capability.
- Do not mark `sub_fund = yes` merely because `LastClosedFundName` is non-empty. Reserve it for explicit feeder / umbrella / parallel fund / SPV / fund-of-funds / sub-fund structure evidence.
- Before `needs_manual_review = yes`, run one extra disambiguation pass using current official sources, aliases, former names, and exact domain probes.
- Keep the six capability columns and `capability_labels` consistent. `capability_labels` must equal the JSON list of all capability columns whose value is `yes`.
- `other_flags`, `risk_flags`, and any snapshot list fields must be valid JSON-list strings.
- `evidence_urls` must use `|`-separated absolute HTTP(S) URLs.
- `evidence_source_types` must use `|`-separated lowercase labels such as `official_site`, `official_docs`, `secondary_profile`, `news_or_blog`, or `local_csv`.
- `confidence` must be exactly `high`, `medium`, or `low`.
- If you hit a blocker or systematic ambiguity, report it back to the main agent instead of silently working around it.

Classifier CSV header:
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,risk_flags,classifier_reason

Result CSV header:
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,capability_search_reason,status,completed_at,capability_labels,otc_trading,algorithm_trading,market_making,execution_services,defi,sub_fund,other_flags,evidence_urls,evidence_source_types,evidence_summary,confidence,needs_manual_review

Final response should report:
- classifier rows written
- total data rows written
- rows with non-empty `capability_labels`
- rows with `capability_labels = []`
- rows with `capability_search_required = yes` and `capability_labels = []`
- rows with `capability_search_required = no` and `capability_labels = []`
- rows by `search_tier`
- `needs_manual_review = yes` count
- authoritative classifier file path
- authoritative results file path
- blocker count
