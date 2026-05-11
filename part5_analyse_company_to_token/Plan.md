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

Final-output authority:

- `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv` is the only final search-result authority.
- Every company whose search is completed and validated must be merged into that global `results.csv`.
- Every row with `needs_manual_review = yes` must also be written into `part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`.
- Batch-local run directories, attempt CSVs, round verifier outputs, and rerun windows are intermediate artifacts only. They may be deleted after merge.
- A round is not operationally complete until validated rows have been promoted into the global final outputs above.

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
14. Collector or coordinator merges verified clean rows into `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`.
15. Collector regenerates `part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv` from the merged final rows.
16. Only after that promotion step may the run be treated as complete.
17. Update checkpoint.
18. Delete temporary worker run directories after their rows are merged into the global final outputs.

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
- Keep worker research on `gpt-5.4-mini` even for 30-company batches by rotating fresh segment attempts inside the batch instead of stretching one worker context across the full batch.
- Use `gpt-5.4-mini` for first-pass round-end verification.
- Escalate only difficult cases to `gpt-5.4` outside the standard worker path. The default worker path remains `gpt-5.4-mini`.
- Use `gpt-5.3-codex` for harness code, script edits, prompt-template edits, collector changes, and debugging, not for routine company/token research.

Reasoning effort:

- Classifier: `gpt-5.4-mini`, `low` or `medium`.
- Normal project/token search: `gpt-5.4-mini`, `medium`.
- Ambiguous project/token search: `gpt-5.4-mini`, `high`.
- Round-end verifier: `gpt-5.4-mini`, `high`.
- Escalation verifier: `gpt-5.4`, `high`.
- Worker rerun with fresh segment handoff: `gpt-5.4-mini`, `high` or `xhigh`.
- Harness engineering and code changes: `gpt-5.3-codex`, `medium` or `high` depending on complexity.

Escalate from `gpt-5.4-mini` to `gpt-5.4` when any of these are true in verifier or manual escalation paths:

- verifier and worker disagree on token tickers
- project has multiple brands, former names, foundations, DAOs, or acquired entities
- company appears to map to multiple projects or multiple fungible tokens
- source evidence conflicts across official docs, token data pages, explorers, or secondary sources
- skipped-search decision would exclude a company with medium or high crypto project likelihood
- previous round produced a systematic error pattern

Do not use `gpt-5.4` for every row by default. The expected workload is 17,000+ companies, so the cost-effective path is:

1. broad pass with `gpt-5.4-mini`
2. batch-internal segment rotation with fresh `gpt-5.4-mini` workers
3. mandatory fresh verifier with `gpt-5.4-mini`
4. targeted verifier/manual escalations with `gpt-5.4`

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

Do not invent finer-grained `company_type` labels in outputs. If a company looks like `defi_protocol`, `nft_marketplace`, `gaming_platform`, `crypto_brokerage_platform`, or similar, map it back to the nearest allowed value above.

Use `search_tier = full` when any of these are true:

- the company appears to operate a protocol, network, dapp, exchange, wallet, tokenized product, or blockchain-native product
- the row mentions a project, token, whitepaper, docs, protocol, chain, app, DAO, or ecosystem
- company names, aliases, former names, or website suggest a project identity that may differ from the legal company name
- the classifier cannot confidently exclude project/token relevance

Use `search_tier = light` when the company is crypto-adjacent or low-likelihood but still has enough signal that a cheap token-existence check is justified, for example:

- service provider, infrastructure, media, mining, validator, custody, analytics, security, compliance, NFT, gaming, or investment-related company with some crypto/project context
- official domain, aliases, former names, or description contain token/project-like terms, but the row does not justify a full deep search
- source context is thin, ambiguous, or likely stale
- the company is crypto-native infrastructure, validator, node, relayer, builder, MEV, rollup, or chain tooling with clear protocol-facing product context but no immediate token evidence
- the row already contains rewards, governance, staking, tokenomics, wrapper, bridge, or liquid-staked language, but the first pass has not yet confirmed a stable ticker

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
- Crypto-native infrastructure or protocol-facing operations must not be routed to `skip_candidate` only because no token is obvious from the first read; these rows require at least `light`.
- `skip_candidate` requires a clear `classifier_reason` grounded in company type and source row context.
- The classifier/router must keep `classifier_reason` short. Do not spend tokens writing long explanations.
- former-name continuity, token-family sweep, and secondary-only linkage are fixed follow-up rules, not optional verifier cleanups.

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
- Write rows incrementally instead of dumping the full batch only at the end.
- A healthy worker should create its first classifier/result rows early; if both CSVs stay header-only for 60-90 seconds, the harness should treat that as a startup failure.
- Do not modify final result files directly.
- Do not modify another worker's run directory.
- Do not rewrite source batches or input dataset.
- Every batch should use a fresh worker subagent. Do not reuse a completed worker context for a later batch.
- The runtime architecture should treat each batch as a state machine with isolated attempts. A respawn must create a new attempt directory instead of reusing the same mutable CSV files.
- The active schedule should point only to the active attempt for each batch; older attempts remain for debugging but are not authoritative for lint, verifier, or merge.
- Each batch should keep one stable `base_worker_instructions.md`; every attempt-specific `worker_instructions.md` should be rendered fresh from that base instead of wrapping the previous attempt instructions recursively.

