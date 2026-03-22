---
name: commit-extract
description: Extract structured semantic knowledge from git history using Team Agent pattern
entrypoint: skills.commit-extract.run.run_commit_extract
disable-model-invocation: false
triggers:
  - commit-extract
  - extract commits
  - commit rules
---

# Commit Extract

Extract structured commit records from git history using a three-role Team Agent architecture.

## Architecture

```
Main Agent (orchestrator)
  │
  ├─ git log --no-merges → SHA list
  ├─ git show --stat → weight estimation per SHA
  ├─ adaptive batching (weight budget + count cap)
  │
  ├─► Worker Agent ×N (parallel Task agents)
  │     ├─ receives: SHA list + docs/generate_commit.md prompt
  │     ├─ per SHA: git show → analyze patch → JSON object
  │     └─ writes: data/commit-extract/tmp/{batch_id}.jsonl
  │
  └─► Merge Agent (after all workers complete)
        ├─ reads: tmp/*.jsonl
        ├─ dedup by sha
        ├─ groups by date → YYYY-MM
        ├─ appends to: data/commit-extract/YYYY-MM.jsonl
        └─ cleans up tmp/
```

## Stages

1. **collect** — SHA collection, stat estimation, adaptive batch manifest output

## Adaptive Batching

Weight-based (not fixed count):
- `weight_budget = 3000` lines, `max_commits_per_batch = 15`
- Each SHA weighted by `insertions + deletions` from `git show --stat`
- Binary files: fixed weight 500 each
- Empty commits: weight 0
- Flush batch when `accumulated_weight + next_weight > budget` or `count >= max`
- Single commit exceeding budget → solo batch

## Worker Agents

Spawned via Task tool after orchestrator prints the batch manifest.

Each worker:
1. Receives a batch of SHAs and the `docs/generate_commit.md` prompt
2. For each SHA: runs `git show --stat --summary {sha}` then `git show {sha}`
3. Analyzes the patch per prompt rules → produces one JSON object
4. Appends JSON line to `data/commit-extract/tmp/{batch_id}.jsonl` immediately

Workers process SHAs one at a time and append immediately — no patch content accumulates in context.

## Merge Agent

Runs after all workers complete:
1. Globs `data/commit-extract/tmp/*.jsonl`
2. Parses each line as JSON (skips invalid lines with warning)
3. Deduplicates by `sha` (last occurrence wins)
4. Groups by `date` field → YYYY-MM
5. For each month: reads existing `YYYY-MM.jsonl` SHA set, appends only new records
6. Deletes `tmp/` directory

## Output Schema

`data/commit-extract/YYYY-MM.jsonl` — one JSON object per line:

```json
{
  "sha": "<SHA>",
  "author": "<author or empty string>",
  "date": "<ISO 8601: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD>",
  "is_large_aggregate": true,
  "is_mixed": true,
  "sections": [
    {
      "name": "<functional block name>",
      "theme": "<short change theme>",
      "importance": "<primary|secondary>",
      "summary": "<optional section summary>",
      "items": [
        {
          "op": "<feat|bugfix|optimize|config|refactor|compat|safety|docs|test|cleanup|other>",
          "summary": "<semantic summary>"
        }
      ]
    }
  ],
  "rules_invariants": [
    {
      "kind": "<lifecycle|ownership|boundary|failure_isolation|compatibility|ordering|alignment|idempotency|resource_limit|other>",
      "statement": "<rule or invariant>",
      "enforced_by_commit": true
    }
  ]
}
```

Fields `original_message`, `files`, `diff_chunks` are NOT stored — recoverable from `sha` via git.

## Resume / Incremental

- Orchestrator scans existing `YYYY-MM.jsonl` files to collect already-processed SHAs
- Excludes those from the new batch manifest
- `tmp/` files from a previous interrupted run are picked up by the Merge Agent directly

## Usage

```
/commit-extract run              # Full pipeline
/commit-extract status           # Check current state
/commit-extract step             # Run next stage only
/commit-extract resume           # Continue from breakpoint
/commit-extract reset            # Clear state, keep artifacts
```

CLI flags (passed after `run`):
```
--repo <path>     Path to git repository (default: .)
--range <range>   Commit range (e.g. HEAD~50..HEAD)
```
