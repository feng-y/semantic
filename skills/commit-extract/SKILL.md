---
name: commit-extract
description: Aggregate raw commits by month with worker-driven commit_log regeneration
entrypoint: skills.commit-extract.run.run_commit_extract
disable-model-invocation: false
triggers:
  - commit-extract
  - extract commits
  - commit rules
---

# Commit Extract

Aggregate CC-generated commits by month, regenerating `commit_log` from diff via worker agents.

## Architecture

```
git commits → collect → batch → spawn workers → aggregate → data/commit-extract/YYYY-MM.yaml
```

**Main agent** reads git commits and orchestrates.
**Worker agents** regenerate `commit_log` from `diff_chunks` (never from `original_message`).

## Stages

1. **collect** — read git commits, group by month, batch for workers

## Batching Strategy

- Batch size: 30 commits per worker
- Each batch sent to a worker agent for parallel processing
- Results aggregated back into the monthly YAML output

## Worker Spawning

Workers are spawned via the `Task` tool with prompts from `prompts/generate_commit_log.md`:

```
Task tool (general-purpose):
  description: "Regenerate commit logs from diff batch"
  prompt: |
    [Injected from prompts/generate_commit_log.md]
    [Plus batch context: list of commits with diff_chunks]
```

## Critical Constraint

**COMMIT_LOG IS NEVER TAKEN FROM ORIGINAL MESSAGE OR ISSUE TEXT.**
- Worker agents receive `diff_chunks` and regenerate `commit_log` from code changes
- Original message stored as `original_message` (reference only)
- The canonical field is `commit_log` (regenerated)

## Output Schema

`data/commit-extract/YYYY-MM.yaml`:
```yaml
metadata:
  month: "2024-03"
  total_commits: 45
commits:
  - commit_id: "abc123"
    timestamp: "2024-03-15T10:30:00"
    author: "yan."
    original_message: "feat: add parser legacy support"
    files: ["src/parser.py"]
    diff_chunks: ["diff --git a/src/parser.py..."]
    commit_log: "在 parser 中补充 legacy 语法的边界检查处理"
```

## Usage

```
/commit-extract run              # Full pipeline
/commit-extract status           # Check current state
/commit-extract step             # Run next stage only
/commit-extract resume           # Continue from breakpoint
/commit-extract reset            # Clear state, keep artifacts
```
