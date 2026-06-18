# Part6 Agent Prompt Template

Before doing any Part6 investor capability work, read:

1. `part6_analyse_investor_capabilities/Plan.md`
2. this file

If this file conflicts with `Plan.md`, `Plan.md` wins.

## Scope

Classify each assigned investor row for:

- `otc_trading`
- `algorithm_trading`
- `market_making`
- `execution_services`
- `defi`
- `sub_fund`

Write exactly one classifier row and one result row per investor. Do not do
token mapping, valuation analysis, market commentary, or entity merging across
unrelated PitchBook rows.

The only active input universe is `part5_to_part6/output/part6_batches/`.
Historical outputs, old branch folders, repair files, and audit files are not
classification evidence.

## Required Workflow

1. Read `Plan.md`.
2. Read the assigned JSONL task row and its `input_row`.
3. Use `MatchedKeywords`, `MatchedColumns`, and `InvestorCapabilityContext`
   only to understand why the investor appears in the formal Part5-to-Part6
   graph.
4. Copy `task_index`, `investor_id`, `investor_name`, `normalized_domain`, and
   `primary_investor_type` exactly from the top-level task fields.
5. Fill classifier fields: `investor_archetype`,
   `crypto_native_likelihood`, `operating_capability_likelihood`,
   `search_tier`, `capability_search_required`, `risk_flags`, and
   `classifier_reason`.
6. Write the classifier row before or together with the result row.
7. Search according to `search_tier`.
8. Write the completed result row.
9. Keep `capability_labels` synchronized with the six capability columns.
10. Set `needs_manual_review = yes` when a boundary remains ambiguous after one
    extra disambiguation pass.

Write incrementally. Do not wait until the batch end to write rows.

## Classification Rules

Allowed `investor_archetype` values:

- `traditional_vc_or_pe`
- `crypto_native_vc`
- `hedge_fund_or_quant`
- `market_maker_or_otc_firm`
- `asset_manager_or_family_office`
- `accelerator_or_incubator`
- `angel_or_individual`
- `exchange_affiliated_investor`
- `operating_company_disguised_as_investor`
- `fund_vehicle_or_fund_platform`
- `unclear`

Allowed likelihood values:

- `high`
- `medium`
- `low`
- `none`
- `unclear`

Allowed `search_tier` values:

- `full`
- `light`
- `skip_candidate`

Hard routing rules:

- `full` or `light` requires `capability_search_required = yes`.
- `skip_candidate` requires `capability_search_required = no`.
- `skip_candidate` is a narrow exception. Use it only when the row is clearly
  and completely unrelated to crypto/Web3, financial services, investing/funds,
  trading/execution/liquidity, DeFi, and parent/sub-fund structure.
- `skip_candidate` requires both likelihood fields to be `none` or `low`.
- If local fields, domain, parent, description, verticals, matched context,
  official pages, portfolio/backer pages, or trusted database profiles contain
  any possible relevant signal, use at least `light`.
- If uncertain between `skip_candidate` and `light`, use `light`.

## Capability Rules

Use current, direct, source-backed evidence. Current official sources beat
current official portfolio/backer pages, which beat trusted third-party
databases, which beat stale databases, ordinary news, social media, and local
PitchBook input.

Do not use ordinary news, social media, or local PitchBook input as direct
`yes` evidence. Use them only for search and disambiguation.

Do not infer capabilities from portfolio exposure, generic crypto exposure,
educational content, exchange listings, maker/taker fee schedules, associated
individuals, or affiliation alone unless `Plan.md` explicitly allows that exact
source-backed attribution.

Parent attribution is one-way only. A parent row may inherit a controlled
child/unit capability when current sources show control. A child, venture arm,
fund, subsidiary, individual, portfolio company, minority investment, LP
investment, client, partner, or ecosystem member does not inherit parent or
affiliate capabilities unless the row itself has current evidence.

Apply these capability standards:

- `otc_trading = yes`: current self-operated OTC trading service, or one-way
  parent inheritance from a controlled child/unit. Includes centralized OTC,
  block, off-exchange, bilateral, dealer/broker/counterparty RFQ, and
  traditional-finance OTC. Exclude OTC access-only, custody/settlement-only,
  on-chain RFQ/intent, and historical/stopped service.
- `algorithm_trading = yes`: current self-operated or provided algorithmic,
  quantitative, systematic, HFT, low-latency trading-engine, automated strategy,
  bot, or algorithm-trading service/agency capability, or one-way parent
  inheritance. Exclude market-maker status alone, proprietary-trading status
  alone, "technology-driven trading firm" wording alone, API/FIX/connectivity,
  routing algorithms alone, and historical/stopped service.
