---
name: semantic-review
version: "1.0.0"
description: "Generate review decisions and evidence checks from recommendations. Fourth stage of semantic layer."
triggers:
  - semantic-review
  - review recommendations
  - semantic step4
argument-hint: "[--recommendations PATH] [--output-decisions PATH] [--output-checks PATH]"
---

# Semantic Review — Review Decision Generation

> Generate structured review decisions and evidence checks from semantic recommendations.
> Converts recommendations into actionable review decisions.
> Fourth stage of the semantic layer.

## Decision Tree

```
START
  ├─ Has recommendations.yaml?
  │   ├─ YES → Load recommendations (primary input)
  │   └─ NO  → BLOCK (required input missing)
  │
  ├─ Validate recommendation structure
  │   ├─ Valid → Continue
  │   └─ Invalid → BLOCK (malformed recommendations)
  │
  ├─ Generate review decisions for all recommendations
  ├─ Generate evidence checks for verify_first items
  │
  └─ Write review-decisions.yaml + evidence-checks.yaml + review-note.md → SUCCESS
```

## Execution Steps

### Step 1: Validate Inputs

**Check for:**
- [ ] `docs/semantic-foundation/semantic/recommendations.yaml` exists (REQUIRED)
- [ ] recommendations.yaml has valid structure (4 recommendation groups)

**Blocking conditions:**
- BLOCK if recommendations.yaml missing
- BLOCK if recommendations.yaml malformed
- BLOCK if recommendation groups missing

### Step 2: Generate Review Decisions

**Process:**
- Read all recommendations from recommendations.yaml
- Convert each recommendation into a review decision
- Determine final_action based on recommendation.action
- Preserve recommendation_id and evidence linkage
- Enforce allowed final actions

**Allowed final actions:**
- `keep` - Include in final semantic assets
- `merge` - Merge with another item (requires merge_target)
- `drop` - Exclude from final assets
- `backlog` - Defer to future iteration
- `verify_first` - Requires evidence verification before finalization

## When to Use

**Use semantic-review when:**
- You have completed semantic-recommend
- recommendations.yaml exists and is valid
- You need to generate review decisions
- You are ready for the fourth semantic stage

## Implementation

This skill is thin and delegates to Python implementation:

```bash
python -m semantic.apply_review \
  --recommendations docs/semantic-foundation/semantic/recommendations.yaml \
  --output-decisions docs/semantic-foundation/semantic/review-decisions.yaml \
  --output-checks docs/semantic-foundation/semantic/evidence-checks.yaml \
  --render-md docs/semantic-foundation/semantic/review-note.md
```
