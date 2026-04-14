# Part5: Company-to-Token Harness Plan

## 0. Required Read Order

Every part5 run, worker instruction, prompt update, script update, or result validation must treat this file as the controlling contract.

Before using the part5 skill or launching any worker:

1. Read this `Plan.md`.
2. Read `part5_analyse_company_to_token/agent_prompt_template.md`.
3. Use the scripts in `part5_analyse_company_to_token/scripts/` as the execution harness.

If a prompt, worker instruction, skill file, or script behavior conflicts with this plan, this plan wins unless the user explicitly changes the plan.

## 1. Goal

Input:

- `part2_build_crypto_candidate/output/crypto_company.csv`

Output:

- `part5_analyse_company_to_token/agent_runs/crypto_company/classifier_results.csv`
- `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- `part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`
- `part5_analyse_company_to_token/agent_runs/crypto_company/checkpoint.json`

The task is to map each company to zero, one, or multiple crypto projects and fungible token tickers.

The task is not:

- mapping NFT collections without fungible tokens
- general crypto-company classification as a final product
- exchange classification as a final product
- listing venue/date research
- investment or market analysis

The final result must contain exactly one row per company. A company with multiple projects or multiple fungible tokens still has one row, with list-valued fields.

## 2. Harness Architecture

The part5 process is a harness around LLM workers. Workers are execution units, not the source of truth for data integrity.

The pipeline has three agent stages:

1. Company relevance classifier and search router.
2. Project/token search worker.
3. Round-end verification subagent.

Pipeline:

1. Extract compact company inputs from `crypto_company.csv`.
2. Build fixed-size JSONL batches.
3. Run a classifier/router pass for every company.
4. Write classifier/router decisions to `classifier_results.csv`.
5. Route each company to a search tier: `full`, `light`, or `skip_candidate`.
6. Run full project/token search only for `full` rows.
7. Run a bounded lightweight token-existence check for `light` rows.
8. For `skip_candidate` rows, write a completed no-token row only when the classifier/router reason clearly explains why a token search budget is not justified.
9. Each worker writes one `results.csv` for its assigned batch.
10. Collector performs structural validation on classifier/router and worker outputs.
11. Before the round ends, spawn a fresh verifier subagent to independently check token correctness for the round.
12. The verifier reads the classifier/router outputs as part of its review and checks whether each company's `token_ticker` list has omissions, extra tickers, wrong project mapping, or non-fungible/stock ticker contamination.
13. Main agent reviews the verifier report, fixes rows or marks manual review/rerun decisions.
14. Collector or coordinator merges verified clean rows into final `results.csv`.
15. Extract `needs_manual_review.csv`.
16. Update `checkpoint.json`.
17. Delete temporary worker run directories after their rows are merged.

Scripts:

- `scripts/1_build_company_token_batches.py`
- `scripts/2_prepare_worker_runs.py`
- `scripts/3_collect_results.py`

Recommended batch/run parameters:

- `batch_size = 30`
- `workers = 5`
- one operational block = 3 rounds = 15 batches = 450 companies

### Model Selection Contract

Default model policy:

- Use `gpt-5.4-mini` for high-volume company classification.
- Use `gpt-5.4-mini` for normal project/token search workers.
- Use `gpt-5.4-mini` for first-pass round-end verification.
- Escalate only difficult cases to `gpt-5.4`.
- Use `gpt-5.3-codex` for harness code, script edits, prompt-template edits, collector changes, and debugging, not for routine company/token research.

Reasoning effort:

- Classifier: `gpt-5.4-mini`, `low` or `medium`.
- Normal project/token search: `gpt-5.4-mini`, `medium`.
- Ambiguous project/token search: `gpt-5.4-mini`, `high`.
- Round-end verifier: `gpt-5.4-mini`, `high`.
- Escalation verifier or rerun: `gpt-5.4`, `high`.
- Harness engineering and code changes: `gpt-5.3-codex`, `medium` or `high` depending on complexity.

Escalate from `gpt-5.4-mini` to `gpt-5.4` when any of these are true:

- verifier and worker disagree on token tickers
- project has multiple brands, former names, foundations, DAOs, or acquired entities
- company appears to map to multiple projects or multiple fungible tokens
- source evidence conflicts across official docs, token data pages, explorers, or secondary sources
- skipped-search decision would exclude a company with medium or high crypto project likelihood
- previous round produced a systematic error pattern

Do not use `gpt-5.4` for every row by default. The expected workload is 17,000+ companies, so the cost-effective path is:

1. broad pass with `gpt-5.4-mini`
2. mandatory fresh verifier with `gpt-5.4-mini`
3. targeted reruns/escalations with `gpt-5.4`

Do not use `gpt-5.3-codex` as the default research worker unless the task includes substantial repo editing, script execution, or long-running coding-agent behavior. For token research, its coding optimization and higher output cost make it less cost-effective than `gpt-5.4-mini`.

## 3. Input Contract

The only source dataset for part5 is:

- `part2_build_crypto_candidate/output/crypto_company.csv`

The extracted agent input should keep fields useful for:

- classifying company business type
- explaining why the company was included in `crypto_company.csv`
- detecting whether the company likely has a crypto project
- identifying official domains, products, whitepapers, docs, or token pages
- disambiguating company, brand, project, and token names

Required fields:

- `task_index`
- `CompanyID`
- `CompanyName`
- `CompanyAlsoKnownAs`
- `CompanyFormerName`
- `CompanyLegalName`
- `Website`
- `normalized_domain`
- `ParentCompany`
- `Exchange`
- `Ticker`
- `Verticals`
- `EmergingSpaces`
- `Description`
- `Keywords`
- `MatchedKeywords`
- `MatchedColumns`

Optional fields:

- `HQLocation`
- `HQCountry`

Useful but bounded context:

- fields explaining why the row is crypto/blockchain-related
- fields indicating official docs, whitepaper, protocol, token, or product names, if present
- concise relation context only when it directly explains why the company entered the crypto candidate set

Do not pass these fields to workers by default:

- financing, valuation, revenue, EBITDA, debt, investor, and deal fields
- address, phone, fax, email, and contact fields
- social media URLs unless needed to identify the official project
- PitchBook profile metadata that does not help classification or project mapping
- long relation descriptions that overwhelm the prompt

Text limits:

- `Description`: max 700 characters
- `Keywords`: max 300 characters
- any relation/explanation context: max 300 characters

`normalized_domain` must be derived from `Website` when not present. Remove `www.` and lower-case the host.

## 4. Stage 1: Company Relevance Classifier and Search Router

Every company must first pass through a classifier/router agent before project/token search.

The classifier/router answers:

- What type of company is this?
- Why is it in `crypto_company.csv`?
- Is it likely connected to a crypto project that could have a fungible token?
- What search tier should be used so the harness spends enough tokens to find likely tickers without wasting tokens on clearly out-of-scope companies?

The classifier/router is a routing gate, not a final skip gate. It must not decide the final `token_ticker` value. It assigns a search budget and records why that budget is appropriate.

Classifier/router output artifact:

- `agent_runs/crypto_company/classifier_results.csv`

`classifier_results.csv` must use this header:

```csv
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,search_tier,project_search_required,risk_flags,classifier_reason
```

Classifier/router output fields:

- `company_type`
- `crypto_project_likelihood`
- `search_tier`
- `project_search_required`
- `risk_flags`
- `classifier_reason`

Allowed `company_type` values:

- `protocol_or_network`
- `dapp_or_product`
- `exchange_or_broker`
- `wallet_or_custody`
- `mining_or_validator`
- `infrastructure_or_data`
- `security_or_compliance`
- `service_provider`
- `investment_or_holdings`
- `media_or_education`
- `gaming_or_nft`
- `traditional_business`
- `unclear`

Allowed `crypto_project_likelihood` values:

- `high`
- `medium`
- `low`
- `none`
- `unclear`

Allowed `project_search_required` values:

- `yes`
- `no`

Allowed `search_tier` values:

- `full`
- `light`
- `skip_candidate`

Use `search_tier = full` when any of these are true:

- the company appears to operate a protocol, network, dapp, exchange, wallet, tokenized product, or blockchain-native product
- the row mentions a project, token, whitepaper, docs, protocol, chain, app, DAO, or ecosystem
- company names, aliases, former names, or website suggest a project identity that may differ from the legal company name
- the classifier cannot confidently exclude project/token relevance

Use `search_tier = light` when the company is crypto-adjacent or low-likelihood but still has enough signal that a cheap token-existence check is justified, for example:

- service provider, infrastructure, media, mining, validator, custody, analytics, security, compliance, NFT, gaming, or investment-related company with some crypto/project context
- official domain, aliases, former names, or description contain token/project-like terms, but the row does not justify a full deep search
- source context is thin, ambiguous, or likely stale

Use `search_tier = skip_candidate` only when the company is clearly out of scope for fungible token mapping and even a lightweight token-existence check is not justified, for example:

- traditional business with only incidental crypto keyword matches
- consulting, legal, accounting, recruitment, marketing, events, or generic service provider with no project/product signal
- investor, holding company, VC, or accelerator with no owned crypto project signal
- media, education, or research company with no owned crypto project signal
- mining, validator, custody, analytics, security, or compliance company with no owned token/project signal
- NFT-only, collectible-only, or gaming asset company with no fungible token signal

Set `project_search_required = yes` for `search_tier = full` or `search_tier = light`.

Set `project_search_required = no` only for `search_tier = skip_candidate`.

`risk_flags` should be a JSON list string using short labels when applicable, for example:

- `alias_or_former_name`
- `token_keyword`
- `protocol_keyword`
- `nft_or_gaming`
- `stock_ticker_present`
- `domain_missing`
- `brand_project_mismatch`
- `multiple_project_signal`
- `thin_source_context`

Conservative rule:

- If the classifier/router is unsure, use `search_tier = full`.
- If token usage is a concern but project/token relevance cannot be excluded, use `search_tier = light`, not `skip_candidate`.
- `skip_candidate` requires a clear `classifier_reason` grounded in company type and source row context.
- The classifier/router must keep `classifier_reason` short. Do not spend tokens writing long explanations.

## 5. Stage 2: Project/Token Search Worker

The project/token search worker runs according to the classifier/router `search_tier`.

Search tiers:

- `full`: use normal project/token search depth.
- `light`: use a bounded token-existence check. Prefer the source row, official domain when available, exact company/project aliases, and major token data pages. Stop after the bounded check when no token/project signal is found.
- `skip_candidate`: do not run full or light search. Write a completed no-token row from the classifier/router decision only when the `classifier_reason` is specific enough to justify the skip.

Worker constraints:

- Read only its assigned `tasks.jsonl` / batch JSONL.
- Write only its assigned run directory.
- Write exactly one row per task.
- Do not modify final result files directly.
- Do not modify another worker's run directory.
- Do not rewrite source batches or input dataset.

Full search policy:

- Workers may search freely.
- Workers are not limited to official sites, CoinGecko, or CoinMarketCap.
- Use search to identify the correct company, project, product, protocol, and token mapping.
- Prefer primary sources when available, but allow reputable secondary sources for discovery and corroboration.
- Search depth should be proportional to classifier likelihood and ambiguity.

Light search policy:

- Keep token usage low.
- Use exact names, aliases, former names, and normalized domain before broad discovery queries.
- Prefer official site/domain and exact-match token data pages.
- Do not browse broadly through generic secondary sources unless the first-pass evidence shows a possible owned project or token.
- If the light check finds a plausible token or project signal, upgrade the row to full search or mark `needs_manual_review = yes` if the round budget cannot support a full rerun.

Light query playbook:

1. exact-domain token probe using `normalized_domain` or official host
2. exact `CompanyName` token/project probe
3. exact alias probe from `CompanyAlsoKnownAs`
4. exact former-name probe from `CompanyFormerName`
5. exact CoinGecko/CoinMarketCap project or token page probe

Light-tier requirements:

- before finalizing `token_ticker = []`, run the exact-domain token probe
- if any probe produces a plausible company -> project -> token signal, reroute to `full` or mark `needs_manual_review = yes`
- do not treat light search as a vague skim; it is a fixed low-cost probe sequence

Full query playbook:

1. company identity stage: confirm official domain, aliases, former names, and current brand
2. project discovery stage: identify the owned project, protocol, app, or tokenized product
3. token confirmation stage: confirm fungible token name, ticker, and token page

Full-tier requirements:

- use at least one primary source for company identity, one for project identity, and one for token identity
- before finalizing `token_ticker = []`, run the exact-domain token probe
- a token page alone is not enough unless it maps back to the company or owned project

Recommended source priority:

1. Official website, docs, whitepaper, litepaper, blog, FAQ, governance forum, or announcement.
2. Token data pages such as CoinGecko and CoinMarketCap.
3. Project documentation, GitHub, explorer, exchange pages, audited docs, or foundation pages.
4. Reputable secondary sources only when needed for disambiguation.

Do not use weak evidence alone:

- generic search snippets
- social media posts without stronger corroboration
- copied token lists without project mapping
- token-like strings that do not map back to the company/project

## 6. Output Schema

All worker and final result CSVs must use this exact v2 header:

```csv
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,project_search_required,project_search_reason,project_name,project_url,status,completed_at,token_ticker,token_name,token_url,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review
```

Column rules:

- `task_index`: integer, unique, continuous within completed range
- `company_id`: PitchBook `CompanyID`
- `company_name`: source `CompanyName`
- `normalized_domain`: normalized official domain when available
- `company_type`: classifier output
- `crypto_project_likelihood`: classifier output
- `project_search_required`: `yes` or `no`
- `project_search_reason`: short classifier explanation
- `project_name`: JSON list string
- `project_url`: JSON list string
- `status`: must be `completed`
- `completed_at`: ISO timestamp when available; blank is allowed for worker output
- `token_ticker`: JSON list string
- `token_name`: JSON list string
- `token_url`: JSON list string
- `has_token_evidence`: short evidence summary
- `evidence_urls`: `|`-separated URLs
- `evidence_source_types`: `|`-separated source type labels
- `confidence`: `high`, `medium`, or `low`
- `needs_manual_review`: `yes` or `no`

Confidence and review are separate decisions:

- `confidence = high`: evidence clearly maps company or owned project to the token, typically with official or strong primary support
- `confidence = medium`: evidence is sufficient to merge, but is not as strong or complete as `high`
- `confidence = low`: evidence is weak, thin, or incomplete
- `needs_manual_review` must not be derived from `confidence` alone
- `medium` confidence rows may still merge with `needs_manual_review = no` when the mapping is stable and verifier review is clean

No-token or skipped-search case:

- `token_ticker = []`
- `token_name = []`
- `token_url = []`
- `project_name` and `project_url` may be `[]`
- `project_search_reason` must explain the final no-token decision: `full`/`light` search found no reliable token, or `skip_candidate` did not justify token search budget
- for `skip_candidate` rows, `project_search_reason` should be derived from `classifier_results.csv` `classifier_reason`

Multi-project or multi-token case:

- still one company row
- put all project names in `project_name` as a JSON list string
- put all tickers in `token_ticker` as a JSON list string, for example `["ANGLE","EURA","USDA"]`
- list-valued columns should align by index whenever possible

CSV safety:

- JSON list columns must be valid JSON after CSV parsing
- free-text fields containing commas, quotes, or newlines must be CSV-quoted
- malformed CSV rows must be repaired or rejected by validation before merging

## 7. Evidence Contract

Positive fungible token evidence requires at least one source that clearly maps:

- company or owned project
- to a crypto project
- to a fungible token name and ticker

Good evidence includes:

- official source explicitly names the token/ticker
- CoinGecko, CoinMarketCap, or similar token data page clearly maps to the company/project
- project docs, whitepaper, explorer, governance docs, or foundation materials identify the token
- reputable secondary sources corroborate the mapping when primary sources are incomplete

Do not treat these as token evidence:

- `crypto`, `blockchain`, `web3`, `DeFi`, or `exchange` keywords alone
- source `Verticals`, `Keywords`, `MatchedKeywords`, or `MatchedColumns` alone
- stock `Exchange` or stock `Ticker`
- relation-derived text about similar or competitor companies
- NFT collection symbols unless they are also fungible token tickers
- token-like strings that do not map back to the company/project

When sources conflict:

- prefer official and primary sources
- otherwise set `needs_manual_review = yes`
- do not invent a ticker to resolve conflict

When no reliable source confirms a fungible token:

- use `token_ticker = []`
- do not output `no`
- do not output `unknown`

## 8. Manual Review Rules

Set `needs_manual_review = yes` when any of these are true:

- classifier decision is uncertain but project search was skipped
- company-to-project mapping is ambiguous
- token page exists but does not clearly map back to the company
- sources disagree
- official site is unavailable, dead, or too thin to confirm mapping
- company has multiple brands, former names, subsidiaries, or project names that could change the mapping
- company appears NFT-only or gaming-related but may also have a fungible token
- evidence depends on a weak similarity between company name and token/project name
- CSV row required repair during collection

Do not set `needs_manual_review = yes` only because `confidence` is `medium` or `low`.
Use manual review only for unresolved ambiguity, unresolved evidence gaps, or unresolved verifier concerns.

Manual review rows are not failures. They are the audit queue:

- `agent_runs/crypto_company/needs_manual_review.csv`

## 9. Round-End Verification Subagent

Every round must end with a fresh verification subagent. This is mandatory, not optional.

Fresh verifier rule:

- Spawn a new verifier subagent for each round.
- Do not reuse the project/token search worker as its own verifier.
- Do not reuse a verifier from a previous round.
- The verifier must read this `Plan.md` before checking results.
- The verifier must receive the round `classifier_results.csv` files as part of its review input.
- The verifier must receive the round input tasks, worker `results.csv`, and any available evidence URLs.

Verifier scope:

- Re-check whether each company has zero, one, or multiple fungible token tickers.
- Check whether classifier/router `search_tier` was too conservative for the row.
- Detect missing tickers in `token_ticker`.
- Detect extra or over-reported tickers in `token_ticker`.
- Detect wrong company-to-project mapping.
- Detect cases where an NFT collection symbol, stock ticker, chain name, or product code was wrongly reported as a fungible token ticker.
- Detect skipped-search rows where project/token search should have been required.
- Detect rows where multiple projects or multiple token tickers should have been represented as a JSON list.

Verifier search policy:

- The verifier may search freely.
- The verifier should use independent search queries, not only the worker's evidence URLs.
- The verifier should focus on disagreement, omissions, and over-reporting rather than rewriting every row from scratch.
- The verifier should prioritize rows with token-positive output, skipped project search, low or medium confidence, ambiguous brands, and multiple-token signals.

Verifier output:

- `verification_report.csv`
- `verification_summary.md`

Store verifier outputs in the current round run directory. If temporary run directories are deleted after merge, preserve the verifier summary or copy verifier reports into the final audit location before deletion.

`verification_report.csv` should include:

```csv
task_index,company_id,company_name,classifier_search_tier,worker_token_ticker,verifier_search_tier,verifier_token_ticker,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

