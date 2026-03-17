# Semantic Documentation Consistency Review

**Review Date**: 2026-03-16
**Reviewer**: Claude Opus 4.6
**Review Target**: Semantic documentation set for implementation readiness

---

## Executive Summary

**Overall Status**: PASS WITH GAPS

**Can Implementation Start**: ✅ **YES**

**Docs Ready for Implementation**: ✅ **YES** (with known gaps)

The semantic documentation set is **internally consistent enough** to support implementation. The core contracts (stage contracts, input contract, output contract, runner design) are well-defined and aligned with FACT input assumptions. However, there are **naming drifts**, **language barriers**, and **missing design docs** that should be addressed to improve implementation clarity.

---

## Review Target

This review assesses whether the current semantic documentation is:
1. Internally consistent
2. Aligned with FACT input assumptions
3. Strong enough to support correct semantic implementation
4. Free from major contradictions, duplication, or ambiguity

---

## Reviewed Documents

### Semantic Contract Documents (6 files)
1. `semantic_design.md` - Overall semantic layer design
2. `semantic_stage_contracts.md` - 5-stage definitions with contracts
3. `semantic_input_contract.md` - FACT input consumption rules
4. `semantic_output_contract.md` - 11 canonical + 4 view outputs
5. `semantic_runner_design.md` - Runner modes and state management
6. `semantic_dev_plan.md` - Implementation phases and roadmap

### Semantic Preflight Documents (2 files)
7. `semantic_preflight_check.md` - Readiness assessment
8. `semantic_preflight_check.yaml` - Structured preflight result

### Semantic Design Documents (6 files)
9. `README.md` - Semantic workspace overview
10. `00_overall_design.md` - Overall design (Chinese, uses 'semantic_asset_build')
11. `01_step2_candidate_synthesis.md` - Step2 design (Chinese)
12. `01_step2_candidate_synthesis_prompt.md` - Step2 prompt (Chinese)
13. `02_step3_scoring_design.md` - Step3 design
14. `03_step4_review_and_evidence_design.md` - Step4 design
15. `04_step5_finalize_design.md` - Step5 design

### FACT Input Documents (9 files)
16. `fact_expected_sample.md` - FACT layer specification
17. `fact_expected_sample.yaml` - Legacy mixed FACT sample (21KB)
18. `fact_naming_mapping.md` - FACT naming and layer boundaries
19. `fact_for_semantic_review.md` - FACT readiness review
20. `fact_for_semantic_review.yaml` - Structured review result
21. `fact_canonical_sample.yaml` - Canonical facts (12KB)
22. `fact_working_summary_sample.yaml` - Working summary (12KB)
23. `fact_contract_mapping.md` - Canonical/working boundary rules
24. `fact_canonical_contract.md` - Frozen canonical schema

---

## Overall Judgment

**Status**: `pass_with_gaps`

### Pass Criteria Met
- ✅ Core contracts are well-defined and implementation-usable
- ✅ FACT input assumptions are stable and documented
- ✅ Stage progression is clear (Step1→Step2→Step3→Step4→Step5)
- ✅ Output contract is comprehensive (11 canonical + 4 view outputs)
- ✅ Runner behavior is well-specified (next/all modes, state management)
- ✅ No major blocking contradictions

### Gaps Identified
- ⚠️ Missing Step1 design doc (contracts define it, but no detailed design)
- ⚠️ Language barrier (3 docs in Chinese)
- ⚠️ Naming drift (semantic_asset_build vs semantic)
- ⚠️ Workspace location inconsistency
- ⚠️ Field name drift between contracts and designs
- ⚠️ View outputs incomplete in contract

---

## Assessment Dimensions

### 1. Layering Consistency: PARTIAL

**Status**: `partial`

#### Strengths
- ✅ All contract docs consistently follow: FACT → SEMANTIC → DEMAND
- ✅ semantic_design.md clearly states: "SEMANTIC is NOT fact extraction, NOT demand analysis"
- ✅ semantic_input_contract.md correctly treats old pipeline as FACT only
- ✅ No doc mixes semantic back into FACT runtime

#### Issues
- ⚠️ **00_overall_design.md uses confusing naming**: Says "Input: docs/semantic/* (fact layer)" which mixes semantic and fact naming
- ⚠️ **Package naming drift**: 00_overall_design.md uses `semantic_asset_build` module, but contracts use `semantic` layer
- ⚠️ **Workspace location drift**: Multiple locations mentioned (docs/semantic/, docs/semantic-foundation/semantic-asset-build/)

