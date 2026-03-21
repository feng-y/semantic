---
name: commit-semantic
version: "1.0.0"
description: "Analyze commit patterns for semantic domain mapping"
disable-model-invocation: false
deprecated: true
replacement: /commit-semantic (consolidated command)
triggers:
  - commit-semantic
  - analyze commit patterns
  - commit domains
---

> **DEPRECATED**: This skill is deprecated and will be removed in a future version.
> Use `/commit-semantic` (consolidated) instead, which provides the same functionality in a unified interface.

# Commit Semantic

Analyze commit patterns and map to semantic domains.

Requires: `/commit-extract` output in `.harness/outputs/commit-extract/`

## Pipeline

1. **analyze** — analyze patterns from extracted commits
2. **domain-map** — map patterns to semantic domains
3. **feed** — prepare output for demand pipeline

## Usage

```
/commit-semantic run              # Full pipeline
/commit-semantic status           # Check current state
/commit-semantic step             # Run next stage only
/commit-semantic resume           # Continue from breakpoint
/commit-semantic reset            # Clear state, keep artifacts
```

## Output

- `.harness/outputs/commit-semantic/patterns/`
- `.harness/outputs/commit-semantic/domains/`
- `.harness/state/commit-semantic/state.json`
