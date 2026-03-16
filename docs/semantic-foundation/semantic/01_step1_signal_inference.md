# Step1: Signal Inference

**Stage**: Step1 (Signal Inference)
**Purpose**: Extract semantic signals from FACT layer outputs
**Status**: Design Document
**Role**: This document is explanatory and must follow canonical contract documents (semantic_stage_contracts.md, semantic_input_contract.md, semantic_output_contract.md).

---

## Goal

Extract semantic signals from FACT layer that indicate:
- Domain boundaries
- Concept definitions
- Business rules
- Demand model structures

**Key Principle**: Signal extraction is **inference from observable facts**, not re-extraction of facts.

---

## Inputs

### Primary Hard Input

**Source**: `docs/semantic-foundation/fact/fact_canonical_sample.yaml`

**Content**:
- `repo_identity`: Repository metadata (name, type, language, build_system)
- `modules`: Observable module structure (name, path, functions, evidence)
- `entrypoints`: Observable entrypoints (name, type, location, command, evidence)
- `core_entities`: Observable data structures (name, type, defined_in, fields, evidence)
- `configuration`: Observable config (name, type, location, evidence)
- `dependencies`: Observable imports and packages
- `execution_flows`: Observable call chains
- `baseline_reference`: Checkpoint metadata (if baseline exists)

**Consumption Rule**: Trust as ground truth, use evidence refs for validation. This is the REQUIRED primary input.

### Auxiliary Soft Input

**Source**: `docs/semantic-foundation/fact/fact_working_summary_sample.yaml`

**Content**:
- System purpose interpretation
- Domain boundary proposals
- Concept role assignments
- Pipeline relationship analysis
- Open questions
- Assumptions

**Consumption Rule**: Use as guidance/bootstrap context, NOT as hard truth. When conflict with canonical, prefer canonical. This input is OPTIONAL.

### Reference Input (Optional)

**Source**: `docs/fact/baseline/*.md` (if available)

**Files**:
- `docs/fact/baseline/purpose.md` - System purpose and non-goals
- `docs/fact/baseline/pipelines.md` - Key execution flows
- `docs/fact/baseline/domains.md` - Domain boundaries (FACT-level)
- `docs/fact/baseline/concepts.md` - Core domain concepts
- `docs/fact/baseline/checkpoint.json` - Version metadata

**Consumption Rule**: Use as additional reference if available. Step1 can proceed without these files.

---

## Outputs

### Canonical Output

**File**: `signals.yaml`

**Location**: `docs/semantic-foundation/semantic/`

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

### View Output

**File**: `signals.md`

**Location**: `docs/semantic-foundation/semantic/`

**Purpose**: Human-readable signal summary for review

---

## Signal Types

### Domain Signals

**Indicators**:
- Module grouping patterns (modules that share responsibility)
- Entrypoint clustering (entrypoints that serve similar purposes)
- Configuration boundaries (config that affects specific modules)
- Dependency isolation (modules with distinct dependency sets)

**Examples**:
- "Modules artifact_writer, state_inspector form Artifact Management domain"
- "Entrypoints semantic-discover, semantic-review form Discovery domain"

### Concept Signals

**Indicators**:
- Core entity definitions (dataclasses, protocols)
- Repeated terminology across modules
- Explicit concept documentation in baseline
- Entity relationship patterns

**Examples**:
- "Artifact Versioning: .vN.md naming pattern across discovery/review"
- "Evidence Traceability: file:line refs in all fact outputs"

### Rule Signals

**Indicators**:
- Validation logic in code
- Constraint enforcement patterns
- Acceptance gates in pipelines
- Schema validation requirements

**Examples**:
- "Baseline Immutability: baseline files cannot be auto-modified"
- "Evidence Requirement: every claim must have file:line evidence"

### Demand Model Signals

**Indicators**:
- Change analysis patterns
- Impact assessment structures
- Diff generation logic
- Version comparison mechanisms

**Examples**:
- "Baseline Diff Model: compare current vs previous baseline"
- "Change Impact Model: identify affected modules from baseline changes"

---

## Program Responsibilities

The Step1 program must:

1. **Read FACT inputs**
   - Load `docs/semantic-foundation/fact/fact_canonical_sample.yaml` (REQUIRED)
   - Load `docs/semantic-foundation/fact/fact_working_summary_sample.yaml` (optional)
   - Load `docs/fact/baseline/*.md` if available (optional reference)

2. **Extract semantic signals**
   - Identify domain boundary indicators from canonical facts
   - Recognize concept definitions from entities and terminology
   - Detect business rule patterns from validation logic
   - Identify demand model structures from change patterns

3. **Assign confidence ratings**
   - High: Strong evidence from multiple sources
   - Medium: Evidence from single source or partial coverage
   - Low: Weak evidence or inference-heavy

4. **Write canonical output**
   - Generate `signals.yaml` with all required fields
   - Write to `docs/semantic-foundation/semantic/signals.yaml`
   - Ensure evidence refs are valid
   - Include metadata (timestamp, version, count)

