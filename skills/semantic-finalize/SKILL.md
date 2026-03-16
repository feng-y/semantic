---
name: semantic-finalize
version: "1.0.0"
description: "Generate final semantic asset maps from reviewed decisions. Fifth stage of semantic layer."
triggers:
  - semantic-finalize
  - finalize semantic
  - semantic step5
argument-hint: "[--decisions PATH] [--checks PATH] [--output-dir PATH]"
---

# Semantic Finalize — Final Asset Generation

> Generate final semantic asset maps from reviewed decisions.
> Applies keep/merge/drop/backlog outcomes and produces final semantic assets.
> Fifth and final stage of the semantic layer.

## When to Use

Use semantic-finalize when:
- You have completed semantic-review
- review-decisions.yaml exists and is valid
- evidence-checks.yaml exists (all verify_first items resolved)
- You are ready for the fifth and final semantic stage

## Implementation

```bash
python -m semantic.finalize_assets \
  --decisions docs/semantic-foundation/semantic/review-decisions.yaml \
  --checks docs/semantic-foundation/semantic/evidence-checks.yaml \
  --output-dir docs/semantic-foundation/semantic/
```

## Outputs

- domain-map.yaml / domain-map.md
- concept-map.yaml / concept-map.md
- rule-map.yaml / rule-map.md
- demand-model-map.yaml / demand-model-map.md
- change-log.yaml / change-log.md
