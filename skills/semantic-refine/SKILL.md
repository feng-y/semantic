---
name: semantic-refine
description: >
  Refine semantic artifacts using architect feedback. Patches
  repo-understanding and knowledge-confidence, generates change log,
  validates results, and applies versioning.
entrypoint: src.refine_executor.run_refine
steps:
  - run: prompts/refine/semantic-refine.patch.prompt
  - run: prompts/refine/semantic-change-log.prompt
  - run: prompts/validation/validate-artifact.prompt
  - apply: protocols/artifact-versioning.md
---

# Semantic Refine

Refine semantic artifacts based on architect feedback.

## Pipeline Steps

1. **Apply Patches** - Update artifacts with feedback
2. **Generate Change Log** - Document what changed and why
3. **Validation** - Validate refined artifacts
4. **Versioning** - Apply artifact versioning protocol

## Usage

```
/semantic-refine
```

Requires architect feedback to be present in `docs/fact/review/architect-feedback.md`.

## Output

Creates new versions of refined artifacts:
- `repo-understanding.vN+1.md`
- `knowledge-confidence.vN+1.md`
- `semantic-change-log.vN.md`

## Implementation

Entrypoint: `src.refine_executor.run_refine`

The refinement pipeline reads feedback, applies patches, and creates new artifact versions.
