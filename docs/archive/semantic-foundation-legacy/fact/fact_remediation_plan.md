# FACT Remediation Plan

**Date**: 2026-03-16
**Status**: COMPLETED
**Review Source**: `fact_for_semantic_review.yaml`

---

## Executive Summary

This document records the FACT remediation work completed to improve FACT layer quality and prepare it as a cleaner input for the future SEMANTIC layer.

**Review Conclusion**:
- overall_status: pass_with_gaps
- can_enter_semantic: true
- should_split_fact_yaml: true

**Remediation Objective**: Split mixed FACT outputs into canonical facts and working summary, freeze canonical contract, and reduce interpretation leakage.

---

## Remediation Tasks Completed

### Task 1: Split Mixed FACT YAML ✅

**Problem**: Original `fact_expected_sample.yaml` mixed observable facts with interpretation.

**Solution**: Split into two files:
- `fact_canonical_sample.yaml` (12KB) - Observable facts only
- `fact_working_summary_sample.yaml` (12KB) - Interpretation and analysis

**Result**: Clear separation between hard facts and soft interpretation.

---

### Task 2: Tighten Canonical Fact ✅

**Problem**: Canonical contained interpretation-heavy fields (purpose, role, domain proposals).

**Solution**: Removed all interpretation from canonical:
- ❌ Removed: `purpose`, `role`, `used_by`, `domain_proposals`, `open_questions`
- ✅ Kept: `modules`, `entrypoints`, `evidence`, `version_metadata`

**Result**: Canonical is now low-ambiguity, observable-only.

---

### Task 3: Move Interpretation to Working Summary ✅

**Problem**: Interpretation was mixed with facts.

**Solution**: Moved all interpretation to working summary:
- ✅ `system_purpose.interpreted_purpose`
- ✅ `concepts.interpreted_role`
- ✅ `domain_proposals`
- ✅ `open_questions`
- ✅ `assumptions`
- ✅ `confidence_assessment`

**Result**: Working summary holds all soft, interpretive content.

---

### Task 4: Freeze Canonical Contract ✅

**Problem**: No frozen schema contract for canonical facts.

**Solution**: Created `fact_canonical_contract.md` (13KB) with:
- Top-level schema definition
- Required/optional/forbidden fields
- Evidence requirements
- Stability guarantees
- Version evolution policy

**Result**: Canonical contract is FROZEN (breaking changes require major version bump).

---

### Task 5: Add Mapping Documentation ✅

**Problem**: No clear mapping between old artifacts and new split.

**Solution**: Created `fact_contract_mapping.md` (11KB) with:
- Observable vs Interpreted rules
- Structure vs Meaning rules
- Evidence vs Analysis rules
- Field-by-field mapping table
- Migration examples

**Result**: Clear guidance on what goes where.

---

### Task 6: Update Naming/Explanation Docs ✅

**Problem**: Docs didn't reflect split.

**Solution**: Updated:
- `fact_expected_sample.md` - Added Section 5: FACT Output Split
- `fact_naming_mapping.md` - Added Section 8: FACT Output Split (2026-03-16 Update)

**Result**: Docs clearly explain canonical/working split.

---

## Remediation Actions Implemented

### From Review: 6 Recommended Actions

#### 1. Separate `repo_understanding` ✅
**Action**: separate
**Target**: repo_understanding
**Reason**: Split 'Purpose/Role/Used By' interpretation into working summary

**Implementation**:
- Canonical: Module names, paths, functions, evidence
- Working Summary: Purpose interpretation, role assignments, pipeline relationships

#### 2. Separate `domain_candidates` ✅
**Action**: separate
**Target**: domain_candidates
**Reason**: Move domain identification to working summary

**Implementation**:
- Canonical: Module boundaries (observable)
- Working Summary: Domain proposals (interpretation)

#### 3. Clarify `confidence_placement` ✅
**Action**: clarify
**Target**: confidence_placement
**Reason**: Decide whether confidence is inline or separate artifact

**Implementation**:
- Decision: Confidence in working summary only
- Canonical: No confidence ratings
- Working Summary: `confidence_assessment` section

#### 4. Separate `open_questions` ✅
**Action**: separate
**Target**: open_questions
**Reason**: Move 'Open Questions' to working summary

**Implementation**:
- Canonical: No open questions
- Working Summary: `open_questions` section with context and rationale

#### 5. Freeze `canonical_schema` ✅
**Action**: freeze_contract
**Target**: canonical_schema
**Reason**: Define strict canonical schema with only observable facts

**Implementation**:
- Created `fact_canonical_contract.md`
- Defined frozen schema with stability guarantees
- Documented forbidden fields

#### 6. Add `canonical_to_working` mapping ✅
**Action**: add_mapping
**Target**: canonical_to_working
**Reason**: Document which fields go to canonical vs working summary

**Implementation**:
- Created `fact_contract_mapping.md`
- Defined 4 mapping rules (Observable vs Interpreted, Structure vs Meaning, Evidence vs Analysis, Existence vs Relationship)
- Provided field-by-field mapping table

---

## Files Created/Modified

### New Files (8)

