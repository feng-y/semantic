# Semantic Development Plan

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Implementation Roadmap

---

## Overview

This document defines the implementation phases for the SEMANTIC layer, from preflight checks to full validation.

**Total Phases**: 5 (Phase 0-4)

---

## Phase 0: Preflight

### Goal

Verify that the repository is ready for semantic implementation.

### Tasks

1. **Check FACT inputs**
   - Verify `fact_canonical_sample.yaml` exists
   - Verify `fact_working_summary_sample.yaml` exists
   - Verify `docs/fact/baseline/*.md` exists
   - Verify FACT contracts are frozen

2. **Check semantic target directories**
   - Verify `prompts/semantic/` exists
   - Verify `templates/semantic/` exists
   - Verify `src/semantic/` exists
   - Verify `tests/semantic/` exists
   - Verify `docs/semantic-foundation/semantic/` exists

3. **Check reference docs**
   - Verify `README.md` exists
   - Verify `USER_GUIDE.md` exists
   - Verify `IMPLEMENTATION_ORDER.md` exists

4. **Create preflight report**
   - `semantic_preflight_check.md`
   - `semantic_preflight_check.yaml`

### Deliverables

- ✅ `semantic_preflight_check.md`
- ✅ `semantic_preflight_check.yaml`

### Status

**COMPLETED** (2026-03-16)

---

## Phase 1: Bootstrap

### Goal

Set up semantic layer foundation: contracts, templates, and basic runner.

### Tasks

1. **Create semantic contracts**
   - `semantic_design.md` - Overall design
   - `semantic_stage_contracts.md` - Stage definitions
   - `semantic_input_contract.md` - Input consumption rules
   - `semantic_output_contract.md` - Output specifications
   - `semantic_runner_design.md` - Runner design
   - `semantic_dev_plan.md` - This document

2. **Verify templates**
   - Verify `templates/semantic/*.template.yaml` exist
   - Verify templates match output contracts

3. **Verify prompts**
   - Verify `prompts/semantic/*.prompt.md` exist
   - Verify prompts match stage contracts

4. **Create basic runner**
   - `src/semantic/run.py` - Main runner
   - `src/semantic/runner_models.py` - Runner models
   - `src/semantic/state_store.py` - State management
   - `src/semantic/stage_registry.py` - Stage registry

5. **Create basic tests**
   - `tests/semantic/test_runner_smoke.py` - Smoke tests
   - `tests/semantic/test_layout.py` - Layout tests

### Deliverables

- ✅ 6 contract documents
- ✅ 11 templates (verified)
- ✅ 8 prompts (verified)
- ✅ Basic runner code
- ✅ Basic tests

### Status

**IN PROGRESS** (contracts created, runner exists, tests exist)

---

## Phase 2: Stage Implementation

### Goal

Implement all 5 semantic stages.

### Tasks

#### Step 1: Signal Inference

**Files**:
- `src/semantic/extract_signals.py`
- `src/semantic/models.py` (signal models)

**Responsibilities**:
- Read FACT baseline files
- Parse canonical facts
- Extract semantic signals
- Assign confidence ratings
- Write `signals.yaml`

**Tests**:
- `tests/semantic/test_extract_signals.py`

#### Step 2: Candidate Synthesis

**Files**:
- `src/semantic/build_candidates.py`
- `src/semantic/models.py` (candidate models)

**Responsibilities**:
- Read `signals.yaml`
- Group signals into candidates
- Assign candidate names
- Collect evidence refs
- Write `candidates.yaml`

**Tests**:
- `tests/semantic/test_build_candidates.py`

#### Step 3: Scoring & Recommendation

**Files**:
- `src/semantic/score_recommend.py`
- `src/semantic/models.py` (recommendation models)

**Responsibilities**:
- Read `candidates.yaml`
- Calculate scores
- Rank candidates
- Generate rationales
- Write `recommendations.yaml`

**Tests**:
- `tests/semantic/test_score_recommend.py`

#### Step 4: Review & Evidence

**Files**:
- `src/semantic/review_models.py`
- `src/semantic/apply_review.py`
- `src/semantic/evidence_check.py`
- `src/semantic/models.py` (review models)

**Responsibilities**:
- Read `recommendations.yaml`
- Present for architect review
- Collect review decisions
- Validate evidence refs
- Write `review-decisions.yaml` and `evidence-checks.yaml`

**Tests**:
- `tests/semantic/test_review_models.py`
- `tests/semantic/test_evidence_check.py`

#### Step 5: Finalize

**Files**:
- `src/semantic/finalize_models.py`
- `src/semantic/finalize_assets.py`
- `src/semantic/models.py` (final models)

**Responsibilities**:
- Read `review-decisions.yaml`
- Check `verify_first_status`
- Generate final semantic models
- Write `domain-map.yaml`, `concept-map.yaml`, `rule-map.yaml`, `demand-model-map.yaml`
- Write `change-log.yaml`
- Generate markdown views

**Tests**:
- `tests/semantic/test_finalize_models.py`
- `tests/semantic/test_finalize_assets.py`

### Deliverables

- ✅ 5 stage implementations (exist)
- ⏳ Stage-specific tests (to be created)

### Status

**IN PROGRESS** (code exists, tests incomplete)

---

