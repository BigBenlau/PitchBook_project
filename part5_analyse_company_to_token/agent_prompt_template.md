# Part5 Agent Prompt Template

## Mission

Map each assigned company to zero, one, or multiple formal fungible token mappings.

The only valid inclusion rule is:

Include a token only when strong, direct, and stable evidence shows that the company is an officially recognized founding entity, co-founding entity, or original founding organization of the token's blockchain or protocol ecosystem.

Do not include a token merely because the company listed it, invested in it, advised it, operated a dApp, issued a product token, built a wallet, ran a DEX, provided staking/liquidity/market-making, promoted the ecosystem, joined later as a participant, or held a token allocation without founding-organization evidence.

## Required Search Behavior

- Start from the company row: legal name, aliases, former names, website, domain, description, verticals, keywords, and crypto relevance context.
- Resolve company/project/token identity before writing a token.
- Prefer official websites, official docs, foundation/project docs, token docs, GitHub/org docs, credible company pages, explorers, CoinGecko, CoinMarketCap, and primary announcements.
- Secondary sources may corroborate but should not be the sole basis for a high-confidence positive mapping.
- Before finalizing `token_results = []`, run a bounded exact-domain / exact-company / alias / former-name token probe.
- For protocol, tokenomics, governance, staking, wrapper, bridge, rewards, or ecosystem language, run a token-family sweep.
- If evidence is ambiguous after reasonable search, set `needs_manual_review = yes`; do not use manual review as a substitute for doing the search.

## Inclusion Examples

Include both a foundation and an operating company only when each has independent direct founding-entity evidence.

Include an association, foundation, legal wrapper, or operating company only when it is officially recognized as an original founding organization of the relevant blockchain/protocol ecosystem.

## Exclusion Examples

Exclude ordinary dApps, games, NFT marketplaces, wallets, exchanges, DEXs, staking providers, validators without founding evidence, investors, launchpads, incubators, market makers, liquidity providers, portfolio companies, later venture arms, ordinary ecosystem funds, and tokenized product issuers without founding-organization evidence.

## Classifier Output

Write exactly one classifier row per company.

Classifier CSV header:

```text
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,search_tier,project_search_required,risk_flags,classifier_reason
```

Allowed `search_tier` values:

- `full`
- `light`
- `skip_candidate`

Allowed `project_search_required` values:

- `yes`
- `no`

Use `project_search_required = yes` for `full` and `light`; use `no` only for `skip_candidate`.

## Result Output

Write exactly one result row per company.

Result CSV header:

```text
task_index,company_id,company_name,normalized_domain,company_type,crypto_project_likelihood,project_search_required,project_search_reason,project_name,project_url,status,completed_at,token_symbol,token_decision_reason,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review,token_results
```

`project_name`, `project_url`, `token_symbol`, and `token_results` must be valid JSON list strings.

Each `token_results` object must use:

```json
{
  "token_symbol": "",
  "token_name": "",
  "token_url": "",
  "reason": "",
  "evidence_urls": [],
  "evidence_source_types": []
}
```

Rules:

- `status = completed`.
- `token_symbol` must equal all `token_symbol` values extracted from `token_results`, in the same order.
- `token_results = []` when no formal founding-entity token mapping exists.
- `token_decision_reason` must explain positive and negative decisions.
- `has_token_evidence` must be a concise evidence summary, not bare `yes` or `no`.
- `evidence_urls` must be `|`-separated absolute HTTP(S) URLs.
- `evidence_source_types` must be `|`-separated lowercase labels such as `official_site`, `official_docs`, `coingecko`, `coinmarketcap`, `explorer`, or `secondary_source`.
- `confidence` must be `high`, `medium`, or `low`.
- `needs_manual_review` must be `yes` or `no`.

## Worker Discipline

- Copy immutable identity fields exactly from `tasks.jsonl`: `task_index`, `company_id`, `company_name`, and `normalized_domain`.
- Append classifier and result rows incrementally as each company is completed.
- Do not hold the full batch and write only at the end.
- Do not invent schema changes, extra columns, or alternate output paths.
- Before finalizing, validate row order, identity fields, CSV quoting, JSON list fields, and required evidence fields.

## Verifier Prompt

The verifier must independently re-check formal token mappings and detect:

- missing token
- extra token
- wrong token mapping
- invalid token JSON
- wrong project mapping
- non-fungible or stock ticker contamination
- search tier too conservative
- search should not have been skipped
- insufficient evidence

Verifier CSV header:

```text
task_index,company_id,company_name,classifier_search_tier,worker_token_results,verifier_search_tier,verifier_token_results,verdict,error_type,error_reason,evidence_urls,recommended_action,corrected_result_row_json
```

Allowed verdicts:

- `pass`
- `missing_token`
- `extra_token`
- `wrong_token_mapping`
- `invalid_token_result_json`
- `suspected_missing_token`
- `suspected_extra_token`
- `wrong_project_mapping`
- `non_fungible_or_stock_ticker`
- `search_tier_too_conservative`
- `search_should_not_have_been_skipped`
- `insufficient_evidence`

If `recommended_action = edit_row`, `corrected_result_row_json` must contain a full result-row JSON object using the exact result schema.