#### Evidence
From `00_overall_design.md`:
```text
docs/semantic/* (fact layer)
→ semantic_asset_build
→ docs/semantic-foundation/semantic-asset-build/*
```

This should be:
```text
docs/fact/baseline/* (fact layer)
→ semantic
→ docs/semantic/*
```

#### Recommendation
- Update or deprecate `00_overall_design.md` to use consistent naming
- Standardize on `semantic` package name (not `semantic_asset_build`)
- Clarify that FACT inputs come from `docs/fact/baseline/*`, not `docs/semantic/*`

---

### 2. FACT Input Alignment: PARTIAL

**Status**: `partial`

#### Strengths
- ✅ **Canonical/working split is well-defined**: fact_canonical_sample.yaml (observable only) + fact_working_summary_sample.yaml (interpretation)
- ✅ **Conflict resolution rules are clear**: Canonical wins, evidence wins, baseline wins, explicit wins
- ✅ **Forbidden assumptions documented**: semantic_input_contract.md lists 5 forbidden assumptions
- ✅ **Consumption rules explicit**: "Trust canonical as ground truth, use working summary as guidance only"

#### Issues
- ⚠️ **00_overall_design.md doesn't reference canonical/working split**: Uses old mixed FACT sample
- ⚠️ **Step design docs don't mention canonical vs working**: Only contract docs reference the split
- ⚠️ **Input directory inconsistency**: Some docs say `docs/semantic/*`, should be `docs/fact/baseline/*`

#### Evidence
From `semantic_input_contract.md`:
```yaml
Primary Hard Input: fact_canonical_sample.yaml + docs/fact/baseline/*.md
Auxiliary Soft Input: fact_working_summary_sample.yaml
```

From `00_overall_design.md`:
```text
Input: docs/semantic/* (fact layer)  # ← Wrong directory
```

#### Recommendation
- Update all semantic docs to reference `docs/fact/baseline/*` as primary input
- Ensure all step designs mention canonical vs working summary distinction
- Deprecate or update `00_overall_design.md` to reflect canonical/working split

---

### 3. Stage Contract Consistency: PARTIAL

**Status**: `partial`

#### Strengths
- ✅ **5 stages consistently defined**: Step1 (signals), Step2 (candidates), Step3 (recommend), Step4 (review), Step5 (finalize)
- ✅ **Per-stage contracts are complete**: Goal, inputs, outputs, program/model/human responsibilities, blocking rules
- ✅ **Stage progression is clear**: Sequential execution, dependency checking, idempotency
- ✅ **Blocking rules are well-defined**: Fatal, blocking, warning distinctions

#### Issues
- ⚠️ **Missing Step1 design doc**: semantic_stage_contracts.md defines Step1 (Signal Inference) but no `01_step1_signal_inference.md` exists
- ⚠️ **Step numbering inconsistency**: Design docs start at `01_step2_*`, skipping Step1
- ⚠️ **Field name drift**: Contracts say "name, summary, boundary" but designs say "name, responsibility, modules"
- ⚠️ **Output file naming drift**: Contracts say "candidates.yaml" but designs say "step2_candidates.yaml"

#### Evidence
From `semantic_stage_contracts.md`:
```yaml
Step1: Signal Inference
Goal: Extract semantic signals from FACT
Outputs: signals.yaml
```

But no `01_step1_signal_inference.md` exists in the reviewed docs.

From `01_step2_candidate_synthesis.md`:
```yaml
Output: step2_candidates.yaml  # ← Should be candidates.yaml
```

#### Recommendation
- Create `01_step1_signal_inference.md` or remove Step1 from contracts if not needed
- Standardize output file naming: use `signals.yaml`, `candidates.yaml` (not `step2_candidates.yaml`)
- Align field names between contracts and design docs

---

### 4. Output Contract Consistency: PARTIAL

**Status**: `partial`

#### Strengths
- ✅ **11 canonical outputs defined**: signals, candidates, recommendations, review-decisions, evidence-checks, domain-map, concept-map, rule-map, demand-model-map, change-log, run-state
- ✅ **4 view outputs defined**: domain-map.md, concept-map.md, rule-map.md, demand-model-map.md
- ✅ **Minimum structure specified**: Each output has required fields and purpose
- ✅ **Consumer identified**: Each output lists who consumes it (Step2, Step3, DEMAND layer, etc.)

