---
name: commit-extract
version: "1.0.0"
description: "Extract commit log facts: rules, invariants, patterns from git history"
disable-model-invocation: false
triggers:
  - commit-extract
  - extract commits
  - commit rules
---

# Commit Extract

Extract structured knowledge from git commit history.

## Pipeline

1. **collect** — gather commits from git history
2. **extract** — extract rules and invariants from each commit
3. **pattern** — identify recurring patterns

## Usage

```
/commit-extract run              # Full pipeline
/commit-extract status           # Check current state
/commit-extract step             # Run next stage only
/commit-extract resume           # Continue from breakpoint
/commit-extract reset            # Clear state, keep artifacts
```

## Output

- `.harness/outputs/commit-extract/commits/`
- `.harness/outputs/commit-extract/rules/`
- `.harness/outputs/commit-extract/invariants/`
- `.harness/state/commit-extract/run-state.json`
