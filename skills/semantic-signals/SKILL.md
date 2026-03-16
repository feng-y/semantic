---
name: semantic-signals
version: "1.0.0"
description: "Extract semantic signals from FACT layer inputs. First stage of semantic layer."
triggers:
  - semantic-signals
  - extract signals
  - semantic step1
argument-hint: "[--fact-root PATH] [--output PATH]"
---

# Semantic Signals — Signal Extraction

> Extract semantic signals from FACT layer inputs.
> Generates domain, concept, rule, and demand pattern signals.
> First stage of the semantic layer.

## Decision Tree

```
START
  ├─ Has fact_canonical_sample.yaml?
  │   ├─ YES → Load canonical facts (primary input)
  │   └─ NO  → BLOCK (required input missing)
  │
  ├─ Has fact_working_summary_sample.yaml?
  │   ├─ YES → Load working summary (auxiliary input)
  │   └─ NO  → WARN (can proceed without it)
  │
  ├─ Has docs/fact/baseline/*.md?
  │   ├─ YES → Load baseline (reference input)
  │   └─ NO  → WARN (can proceed without it)
  │
  ├─ Extract domain signals
  ├─ Extract concept signals
  ├─ Extract rule signals
  ├─ Extract demand pattern signals
  │
  └─ Write signals.yaml + signals.md → SUCCESS
```

## Execution Steps

### Step 1: Validate Inputs

**Check for:**
- [ ] `docs/semantic-foundation/fact/fact_canonical_sample.yaml` exists (REQUIRED)
- [ ] `docs/semantic-foundation/fact/fact_working_summary_sample.yaml` exists (optional)
- [ ] `docs/fact/baseline/*.md` exists (optional)

**Blocking conditions:**
- BLOCK if canonical YAML missing
- BLOCK if canonical YAML malformed
- WARN if working summary missing (can proceed)
- WARN if baseline files missing (can proceed)

### Step 2: Extract Domain Signals

**Look for:**
- Module grouping patterns (from canonical:modules)
- Configuration boundaries (from canonical:configuration)
- Domain proposals (from working:domain_proposals)
- Responsibility clustering patterns

**Output:**
```yaml
domain_signals:
  - signal_type: "module_grouping"
    source: "fact_canonical:modules"
    evidence: "N modules observed"
    confidence: "high|medium|low"
    summary: "Description"
```

### Step 3: Extract Concept Signals

**Look for:**
- Core entity definitions (from canonical:core_entities)
- Repeated terminology patterns
- Concept identifications (from working:concepts)
- Entity relationship patterns

**Output:**
```yaml
concept_signals:
  - signal_type: "entity_definition"
    source: "fact_canonical:core_entities"
    evidence: "N entities observed"
    confidence: "high|medium|low"
    summary: "Description"
```

### Step 4: Extract Rule Signals

**Look for:**
- Validation logic patterns (from canonical:modules)
- Constraint enforcement patterns
- Acceptance gate patterns
- Schema validation requirements

**Output:**
```yaml
rule_signals:
  - signal_type: "validation_logic"
    source: "fact_canonical:modules"
    evidence: "N validation modules"
    confidence: "high|medium|low"
    summary: "Description"
```

### Step 5: Extract Demand Pattern Signals

**Look for:**
- Change analysis patterns (from canonical:modules)
- Impact assessment structures
- Diff generation logic
- Version comparison mechanisms

**Output:**
```yaml
demand_pattern_signals:
  - signal_type: "change_analysis_pattern"
    source: "fact_canonical:modules"
    evidence: "N change modules"
    confidence: "high|medium|low"
    summary: "Description"
```

### Step 6: Write Outputs

**Canonical output:**
- `docs/semantic-foundation/semantic/signals.yaml`

**View output:**
- `docs/semantic-foundation/semantic/signals.md`

**Metadata:**
```yaml
metadata:
  generated_at: "ISO 8601 timestamp"
  fact_source: "fact_canonical_sample.yaml"
  signal_count: N
```

## Usage

### Basic Usage

```bash
python -m semantic.extract_signals \
  --fact-root docs/semantic-foundation/fact \
  --output docs/semantic-foundation/semantic/signals.yaml \
  --render-md docs/semantic-foundation/semantic/signals.md
```

### From Skill

```
/semantic-signals
```

## Constraints

**This skill ONLY:**
- Extracts semantic signals
- Preserves evidence and source traceability
- Follows semantic input/output contracts

**This skill does NOT:**
- Generate semantic candidates (use semantic-candidates)
- Score or recommend (use semantic-recommend)
- Perform final model generation (use semantic-finalize)
- Modify FACT layer outputs

## Success Criteria

✅ **Success when:**
- `signals.yaml` created with valid YAML structure
- All four signal groups present (domain, concept, rule, demand_pattern)
- Evidence refs preserved where available
- `signals.md` view generated
- Metadata includes timestamp and signal count

❌ **Failure when:**
- `fact_canonical_sample.yaml` missing (BLOCK)
- `fact_canonical_sample.yaml` malformed (BLOCK)
- Output directory cannot be created (BLOCK)
- YAML generation fails (BLOCK)

⚠️ **Warnings (non-blocking):**
- `fact_working_summary_sample.yaml` missing
- Baseline files missing
- Signal count very low (< 10 signals)

## Related Skills

- **semantic-discover**: FACT layer discovery (run before this)
- **semantic-candidates**: Generate candidates from signals (run after this)
- **semantic-recommend**: Score and recommend candidates
- **semantic-finalize**: Generate final semantic models

## Implementation

**Backed by:**
- `src/semantic/extract_signals.py` - Signal extraction logic
- `src/semantic/models.py` - Signal models (Signal, DomainSignal, ConceptSignal, RuleSignal, DemandPatternSignal)
- `templates/semantic/signals.template.yaml` - Output template
- `prompts/semantic/semantic_signals.prompt.md` - Extraction guidance

**Tests:**
- `tests/semantic/test_extract_signals.py` - Signal extraction tests

## Confidence Guidelines

**High confidence** (strong evidence):
- Multiple evidence sources
- Explicit observable patterns
- Strong structural indicators

**Medium confidence** (moderate evidence):
- Single evidence source
- Implicit patterns
- Partial coverage

**Low confidence** (weak evidence):
- Weak evidence
- Inference-heavy
- Ambiguous patterns

## Output Example

```yaml
domain_signals:
  - signal_type: "module_grouping"
    source: "fact_canonical:modules"
    evidence: "15 modules observed"
    confidence: "high"
    summary: "Repository contains 15 distinct modules"

concept_signals:
  - signal_type: "entity_definition"
    source: "fact_canonical:core_entities"
    evidence: "8 entities observed"
    confidence: "high"
    summary: "Repository defines 8 core entities"

rule_signals:
  - signal_type: "validation_logic"
    source: "fact_canonical:modules"
    evidence: "2 validation modules"
    confidence: "high"
    summary: "Repository contains 2 validation modules"

demand_pattern_signals:
  - signal_type: "change_analysis_pattern"
    source: "fact_canonical:modules"
    evidence: "3 change-related modules"
    confidence: "medium"
    summary: "Repository contains 3 change analysis modules"

metadata:
  generated_at: "2026-03-17T00:00:00Z"
  fact_source: "fact_canonical_sample.yaml"
  signal_count: 4
```