#### Issues
- ⚠️ **View outputs incomplete**: Step designs mention `signals.md`, `candidates.md`, `recommendations.md`, `review-note.md` but semantic_output_contract.md only lists 4 final view outputs
- ⚠️ **Field name drift**: Contracts define different field names than step designs
- ⚠️ **Output location inconsistency**: Some docs say `docs/semantic/`, others say `docs/semantic-foundation/semantic-asset-build/`

#### Evidence
From `semantic_output_contract.md`:
```yaml
View Outputs (4 files):
- domain-map.md
- concept-map.md
- rule-map.md
- demand-model-map.md
```

From `02_step3_scoring_design.md`:
```yaml
Canonical output:
- recommendations.yaml
- recommendations.md (view)  # ← Not in output contract
```

#### Recommendation
- Add intermediate view outputs to semantic_output_contract.md (signals.md, candidates.md, recommendations.md, review-note.md)
- Standardize output location: use `docs/semantic/` (as per semantic_runner_design.md)
- Align field names between output contract and step designs

---

### 5. Runner Consistency: PARTIAL

**Status**: `partial`

#### Strengths
- ✅ **Modes well-defined**: next (single stage), all (full pipeline)
- ✅ **State file structure clear**: run-state.yaml with stage_status, blocking_issues, verify_first_status
- ✅ **Stage progression rules explicit**: Sequential, dependency checking, idempotency, human review gate
- ✅ **Finalize guard correct**: verify_first blocks Step5 if unresolved issues exist
- ✅ **Blocking rules clear**: Fatal (stop immediately), blocking (complete stage, block next), warning (continue)

#### Issues
- ⚠️ **Workspace location inconsistency**: semantic_runner_design.md says `docs/semantic/`, but 00_overall_design.md says `docs/semantic-foundation/semantic-asset-build/`
- ⚠️ **CLI commands not implemented**: semantic_runner_design.md defines `python -m semantic.run next/all/status/reset` but no implementation exists yet

#### Evidence
From `semantic_runner_design.md`:
```yaml
Workspace: docs/semantic/ (or semantic workspace)
```

From `00_overall_design.md`:
```yaml
Output: docs/semantic-foundation/semantic-asset-build/*
```

#### Recommendation
- Standardize workspace location: use `docs/semantic/` consistently
- Update or deprecate `00_overall_design.md` to match runner design
- Implement CLI commands as specified in semantic_runner_design.md

---

### 6. Implementation Readiness: PARTIAL

**Status**: `partial`

#### Can Implementation Start?
✅ **YES** - Core contracts are strong enough to support implementation

#### What's Clear for Implementation
- ✅ Stage progression: Step1→Step2→Step3→Step4→Step5
- ✅ Input consumption: Canonical facts (primary), working summary (auxiliary)
- ✅ Output structure: 11 canonical YAML + 4 view markdown
- ✅ Runner behavior: next/all modes, state management, blocking rules
- ✅ Finalize guard: verify_first blocks Step5

#### What's Unclear for Implementation
- ⚠️ Step1 detailed design (only contract exists, no design doc)
- ⚠️ Workspace location (multiple locations mentioned)
- ⚠️ Package naming (semantic vs semantic_asset_build)
- ⚠️ Field names (drift between contracts and designs)
- ⚠️ Output file naming (candidates.yaml vs step2_candidates.yaml)

#### Can Implementation Agent Answer These Questions?
- ✅ What to read: Yes (canonical facts + baseline)
- ✅ What to write: Yes (11 canonical + 4 view outputs)
- ✅ What each stage must do: Yes (stage contracts are clear)
- ⚠️ What each stage must not do: Partially (some design docs lack detail)
- ✅ What blocks progression: Yes (blocking rules are clear)
- ✅ What is left for human review: Yes (Step4 review gate)
- ✅ What is explicitly out of scope: Yes (DEMAND layer, FACT re-extraction)

#### Recommendation
- Implementation can start with current contracts
- Address naming/location inconsistencies during implementation
- Create Step1 design doc if Step1 is needed (or remove from contracts)

---

### 7. Redundancy and Drift: MEDIUM

**Status**: `medium`

#### Harmless Redundancy
- ✅ semantic_design.md and semantic_stage_contracts.md overlap on stage definitions (acceptable for different audiences)
- ✅ semantic_preflight_check.md and semantic_preflight_check.yaml duplicate content (acceptable for human/machine consumption)

#### Harmful Redundancy
- ⚠️ **00_overall_design.md duplicates semantic_design.md** but with different naming (semantic_asset_build vs semantic)
- ⚠️ **Step design docs duplicate stage contracts** but with different field names and output file names