## Phase 3: Runner Integration

### Goal

Integrate all stages into runner with proper state management.

### Tasks

1. **Implement stage registry**
   - Register all 5 stages
   - Define stage dependencies
   - Define blocking rules

2. **Implement state management**
   - Read/write `run-state.yaml`
   - Track stage status
   - Log errors and warnings
   - Manage blocking issues

3. **Implement next mode**
   - Determine next incomplete stage
   - Execute stage
   - Update state
   - Stop

4. **Implement all mode**
   - Execute stages sequentially
   - Stop on blocking error
   - Handle human review wait
   - Complete or stop

5. **Implement finalize guard**
   - Check `verify_first_status`
   - Block Step5 if unresolved issues
   - Allow Step5 if resolved

### Deliverables

- ⏳ Stage registry implementation
- ⏳ State management implementation
- ⏳ Next/all mode implementation
- ⏳ Finalize guard implementation

### Status

**PENDING** (basic runner exists, full integration needed)

---

## Phase 4: Validation & Tests

### Goal

Comprehensive testing and validation of semantic layer.

### Tasks

1. **Unit tests**
   - Test each stage independently
   - Test models and data structures
   - Test state management
   - Test runner modes

2. **Integration tests**
   - Test full pipeline (Step1-5)
   - Test next mode
   - Test all mode
   - Test blocking scenarios
   - Test finalize guard

3. **End-to-end tests**
   - Test with real FACT inputs
   - Test with sample repository
   - Validate outputs against contracts
   - Verify DEMAND layer can consume outputs

4. **Documentation validation**
   - Verify all contracts are followed
   - Verify templates match contracts
   - Verify prompts match contracts
   - Update docs if needed

### Deliverables

- ⏳ Unit tests for all stages
- ⏳ Integration tests
- ⏳ End-to-end tests
- ⏳ Documentation validation

### Status

**PENDING**

---

## Deferred Items

### Items NOT in Current Scope

1. **DEMAND layer implementation**
   - Deferred until semantic is stable
   - Requires semantic models as input

2. **Public skill creation**
   - No `semantic-run` skill yet
   - Semantic is internal-only for now
   - May add skill later

3. **Old skill rename**
   - `semantic-discover` etc. remain FACT-layer skills
   - No rename planned
   - Naming is transitional but documented

4. **Manifest changes**
   - No manifest changes for semantic
   - Semantic is internal runtime only

5. **FACT runtime changes**
   - No changes to discover/review/refine/baseline
   - FACT remains stable

6. **Advanced features**
   - Incremental updates
   - Diff-based synthesis
   - Multi-repo support
   - Deferred to future versions

### Technical Debt

1. **Test coverage**
   - Stage-specific tests incomplete
   - Integration tests missing
   - End-to-end tests missing

2. **Error handling**
   - Basic error handling exists
   - Need more robust error recovery
   - Need better error messages

3. **Performance**
   - No performance optimization yet
   - May be slow on large repos
   - Deferred until functionality is stable

4. **Documentation**
   - Some prompts may need refinement
   - Some templates may need examples
   - User guide for semantic not written

---

## Implementation Order

### Recommended Sequence

1. ✅ **Phase 0: Preflight** (DONE)
2. 🔄 **Phase 1: Bootstrap** (IN PROGRESS)
   - ✅ Contracts created
   - ✅ Templates verified
   - ✅ Prompts verified
   - ✅ Basic runner exists
   - ✅ Basic tests exist
3. ⏳ **Phase 2: Stage Implementation** (NEXT)
   - Start with Step1 (signals)
   - Then Step2 (candidates)
   - Then Step3 (recommend)
   - Then Step4 (review)
   - Finally Step5 (finalize)
4. ⏳ **Phase 3: Runner Integration**
5. ⏳ **Phase 4: Validation & Tests**

### What NOT to Do Too Early

1. **Don't implement DEMAND** before semantic is stable
2. **Don't create public skills** before semantic is validated
3. **Don't rename old skills** (not needed, documented as transitional)
4. **Don't modify FACT runtime** (semantic is separate layer)
5. **Don't optimize performance** before functionality is complete

---

## Success Criteria

### Phase 1 Complete When

- ✅ All 6 contract documents exist
- ✅ All templates verified
- ✅ All prompts verified
- ✅ Basic runner can execute
- ✅ Basic tests pass

### Phase 2 Complete When

- All 5 stages implemented
- Each stage can execute independently
- Each stage produces correct output
- Stage-specific tests pass

### Phase 3 Complete When

- Runner can execute next mode
- Runner can execute all mode
- State management works correctly
- Finalize guard works correctly

### Phase 4 Complete When

- All unit tests pass
- All integration tests pass
- End-to-end tests pass
- Documentation validated

### Semantic Layer Complete When

- All phases complete
- DEMAND layer can consume semantic outputs
- No blocking issues
- Technical debt documented

---

## Current Status Summary

**Phase 0**: ✅ COMPLETED
**Phase 1**: 🔄 IN PROGRESS (80% complete)
**Phase 2**: ⏳ PENDING (code exists, tests needed)
**Phase 3**: ⏳ PENDING
**Phase 4**: ⏳ PENDING

**Next Step**: Complete Phase 1, then start Phase 2 (Step1 implementation).