Allowed `verdict` values:

- `pass`
- `suspected_missing_token`
- `suspected_extra_token`
- `wrong_project_mapping`
- `non_fungible_or_stock_ticker`
- `search_tier_too_conservative`
- `search_should_not_have_been_skipped`
- `insufficient_evidence`

Allowed `recommended_action` values:

- `accept_worker_row`
- `edit_row`
- `mark_manual_review`
- `rerun_company`
- `rerun_batch`
- `update_prompt_or_process`

Authoritative verifier rule:

- `edit_row` is authoritative only when `corrected_result_row_json` is present and valid
- `corrected_result_row_json` must be a full JSON object using the exact result-row schema
- collector applies the corrected row directly if it passes validation

Main agent responsibilities after verifier report:

- Review every non-`pass` verifier row before the round is considered complete.
- If the verifier finds a clear worker error, update the row or rerun the company/batch before merging.
- If the verifier finds uncertainty but not a clear correction, set `needs_manual_review = yes`.
- If the verifier returns `pass` with `accept_worker_row`, set `needs_manual_review = no` for that row unless another unresolved manual-review condition still exists.
- If the verifier returns `edit_row` and `corrected_result_row_json` passes validation, collector should apply that corrected row as the authoritative merged row.
- If the verifier returns `mark_manual_review`, set `needs_manual_review = yes`.
- If the verifier identifies a systematic cause, update the operation flow before the next round.
- Report the detected cause back to the main agent context, including whether it came from classification, search, evidence interpretation, CSV formatting, or prompt ambiguity.

