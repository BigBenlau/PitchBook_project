# Risk Rules

## Layer Escalation

Escalate a row from Layer 1 to Layer 2 if:

- all three target arrays are empty
- confidence is `low`
- evidence comes from only one CG/CMC source
- candidate sentence has risk flags
- token is wrapped, bridged, staked, liquid-staking, or synthetic
- evidence mentions a project but not a directly related token entity

Escalate to Layer 3 if:

- official evidence is unavailable or conflicts with CG/CMC
- official page is JS-rendered or PDF-only and cannot be parsed
- founder/company/org remains ambiguous after Layer 2
- token is high priority and unresolved

## False Positive Controls

Do not treat these as related company evidence:

- `listed on`
- `traded on`
- `available on`
- `partnered with`
- `backed by`
- `portfolio`
- `custody`
- `custodian`

Common false positives:

- ETF issuer is not token issuer
- technical foundation is not a foundation organization
- heading-only sentences such as "Who are the founders?" contain no entity
- ecosystem participants are not operators
- contributors are not founders unless explicitly called founders

## Confidence Caps

Use `high` only if:

- official source explicitly supports the result, or
- two independent structured sources agree and there is no conflict

Use max `medium` if:

- only one non-official source supports the result
- evidence has weak relation context
- CMC match method is not `slug`

Use `low` if:

- evidence is incomplete
- source text is ambiguous
- entity type could be confused

## Mandatory Review

Send to review queue if:

- non-slug match
- high confidence without official support
- any target array is populated without evidence spans
- entity type appears mixed
- token variant risk is present
- source conflict exists
- weak relation context supports related company