Full search policy:

- Workers may search freely.
- Workers are not limited to official sites, CoinGecko, or CoinMarketCap.
- Use search to identify the correct company, project, product, protocol, and token mapping.
- Prefer primary sources when available, but allow reputable secondary sources for discovery and corroboration.
- Search depth should be proportional to classifier likelihood and ambiguity.
- Do not close a row as skipped or no-token until former-name / alias / rebrand continuity has been checked.
- If docs mention governance, staking, wrapper, liquid-staked, bridge, reward token, or tokenomics language, run a token-family sweep before closing the row.
- If a token is supported only by secondary token pages, run one extra company/project linkage pass; if it remains secondary-only, keep `needs_manual_review = yes` or keep `token_ticker = []`.

Light search policy:

- Keep token usage low.
- Use exact names, aliases, former names, and normalized domain before broad discovery queries.
- Prefer official site/domain and exact-match token data pages.
- Do not browse broadly through generic secondary sources unless the first-pass evidence shows a possible owned project or token.
- If the light check finds a plausible token or project signal, upgrade the row to full search in the same run.
- Do not use `needs_manual_review = yes` as a substitute for completing the full search.

Light query playbook:

1. exact-domain token probe using `normalized_domain` or official host
2. exact `CompanyName` token/project probe
3. exact alias probe from `CompanyAlsoKnownAs`
4. exact former-name probe from `CompanyFormerName`
5. exact CoinGecko/CoinMarketCap project or token page probe

Light-tier requirements:

- before finalizing `token_ticker = []`, run the exact-domain token probe
- if any probe produces a plausible company -> project -> token signal, reroute to `full`
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
- `evidence_urls`: `|`-separated absolute HTTP(S) URLs
- `evidence_source_types`: `|`-separated lowercase source type labels
- `confidence`: `high`, `medium`, or `low`
- `needs_manual_review`: `yes` or `no`

Confidence and review are separate decisions:

- `confidence = high`: evidence clearly maps company or owned project to the token, typically with official or strong primary support
- `confidence = medium`: evidence is sufficient to merge, but is not as strong or complete as `high`
- `confidence = low`: evidence is weak, thin, or incomplete
- `needs_manual_review` must not be derived from `confidence` alone
- `medium` confidence rows may still merge with `needs_manual_review = no` when the mapping is stable and verifier review is clean
- `has_token_evidence` must never be blank
- searched rows must not use bare `yes` or `no` in `has_token_evidence`; they must summarize the positive or negative finding
- `project_search_required = yes` rows must have non-empty `evidence_urls` and `evidence_source_types`
- token-positive rows must have both `evidence_urls` and `evidence_source_types`

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

Resolution pass before manual review:

- Before setting `needs_manual_review = yes`, run an extra resolution pass unless an external blocker makes search impossible.
- Current-official pass: re-check official site, docs, blog, FAQ, announcements, foundation pages, GitHub, and explorer references for the current brand, current project name, and current active ticker.
- Identity-resolution pass: re-check aliases, former names, legal name, parent/subsidiary/acquired brand relationships, and project rebrands.
- Token-data corroboration pass: use exact project names on CoinGecko, CoinMarketCap, explorer, exchange, or docs pages to confirm or reject the company -> project -> token mapping.
- Negative-resolution pass: for no-token rows, confirm that current official materials do not identify a company-owned fungible token and that exact major token-page probes do not produce a stable mapping.
- Only keep `needs_manual_review = yes` when ambiguity remains unresolved after the resolution pass.

Cases that usually should resolve to `needs_manual_review = no` after the resolution pass:

- no-token rows where full search plus the resolution pass still finds no company-owned fungible token
- web3, tokenized-asset, NFT, or gaming language without a reliable fungible ticker after full search
- current official docs resolve a rename or migration and at least one current corroborating source supports the active ticker
- brand/domain mismatch explained by a stable rebrand, former name, acquisition, subsidiary, or owned project relationship
- thin official site, but enough current docs, foundation, explorer, or token-data evidence exists to complete the mapping

