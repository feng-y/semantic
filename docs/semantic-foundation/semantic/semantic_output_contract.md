# Semantic Output Contract

**Version**: 1.0
**Date**: 2026-03-16
**Status**: Contract Definition

---

## Overview

This document defines all SEMANTIC layer outputs, their purposes, minimum structures, and consumers.

**Output Types**:
- **Canonical Outputs**: YAML files (machine-consumable)
- **View Outputs**: Markdown files (human-readable)

---

## Canonical Outputs

### 1. signals.yaml

**Purpose**: Extracted semantic signals from FACT layer

**Consumer**: Step2 (Candidate Synthesis)

**Type**: Canonical

**Minimum Structure**:
```yaml
signals:
  domain_signals:
    - signal_type: string
      source: string
      evidence: string
      confidence: "high|medium|low"

  concept_signals:
    - signal_type: string
      source: string
      evidence: string
      confidence: "high|medium|low"

  rule_signals:
    - signal_type: string
      source: string
      evidence: string
      confidence: "high|medium|low"

  demand_model_signals:
    - signal_type: string
      source: string
      evidence: string
      confidence: "high|medium|low"

metadata:
  generated_at: string
  fact_baseline_version: string
  signal_count: integer
```

**Required Fields**:
- `signal_type`: Type of semantic signal
- `source`: Where signal was extracted from
- `evidence`: Evidence ref (file:line)
- `confidence`: Confidence level

---

### 2. candidates.yaml

**Purpose**: Candidate semantic models (domains, concepts, rules, demand models)

**Consumer**: Step3 (Scoring & Recommendation)

**Type**: Canonical

**Minimum Structure**:
```yaml
candidates:
  domains:
    - name: string
      responsibility: string
      modules: [string]
      evidence: [string]
      confidence: "high|medium|low"

  concepts:
    - name: string
      definition: string
      relationships: [string]
      evidence: [string]
      confidence: "high|medium|low"

  rules:
    - name: string
      constraint: string
      evidence: [string]
      confidence: "high|medium|low"

  demand_models:
    - name: string
      structure: string
      evidence: [string]
      confidence: "high|medium|low"

metadata:
  generated_at: string
  signal_source: string
  candidate_count: integer
```

**Required Fields**:
- `name`: Candidate name
- `evidence`: Evidence refs supporting candidate
- `confidence`: Confidence level

---

### 3. recommendations.yaml

**Purpose**: Scored and ranked recommendations

**Consumer**: Step4 (Review & Evidence)

**Type**: Canonical

**Minimum Structure**:
```yaml
recommendations:
  domains:
    - name: string
      score: float
      rank: integer
      rationale: string
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"

  concepts:
    - name: string
      score: float
      rank: integer
      rationale: string
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"

  rules:
    - name: string
      score: float
      rank: integer
      rationale: string
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"

  demand_models:
    - name: string
      score: float
      rank: integer
      rationale: string
      evidence_strength: "high|medium|low"
      recommendation: "accept|review|reject"

metadata:
  generated_at: string
  candidate_source: string
  scoring_method: string
```

**Required Fields**:
- `name`: Recommendation name
- `score`: Numeric score (0.0-1.0)
- `rank`: Ranking position
- `rationale`: Why this is recommended
- `recommendation`: Accept/review/reject

---

### 4. review-decisions.yaml

**Purpose**: Architect review decisions

**Consumer**: Step5 (Finalize)

**Type**: Canonical

**Minimum Structure**:
```yaml
review_decisions:
  domains:
    - name: string
      decision: "accept|reject|defer"
      rationale: string
      modifications: string

  concepts:
    - name: string
      decision: "accept|reject|defer"
      rationale: string
      modifications: string

  rules:
    - name: string
      decision: "accept|reject|defer"
      rationale: string
      modifications: string

  demand_models:
    - name: string
      decision: "accept|reject|defer"
      rationale: string
      modifications: string

metadata:
  reviewed_at: string
  reviewer: string
  recommendation_source: string
```

**Required Fields**:
- `name`: Item name
- `decision`: Accept/reject/defer
- `rationale`: Why this decision was made

---

### 5. evidence-checks.yaml

**Purpose**: Evidence validation results

**Consumer**: Step4/Step5 (Review & Finalize)

**Type**: Canonical

**Minimum Structure**:
```yaml
evidence_checks:
  domains:
    - name: string
      evidence_refs: [string]
      validation_status: "valid|invalid|partial"
      issues: [string]

  concepts:
    - name: string
      evidence_refs: [string]
      validation_status: "valid|invalid|partial"
      issues: [string]

  rules:
    - name: string
      evidence_refs: [string]
      validation_status: "valid|invalid|partial"
      issues: [string]

  demand_models:
    - name: string
      evidence_refs: [string]
      validation_status: "valid|invalid|partial"
      issues: [string]

metadata:
  checked_at: string
  fact_baseline_version: string
```

**Required Fields**:
- `name`: Item name
- `evidence_refs`: Evidence refs to validate
- `validation_status`: Valid/invalid/partial
- `issues`: List of validation issues (if any)

