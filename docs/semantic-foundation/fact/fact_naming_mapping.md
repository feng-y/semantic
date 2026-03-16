# FACT Naming Mapping

## 1. Why Current Pipeline = FACT Layer Only

### Current Reality

The existing `discover → review → refine → baseline` pipeline operates **entirely within the FACT layer**:

1. **discover** extracts observable facts with evidence
2. **review** presents facts for human validation
3. **refine** patches facts based on corrections
4. **baseline** synthesizes accepted facts into canonical form

### What's Missing

- **No semantic layer**: Current pipeline does not abstract facts into "semantic intent", "behavioral contracts", or "domain models"
- **No demand layer**: Current pipeline does not analyze "what should change", "user needs", or "impact analysis for future work"

### Why This Matters

Calling the current pipeline "semantic" is misleading. It's a **fact extraction and validation system**, not a semantic modeling system.

---

## 2. Naming Mapping: Old → FACT

### 2.1 Artifact Names

| Old Name | FACT Interpretation | Why |
|----------|---------------------|-----|
| `repo-facts.vN.md` | **FACT: Repository Structure** | Observable structure facts (modules, entrypoints, config) |
| `repo-understanding.vN.md` | **FACT: System Purpose and Flows** | Purpose, pipelines, concepts extracted from code |
| `domain-candidates.vN.md` | **FACT: Candidate Boundaries** | Observed domain boundaries, not designed architecture |
| `knowledge-confidence.vN.md` | **FACT: Confidence Assessment** | Confidence ratings for extracted facts |
| `review-summary.vN.md` | **FACT: Consolidated Facts** | Summary of facts for architect review |
| `architect-feedback.md` | **FACT: Corrections** | Human corrections to extracted facts |
| `baseline/{purpose,pipelines,domains,concepts}.md` | **FACT: Accepted Baseline** | Synthesized canonical facts, not semantic model |
| `change-analysis.vN.md` | **FACT: Baseline Diff** | Diff between baseline versions, not impact analysis |

### 2.2 Directory Names

| Old Name | FACT Interpretation | Why |
|----------|---------------------|-----|
| `docs/fact/` | **FACT: Generated State** | Should be `docs/fact/` or `docs/fact-state/` |
| `docs/fact/discovery/` | **FACT: Working Artifacts** | Versioned fact extraction outputs |
| `docs/fact/review/` | **FACT: Review Artifacts** | Human-agent interaction on facts |
| `docs/fact/baseline/` | **FACT: Accepted Artifacts** | Immutable accepted facts |
| `docs/fact/schemas/` | **FACT: Artifact Schemas** | Structural contracts for fact artifacts |

### 2.3 Phase Names

| Old Name | FACT Interpretation | Why |
|----------|---------------------|-----|
| `discover` | **FACT: Extract** | Extract observable facts from repository |
| `review` | **FACT: Validate** | Human validates extracted facts |
| `refine` | **FACT: Patch** | Patch facts with corrections |
| `baseline` | **FACT: Synthesize** | Synthesize accepted facts into canonical form |

### 2.4 Skill Names

| Old Name | FACT Interpretation | Recommended Rename |
|----------|---------------------|-------------------|
| `semantic-init` | **FACT: Initialize Workspace** | `fact-init` |
| `semantic-discover` | **FACT: Extract Facts** | `fact-extract` |
| `semantic-review` | **FACT: Present Facts** | `fact-review` |
| `semantic-refine` | **FACT: Patch Facts** | `fact-refine` |
| `semantic-baseline` | **FACT: Synthesize Baseline** | `fact-baseline` |
| `semantic-status` | **FACT: Report State** | `fact-status` |
| `semantic-reset` | **FACT: Reset State** | `fact-reset` |

**Note**: Renaming skills is **not recommended now**. Keep current names for backward compatibility. This mapping is for **conceptual clarity only**.

---

## 3. Why Semantic and Demand Are Not in Current Pipeline

### 3.1 What Semantic Layer Would Do

**Semantic layer** abstracts facts into **meaning and intent**:

- **Input**: FACT baseline (purpose, pipelines, domains, concepts)
- **Process**: Abstract facts into semantic models (behavioral contracts, domain boundaries, interaction patterns)
- **Output**: Semantic model (e.g., "Authentication Domain", "Data Flow Contract", "API Boundary")

**Example**:
- **FACT**: "Pipeline: Discovery Pipeline, Flow: sampling → repo-facts → evidence-extraction"
- **SEMANTIC**: "Discovery Domain: Responsible for extracting and validating repository facts through evidence-driven sampling"

### 3.2 What Demand Layer Would Do

**Demand layer** analyzes **what should change**:

- **Input**: FACT baseline + Semantic model + Change request
- **Process**: Impact analysis, risk assessment, change planning
- **Output**: Demand analysis (e.g., "Affected domains", "Breaking changes", "Migration path")

**Example**:
- **FACT**: "Entrypoint: semantic-discover, Type: skill"
- **SEMANTIC**: "Discovery Domain: Entry point for fact extraction"
- **DEMAND**: "Change request: Add incremental discovery → Impact: Modify discovery_executor.py, Add new skill, Update baseline schema"

### 3.3 Why Not Mix Them Now

1. **Current pipeline is fact-only**: No abstraction, no interpretation, no design intent
2. **Semantic requires stable facts**: Can't build semantic model on unstable fact foundation
3. **Demand requires semantic model**: Can't analyze impact without understanding semantic boundaries
4. **Mixing layers = confusion**: Calling facts "semantic" makes it unclear what's observable vs. interpreted

---

## 4. Migration Path: FACT → Semantic → Demand

### Phase 1: Stabilize FACT (Current)

- ✅ Extract facts with evidence
- ✅ Validate facts through human review
- ✅ Synthesize accepted baseline
- ✅ Version and track fact changes

### Phase 2: Add Semantic Layer (Future)

- ❌ Abstract facts into semantic models
- ❌ Define domain boundaries and contracts
- ❌ Model behavioral patterns and interactions
- ❌ Generate semantic documentation

**Input**: `docs/fact/baseline/*.md` (FACT)
**Output**: `docs/fact-model/*.yaml` (SEMANTIC)

### Phase 3: Add Demand Layer (Future)

- ❌ Analyze change requests against semantic model
- ❌ Assess impact and risks
- ❌ Generate migration plans
- ❌ Track demand evolution

**Input**: `docs/fact-model/*.yaml` (SEMANTIC) + Change request
**Output**: `docs/demand-analysis/*.md` (DEMAND)

---

## 5. Canonical FACT Output Contract

### 5.1 What FACT Layer Must Provide

For downstream semantic layer to consume, FACT must provide:

1. **Stable baseline**: Immutable accepted facts in `docs/fact/baseline/`
2. **Structured format**: YAML or JSON for agent consumption
3. **Evidence traceability**: Every claim backed by file paths
4. **Version metadata**: `checkpoint.json` with source version tracking
5. **Confidence ratings**: Per-claim confidence assessment

### 5.2 FACT Canonical Output Shape

```yaml
fact_layer_version: "1.0"
repo_identity: {...}
repo_facts: {...}
repo_understanding: {...}
domain_candidates: {...}
knowledge_confidence: {...}
review_summary: {...}
baseline_reference: {...}
```

See `fact_expected_sample.yaml` for full specification.

### 5.3 What Semantic Layer Will Consume

Semantic layer will read:
- `docs/fact/baseline/*.md` (human-readable)
- `docs/fact/baseline/fact-canonical.yaml` (agent-consumable)
- `docs/fact/baseline/checkpoint.json` (version metadata)

Semantic layer will NOT read:
- `docs/fact/discovery/*.md` (working state, not canonical)
- `docs/fact/review/*.md` (human interaction, not facts)

---

## 6. Key Principles

### 6.1 FACT Layer Principles

1. **Evidence-driven**: Every claim must have file path or command evidence
2. **Observable only**: No interpretation, abstraction, or design intent
3. **Versioned**: All outputs are immutable snapshots
4. **Schema-validated**: All artifacts must satisfy structural contracts
5. **Human-validated**: Architect must accept before baseline synthesis

### 6.2 Why Not Call It "Semantic"

- **Semantic** implies meaning, intent, and abstraction
- **FACT** is observable, traceable, and evidence-based
- **Calling facts "semantic"** conflates extraction with interpretation
- **Separation of concerns**: FACT → Semantic → Demand is a clear pipeline

### 6.3 Why Not Implement Semantic Now

1. **FACT is not stable**: Current baseline still evolving
2. **Semantic requires design**: Need to define semantic model schema
3. **Premature abstraction**: Don't abstract before facts are validated
4. **Focus on foundation**: Get FACT right before building on top

---

## 7. Summary

| Layer | Current Status | Input | Output | Purpose |
|-------|---------------|-------|--------|---------|
| **FACT** | ✅ Implemented | Repository | `baseline/*.md` | Extract and validate observable facts |
| **Semantic** | ❌ Not implemented | `baseline/*.md` | `semantic-model/*.yaml` | Abstract facts into meaning and intent |
| **Demand** | ❌ Not implemented | `semantic-model/*.yaml` + Change request | `demand-analysis/*.md` | Analyze what should change |

**Current pipeline = FACT only.**

**Next step**: Stabilize FACT baseline, then design Semantic layer.

**Do not**: Mix FACT and Semantic in current pipeline.
