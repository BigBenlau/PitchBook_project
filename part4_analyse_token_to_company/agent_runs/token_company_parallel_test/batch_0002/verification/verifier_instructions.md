# Part4 Verifier Run

You are the fresh verifier for `batch_0002` in the Part4 token-to-company harness.

Read:
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/Plan.md
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/pipeline.md
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/agent_runs/token_company_parallel_test/batch_0002/merged_input.csv
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/agent_runs/token_company_parallel_test/batch_0002/token_evidence_sentences.csv
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/agent_runs/token_company_parallel_test/batch_0002/founder_company_validated.csv
- /Users/benlao/Downloads/STANFORD_20260201/part4_analyse_token_to_company/agent_runs/token_company_parallel_test/batch_0002/founder_company_review_queue.csv

Verifier goals:
- detect missing founders / related companies / orgs
- detect over-reported entities
- detect wrong entity typing
- flag weak-evidence rows that should remain in review
- flag rows that should escalate to Layer 3 fallback

Required CSV header for `verification_report.csv`:
row_index,token_name,worker_founder_people,worker_related_companies,worker_foundation_or_orgs,verifier_founder_people,verifier_related_companies,verifier_foundation_or_orgs,verdict,error_type,error_reason,evidence_notes,recommended_action
