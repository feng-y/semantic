---
name: semantic-candidates
version: "1.0.0"
description: "Synthesize semantic candidates from signals. Second stage of semantic layer."
triggers:
  - semantic-candidates
  - build candidates
  - semantic step2
argument-hint: "[--signals PATH] [--output PATH]"
---

# Semantic Candidates — Candidate Synthesis

> Synthesize semantic candidates from signal inputs.
> Generates domain, concept, rule, and demand model candidates.
> Second stage of the semantic layer.

## Decision Tree

```
START
  ├─ Has signals.yaml?
  │   ├─ YES → Load signals (primary input)
  │   └─ NO  → BLOCK (required input missing)
  │
  ├─ Validate signal structure
  │   ├─ Valid → Continue
  │   └─ Invalid → BLOCK (malformed signals)
  │
  ├─ Synthesize domain candidates from domain_signals
  ├─ Synthesize concept candidates from concept_signals
  ├─ Synthesize rule candidates from rule_signals
  ├─ Synthesize demand model candidates from demand_pattern_signals
  │
  └─ Write candidates.yaml + candidates.md → SUCCESS
```

## Execution Steps

### Step 1: Validate Inputs

**Check for:**
- [ ] `docs/fact/signals.yaml` exists (REQUIRED)
- [ ] signals.yaml has valid structure (4 signal groups)

**Blocking conditions:**
- BLOCK if signals.yaml missing
- BLOCK if signals.yaml malformed
- BLOCK if signal groups missing

### Step 2: Synthesize Domain Candidates

**Process:**
- Read domain_signals from signals.yaml
- Group related signals
- Synthesize stronger domain candidates
- Preserve source_signal_ids and evidence_refs

**Output:**
```yaml
domains:
  - id: "domain_abc123"
    name: "Domain Name"
    summary: "What this domain does"
    boundary:
      modules: ["module1", "module2"]
    source_signal_ids: ["signal_type"]
    evidence_refs: ["evidence"]
    confidence: "high|medium|low"
```

### Step 3: Synthesize Concept Candidates

**Process:**
- Read concept_signals from signals.yaml
- Group related signals
- Synthesize stronger concept candidates
- Preserve source_signal_ids and evidence_refs

**Output:**
```yaml
concepts:
  - id: "concept_abc123"
    name: "Concept Name"
    summary: "What this concept represents"
    relationships: ["related_concept"]
    source_signal_ids: ["signal_type"]
    evidence_refs: ["evidence"]
    confidence: "high|medium|low"
```

### Step 4: Synthesize Rule Candidates

**Process:**
- Read rule_signals from signals.yaml
- Group related signals
- Synthesize stronger rule candidates
- Preserve source_signal_ids and evidence_refs

**Output:**
```yaml
rules:
  - id: "rule_abc123"
    name: "Rule Name"
    summary: "What this rule enforces"
    source_signal_ids: ["signal_type"]
    evidence_refs: ["evidence"]
    confidence: "high|medium|low"
```

### Step 5: Synthesize Demand Model Candidates

**Process:**
- Read demand_pattern_signals from signals.yaml
- Group related signals
- Synthesize stronger demand model candidates
- Preserve source_signal_ids and evidence_refs

**Output:**
```yaml
demand_models:
  - id: "demand_abc123"
    name: "Demand Model Name"
    summary: "What this demand model represents"
    source_signal_ids: ["signal_type"]
    evidence_refs: ["evidence"]
    confidence: "high|medium|low"
```

### Step 6: Write Outputs

**Canonical output:**
- `docs/fact/candidates.yaml`

**View output:**
- `docs/fact/candidates.md`

**Metadata:**
```yaml
metadata:
  generated_at: "ISO 8601 timestamp"
  signals_source: "signals.yaml"
  candidate_count: N
```

## Usage

### Basic Usage

```bash
python -m semantic.build_candidates \
  --signals docs/fact/signals.yaml \
  --output docs/fact/candidates.yaml \
  --render-md docs/fact/candidates.md
```

### From Skill

```
/semantic-candidates
```

## Constraints

**This skill ONLY:**
- Synthesizes semantic candidates from signals
- Preserves source signal traceability
- Follows semantic input/output contracts
- Generates structured candidates for recommendation

**This skill does NOT:**
- Score or recommend candidates (use semantic-recommend)
- Perform architect review (use semantic-review)
- Generate final models (use semantic-finalize)
- Modify signals or FACT layer

## Success Criteria

✅ **Success when:**
- `candidates.yaml` created with valid YAML structure
- All four candidate groups present (domains, concepts, rules, demand_models)
- Source signal IDs preserved
- Evidence refs preserved
- `candidates.md` view generated
- Metadata includes timestamp and candidate count

❌ **Failure when:**
- `signals.yaml` missing (BLOCK)
- `signals.yaml` malformed (BLOCK)
- Output directory cannot be created (BLOCK)
- YAML generation fails (BLOCK)

⚠️ **Warnings (non-blocking):**
- Candidate count very low (< 4 candidates)
- All candidates have low confidence

## Related Skills

- **semantic-signals**: Extract signals (run before this)
- **semantic-recommend**: Score and recommend candidates (run after this)
- **semantic-review**: Architect review and evidence validation
- **semantic-finalize**: Generate final semantic models

## Implementation

**Backed by:**
- `src/semantic/build_candidates.py` - Candidate synthesis logic
- `src/semantic/models.py` - Candidate models (DomainCandidate, ConceptCandidate, RuleCandidate, DemandModelCandidate)
- `templates/semantic/candidates.template.yaml` - Output template
- `prompts/semantic/semantic_candidates.prompt.md` - Synthesis guidance

**Tests:**
- `tests/semantic/test_build_candidates.py` - Candidate synthesis tests

## Synthesis Strategy

**Deterministic-first approach:**
- Group related signals by type
- Synthesize stronger candidates from signal groups
- Preserve provenance (source_signal_ids, evidence_refs)
- Generate stable IDs (hash-based)
- Avoid one-to-one signal copying unless justified

**Confidence inheritance:**
- Candidate confidence = highest signal confidence in group
- Multiple high-confidence signals → high-confidence candidate
- Mixed confidence signals → medium-confidence candidate

## Output Example

```yaml
domains:
  - id: "domain_a1b2c3d4"
    name: "Repository Structure"
    summary: "Core repository organization and module structure"
    boundary:
      modules: ["all_modules"]
    source_signal_ids: ["module_grouping"]
    evidence_refs: ["14 modules observed"]
    confidence: "high"

concepts:
  - id: "concept_e5f6g7h8"
    name: "Core Entities"
    summary: "Core data structures and entities"
    relationships: ["domain_models", "data_structures"]
    source_signal_ids: ["entity_definition"]
    evidence_refs: ["4 entities observed"]
    confidence: "high"

rules:
  - id: "rule_i9j0k1l2"
    name: "Validation Rules"
    summary: "Validation and constraint enforcement rules"
    source_signal_ids: ["validation_logic"]
    evidence_refs: ["2 validation modules"]
    confidence: "high"

demand_models:
  - id: "demand_m3n4o5p6"
    name: "Change Analysis Model"
    summary: "Change analysis and impact assessment structure"
    source_signal_ids: ["change_analysis_pattern"]
    evidence_refs: ["2 change-related modules"]
    confidence: "medium"

metadata:
  generated_at: "2026-03-17T01:00:00Z"
  signals_source: "signals.yaml"
  candidate_count: 4
```
