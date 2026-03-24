---
name: commit-semantic
description: Analyze commit patterns from structured JSONL (5-stage pipeline)
entrypoint: skills.commit-semantic.run.run_commit_semantic
triggers:
  - commit-semantic
  - analyze commit patterns
  - semantic commit analysis
---

# Commit Semantic

Commit-first, capability-first semantic extraction over `commit-extract` JSONL output.

## Prerequisites

Requires `data/commit-extract/*.jsonl` files produced by `/commit-extract run`.

## V1 Pipeline Stages

### 1. context

Build repo-local semantic priors from lightweight understanding docs.

- Reads repo-local understanding docs such as README / architecture / specs when present
- Synthesizes minimal repo hints: `local_capabilities`, `aliases`, `ownership_hints`, `seed_concepts`
- Writes `data/commit-semantic/repo-hints.json`
- Writes `data/commit-semantic/repo-context.json`

### 2. extract-signals

Extract commit-level semantic signals from commit-extract records using LLM analysis.

- Treats commit / section-item as the semantic observation unit
- Produces capability / concept / rule / domain-hint signals
- Persists raw V1 signal records for later synthesis

### 3. synthesize-capabilities

Aggregate commit-level signals into capability candidates.

- Preserves `observed_names`
- Assigns `canonical_name`
- Keeps `capability_id`, evidence refs, and status fields
- Writes `data/commit-semantic/capabilities-candidates.jsonl`

### 4. validate

Validate and normalize capability candidates into the stable V1 layer.

- Enforces minimum evidence expectations
- Rejects malformed or weak records from the stable layer
- Writes `data/commit-semantic/capabilities.jsonl`

### 5. export

Generate V1 summary artifacts.

- `summary.json` is a health and consumption overview, not the semantic ground truth
- Reports candidate count, stable count, mixed / low-signal ratios, evidence coverage, and naming drift
- Output: `data/commit-semantic/summary.json`

## V1 Output Schema

```
data/commit-semantic/
  repo-hints.json                 # Repo-local semantic priors
  repo-context.json               # Repo-local grounding view
  capabilities-candidates.jsonl   # Capability candidates from commit synthesis
  capabilities.jsonl              # Stable capability layer
  summary.json                    # V1 health / overview output
```

## Usage

```bash
/commit-semantic run                      # Full V1 pipeline
/commit-semantic run --stage context      # Run specific stage
/commit-semantic step                     # Run next stage only
/commit-semantic resume                   # Continue from breakpoint
/commit-semantic reset                    # Clear state, keep artifacts
```
