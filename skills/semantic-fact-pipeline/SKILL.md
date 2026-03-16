---
name: semantic-fact-pipeline
version: "1.0.0"
description: "Run the FACT pipeline workflow (discover → review → refine → baseline)"
disable-model-invocation: true
triggers:
  - semantic-fact-pipeline
  - fact pipeline
  - run fact
---

# Semantic FACT Pipeline

> Composite workflow skill that runs the FACT pipeline sequence.
> This is the old pipeline that remains FACT-focused.

## What This Skill Does

Runs the FACT pipeline in sequence:
1. **semantic-discover** - Discovery and fact extraction
2. **semantic-review** - Human review checkpoint
3. **semantic-refine** - Refinement based on review
4. **semantic-baseline** - Create baseline artifacts

## When to Use

Use this skill when:
- Starting fresh FACT discovery
- Need to update FACT baseline
- Working on FACT layer only (not semantic layer)

## Invocation

```bash
/semantic-fact-pipeline
```

## Pipeline Flow

```
START
  ↓
semantic-discover
  ↓
[STOP for human review]
  ↓
semantic-review (manual)
  ↓
semantic-refine
  ↓
semantic-baseline
  ↓
END
```

## Success Criteria

- [ ] Discovery artifacts created in docs/fact/discovery/
- [ ] Review completed (manual step)
- [ ] Refinement applied
- [ ] Baseline created in docs/fact/baseline/

## Notes

- This pipeline stops for human review
- Does NOT automatically proceed to semantic layer
- Use `semantic-pipeline` for semantic layer workflow
