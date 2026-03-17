# Demand Chain Inventory And Completion

## Demand Main Chain Target

Target chain in this run:

`normalize -> map -> match -> demand_card -> validate`

Purpose:
- transform issue input + semantic foundation assets into a validated Demand Card V1
- keep Demand Card factual, minimal, execution-facing

## Current Implementation Inventory

### normalize

- Already existed before this run: yes (`src/demand/normalize_issue.py`)
- Previous status: implemented
- This run changes: no logic change
- Current status: implemented

### map

- Already existed before this run: yes (`src/demand/map_semantics.py`)
- Previous status: implemented (with controlled alias support)
- This run changes:
  - added explicit real-foundation integration verification via test using `load_semantic_foundation_assets(...)`
- Current status: implemented

### match

- Already existed before this run: yes (`src/demand/match_development_type.py`)
- Previous status: partial (mainly issue-text heuristics; semantic foundation linkage weak)
- This run changes:
  - added semantic-mapping context signal usage
  - added demand-model-map hint usage (when demand model is explicitly referenced)
  - kept deterministic single-type output and bounded logic
- Current status: implemented

### demand_card

- Already existed before this run: yes (`src/demand/build_demand_card.py`)
- Previous status: implemented
- This run changes:
  - wired `demand_model_map` through analyze path into `match_development_type(...)`
- Current status: implemented

### validate

- Already existed before this run: yes (`src/demand/validate_demand_card.py`)
- Previous status: implemented (strict)
- This run changes: no logic change
- Current status: implemented

## Semantic Foundation Integration Status

### Domain Map

- Artifact exists: yes (`docs/semantic-foundation/semantic/domain-map.yaml`)
- Usage: real (loaded and matched in `map_semantics`)
- Status: integrated

### Concept Map

- Artifact exists: yes (`docs/semantic-foundation/semantic/concept-map.yaml`)
- Usage: real (loaded and matched in `map_semantics`)
- Status: integrated

### Rule Map

- Artifact exists: yes (`docs/semantic-foundation/semantic/rule-map.yaml`)
- Usage: real (loaded and matched in `map_semantics`)
- Status: integrated

### Demand Model Map

- Artifact exists: yes (`docs/semantic-foundation/semantic/demand-model-map.yaml`)
- Usage:
  - map step: used for invariant extraction fallback (`constraints` / `invariants`)
  - match step: used for explicit development-type hints when issue references a demand model
- Status: integrated (bounded/conditional)

## Missing Or Weak Links

No blocking missing links remain for Demand main-chain wiring.

Non-blocking weak links:
- demand-model-map in current repo sample is often sparse/empty, so hinting path is wired but may be inactive until richer models exist
- alias catalog remains intentionally bounded and may need incremental expansion

## Changes Made In This Run

- Tightened match grounding:
  - `src/demand/match_development_type.py`
  - semantic mapping context incorporated into classification
  - demand-model-map hints incorporated (explicit reference-based)
- Completed wiring:
  - `src/demand/run.py` now passes `demand_model_map` to match
  - `src/demand/build_demand_card.py` analyze path now passes `demand_model_map` to match
- Documentation consistency:
  - `docs/demand/demand_analysis_steps.md` updated to reflect match grounding sources

## Tests Added/Updated

- `tests/demand/test_map_semantics.py`
  - added real semantic foundation integration test using repo artifacts
- `tests/demand/test_match_development_type.py`
  - added semantic-mapping-context-driven classification case
  - added demand-model-map-hint classification case
  - added shared assertions that output type is always one allowed enum and `open_questions` is always array
- `tests/demand/test_demand_pipeline.py`
  - added explicit build-failure surfacing test

Validation run:
- `pytest -q tests/demand` -> `53 passed`

## Remaining Gaps

- Alias and model-hint coverage is deterministic but intentionally narrow (needs incremental growth from real issue language)
- demand-model-map hinting depends on explicit model reference in issue text (bounded by design)

## Final Decision

- demand_main_chain_ready: true
