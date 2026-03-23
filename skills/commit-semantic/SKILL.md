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

5-stage pipeline consuming commit-extract JSONL output: discover → ingest → aggregate → distill → export.

## Prerequisites

Requires `data/commit-extract/*.jsonl` files produced by `/commit-extract run`.

## Pipeline Stages

### 1. discover

Bottom-up domain discovery from semantic units, cached by `domains.json` fingerprint.

- Builds domains from unit-level semantic signals
- Reuses cached `domains.json` when fingerprint matches current inputs
- First run may bootstrap by running ingest first to create units
- Output: `data/commit-semantic/domains.json`

### 2. ingest

Expand sections into semantic units, collect invariants, and assign domains.

- Each section item becomes a unit with commit metadata, semantic fields, and domain assignment when `domains.json` exists
- Collects invariants separately into `invariants.jsonl`
- Mixed or no-path commits may require LLM classification
- Output: `data/commit-semantic/units/all.jsonl`, `data/commit-semantic/invariants.jsonl`

### 3. aggregate

Group units by domain and compute domain-level statistics.

- Primary key: `domain`, not theme
- Preserves `sub_themes` within each domain
- `uncategorized` remains an independent domain bucket
- Output: `data/commit-semantic/domains-aggregated.jsonl`

### 4. distill

Extract canonical demands from aggregated domains, score them, and rank them.

- Uses multi-dimensional scoring with invariant SHA association and caps
- Emits score breakdown fields for downstream review
- Produces ranked canonical demands per domain cluster
- Output: `data/commit-semantic/canonical-demands.jsonl`

### 5. export

Generate summary statistics for the domain-based pipeline.

- `summary.json` includes `top_domains`, `domain_count`, `uncategorized_ratio`, `file_paths_available`
- Also includes `op_distribution`, `invariant_count`, `date_range`, and `bugfix_ratio`
- Also reports runtime provenance via `orchestration_mode`, `discover_mode`, and `classify_mode`
- Output: `data/commit-semantic/summary.json`

## Output Schema

```
data/commit-semantic/
  domains.json                 # Discovered domains + fingerprint cache
  domains-aggregated.jsonl     # Aggregated domain statistics
  canonical-demands.jsonl      # Scored and ranked demands
  summary.json                 # Domain summary statistics
  units/all.jsonl              # Expanded semantic units
  invariants.jsonl             # Collected invariants
```

## Usage

```bash
/commit-semantic run                 # Full pipeline (5 stages)
/commit-semantic run --stage discover  # Run specific stage
/commit-semantic step                # Run next stage only
/commit-semantic resume              # Continue from breakpoint
/commit-semantic reset               # Clear state, keep artifacts
```
