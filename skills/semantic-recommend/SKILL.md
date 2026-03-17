---
name: semantic-recommend
version: "1.0.0"
description: "Generate structured recommendations from semantic candidates. Third stage of semantic layer."
triggers:
  - semantic-recommend
  - score candidates
  - semantic step3
argument-hint: "[--candidates PATH] [--output PATH]"
---

# Semantic Recommend — Recommendation Generation

> Generate structured recommendations from semantic candidates.
> Scores candidates and produces recommendation decisions.
> Third stage of the semantic layer.

## Decision Tree

```
START
  ├─ Has candidates.yaml?
  │   ├─ YES → Load candidates (primary input)
  │   └─ NO  → BLOCK (required input missing)
  │
  ├─ Validate candidate structure
  │   ├─ Valid → Continue
  │   └─ Invalid → BLOCK (malformed candidates)
  │
  ├─ Generate domain recommendations
  ├─ Generate concept recommendations
  ├─ Generate rule recommendations
  ├─ Generate demand model recommendations
  │
  └─ Write recommendations.yaml + recommendations.md → SUCCESS
```

## Execution Steps

### Step 1: Validate Inputs

**Check for:**
- [ ] `docs/fact/candidates.yaml` exists (REQUIRED)
- [ ] candidates.yaml has valid structure (4 candidate groups)

**Blocking conditions:**
- BLOCK if candidates.yaml missing
- BLOCK if candidates.yaml malformed
- BLOCK if candidate groups missing

### Step 2: Generate Domain Recommendations

**Process:**
- Read domains from candidates.yaml
- Evaluate semantic validity
- Compute business_score and value_score
- Determine recommendation status and action
- Preserve candidate_id and evidence linkage

**Output:**
```yaml
domains:
  - id: "rec_domain_abc123"
    name: "Domain Name"
    candidate_id: "domain_abc123"
    semantic_validity: "pass|fail"
    validity_reason: "Reason for validity decision"
    business_score: 7.5  # 1.0-10.0
    value_score: 8.0     # 1.0-10.0
    priority: 8.0        # max(business_score, value_score)
    recommendation:
      status: "recommend|not_recommend|defer"
      action: "keep|merge|drop|backlog|verify_first"
      target_layer: "final_asset|candidate_pool"
      target_asset_type: "domain_map|none"
    recommended_reasons: ["reason1", "reason2"]
    not_recommended_reasons: []
    needs_evidence_check: false
    evidence_gap: null
    merge_target: null
    source_candidate_ids: ["domain_abc123"]
    evidence_refs: ["evidence"]
```

### Step 3: Generate Concept Recommendations

**Process:**
- Read concepts from candidates.yaml
- Evaluate semantic validity
- Compute scores and priority
- Determine recommendation
- Preserve traceability

**Output:** Similar structure to domains, with `target_asset_type: "concept_map"`

### Step 4: Generate Rule Recommendations

**Process:**
- Read rules from candidates.yaml
- Evaluate semantic validity
- Compute scores and priority
- Determine recommendation
- Preserve traceability

**Output:** Similar structure, with `target_asset_type: "rule_map"`

### Step 5: Generate Demand Model Recommendations

**Process:**
- Read demand_models from candidates.yaml
- Evaluate semantic validity
- Compute scores and priority
- Determine recommendation
- Preserve traceability

**Output:** Similar structure, with `target_asset_type: "demand_model_map"`

### Step 6: Write Outputs

**Canonical output:**
- `docs/fact/recommendations.yaml`

**View output:**
- `docs/fact/recommendations.md`

**Metadata:**
```yaml
metadata:
  generated_at: "ISO 8601 timestamp"
  candidates_source: "candidates.yaml"
  recommendation_count: N
```

## When to Use

**Use semantic-recommend when:**
- You have completed semantic-candidates
- candidates.yaml exists and is valid
- You need to generate recommendation decisions
- You are ready for the third semantic stage

**Do NOT use when:**
- candidates.yaml is missing (run semantic-candidates first)
- You need to implement review/finalize (those are later stages)
- You need demand layer logic (that's a different layer)

## Required Inputs

**Primary input (REQUIRED):**
- `docs/fact/candidates.yaml`

**Optional auxiliary context:**
- `docs/fact/signals.yaml` (for traceability)
- `docs/fact/fact_canonical_sample.yaml` (for context)

## Expected Outputs

**Workspace:**
- `docs/fact/`

**Canonical output:**
- `recommendations.yaml` (structured recommendation data)

**View output:**
- `recommendations.md` (human-readable view)

## Capability Boundary

**This skill ONLY handles:**
- Recommendation generation from candidates
- Scoring and priority computation
- Recommendation status/action decisions
- Traceability preservation

**This skill does NOT handle:**
- Review/finalize stages (later capabilities)
- Demand layer logic (different layer)
- Signal extraction (earlier stage)
- Candidate synthesis (earlier stage)

## Allowed Tools

- Read (for loading candidates.yaml)
- Write (for writing outputs)
- Bash (for invoking Python implementation)

## Implementation

This skill is thin and delegates to Python implementation:

```bash
python -m semantic.score_recommend \
  --candidates docs/fact/candidates.yaml \
  --output docs/fact/recommendations.yaml \
  --render-md docs/fact/recommendations.md
```

## Usage Examples

**Basic usage:**
```bash
/semantic-recommend
```

**With custom paths:**
```bash
python -m semantic.score_recommend \
  --candidates path/to/candidates.yaml \
  --output path/to/recommendations.yaml \
  --render-md path/to/recommendations.md
```

## Success Criteria

- [ ] recommendations.yaml created with valid structure
- [ ] recommendations.md created with readable view
- [ ] All 4 recommendation groups present (domains, concepts, rules, demand_models)
- [ ] Priority correctly computed as max(business_score, value_score)
- [ ] Candidate traceability preserved (candidate_id, evidence_refs)
- [ ] Valid status values (recommend, not_recommend, defer)
- [ ] Valid action values (keep, merge, drop, backlog, verify_first)
- [ ] Metadata includes generation timestamp and source

## Example Output Structure

```yaml
domains:
  - id: "rec_domain_2aa02a6c"
    name: "Repository Structure"
    candidate_id: "domain_2aa02a6c"
    semantic_validity: "pass"
    validity_reason: "Clear boundary and high confidence"
    business_score: 8.0
    value_score: 9.0
    priority: 9.0
    recommendation:
      status: "recommend"
      action: "keep"
      target_layer: "final_asset"
      target_asset_type: "domain_map"
    recommended_reasons:
      - "High confidence from canonical fact"
      - "Clear module boundary"
      - "Core repository structure"
    not_recommended_reasons: []
    needs_evidence_check: false
    evidence_gap: null
    merge_target: null
    source_candidate_ids: ["domain_2aa02a6c"]
    evidence_refs: ["14 modules observed"]

concepts: [...]
rules: [...]
demand_models: [...]

metadata:
  generated_at: "2026-03-17T01:00:00Z"
  candidates_source: "candidates.yaml"
  recommendation_count: 6
```
