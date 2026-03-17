# Demand Analysis Steps Hardening (PR2)

## Hardening Target

PR2 mapping quality hardening for non-literal issue phrasing.

## Observed Weakness

Previous semantic mapping was mainly literal/token overlap, which could under-match when issue text used paraphrased wording instead of exact asset labels.

## Controlled Synonym/Alias Support Added

Updated `src/demand/map_semantics.py` with a bounded, explicit alias catalog:
- domain aliases
- concept aliases
- rule aliases
- invariant aliases

Matching behavior remains deterministic:
- explicit phrase normalization
- explicit phrase containment checks
- bounded alias matching (phrase-like aliases only)
- stable ranking/order maintained

No confidence, trace, explanation, or metadata fields were added to card output.

## New Test Scenarios Added

Updated mapping tests with non-literal wording coverage:
- domain recovered from paraphrased wording
- concept recovered from paraphrased wording
- rule and invariant recovered from paraphrased wording
- explicit minimal-shape/prohibited-field checks retained

Updated e2e test coverage with a paraphrased issue path that still produces a valid minimal Demand Card.

## Intentionally Out of Scope

- pipeline implementation
- teams orchestration
- execution runtime
- trace/audit artifacts
- broad NLP/fuzzy search infrastructure
- Demand Card schema/shape redesign
