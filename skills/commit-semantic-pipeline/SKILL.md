---
name: commit-semantic-pipeline
description: "Run full commit-semantic pipeline: collect → generate → export"
triggers:
  - commit-semantic-pipeline
  - run commit semantic pipeline
  - commit semantic all
---

# commit-semantic-pipeline

Composite skill that runs all three commit-semantic stages in sequence.

## When to Use

Use when you want to go from git history to a deduplicated, pattern-aggregated case library in one call.

## Invocation

```
/commit-semantic-pipeline 最近 50 个 commit
/commit-semantic-pipeline HEAD~100..HEAD，排除 config 目录
/commit-semantic-pipeline 最近一个月，增量模式
```

## Pipeline Flow

```
commit history
     ↓
commit-semantic-collect    →  data/semantic_case_inputs/
     ↓
commit-semantic-generate   →  data/semantic_cases/
     ↓
commit-semantic-export     →  data/exports/
                               ├── cases.jsonl
                               ├── duplicates.jsonl
                               ├── patterns.jsonl
                               └── summary.json
```

Supports resume: if a stage was already completed, it is skipped automatically via checkpoint file (`data/.pipeline-checkpoint.json`).

## Parameters (natural language → resolved by Claude)

| Description | Resolved to |
|-------------|-------------|
| 最近 N 个 commit | `commit_range="HEAD~N..HEAD"` |
| 最近一周 / 一个月 | `since="1 week ago"` / `since="1 month ago"` |
| 增量模式 | `incremental=True` |
| 排除 X 目录 | `exclude_paths=["X/"]` |

## Python API

```python
from src.commit_semantic.pipeline import run_pipeline

result = run_pipeline(
    repo_path=".",
    commit_range="HEAD~50..HEAD",
    executor=my_llm_executor,
    incremental=False,
    exclude_paths=["config/", "docs/"],
    resume=True,          # skip already-completed stages
    stages="all",         # or "collect,generate"
)
```

## Non-goals

Does not modify semantic fields after generation. Does not re-run completed stages unless checkpoint is deleted.
