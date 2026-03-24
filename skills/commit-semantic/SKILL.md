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

For this subproject, `commit-semantic` remains the temporary producer of the repo-local semantic context fallback artifacts. The stable layered contract centers on `repo-context.json`; `repo-hints.json` remains a compatibility/input-layer artifact used to derive that grounding view, not a peer semantic asset. When `data/commit-extract/repo-context.json` is present, downstream semantic stages prefer that shared extract context and consume only its `semantic_context` layer. The local `data/commit-semantic/repo-context.json` remains a compatibility fallback when the shared extract artifact is absent.

## Prerequisites

Requires `data/commit-extract/*.jsonl` files produced by `/commit-extract run`.

## V1 Pipeline Stages

### 1. context

Build the layered repo-local semantic context from lightweight understanding docs.

- Reads repo-local understanding docs such as README / architecture / specs when present
- Synthesizes minimal repo hints: `local_capabilities`, `aliases`, `ownership_hints`, `seed_concepts`
- Writes `data/commit-semantic/repo-hints.json` as the compatibility/input-layer prior artifact
- Writes `data/commit-semantic/repo-context.json` as the local layered grounding fallback artifact
- `repo-context.json` is layered as `shared_hints` (reusable context), `semantic_context` (semantic-local interpreted context), and `summary` (provisional schema anchor that will gain stronger semantics later)
- Downstream V1 stages consume only `semantic_context`; when `data/commit-extract/repo-context.json` exists it wins, otherwise the local semantic artifact is used as a compatibility fallback
- Keeps producer ownership in `commit-semantic` for now, even though the long-term model may separate shared context production from capability extraction

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
  repo-hints.json                 # Compatibility/input-layer priors used to derive grounding
  repo-context.json               # Primary repo-local grounding contract for V1
  capabilities-candidates.jsonl   # Capability candidates from commit synthesis
  capabilities.jsonl              # Stable capability layer
  summary.json                    # V1 health / overview output
```

`repo-hints.json` and `repo-context.json` are intentionally not the same artifact. The former is a synthesized prior layer and compatibility-only in this subproject; the latter is the canonical layered grounding contract that downstream stages should treat as the stable semantic context surface in V1.

Later subprojects may move producer ownership upstream to `commit-extract`, but that migration has not happened yet here.

## Usage

```bash
/commit-semantic run                      # Full V1 pipeline
/commit-semantic run --stage context      # Run specific stage
/commit-semantic step                     # Run next stage only
/commit-semantic resume                   # Continue from breakpoint
/commit-semantic reset                    # Clear state, keep artifacts
```