#### Semantic Drift
- ⚠️ **Package naming drift**: semantic_asset_build (00_overall_design.md) vs semantic (contracts)
- ⚠️ **Workspace location drift**: docs/semantic/ vs docs/semantic-foundation/semantic-asset-build/
- ⚠️ **Field name drift**: name/summary/boundary vs name/responsibility/modules
- ⚠️ **Output file naming drift**: candidates.yaml vs step2_candidates.yaml

#### Stale Assumptions
- ⚠️ **00_overall_design.md assumes old FACT structure**: Says "Input: docs/semantic/* (fact layer)" but should be "docs/fact/baseline/*"
- ⚠️ **Step design docs don't reference canonical/working split**: Assume old mixed FACT sample

#### Recommendation
- Deprecate or update `00_overall_design.md` to match current contracts
- Standardize naming across all docs (semantic, not semantic_asset_build)
- Align field names and output file names between contracts and designs
- Update step designs to reference canonical/working split

---

## Strengths

1. **Strong FACT input foundation**: Canonical/working split is well-defined, frozen contract provides stability
2. **Clear stage progression**: Step1→Step2→Step3→Step4→Step5 is consistent across all contract docs
3. **Comprehensive output contract**: 11 canonical + 4 view outputs with minimum structure and consumers
4. **Runner modes well-defined**: next/all modes with clear state management and blocking rules
5. **Evidence-first principle**: FACT inputs are evidence-backed, semantic consumes with trust
6. **Conflict resolution rules**: Canonical wins, evidence wins, baseline wins, explicit wins
7. **Finalize guard**: verify_first blocks Step5 correctly, preventing premature finalization
8. **Forbidden assumptions documented**: 5 forbidden assumptions prevent semantic from treating working summary as hard truth

---

## Gaps

1. **Missing Step1 design doc**: semantic_stage_contracts.md defines Step1 (Signal Inference) but no detailed design doc exists
2. **Language barrier**: 3 docs in Chinese (00_overall_design.md, 01_step2_candidate_synthesis.md, 01_step2_candidate_synthesis_prompt.md)
3. **Naming drift**: semantic_asset_build (00_overall_design.md) vs semantic (contracts)
4. **Workspace location inconsistency**: docs/semantic/ vs docs/semantic-foundation/semantic-asset-build/
5. **Field name drift**: Contracts say "name, summary, boundary" but designs say "name, responsibility, modules"
6. **View outputs incomplete**: semantic_output_contract.md lists 4 view outputs but step designs mention additional view files
7. **Output file naming drift**: Contracts say "candidates.yaml" but designs say "step2_candidates.yaml"
8. **Input directory inconsistency**: Some docs say "docs/semantic/*" but should be "docs/fact/baseline/*"

---

## Contradictions

1. **Step numbering**: 01_step2_candidate_synthesis.md starts at Step2, but semantic_stage_contracts.md defines Step1 first
2. **Package naming**: 00_overall_design.md uses 'semantic_asset_build' module, but semantic_design.md uses 'semantic' layer
3. **Workspace location**: semantic_runner_design.md says 'docs/semantic/', 00_overall_design.md says 'docs/semantic-foundation/semantic-asset-build/'
4. **Input directory**: 00_overall_design.md says 'Input: docs/semantic/* (fact layer)' but should be 'docs/fact/baseline/*'
5. **View outputs**: semantic_output_contract.md lists 4 view outputs, but step designs mention signals.md, candidates.md, recommendations.md, review-note.md
6. **Field names**: semantic_output_contract.md defines different field names than step design docs

---

## Blocking Issues

**None**: Implementation can start despite gaps and contradictions.

The core contracts (semantic_stage_contracts.md, semantic_input_contract.md, semantic_output_contract.md, semantic_runner_design.md) are strong enough to support implementation. The gaps and contradictions are primarily in:
- Naming consistency (semantic vs semantic_asset_build)
- Workspace location (docs/semantic/ vs docs/semantic-foundation/semantic-asset-build/)
- Language accessibility (3 docs in Chinese)
- Missing Step1 design doc

These can be addressed during or after implementation without blocking progress.

---

## Recommended Fixes

### High Priority

1. **Standardize workspace location**
   - **Issue**: Multiple locations mentioned (docs/semantic/, docs/semantic-foundation/semantic-asset-build/)
   - **Recommendation**: Use `docs/semantic/` consistently (as per semantic_runner_design.md)
   - **Impact**: Prevents implementation confusion about where to write outputs

