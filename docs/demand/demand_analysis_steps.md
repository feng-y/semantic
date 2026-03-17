# Demand Analysis Steps (PR2)

## Scope

PR2 implements bounded demand analysis steps that populate Demand Card V1 fields from:
- issue input (`issue_id`, `issue_text`)
- semantic foundation assets (domain/concept/rule/demand model maps)

This stage does not implement pipeline, teams orchestration, execution runtime, trace, or audit systems.

## Step 1: Normalize

Module: `src/demand/normalize_issue.py`

What it does:
- trims `issue_id` and `issue_text`
- rejects empty values
- preserves original issue meaning without rewriting into summary prose

Output:
- normalized `issue_id`
- normalized `issue_text`

## Step 2: Map

Module: `src/demand/map_semantics.py`

What it does:
- reads semantic assets (in-memory or from semantic foundation map files)
- maps issue text to:
  - `domains`
  - `concepts`
  - `rules`
  - `invariants`

How mapping works:
- deterministic token/phrase matching against semantic asset names/statements
- controlled synonym/alias matching for known wording variants (bounded dictionary)
- preserves stable order from ranked matches
- returns all four arrays every time

Notes:
- no confidence/evidence fields are emitted into Demand Card
- intermediate ranking is internal only
- alias support is explicit and reviewable (not unconstrained fuzzy search)

## Step 3: Match

Module: `src/demand/match_development_type.py`

What it does:
- chooses exactly one `development_type` from:
  - `feature`
  - `bugfix`
  - `refactor`
  - `migration`
  - `optimize`
- derives `open_questions` when intent is ambiguous or under-specified

Rule style:
- deterministic classification from issue text, semantic mapping context, and demand-model hints (when explicitly referenced)
- no extra development types are introduced

## Step 4: Assemble Demand Card

Module: `src/demand/build_demand_card.py`

Assembly flow:
1. normalize issue
2. map semantics
3. match development type
4. assemble Demand Card V1 shape via existing builder
5. validate final card via existing validator

Result:
- a valid, minimal, execution-facing Demand Card V1 object

## Why the Card Stays Factual and Minimal

The final card still contains only:
- request source (`issue_id`, `issue_text`)
- selected semantic facts (`domains`, `concepts`, `rules`, `invariants`)
- one execution type (`development_type`)
- unresolved questions (`open_questions`)

It intentionally excludes summary/explanation/trace/evidence/confidence/metadata fields.
