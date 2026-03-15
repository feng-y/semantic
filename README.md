# Semantic Harness

Evidence-driven semantic construction pipeline for Claude Code. Extracts structured understanding from repositories through discovery, human review, refinement, and accepted baseline generation.

## What It Does

Semantic Harness builds a versioned semantic model of your repository:

1. **Discover** — samples the repo, extracts facts, identifies domains and concepts
2. **Review** — human architect reviews and provides feedback
3. **Refine** — patches artifacts using architect feedback, validates results
4. **Baseline** — on architect acceptance, synthesizes stable semantic reference

All artifacts are versioned, validated, and stored in `docs/semantic/`.

## Quickstart

```bash
git clone <repo-url> && cd semantic-harness
pip install -e ".[test]"
pytest                    # verify 108 tests pass
```

Then use via Claude Code skill execution:

```
init      → creates docs/semantic/ workspace
discover  → runs full discovery pipeline
refine    → patches artifacts with architect feedback
```

## Installation

See [INSTALL.md](INSTALL.md) for detailed setup instructions.

## Core Commands

| Command    | What it does                                      |
|------------|---------------------------------------------------|
| `init`     | Create `docs/semantic/` workspace directories     |
| `discover` | Run sampling, fact extraction, domain analysis    |
| `refine`   | Patch artifacts using `architect-feedback.md`     |
| `baseline` | Synthesize accepted baseline (requires acceptance)|

## Architecture Overview

```
manifest.yaml          → skill definitions
skills/                → .skill YAML files (discovery, refinement)
prompts/               → .prompt files per pipeline step
src/                   → runtime modules
  artifact_writer.py   → versioned artifact I/O
  context_builder.py   → bounded prompt context assembly
  discovery_executor.py→ discovery pipeline
  refine_executor.py   → refinement + baseline synthesis
  state_inspector.py   → semantic state routing
docs/semantic/           → generated semantic state (not human-written docs)
  schemas/             → artifact schema contracts
  discovery/           → versioned working artifacts (generated)
  review/              → review-summary, architect-feedback (generated)
  baseline/            → accepted baseline (generated, immutable)
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

v1.0.0 — stable. 108 tests passing. All safety boundaries verified.
