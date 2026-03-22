# Repo-Structure & Domain-Model Implementation Plan

**Date:** 2026-03-22
**Spec:** `2026-03-22-repo-structure-domain-model-design.md`
**Phase:** 1 (fact) + 2 (domain-model) combined
**Status:** Pending implementation

---

## Overview

Implement two Team Agent pipelines that extract structured semantic knowledge from a codebase and its git history, replacing the deprecated `semantic-fact-pipeline` and `semantic-pipeline` commands.

**Phase 1 — repo-structure (fact):** `sample` → `extract` → `validate` → `hotspot` → `baseline`
**Phase 2 — domain-model:** `signals` → `candidates` → `score` → `aggregate` → `distill`

Command hard cutoff (no aliases retained):

| New | Old (removed) |
|-----|---------------|
| `/repo-structure` | `/semantic-fact-pipeline` |
| `/domain-model` | `/semantic-pipeline` |

---

## Evidence Model

Every fact entry carries evidence with `locator` (not `line_range`/`snippet`):

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

Evidence priority (when sources conflict):
1. **architect** — evidence-backed augmentation only (evidence + rationale + stable_ref)
2. **rule-validated hotspot** — git history signals validated by rules
3. **codebase** — static structure from code analysis

---

## Task 1: Phase 1 — repo-structure

### 1.1. Create directory structure

```
skills/repo-structure/
├── SKILL.md
├── run.py
└── prompts/
    ├── extract_codebase.md
    ├── extract_hotspot.md
    ├── validate_facts.md
    └── score_domain.md   # shared with domain-model
```

### 1.2. Implement `skills/repo-structure/run.py`

Follow the pattern established by `skills/commit-extract/run.py` and `skills/commit-semantic/run.py`:

```python
class RepoStructureRunner(SkillRunner):
    STAGES = ["sample", "extract", "validate", "hotspot", "baseline"]
    PIPELINE = "repo-structure"

    # Public API (used by tests and main agent)
    def _batch_units(self, units, batch_size=20): ...
    def _spawn_worker(self, batch, prompt_template): ...
    def _get_worker_prompt_template(self, name): ...
```

**Stage implementations:**

| Stage | Description |
|-------|-------------|
| `sample` | Deterministic file tree + key file sampling; output to `data/repo-structure/sample/` |
| `extract` | Spawn worker agents to extract structure facts from sampled code; output to `data/repo-structure/maps/codebase_map.yaml` |
| `validate` | Rule/schema validation; invalid facts to `data/repo-structure/facts/` |
| `hotspot` | Extract change signals from git history (churn, author distribution, bugfix density); output to `data/repo-structure/maps/hotspot_map.yaml`. Reuses commit-extract artifacts if available. |
| `baseline` | Freeze versioned fact baseline to `data/repo-structure/baseline/facts.vN.yaml` |

**Output structure:**

```
data/repo-structure/
├── sample/
├── maps/
│   ├── codebase_map.yaml
│   ├── hotspot_map.yaml
│   └── architect_augment.yaml   # added by architect (manual)
├── facts/
├── baseline/
│   └── facts.vN.yaml
└── state.json
```

### 1.3. Write `skills/repo-structure/SKILL.md`

Main agent orchestration template. Load into context at start of each run.

```markdown
---
name: repo-structure
description: Extract structured facts from codebase + git history
---

# Repo Structure

[Main agent orchestration steps per stage]
[Reference run.py for deterministic parts]
[Worker spawning via Task tool for LLM analysis]
```

### 1.4. Write worker prompt templates

- `prompts/extract_codebase.md` — extract structure facts from sampled files (symbol types, relationships, invariants)
- `prompts/extract_hotspot.md` — extract change signals from git history
- `prompts/validate_facts.md` — validate facts against schema and rules

### 1.5. Add E2E tests

Follow pattern from `tests/e2e/test_commit_extract.py`:

- `test_repo_structure_produces_baseline_yaml`
- `test_facts_have_evidence_with_locator`
- `test_hotspot_extracts_change_signals`

### 1.6. Add CLI entry point

In `src/dispatcher.py`, add routing for `/repo-structure` command.

---

