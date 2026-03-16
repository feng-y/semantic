# Semantic Candidates Synthesis Prompt

## Goal

Synthesize semantic candidates from signal inputs and generate structured candidates output.

## Input Source

**Primary Input**:
- `signals.yaml` - Semantic signals from Step1

## Candidate Types

Synthesize four types of candidates:

### 1. Domain Candidates
Synthesized from domain_signals:
- Module grouping patterns
- Domain proposals
- Configuration boundaries
- Responsibility clustering

**Synthesis strategy:**
- Group related domain signals
- Identify common themes
- Create stronger domain candidates
- Preserve source signal traceability

### 2. Concept Candidates
Synthesized from concept_signals:
- Entity definitions
- Concept identifications
- Terminology patterns
- Relationship patterns

**Synthesis strategy:**
- Group related concept signals
- Identify core concepts
- Map concept relationships
- Preserve source signal traceability

### 3. Rule Candidates
Synthesized from rule_signals:
- Validation logic patterns
- Constraint enforcement
- Acceptance gates
- Schema validation

**Synthesis strategy:**
- Group related rule signals
- Identify rule patterns
- Create rule candidates
- Preserve source signal traceability

### 4. Demand Model Candidates
Synthesized from demand_pattern_signals:
- Change analysis patterns
- Impact assessment structures
- Diff generation logic
- Version comparison mechanisms

**Synthesis strategy:**
- Group related demand pattern signals
- Identify demand model structures
- Create demand model candidates
- Preserve source signal traceability

## Synthesis Rules

1. **Signal grouping**: Group related signals by type and theme
2. **Candidate creation**: Synthesize stronger candidates from signal groups
3. **Provenance preservation**: Preserve source_signal_ids and evidence_refs
4. **Stable IDs**: Generate stable, hash-based IDs
5. **Confidence inheritance**: Candidate confidence = highest signal confidence in group
6. **Avoid one-to-one copying**: Synthesize, don't just copy signals

## Output Structure

```yaml
domains:
  - id: string
    name: string
    summary: string
    boundary:
      modules: [string]
    source_signal_ids: [string]
    evidence_refs: [string]
    confidence: high|medium|low

concepts:
  - id: string
    name: string
    summary: string
    relationships: [string]
    source_signal_ids: [string]
    evidence_refs: [string]
    confidence: high|medium|low

rules:
  - id: string
    name: string
    summary: string
    source_signal_ids: [string]
    evidence_refs: [string]
    confidence: high|medium|low

demand_models:
  - id: string
    name: string
    summary: string
    source_signal_ids: [string]
    evidence_refs: [string]
    confidence: high|medium|low

metadata:
  generated_at: string
  signals_source: string
  candidate_count: integer
```

## Confidence Guidelines

**High confidence**:
- Multiple high-confidence signals support candidate
- Strong structural evidence
- Clear boundaries

**Medium confidence**:
- Mixed confidence signals
- Partial evidence
- Some ambiguity

**Low confidence**:
- Low-confidence signals only
- Weak evidence
- High ambiguity
