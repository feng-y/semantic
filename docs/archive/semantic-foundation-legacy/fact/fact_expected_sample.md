# FACT Layer Expected Sample

## 1. FACT Layer Definition

**FACT** = Factual Artifact Collection and Traceability

The FACT layer is the **evidence-driven foundation** of semantic understanding. It extracts, validates, and versions observable facts about the repository without interpretation, abstraction, or design intent.

**IMPORTANT**: As of 2026-03-16, FACT outputs are split into two contracts:
1. **Canonical Facts** (`fact_canonical_sample.yaml`) - Observable facts only
2. **Working Summary** (`fact_working_summary_sample.yaml`) - Interpretation and analysis

### What FACT Is

- **Observable evidence**: Files, code structure, imports, entrypoints, configuration
- **Traceable claims**: Every assertion backed by file paths, line numbers, or commands
- **Versioned artifacts**: All outputs are immutable snapshots with version numbers
- **Schema-validated**: Every artifact must satisfy structural contracts in `docs/fact/schemas/`
- **Split contracts**: Canonical facts separated from working summary

### What FACT Is Not

- **Not semantic modeling**: FACT does not synthesize "what the system means"
- **Not demand analysis**: FACT does not infer "what users need" or "what should change"
- **Not architecture**: FACT does not propose boundaries, layers, or design patterns

---

## 2. FACT Layer Inputs

| Input | Source | Purpose |
|-------|--------|---------|
| Repository tree | `git ls-files`, directory structure | Sampling scope |
| Source files | Selected `.py`, `.yaml`, `.md`, `.skill`, `.prompt` | Evidence extraction |
| Configuration | `manifest.yaml`, `pyproject.toml`, `.gitignore` | Build/runtime facts |
| Existing baseline | `docs/fact/baseline/*.md` (if exists) | Change analysis context |

---

## 3. FACT Layer Outputs (Canonical)

### 3.1 Discovery Artifacts (Working State)

These are **versioned, mutable** artifacts generated during discovery and refined through architect feedback.

| Artifact | Location | Purpose | Agent-Consumable |
|----------|----------|---------|------------------|
| `sampling-report.md` | `docs/fact/discovery/` | File selection log | No (human audit) |
| `repo-facts.vN.md` | `docs/fact/discovery/` | Observable repository structure | Partial (Evidence sections) |
| `repo-understanding.vN.md` | `docs/fact/discovery/` | Purpose, pipelines, concepts with evidence | Yes (structured fields) |
| `domain-candidates.vN.md` | `docs/fact/discovery/` | Candidate domain boundaries | Yes (Domain sections) |
| `knowledge-confidence.vN.md` | `docs/fact/discovery/` | Confidence assessment per claim | Yes (Confidence ratings) |

### 3.2 Review Artifacts (Human-Agent Interaction)

| Artifact | Location | Purpose | Agent-Consumable |
|----------|----------|---------|------------------|
| `review-summary.vN.md` | `docs/fact/review/` | Consolidated summary for architect | Partial (System Summary) |
| `architect-feedback.md` | `docs/fact/review/` | Human corrections and acceptance gate | Yes (structured corrections) |
| `semantic-change-log.md` | `docs/fact/review/` | Diff log between refine cycles | No (human audit) |

### 3.3 Baseline Artifacts (Accepted State)

These are **immutable** artifacts synthesized only after architect acceptance.

| Artifact | Location | Purpose | Agent-Consumable |
|----------|----------|---------|------------------|
| `purpose.md` | `docs/fact/baseline/` | System purpose and non-goals | Yes (Primary Purpose field) |
| `pipelines.md` | `docs/fact/baseline/` | Key execution flows | Yes (Pipeline sections) |
| `domains.md` | `docs/fact/baseline/` | Domain boundaries | Yes (Domain sections) |
| `concepts.md` | `docs/fact/baseline/` | Core domain concepts | Yes (Concept sections) |
| `checkpoint.json` | `docs/fact/baseline/` | Source version traceability | Yes (version metadata) |
| `change-analysis.vN.md` | `docs/fact/review/` | Impact analysis from baseline | Yes (structured sections) |

---

## 4. FACT Layer and Current Pipeline Mapping

### Current Pipeline Phases

```
init → discover → review → refine → baseline
```

### Mapping to FACT Layer

| Phase | FACT Role | Outputs | Human Role |
|-------|-----------|---------|------------|
| **init** | Create workspace structure | `docs/fact/{discovery,review,baseline,schemas}/` | None |
| **discover** | Extract observable facts | `repo-facts`, `repo-understanding`, `domain-candidates`, `knowledge-confidence`, `review-summary` (all `.v1.md`) | None |
| **review** | Present facts for validation | Display `review-summary.vN.md` | Architect reads and writes `architect-feedback.md` |
| **refine** | Patch facts with corrections | Updated `.vN+1.md` artifacts, `semantic-change-log.md` | Architect reviews changes |
| **baseline** | Synthesize accepted facts | `purpose.md`, `pipelines.md`, `domains.md`, `concepts.md`, `checkpoint.json`, `change-analysis.v1.md` | Architect adds `acceptance: true` |

