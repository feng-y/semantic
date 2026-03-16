---
name: semantic-status
description: >
  Report current semantic state and recommend next action
  (discover, refine, or done).
entrypoint: src.state_inspector.inspect
---

# Semantic Status

Report the current state of the semantic workflow and recommend next steps.

## What It Does

Analyzes the current workspace state and provides:
- Current workflow stage
- Available artifacts
- Recommended next action

## Usage

```
/semantic-status
```

## Output

Displays:
- Workspace initialization status
- Discovery artifacts status
- Review/feedback status
- Baseline status
- Recommended next command

## Implementation

Entrypoint: `src.state_inspector.inspect`

This skill inspects the workspace and determines the current state of the semantic construction process.