Systematic causes that require operation-flow updates:

- classifier skips relevant project companies
- workers miss obvious multiple-token projects
- workers confuse stock tickers with token tickers
- workers report NFT-only symbols as fungible tokens
- workers over-trust weak secondary sources
- workers fail to use company aliases, former names, or official domains for disambiguation
- CSV list formatting causes token loss or merge errors

Round completion gate:

- A round is not complete until `verification_report.csv` and `verification_summary.md` exist.
- A round is not complete until every verifier non-`pass` row has a recorded action.
- Do not update `checkpoint.json` past the round until verifier issues are resolved or explicitly moved to `needs_manual_review.csv`.
- Do not delete temporary worker run directories until verification is complete.

## 10. Checkpoint and Resume Contract

The only resume authority is:

- `agent_runs/crypto_company/checkpoint.json`

Required checkpoint fields:

- `completed_rows_in_final_results`
- `completed_through_task_index`
- `completed_through_batch`
- `next_batch_to_process`
- `next_task_index_to_process`
- `batch_size`
- `workers`
- `total_batches`
- `classifier_results_csv`
- `final_results_csv`
- `manual_review_csv`

Resume rule:

- start from `next_batch_to_process`
- never rerun batches already merged into final results unless explicitly requested
- if a temporary worker run exists but is not merged, validate it before deciding whether to merge or discard

