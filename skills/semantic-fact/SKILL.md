---
name: semantic-fact
version: "1.0.0"
description: "Unified semantic fact pipeline: discover → review → refine → baseline"
disable-model-invocation: false
triggers:
  - semantic-fact
  - fact pipeline
  - semantic baseline
---

# Semantic Fact

Unified fact discovery and baseline management.

## Prerequisites

Requires accepted fact baseline in `docs/fact/baseline/`.

## Pipeline

1. **discover** — sample repo and extract facts
2. **review** — architect reviews extracted facts
3. **refine** — patch based on feedback
4. **baseline** — accept and lock baseline

## Usage

```
/semantic-fact run              # Full pipeline
/semantic-fact status           # Check current state
/semantic-fact step             # Run next stage only
/semantic-fact resume           # Continue from breakpoint
/semantic-fact reset            # Clear state, keep artifacts
```

## Output

- `.harness/outputs/semantic-fact/discovery/`
- `.harness/outputs/semantic-fact/review/`
- `.harness/outputs/semantic-fact/refine/`
- `.harness/outputs/semantic-fact/baseline/`
- `.harness/state/semantic-fact/state.json`
