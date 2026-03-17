# Semantic Harness

Claude Code plugin / skill repository for semantic repository understanding.

Builds a versioned semantic model of your repository through evidence-driven discovery, human review, iterative refinement, and accepted baseline generation.

## What It Does

1. **Discover** — samples the repo, extracts facts, identifies domains and concepts
2. **Review** — human architect reviews and provides feedback
3. **Refine** — patches artifacts using architect feedback, validates results
4. **Baseline** — on architect acceptance, synthesizes stable semantic reference

All artifacts are versioned, validated, and stored in `docs/fact/`.

## Quickstart

```bash
git clone <repo-url> && cd semantic-harness
pip install -e ".[test]"
pytest                    # verify tests pass in your current checkout
```

Then use via Claude Code skill execution:

```
# Composite workflows
semantic-fact-pipeline     → run FACT pipeline (discover → review → refine → baseline)
semantic-pipeline          → run semantic pipeline (signals → candidates → recommend → review → finalize)

# Individual skills
semantic-init              → creates docs/fact/ workspace
semantic-discover          → runs full discovery pipeline
semantic-refine            → patches artifacts with architect feedback
semantic-baseline          → synthesizes accepted baseline
semantic-status            → reports current semantic state
semantic-reset             → resets working state
```

## Installation

### From Repository

```bash
# Install directly from local path
claude code plugin install /path/to/semantic-harness

# Or install from git URL
claude code plugin install git+https://github.com/feng-y/semantic-harness.git
```

The plugin will be available in Claude Code with skills prefixed by the plugin name:
```
/semantic-harness:semantic-init
/semantic-harness:semantic-discover
/semantic-harness:semantic-review
...
```

### For Python Development

```bash
git clone <repo-url> && cd semantic-harness
pip install -e ".[test]"
pytest                    # verify tests pass
```

See [INSTALL.md](INSTALL.md) for detailed setup instructions.

## Public Skills

The plugin provides skills organized into layers and workflows:

### Composite Workflows

| Skill | Description | Pipeline |
|-------|-------------|----------|
| `semantic-fact-pipeline` | Run FACT workflow (discover → review → refine → baseline) | FACT Layer |
| `semantic-pipeline` | Run semantic workflow (signals → candidates → recommend → review → finalize) | Semantic Layer |

### FACT Layer (Foundation)

| Skill | Description | Stage |
|-------|-------------|-------|
| `semantic-init` | Create workspace directories | Setup |
| `semantic-discover` | Run sampling, fact extraction, domain analysis | Discovery |
| `semantic-review` | Present artifacts for architect review | Review |
| `semantic-refine` | Patch artifacts using architect feedback | Refinement |
| `semantic-baseline` | Synthesize accepted baseline (requires acceptance) | Finalization |

### Semantic Layer (Advanced)

| Skill | Description | Stage |
|-------|-------------|-------|
| `semantic-signals` | Extract semantic signals from repository facts | Stage 1 |
| `semantic-candidates` | Synthesize semantic candidates from signals | Stage 2 |
| `semantic-recommend` | Score and recommend semantic assets | Stage 3 |
| `semantic-review` | Generate review decisions from recommendations | Stage 4 |
| `semantic-finalize` | Generate final semantic asset maps | Stage 5 |

### Utility Skills

| Skill | Description |
|-------|-------------|
| `semantic-status` | Report current state and recommend next action |
| `semantic-reset` | Reset working state (preserves baseline and schemas) |

Each skill is defined in `skills/<skill-name>/SKILL.md` with YAML frontmatter containing metadata and markdown documentation.

## Repository Structure

```
Plugin manifest:
  .claude-plugin/
    plugin.json          → Claude Code plugin manifest
    marketplace.json     → marketplace metadata
  skills/                → skill definitions (SKILL.md format)
    semantic-fact-pipeline/  → FACT workflow composite
    semantic-pipeline/       → Semantic workflow composite
    semantic-init/
    semantic-discover/
    semantic-signals/
    semantic-candidates/
    semantic-recommend/
    semantic-review/
    semantic-finalize/
    semantic-refine/
    semantic-baseline/
    semantic-status/
    semantic-reset/
  prompts/               → prompt files per pipeline step

Internal runtime:
  src/                   → Python runtime modules
    semantic/            → semantic layer implementation
      extract_signals.py
      build_candidates.py
      score_recommend.py
      apply_review.py
      evidence_check.py
      finalize_assets.py
    artifact_writer.py   → versioned artifact I/O
    context_builder.py   → bounded prompt context assembly
    discovery_executor.py→ discovery pipeline
    refine_executor.py   → refinement + baseline synthesis
    dispatcher.py        → command routing
    state_inspector.py   → semantic state routing

Semantic state (generated):
  docs/fact/  → generated semantic state
    schemas/             → artifact schema contracts
    discovery/           → versioned working artifacts (generated)
    review/              → review-summary, architect-feedback (generated)
    baseline/            → accepted baseline (generated, immutable)

Documentation:
  docs/semantic-design/  → architecture decision records
  docs/review/           → development reports and audit artifacts
```

> **Note:** `docs/fact/` contains machine-generated semantic state, not ordinary documentation. The `discovery/`, `review/`, and `baseline/` subdirectories are written by the pipeline at runtime.

## Documentation

- [INSTALL.md](INSTALL.md) — prerequisites, setup, verification
- [USER_GUIDE.md](USER_GUIDE.md) — workflow, commands, failure handling
- [CHANGELOG.md](CHANGELOG.md) — version history
- `docs/fact/design/` — architecture decision records (001–010)
- `docs/review/` — development reports, audits, migration artifacts

## Release Status

v0.0.1 — stable. Test status is tracked by current CI/local `pytest` results.
