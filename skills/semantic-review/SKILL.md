---
name: semantic-review
description: >
  Present discovery artifacts for architect review. Reads latest
  repo-understanding, knowledge-confidence, and review-summary
  for human inspection.
entrypoint: src.state_inspector.inspect
---

# Semantic Review

Present discovery artifacts for architect review and feedback.

## What It Does

Reads and displays the latest versions of:
- Repository Understanding
- Knowledge Confidence Assessment
- Review Summary

## Usage

```
/semantic-review
```

## Output

Displays the current state of semantic artifacts for human review. The architect can then provide feedback for refinement.

## Implementation

Entrypoint: `src.state_inspector.inspect`

This skill reads the latest versioned artifacts from `docs/fact/discovery/` and presents them in a readable format.
