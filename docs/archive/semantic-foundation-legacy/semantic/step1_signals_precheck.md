# Step1 Signals Implementation Readiness Check

**Review Date**: 2026-03-16
**Reviewer**: Claude Opus 4.6
**Review Target**: `step1_signals` implementation readiness

---

## Executive Summary

**Can Implement Step1 Signals**: ❌ **NO** (with blocking issue)

**Blocking Issue**: Primary FACT input files (`docs/fact/baseline/*.md`) do not exist

**Workaround Available**: ✅ **YES** - Can use `fact_canonical_sample.yaml` as sole primary input

**Recommendation**: Either generate baseline files from FACT pipeline, or modify Step1 to work with canonical YAML only

---

## Review Target

This precheck assesses whether `step1_signals` (Signal Inference) can be implemented now with low ambiguity.

**Question**: Can `step1_signals` be implemented now?

**Answer**: Not without modification - primary FACT baseline files are missing, but workarounds exist.

---

## Files Checked

### FACT Input Files (9 files)

**Primary Hard Inputs**:
1. ✅ `docs/semantic-foundation/fact/fact_canonical_sample.yaml` (11.8KB) - EXISTS
2. ❌ `docs/fact/baseline/purpose.md` - MISSING (directory empty)
3. ❌ `docs/fact/baseline/pipelines.md` - MISSING (directory empty)
4. ❌ `docs/fact/baseline/domains.md` - MISSING (directory empty)
5. ❌ `docs/fact/baseline/concepts.md` - MISSING (directory empty)

**Auxiliary Soft Inputs**:
6. ✅ `docs/semantic-foundation/fact/fact_working_summary_sample.yaml` (11.8KB) - EXISTS

**Reference Inputs**:
7. ✅ `docs/semantic-foundation/fact/fact_canonical_contract.md` (13.6KB) - EXISTS
8. ✅ `docs/semantic-foundation/fact/fact_contract_mapping.md` (11.3KB) - EXISTS
9. ✅ `docs/semantic-foundation/fact/fact_for_semantic_review.md` - EXISTS

---

### Semantic Documentation Files (6 files)

**Contract Documents**:
1. ✅ `semantic_stage_contracts.md` - EXISTS, Step1 contract clearly defined
2. ✅ `semantic_input_contract.md` - EXISTS, input consumption rules clear
3. ✅ `semantic_output_contract.md` - EXISTS, output structure fully specified

**Design Documents**:
4. ✅ `01_step1_signal_inference.md` - EXISTS (359 lines), complete Step1 design
5. ✅ `semantic_runner_design.md` - EXISTS, runner behavior specified
6. ✅ `README.md` - EXISTS, workspace semantics clarified

---

### Implementation Dependencies (11 files)

**Prompt**:
1. ✅ `prompts/semantic/step1_signal_inference.prompt.md` - EXISTS, aligned with contract

**Template**:
2. ✅ `templates/semantic/signals.template.yaml` - EXISTS, aligned with output structure

**Code Files**:
3. ✅ `src/semantic/extract_signals.py` - EXISTS (scaffold only, needs implementation)
4. ✅ `src/semantic/models.py` - EXISTS (no Signal models yet)
5. ✅ `src/semantic/run.py` - EXISTS
6. ✅ `src/semantic/stage_registry.py` - EXISTS

**Test Files**:
7. ✅ `tests/semantic/test_layout.py` - EXISTS
8. ✅ `tests/semantic/test_runner_smoke.py` - EXISTS
9. ✅ `tests/semantic/fixtures/` - EXISTS

**Output Workspace**:
10. ❌ `docs/semantic/` - MISSING (needs to be created)

---

## FACT Input Readiness: PARTIAL

### Status: `partial`

### Assessment

**Primary Hard Inputs**:
- ✅ `fact_canonical_sample.yaml` EXISTS and is high quality (11.8KB)
- ❌ `docs/fact/baseline/*.md` files DO NOT EXIST (directory empty except .keep)

**Auxiliary Soft Inputs**:
- ✅ `fact_working_summary_sample.yaml` EXISTS and is high quality (11.8KB)

**Reference Inputs**:
- ✅ All reference docs exist and are high quality

### Issue

The Step1 contract (`semantic_stage_contracts.md`) specifies:

```yaml
Primary Inputs:
- docs/fact/baseline/purpose.md
- docs/fact/baseline/pipelines.md
- docs/fact/baseline/domains.md
- docs/fact/baseline/concepts.md
- fact_canonical_sample.yaml
```