---

### 6. domain-map.yaml

**Purpose**: Final domain boundaries and responsibilities

**Consumer**: DEMAND layer

**Type**: Canonical

**Minimum Structure**:
```yaml
domains:
  - name: string
    responsibility: string
    modules: [string]
    concepts: [string]
    rules: [string]
    evidence: [string]
    relationships:
      depends_on: [string]
      provides_to: [string]

metadata:
  finalized_at: string
  version: string
  source_decisions: string
```

**Required Fields**:
- `name`: Domain name
- `responsibility`: What this domain does
- `modules`: Modules in this domain
- `evidence`: Evidence refs

---

### 7. concept-map.yaml

**Purpose**: Final concept definitions and relationships

**Consumer**: DEMAND layer

**Type**: Canonical

**Minimum Structure**:
```yaml
concepts:
  - name: string
    definition: string
    domain: string
    relationships:
      is_a: [string]
      has_a: [string]
      uses: [string]
      used_by: [string]
    evidence: [string]
    rules: [string]

metadata:
  finalized_at: string
  version: string
  source_decisions: string
```

**Required Fields**:
- `name`: Concept name
- `definition`: What this concept represents
- `domain`: Which domain this concept belongs to
- `evidence`: Evidence refs

---

### 8. rule-map.yaml

**Purpose**: Final business rules and constraints

**Consumer**: DEMAND layer

**Type**: Canonical

**Minimum Structure**:
```yaml
rules:
  - name: string
    constraint: string
    domain: string
    concepts: [string]
    enforcement: string
    evidence: [string]
    violations:
      condition: string
      consequence: string

metadata:
  finalized_at: string
  version: string
  source_decisions: string
```

**Required Fields**:
- `name`: Rule name
- `constraint`: What this rule enforces
- `domain`: Which domain this rule applies to
- `evidence`: Evidence refs

---

### 9. demand-model-map.yaml

**Purpose**: Demand model structures for change analysis

**Consumer**: DEMAND layer

**Type**: Canonical

**Minimum Structure**:
```yaml
demand_models:
  - name: string
    structure: string
    domains: [string]
    concepts: [string]
    rules: [string]
    change_patterns:
      - pattern: string
        impact: string
    evidence: [string]

metadata:
  finalized_at: string
  version: string
  source_decisions: string
```

**Required Fields**:
- `name`: Demand model name
- `structure`: What this model captures
- `domains`: Related domains
- `evidence`: Evidence refs

---

### 10. change-log.yaml

**Purpose**: Semantic model change history

**Consumer**: Audit/versioning

**Type**: Canonical

**Minimum Structure**:
```yaml
changes:
  - timestamp: string
    stage: string
    change_type: string
    item_type: string
    item_name: string
    before: string
    after: string
    rationale: string

metadata:
  log_version: string
  first_entry: string
  last_entry: string
```

**Required Fields**:
- `timestamp`: When change occurred
- `stage`: Which stage made the change
- `change_type`: Add/modify/remove
- `item_name`: What was changed

---

### 11. run-state.yaml

**Purpose**: Semantic runner state

**Consumer**: Runner control

**Type**: Canonical

**Minimum Structure**:
```yaml
run_state:
  current_stage: string
  completed_stages: [string]
  pending_stages: [string]
  blocking_issues: [string]
  warnings: [string]

  stage_status:
    step1_signals:
      status: "pending|running|completed|failed"
      started_at: string
      completed_at: string
    step2_candidates:
      status: "pending|running|completed|failed"
      started_at: string
      completed_at: string
    step3_recommend:
      status: "pending|running|completed|failed"
      started_at: string
      completed_at: string
    step4_review:
      status: "pending|running|completed|failed"
      started_at: string
      completed_at: string
    step5_finalize:
      status: "pending|running|completed|failed"
      started_at: string
      completed_at: string

metadata:
  run_id: string
  started_at: string
  last_updated: string
```

**Required Fields**:
- `current_stage`: Which stage is running
- `completed_stages`: Which stages are done
- `blocking_issues`: What blocks progression

---

## View Outputs

### Intermediate View Outputs

These view outputs are generated during semantic processing for human review and debugging.

#### 1. signals.md

**Purpose**: Human-readable signal summary

**Consumer**: Step1 debugging, signal review

**Type**: View (Intermediate)

**Generated By**: Step1 (Signal Inference)

**Minimum Structure**:
```markdown
# Semantic Signals

## Domain Signals
- Signal: [description]
  - Source: [source]
  - Evidence: [file:line]
  - Confidence: [high|medium|low]

## Concept Signals
- Signal: [description]
  - Source: [source]
  - Evidence: [file:line]
  - Confidence: [high|medium|low]

## Rule Signals
- Signal: [description]
  - Source: [source]
  - Evidence: [file:line]
  - Confidence: [high|medium|low]
```

---

#### 2. candidates.md

**Purpose**: Human-readable candidate summary

**Consumer**: Step2 debugging, candidate review

**Type**: View (Intermediate)