### Why This Is FACT, Not Semantic

- **discover/review/refine** = iterative fact extraction and validation
- **baseline** = accepted fact snapshot, not semantic model synthesis
- **No interpretation layer**: Current pipeline does not abstract facts into "semantic intent" or "behavioral contracts"
- **No demand layer**: Current pipeline does not analyze "what should change" or "user needs"

---

## 5. FACT Output Split: Canonical vs Working Summary

**As of 2026-03-16**, FACT outputs are split into two distinct contracts to improve semantic input quality:

### 5.1 Canonical Facts (`fact_canonical_sample.yaml`)

**Purpose**: Observable, evidence-backed facts only

**Contains**:
- Module names, file paths, function signatures
- Entrypoint definitions, execution flows
- Configuration values, build system facts
- Evidence refs (file:line)
- Version metadata, checkpoint data

**Does NOT contain**:
- Purpose interpretation
- Role assignments
- Domain proposals
- Relationship analysis
- Open questions
- Assumptions

**Schema**: See `fact_canonical_contract.md` for frozen schema

**Template**: `templates/fact/fact-canonical.template.yaml`

### 5.2 Working Summary (`fact_working_summary_sample.yaml`)

**Purpose**: Interpretation, analysis, and working context

**Contains**:
- System purpose interpretation
- Domain boundary proposals
- Concept role assignments
- Pipeline relationship analysis
- Open questions for architect
- Assumptions and uncertainties
- Confidence ratings

**Does NOT contain**:
- Module names, file paths (these are in canonical)
- Evidence refs (these are in canonical)
- Version numbers (these are in canonical)

**Schema**: Mutable, optimized for human review

**Template**: `templates/fact/fact-working-summary.template.yaml`

### 5.3 Contract Mapping

See `fact_contract_mapping.md` for detailed rules on what goes where.

**Key principle**: Observable → Canonical, Interpreted → Working Summary

---

## 6. FACT Canonical Outputs Specification

### 5.1 repo-facts.vN.md

**Purpose**: Observable repository structure facts

**Agent-Consumable Fields**:
- `Repository.Primary Language`
- `Repository.Build System`
- `Repository.Repository Type`
- `Modules[].Name`, `Modules[].Path`, `Modules[].Responsibility`
- `Entrypoints[].Name`, `Entrypoints[].Type`, `Entrypoints[].Location`
- `Core Entities[].Name`, `Core Entities[].Type`, `Core Entities[].Role`
- `Configuration[].Name`, `Configuration[].Type`, `Configuration[].Location`

**Human-Only Fields**:
- All `Evidence` fields (file paths for audit)

### 5.2 repo-understanding.vN.md

**Purpose**: System purpose, pipelines, and concepts with evidence

**Agent-Consumable Fields**:
- `System Purpose` (text block)
- `Pipelines[].Pipeline Name`, `Pipelines[].Purpose`, `Pipelines[].Flow`, `Pipelines[].Inputs`, `Pipelines[].Outputs`, `Pipelines[].Concepts`
- `Concepts[].Concept Name`, `Concepts[].Description`, `Concepts[].Role`, `Concepts[].Used By`
- `Candidate Domains[].Domain Name`, `Candidate Domains[].Description`, `Candidate Domains[].Related Pipelines`

**Human-Only Fields**:
- All `Evidence` fields
- All `Confidence` fields (for architect assessment)
- `Open Questions` section

### 5.3 domain-candidates.vN.md

**Purpose**: Candidate domain boundaries

**Agent-Consumable Fields**:
- `Candidate Domains[].Domain Name`
- `Candidate Domains[].Description`
- `Candidate Domains[].Related Pipelines`

**Human-Only Fields**:
- `Evidence` fields

### 5.4 knowledge-confidence.vN.md

**Purpose**: Confidence assessment per claim

**Agent-Consumable Fields**:
- `Confidence` (overall rating: high/medium/low)
- Structured confidence ratings per section

**Human-Only Fields**:
- `Evidence` (rationale for confidence level)

### 5.5 review-summary.vN.md

**Purpose**: Consolidated summary for architect review

**Agent-Consumable Fields**:
- `System Summary` (text block)
- `Main Pipelines` (list)
- `Core Concepts` (list)
- `Candidate Domains` (list)

**Human-Only Fields**:
- `Assumptions` (for architect validation)
- `Questions for Architect` (for feedback loop)

### 5.6 Baseline Artifacts (purpose.md, pipelines.md, domains.md, concepts.md)

**Purpose**: Immutable accepted fact snapshot