## Task 2: Phase 2 — domain-model

### 2.1. Create directory structure

```
skills/domain-model/
├── SKILL.md
├── run.py
└── prompts/
    ├── extract_signals.md
    ├── generate_candidates.md
    ├── score_candidates.md
    └── distill_domain.md
```

### 2.2. Implement `skills/domain-model/run.py`

```python
class DomainModelRunner(SkillRunner):
    STAGES = ["signals", "candidates", "score", "aggregate", "distill"]
    PIPELINE = "domain-model"
```

**Prerequisite:** Requires `data/repo-structure/baseline/facts.vN.yaml`.

**Stage implementations:**

| Stage | Description |
|-------|-------------|
| `signals` | Read fact baseline; extract domain signals (priority, conflicts, coverage gaps) |
| `candidates` | Worker agents generate domain candidates |
| `score` | Worker agents score candidates (clarity, boundary, reusability) |
| `aggregate` | Group by domain; extract patterns |
| `distill` | Synthesize canonical domain assets |

**Output structure:**

```
data/domain-model/
├── units/all.yaml
├── scored/
│   └── units.yaml
├── patterns/
│   └── {domain}.yaml
├── assets/
│   └── {domain}-asset.yaml
└── state.json
```

### 2.3. Write `skills/domain-model/SKILL.md`

### 2.4. Write worker prompt templates

- `prompts/extract_signals.md` — read facts, extract domain signals
- `prompts/generate_candidates.md` — generate domain unit candidates
- `prompts/score_candidates.md` — score candidates
- `prompts/distill_domain.md` — synthesize canonical assets

### 2.5. Add E2E tests

- `test_domain_model_requires_fact_baseline`
- `test_domain_model_produces_assets`

---

## Task 3: Hard cutoff old commands

In `src/dispatcher.py`:

1. Remove routing for `/semantic-fact-pipeline`
2. Remove routing for `/semantic-pipeline`
3. Verify `/repo-structure` and `/domain-model` are the only available commands

---

## Task 4: Update project docs

After Phase 1 + 2 complete:

1. **README.md** — update command table, remove old commands
2. **docs/superpowers/ARCHITECTURE.md** — confirm Team Agent pattern documented
3. **docs/superpowers/specs/** — ensure spec is committed

---

## Verification Gates

After each task:

| Gate | Command |
|------|---------|
| repo-structure produces valid YAML | `python -c "import yaml; yaml.safe_load(open('data/repo-structure/baseline/facts.v0.yaml'))"` |
| All facts have evidence | `grep -c "evidence:" data/repo-structure/baseline/facts.vN.yaml` |
| Evidence uses locator (no line_range) | grep for `line_range` should return 0 |
| domain-model reads fact baseline | baseline must exist before domain-model runs |
| Old commands return error | `/semantic-fact-pipeline` should not route |
| Tests pass | `pytest tests/e2e/test_repo_structure.py tests/e2e/test_domain_model.py -q` |

---

## Files to create

```
skills/repo-structure/SKILL.md          (new)
skills/repo-structure/run.py            (new)
skills/repo-structure/prompts/extract_codebase.md   (new)
skills/repo-structure/prompts/extract_hotspot.md    (new)
skills/repo-structure/prompts/validate_facts.md     (new)
tests/e2e/test_repo_structure.py        (new)
skills/domain-model/SKILL.md            (new)
skills/domain-model/run.py              (new)
skills/domain-model/prompts/extract_signals.md      (new)
skills/domain-model/prompts/generate_candidates.md  (new)
skills/domain-model/prompts/score_candidates.md    (new)
skills/domain-model/prompts/distill_domain.md       (new)
tests/e2e/test_domain_model.py           (new)
```

## Files to modify

```
src/dispatcher.py                       (add /repo-structure, /domain-model; remove old)
README.md                               (update commands)
```

## Implementation order

1. `skills/repo-structure/run.py` + E2E tests
2. `skills/repo-structure/SKILL.md` + prompt templates
3. `skills/domain-model/run.py` + E2E tests
4. `skills/domain-model/SKILL.md` + prompt templates
5. `src/dispatcher.py` hard cutoff
6. Update project docs
7. Commit + push
