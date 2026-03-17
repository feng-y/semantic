# Step1 Signals Contract Fix Result

**Fix Date**: 2026-03-16
**Reviewer**: Claude Opus 4.6
**Fix Target**: Step1 signals contract and documentation

---

## Executive Summary

**Step1 Contract Ready for Implementation**: ✅ **YES**

**Can Implement Immediately**: ✅ **YES**

All Step1 input/workspace inconsistencies have been fixed. Step1 can now be implemented using `fact_canonical_sample.yaml` as the primary input, with baseline files as optional reference only.

---

## Fix Target

This fix addressed the Step1 contract inconsistencies identified in `step1_signals_precheck.md`:

**Problem**: Step1 docs required `docs/fact/baseline/*.md` as primary input, but these files don't exist.

**Solution**: Made `fact_canonical_sample.yaml` the sole REQUIRED primary input, demoted baseline files to optional reference.

---

## Files Updated

### 1. semantic_stage_contracts.md

**Changes**:
- **Inputs section**: Restructured to clearly separate Primary Hard Input, Auxiliary Soft Input, and Reference Input
- **Primary Hard Input**: Changed from "baseline/*.md + canonical YAML" to "canonical YAML only"
- **Reference Input**: Moved baseline/*.md to optional reference input
- **Outputs section**: Added explicit location `docs/semantic-foundation/semantic/`
- **Program Responsibilities**: Updated to reflect new input priority
- **Blocking Rules**: Changed from "BLOCK if baseline missing" to "BLOCK if canonical YAML missing, WARN if baseline missing"
- **Signal groups**: Added `demand_pattern_signals` to output structure

**Before**:
```yaml
Primary:
- docs/fact/baseline/purpose.md
- docs/fact/baseline/pipelines.md
- docs/fact/baseline/domains.md
- docs/fact/baseline/concepts.md
- fact_canonical_sample.yaml

Blocking Rules:
- BLOCK if baseline files missing
```

**After**:
```yaml
Primary Hard Input:
- docs/semantic-foundation/fact/fact_canonical_sample.yaml (REQUIRED)

Auxiliary Soft Input:
- docs/semantic-foundation/fact/fact_working_summary_sample.yaml (optional)

Reference Input (optional):
- docs/fact/baseline/*.md (if available)

Blocking Rules:
- BLOCK if fact_canonical_sample.yaml missing
- WARN if baseline files missing
```

---

### 2. 01_step1_signal_inference.md

**Changes**:
- **Inputs section**: Completely restructured to match semantic_stage_contracts.md
- **Primary Hard Input**: Now clearly `fact_canonical_sample.yaml` with full content description
- **Auxiliary Soft Input**: Clearly marked as optional
- **Reference Input**: New section for baseline files (optional)
- **Outputs section**: Changed location from `docs/semantic/` to `docs/semantic-foundation/semantic/`
- **Program Responsibilities**: Updated to load canonical YAML (required), working summary (optional), baseline (optional)
- **Blocking Rules**: Changed to BLOCK only on canonical YAML missing, WARN on baseline missing

**Before**:
```
Primary Hard Input:
- docs/fact/baseline/*.md + fact_canonical_sample.yaml

Location: docs/semantic/

Blocking: BLOCK if baseline files missing
```

**After**:
```
Primary Hard Input:
- docs/semantic-foundation/fact/fact_canonical_sample.yaml (REQUIRED)

Auxiliary Soft Input:
- docs/semantic-foundation/fact/fact_working_summary_sample.yaml (optional)

Reference Input:
- docs/fact/baseline/*.md (optional, if available)

Location: docs/semantic-foundation/semantic/

Blocking: BLOCK if canonical YAML missing, WARN if baseline missing
```

---

### 3. semantic_runner_design.md

**Changes**:
- **State file location**: Changed from `docs/semantic/run-state.yaml` to `docs/semantic-foundation/semantic/run-state.yaml`
- **Workspace section**: Changed from `docs/semantic/` to `docs/semantic-foundation/semantic/`
- **Added note**: Clarified that `docs/semantic/` contains old FACT runtime artifacts (transitional naming)
- **Structure**: Added intermediate view outputs (signals.md, candidates.md, recommendations.md, review-note.md)

**Before**:
```
Path: docs/semantic/
```

**After**:
```
Path: docs/semantic-foundation/semantic/

Note: Do not confuse with docs/semantic/ which contains old FACT runtime artifacts (transitional naming).
```

---

### 4. semantic_output_contract.md

**Changes**:
- **Output Location section**: Changed from `docs/semantic/` to `docs/semantic-foundation/semantic/`
- **Added note**: Clarified transitional naming issue

**Before**:
```
Canonical outputs: docs/semantic/ or semantic workspace
View outputs: docs/semantic/*.md
```

**After**:
```
Canonical outputs: docs/semantic-foundation/semantic/ (semantic workspace)
View outputs: docs/semantic-foundation/semantic/*.md

Note: Do not confuse with docs/semantic/ which contains old FACT runtime artifacts (transitional naming).
```

---

## Normalization Decisions Applied

### Input Contract Normalization

**Primary Hard Input**: `docs/semantic-foundation/fact/fact_canonical_sample.yaml`
- This is the REQUIRED input
- Contains all observable facts
- Step1 BLOCKS if this is missing

**Auxiliary Soft Input**: `docs/semantic-foundation/fact/fact_working_summary_sample.yaml`
- This is OPTIONAL
- Provides interpretation and guidance
- Step1 WARNS if this is missing but can proceed

**Reference Input**: `docs/fact/baseline/*.md`
- This is OPTIONAL
- Used as additional reference if available
- Step1 WARNS if these are missing but can proceed

### Workspace Normalization

**Semantic Workspace**: `docs/semantic-foundation/semantic/`
- All Step1 outputs go here
- signals.yaml (canonical)
- signals.md (view)

**Old FACT Workspace**: `docs/semantic/`
- Contains old FACT runtime artifacts
- Transitional naming (should be `docs/fact/`)
- Not used by semantic layer

### Output Normalization

**Canonical Output**: `signals.yaml`
**View Output**: `signals.md`
**Location**: `docs/semantic-foundation/semantic/`

**Signal Groups**:
- domain_signals
- concept_signals
- rule_signals
- demand_pattern_signals

---

## Fixed Issues

### Issue 1: Baseline Files Required but Missing (HIGH)

**Problem**: Step1 contract listed `docs/fact/baseline/*.md` as primary input, but these files don't exist.

**Impact**: Step1 could not be implemented without generating baseline files first.

**Resolution**: Made `fact_canonical_sample.yaml` the sole REQUIRED primary input. Baseline files are now optional reference input.

**Result**: Step1 can be implemented immediately using canonical YAML.

---

### Issue 2: Blocking Rule Too Strict (HIGH)

**Problem**: Step1 blocking rule would BLOCK if baseline files missing.

**Impact**: Step1 would fail to run even though canonical YAML contains all necessary information.

**Resolution**: Changed blocking rule to BLOCK only if `fact_canonical_sample.yaml` missing, WARN if baseline files missing.

**Result**: Step1 can proceed without baseline files.

---

### Issue 3: Workspace Location Inconsistent (HIGH)

**Problem**: Docs referenced both `docs/semantic/` and `docs/semantic-foundation/semantic/` as output location.

**Impact**: Unclear where Step1 should write outputs.

**Resolution**: Normalized all docs to use `docs/semantic-foundation/semantic/` as semantic workspace. Added notes explaining that `docs/semantic/` is old FACT runtime artifacts.

**Result**: Clear, unambiguous output location.

---

### Issue 4: Program Responsibilities Assumed Baseline Required (MEDIUM)

**Problem**: Step1 program responsibilities said "Read FACT baseline files" without clarifying they're optional.

**Impact**: Implementation ambiguity about whether baseline files are required.

**Resolution**: Updated to "Load canonical YAML (required), working summary (optional), baseline files (optional reference)".

**Result**: Clear priority and optionality of inputs.

---

### Issue 5: Output Location Ambiguous (MEDIUM)

**Problem**: Multiple docs referenced `docs/semantic/` without clarifying it's old FACT workspace.

**Impact**: Confusion about semantic vs FACT workspaces.

**Resolution**: Added explicit notes in all docs clarifying `docs/semantic-foundation/semantic/` is semantic workspace, `docs/semantic/` is old FACT runtime artifacts.

**Result**: Clear workspace distinction.

---

### Issue 6: Signal Groups Incomplete (LOW)

**Problem**: `demand_pattern_signals` missing from semantic_stage_contracts.md output structure.

**Impact**: Minor inconsistency with other docs.

**Resolution**: Added `demand_pattern_signals` to output structure.

**Result**: Consistent signal groups across all docs.

---

## Remaining Risks

### Risk 1: Old FACT Runtime Still Uses docs/semantic/

**Description**: The old FACT runtime code may still write to `docs/semantic/`.

**Impact**: Low - this is intentional (transitional naming).

**Mitigation**: Documented clearly that `docs/semantic/` is old FACT workspace, not semantic layer workspace.

---

### Risk 2: Baseline Files May Be Generated Later

**Description**: FACT pipeline may generate baseline files in future.

**Impact**: Low - Step1 should use them as reference if available.

**Mitigation**: Step1 contract now treats baseline files as optional reference input. If they exist, Step1 can use them for additional context.

---

### Risk 3: Working Summary is Optional

**Description**: Step1 can proceed without `fact_working_summary_sample.yaml`.

**Impact**: Low - Step1 may have less context for signal inference.

**Mitigation**: Step1 warns if working summary is missing. Canonical YAML contains all necessary information for basic signal extraction.

---

## Key Questions Answered

### Is fact_canonical_sample.yaml now the Step1 primary input?

✅ **YES** - `docs/semantic-foundation/fact/fact_canonical_sample.yaml` is now the sole REQUIRED primary hard input for Step1.

### Is baseline markdown now reference-only?

✅ **YES** - `docs/fact/baseline/*.md` files are now optional reference input. Step1 can proceed without them.

### Is the semantic workspace now normalized?

✅ **YES** - All docs now consistently use `docs/semantic-foundation/semantic/` as the semantic workspace.

### Is Step1 now ready for implementation?

✅ **YES** - All contract inconsistencies are fixed. Step1 can be implemented immediately.

---

## Implementation Readiness Checklist

✅ **Primary input clear**: fact_canonical_sample.yaml is REQUIRED
✅ **Auxiliary input clear**: fact_working_summary_sample.yaml is optional
✅ **Reference input clear**: baseline/*.md is optional
✅ **Workspace clear**: docs/semantic-foundation/semantic/
✅ **Output files clear**: signals.yaml + signals.md
✅ **Blocking rules clear**: BLOCK on canonical YAML missing only
✅ **No ambiguity**: All contracts aligned

---

## Contract Changes Summary

### Input Contract

**Before**:
- Primary: baseline/*.md + canonical YAML (both required)
- Auxiliary: working summary

**After**:
- Primary Hard: canonical YAML only (REQUIRED)
- Auxiliary Soft: working summary (optional)
- Reference: baseline/*.md (optional)

### Blocking Rules

**Before**:
- BLOCK if baseline files missing
- BLOCK if canonical facts malformed

**After**:
- BLOCK if canonical YAML missing
- BLOCK if canonical YAML malformed
- WARN if working summary missing
- WARN if baseline files missing

### Workspace

**Before**:
- docs/semantic/ (ambiguous)

**After**:
- docs/semantic-foundation/semantic/ (clear)
- Note: docs/semantic/ is old FACT runtime artifacts

---

## Verification

✅ **fact_canonical_sample.yaml is primary**: Confirmed in all docs
✅ **baseline files are optional**: Confirmed in all docs
✅ **working summary is auxiliary**: Confirmed in all docs
✅ **workspace is normalized**: Confirmed in all docs
✅ **Step1 can run without baseline**: Confirmed by blocking rules

---

## Final Confirmation

✅ **Step1 code was NOT implemented** - This was documentation-only fix
✅ **Old FACT runtime behavior was NOT changed** - No code modifications
✅ **Demand was NOT implemented** - Out of scope

---

**Fix Completed**: 2026-03-16
**Result**: Step1 contract is now ready for implementation with low ambiguity