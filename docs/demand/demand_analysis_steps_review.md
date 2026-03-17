# Demand Analysis Steps Review (PR2)

## Review Target

PR2: demand analysis steps (`normalize -> map -> match -> assemble -> validate`).

## Reviewed Files

- `docs/demand/demand_analysis_steps.md`
- `src/demand/normalize_issue.py`
- `src/demand/map_semantics.py`
- `src/demand/match_development_type.py`
- `src/demand/build_demand_card.py`
- `src/demand/validate_demand_card.py`
- `schemas/demand/demand-card.schema.json`
- `templates/demand/demand-card.template.yaml`
- `src/demand/models.py`
- `tests/demand/test_normalize_issue.py`
- `tests/demand/test_map_semantics.py`
- `tests/demand/test_match_development_type.py`
- `tests/demand/test_demand_card_e2e.py`

## Overall Judgment

pass_with_gaps

## Normalize Correctness Assessment

PASS.
- preserves `issue_id` and `issue_text`
- trims whitespace
- rejects empty values
- does not inject summary/prose fields

## Semantic Mapping Correctness Assessment

PARTIAL.
- always returns all four arrays
- grounded in semantic foundation asset inputs
- deterministic ranking/ordering exists
- does not leak confidence/evidence/trace fields into final card

Gap:
- heuristic token/phrase matching can miss valid semantic links when vocabulary differs substantially from asset labels.

## development_type Matching Assessment

PASS.
- always returns exactly one type
- type is constrained to the five enums only
- ambiguous or unclear input yields `open_questions`
- no extra development types introduced

## Demand Card Assembly Assessment

PASS.
- assembly reuses Demand Card V1 builder/validator
- final shape remains canonical
- prohibited fields were not reintroduced

## End-to-End Validity Assessment

PASS.
- issue + semantic assets can produce valid Demand Card
- validator accepts valid generated cards
- `issue_id`/`issue_text` preserved in final output
- `open_questions` stays array-typed

## Test Quality Assessment

PASS.
- normalize tests cover trim + empty rejection
- mapping tests cover shape + deterministic controlled mapping + minimal output families
- matching tests cover feature/bugfix/refactor/migration/optimize and ambiguity
- e2e tests cover valid final card and prohibited-field absence

## Minimality Discipline Assessment

PASS.
- Demand Card remains factual, minimal, execution-facing
- no summary/explanation/trace/evidence/confidence/metadata/card_id/schema_version added
- no pipeline/teams/runtime drift introduced

## Strengths

- PR2 flow is implemented as bounded deterministic steps.
- Demand Card V1 contract stayed stable.
- Enum constraints and minimality rules remained enforced.
- E2E path is implemented and test-covered.

## Gaps

- Mapping quality is intentionally heuristic and may under-match in synonym-heavy or implicit-domain issues.
- Invariant projection fallback is broad when semantic matches exist.

## Blocking Issues

- None identified.

## Recommended Fixes

- Priority: medium  
  Target: `src/demand/map_semantics.py`  
  Issue: heuristic matching can under-match semantically equivalent but lexically different issue text  
  Recommendation: add optional alias dictionary (domain/concept/rule synonyms) while keeping deterministic output.

- Priority: low  
  Target: `tests/demand/test_map_semantics.py`  
  Issue: limited coverage for synonym/indirect phrasing scenarios  
  Recommendation: add one or two controlled fixtures for non-literal but expected mappings.

## Final Decision

- demand_analysis_steps_ready: true
