---
name: repo-structure
description: Build or refresh repo-level baseline facts from commit history artifacts, precomputed codebase analysis artifacts, and optional architecture documents. Use when the task is to extract structured repo facts, run the repo-structure pipeline, inspect stage status, or regenerate facts.vN.yaml for downstream semantic modeling.
---

# Repo Structure

`repo-structure` is a stage-driven extraction skill.

Its only goal is to convert three upstream evidence sources into a versioned factual baseline:

- commit history artifacts -> `hotspot_map`
- precomputed codebase analysis artifacts -> `codebase_map`
- optional architecture docs + repo evidence -> `architect_augment`

These are validated and fused into:

- `data/repo-structure/baseline/facts.vN.yaml`

This file is the only source-of-truth produced by this skill.

## Usage

### Commands

- `/repo-structure check` - Run preflight checks and print dependency report
- `/repo-structure run` - Run all stages from sample through baseline
- `/repo-structure run --stage <stage>` - Run a specific stage
- `/repo-structure resume` - Resume from last incomplete stage
- `/repo-structure status` - Show current pipeline state
- `/repo-structure reset` - Reset pipeline state, preserve artifacts

### Supported Stages

1. `sample` - Build sampling manifest from 7-file gsd dossier
2. `hotspot` - Consume commit-extract/commit-semantic -> hotspot_map
3. `extract` - LLM workers extract facts from dossier (section-routed)
4. `augment` - LLM workers adjudicate architecture claims vs repo evidence
5. `validate` - Schema + deduplication + conflict detection
6. `baseline` - Source-aware arbitration -> facts.vN.yaml

## Preconditions

### Required Inputs

Before running this skill, these must exist:

- `data/commit-extract/` - upstream commit-extract output (produced by `commit-extract`)
- `.planning/codebase/STRUCTURE.md` - gsd dossier structure file
- `.planning/codebase/ARCHITECTURE.md` - gsd dossier architecture file
- `.planning/codebase/CONCERNS.md` - gsd dossier concerns file
- `.planning/codebase/CONVENTIONS.md` - gsd dossier conventions file
- `.planning/codebase/INTEGRATIONS.md` - gsd dossier integrations file
- `.planning/codebase/STACK.md` - gsd dossier stack file
- `.planning/codebase/TESTING.md` - gsd dossier testing file

### Optional Input

- `docs/ARCHITECTURE.md` - explicit architecture claims document; if absent, augment stage emits empty output

### Important Rules

- `gsd` is an upstream analyzer; this skill consumes `.planning/codebase/` artifacts and does **not** invoke `gsd` internally
- `commit-extract` is an upstream artifact; this skill does **not** generate it internally
- dependencies must be checked before stage execution via preflight
- missing required dependencies fail fast
- do not silently backfill missing upstream inputs inside a stage

## Stages

| Stage | Input | Output | Purpose |
|-------|-------|--------|---------|
| sample | 7-file gsd dossier | `data/repo-structure/sample/manifest.yaml` | Build DocSectionTask manifest for downstream extraction |
| hotspot | `data/commit-extract/`, `data/commit-semantic/patterns/` | `data/repo-structure/maps/hotspot_map.vN.yaml` | Extract recurring change patterns and hotspot signals |
| extract | 7-file gsd dossier, sample manifest | `data/repo-structure/maps/codebase_map.vN.yaml` | Extract atomic fact entries with evidence binding per section |
| augment | `docs/ARCHITECTURE.md`, Python-collected evidence | `data/repo-structure/maps/architect_augment.vN.yaml` | Adjudicate architecture claims vs repo evidence |
| validate | hotspot_map, codebase_map, architect_augment | `data/repo-structure/facts/validated.vN.yaml`, `conflicts.vN.yaml` | Schema check, deduplicate, detect conflicts |
| baseline | validated, conflicts | `data/repo-structure/baseline/facts.vN.yaml`, `facts.latest.yaml`, `snapshot.yaml` | Source-aware arbitration, freeze baseline |

## Output

### Sole Source of Truth

- `data/repo-structure/baseline/facts.vN.yaml` - versioned frozen baseline; the only canonical output of this skill

### Derived Views (intermediate artifacts, not source of truth)

- `data/repo-structure/sample/manifest.yaml` - sampling manifest
- `data/repo-structure/maps/hotspot_map.vN.yaml` - hotspot signals
- `data/repo-structure/maps/codebase_map.vN.yaml` - extracted codebase facts
- `data/repo-structure/maps/architect_augment.vN.yaml` - architecture adjudication
- `data/repo-structure/facts/validated.vN.yaml` - validated facts
- `data/repo-structure/facts/conflicts.vN.yaml` - preserved conflicts
- `data/repo-structure/baseline/snapshot.yaml` - snapshot metadata