After merging a run:

- update checkpoint
- regenerate `needs_manual_review.csv`
- preserve or summarize verifier reports for audit
- delete temporary worker run directories unless the user asks to keep them for audit

## 11. Validation Gates

Validation must happen before rows are merged into final results.

Structural checks:

- classifier results CSV header exactly matches the classifier/router schema
- classifier results row count equals expected task count for the completed range
- every classifier result has one allowed `search_tier`
- classifier `risk_flags` parses as a JSON list string
- classifier `project_search_required` matches `search_tier`: `yes` for `full` or `light`, `no` for `skip_candidate`
- CSV header exactly matches the v2 schema
- row count equals expected task count
- no duplicate `task_index`
- task indexes are continuous for the completed range
- every list-valued column parses as JSON list
- `status = completed`
- `company_type` uses the allowed values
- `crypto_project_likelihood` uses the allowed values
- `project_search_required` in `yes|no`
- `confidence` in `high|medium|low`
- `needs_manual_review` in `yes|no`

Evidence checks:

- if `token_ticker != []`, then `token_url` or `evidence_urls` must be non-empty
- `evidence_source_types` must identify the source categories used
- token-positive rows must have evidence that maps company/project to token
- stock ticker must not be used as crypto token evidence
- list-valued token fields should align by index where possible
- `project_search_required = no` rows must have a non-empty `project_search_reason`