- `market_making = yes`: current self-operated market making or liquidity
  provision using own/proprietary/balance-sheet/controlled capital, or one-way
  parent inheritance. Exclude generic liquidity language, quotes/pricing only,
  exchange/broker status alone, AMM/DEX operation without LP capital,
  third-party market-maker allocations, and historical/stopped service.
- `execution_services = yes`: current self-operated order placement, order
  handling, executable brokerage, trade execution, execution venue, matching
  engine, exchange/CEX, ATS/MTF/ECN, executable DMA, DEX, swap, perp DEX, AMM,
  or on-chain trading protocol, or one-way parent inheritance. Exclude
  API/FIX/connectivity alone, routing alone, liquidity access alone, external
  wallet links, white-label third-party execution, custody/post-trade-only
  service, market making alone, OTC desk alone, and historical/stopped service.
- `defi = yes`: current DeFi trading or DeFi protocol operation. Count current
  DeFi protocol operation, DEX/AMM/swap/perp/options/RFQ/intent trading,
  lending/borrowing/credit use, leverage/collateral activity, vault/yield,
  liquid staking/restaking, LP capital deployment, DeFi market making,
  on-chain arbitrage, MEV, liquidations, managed DeFi strategy, or one-way
  parent inheritance from a controlled child/unit/fund doing those activities.
  Exclude DeFi portfolio exposure, token investment, SAFT, grants, accelerator
  support, ecosystem funding, DeFi-adjacent infrastructure exposure, customer
  DeFi access, secondary-market token holding, and historical/stopped activity
  unless current DeFi trading/protocol-operation evidence is also present.
- `sub_fund = yes`: current parent/mother-entity structure label. Count only
  when current official/trusted evidence shows the current investor currently
  has under it a sub-fund, fund vehicle, venture arm, investment arm, crypto
  arm, dedicated capital pool, dedicated investment/trading branch, or
  comparable sub-fund-like structure. Exclude row-itself-is-child cases,
  manager-only evidence, name-only matches, ordinary closed funds, and
  historical/stopped structures.

## Output Schemas

Classifier CSV header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,risk_flags,classifier_reason
```

Result CSV header:

```csv
task_index,investor_id,investor_name,normalized_domain,primary_investor_type,investor_archetype,crypto_native_likelihood,operating_capability_likelihood,search_tier,capability_search_required,capability_search_reason,status,completed_at,capability_labels,otc_trading,algorithm_trading,market_making,execution_services,defi,sub_fund,other_flags,evidence_urls,evidence_source_types,evidence_summary,confidence,needs_manual_review
```

Output rules:

- `risk_flags`, `other_flags`, and `capability_labels` must be JSON list
  strings.
- `capability_labels` must exactly equal the list of capability columns whose
  value is `yes`.
- All six capability columns must be `yes` or `no`.
- `status` must be `completed`.
- `completed_at` must be a literal ISO-8601 timestamp. Never write shell syntax
  such as `$(date -u ...)`.
- `evidence_urls` must use `|`-separated absolute HTTP(S) URLs.
- `evidence_source_types` must use `|`-separated lowercase labels such as
  `official_site`, `official_docs`, `official_filing`,
  `official_blog_or_press`, `trusted_database`, `secondary_profile`,
  `ordinary_news_context`, or `local_csv`.
- `ordinary_news_context` and `local_csv` cannot directly support a capability
  `yes`.
- For no-search skip rows, leave `evidence_urls` and `evidence_source_types`
  blank instead of writing `[]`.
- For searched rows, `evidence_urls` and `evidence_source_types` must be
  non-empty unless the identity/current entity cannot be resolved after real
  search. That narrow exception requires all capabilities `no`,
  `confidence = low`, `needs_manual_review = yes`, and an `other_flags` marker
  such as `identity_unresolved` or `no_reliable_external_match`.
- `evidence_summary` must be non-empty for every row.
- `confidence` must be exactly `high`, `medium`, or `low`.

## Final Self-Check

Before final response, verify:

- classifier row count equals assigned task count;
- result row count equals assigned task count;
- no duplicate `task_index`;
- no missing `task_index`;
- every `capability_labels` JSON list matches the six capability columns;
- no `skip_candidate` row has medium/high/unclear likelihood;
- all searched rows have non-empty evidence URLs, source types, and summary,
  except unresolved-identity manual-review rows using the narrow exception.

Final response should report row counts, rows by `search_tier`,
non-empty `capability_labels` count, `needs_manual_review = yes` count,
authoritative classifier/results paths, and blockers.
