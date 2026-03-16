# Semantic Stage Contracts

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Contract Definition

---

## Overview

The SEMANTIC layer executes through 5 stages:
1. **Step1: Signal Inference** - Extract semantic signals from FACT
2. **Step2: Candidate Synthesis** - Generate candidate domains/concepts/rules
3. **Step3: Scoring & Recommendation** - Score and rank candidates
4. **Step4: Review & Evidence** - Architect review and evidence validation
5. **Step5: Finalize** - Produce final semantic models

---

## Stage 1: Signal Inference

### Goal

Extract semantic signals from FACT layer outputs that indicate:
- Domain boundaries
- Concept definitions
- Business rules
- Demand model structures

### Inputs

**Primary**:
- `docs/fact/baseline/purpose.md`
- `docs/fact/baseline/pipelines.md`
- `docs/fact/baseline/domains.md`
- `docs/fact/baseline/concepts.md`
- `fact_canonical_sample.yaml`

**Auxiliary**:
- `fact_working_summary_sample.yaml`
- `docs/fact/discovery/repo-understanding.vN.md`

### Outputs

**File**: `signals.yaml`

**Structure**:
```yaml
signals:
  domain_signals:
    - signal_type: "module_grouping"
      evidence: "file:line"
      confidence: "high|medium|low"
  concept_signals:
    - signal_type: "entity_definition"
      evidence: "file:line"
      confidence: "high|medium|low"
  rule_signals:
    - signal_type: "validation_logic"
      evidence: "file:line"
      confidence: "high|medium|low"
```

### Program Responsibilities

- Read FACT baseline files
- Parse canonical facts
- Extract semantic signals
- Assign confidence ratings
- Write `signals.yaml`

### Model Responsibilities

- Identify domain boundary indicators
- Recognize concept definitions
- Detect business rule patterns
- Assess signal confidence

### Human Responsibilities

None (fully automated).

### Blocking Rules

- **BLOCK** if baseline files missing
- **BLOCK** if canonical facts malformed
- **WARN** if confidence is low across all signals

---

## Stage 2: Candidate Synthesis

### Goal

Generate candidate semantic models:
- Candidate domains with responsibilities
- Candidate concepts with relationships
- Candidate rules with constraints
- Candidate demand model structures

### Inputs

**Primary**:
- `signals.yaml` (from Step1)
- `docs/fact/baseline/*.md`

**Auxiliary**:
- `fact_working_summary_sample.yaml`
- `docs/fact/discovery/domain-candidates.vN.md`

### Outputs

**File**: `candidates.yaml`

**Structure**:
```yaml
candidates:
  domains:
    - name: "Domain Name"
      responsibility: "What this domain does"
      modules: ["module1", "module2"]
      evidence: ["file:line"]
      confidence: "high|medium|low"
  concepts:
    - name: "Concept Name"
      definition: "What this concept represents"
      relationships: ["related_concept"]
      evidence: ["file:line"]
      confidence: "high|medium|low"
  rules:
    - name: "Rule Name"
      constraint: "What this rule enforces"
      evidence: ["file:line"]
      confidence: "high|medium|low"
  demand_models:
    - name: "Demand Model Name"
      structure: "What this model captures"
      evidence: ["file:line"]
      confidence: "high|medium|low"
```

### Program Responsibilities

- Read `signals.yaml`
- Group signals into candidates
- Assign candidate names
- Collect evidence refs
- Write `candidates.yaml`

### Model Responsibilities

- Synthesize domains from module groupings
- Define concepts from entity definitions
- Extract rules from validation logic
- Propose demand model structures
- Assess candidate quality

### Human Responsibilities

None (fully automated).

### Blocking Rules

- **BLOCK** if `signals.yaml` missing
- **BLOCK** if no candidates generated
- **WARN** if candidate count < minimum threshold

---

## Stage 3: Scoring & Recommendation

### Goal

Score and rank candidates based on:
- Business value
- Evidence strength
- Confidence level
- Completeness

Produce ranked recommendations for architect review.

### Inputs

**Primary**:
- `candidates.yaml` (from Step2)

**Auxiliary**:
- `fact_working_summary_sample.yaml` (for business context)

### Outputs

**File**: `recommendations.yaml`

**Structure**:
```yaml
recommendations:
  domains:
    - name: "Domain Name"
      score: 0.85
      rank: 1
      rationale: "Why this is recommended"
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"
  concepts:
    - name: "Concept Name"
      score: 0.78
      rank: 2
      rationale: "Why this is recommended"
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"
  rules:
    - name: "Rule Name"
      score: 0.72
      rank: 3
      rationale: "Why this is recommended"
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"
  demand_models:
    - name: "Demand Model Name"
      score: 0.80
      rank: 1
      rationale: "Why this is recommended"
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"
```

### Program Responsibilities

- Read `candidates.yaml`
- Calculate scores
- Rank candidates
- Generate rationales
- Write `recommendations.yaml`

### Model Responsibilities

- Assess business value
- Evaluate evidence strength
- Assign confidence-weighted scores
- Provide recommendation rationale

### Human Responsibilities

None (fully automated).

### Blocking Rules

- **BLOCK** if `candidates.yaml` missing
- **BLOCK** if scoring fails
- **WARN** if all scores < threshold

---

## Stage 4: Review & Evidence

### Goal

Enable architect review of recommendations and validate evidence.

