# Semantic Normalization Rules

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Global Normalization Reference
**Purpose**: Single source of truth for semantic documentation normalization

---

## Overview

This document defines the global normalization rules for all semantic layer documentation. All semantic docs must align with these rules.

**Role**: This is the canonical normalization reference. When conflicts arise between documents, these rules take precedence.

---

## 1. Layer Naming

### Canonical Layer Name

**Current canonical name**: `semantic`

**Legacy/transitional names**:
- `semantic_asset_build` (old package name, transitional only)

### Rules

1. All new documentation must use `semantic` as the layer name
2. `semantic_asset_build` may appear only when:
   - Explaining legacy/transitional naming
   - Marked explicitly as "legacy" or "transitional"
3. Do not use both terms as equal current names
4. When in doubt, use `semantic`

### Layer Hierarchy

```
FACT (fact layer) → SEMANTIC (semantic layer) → DEMAND (demand layer)
```

**Rules**:
- Old pipeline (discover/review/refine/baseline) remains FACT only
- Semantic is a new layer on top of FACT
- Demand is out of scope (future work)
- Semantic must not be folded back into FACT runtime

---

## 2. Workspace Semantics

### Two Distinct Workspaces

There are **two distinct workspaces** that must not be confused:

#### Workspace 1: FACT Runtime Generated Workspace

**Location**: `docs/semantic/`

**Purpose**: Old FACT pipeline generated artifacts

**Contains**: Discovery, review, refine, baseline outputs from old pipeline

**Note**: This uses transitional naming (should be `docs/fact/` but kept for compatibility)

**Rule**: This is NOT the semantic layer workspace

#### Workspace 2: Semantic Layer Workspace

**Location**: `docs/semantic-foundation/semantic/`

**Purpose**: Semantic layer documentation, contracts, and runtime outputs

**Contains**:
- Contract documents
- Design documents
- Semantic runtime outputs (signals.yaml, candidates.yaml, etc.)

**Rule**: This IS the semantic layer workspace

### Rules

1. All semantic layer outputs go to `docs/semantic-foundation/semantic/`
2. Do not write semantic outputs to `docs/semantic/`
3. Do not treat `docs/semantic/` as the semantic implementation workspace
4. Always clarify which workspace is being referenced
5. Add notes about transitional naming where confusion may arise

---

## 3. Stage Sequence

### Canonical Stage Names

The semantic layer executes through **5 stages**:

1. `step1_signals` (Signal Inference)
2. `step2_candidates` (Candidate Synthesis)
3. `step3_recommend` (Scoring & Recommendation)
4. `step4_review` (Review & Evidence)
5. `step5_finalize` (Finalize)

### Rules

1. All documentation must use this exact sequence
2. Step1 must be included (not optional)
3. Stage names must be consistent across all docs
4. Design coverage must include all 5 stages
5. Do not skip Step1 and start from Step2

---

## 4. Input Contract

### Primary Hard Input

**Source**: `docs/semantic-foundation/fact/fact_canonical_sample.yaml`

**Role**: REQUIRED primary input

**Content**: Observable facts only (no interpretation)

**Rule**: Semantic layer BLOCKS if this is missing

### Auxiliary Soft Input

**Source**: `docs/semantic-foundation/fact/fact_working_summary_sample.yaml`

**Role**: OPTIONAL auxiliary input

**Content**: Interpretation, analysis, guidance

**Rule**: Use as guidance only, NOT as hard truth

### Reference Input

**Source**: `docs/fact/baseline/*.md` (if available)

**Role**: OPTIONAL reference input

**Content**: Baseline markdown files (purpose, pipelines, domains, concepts)

**Rule**: Use as additional reference if available, but semantic can proceed without them

### Conflict Resolution

When conflicts arise between inputs:

1. **Canonical wins**: `fact_canonical_sample.yaml` is the ground truth
2. **Evidence wins**: Evidence-backed claims override interpretation
3. **Baseline wins**: Accepted baseline overrides working artifacts
4. **Explicit wins**: Explicit corrections override inferred content

---

## 5. Output Naming

### Canonical Output Files (11 YAML files)

All semantic canonical outputs use these exact names:

1. `signals.yaml`
2. `candidates.yaml`
3. `recommendations.yaml`
4. `review-decisions.yaml`
5. `evidence-checks.yaml`
6. `domain-map.yaml`
7. `concept-map.yaml`
8. `rule-map.yaml`
9. `demand-model-map.yaml`
10. `change-log.yaml`
11. `run-state.yaml`

### View Output Files (8 Markdown files)

**Intermediate views**:
1. `signals.md`
2. `candidates.md`
3. `recommendations.md`
4. `review-note.md`

**Final views**:
5. `domain-map.md`
6. `concept-map.md`
7. `rule-map.md`
8. `demand-model-map.md`

### Rules

1. Do NOT use step-prefixed names as canonical (e.g., `step2_candidates.yaml`)
2. Step-prefixed names may appear only as:
   - Legacy/transitional references
   - Explicitly marked as non-canonical
3. All documentation must use canonical names
4. All code must generate canonical names
5. When in doubt, use the canonical name from this list

---

## 6. Field Naming

### Canonical Fields for Semantic Objects

For candidate-like semantic objects (domains, concepts, rules), the canonical fields are:

**Core fields**:
- `id`: Unique identifier
- `name`: Object name
- `summary`: Brief description
- `boundary`: Scope definition (for domains)
- `evidence`: Evidence references (file:line)
- `confidence`: Confidence level (high|medium|low)

### Legacy/Non-Canonical Fields

These fields may appear in design docs as explanatory content but are NOT canonical:

- `responsibility`: Use `summary` instead
- `modules`: Use as subfield under `boundary` if needed
- `definition`: Use `summary` instead
- `constraint`: Use `summary` instead

### Rules

1. Contract documents must use canonical field names
2. Design documents may use legacy fields for explanation, but must:
   - Mark them as non-canonical
   - Map them to canonical fields
   - Not present them as equal alternatives
3. When implementing, use canonical fields
4. When in doubt, use canonical fields from this list

---

## 7. Signal Groups

### Canonical Signal Types

Step1 (Signal Inference) must output these 4 signal groups:

1. `domain_signals`: Domain boundary indicators
2. `concept_signals`: Concept definition indicators
3. `rule_signals`: Business rule indicators
4. `demand_pattern_signals`: Demand model structure indicators

### Rules

1. All 4 signal groups must be present in Step1 output
2. Use exact names (not `demand_model_signals` or `demand_signals`)
3. All documentation must reference these 4 groups consistently

---

## 8. Document Roles

### Contract Documents (Canonical)

These documents define canonical contracts:

- `semantic_stage_contracts.md`
- `semantic_input_contract.md`
- `semantic_output_contract.md`
- `semantic_runner_design.md`

**Role**: Final truth for contracts, interfaces, I/O semantics, runner semantics

**Rule**: These are canonical. Design docs must follow them.

### Design Documents (Explanatory)

These documents provide implementation guidance:

- `semantic_design.md`
- `semantic_dev_plan.md`
- `01_step1_signal_inference.md`
- `02_step3_scoring_design.md`
- `03_step4_review_and_evidence_design.md`
- `04_step5_finalize_design.md`

**Role**: Explanatory and implementation-guiding

**Rule**: These must follow contract documents. They provide detail but do not override contracts.

### Status/Review Documents (Non-Canonical)

These documents record status and review results:

- `semantic_preflight_check.md`
- `semantic_preflight_check.yaml`
- `semantic_doc_review.md`
- `semantic_doc_review.yaml`
- `semantic_doc_fix_result.md`
- `semantic_doc_fix_result.yaml`
- `step1_signals_precheck.md`
- `step1_signals_precheck.yaml`
- `step1_signals_fix_result.md`
- `step1_signals_fix_result.yaml`