Classifier checks:

- all companies have classifier fields populated
- every worker row has a matching `classifier_results.csv` row
- worker `company_type`, `crypto_project_likelihood`, and `project_search_required` must match the classifier/router result unless the row records an explicit reroute reason
- `search_tier = skip_candidate` rows are sampled more heavily because they are search-budget skipping decisions
- `skip_candidate` rows with `crypto_project_likelihood` of `medium`, `high`, or `unclear` are invalid and must be rerouted to `full` or `light`
- low-confidence skipped rows must be marked `needs_manual_review = yes`

Verifier checks:

- each round has a fresh `verification_report.csv`
- each round has a `verification_summary.md`
- every non-`pass` verifier row has a recorded action
- missing-token and extra-token findings are resolved before checkpoint update
- verifier-identified systematic causes are reported back to the main agent context

Checkpoint checks:

- final row count equals `completed_rows_in_final_results`
- max task index equals `completed_through_task_index`
- `next_task_index_to_process = completed_through_task_index + 1`
- `next_batch_to_process = completed_through_batch + 1`

Quality checks:

- all `needs_manual_review = yes` rows go to `needs_manual_review.csv`
- sample token-positive rows
- sample `token_ticker = []` rows
- review all rows where company name and project/token name differ materially
- review all rows where project search was skipped
- review all verifier non-`pass` rows

