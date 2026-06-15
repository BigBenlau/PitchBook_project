# Part5 to Part6 Investor Input Builder

This folder builds a Part6-ready investor input dataset from Part5 company-to-token results.

## Goal

Use `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv` as the company universe. A company is in scope when either `token_ticker` or `token_name` is a non-empty JSON list.

The builder then finds related investors through four PitchBook paths:

1. `CompanyInvestorRelation.csv`
2. `Deal.csv` + `DealInvestorRelation.csv`
3. `InvestorInvestmentRelation.csv`
4. `FundInvestmentRelation.csv` + `FundInvestorRelation.csv`

The final output is shaped like the Part6 input contract so it can be passed to `part6_analyse_investor_capabilities/scripts/1_build_investor_capability_batches.py`.

## Outputs

Default output directory:

- `part5_to_part6/output/`

Main files:

- `part6_investor_input.csv`: one row per selected investor, using the Part6 input columns.
- `investor_candidate_audit.csv`: source-path counts and context for every selected investor.
- `token_company_universe.csv`: Part5 token-bearing company rows used as the seed set.
- `summary.json`: row counts, source-path counts, and output metadata.

## Run

```bash
python3 part5_to_part6/scripts/1_build_part6_investor_input.py
```

Then build Part6 batches from the generated input:

```bash
python3 part6_analyse_investor_capabilities/scripts/1_build_investor_capability_batches.py \
  --input-csv part5_to_part6/output/part6_investor_input.csv \
  --output-dir part5_to_part6/output/part6_batches
```

## Rule B Investor Delta

Build an investor universe using only Part5 rows where `include_rule_B = yes` and
`rule_B_token_results` is non-empty. The same four PitchBook relationship paths
used by the main builder are applied, then the result is compared by
`InvestorID` with the current `part6_investor_input.csv`.

```bash
python3 part5_to_part6/scripts/2_build_rule_b_investor_delta.py
```

Default output directory:

- `part5_to_part6/output/rule_b_delta/`

Key files:

- `rule_b_part6_investor_input.csv`: complete Rule B investor universe.
- `rule_b_only_added_part6_input.csv`: investors present in Rule B but absent
  from the current Part6 input; this is the incremental Part6 input.
- `current_only_removed_investors.csv`: investors present in the current Part6
  input but absent from Rule B; use these IDs to exclude obsolete results.
- `intersection_part6_input.csv`: investors shared by both lists.
- `investor_membership_delta.csv`: combined membership and evidence-count audit.
- `summary.json`: company, investor, intersection, added, removed, and source
  relationship counts.

Build Part6 batches only for the newly added Rule B investors:

```bash
python3 part6_analyse_investor_capabilities/scripts/1_build_investor_capability_batches.py \
  --input-csv part5_to_part6/output/rule_b_delta/rule_b_only_added_part6_input.csv \
  --output-dir part5_to_part6/output/rule_b_delta/added_part6_batches
```
