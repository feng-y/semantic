# Demand Pipeline (PR3)

## Purpose

Demand pipeline provides one coherent demand stage entry that orchestrates:

1. normalize issue input
2. map semantics
3. match development type
4. build Demand Card
5. validate Demand Card

This stage is orchestration-only and reuses existing demand modules.

## Inputs

Required:
- `issue_id`
- `issue_text`

Optional:
- semantic assets object (domain/concept/rule/demand model maps)
- repository root for loading semantic foundation assets

## Step Order

Execution order is fixed:

1. `normalize_issue`
2. `map_semantics`
3. `match_development_type`
4. `build_demand_card`
5. `validate_demand_card`

## Output Contract

The pipeline returns a structured result with:
- `ok` (success/failure)
- `issue_id`
- `demand_card` (final card on success)
- `validation_errors`
- `failed_stage`
- `error`
- `stage_order`
- `stages` (per-stage status)
- `intermediate`:
  - `normalized_issue`
  - `semantic_mapping`
  - `development_type_match`

## Failure Surfacing

- normalize failure: pipeline stops immediately and returns `failed_stage=normalize_issue`
- build failure: pipeline stops immediately and returns `failed_stage=build_demand_card`
- validator errors: pipeline returns `failed_stage=validate_demand_card` with `validation_errors`

Pipeline never silently repairs malformed cards with invented fields.

## Why Output Stays Minimal

Pipeline output card remains Demand Card V1 only:
- request source
- semantic mapping arrays
- development type
- open questions

No summary/explanation/trace/evidence/confidence/metadata fields are added.

## Out of Scope

- teams orchestration
- initializer systems
- execution runtime
- trace/audit artifact systems
- broader state-machine orchestration frameworks