When no reliable source confirms a fungible token:

- use `token_ticker = []`
- do not output `no`
- do not output `unknown`

## 8. Manual Review Rules

Set `needs_manual_review = yes` only when one of these is still true after the resolution pass:

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

These cases usually should not stay in manual review:

- no-token rows with a completed full search and no remaining plausible owned fungible ticker
- rows where the only issue is crypto-adjacent or tokenized-product language but no token can be mapped
- rows where former names, aliases, or brand/domain mismatch were resolved by current sources
- rename / migration cases with a stable current active ticker backed by current corroboration

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

Do not create a new top-level run folder for every round. Reuse one working runs directory, keep verifier outputs as round-specific files in that shared working directory, merge the round into the authoritative final tables, then delete the temporary per-batch/per-round artifacts unless the user asks to keep them.

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

- sync all validated rows into `agent_runs/crypto_company/results.csv`
- update checkpoint
- regenerate `agent_runs/crypto_company/needs_manual_review.csv`
- preserve or summarize verifier reports for audit
- delete temporary worker run directories and round-specific verifier files unless the user asks to keep them for audit


## Runtime Strategy Layer

The authoritative runtime strategy layer lives in `part5_analyse_company_to_token/runtime/`:

- `policy.json`: controller statuses, failure taxonomy, timeouts, escalation, and cleanup globs
- `worker_base_template.md`: canonical worker base prompt; prepare and controller both render from this file
- `ARCHITECTURE.md`: ownership model, state machine, attempt layout, and main-agent execution order
- `README.md`: short index for the strategy-layer files

## 11. Validation Gates

Validation must happen before rows are merged into final results.

Structural checks:

- the codebase now has 2 scheduler paths:
  - blocking / fallback round mode: `python part5_analyse_company_to_token/scripts/5_run_round_supervisor.py --runs-dir part5_analyse_company_to_token/agent_runs/crypto_company_parallel --start-round-index <ROUND_INDEX> --round-count <ROUND_COUNT>`
  - unattended longrun entrypoint: `python part5_analyse_company_to_token/scripts/6_start_long_running_supervisor.py`
- unattended longrun should go through `6_start_long_running_supervisor.py`, not ad hoc prepare / launch / watch loops in the main agent.
- the launcher supports `--scheduler-mode round|queue`; the flag default is still `round` for backward compatibility, but the default unattended backlog path for future reruns is `queue`.
- queue mode keeps slots full across the whole target window instead of waiting for a full round barrier before launching more work.
- queue-mode execution order is:
  - prepare batch-scoped launch rows with `4_manage_round_runtime.py --prepare-launches`
  - spawn only selected launch rows
  - mark only those selected batches started
  - watch / reconcile running attempts
  - move completed batches into a serialized collect lane
  - keep filling free slots while ordinary waiting work exists
- round indices still exist in `schedule.csv`, verifier artifacts, and reporting, but they are metadata in queue mode rather than the primary execution barrier.
- after repeated runtime/lint failure loops on the same batch, the supervisor should promote that batch into `split_batch_2x15`: relaunch it as 2 fresh shard workers over 15 companies each, then merge shard outputs back into one authoritative batch result instead of directly writing manual-fallback rows
- the long-running launcher must auto-detect the next missing batch window from `agent_runs/crypto_company/results.csv`, prepare the next window, prefer launching the supervisor through `systemd-run --user`, fall back to detached `nohup` only if `systemd-run` fails, and write PID / run_dir / `unit_name` / log metadata to `part5_analyse_company_to_token/agent_runs/crypto_company_longrun_latest.json`.
- the long-running launcher and supervisor must pass the resolved absolute `codex` binary path into worker launches; do not rely on PATH lookup inside systemd user services.
- do not keep unattended supervisors inside an interactive PTY session. If the main agent needs a background longrun, it should delegate only to `6_start_long_running_supervisor.py`; otherwise a session exit can leave orphan worker processes and a frozen `schedule.csv`.
- if `5_run_round_supervisor.py` exits by uncaught exception or non-zero terminal failure, it must record that terminal condition into `supervisor_events.log` and `supervisor_state.json` instead of failing silently.
- in longrun mode, each batch has a fixed wall-clock budget of 2 hours by default.
- current queue-mode long-tail rule is two-stage, not immediate terminal defer:
  - first timeout: terminate active workers, preserve the partial prefix, and park the batch as `status=needs_rerun`, `queue_state=tail_retry_pending`, `tail_retry_pending=yes`, `tail_retry_count += 1`
  - parked tail retries must not re-enter the ordinary waiting queue immediately
  - parked tail retries are only eligible to relaunch after the normal waiting queue and the collect queue are both empty
  - with the current policy `DEFAULT_MAX_TAIL_RETRIES = 1`, the next timeout becomes terminal `deferred_long_tail`
