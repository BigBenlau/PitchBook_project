# Round 1 Verification Summary

- checked row count: 2
- pass count: 2
- non-pass count: 0
- suspected missing token count: 0
- suspected extra token count: 0
- wrong mapping count: 0
- skipped-search concern count: 0
- systematic causes found: none
- recommended process updates: none required for this round; current prompt and schema were sufficient for both rows
- explicit feedback items for the main agent when a rerun, prompt change, or process change is recommended: none

## Decision Notes

- `Wintermute Ventures`: accepted as `full` with `["otc_trading", "algorithm_trading", "market_making", "execution_services", "defi"]`. Official Wintermute pages place Ventures on the same first-party property as Wintermute's OTC, algorithmic trading, liquidity provision, and DeFi operating lines, and the worker's `operating_company_disguised_as_investor` mapping is consistent with the harness rules. `sub_fund = no` remains correct.
- `Jump Crypto`: accepted as `full` with `["algorithm_trading", "market_making", "defi"]`. Official Jump/Jump Crypto pages clearly support active trading, quant-style operating context, liquidity-provider / market-participant language, and DeFi building. They do not clearly support `otc_trading = yes` or `execution_services = yes` for the `Jump Crypto` investor row, even after considering parent-company context.
- Manual review: neither row needs `needs_manual_review = yes`. The parent-context boundaries are understandable and the official-source record is coherent enough to accept both rows without escalation.