**Role**: Status tracking and review results

**Rule**: These are NOT contract sources. They document state, not define contracts.

### Transitional Documents (Legacy)

These documents use legacy naming and are kept for historical context:

- `00_overall_design.md` (uses `semantic_asset_build`, Chinese)
- `01_step2_candidate_synthesis.md` (Chinese, legacy naming)
- `01_step2_candidate_synthesis_prompt.md` (Chinese, legacy naming)

**Role**: Historical reference only

**Rule**: These are marked as transitional. For implementation, use contract documents.

---

## 9. Blocking Rules

### Step1 Blocking Rules

**BLOCK** (stop execution):
- If `fact_canonical_sample.yaml` is missing or malformed

**WARN** (continue with caution):
- If `fact_working_summary_sample.yaml` is missing
- If `docs/fact/baseline/*.md` files are missing
- If confidence is low across all signals

### General Blocking Principles

1. Block only on missing REQUIRED inputs
2. Warn on missing OPTIONAL inputs
3. Canonical facts are REQUIRED
4. Working summary is OPTIONAL
5. Baseline files are OPTIONAL

---

## 10. Implementation Priorities

### When Implementing Semantic Layer

Follow this priority order:

1. **Read contract documents first**
   - semantic_stage_contracts.md
   - semantic_input_contract.md
   - semantic_output_contract.md
   - semantic_runner_design.md

2. **Use canonical naming**
   - Layer name: `semantic`
   - Workspace: `docs/semantic-foundation/semantic/`
   - Output files: canonical names (signals.yaml, not step1_signals.yaml)
   - Fields: canonical fields (id, name, summary, boundary)

3. **Follow input contract**
   - Primary: fact_canonical_sample.yaml (REQUIRED)
   - Auxiliary: fact_working_summary_sample.yaml (optional)
   - Reference: baseline/*.md (optional)

4. **Refer to design documents for guidance**
   - Use them for implementation details
   - But follow contracts when conflicts arise

5. **Ignore transitional documents**
   - 00_overall_design.md and Chinese docs are legacy
   - Use contract documents instead

---

## 11. Conflict Resolution

### When Documentation Conflicts Arise

Apply these rules in order:

1. **Contract documents win** over design documents
2. **This normalization rules document wins** over all other documents
3. **Canonical naming wins** over legacy naming
4. **Explicit rules win** over implicit assumptions
5. **Evidence-backed claims win** over interpretation

### When to Update This Document

Update this document when:
- A new global normalization decision is made
- An existing rule needs clarification
- A conflict resolution principle changes

Do NOT update this document for:
- Implementation details (use design docs)
- Status updates (use status docs)
- Temporary decisions (use comments in code)

---

## 12. Summary

**Key Normalization Rules**:

1. **Layer name**: `semantic` (not `semantic_asset_build`)
2. **Workspace**: `docs/semantic-foundation/semantic/` (not `docs/semantic/`)
3. **Stages**: 5 stages (step1_signals through step5_finalize)
4. **Primary input**: `fact_canonical_sample.yaml` (REQUIRED)
5. **Output names**: Canonical names (candidates.yaml, not step2_candidates.yaml)
6. **Field names**: Canonical fields (id, name, summary, boundary)
7. **Signal groups**: 4 groups (domain, concept, rule, demand_pattern)
8. **Document roles**: Contract docs are canonical, design docs are explanatory
9. **Blocking**: Block only on missing canonical facts
10. **Conflicts**: Contract docs win, this doc wins over all

**For Implementation**: Read contract documents, use canonical naming, follow input contract, refer to design docs for guidance.

---

**Normalization Rules Version**: 1.0
**Last Updated**: 2026-03-16
**Status**: CANONICAL REFERENCE