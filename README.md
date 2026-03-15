# Semantic Harness

Claude Code plugin / skill repository for semantic repository understanding.

Builds a versioned semantic model of your repository through evidence-driven discovery, human review, iterative refinement, and accepted baseline generation.

## What It Does

1. **Discover** — samples the repo, extracts facts, identifies domains and concepts
2. **Review** — human architect reviews and provides feedback
3. **Refine** — patches artifacts using architect feedback, validates results
4. **Baseline** — on architect acceptance, synthesizes stable semantic reference

All artifacts are versioned, validated, and stored in `docs/semantic/`.

## Quickstart

```bash
git clone <repo-url> && cd semantic-harness
pip install -e ".[test]"
pytest                    # verify 143 tests pass
```

Then use via Claude Code skill execution:

```
semantic-init      → creates docs/semantic/ workspace
semantic-discover  → runs full discovery pipeline
semantic-refine    → patches artifacts with architect feedback
semantic-baseline  → synthesizes accepted baseline
semantic-status    → reports current semantic state
semantic-reset     → resets working state
```

## Installation

See [INSTALL.md](INSTALL.md) for detailed setup instructions.

## Public Skills

| Skill | Description |
|-------|-------------|
| `semantic-init` | Create `docs/semantic/` workspace directories |
| `semantic-discover` | Run sampling, fact extraction, domain analysis |
| `semantic-review` | Present artifacts for architect review |
| `semantic-refine` | Patch artifacts using `architect-feedback.md` |
| `semantic-baseline` | Synthesize accepted baseline (requires acceptance) |
| `semantic-status` | Report current semantic state and recommend next action |
| `semantic-reset` | Reset working state (preserves baseline and schemas) |

## Repository Structure

```
Plugin-facing layer:
  manifest.yaml          → plugin manifest (skill registry)
  skills/                → .skill YAML files (7 public skills)
  prompts/               → .prompt files per pipeline step

Internal runtime:
  src/                   → Python runtime modules
    artifact_writer.py   → versioned artifact I/O
    context_builder.py   → bounded prompt context assembly
    discovery_executor.py→ discovery pipeline
    refine_executor.py   → refinement + baseline synthesis
    dispatcher.py        → command routing
    state_inspector.py   → semantic state routing

Semantic state (generated):
  docs/semantic/           → generated semantic state (not human-written docs)
    schemas/             → artifact schema contracts
    discovery/           → versioned working artifacts (generated)
    review/              → review-summary, architect-feedback (generated)
    baseline/            → accepted baseline (generated, immutable)

Documentation:
  docs/semantic-design/  → human-written architecture decision records
  docs/review/           → development reports and audit artifacts
```

> **Note:** `docs/semantic/` contains machine-generated semantic state, not ordinary documentation. The `discovery/`, `review/`, and `baseline/` subdirectories are written by the pipeline at runtime. `docs/semantic/schemas/` defines the structural contracts these artifacts must satisfy. Human-written design docs live in `docs/semantic-design/`.

## Documentation

- [INSTALL.md](INSTALL.md) — prerequisites, setup, verification
- [USER_GUIDE.md](USER_GUIDE.md) — workflow, commands, failure handling
- [CHANGELOG.md](CHANGELOG.md) — version history
- `docs/semantic-design/` — architecture decision records (001–010)
- `docs/review/` — development reports, audits, migration artifacts

## Release Status

v1.0.0 — stable. 143 tests passing. All safety boundaries verified.