## 12. Accuracy Review After a Run

After each round, before checkpoint update or round closure:

1. Run collector validation.
2. Confirm `classifier_results.csv` exists and covers every task in the round.
3. Confirm classifier `search_tier` and `project_search_required` values are consistent.
4. Confirm JSON list parse failures are zero.
5. Confirm row count increased by expected count.
6. Confirm no duplicate task indexes.
7. Spawn a fresh verifier subagent for the round.
8. Verify missing, extra, and wrongly mapped `token_ticker` values.
9. Resolve every verifier non-`pass` row by editing, rerunning, or marking manual review.
10. Inspect all `needs_manual_review = yes` rows.
11. Spot-check a sample of token-positive rows.
12. Spot-check a sample of `token_ticker = []` rows.
13. Spot-check skipped-search rows.
14. Update checkpoint only after verification is complete.
15. Remove temporary run directories only after verification is complete.

Suggested sample checks:

- 100% of manual review rows
- 10% of token-positive rows per block
- 5% of `project_search_required = no` rows per block
- 2% of `token_ticker = []` rows per block
- all rows with multiple token tickers
- all rows where `confidence = high` but evidence is only secondary sources
- 100% of verifier non-`pass` rows

## 13. Failure Handling

If worker output is malformed:

- do not merge directly
- try deterministic CSV repair only for known quoting issues
- if repair changes column positions, keep `needs_manual_review = yes`
- if repair is unsafe, rerun the batch

