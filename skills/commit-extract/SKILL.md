---
name: commit-extract
description: Aggregate raw commits by month with LLM worker-driven semantic analysis
entrypoint: skills.commit-extract.run.run_commit_extract
disable-model-invocation: false
triggers:
  - commit-extract
  - extract commits
  - commit rules
---

# Commit Extract

LLM-powered commit analysis with adaptive batching. Replaces regex heuristic with `docs/generate_commit.md` prompt.

## Architecture

```
Main Agent (orchestrator = run.py, inherits SkillRunner)
  │
  ├─ git log --no-merges → SHA list
  ├─ git show --stat → weight estimation (parse insertions+deletions)
  ├─ adaptive batching (weight_budget=3000, max_commits_per_batch=15)
  │
  ├─► Worker Agent ×N (parallel, via Task tool)
  │     ├─ receives: SHA list + prefix instructions + docs/generate_commit.md
  │     ├─ per SHA: git show → analyze patch → JSON object → append
  │     └─ writes: data/commit-extract/tmp/{batch_id}.jsonl
  │
  └─► Merge (orchestrator, after all workers)
        ├─ reads: tmp/*.jsonl
        ├─ dedup by sha, skip invalid JSON lines
        ├─ groups by date → YYYY-MM
        ├─ appends to: data/commit-extract/YYYY-MM.jsonl
        └─ cleans up tmp/
```

## Output Schema

`data/commit-extract/YYYY-MM.jsonl`, each line:
```json
{
  "sha": "<SHA>",
  "author": "<author or empty string>",
  "date": "<ISO 8601>",
  "is_large_aggregate": true,
  "is_mixed": true,
  "sections": [
    {
      "name": "<generic functional block name>",
      "theme": "<short change theme>",
      "importance": "<primary|secondary>",
      "summary": "<optional>",
      "items": [{"op": "<feat|bugfix|...>", "summary": "<semantic summary>"}]
    }
  ],
  "rules_invariants": [
    {"kind": "<lifecycle|ownership|...>", "statement": "<rule>", "enforced_by_commit": true}
  ]
}
```

## Usage

```
/commit-extract run              # Full pipeline: collect → manifest → (workers) → merge
/commit-extract run --range HEAD~10..HEAD  # Limit range
/commit-extract run --merge      # Merge tmp files only (after workers complete)
/commit-extract status           # Check current state
/commit-extract resume           # Continue from breakpoint
/commit-extract reset            # Clear state, keep artifacts
```

## Resume / Incremental

- Reads existing YYYY-MM.jsonl to get processed SHA set
- Only new commits go through batching + workers
- tmp/ files from interrupted runs are merged on next run