**Generated By**: Step2 (Candidate Synthesis)

**Minimum Structure**:
```markdown
# Semantic Candidates

## Domains
- Name: [name]
  - Responsibility: [what this domain does]
  - Modules: [module list]
  - Evidence: [file:line refs]
  - Confidence: [high|medium|low]

## Concepts
- Name: [name]
  - Definition: [what this concept represents]
  - Relationships: [related concepts]
  - Evidence: [file:line refs]
  - Confidence: [high|medium|low]

## Rules
- Name: [name]
  - Constraint: [what this rule enforces]
  - Evidence: [file:line refs]
  - Confidence: [high|medium|low]
```

---

#### 3. recommendations.md

**Purpose**: Human-readable recommendation summary

**Consumer**: Step3 debugging, recommendation review

**Type**: View (Intermediate)

**Generated By**: Step3 (Scoring & Recommendation)

**Minimum Structure**:
```markdown
# Semantic Recommendations

## Domains
- Name: [name]
  - Score: [0.0-1.0]
  - Rank: [position]
  - Rationale: [why recommended]
  - Recommendation: [accept|review|reject]

## Concepts
- Name: [name]
  - Score: [0.0-1.0]
  - Rank: [position]
  - Rationale: [why recommended]
  - Recommendation: [accept|review|reject]

## Rules
- Name: [name]
  - Score: [0.0-1.0]
  - Rank: [position]
  - Rationale: [why recommended]
  - Recommendation: [accept|review|reject]
```

---

#### 4. review-note.md

**Purpose**: Human-readable review summary

**Consumer**: Architect review, Step4 documentation

**Type**: View (Intermediate)

**Generated By**: Step4 (Review & Evidence)

**Minimum Structure**:
```markdown
# Review Summary

## Accepted Items
- Domain: [name] - [rationale]
- Concept: [name] - [rationale]
- Rule: [name] - [rationale]

## Rejected Items
- Domain: [name] - [rationale]
- Concept: [name] - [rationale]

## Deferred Items
- Domain: [name] - [rationale]

## Evidence Issues
- Item: [name] - [issue description]
```

---

### Final View Outputs

These view outputs are the final human-readable semantic models.

#### 5. domain-map.md

**Purpose**: Human-readable domain map

**Consumer**: Architect review, documentation

**Type**: View (Final)

**Minimum Structure**:
```markdown
# Domain Map

## Domain: [Name]

**Responsibility**: [What this domain does]

**Modules**:
- module1
- module2

**Concepts**:
- concept1
- concept2

**Rules**:
- rule1
- rule2

**Evidence**:
- file:line
- file:line

**Relationships**:
- Depends on: [domain]
- Provides to: [domain]
```

---

#### 6. concept-map.md

**Purpose**: Human-readable concept map

**Consumer**: Architect review, documentation

**Type**: View

**Minimum Structure**:
```markdown
# Concept Map

## Concept: [Name]

**Definition**: [What this concept represents]

**Domain**: [Domain name]

**Relationships**:
- Is a: [concept]
- Has a: [concept]
- Uses: [concept]
- Used by: [concept]

**Rules**:
- rule1
- rule2

**Evidence**:
- file:line
- file:line
```

---

#### 7. rule-map.md

**Purpose**: Human-readable rule map

**Consumer**: Architect review, documentation

**Type**: View

**Minimum Structure**:
```markdown
# Rule Map

## Rule: [Name]

**Constraint**: [What this rule enforces]

**Domain**: [Domain name]

**Concepts**:
- concept1
- concept2

**Enforcement**: [How this rule is enforced]

**Violations**:
- Condition: [When violated]
- Consequence: [What happens]

**Evidence**:
- file:line
- file:line
```

---

#### 8. demand-model-map.md

**Purpose**: Human-readable demand model map

**Consumer**: Architect review, documentation

**Type**: View

**Minimum Structure**:
```markdown
# Demand Model Map

## Demand Model: [Name]

**Structure**: [What this model captures]

**Domains**:
- domain1
- domain2

**Concepts**:
- concept1
- concept2

**Rules**:
- rule1
- rule2

**Change Patterns**:
- Pattern: [pattern]
  Impact: [impact]

**Evidence**:
- file:line
- file:line
```

---

## Output Location

**Canonical outputs**: `docs/semantic/` or semantic workspace
**View outputs**: `docs/semantic/*.md`

---

## Output Versioning

All canonical outputs should include:
- `metadata.generated_at`: ISO 8601 timestamp
- `metadata.version`: Semantic version (if applicable)
- `metadata.source_*`: Source file references

---

## Summary

**11 Canonical Outputs** (YAML):
- signals, candidates, recommendations
- review-decisions, evidence-checks
- domain-map, concept-map, rule-map, demand-model-map
- change-log, run-state

**8 View Outputs** (Markdown):
- **Intermediate**: signals.md, candidates.md, recommendations.md, review-note.md
- **Final**: domain-map.md, concept-map.md, rule-map.md, demand-model-map.md

**All outputs are contract-defined and stable for DEMAND layer consumption.**
