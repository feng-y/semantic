# Repo-Structure & Domain-Model Design

**Date:** 2026-03-22
**Status:** Draft — pending implementation

---

## Overview

Two-phase semantic foundation pipeline for extracting structured system knowledge from a codebase and its git history.

- **repo-structure** — Codebase structure facts + Hotspot signals + Architect augmentation → Versioned fact baseline
- **domain-model** — Consumes fact baseline, produces semantic domain models → Consumed by Harness layer

Architecture: Full alignment with Team Agent pattern (same as commit-extract/commit-semantic).

---

## Critical Constraints

### 1. Evidence Model

Every fact entry MUST carry evidence with locator (no line_range/snippet):

```yaml
repo_snapshot_commit: <HEAD at run start>

evidence:
  - source_type: codebase | hotspot | architect
    file_path: src/hermes/operator_registry.py
    locator_type: symbol | ast_pattern | config_key | test_case
    locator: "REGISTER_OPERATOR_BY_OPS"
    stable_ref: <symbol_signature_hash or file_blob_sha>
    rationale: Why this evidence is relevant
```

**Progressive disclosure:** A single semantic object maps to multiple code anchors.

### 2. Evidence Priority (Fact-Based)

When evidence conflicts across sources:

1. **architect** — architect augmentation (MUST be evidence-backed: has evidence + rationale + stable_ref)
2. **rule-validated hotspot** — git history signals validated by rules
3. **codebase** — static structure from code analysis

### 3. Hotspot Signal Extraction

When no commit artifact exists, `repo-structure` extracts hotspot signals directly from git history:

- Change frequency per module/file (churn)
- Author distribution
- Bugfix density (`bugfix:` / `fix:` prefix ratio)
- Default window: all available commits (not capped)

### 4. Architect Augmentation

Architect supplements hotspots with domain-level knowledge that code/hotspot alone cannot infer:

- Thread safety constraints
- Global uniqueness invariants
- Configuration-driven behavior rules
- Registration/composition patterns

Must include evidence anchors (not just textual claims).

---

## Repo-Structure Pipeline

### Command

```
/repo-structure
```

### Stages

| Stage | Description |
|-------|-------------|
| `sample` | Deterministic code sampling (file tree + key files) |
| `extract` | Worker agents extract structure facts from sampled code |
| `validate` | Rule/schema validation of extracted facts |
| `hotspot` | Extract change signals from git history (or reuse existing commit artifact) |
| `augment` | Architect reviews and adds domain-level augmentation |
| `baseline` | Freeze versioned fact baseline |

### Output

```
data/repo-structure/
├── sample/           # Raw sampling output
├── maps/             # Worker outputs (codebase_map, hotspot_map, augment_map)
│   ├── codebase_map.yaml
│   ├── hotspot_map.yaml
│   └── architect_augment.yaml
├── facts/            # Validated fact entries
├── baseline/         # Versioned frozen baseline
│   └── facts.vN.yaml
└── state.json        # Pipeline state
```

### Data Schema: Fact Entry

```yaml
fact_id: <uuid>
domain: <problem domain>
category: domain | concept | rule | invariant
statement: <human-readable fact>
priority: P0 | P1 | P2
repo_snapshot_commit: <HEAD at run start>

evidence:
  - source_type: codebase | hotspot | architect
    file_path:
    locator_type: symbol | ast_pattern | config_key | test_case
    locator:
    stable_ref:
    rationale:

conflicts_with: [<fact_id>]  # If any
resolution_reason: <when override applied>

metadata:
  generated_at: <ISO timestamp>
  mapper_version: <tool version>
```

---

## Domain-Model Pipeline

### Command

```
/domain-model
```

### Prerequisites

Requires `data/repo-structure/baseline/facts.vN.yaml`.

### Stages

| Stage | Description |
|-------|-------------|
| `signals` | Read fact baseline, extract domain signals |
| `candidates` | Worker agents generate domain candidates |
| `score` | Worker agents score candidates (clarity, boundary, reusability) |
| `aggregate` | Group by domain, extract patterns |
| `distill` | Synthesize canonical domain assets |

### Output

```
data/domain-model/
├── units/all.yaml          # All domain units
├── scored/                 # Scored candidates
│   └── units.yaml
├── patterns/                # Aggregated patterns per domain
│   └── {domain}.yaml
├── assets/                  # Canonical domain assets
│   └── {domain}-asset.yaml
└── state.json
```

---

## Architecture (Team Agent Pattern)

Identical to commit-extract/commit-semantic:

```
SKILL.md expands into main agent context
    ↓
Main agent orchestrates via Task tool (batching, aggregation)
    ↓
Worker agents do isolated LLM analysis (fresh context, no token bloat)
    ↓
Workers return structured results (YAML/JSON)
    ↓
Main agent writes output files
```

### SKILL.md Structure

```markdown
---
name: repo-structure
description: Extract structured facts from codebase + git history
---

# Repo Structure

[Main agent orchestration steps]

## Worker Agents

[Describe each worker type and when spawned]

## Output

[Output format and location]
```

### Worker Prompt Templates

```
skills/repo-structure/prompts/
├── extract_codebase.md
├── extract_hotspot.md
├── validate_facts.md
└── score_domain.md
```

### run.py Structure

```python
class RepoStructureRunner(SkillRunner):
    STAGES = ["sample", "extract", "validate", "hotspot", "augment", "baseline"]

    def _batch_units(self, units, batch_size=20): ...
    def _spawn_worker(self, batch, prompt_template): ...
    def _get_worker_prompt_template(self, name): ...
```

---

## Commands

| New Command | Old Command (Hard Cutoff) |
|-------------|---------------------------|
| `/repo-structure` | `/semantic-fact-pipeline` |
| `/domain-model` | `/semantic-pipeline` |

No aliases retained.

---

## Data Flow

```
git commits + code tree
    ↓
repo-structure (Team Agent)
    ↓ sample → extract → validate → hotspot → augment → baseline
data/repo-structure/baseline/facts.vN.yaml
    ↓
domain-model (Team Agent)
    ↓ signals → candidates → score → aggregate → distill
data/domain-model/assets/{domain}-asset.yaml
    ↓
Harness layer (Demand Matching, Execution Verification)
```

---

## Key Decisions

1. **Evidence model uses locator (not line_range/snippet)** — stable across formatting/reformatting
2. **Hotspot always runs** — extracts from git if no commit artifact exists
3. **Architect augmentation is evidence-backed** — must have evidence + rationale + stable_ref to override
4. **Evidence priority: architect > rule-validated hotspot > codebase** — all sources are fact-based
5. **No aliases** — hard cutoff of old commands
6. **Team Agent architecture** — aligned with commit-extract/commit-semantic pattern
