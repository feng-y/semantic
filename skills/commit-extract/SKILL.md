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

## Natural-language invocation

When this skill is invoked from Claude Code, the interaction should feel like a guided workflow, not a raw CLI wrapper.

### Step 0 — bootstrap / doc analysis
Before commit batching, explicitly treat repo understanding as part of the flow:
- read lightweight repo docs and planning/codebase inputs
- build or reuse `repo-context.json`
- determine runtime mode: `full` / `degraded` / `bypass`
- only then proceed to collect, batch, and worker execution

The user should be able to understand that bootstrap/context analysis happens first; do not hide this behind worker spawning language.

### Step 1 — resolve scope from natural language
Prefer interpreting user intent directly instead of asking for raw subcommands or CLI flags.

Support these natural entry patterns first:

### A. Recent N commits
- "提取最近 10 个 commit" / "extract the last 10 commits" → `run --range HEAD~10..HEAD --yes`
- "提取最近 30 个 commit" → `run --range HEAD~30..HEAD --yes`
- "提取最近 90 个 commit" → `run --range HEAD~90..HEAD --yes`

### B. Recent time window
- "提取最近 7 天" → `run --range --since=7.days --yes` (or equivalent computed git date range)
- "提取最近 30 天" → `run --range --since=30.days --yes`
- "提取最近 90 天" → `run --range --since=90.days --yes`

### C. Calendar periods
- "提取本周的 commit" → resolve to current-week date range, then run
- "提取上周的 commit" → resolve to previous-week date range, then run
- "提取本月的 commit" → resolve to current-month date range, then run
- "提取上个月的 commit" → resolve to previous-month date range, then run
- "提取这个季度的 commit" → resolve to current-quarter date range, then run

### D. Explicit date range
- "提取 2026-03-01 到 2026-03-15 的 commit" → date-range mode
- "提取 20260101 - 20260201 的 commit" → parse compact numeric date range, then run
- "提取 3 月上半月的 commit" → resolve to concrete date range before running
- "提取 2026-03-01 之后的 commit" → lower-bound date mode
- "提取 2026-03-15 之前的 commit" → upper-bound date mode

### Other common intents
- "跳过 bootstrap 跑 extract" → keep the chosen scope, add `--skip-bootstrap`
- "看状态" → `status`
- "继续" → `resume`
- "只 merge" → `run --merge`
- "重置" → `reset`

Interaction rule:
- If the user provides a scope in natural language, do **not** ask for raw CLI flags.
- If the user gives no scope, ask a natural-language follow-up offering these choices:
  - 最近 10 个 commit
  - 最近 30 个 commit
  - 最近 90 个 commit
  - 最近 7 天
  - 最近 30 天
  - 自定义时间区间

Recommended default when the user wants extraction but gives no scope:
- 最近 30 个 commit

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
/commit-extract run --skip-bootstrap       # Bypass shared bootstrap context for this run
/commit-extract run --merge      # Merge tmp files only (after workers complete)
/commit-extract status           # Check current state
/commit-extract resume           # Continue from breakpoint
/commit-extract reset            # Clear state, keep artifacts
```

## Reliability layer

`commit-extract` now treats shared bootstrap context as an operational layer with explicit runtime modes:

- `full` — fresh valid shared context, inject full `shared_hints`
- `degraded` — fresh but reduced context; inject reduced `shared_hints` only when non-empty degraded hints remain
- `bypass` — missing / invalid / stale / explicitly skipped context, inject no shared hints

Operational nuance:
- `degraded` with `reduced-shared-hints` → inject a reduced `shared_hints` block
- `degraded` with `empty-shared-hints` → inject no shared hints (runtime behaves like no prior, but remains `degraded` rather than `bypass`)

Operational summary fields live in `data/commit-extract/repo-context.json` under `summary`:
- `bootstrap_status`
- `hint_count`
- `source_counts`
- `used_cached_context`
- `degraded_reasons`
- `bypass_reason`
- `fingerprint`

`--skip-bootstrap` is a narrow debug bypass: it forces `bootstrap_status=bypass`, skips hint injection, but still lets collect proceed and write the manifest.

## Resume / Incremental

- Reads existing YYYY-MM.jsonl to get processed SHA set
- Only new commits go through batching + workers
- tmp/ files from interrupted runs are merged on next run