**Reality**: Only `fact_canonical_sample.yaml` exists. The baseline markdown files do not exist.

### Impact

**Blocking**: Step1 cannot run as specified in the contract without baseline files.

**Workaround**: Step1 can be modified to work with `fact_canonical_sample.yaml` as the sole primary input.

---

## Semantic Doc Readiness: PASS

### Status: `pass`

### Assessment

All semantic documentation is present and sufficient:

1. **semantic_stage_contracts.md**: Step1 contract clearly defined
   - Goal: Extract semantic signals from FACT layer
   - Inputs: Primary (baseline + canonical), Auxiliary (working summary)
   - Outputs: signals.yaml
   - Signal groups: domain_signals, concept_signals, rule_signals, demand_pattern_signals
   - Program/Model/Human responsibilities clearly separated
   - Blocking rules specified

2. **semantic_input_contract.md**: Input consumption rules clear
   - Primary hard input: canonical facts
   - Auxiliary soft input: working summary
   - Conflict resolution: canonical wins
   - Forbidden assumptions documented

3. **semantic_output_contract.md**: Output structure fully specified
   - signals.yaml structure defined
   - signals.md view output defined
   - Required fields documented

4. **01_step1_signal_inference.md**: Complete Step1 design (359 lines)
   - Goal, inputs, outputs clearly defined
   - Signal types explained (domain, concept, rule, demand model)
   - Program/Model responsibilities detailed
   - Blocking rules specified
   - Implementation guidance provided

5. **semantic_runner_design.md**: Runner behavior specified
   - next/all modes defined
   - State management specified
   - Blocking rules documented

6. **README.md**: Workspace semantics clarified
   - Three workspaces distinguished
   - Canonical layer name: semantic
   - Output location: docs/semantic/

### Conclusion

Semantic documentation is **ready for implementation**. No gaps or ambiguities found.

---

## Prompt/Template Alignment: PASS

### Status: `pass`

### Assessment

**Prompt** (`prompts/semantic/step1_signal_inference.prompt.md`):
```
Goal:
Convert fact-layer inputs into `signals.yaml`.

Pipeline:
- program: normalize inputs
- model: infer fact clusters and implicit semantic signals
- program: validate schema and write canonical YAML

Output groups:
- domain_signals
- concept_signals
- rule_signals
- demand_pattern_signals
```

**Template** (`templates/semantic/signals.template.yaml`):
```yaml
domain_signals: []
concept_signals: []
rule_signals: []
demand_pattern_signals: []
```

**Contract** (`semantic_stage_contracts.md`):
```yaml
signals:
  domain_signals:
    - signal_type: string
      evidence: string
      confidence: string
  concept_signals: [...]
  rule_signals: [...]
```

### Alignment Check

✅ **Prompt matches contract**: Output groups align (domain/concept/rule/demand_pattern)
✅ **Template matches contract**: Structure aligns with expected output
✅ **Prompt matches template**: Both use same 4 signal groups

### Conclusion

Prompt and template are **fully aligned** with contracts. No changes needed.

---

## Code Skeleton Readiness: PARTIAL

### Status: `partial`

### Assessment

**Code Files**:

1. **src/semantic/extract_signals.py** (25 lines)
   - ✅ Scaffold exists
   - ✅ CLI argument parsing present
   - ✅ Output directory creation logic present
   - ❌ Only writes empty signal groups (scaffold only)
   - ❌ No actual signal extraction logic

2. **src/semantic/models.py** (56 lines)
   - ✅ Pydantic models exist
   - ✅ RecommendationItem model defined (for Step3)
   - ❌ No Signal models defined
   - ❌ No DomainSignal, ConceptSignal, RuleSignal, DemandPatternSignal models

3. **src/semantic/run.py** (exists)
   - ✅ Runner exists
   - Status: Not inspected in detail (assumed functional)

4. **src/semantic/stage_registry.py** (exists)
   - ✅ Registry exists
   - Status: Not inspected in detail (assumed functional)

**Test Files**:

1. **tests/semantic/test_layout.py** (exists)
   - ✅ Layout tests exist

2. **tests/semantic/test_runner_smoke.py** (exists)
   - ✅ Smoke tests exist