2. **Standardize package naming**
   - **Issue**: 00_overall_design.md uses 'semantic_asset_build', contracts use 'semantic'
   - **Recommendation**: Use `semantic` package name, update or deprecate 00_overall_design.md
   - **Impact**: Prevents implementation confusion about module structure

3. **Fix input directory references**
   - **Issue**: Some docs say "docs/semantic/*" for FACT inputs
   - **Recommendation**: Use `docs/fact/baseline/*` consistently
   - **Impact**: Prevents implementation from reading wrong input directory

### Medium Priority

4. **Create or remove Step1 design doc**
   - **Issue**: semantic_stage_contracts.md defines Step1 but no design doc exists
   - **Recommendation**: Create 01_step1_signal_inference.md or remove Step1 from contracts if not needed
   - **Impact**: Clarifies whether Step1 is part of MVP or future work

5. **Translate or deprecate Chinese docs**
   - **Issue**: 3 docs in Chinese (00_overall_design.md, 01_step2_candidate_synthesis.md, 01_step2_candidate_synthesis_prompt.md)
   - **Recommendation**: Translate to English or mark as deprecated/transitional
   - **Impact**: Improves accessibility for non-Chinese-speaking implementers

6. **Align field names**
   - **Issue**: Contracts say "name, summary, boundary" but designs say "name, responsibility, modules"
   - **Recommendation**: Standardize field names across all docs
   - **Impact**: Prevents implementation confusion about output structure

### Low Priority

7. **Add intermediate view outputs to contract**
   - **Issue**: semantic_output_contract.md lists 4 view outputs but step designs mention additional view files
   - **Recommendation**: Add signals.md, candidates.md, recommendations.md, review-note.md to output contract
   - **Impact**: Clarifies which view outputs are canonical vs optional

8. **Standardize output file naming**
   - **Issue**: Contracts say "candidates.yaml" but designs say "step2_candidates.yaml"
   - **Recommendation**: Use `candidates.yaml` (not `step2_candidates.yaml`)
   - **Impact**: Prevents implementation confusion about file naming

---

## Final Decision

**Docs Ready for Implementation**: ✅ **YES**

### Rationale

The semantic documentation set is **strong enough** to support implementation:

1. ✅ **Core contracts are well-defined**: Stage contracts, input contract, output contract, runner design are all implementation-usable
2. ✅ **FACT input assumptions are stable**: Canonical/working split is documented, frozen contract provides stability
3. ✅ **Stage progression is clear**: Step1→Step2→Step3→Step4→Step5 with blocking rules and finalize guard
4. ✅ **No major blocking contradictions**: Gaps are primarily naming/location inconsistencies, not semantic ambiguities

### Known Limitations

Implementation should be aware of:
- ⚠️ Naming drift (semantic vs semantic_asset_build) - use `semantic`
- ⚠️ Workspace location drift - use `docs/semantic/`
- ⚠️ Missing Step1 design doc - refer to semantic_stage_contracts.md
- ⚠️ Language barrier (3 docs in Chinese) - refer to English contract docs

### Implementation Strategy

1. **Start with contract docs**: Use semantic_stage_contracts.md, semantic_input_contract.md, semantic_output_contract.md, semantic_runner_design.md as primary references
2. **Ignore naming drift**: Use `semantic` package name, `docs/semantic/` workspace location
3. **Refer to English docs**: If Chinese docs conflict with English contracts, prefer English contracts
4. **Address gaps during implementation**: Create Step1 design doc if needed, standardize naming as you go

---

## Conclusion

**Overall Status**: PASS WITH GAPS

**Can semantic implementation start now?** ✅ **YES**

**Are the semantic docs internally consistent?** ⚠️ **PARTIALLY** (naming drift, location inconsistency)

**Are the semantic docs aligned with FACT input assumptions?** ✅ **YES** (canonical/working split is well-defined)

**Are the docs strong enough to support implementation?** ✅ **YES** (core contracts are implementation-usable)

**Highest-priority fixes**:
1. Standardize workspace location (use `docs/semantic/`)
2. Standardize package naming (use `semantic`, not `semantic_asset_build`)
3. Fix input directory references (use `docs/fact/baseline/*`)

**Implementation can proceed** with awareness of naming/location inconsistencies. Address gaps during implementation or in follow-up documentation cleanup.

---

**Review Completed**: 2026-03-16
**Reviewer**: Claude Opus 4.6
**Result**: ✅ READY FOR IMPLEMENTATION (with known gaps)
