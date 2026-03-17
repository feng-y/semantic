---
name: demand-pipeline
version: "1.0.0"
description: "Run demand stage (normalize -> map -> match -> build -> validate)"
disable-model-invocation: true
triggers:
  - demand-pipeline
  - run demand pipeline
  - build demand card from issue
---

# Demand Pipeline

Thin orchestration skill for running the repository demand stage implementation.

## When to Use

Use this skill when you need one-shot demand stage execution from issue input.

## Required Inputs

- `issue_id`
- `issue_text`

Optional:
- repository root for semantic foundation loading
- explicit semantic assets object

## Output

- structured pipeline result with stage statuses
- validated Demand Card V1 on success

## Implementation Entry

Use repository implementation entrypoints:
- `src/demand/run.py::run_demand_pipeline`
- `src/demand/run.py::run_and_write_demand_pipeline`

Example CLI:

```bash
python -m src.demand.run --issue-id ISSUE-100 --issue-text "Add hash_to_context operator" --repo-root .
```
