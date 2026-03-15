# Stage 3 — Change Analysis Report

## Scope

Implemented Stage 3 minimum bridge only:

`IBS Core -> change-analysis`

Current semantics in this implementation:

- generic semantic impact analysis derived from IBS Core
- no explicit external change-context/request input path yet

Out of scope (deferred to later stages):

- implementation-plan generation
- full IBS analysis pack
- runtime architecture redesign
- discovery pipeline changes
- public skill interface changes

## Files Modified

- `docs/review/stage3_change_analysis_mapping.md`
- `docs/review/stage3_change_analysis_report.md`
- `tests/test_stage3_change_analysis.py`

## Previously Added in Stage 3

- `docs/review/stage3_change_analysis_mapping.md`
- `docs/semantic-design/012-change-analysis-output-model.md`
- `docs/semantic/templates/change-analysis.template.md`
- `src/change_analysis_generator.py`
- `src/change_analysis_validation.py`
- `src/refine_executor.py`
- `src/context_builder.py`
- `docs/semantic/templates/README.md`
- `tests/test_stage3_change_analysis.py`

## Mapping Summary

Stage 3 mapping source is documented in:

- `docs/review/stage3_change_analysis_mapping.md`

IBS Core -> change-analysis mapping:

- `purpose.md` -> `Change Intent`
- `pipelines.md` -> `Affected Pipelines` (pipeline names only)
- `domains.md` + `concepts.md` -> `Affected Domains and Concepts`
- `pipelines.md` + `concepts.md` confidence markers -> `Impact and Risks`
- all IBS Core artifacts -> `Suggested Next Changes`

Mapping corrections in this revision:

- removed over-claim that Stage 3 generates per-pipeline purpose/flow impact notes
- clarified current Stage 3 output as IBS-grounded generic analysis, not request-specific analysis

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

## Tests Added / Strengthened

`tests/test_stage3_change_analysis.py` verifies:

- Stage 3 mapping doc exists and contains required mapping concepts
- Stage 3 design doc exists
- `change-analysis.template.md` passes validator
- IBS Core field mapping into all required change-analysis sections
- same IBS Core input produces identical change-analysis output (repeatability)
- validator rejects missing required structure
- refine integration generates `change-analysis.v1.md` from IBS Core baseline
- post-baseline Stage 3 failure path is explicit (`status=validation_failed`) while baseline artifacts remain written

## Pytest Result

Commands run:

- `pytest tests/test_stage3_change_analysis.py -q`
- `pytest -q --maxfail=1`

Result:

- `tests/test_stage3_change_analysis.py`: **8 passed**
- full suite: **245 passed, 0 failed**

## Remaining Gaps (Deferred to Stage 4+)

- implementation-plan generation is not implemented
- change-analysis does not yet emit structured implementation tasks
- no request-context ingestion path for request-specific change analysis
- no full analysis-pack decomposition (kept intentionally minimal in Stage 3)
- deeper semantic-quality scoring across artifacts remains deferred

## Failure-Path Note

Current behavior when Stage 3 fails after successful baseline generation:

- refine result returns `validation_failed`
- IBS Core baseline files remain written
- `change-analysis.vN.md` is not written
- baseline checkpoint write is skipped because it occurs after successful Stage 3 completion

Checkpoint/baseline consistency policy for this edge case is deferred to Stage 4+.
