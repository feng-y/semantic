---
name: commit-semantic
description: Analyze commit patterns from JSONL extract output
entrypoint: skills.commit-semantic.run.run_commit_semantic
triggers:
  - commit-semantic
  - analyze commit patterns
  - semantic commit analysis
---

# Commit Semantic

Pure Python ETL pipeline. Consumes structured JSONL from commit-extract and
produces canonical demand patterns with summary statistics.

## Prerequisites

Requires `data/commit-extract/YYYY-MM.jsonl` files produced by `/commit-extract run`.

Each line is a JSON object with fields: `sha`, `author`, `date`,
`is_large_aggregate`, `is_mixed`, `sections[]`, `rules_invariants[]`.

## Pipeline Stages

### 1. ingest

Read all `data/commit-extract/YYYY-MM.jsonl` files. Expand each section's
items into individual semantic units.

- Each item becomes one unit inheriting the section's `name`/`theme`/`importance`
  and the commit's `is_large_aggregate`/`is_mixed`
- `rules_invariants` collected separately
- Invalid JSON lines skipped with a warning (fault-tolerant)
- Output: `data/commit-semantic/units/all.jsonl`
- Output: `data/commit-semantic/invariants.jsonl`

Unit schema:
```json
{"sha": "...", "date": "...", "author": "...", "section_name": "...",
 "theme": "...", "importance": "primary|secondary", "op": "feat|bugfix|...",
 "summary": "...", "is_large_aggregate": false, "is_mixed": false}
```

### 2. aggregate

Group units by `theme` (cross-commit semantic theme). Same theme from
different `section_name` values is merged.

- `count`: total units for this theme
- `distinct_commits`: number of unique SHAs
- `op_distribution`: `{"feat": N, "bugfix": N, ...}`
- `importance_ratio`: `{"primary": N, "secondary": N}`
- `representative_summaries`: up to 3 example summaries
- High-frequency pattern: theme appears in >= 3 distinct commits
- Output: `data/commit-semantic/patterns.jsonl`

Pattern schema:
```json
{"theme": "...", "count": N, "distinct_commits": N,
 "op_distribution": {"feat": N, ...},
 "importance_ratio": {"primary": N, "secondary": N},
 "representative_summaries": ["...", "..."]}
```

### 3. distill

Score patterns and produce ranked canonical demands.

- Score formula: `score = distinct_commits × importance_weight`
  where `importance_weight = (primary×2 + secondary×1) / total`
- Tiebreak: `distinct_commits` desc, then `theme` alphabetical
- Invariants appearing in >= 3 commits add a small score bonus
- Output: `data/commit-semantic/canonical-demands.jsonl`

### 4. export

Compute summary statistics across all units and demands.

- `total_units`, `total_patterns`
- `op_distribution`: aggregated across all units
- `top_patterns`: top 10 by score
- `bugfix_ratio`: bugfix ops / total ops
- `invariant_count`: total invariants collected
- `date_range`: `{"from": "...", "to": "..."}`
- Output: `data/commit-semantic/summary.json`

## Output Layout

```
data/commit-semantic/
  units/all.jsonl          # Expanded semantic units
  invariants.jsonl         # Collected rules/invariants
  patterns.jsonl           # Aggregated theme patterns
  canonical-demands.jsonl  # Ranked demands
  summary.json             # Summary statistics
```

## Usage

```bash
/commit-semantic run              # Full pipeline (all 4 stages)
/commit-semantic run --stage ingest     # Single stage
/commit-semantic step             # Run next stage only
/commit-semantic resume           # Continue from last completed stage
/commit-semantic status           # Show pipeline state
/commit-semantic reset            # Clear state, keep artifacts
```
