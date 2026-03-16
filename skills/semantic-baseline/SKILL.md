---
name: semantic-baseline
description: >
  Synthesize accepted semantic baseline. Requires acceptance: true
  in architect feedback and all structural gates to pass. Produces
  purpose, domains, concepts, and pipelines baseline artifacts.
entrypoint: src.refine_executor.run_refine
steps:
  - if: architect acceptance detected
    run: prompts/refine/baseline-synthesis.prompt
---

# Semantic Baseline

Synthesize the accepted semantic baseline from refined artifacts.

## Prerequisites

- Architect feedback with `acceptance: true`
- All structural validation gates passed
- Refined artifacts present

## Pipeline Steps

1. **Check Acceptance** - Verify architect approval
2. **Synthesize Baseline** - Generate baseline artifacts

## Usage

```
/semantic-baseline
```

## Output

Creates immutable baseline artifacts in `docs/fact/baseline/`:
- `purpose.md` - Repository purpose and goals
- `domains.md` - Domain boundaries and responsibilities
- `concepts.md` - Core concepts and entities
- `pipelines.md` - Key workflows and processes

## Implementation

Entrypoint: `src.refine_executor.run_refine`

This skill only executes if architect acceptance is detected in the feedback.
