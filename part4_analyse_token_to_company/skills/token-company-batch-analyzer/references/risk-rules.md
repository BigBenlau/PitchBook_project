# Risk Rules

## 1. Field-Level Escalation

Escalate a token when any target remains unresolved:

- `founder_status = unresolved`
- `related_company_status = unresolved`
- `foundation_status = unresolved`

This is field-level escalation, not row-level escalation.

If one target is supported and two are unresolved, the token is still incomplete and must remain in the workflow.

## 2. High-Risk Token Types

Treat these token types as high-risk:

- `wrapped_or_bridged`
- `liquid_staking_or_receipt`
- `synthetic_or_fund`
- `unknown`

These types should usually escalate faster and remain in review longer.

## 3. Official Evidence Priority

For `related_companies` and `foundation_or_orgs`, use official/company evidence first.

Do not let CG/CMC founder prose become the only high-confidence basis for:

- issuer attribution
- operator attribution
- parent company attribution
- foundation attribution

If official/company evidence is absent or conflicts with CG/CMC, escalate.

## 4. False Positive Controls

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
- heading-only founder text contains no entity
- ecosystem participants are not operators
- contributors are not founders unless explicitly called founders
- underlying asset team is not automatically the wrapped / bridged / staked token team

## 5. Confidence Controls

Use `high` only if:

- the evidence is direct, correctly typed, and strongly supported
- company/foundation claims have official support

Use max `medium` if:

- only one weak source supports the result
- official/company evidence is missing for a company/foundation claim
- target coverage is incomplete

Use `low` if:

- evidence is ambiguous
- entity typing is fragile
- the token is high-risk and the mapping is still partial

## 6. Mandatory Review

Send to review queue if:

- any target is unresolved
- `status = pending_layer3`
- `needs_manual_review = 1`
- token type is high-risk
- company/foundation support exists without official-site evidence
- source conflict exists
- weak relation context supports a company claim