- terminal `deferred_long_tail` batches count as operationally resolved for the current window so the remaining work can finish, but they remain explicit unfinished backlog.
- queue-mode collect is batch-scoped and serialized: completed batches can be merged into the global final outputs before their same-round peers finish, while `deferred_long_tail` batches are excluded from collect scope.
- when the user asks for “continue 10 rounds” or any equivalent long-running continuation request and explicitly accepts multi-hour background execution, the main agent should prefer the detached launcher instead of trying to stay inside the same interactive turn until completion.
- for status checks on the latest long-running job, use `python part5_analyse_company_to_token/scripts/7_check_longrun_status.py` as the default read-only entrypoint instead of manually opening multiple logs.
- when the user says “檢查 longrun 狀態” or equivalent, the main agent should run `7_check_longrun_status.py`, first query `systemctl --user` if `crypto_company_longrun_latest.json` includes a `unit_name`, then report `status / phase / active_workers / round_summaries`, and in queue mode also include the live slot view plus `waiting_queue / tail_retry_queue / collect_queue / deferred_queue` when present.
- the longrun status check should also include a host-process scan equivalent to `ps -ef | grep part5`, and use it as a secondary signal alongside heartbeat so the checker does not misclassify a still-running supervisor as stopped merely because current-context PID visibility is incomplete.
- do not launch workers directly from static schedule rows. First run the runtime controller to build a launch queue for the round: `python part5_analyse_company_to_token/scripts/4_manage_round_runtime.py --runs-dir part5_analyse_company_to_token/agent_runs/crypto_company_parallel --round-index <ROUND_INDEX> --prepare-launches`
- the runtime controller should upgrade legacy batch folders into isolated attempt directories and rewrite schedule.csv so the active paths point to the active attempt only
- after spawning workers from the launch queue, mark the round as started: `python part5_analyse_company_to_token/scripts/4_manage_round_runtime.py --runs-dir part5_analyse_company_to_token/agent_runs/crypto_company_parallel --round-index <ROUND_INDEX> --mark-round-started`
- while the round is running, use the runtime controller instead of ad hoc watcher commands: `python part5_analyse_company_to_token/scripts/4_manage_round_runtime.py --runs-dir part5_analyse_company_to_token/agent_runs/crypto_company_parallel --round-index <ROUND_INDEX> --watch-round --startup-no-row-timeout-seconds 480 --partial-stall-timeout-seconds 240`
- the runtime controller should detect two distinct failure modes:
  - startup no-row failure: both CSVs remain header-only after worker start
  - partial stall: a batch writes an initial prefix but row counts stop increasing for too long
- startup failures and partial stalls should not reuse the same mutable CSV files. Recovery must create a fresh attempt directory and switch schedule.csv to that attempt before the next launch
- runtime controller artifacts should be written to `launch_queue_round_XXXX.csv` / `launch_queue_round_XXXX.md` and `runtime_actions_round_XXXX.csv` / `runtime_actions_round_XXXX.md`
- all runtime-side `schedule.csv` writes must go through the shared locked atomic writer in `scripts/part5_schedule_io.py`; do not rewrite the live schedule directly with a raw `open(..., "w")` path.
- model escalation should be policy-driven instead of ad hoc: repeated startup failures should escalate model tier, and repeated partial stalls should escalate further or switch to continuation attempts
- before verifier, run local lint with `python part5_analyse_company_to_token/scripts/3_collect_results.py --runs-dir part5_analyse_company_to_token/agent_runs/crypto_company_parallel --lint-only --fail-on-identity-drift`
- preferred pre-verifier lint command is `python part5_analyse_company_to_token/scripts/3_collect_results.py --runs-dir part5_analyse_company_to_token/agent_runs/crypto_company_parallel --lint-only --repair-identity-drift-in-place --fail-on-identity-drift`
- classifier results CSV header exactly matches the classifier/router schema
- classifier results row count equals expected task count for the completed range
- `task_index`, `company_id`, `company_name`, and `normalized_domain` are immutable identity fields sourced from `tasks.jsonl`
- workers must copy immutable identity fields verbatim from `tasks.jsonl`; they are read-only output fields, not research fields
- any immutable identity drift is a run-blocking lint failure unless the operator explicitly chooses partial recovery
- collector must canonicalize immutable identity fields from `tasks.jsonl` and report any overrides as an operational warning and debugging signal
- lint should auto-mark `needs_rerun` in `schedule.csv` when it detects empty-header outputs, header mismatch, row-count mismatch, row-order mismatch, or severe schema failure density within a batch
- auto-marked lint reruns should be written to `lint_rerun_batches.csv` / `lint_rerun_batches.md` inside the shared runs dir
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
- `has_token_evidence` must be non-empty for every row
- searched rows must have non-empty `evidence_urls` and `evidence_source_types`
- searched rows must not use bare `yes` or `no` in `has_token_evidence`
- `evidence_urls` must contain only absolute HTTP(S) URLs separated by `|`
- `evidence_source_types` must use lowercase underscore labels separated by `|`
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

