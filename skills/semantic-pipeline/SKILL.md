---
name: semantic-pipeline
version: "1.0.0"
description: "Run the semantic workflow (signals → candidates → recommend → review → finalize)"
disable-model-invocation: true
triggers:
  - semantic-pipeline
  - semantic workflow
  - run semantic
---

# Semantic Pipeline

> Composite workflow skill that runs the semantic layer sequence.
> Transforms FACT inputs into final semantic assets.

## What This Skill Does

Runs the semantic workflow in sequence:
1. **semantic-signals** - Extract signals from FACT
2. **semantic-candidates** - Generate candidates from signals
3. **semantic-recommend** - Score and recommend candidates
4. **semantic-review** - Generate review decisions
5. **semantic-finalize** - Produce final semantic assets

## When to Use

Use this skill when:
- FACT baseline exists
- Ready to generate semantic assets
- Want to run full semantic pipeline

## Invocation

```bash
/semantic-pipeline
```

## Pipeline Flow

```
START
  ↓
semantic-signals
  ↓
semantic-candidates
  ↓
semantic-recommend
  ↓
semantic-review
  ↓
[STOP if verify_first items unresolved]
  ↓
semantic-finalize
  ↓
END
```

## Success Criteria

- [ ] signals.yaml created
- [ ] candidates.yaml created
- [ ] recommendations.yaml created
- [ ] review-decisions.yaml created
- [ ] evidence-checks.yaml created
- [ ] Final asset maps created (domain-map.yaml, etc.)
- [ ] change-log.yaml created

## Gating Conditions

**The pipeline will stop if:**
- Any stage fails validation
- Evidence checks have unresolved verify_first items

**Manual intervention required when:**
- Review decisions need human approval
- Evidence verification is incomplete

## Notes

- Requires FACT baseline as input
- Does NOT include demand layer (separate concern)
- Use `semantic-fact-pipeline` for FACT layer workflow
