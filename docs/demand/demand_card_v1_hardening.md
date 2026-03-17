# Demand Card V1 Hardening (PR1.1)

## Hardening Target

PR1.1 runtime hardening for Demand Card Foundation:
1. add explicit negative test for non-array `open_questions`
2. reject unknown fields at runtime to align with schema `additionalProperties: false`

## Files Updated

- `src/demand/validate_demand_card.py`
- `tests/demand/test_validate_demand_card.py`

## Unknown-Field Validation Changes

Runtime validator now rejects unknown fields at these levels:
- root object (only `demand_card` allowed)
- `demand_card` object
- `demand_card.request_source`
- `demand_card.semantic_mapping`
- `demand_card.uncertainties`

Implementation uses explicit allow-lists and deterministic error messages.

## open_questions Negative Test Added

Added explicit negative test where:
- `demand_card.uncertainties.open_questions` is a string, not a list

The test asserts:
- validation fails
- returned error references `open_questions`

## Remaining Risks

- Runtime unknown-field checks are hand-maintained allow-lists; future shape changes require synchronized updates to validator constants.

## Final Decision

- hardening_completed: true
