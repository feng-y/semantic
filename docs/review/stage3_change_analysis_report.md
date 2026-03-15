# Stage 3 — Change Analysis Report

## Scope

Implemented Stage 3 minimum bridge only:

`IBS Core -> change-analysis`

Out of scope (deferred):

- implementation-plan generation
- full IBS analysis pack
- runtime architecture redesign
- discovery pipeline changes
- public skill interface changes

## Files Added

- `docs/review/stage3_change_analysis_mapping.md`
- `docs/semantic-design/012-change-analysis-output-model.md`
- `docs/semantic/templates/change-analysis.template.md`
- `src/change_analysis_generator.py`
- `src/change_analysis_validation.py`
- `tests/test_stage3_change_analysis.py`
- `docs/review/stage3_change_analysis_report.md`

## Files Modified

- `src/refine_executor.py`
- `src/context_builder.py`
- `docs/semantic/templates/README.md`

## Mapping Summary

Stage 3 mapping source is documented in:

- `docs/review/stage3_change_analysis_mapping.md`

IBS Core -> change-analysis mapping:

- `purpose.md` -> `Change Intent`
- `pipelines.md` -> `Affected Pipelines`
- `domains.md` + `concepts.md` -> `Affected Domains and Concepts`
- `pipelines.md` + `concepts.md` confidence markers -> `Impact and Risks`
- all IBS Core artifacts -> `Suggested Next Changes`

## Generation Flow

1. Stage 2 baseline synthesis writes IBS Core artifacts:
   - `docs/semantic/baseline/purpose.md`
   - `docs/semantic/baseline/pipelines.md`
   - `docs/semantic/baseline/domains.md`
   - `docs/semantic/baseline/concepts.md`
2. New Stage 3 step (`_execute_change_analysis_step`) runs after successful baseline synthesis.
3. `context_builder.build_change_analysis_context()` reads IBS Core baseline artifacts.
4. `generate_change_analysis(...)` creates deterministic sectioned output.
5. `validate_change_analysis(...)` validates structure.
6. Artifact is written as versioned review output:
   - `docs/semantic/review/change-analysis.vN.md`

## Validation Logic

`src/change_analysis_validation.py` enforces:

- non-empty artifact
- required sections:
  - `Change Intent`
  - `Affected Pipelines`
  - `Affected Domains and Concepts`
  - `Impact and Risks`
  - `Suggested Next Changes`
- minimal section content checks
- section-shape checks:
  - affected pipelines must include pipeline entries
  - affected domains/concepts section must include both `Domains` and `Concepts` blocks

## Tests Added

`tests/test_stage3_change_analysis.py` verifies:

- Stage 3 mapping doc exists and contains required mapping concepts
- Stage 3 design doc exists
- `change-analysis.template.md` passes validator
- IBS Core field mapping into generated change-analysis content
- validator rejects missing required structure
- refine integration generates `change-analysis.v1.md` from IBS Core baseline

## Pytest Result

Command run:

- `pytest`

Result:

- **243 passed, 0 failed**

## Remaining Gaps (Deferred to Stage 4)

- implementation-plan generation is not implemented
- change-analysis does not yet emit structured implementation tasks
- no full analysis-pack decomposition (kept intentionally minimal in Stage 3)
- deeper semantic-quality scoring across artifacts remains deferred