If a worker writes fewer or more rows than expected:

- do not merge
- inspect the worker result
- rerun the batch if necessary

If a batch was partially completed:

- keep temporary run directory
- do not update final checkpoint past that batch
- resume from the same batch after repair

If the classifier/router assigns too many companies to `skip_candidate`:

- audit `skip_candidate` rows by company type and risk flags
- lower the `skip_candidate` threshold
- reroute affected batches to `light` or `full`
- rerun affected batches with `project_search_required = yes`

If the verifier finds missing or extra token tickers:

- do not merge the affected rows as-is
- identify whether the root cause is classifier/router tiering, search miss, source ambiguity, evidence misread, or CSV formatting
- edit the affected row only when the correction is clearly supported
- otherwise mark `needs_manual_review = yes` or rerun the company/batch
- update prompt, worker instruction, classifier/router threshold, or validation rule when the same error pattern can recur

## 14. Current Operating State

As of the latest completed run:

- classifier result path: `part5_analyse_company_to_token/agent_runs/crypto_company/classifier_results.csv`
- final result path: `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- manual review path: `part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`
- checkpoint path: `part5_analyse_company_to_token/agent_runs/crypto_company/checkpoint.json`
- resume from the batch recorded in `checkpoint.json`

Do not infer current progress from temporary worker folders. Temporary folders may be deleted after merge.

Existing pre-v2 results should be treated as legacy output. Before running new batches under this plan, update `agent_prompt_template.md`, worker instructions, and collector validation to the v2 schema.
