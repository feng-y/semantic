# Semantic Layer Documentation Workspace

**Purpose**: This directory contains semantic layer design documents, contracts, and implementation guides.

**Status**: Contract Definition and Design Documentation

---

## Workspace Distinction

**IMPORTANT**: This repository has two distinct semantic-related workspaces:

### 1. FACT Runtime Generated Workspace
**Location**: `docs/semantic/`

**Purpose**: Old FACT pipeline generated artifacts (transitional naming)

**Contains**: Discovery, review, refine, baseline outputs from the old pipeline

**Note**: This is the FACT layer workspace, not the semantic layer workspace. The naming is transitional.

### 2. Semantic Layer Documentation Workspace
**Location**: `docs/semantic-foundation/semantic/` (this directory)

**Purpose**: Semantic layer contracts, design docs, and implementation guides

**Contains**: Contract documents, stage designs, preflight checks, review results

---

## Semantic Layer Output Workspace

**Location**: `docs/semantic/` (runtime output location)

**Purpose**: Semantic layer will write its canonical outputs here

**Canonical Outputs** (11 YAML files):
- signals.yaml
- candidates.yaml
- recommendations.yaml
- review-decisions.yaml
- evidence-checks.yaml
- domain-map.yaml
- concept-map.yaml
- rule-map.yaml
- demand-model-map.yaml
- change-log.yaml
- run-state.yaml

**View Outputs** (8 Markdown files):
- signals.md, candidates.md, recommendations.md, review-note.md (intermediate)
- domain-map.md, concept-map.md, rule-map.md, demand-model-map.md (final)

---

## Contract Documents (Canonical)

These documents define the semantic layer contracts:

1. **semantic_design.md** - Overall semantic layer design
2. **semantic_stage_contracts.md** - 5-stage definitions with contracts
3. **semantic_input_contract.md** - FACT input consumption rules
4. **semantic_output_contract.md** - 11 canonical + 8 view outputs
5. **semantic_runner_design.md** - Runner modes and state management
6. **semantic_dev_plan.md** - Implementation phases and roadmap

---

## Stage Design Documents (Implementation Guides)

These documents provide implementation guidance for each stage:

1. **01_step1_signal_inference.md** - Step1 (Signal Inference) design
2. **02_step3_scoring_design.md** - Step3 (Scoring & Recommendation) design
3. **03_step4_review_and_evidence_design.md** - Step4 (Review & Evidence) design
4. **04_step5_finalize_design.md** - Step5 (Finalize) design

---

## Transitional Documents (Legacy Naming)

These documents use legacy naming and are kept for historical context:

1. **00_overall_design.md** - Uses `semantic_asset_build` naming (Chinese)
2. **01_step2_candidate_synthesis.md** - Step2 design (Chinese, legacy naming)
3. **01_step2_candidate_synthesis_prompt.md** - Step2 prompt (Chinese, legacy naming)

**For Implementation**: Use contract documents and English stage design documents as canonical references.

---

## Preflight and Review Documents

1. **semantic_preflight_check.md** - Readiness assessment
2. **semantic_preflight_check.yaml** - Structured preflight result
3. **semantic_doc_review.md** - Documentation consistency review
4. **semantic_doc_review.yaml** - Structured review result

---

## Layer Naming

**Canonical Layer Name**: `semantic`

**Legacy Names** (transitional only):
- `semantic_asset_build` (old package name)

**For Implementation**: Use `semantic` as the package/module name.
