# Demand Pipeline Review

## Review Target

PR3: Demand Pipeline wiring review (orchestration-only scope).

## Reviewed Files

- `docs/demand/demand_pipeline.md`
- `src/demand/run.py`
- `src/demand/stage_registry.py`
- `skills/demand-pipeline/SKILL.md`
- `src/demand/normalize_issue.py`
- `src/demand/map_semantics.py`
- `src/demand/match_development_type.py`
- `src/demand/build_demand_card.py`
- `src/demand/validate_demand_card.py`
- `tests/demand/test_demand_pipeline.py`
- `tests/demand/test_demand_pipeline_e2e.py`

## Overall Judgment

pass_with_gaps

## Pipeline Wiring Correctness Assessment

PASS.

The pipeline correctly wires:
1. `normalize_issue`
2. `map_semantics`
3. `match_development_type`
4. `build_demand_card`
5. `validate_demand_card`

Issue input flows through intermediate objects, final card is produced by existing builder, and final validation uses existing validator.

## Result/Output Contract Assessment

PASS.

`run_demand_pipeline()` returns a stable and explicit result shape with:
- `ok`
- `issue_id`
- `demand_card`
- `validation_errors`
- `failed_stage`
- `error`
- `stage_order`
- `stages`
- `intermediate` (`normalized_issue`, `semantic_mapping`, `development_type_match`)

This is clear for callers and suitable for stage-level debugging.

## Failure Surfacing Assessment

PASS.

Failures are surfaced explicitly by stage:
- normalize failures stop immediately
- map/match/build failures stop immediately
- validation failures return `failed_stage=validate_demand_card` and `validation_errors`

No silent repair path for malformed cards is present.

## Demand Card Integrity Assessment

PASS.

The final card remains canonical V1 shape and minimal. No prohibited fields are introduced by pipeline orchestration.

## Skill Correctness Assessment

PASS.

`skills/demand-pipeline/SKILL.md` is thin and implementation-driven:
- clearly states required inputs and outputs
- points to `src/demand/run.py` entrypoints
- does not embed business logic or teams/workflow complexity

## Test Quality Assessment

PARTIAL.

Good coverage exists for:
- success path and result structure
- normalize failure surfacing
- validation failure surfacing
- realistic e2e scenarios (feature/bugfix/optimize)
- minimality/prohibited-field assertions

Gap:
- no explicit unit test that forces a **build-step exception** and asserts `failed_stage=build_demand_card`.

## Minimal Orchestration Discipline Assessment

PASS.

PR3 remains minimal orchestration and does not introduce:
- teams orchestration
- initializer systems
- execution runtime
- large workflow/state-machine frameworks

## Strengths

- Correct end-to-end step wiring.
- Explicit, stable pipeline result contract.
- Clear failure surfacing by stage.
- Demand Card contract preserved unchanged.
- Thin and aligned skill entry.

## Gaps

- Missing direct test for build-step failure surfacing.

## Blocking Issues

- None.

## Recommended Fixes

- Priority: medium  
  Target: `tests/demand/test_demand_pipeline.py`  
  Issue: build-step failure path is not explicitly locked by test  
  Recommendation: patch `build_demand_card` to raise and assert `failed_stage=build_demand_card`, `ok=false`, and explicit error propagation.

## Final Decision

- demand_pipeline_ready: true
