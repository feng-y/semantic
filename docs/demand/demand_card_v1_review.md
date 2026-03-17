# Demand Card V1 Foundation Review

## Review Target

PR1: Demand Card Foundation (review-only scope).

## Reviewed Files

- `docs/demand/demand_card_v1.md`
- `schemas/demand/demand-card.schema.json`
- `templates/demand/demand-card.template.yaml`
- `src/demand/models.py`
- `src/demand/build_demand_card.py`
- `src/demand/validate_demand_card.py`
- `tests/demand/test_build_demand_card.py`
- `tests/demand/test_validate_demand_card.py`

## Overall Judgment

pass_with_gaps

## Shape Correctness Assessment

PASS. Canonical shape is stable and matches the target V1 structure:
- single top-level `demand_card`
- `request_source`, `semantic_mapping`, `development_type`, `uncertainties`
- required semantic mapping arrays present
- `open_questions` array present

No prohibited field family was introduced in card shape.

## Schema Usefulness Assessment

PASS. Schema is enforceable and not decorative:
- strict `required` fields
- strict `development_type` enum
- object and array types defined
- non-empty string constraints on key string fields
- `additionalProperties: false` used throughout

## Template Alignment Assessment

PASS. Template aligns with schema:
- includes all required fields
- arrays are present and initialized
- valid sample `development_type` provided
- no extra unsupported fields

## Model Correctness Assessment

PASS. Models reflect V1 shape and remain minimal:
- `RequestSource`, `SemanticMapping`, `Uncertainties`, `DemandCardBody`, `DemandCard`
- `DevelopmentType` uses `Literal` with the 5 allowed values
- no extra semantic layers added

## Builder Correctness Assessment

PASS. Builder behavior is consistent with PR1:
- emits canonical shape only
- normalizes list inputs (trim, dedupe, preserve order, drop empties)
- defaults arrays to empty
- rejects empty `issue_id` / `issue_text`
- strictly validates `development_type`
- does not inject summary/trace/confidence/metadata

## Validator Correctness Assessment

PASS. Validator meaningfully enforces core contract:
- rejects missing/empty `issue_id` and `issue_text`
- validates all semantic mapping fields as arrays of non-empty strings
- strictly validates `development_type`
- validates `open_questions` as array of non-empty strings

## Test Quality Assessment

PARTIAL. Coverage is solid for core pass/fail paths, but one contract case is not explicitly locked:
- missing explicit negative test for `open_questions` being non-array (e.g., string/object)

Existing tests do cover:
- valid card pass
- missing `issue_id`/`issue_text` fail
- invalid `development_type` fail
- non-array `domains` fail
- empty-string item in `rules` fail
- builder defaults and normalization behavior

## Minimality Discipline Assessment

PASS. Implementation remains a semantic fact card and does not drift into trace/audit/explanation/metadata container patterns.

## Strengths

- Canonical shape is clear and stable.
- Schema/template/model/builder are aligned.
- `development_type` enforcement is strict in builder and validator.
- Builder normalization is deterministic and execution-friendly.
- Core negative-path validation coverage is present.

## Gaps

- Missing explicit unit test for non-array `open_questions`.
- Validator does not currently enforce unknown-field rejection in code path (schema does), so schema/validator strictness is not fully mirrored.

## Blocking Issues

- None identified.

## Recommended Fixes

- Priority: medium  
  Target: `tests/demand/test_validate_demand_card.py`  
  Issue: no explicit non-array `open_questions` test  
  Recommendation: add a case where `open_questions` is a non-list value and assert validation failure.

- Priority: medium  
  Target: `src/demand/validate_demand_card.py`  
  Issue: validator does not reject unknown fields, while schema is strict (`additionalProperties: false`)  
  Recommendation: add optional unknown-field checks to keep runtime validator behavior consistent with schema strictness.

## Final Decision

- demand_card_v1_ready: true
