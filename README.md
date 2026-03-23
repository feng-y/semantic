# semantic-harness

Claude Code skill repository for extracting structured semantic knowledge from a codebase and its git history.

## Installation

### Marketplace (recommended)

Register the plugin marketplace and install:

```
/plugin marketplace add feng-y/semantic
/plugin install semantic-harness@semantic
```

This exposes all 14 skills listed below.

### Manual

```bash
pip install -e ".[test]"
pytest tests/test_system.py -q
```

---

## 14 Claude Code Skills

All skills are invoked with `/<name>` in Claude Code.

### FACT Pipeline (repo structure discovery)

| Command | Purpose |
|---------|---------|
| `/semantic-discover` | Stage 1: sample + extract facts from codebase |
| `/semantic-review` | Stage 2: architect reviews discovery artifacts |
| `/semantic-refine` | Stage 3: patch artifacts with review feedback |
| `/semantic-baseline` | Stage 4: accept and lock baseline |
| `/semantic-reset` | Reset working state (preserves baseline) |
| `/semantic-status` | Show current pipeline state |

### Semantic Pipeline (domain extraction)

| Command | Purpose |
|---------|---------|
| `/semantic-signals` | Stage 1: extract signals from fact baseline |
| `/semantic-candidates` | Stage 2: synthesize domain candidates |
| `/semantic-recommend` | Stage 3: score and recommend |
| `/semantic-finalize` | Stage 4: finalize asset maps |

### Git History Analysis

| Command | Purpose |
|---------|---------|
| `/commit-extract` | Extract commits by month with LLM-regenerated logs |
| `/commit-semantic` | Classify, score, aggregate, and distill commit patterns |

### Repo Structure

| Command | Purpose |
|---------|---------|
| `/repo-structure` | Build versioned baseline facts from hotspots + codebase |

---

## Quick Start

### 1. Discover repo structure

```
/semantic-discover
```

### 2. Analyze git history

```
/commit-extract run
/commit-semantic run
```

### 3. Build semantic layer

```
/semantic-signals
/semantic-candidates
```

---

## Output Artifacts

```
data/
  commit-extract/YYYY-MM.yaml   # commits by month
  commit-semantic/
    units/all.yaml              # change units
    functional/{high,medium,low}/units.yaml
    non-functional/all/units.yaml
    patterns/{module}.yaml      # aggregated patterns
    canonical-demands.yaml     # distilled demands
    summary.yaml               # export statistics
  repo-structure/
    baseline/facts.vN.yaml     # versioned baseline (source of truth)

docs/fact/
  schemas/                     # artifact schemas
  discovery/repo-facts.vN.md   # discovered facts
  review/architect-feedback.md # review feedback
  baseline/facts.vN.yaml      # locked baseline
```

---

## Architecture

Two skill patterns:

- **Python ETL skill** — deterministic pipeline: `skills/<name>/run.py` + `SKILL.md`
- **Team Agent skill** — LLM analysis via Task tool workers + prompt templates in `prompts/`

Python runtime lives in `src/`; skill definitions in `skills/`.

See `docs/superpowers/ARCHITECTURE.md` for full details.
