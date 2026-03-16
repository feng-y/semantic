# Semantic Recommendation Generation Prompt

## Goal

Generate structured recommendations from semantic candidates and produce recommendations.yaml output.

## Input Source

**Primary Input**:
- `candidates.yaml` - Semantic candidates from Step2

**Optional Auxiliary Context**:
- `signals.yaml` - For traceability
- `fact_canonical_sample.yaml` - For context

## Recommendation Generation

For each candidate, generate a recommendation with:

### 1. Semantic Validity Evaluation

Evaluate whether the candidate is semantically valid:

**Rules:**
- PASS if confidence is high
- PASS if confidence is medium and has evidence
- FAIL if confidence is low
- FAIL if missing required fields

**Output:**
```yaml
semantic_validity: "pass|fail"
validity_reason: "Reason for decision"
```

### 2. Score Computation

Compute business and value scores (1.0-10.0):

**Business Score:**
- Base score from confidence level
- Bonus for evidence strength
- Reflects business value

**Value Score:**
- Base score from confidence level
- Bonus for signal quality
- Reflects technical value

**Priority:**
```
priority = max(business_score, value_score)
```

### 3. Recommendation Decision

Determine status and action:

**Status values:**
- `recommend` - Should be included
- `not_recommend` - Should be excluded
- `defer` - Needs more work

**Action values:**
- `keep` - Include in final assets
- `merge` - Merge with another candidate
- `drop` - Exclude from consideration
- `backlog` - Defer to later
- `verify_first` - Needs verification before inclusion

**Decision Rules:**
- If validity=fail: not_recommend + drop
- If priority >= 7.0: recommend + keep
- If priority >= 5.0: recommend + verify_first
- If priority < 5.0: defer + backlog

### 4. Reason Generation

Generate lists of reasons:

**recommended_reasons:**
- Why this candidate should be included
- Based on validity, confidence, evidence, scores

**not_recommended_reasons:**
- Why this candidate should be excluded
- Based on validity failures, low confidence, missing evidence

### 5. Evidence Check

Determine if additional evidence is needed:

```yaml
needs_evidence_check: boolean
evidence_gap: "Description of missing evidence" | null
```

### 6. Traceability Preservation

Preserve linkage to source candidates:

```yaml
candidate_id: "domain_abc123"
source_candidate_ids: ["domain_abc123"]
evidence_refs: ["evidence from candidate"]
```

## Output Structure

```yaml
domains:
  - id: "rec_domain_abc123"
    name: "Domain Name"
    candidate_id: "domain_abc123"
    semantic_validity: "pass"
    validity_reason: "High confidence with strong evidence"
    business_score: 8.5
    value_score: 8.3
    priority: 8.5
    recommendation:
      status: "recommend"
      action: "keep"
      target_layer: "final_asset"
      target_asset_type: "domain_map"
    recommended_reasons:
      - "Semantic validity passed"
      - "High confidence level"
      - "Strong evidence support (1 refs)"
      - "High business value (score: 8.5)"
      - "High technical value (score: 8.3)"
    not_recommended_reasons: []
    needs_evidence_check: false
    evidence_gap: null
    merge_target: null
    source_candidate_ids: ["domain_abc123"]
    evidence_refs: ["14 modules observed"]

concepts:
  - id: "rec_concept_def456"
    name: "Concept Name"
    candidate_id: "concept_def456"
    # ... similar structure

rules:
  - id: "rec_rule_ghi789"
    name: "Rule Name"
    candidate_id: "rule_ghi789"
    # ... similar structure

demand_models:
  - id: "rec_demand_jkl012"
    name: "Demand Model Name"
    candidate_id: "demand_jkl012"
    # ... similar structure

metadata:
  generated_at: "2026-03-17T01:00:00Z"
  candidates_source: "candidates.yaml"
  recommendation_count: 6
```

## Deterministic Rules

1. **Validity evaluation**: Based on confidence + evidence
2. **Score computation**: Deterministic formulas
3. **Priority computation**: Always max(business_score, value_score)
4. **Recommendation decision**: Based on validity + priority thresholds
5. **Stable IDs**: Hash-based from candidate name

## Quality Requirements

- All 4 recommendation groups must be present (even if empty)
- Priority must equal max(business_score, value_score)
- Status must be one of: recommend, not_recommend, defer
- Action must be one of: keep, merge, drop, backlog, verify_first
- Traceability must be preserved (candidate_id, evidence_refs)
- Scores must be in range 1.0-10.0
- If action=merge, merge_target must be provided
- If needs_evidence_check=true, evidence_gap must be provided