### Downstream Rule

Domain Map, Concept Map, and Rule Map are derived views. They must be generated from baseline facts, not hand-edited as a substitute for baseline repair.

## Evidence Model

### Locator Types

| Type | Use For |
|------|---------|
| `file_path` | directory/module roles, fragile files, explicit file-level ownership |
| `symbol` | entry points, registries, macros, interfaces, named abstractions |
| `config_key` | config-driven behavior, feature flags, slot allocation rules |
| `section_ref` | document-level structural rules, conventions, architecture claims without concrete anchors |
| `test_case` | explicit test file + test name pairs |
| `ast_pattern` | registration patterns, structural macros (use sparingly) |

### stable_ref

Canonical stable reference format for evidence comparison, deduplication, and downstream traceability:

- `path:<file_path>` - file path reference
- `symbol:<file_path>::<symbol_name>` - symbol in file
- `config:<config_path>::<key>` - config key
- `section:<source_doc>::<section_path>` - section reference
- `test:<file_path>::<test_name>` - test case

### Evidence Priority

Evidence strength (strongest to weakest):
1. concrete symbol refs with file anchors
2. concrete config refs
3. test/validation evidence tied to claimed behavior
4. multiple aligned evidence items
5. single section-level statement
6. comments only (weakest)

## Key Rules

1. **Do not treat Domain/Concept/Rule Map as outputs of this skill** - only `facts.vN.yaml` is the source of truth; derived views must not be hand-edited
2. **Do not invoke `gsd` from inside this pipeline** - consume precomputed artifacts only
3. **Do not generate `commit-extract` internally** - hotspot consumes it, does not produce it
4. **Do not skip preflight** - all dependencies must be checked before stage execution
5. **Do not batch extract by whole file** - extraction unit is a section task, not a whole file
6. **Do not output summaries from extract** - output unit is a fact entry with evidence binding, not a paragraph
7. **Do not let augment trust architecture docs by default** - adjudicate with evidence; classify as `evidence_backed`, `weakly_backed`, `gap`, or `drift`
8. **Do not collapse weakly_backed/gap/drift** - these statuses are distinct; downstream actions differ
9. **Do not hide conflicts** - preserve them explicitly in `conflicts.vN.yaml`

### Arbitration Priority

When competing facts overlap, resolve in this order:

1. Source priority: `architect > hotspot > codebase`
2. Within same priority: `recurring > evidence_backed > isolated`
3. Snapshot alignment: prefer current `repo_snapshot_commit`
4. If still unresolved: preserve both facts and record the conflict

## Worker Prompts

Worker prompt templates used by extract and augment stages:

- `skills/repo_structure/prompts/extract_codebase.md` - section-based fact extraction worker
- `skills/repo_structure/prompts/augment_architect.md` - architecture claim adjudication worker

## References

Detailed reference documents for implementation:

- `skills/repo_structure/references/pipeline-overview.md` - full pipeline execution map
- `skills/repo_structure/references/evidence-model.md` - fact entry and evidence item schemas
- `skills/repo_structure/references/arbitration-rules.md` - baseline arbitration decision rules
- `skills/repo_structure/references/preflight-rules.md` - dependency check contract
- `skills/repo_structure/references/gotchas.md` - highest-value failure modes

## Architecture

```
commit-extract/  +  commit-semantic/patterns/
      +-----------+----------+
      v                       v
    hotspot              hotspot
      v                       |
7-file gsd dossier  -->  sample --> extract --> codebase_map
                                                   |
docs/ARCHITECTURE.md + evidence collection --> augment --> architect_augment
                                                   |
                                         hotspot_map + codebase_map + architect_augment
                                                   |
                                              validate --> validated + conflicts
                                                   |
                                                   v
                                               baseline --> facts.vN.yaml
```

The pipeline is stage-driven with independent versioning. All three source maps (`hotspot_map`, `codebase_map`, `architect_augment`) have independent versions. The baseline snapshot records their combination.

## Implementation

### CLI Usage

```bash
# Run preflight checks
python -m skills.repo_structure.run check

# Run full pipeline
python -m skills.repo_structure.run run

# Run single stage
python -m skills.repo_structure.run run --stage extract

# Resume from last checkpoint
python -m skills.repo_structure.run resume

# Check current state
python -m skills.repo_structure.run status

# Reset state
python -m skills.repo_structure.run reset
```

### Dispatcher Integration

The `dispatcher.py` module routes `repo-structure` commands via:

```python
from skills.repo_structure.run import RepoStructureRunner
_REPO_STRUCTURE_RUNNER = RepoStructureRunner()

# In dispatch():
if command == "repo-structure":
    return {"command": command, "status": "ok",
            "exit_code": _REPO_STRUCTURE_RUNNER.main(sys.argv[2:])}
```
