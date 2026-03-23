---
name: commit-semantic
description: Analyze commit patterns from structured JSONL (4-stage pipeline)
entrypoint: skills.commit-semantic.run.run_commit_semantic
triggers:
  - commit-semantic
  - analyze commit patterns
  - semantic commit analysis
---

# Commit Semantic

4-stage pipeline consuming commit-extract JSONL output: ingest → aggregate → distill → export.

## Prerequisites

Requires `data/commit-extract/*.jsonl` files produced by `/commit-extract run`.

## Pipeline Stages

### 1. ingest

Expand sections into semantic units + collect rules_invariants.

- Each section's items become individual units with `sha`, `date`, `author`, `theme`, `importance`, `op`, `summary`
- Commit-level `is_large_aggregate` and `is_mixed` flags carried to each unit
- `rules_invariants` collected separately
- Skips invalid JSON lines with warning
- Output: `data/commit-semantic/units/all.jsonl`, `data/commit-semantic/invariants.jsonl`

### 2. aggregate

Group units by theme, compute statistics.

- Primary key: `theme` (cross-commit semantic theme)
- Same theme from different `section_name` values merged
- Statistics: `op` distribution, `importance` ratio (primary/secondary)
- Threshold: theme must appear in >= 3 distinct commits
- Output: `data/commit-semantic/patterns.jsonl`

### 3. distill

Extract canonical demands from patterns, scored and ranked.

- Score: `distinct_commits × importance_weight` where `primary=2, secondary=1`
- Tie-break: `distinct_commits` desc → `theme` alpha
- Invariants appearing in >= 3 commits get extra weight
- Output: `data/commit-semantic/canonical-demands.jsonl`

### 4. export

Generate summary statistics.

- Total units, patterns, op distribution, bugfix ratio
- Top patterns by score
- Date range
- Output: `data/commit-semantic/summary.json`

## Output Schema

```
data/commit-semantic/
  units/all.jsonl              # Expanded semantic units
  invariants.jsonl             # Rules and invariants
  patterns.jsonl               # Aggregated patterns (threshold >= 3)
  canonical-demands.jsonl      # Scored and ranked demands
  summary.json                 # Summary statistics
```

## Usage

```bash
/commit-semantic run              # Full pipeline (4 stages)
/commit-semantic run --stage ingest  # Run specific stage
/commit-semantic step             # Run next stage only
/commit-semantic resume           # Continue from breakpoint
/commit-semantic reset            # Clear state, keep artifacts
```