**Agent-Consumable**: Entire content (structured fields only)

**Human-Only**: None (baseline is canonical agent input)

### 5.7 change-analysis.vN.md

**Purpose**: Impact analysis from baseline changes

**Agent-Consumable Fields**:
- `Change Intent` (text block)
- `Affected Pipelines` (list)
- `Affected Domains and Concepts` (list)
- `Impact and Risks` (structured)
- `Suggested Next Changes` (list)

**Human-Only**: None (change-analysis is agent-facing)

---

## 6. Agent Consumption Patterns

### Pattern 1: Initial Discovery

Agent reads:
- `repo-facts.vN.md` → Extract repository type, entrypoints, modules
- `repo-understanding.vN.md` → Extract system purpose, pipelines, concepts

Agent uses for:
- Understanding execution flows
- Identifying key components
- Mapping concepts to code

### Pattern 2: Baseline-Driven Work

Agent reads:
- `baseline/purpose.md` → Primary purpose, non-goals
- `baseline/pipelines.md` → Canonical execution flows
- `baseline/domains.md` → Domain boundaries
- `baseline/concepts.md` → Core concepts

Agent uses for:
- Change impact analysis
- Refactoring scope
- Test coverage planning

### Pattern 3: Change Analysis

Agent reads:
- `baseline/*.md` → Current accepted state
- `change-analysis.vN.md` → Impact of proposed changes

Agent uses for:
- Risk assessment
- Dependency analysis
- Rollback planning

---

## 7. Markdown vs. Agent-Consumable Trade-offs

### Current Design Choice

**Markdown with structured fields** (current implementation)

Pros:
- Human-readable for architect review
- Git-diffable for change tracking
- Schema-validatable via section headings
- Evidence fields co-located with claims

Cons:
- Requires parsing for agent consumption
- Field extraction is regex-based (fragile)
- No type safety for structured data

### Future Consideration (Not Current Scope)

**YAML/JSON companion files** (not implemented)

Would provide:
- Type-safe agent consumption
- Direct deserialization
- Schema validation via JSON Schema

Trade-off:
- Dual maintenance burden (Markdown + YAML)
- Drift risk between human view and agent view

**Current Decision**: Markdown-only, with structured field conventions. Agent consumption via regex parsing in `context_builder.py`.

---

## 8. What FACT Layer Enables (Future Semantic/Demand Layers)

### Semantic Layer (Not Yet Implemented)

Would consume FACT outputs to:
- Synthesize behavioral contracts from pipelines
- Abstract domain models from concepts
- Infer architectural patterns from structure

### Demand Layer (Not Yet Implemented)

Would consume Semantic outputs to:
- Analyze change requests against semantic model
- Propose refactoring strategies
- Generate implementation plans

### Why FACT Must Stay Pure

- **Semantic drift**: If FACT includes interpretation, semantic layer has no stable foundation
- **Demand contamination**: If FACT includes "should" statements, demand analysis is circular
- **Evidence loss**: If FACT abstracts too early, traceability is lost

---

## 9. FACT Layer Quality Gates

### Discovery Phase Gates

1. **Sampling coverage**: At least 20 files sampled across modules
2. **Evidence traceability**: Every claim has file path or command
3. **Schema compliance**: All artifacts pass schema validation
4. **Confidence assessment**: Every section has confidence rating

### Baseline Phase Gates

1. **Architect acceptance**: `acceptance: true` in `architect-feedback.md`
2. **Structural completeness**: `knowledge-confidence` has expected sections
3. **Evidence depth**: `repo-understanding` has Evidence sections
4. **Domain non-empty**: `domain-candidates` has at least one domain

### Change Analysis Gates

1. **Baseline exists**: `baseline/*.md` files present
2. **Baseline complete**: All 4 baseline files (purpose, pipelines, domains, concepts)
3. **Change traceability**: Change analysis references baseline artifacts

---

## 10. FACT Layer Boundaries

### In Scope

- Observable code structure
- Execution flows from entrypoints
- Configuration and build facts
- Domain candidate identification
- Confidence assessment

### Out of Scope

- Semantic intent modeling
- Behavioral contract synthesis
- Change demand analysis
- Implementation planning
- Refactoring strategies

### Boundary Enforcement

- **Schema validation**: Rejects artifacts with interpretation language
- **Evidence requirement**: Every claim must have file/command evidence
- **Confidence separation**: Confidence is metadata, not claim content
- **Baseline immutability**: Accepted facts cannot be auto-modified

---

## Summary

The FACT layer is the **evidence-driven foundation** of the current `semantic-harness` pipeline. It extracts, validates, and versions observable repository facts through `discover → review → refine → baseline` phases. All outputs are Markdown artifacts with structured fields, stored in `docs/fact/`, and validated against schemas in `docs/fact/schemas/`.

**Current pipeline = FACT layer only**. Semantic and demand layers are future work.
