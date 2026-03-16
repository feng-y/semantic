# Semantic Layer Design

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Contract Definition

---

## Goal

The SEMANTIC layer transforms observable FACT layer outputs into semantic models that capture:
- Domain boundaries and relationships
- Concept definitions and roles
- Business rules and constraints
- Demand model structures

**Primary Goal**: Bridge the gap between raw repository facts and actionable change demand analysis.

---

## Why Semantic Exists

### Problem

FACT layer provides:
- Observable repository structure (modules, entrypoints, config)
- Evidence-backed claims (file:line refs)
- Working summaries (interpretation, domain proposals)

But FACT layer does NOT provide:
- Stable domain models
- Concept relationship maps
- Business rule extraction
- Demand model structures

### Solution

SEMANTIC layer synthesizes FACT outputs into:
- **Domain Map**: Stable domain boundaries with responsibilities
- **Concept Map**: Core concepts with relationships and roles
- **Rule Map**: Business rules and constraints
- **Demand Model Map**: Change demand model structures

---

## Boundaries

### What SEMANTIC Is

- **Model synthesis**: Transform facts into semantic models
- **Relationship extraction**: Identify concept relationships
- **Domain stabilization**: Propose stable domain boundaries
- **Rule identification**: Extract business rules from code/docs

### What SEMANTIC Is Not

- **Not fact extraction**: SEMANTIC consumes facts, does not extract them
- **Not demand analysis**: SEMANTIC prepares models, does not analyze change requests
- **Not implementation**: SEMANTIC models structure, does not generate code

### Boundary with FACT

**FACT → SEMANTIC**:
- FACT provides: observable structure, evidence, working summaries
- SEMANTIC consumes: canonical facts (primary), working summary (auxiliary)
- SEMANTIC does NOT: re-extract facts, re-scan repository

### Boundary with DEMAND

**SEMANTIC → DEMAND**:
- SEMANTIC provides: domain/concept/rule/demand-model maps
- DEMAND consumes: semantic models to analyze change requests
- DEMAND does NOT: modify semantic models, re-synthesize domains

---

## Inputs

### Primary Hard Input

**Source**: `docs/fact/baseline/*.md` + `fact_canonical_sample.yaml`

**Content**:
- `purpose.md`: System purpose and non-goals
- `pipelines.md`: Execution flows
- `domains.md`: Domain boundaries (FACT-level)
- `concepts.md`: Core concepts
- `checkpoint.json`: Version metadata

**Consumption Rule**: Trust as ground truth, use evidence refs for validation.

### Auxiliary Soft Input

**Source**: `fact_working_summary_sample.yaml`

**Content**:
- System purpose interpretation
- Domain boundary proposals
- Concept role assignments
- Open questions
- Assumptions

**Consumption Rule**: Use as guidance/bootstrap context, NOT as hard truth. When conflict with canonical, prefer canonical.

### Reference Input

**Source**: `docs/fact/discovery/*.vN.md`, `docs/fact/review/*.vN.md`

**Content**:
- `repo-facts.vN.md`: Observable repository structure
- `repo-understanding.vN.md`: Purpose, pipelines, concepts
- `domain-candidates.vN.md`: Candidate domain boundaries
- `knowledge-confidence.vN.md`: Confidence ratings
- `review-summary.vN.md`: Architect review summary

**Consumption Rule**: Use for additional context, cross-reference with baseline.

---

## Outputs

### Canonical Outputs

**Location**: `docs/semantic/` (or semantic workspace)

| File | Purpose | Consumer |
|------|---------|----------|
| `signals.yaml` | Extracted semantic signals from FACT | Step2 candidate synthesis |
| `candidates.yaml` | Candidate domains/concepts/rules | Step3 scoring |
| `recommendations.yaml` | Scored and ranked recommendations | Step4 review |
| `review-decisions.yaml` | Architect review decisions | Step5 finalize |
| `evidence-checks.yaml` | Evidence validation results | Step4/Step5 |
| `domain-map.yaml` | Final domain boundaries | DEMAND layer |
| `concept-map.yaml` | Final concept relationships | DEMAND layer |
| `rule-map.yaml` | Final business rules | DEMAND layer |
| `demand-model-map.yaml` | Demand model structures | DEMAND layer |
| `change-log.yaml` | Semantic model change history | Audit/versioning |
| `run-state.yaml` | Semantic runner state | Runner control |

### View Outputs

**Location**: `docs/semantic/*.md` (markdown views)

- `domain-map.md`: Human-readable domain map
- `concept-map.md`: Human-readable concept map
- `rule-map.md`: Human-readable rule map
- `demand-model-map.md`: Human-readable demand model map

**Purpose**: Human review and documentation.

---

## Relationship with FACT

### FACT Provides Foundation

- Observable structure (modules, entrypoints, entities)
- Evidence refs (file:line)
- Baseline checkpoint (accepted facts)
- Working summary (interpretation hints)

### SEMANTIC Builds on FACT

- Consumes canonical facts as primary input
- Uses working summary as auxiliary guidance
- Does NOT re-extract facts
- Does NOT modify FACT outputs

### Separation Principle

**FACT** = Observable, evidence-backed, low-interpretation
**SEMANTIC** = Model synthesis, relationship extraction, domain stabilization

**Rule**: SEMANTIC must not leak back into FACT. FACT remains stable and interpretation-free.

---

## Relationship with DEMAND

### SEMANTIC Prepares Models

- Domain map: Stable domain boundaries
- Concept map: Core concepts with relationships
- Rule map: Business rules and constraints
- Demand model map: Change demand structures

### DEMAND Consumes Models

- Analyzes change requests against semantic models
- Identifies impacted domains/concepts/rules
- Proposes change strategies
- Does NOT modify semantic models

### Separation Principle

**SEMANTIC** = Model synthesis (what the system IS)
**DEMAND** = Change analysis (what SHOULD change)

**Rule**: DEMAND must not modify semantic models. Semantic models are stable references for demand analysis.

---

## Summary

**SEMANTIC layer**:
- Transforms FACT outputs into semantic models
- Bridges observable facts and change demand analysis
- Produces domain/concept/rule/demand-model maps
- Consumes canonical facts (primary) + working summary (auxiliary)
- Feeds DEMAND layer with stable semantic models

**Key Principle**: SEMANTIC is the interpretation layer between observable FACT and actionable DEMAND.
