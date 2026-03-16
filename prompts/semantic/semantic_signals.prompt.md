# Semantic Signals Extraction Prompt

## Goal

Extract semantic signals from FACT layer inputs and generate structured signals output.

## Input Sources

**Primary Hard Input**:
- `fact_canonical_sample.yaml` - Observable facts only

**Auxiliary Soft Input**:
- `fact_working_summary_sample.yaml` - Interpretation and guidance

## Signal Types

Extract four types of signals:

### 1. Domain Signals
Indicators of domain boundaries:
- Module grouping patterns
- Configuration boundaries
- Responsibility clustering
- Dependency isolation

### 2. Concept Signals
Indicators of concept definitions:
- Core entity definitions
- Repeated terminology
- Explicit concept documentation
- Entity relationship patterns

### 3. Rule Signals
Indicators of business rules:
- Validation logic
- Constraint enforcement patterns
- Acceptance gate patterns
- Schema validation requirements

### 4. Demand Pattern Signals
Indicators of demand model structures:
- Change analysis patterns
- Impact assessment structures
- Diff generation logic
- Version comparison mechanisms

## Extraction Rules

1. **Evidence-based**: Every signal must reference evidence from FACT inputs
2. **Confidence rating**: Assign high/medium/low confidence based on evidence strength
3. **Source traceability**: Preserve source refs (canonical vs working summary)
4. **No interpretation**: Extract signals, don't invent semantic models yet
5. **Deterministic**: Same inputs should produce same signals

## Output Structure

```yaml
domain_signals:
  - signal_type: string
    source: string
    evidence: string
    confidence: high|medium|low
    summary: string

concept_signals:
  - signal_type: string
    source: string
    evidence: string
    confidence: high|medium|low
    summary: string

rule_signals:
  - signal_type: string
    source: string
    evidence: string
    confidence: high|medium|low
    summary: string

demand_pattern_signals:
  - signal_type: string
    source: string
    evidence: string
    confidence: high|medium|low
    summary: string

metadata:
  generated_at: string
  fact_source: string
  signal_count: integer
```

## Confidence Guidelines

**High confidence**:
- Multiple evidence sources
- Explicit observable patterns
- Strong structural indicators

**Medium confidence**:
- Single evidence source
- Implicit patterns
- Partial coverage

**Low confidence**:
- Weak evidence
- Inference-heavy
- Ambiguous patterns
