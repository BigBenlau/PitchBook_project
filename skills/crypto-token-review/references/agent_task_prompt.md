Use the repo-local skill at {{skill_path}}.

Review one company from the crypto company queue.

Allowed sources only:
- official website under the official domain
- CoinGecko
- CoinMarketCap

Do not use:
- DefiLlama
- GeckoTerminal
- DexScreener
- news sites
- third-party media
- forums
- social media
- any other websites

Task scope:
- map the company to zero, one, or multiple crypto projects
- fill `token_ticker` only when supported by allowed sources
- return exactly one CSV row per company
- provide short evidence text
- provide evidence URLs
- provide evidence source types
- provide confidence
- provide `needs_manual_review`

Decision rules:
- `token_ticker` requires positive evidence from the allowed sources
- no evidence means `token_ticker` must be an empty JSON list: []
- no token means `token_ticker` must be an empty JSON list: []
- exchange status does not imply a token
- a company may map to multiple crypto projects and multiple token tickers
- if multiple token tickers are confirmed, put them in one JSON list in `token_ticker`
- do not treat stock `Exchange` or stock `Ticker` as crypto token evidence
- if sources conflict, prefer the official site; otherwise set `token_ticker` to [] and mark `needs_manual_review = yes`
- do not deep-search listing data unless it is already explicit on the allowed sources

Company row:
task_index: {{task_index}}
CompanyID: {{CompanyID}}
CompanyName: {{CompanyName}}
CompanyAlsoKnownAs: {{CompanyAlsoKnownAs}}
CompanyFormerName: {{CompanyFormerName}}
CompanyLegalName: {{CompanyLegalName}}
Website: {{Website}}
normalized_domain: {{normalized_domain}}
ParentCompany: {{ParentCompany}}
Exchange: {{Exchange}}
Ticker: {{Ticker}}
HQLocation: {{HQLocation}}
HQCountry: {{HQCountry}}
Verticals: {{Verticals}}
EmergingSpaces: {{EmergingSpaces}}
Description: {{Description}}
Keywords: {{Keywords}}
MatchedKeywords: {{MatchedKeywords}}
MatchedColumns: {{MatchedColumns}}
AllowedSources: {{allowed_sources}}
TaskScope: {{agent_task_scope}}

Return CSV only. Return exactly one row for this company. If no token is found, return `token_ticker`, `token_name`, and `token_url` as empty JSON lists: []. If multiple projects or token tickers are confirmed, keep one row and use JSON lists in the list-valued columns.

Do not return these columns:
- CompanyID
- CompanyName
- has_token
- raw_output

CSV columns:
task_index,company_id,company_name,normalized_domain,project_name,project_url,status,completed_at,token_ticker,token_name,token_url,has_token_evidence,evidence_urls,evidence_source_types,confidence,needs_manual_review

CSV row template:
{{task_index}},{{CompanyID}},{{CompanyName}},{{normalized_domain}},"[]","[]","completed",,"[]","[]","[]","short evidence","https://example.com/","official_site","high","no"
