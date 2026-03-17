# Demand Card V1

## Goal

Demand Card is the execution-facing semantic fact card.

It is not:
- a trace artifact
- an audit artifact
- a summary/explanation document
- a work-context snapshot

It is:
- a structured semantic fact object
- the output of demand analysis
- the input to execution

## Canonical Structure

```yaml
demand_card:
  request_source:
    issue_id:
    issue_text:

  semantic_mapping:
    domains: []
    concepts: []
    rules: []
    invariants: []

  development_type:

  uncertainties:
    open_questions: []
```

## Field Semantics

### request_source.issue_id

The upstream issue/request identifier.
This is the primary anchor of the card.

### request_source.issue_text

The original issue text.
This preserves user intent and avoids over-rewriting.

### semantic_mapping.domains

Problem domains relevant to this issue.

### semantic_mapping.concepts

Core semantic objects involved in the issue.

### semantic_mapping.rules

Rules touched by this issue.

### semantic_mapping.invariants

Hard invariants that must not be broken.

### development_type

Execution-oriented development category.

Allowed values:
- `feature`
- `bugfix`
- `refactor`
- `migration`
- `optimize`

Usage examples:
- `feature`: add a new API endpoint for bulk export.
- `bugfix`: fix incorrect rounding in invoice total calculation.
- `refactor`: restructure a module without changing external behavior.
- `migration`: move persisted config from v1 shape to v2 shape.
- `optimize`: reduce latency of a hot query path.

### uncertainties.open_questions

Questions that remain unresolved after demand analysis.

## Design Principles

1. Keep the card factual.
2. Do not add prose summary fields.
3. Do not add trace/evidence/confidence into the card.
4. Keep the card short and execution-friendly.
5. Arrays must always exist, even if empty.

## Non-Goals

Demand Card V1 does not include:
- traceability logs
- evidence refs
- analysis summary
- normalized request
- metadata
- confidence scores
- card_id
- schema_version

## Validator Fail Conditions

Validation must fail when:
- `demand_card` is missing or not an object.
- `request_source.issue_id` is missing or blank.
- `request_source.issue_text` is missing or blank.
- `semantic_mapping.domains` is not an array.
- `semantic_mapping.concepts` is not an array.
- `semantic_mapping.rules` is not an array.
- `semantic_mapping.invariants` is not an array.
- any array item is not a non-empty string.
- `development_type` is missing, blank, or outside the 5 allowed values.
- `uncertainties.open_questions` is not an array.
