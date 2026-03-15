# Stage 2 — IBS Core Report

## Scope

Implemented Stage 2 IBS Core only:

- `purpose.md`
- `pipelines.md`
- `domains.md`
- `concepts.md`

Excluded by design:

- change-analysis
- implementation-plan
- runtime architecture redesign

## Delivered Changes

1. Mapping specification
   - Added `docs/review/stage2_ibs_core_mapping.md`.
   - Documents FACT -> IBS Core mapping for purpose/pipelines/domains/concepts.
   - Defines explicit IBS Core file contracts used as implementation source of truth.

2. IBS Core templates
   - Added:
     - `docs/semantic/templates/purpose.template.md`
     - `docs/semantic/templates/pipelines.template.md`
     - `docs/semantic/templates/domains.template.md`
     - `docs/semantic/templates/concepts.template.md`
   - Contracts aligned to:
     - purpose: `Primary Purpose`, `Supported Scenarios`, `Non Goals`
     - pipelines: `Pipeline Name`, `Purpose`, `Flow`, `Inputs`, `Outputs`, `Concepts`, `Evidence`, `Confidence`
     - domains: `Domain Name`, `Description`, `Related Pipelines`
     - concepts: `Concept Name`, `Description`, `Role`, `Used By`, `Evidence`, `Confidence`

3. IBS Core generation + validation modules
   - Added `src/ibs_core_generator.py`
     - `generate_ibs_core(...)` synthesizes the 4 IBS Core outputs from FACT artifacts.
   - Added `src/ibs_core_validation.py`
     - `validate_ibs_core_outputs(...)` validates generated outputs with existing baseline keyword contracts.

4. Refine/baseline integration
   - Updated `src/refine_executor.py` baseline step:
     - Keeps existing baseline parser/validator gate behavior unchanged.
     - After gate pass, synthesizes IBS Core outputs from FACT artifacts.
     - Validates IBS Core outputs and writes baseline files.

5. Stage 2 tests
   - Added `tests/test_stage2_ibs_core.py`:
     - mapping spec presence
     - IBS templates contract checks
    - generator output validation
    - refine integration writes IBS Core baseline outputs

6. Stage 2 revision hardening
   - Deterministic extraction precedence in `src/ibs_core_generator.py`:
     - removed set-based heading lookup
     - enforced ordered heading precedence from mapping contracts
   - Mapping spec alignment:
     - revised purpose mapping text to reflect current implementation
       (no direct `knowledge-confidence` overlay in `purpose.md`)
   - Validation hardening in `src/ibs_core_validation.py`:
     - keeps baseline keyword checks
     - adds required field-label checks per artifact
     - adds minimal structure checks (list blocks / at-least-one section checks)
   - Stage 2 tests expanded:
     - deterministic precedence behavior
     - field-level FACT -> IBS mapping assertions
     - rejection cases for missing required structure

## Compatibility Notes

- Existing artifact validators were not changed.
- Existing templates were not changed for this stage's runtime behavior.
- Existing baseline parser contract was preserved.
- Existing failure semantics remain intact (invalid baseline prompt output still blocks baseline write).

`tests/fake_executors.py` did not require changes for Stage 2.

## Files Added

- `docs/review/stage2_ibs_core_mapping.md`
- `docs/review/stage2_ibs_core_report.md`
- `docs/semantic/templates/purpose.template.md`
- `docs/semantic/templates/pipelines.template.md`
- `docs/semantic/templates/domains.template.md`
- `docs/semantic/templates/concepts.template.md`
- `src/ibs_core_generator.py`
- `src/ibs_core_validation.py`
- `tests/test_stage2_ibs_core.py`

## Files Modified

- `src/refine_executor.py`
- `src/ibs_core_generator.py` (revision hardening)
- `src/ibs_core_validation.py` (revision hardening)
- `tests/test_stage2_ibs_core.py` (revision hardening)
- `docs/review/stage2_ibs_core_mapping.md` (implementation alignment)

## Test Result

- `pytest -q`
- Result: **233 passed, 0 failed**

Stage 2 IBS Core generation is complete and validated.

## Remaining Gaps

- IBS Core validation remains structural/contract-focused, not semantic-quality scoring.
- FACT validators are still "has any recognized heading" style from Stage 1.
- Generator heuristics are intentionally minimal and do not perform deep semantic reconciliation.

## Deferred To Later Stages

- change-analysis artifacts and validation
- implementation-plan artifacts and validation
- stronger cross-artifact semantic consistency enforcement beyond Stage 2 scope
