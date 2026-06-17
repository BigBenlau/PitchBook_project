# Part5-to-Part6 Formal Investor Bridge

This folder builds the canonical Part6 investor input universe from the current
Part5 company-to-token results.

## Goal

Use `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv` as
the only Part5 source of truth. A company is in scope only when its formal
`token_results` JSON list is non-empty.

The inherited Part5 rule is:

- include a token only when the company is an officially recognized founding
  entity, co-founding entity, or original founding organization of the
  blockchain/protocol ecosystem;
- require strong, direct, stable evidence from official, primary, or trusted
  sources;
- exclude ordinary investors, advisors, partners, vendors, customers,
  portfolio-only exposure, grants, ecosystem mentions, and generic token
  references.

The bridge expands those token-bearing companies into investor rows through
four PitchBook relationship paths:

1. `CompanyInvestorRelation.csv`
2. `Deal.csv` + `DealInvestorRelation.csv`
3. `InvestorInvestmentRelation.csv`
4. `FundInvestmentRelation.csv` + `FundInvestorRelation.csv`

The final `part6_investor_input.csv` keeps the Part6 26-column input contract
and is the only active Part6 investor universe. The current approved output has
10,353 unique investors and 346 Part6 JSONL batches. Historical branch, delta,
backup, staging, or removed-investor artifacts are not active Part6 inputs.

## Outputs

Default output directory:

- `part5_to_part6/output/`

Active output files:

- `token_company_universe.csv`: formal Part5 token-company seed rows.
- `part6_investor_input.csv`: one row per selected investor, using the Part6
  input columns.
- `investor_candidate_audit.csv`: source-path counts and relationship context
  for every selected or candidate investor.
- `summary.json`: formal company, investor, source-path, and output counts.
- `verification_report.json`: deterministic bridge verification report.
- `part6_batches/`: canonical Part6 JSONL batches, `input_investors.csv`, and
  `manifest.csv`.

Operational backups, older intermediate artifacts, and historical branch or
delta artifacts must live outside the active `output/` folder, for example
under `part5_to_part6/output_ops/`.

## Build

Build the formal investor input:

```bash
python3 part5_to_part6/scripts/1_build_part6_investor_input.py
```

Build Part6 batches from the generated input:

```bash
python3 part6_analyse_investor_capabilities/scripts/1_build_investor_capability_batches.py \
  --input-csv part5_to_part6/output/part6_investor_input.csv \
  --output-dir part5_to_part6/output/part6_batches
```

## Verify

Run the bridge verifier:

```bash
python3 part5_to_part6/scripts/2_verify_formal_bridge_outputs.py
```

The verifier checks that:

- Part5 rows with non-empty `token_results` exactly match
  `token_company_universe.csv` by company ID set.
- `part6_investor_input.csv` has unique `InvestorID` values.
- `part6_batches/manifest.csv`, `part6_batches/input_investors.csv`, and all
  batch JSONL rows align with `part6_investor_input.csv`.
- `summary.json` agrees with generated row counts.
- the optional Part6 reference result has the same investor ID set and order as
  the active bridge output.

To compare against a read-only Part6 reference result, pass:

```bash
python3 part5_to_part6/scripts/2_verify_formal_bridge_outputs.py \
  --part6-reference-results-csv <path-to-reference-results.csv>
```

The reference comparison checks investor ID set and order only. It does not
modify Part6 results.
