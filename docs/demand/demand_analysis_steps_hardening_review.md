# Demand Analysis Steps Hardening Review

## Review Target

PR2 hardening pass for semantic mapping robustness under non-literal phrasing.

## Reviewed Files

- `docs/demand/demand_analysis_steps.md`
- `docs/demand/demand_analysis_steps_hardening.md`
- `docs/demand/demand_analysis_steps_hardening.yaml`
- `src/demand/map_semantics.py`
- `tests/demand/test_map_semantics.py`
- `tests/demand/test_demand_card_e2e.py`
- `schemas/demand/demand-card.schema.json` (reference)
- `src/demand/build_demand_card.py` (reference)
- `src/demand/validate_demand_card.py` (reference)

## Overall Judgment

pass_with_gaps

## Controlled Synonym/Alias Support Assessment

PASS.

`map_semantics.py` contains real, explicit alias support:
- bounded alias catalog by family (`domains`, `concepts`, `rules`, `invariants`)
- explicit phrase normalization and phrase containment checks
- deterministic scoring and ranking
- bounded alias trigger (phrase-like aliases only)

No unconstrained fuzzy search behavior was introduced.

## Non-literal Mapping Correctness Assessment

PARTIAL.

Improvements are real:
- non-literal domain mapping works (`service registry backend` -> `Redis Discovery`)
- non-literal concept mapping works (`context hashing op` -> `hash_to_context operator`)
- non-literal rule/invariant mapping works for controlled cases

Remaining gap:
- improvement depends on a small alias catalog; under-match can still happen for unseen paraphrases.

## Test Coverage Assessment

PASS.

Coverage now includes:
- non-literal domain case
- non-literal concept case
- non-literal rule + invariant case
- deterministic behavior checks
- minimal-shape/prohibited-field assertions
- paraphrased e2e scenario with validator pass

## Minimality Discipline Assessment

PASS.

Hardening did not reintroduce prohibited fields. Demand Card remains factual/minimal with only canonical families.

## Consistency Assessment

PASS.

Code, tests, and hardening docs are aligned:
- docs claim controlled alias support, and code implements it explicitly
- tests exercise the described non-literal scenarios
- no undocumented behavior drift observed

## Strengths

- Controlled alias mechanism is real and reviewable.
- Deterministic mapping behavior is preserved.
- Non-literal mapping quality improved in practical scenarios.
- Minimal Demand Card contract remains intact.
- Test coverage materially strengthened for paraphrase handling.

## Remaining Gaps

- Alias catalog breadth is intentionally limited and requires maintenance for new wording variants.
- Highly indirect or domain-specific paraphrases may still under-match.

## Blocking Issues

- None.

## Recommended Fixes

- Priority: medium  
  Target: `src/demand/map_semantics.py`  
  Issue: alias coverage is narrow for broader repository vocabularies  
  Recommendation: expand alias catalog incrementally using observed issue language patterns.

- Priority: low  
  Target: `tests/demand/test_map_semantics.py`  
  Issue: paraphrase coverage is still compact  
  Recommendation: add a few additional controlled paraphrase fixtures per family to reduce regression risk.

## Final Decision

- hardening_review_passed: true