5. **Render view output**
   - Generate `signals.md` for human review
   - Write to `docs/semantic-foundation/semantic/signals.md`
   - Group signals by type
   - Include confidence ratings

---

## Model Responsibilities

The AI model must:

1. **Identify domain boundary indicators**
   - Recognize module grouping patterns
   - Identify responsibility clustering
   - Detect configuration boundaries

2. **Recognize concept definitions**
   - Extract core entities from canonical facts
   - Identify repeated terminology
   - Map concept relationships

3. **Detect business rule patterns**
   - Identify validation logic
   - Recognize constraint enforcement
   - Extract acceptance gates

4. **Assess signal confidence**
   - Evaluate evidence strength
   - Consider source reliability
   - Rate confidence level

---

## Human Responsibilities

**None** - Step1 is fully automated.

Human review occurs in Step4 (Review & Evidence), not Step1.

---

## Blocking Rules

### Fatal Errors (Stop Execution)

- **BLOCK** if `fact_canonical_sample.yaml` missing
  - `docs/semantic-foundation/fact/fact_canonical_sample.yaml` not found
  - This is the REQUIRED primary input

- **BLOCK** if canonical facts malformed
  - `fact_canonical_sample.yaml` invalid YAML
  - Required top-level keys missing
  - Evidence refs malformed

### Warnings (Continue with Caution)

- **WARN** if `fact_working_summary_sample.yaml` missing
  - Step1 can proceed without auxiliary input
  - May have less context for signal inference

- **WARN** if baseline files missing
  - `docs/fact/baseline/*.md` not found
  - Step1 can proceed without reference input
  - Canonical YAML contains all necessary information

- **WARN** if confidence is low across all signals
  - Less than 30% high-confidence signals
  - Suggests FACT baseline may be incomplete

- **WARN** if signal count is very low
  - Less than 10 total signals
  - Suggests extraction may have failed

---

## Implementation Notes

### Signal Extraction Strategy

1. **Start with canonical facts**
   - Module structure → domain signals
   - Core entities → concept signals
   - Configuration → rule signals

2. **Cross-reference with baseline**
   - `purpose.md` → concept signals
   - `pipelines.md` → domain signals
   - `domains.md` → domain signals
   - `concepts.md` → concept signals

3. **Use working summary as hints**
   - Domain proposals → validate against canonical
   - Concept roles → validate against canonical
   - Open questions → flag as low-confidence areas

### Confidence Rating Guidelines

**High Confidence**:
- Signal supported by multiple FACT sources
- Evidence refs are explicit and verifiable
- Canonical facts directly support the signal

**Medium Confidence**:
- Signal supported by single FACT source
- Evidence refs are partial or indirect
- Working summary supports but canonical is weak

**Low Confidence**:
- Signal inferred from working summary only
- Evidence refs are missing or weak
- Canonical facts don't directly support

---

## Example Signal Extraction

### Input (from fact_canonical_sample.yaml)

```yaml
modules:
  - name: "artifact_writer"
    path: "src/artifact_writer.py"
    functions: ["write_versioned_artifact", "get_latest_working_version_path"]
    evidence: "src/artifact_writer.py:1-520"

  - name: "state_inspector"
    path: "src/state_inspector.py"
    functions: ["inspect_semantic_state", "check_semantic_snapshot"]
    evidence: "src/state_inspector.py:1-250"
```

### Output (signals.yaml)

```yaml
signals:
  domain_signals:
    - signal_type: "module_grouping"
      source: "fact_canonical_sample.yaml:modules"
      evidence: "src/artifact_writer.py:1-520, src/state_inspector.py:1-250"
      confidence: "high"
      interpretation: "artifact_writer and state_inspector form Artifact Management domain"

  concept_signals:
    - signal_type: "entity_definition"
      source: "fact_canonical_sample.yaml:core_entities"
      evidence: "src/artifact_writer.py:write_versioned_artifact"
      confidence: "high"
      interpretation: "Artifact Versioning is a core concept"
```

---

## Relationship with Other Stages

### Step1 → Step2

**Output**: `signals.yaml`
**Consumer**: Step2 (Candidate Synthesis)

Step2 will:
- Read `signals.yaml`
- Group signals into candidates
- Assign candidate names
- Prepare for scoring

### Step1 ← FACT

**Input**: FACT baseline + canonical facts
**Provider**: FACT layer

Step1 does NOT:
- Re-extract facts from repository
- Modify FACT outputs
- Generate new evidence refs

---

## Summary

**Step1 (Signal Inference)**:
- Extracts semantic signals from FACT layer
- Produces `signals.yaml` (canonical) + `signals.md` (view)
- Fully automated (no human review)
- Blocks on missing baseline or malformed canonical facts
- Assigns confidence ratings based on evidence strength

**Key Principle**: Signal extraction is inference from observable facts, not re-extraction.