3. **tests/semantic/fixtures/** (exists)
   - ✅ Fixtures directory exists

4. **tests/semantic/test_extract_signals.py** (MISSING)
   - ❌ No step1-specific tests

### Gaps

1. **extract_signals.py needs full implementation**
   - Current: Scaffold that writes empty signal groups
   - Needed: Full signal extraction logic from FACT inputs

2. **models.py needs Signal models**
   - Current: Only RecommendationItem model
   - Needed: Signal, DomainSignal, ConceptSignal, RuleSignal, DemandPatternSignal models

3. **No step1-specific tests**
   - Current: Only layout and smoke tests
   - Needed: test_extract_signals.py with signal extraction tests

### Conclusion

Code skeleton is **partially ready**. Scaffold exists but needs full implementation.

---

## Gaps

### High Priority Gaps

1. **docs/fact/baseline/*.md files missing**
   - Severity: HIGH (blocking)
   - Impact: Step1 contract requires these as primary input
   - Workaround: Use fact_canonical_sample.yaml only

2. **docs/semantic/ output workspace missing**
   - Severity: HIGH (blocking)
   - Impact: Step1 needs to write outputs here
   - Fix: Create directory before running Step1

### Medium Priority Gaps

3. **src/semantic/models.py lacks Signal models**
   - Severity: MEDIUM
   - Impact: Implementation needs Signal models for type safety
   - Fix: Add Signal, DomainSignal, ConceptSignal, RuleSignal, DemandPatternSignal models

4. **src/semantic/extract_signals.py is scaffold only**
   - Severity: MEDIUM
   - Impact: No actual signal extraction logic
   - Fix: Implement full signal extraction from FACT inputs

### Low Priority Gaps

5. **No step1-specific tests**
   - Severity: LOW
   - Impact: Cannot verify Step1 behavior
   - Fix: Add test_extract_signals.py

---

## Blocking Issues

### Issue 1: Primary FACT Input Missing

**Issue**: `docs/fact/baseline/*.md` files do not exist

**Contract Requirement**:
```yaml
Primary Inputs:
- docs/fact/baseline/purpose.md
- docs/fact/baseline/pipelines.md
- docs/fact/baseline/domains.md
- docs/fact/baseline/concepts.md
```

**Reality**: Directory exists but is empty (only .keep file)

**Impact**: Step1 cannot run as specified in the contract

**Blocking**: YES

---

### Issue 2: Output Workspace Missing

**Issue**: `docs/semantic/` directory does not exist

**Contract Requirement**: Step1 writes `signals.yaml` to `docs/semantic/`

**Reality**: Directory does not exist

**Impact**: Step1 will fail when trying to write output

**Blocking**: YES (but easy to fix)

---

## Recommended Fixes

### Fix 1: Resolve Baseline Files Issue (HIGH PRIORITY)

**Target**: `docs/fact/baseline/*.md`

**Issue**: Baseline files do not exist

**Options**:

**Option A: Run FACT Pipeline**
- Run `discover → review → refine → baseline` to generate baseline files
- Pros: Generates real baseline from actual repository
- Cons: Requires full FACT pipeline execution

**Option B: Create Sample Baseline Files**
- Generate sample baseline files from `fact_canonical_sample.yaml`
- Pros: Quick, allows Step1 testing
- Cons: Sample data only, not real baseline

**Option C: Modify Step1 Contract**
- Update Step1 to work with `fact_canonical_sample.yaml` only
- Make baseline/*.md optional instead of required
- Pros: Simplifies Step1, removes dependency on baseline files
- Cons: Changes contract, may reduce signal quality

**Recommendation**: **Option C** - Modify Step1 to work with canonical YAML only
- Rationale: fact_canonical_sample.yaml contains all necessary information
- Baseline markdown files are human-readable views, not required for signal extraction
- Simplifies implementation and removes blocking dependency

---

### Fix 2: Create Output Workspace (HIGH PRIORITY)

**Target**: `docs/semantic/`

**Issue**: Output workspace does not exist

**Fix**: Create directory
```bash
mkdir -p docs/semantic
```

**Impact**: Unblocks Step1 output writing

---

### Fix 3: Add Signal Models (MEDIUM PRIORITY)

**Target**: `src/semantic/models.py`

**Issue**: No Signal models defined

**Fix**: Add Signal models
```python
class Signal(BaseModel):
    signal_type: str
    source: str
    evidence: str
    confidence: Literal["high", "medium", "low"]

class DomainSignal(Signal):
    pass

class ConceptSignal(Signal):
    pass

class RuleSignal(Signal):
    pass

class DemandPatternSignal(Signal):
    pass
```

**Impact**: Enables type-safe signal extraction

---

### Fix 4: Implement Signal Extraction (MEDIUM PRIORITY)

**Target**: `src/semantic/extract_signals.py`

**Issue**: Only scaffold implementation exists

**Fix**: Implement full signal extraction logic
- Parse fact_canonical_sample.yaml
- Extract domain signals (module groupings, entrypoint clusters)
- Extract concept signals (entity definitions, terminology patterns)
- Extract rule signals (validation logic, constraints)
- Extract demand pattern signals (change analysis patterns)
- Assign confidence ratings
- Write signals.yaml

**Impact**: Enables actual Step1 execution

---

### Fix 5: Add Step1 Tests (LOW PRIORITY)

**Target**: `tests/semantic/test_extract_signals.py`

**Issue**: No step1-specific tests

**Fix**: Add test_extract_signals.py
- Test signal extraction from sample FACT inputs
- Test confidence rating assignment
- Test output YAML structure
- Test view markdown generation

**Impact**: Enables Step1 verification

---

## Alternative Approaches

### Approach 1: Use fact_canonical_sample.yaml as Sole Primary Input

**Feasibility**: HIGH

**Changes Required**:
1. Update `semantic_stage_contracts.md` to make baseline/*.md optional
2. Update `01_step1_signal_inference.md` to clarify canonical YAML is sufficient
3. Implement `extract_signals.py` to parse YAML directly

**Pros**:
- Removes dependency on baseline files
- Simplifies Step1 implementation
- fact_canonical_sample.yaml contains all necessary information

**Cons**:
- Changes contract (minor)
- May reduce signal quality if baseline markdown provides additional context

**Recommendation**: **PREFERRED** - This is the cleanest approach

---

### Approach 2: Generate Sample Baseline Files

**Feasibility**: HIGH

**Changes Required**:
1. Create `docs/fact/baseline/purpose.md` from canonical YAML
2. Create `docs/fact/baseline/pipelines.md` from canonical YAML
3. Create `docs/fact/baseline/domains.md` from canonical YAML
4. Create `docs/fact/baseline/concepts.md` from canonical YAML

**Pros**:
- No contract changes needed
- Allows Step1 to run as specified

**Cons**:
- Sample data only, not real baseline
- Extra work to generate sample files
- Duplicates information already in canonical YAML

**Recommendation**: **ACCEPTABLE** - If contract changes are not desired

---

### Approach 3: Run Full FACT Pipeline

**Feasibility**: MEDIUM

**Changes Required**:
1. Run `discover` to generate discovery artifacts
2. Run `review` to present facts for architect validation
3. Run `refine` to apply corrections
4. Run `baseline` to synthesize baseline files

**Pros**:
- Generates real baseline from actual repository
- No contract changes needed
- Produces high-quality baseline

**Cons**:
- Requires full FACT pipeline execution
- Time-consuming
- May not be necessary for Step1 testing

**Recommendation**: **DEFERRED** - Only if real baseline is needed for production

---

## Final Decision

**Can Implement Step1 Signals**: ❌ **NO** (with blocking issue)

**Blocking Reason**: Primary FACT input (`docs/fact/baseline/*.md`) does not exist

**Workaround Available**: ✅ **YES**

**Recommended Workaround**: Modify Step1 to use `fact_canonical_sample.yaml` as sole primary input

**Implementation Path**:
1. Create `docs/semantic/` output workspace
2. Update Step1 contract to make baseline/*.md optional
3. Implement `extract_signals.py` to parse canonical YAML
4. Add Signal models to `models.py`
5. Add step1-specific tests

**Estimated Effort**: 2-4 hours (with workaround)

---

## Summary

### Are FACT inputs ready for Step1?

**PARTIALLY** - `fact_canonical_sample.yaml` exists and is high quality, but baseline markdown files are missing.

### Are semantic docs ready for Step1?

**YES** - All semantic documentation is present, clear, and sufficient for implementation.

### Is the Step1 prompt aligned?

**YES** - Prompt, template, and contract are fully aligned.

### Can Step1 implementation start now?

**NO** - Blocked by missing baseline files, but workaround available (use canonical YAML only).

---

**Precheck Completed**: 2026-03-16
**Reviewer**: Claude Opus 4.6
**Result**: ❌ BLOCKED (workaround available)