**Sub-stages**:
- **Step4a: Review Assist** - Present recommendations for architect decision
- **Step4b: Evidence Check** - Validate evidence refs for accepted recommendations

### Inputs

**Primary**:
- `recommendations.yaml` (from Step3)

**Auxiliary**:
- `fact_canonical_sample.yaml` (for evidence validation)

### Outputs

**File 1**: `review-decisions.yaml`

**Structure**:
```yaml
review_decisions:
  domains:
    - name: "Domain Name"
      decision: "accept|reject|defer"
      architect_note: "Optional feedback"
  concepts:
    - name: "Concept Name"
      decision: "accept|reject|defer"
      architect_note: "Optional feedback"
  rules:
    - name: "Rule Name"
      decision: "accept|reject|defer"
      architect_note: "Optional feedback"
  demand_models:
    - name: "Demand Model Name"
      decision: "accept|reject|defer"
      architect_note: "Optional feedback"
```

**File 2**: `evidence-checks.yaml`

**Structure**:
```yaml
evidence_checks:
  domains:
    - name: "Domain Name"
      evidence_valid: true|false
      missing_evidence: []
      validation_note: "Optional note"
  concepts:
    - name: "Concept Name"
      evidence_valid: true|false
      missing_evidence: []
      validation_note: "Optional note"
  rules:
    - name: "Rule Name"
      evidence_valid: true|false
      missing_evidence: []
      validation_note: "Optional note"
```

### Program Responsibilities

- Read `recommendations.yaml`
- Present recommendations to architect
- Collect architect decisions
- Validate evidence refs
- Write `review-decisions.yaml` and `evidence-checks.yaml`

### Model Responsibilities

- Assist architect with recommendation context
- Validate evidence refs against canonical facts
- Identify missing evidence

### Human Responsibilities

- **Architect**: Review recommendations
- **Architect**: Make accept/reject/defer decisions
- **Architect**: Provide optional feedback

### Blocking Rules

- **BLOCK** if `recommendations.yaml` missing
- **BLOCK** if architect decisions incomplete
- **FATAL** if evidence validation fails for accepted items

---

## Stage 5: Finalize

### Goal

Produce final semantic models from accepted recommendations.

**Outputs**:
- `domain-map.yaml` + `domain-map.md`
- `concept-map.yaml` + `concept-map.md`
- `rule-map.yaml` + `rule-map.md`
- `demand-model-map.yaml` + `demand-model-map.md`
- `change-log.yaml`

### Inputs

**Primary**:
- `review-decisions.yaml` (from Step4)
- `evidence-checks.yaml` (from Step4)
- `candidates.yaml` (from Step2)

### Outputs

**File 1**: `domain-map.yaml`

**Structure**:
```yaml
domains:
  - name: "Domain Name"
    responsibility: "What this domain does"
    modules: ["module1", "module2"]
    concepts: ["concept1", "concept2"]
    rules: ["rule1", "rule2"]
    evidence: ["file:line"]
```

**File 2**: `concept-map.yaml`

**Structure**:
```yaml
concepts:
  - name: "Concept Name"
    definition: "What this concept represents"
    domain: "Domain Name"
    relationships:
      - target: "Related Concept"
        type: "uses|extends|contains"
    evidence: ["file:line"]
```

**File 3**: `rule-map.yaml`

**Structure**:
```yaml
rules:
  - name: "Rule Name"
    constraint: "What this rule enforces"
    domain: "Domain Name"
    concepts: ["concept1", "concept2"]
    evidence: ["file:line"]
```

**File 4**: `demand-model-map.yaml`

**Structure**:
```yaml
demand_models:
  - name: "Demand Model Name"
    structure: "What this model captures"
    domains: ["domain1", "domain2"]
    concepts: ["concept1", "concept2"]
    evidence: ["file:line"]
```

**File 5**: `change-log.yaml`

**Structure**:
```yaml
changes:
  - timestamp: "ISO 8601"
    stage: "step5_finalize"
    action: "created|updated|deleted"
    target: "domain|concept|rule|demand_model"
    name: "Item Name"
    reason: "Why this change"
```

### Program Responsibilities

- Read `review-decisions.yaml` and `evidence-checks.yaml`
- Filter accepted items
- Generate final maps
- Write YAML and markdown views
- Update `change-log.yaml`

### Model Responsibilities

None (finalization is deterministic).

### Human Responsibilities

None (fully automated).

### Blocking Rules

- **BLOCK** if `review-decisions.yaml` missing
- **BLOCK** if evidence validation failed for accepted items
- **FATAL** if finalization produces empty maps

---

## Summary

| Stage | Input | Output | Human Role | Blocking |
|-------|-------|--------|------------|----------|
| Step1 | FACT baseline | `signals.yaml` | None | Missing baseline |
| Step2 | `signals.yaml` | `candidates.yaml` | None | No candidates |
| Step3 | `candidates.yaml` | `recommendations.yaml` | None | Scoring fails |
| Step4 | `recommendations.yaml` | `review-decisions.yaml`, `evidence-checks.yaml` | Architect review | Incomplete decisions |
| Step5 | `review-decisions.yaml` | `domain-map.yaml`, `concept-map.yaml`, `rule-map.yaml`, `demand-model-map.yaml` | None | Evidence validation fails |

**Contract Version**: 1.0
**Status**: Frozen for implementation