After each completed scope, before checkpoint update or terminal closure:

1. Build launch rows with the runtime controller; in queue mode this is done batch-scoped inside the target rounds, not only as one whole-round barrier.
2. Spawn workers only from those launch rows and mark only the selected batches started.
3. While execution is live, let the runtime controller and supervisor detect startup no-row failures, dead workers, partial stalls, split-recovery promotion, and queue-state transitions.
4. If runtime or lint marks a batch `needs_rerun`, rerun `--prepare-launches` only for that affected batch scope and relaunch only that affected work.
5. In queue mode, completed batches enter the collect lane as soon as they are ready; they do not wait for all same-round peers to finish.
6. If a batch hits the first long-tail timeout, park it as `tail_retry_pending` and do not relaunch it until ordinary waiting work and collect work are both empty.
7. If that same batch times out again after the parked retry, mark it terminal `deferred_long_tail`.
8. Run the local worker-output lint pass before final merge of the affected completed batches.
9. Confirm the authoritative attempt outputs cover every task in the completed or shard-completed scope being merged.
10. Confirm classifier `search_tier` and `project_search_required` values are consistent.
11. Confirm JSON list parse failures are zero, row counts are correct, and there are no duplicate task indexes.
12. Run verifier / collector resolution for the completed scope, then resolve every non-`pass` finding by edit, rerun, or manual review before those rows remain in final outputs.
13. Spot-check a sample of token-positive rows.
14. Spot-check a sample of `token_ticker = []` rows.
15. Spot-check skipped-search rows.
16. Update checkpoint only after verification is complete.
17. Remove temporary run directories only after verification is complete.

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

As of the current checkout state on `2026-05-05`:

- authoritative batch directory: `part5_analyse_company_to_token/agent_task_batches/crypto_company`
- generated input rows: `17837`
- generated batch files: `595`
- classifier result path: `part5_analyse_company_to_token/agent_runs/crypto_company/classifier_results.csv`
- final result path: `part5_analyse_company_to_token/agent_runs/crypto_company/results.csv`
- manual review path: `part5_analyse_company_to_token/agent_runs/crypto_company/needs_manual_review.csv`
- verification findings path: `part5_analyse_company_to_token/agent_runs/crypto_company/verification_findings.csv`
- checkpoint path: `part5_analyse_company_to_token/agent_runs/crypto_company/checkpoint.json`
- merged classifier rows: `17837`
- merged completed result rows: `17837`
- manual review rows currently present: `2460`
- completed through batch: `595`
- remaining ordinary batch backlog: `0`
- checkpoint sentinel next batch: `596`

Current interpretation rules:

- Treat `agent_runs/crypto_company/` as the only final-output authority for this completed checkout.
- Treat `agent_runs/crypto_company/results.csv` as the durable source of truth showing that all `595` planned batches have already been merged.
- Treat `agent_runs/crypto_company/needs_manual_review.csv` as the durable source of truth for unresolved manual-confirm rows.
- Treat `agent_runs/crypto_company/checkpoint.json` with `next_batch_to_process = 596` and `status = completed_all_batches` as the sentinel completed state, not as pending ordinary backlog work.
- Treat `agent_task_batches/crypto_company/` as the authoritative batch source only for audits, forensics, or explicit reruns.
- `part5_analyse_company_to_token/agent_task_batches/crypto_company_batch_0001_v2` is a legacy snapshot and must not be used as resume authority.
- Do not infer current progress from temporary worker folders or assume that a detached longrun is still active; temporary run directories may have been deleted after merge.

Existing pre-v2 or legacy batch artifacts should be treated as historical output only. There is no remaining ordinary batch window to resume from this checkout; any future work should start as an explicit audit, targeted rerun, or manual-review follow-up against the current final outputs.