1. `docs/semantic-foundation/fact/fact_canonical_sample.yaml` (12KB)
2. `docs/semantic-foundation/fact/fact_working_summary_sample.yaml` (12KB)
3. `docs/semantic-foundation/fact/fact_canonical_contract.md` (13KB)
4. `docs/semantic-foundation/fact/fact_contract_mapping.md` (11KB)
5. `docs/semantic-foundation/fact/fact_for_semantic_review.md` (18KB)
6. `docs/semantic-foundation/fact/fact_for_semantic_review.yaml` (5.3KB)
7. `templates/fact/fact-canonical.template.yaml` (5.6KB)
8. `templates/fact/fact-working-summary.template.yaml` (6.7KB)

### Modified Files (2)

1. `docs/semantic-foundation/fact/fact_expected_sample.md` - Added split explanation
2. `docs/semantic-foundation/fact/fact_naming_mapping.md` - Added split documentation

### Legacy Files (Kept for Reference)

1. `docs/semantic-foundation/fact/fact_expected_sample.yaml` (21KB) - Marked as legacy mixed sample

---

## Semantic Consumption Guidelines

### Primary Input: Canonical Facts (Hard Input)

**File**: `fact_canonical_sample.yaml`

**Semantic MUST consume**:
- `repo_identity` - Repository metadata
- `modules` - Observable code structure
- `entrypoints` - Execution entry points
- `core_entities` - Data structures
- `configuration` - Config files
- `dependencies` - Imports and packages
- `execution_flows` - Observable call chains
- `baseline_reference` - Checkpoint metadata

**Consumption rule**: Trust as hard facts, use evidence refs for validation.

### Auxiliary Input: Working Summary (Soft Input)

**File**: `fact_working_summary_sample.yaml`

**Semantic MAY consume**:
- `system_purpose` - For context only
- `domain_proposals` - As hints, not truth
- `open_questions` - For awareness
- `assumptions` - For validation

**Consumption rule**: Use as guidance/bootstrap context, do not treat as hard truth.

### Conflict Resolution

**Rule**: When canonical and working summary conflict, **canonical wins**.

---

## Quality Metrics

### Canonical Purity

**Before**: partial (mixed interpretation)
**After**: pass (observable-only)

**Improvements**:
- Removed all `purpose`, `role`, `used_by` fields
- Removed `domain_proposals` from canonical
- Removed `open_questions` from canonical
- All fields now have evidence refs

### Structure Stability

**Before**: pass
**After**: pass (frozen contract)

**Improvements**:
- Canonical contract frozen
- Breaking changes require major version bump
- Schema evolution policy documented

### Working Summary Separation

**Before**: partial (not separated)
**After**: pass (fully separated)

**Improvements**:
- Working summary is distinct file
- Clear boundary rules documented
- Mapping table provided

### Semantic Minimum Input Completeness

**Before**: pass
**After**: pass (improved)

**Improvements**:
- Canonical provides all minimum inputs
- Working summary provides auxiliary context
- Consumption guidelines clear

---

## Impact Assessment

### Runtime Impact

**Pipeline Behavior**: ✅ UNCHANGED
- `discover → review → refine → baseline` flow unchanged
- All 237 tests passing
- No code changes to executors

### Documentation Impact

**Documentation**: ✅ IMPROVED
- 8 new files created
- 2 files updated
- Clear split explanation
- Frozen contract

### Public API Impact

**Public Skills**: ✅ UNCHANGED
- No skill renames
- Manifest unchanged
- Backward compatible

---

## Remaining Technical Debt

### Low Priority

1. **Test Coverage**: `tests/fact/test_fact_canonical_contract.py` not created (optional)
2. **Runtime Generation**: Pipeline doesn't yet generate split outputs (documentation only)
3. **Schema Validation**: No YAML schema validator implemented (can add later)

### No Blockers

All critical work completed:
- ✅ Split completed
- ✅ Contract frozen
- ✅ Mapping documented
- ✅ Templates created

---

## Verification Checklist

- ✅ Canonical sample contains only observable facts
- ✅ Working summary contains all interpretation
- ✅ Canonical contract is frozen
- ✅ Mapping documentation is clear
- ✅ Templates are usable
- ✅ All tests passing (237/237)
- ✅ No runtime changes
- ✅ No public API changes
- ✅ Git committed (a4d349d)

---

## Next Steps for Semantic Layer

### When Implementing Semantic

1. **Read canonical first**: `fact_canonical_sample.yaml` is primary input
2. **Use working summary as context**: Don't trust blindly
3. **Respect frozen contract**: Canonical schema is stable
4. **Validate with evidence**: All canonical facts have evidence refs
5. **Prefer canonical on conflict**: Canonical wins over working summary

### Semantic Should NOT

- ❌ Mix interpretation back into canonical
- ❌ Treat working summary as hard truth
- ❌ Break canonical contract
- ❌ Ignore evidence refs

---

## Conclusion

**FACT remediation completed successfully.**

**Benefits**:
- Clearer separation between facts and interpretation
- Improved semantic input quality
- Frozen canonical contract
- Better FACT purity
- Lower ambiguity for future semantic work

**Status**: READY FOR SEMANTIC LAYER IMPLEMENTATION

**Commit**: `a4d349d` - feat: split FACT outputs into canonical and working summary

**Date Completed**: 2026-03-16
