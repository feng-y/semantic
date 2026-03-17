---
name: semantic-status
description: >
  Report current semantic state and recommend next action.
  Shows FACT layer discovery/review/baseline status and runner
  pipeline state. Always includes a --next recommendation.
entrypoint: src.state_inspector.inspect_with_runner
---

# Semantic Status

Report the current state of the semantic workflow and recommend next steps.

## What It Does

Analyzes the current workspace state and provides:
- Current workflow stage
- Available artifacts
- Runner pipeline stage and blocked status
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
- Runner pipeline stage (current_stage, completed stages)
- Blocked status and reason if blocked
- Next recommended command

## Implementation

Entrypoint: `src.state_inspector.inspect_with_runner`

This skill inspects the workspace and determines the current state of the semantic construction process, combining FACT layer state with runner pipeline state.
