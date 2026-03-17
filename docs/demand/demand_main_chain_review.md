# Demand Main Chain Review

## Review Target

Demand main-chain inventory/completion result for:

`normalize -> map -> match -> demand_card -> validate`

## Reviewed Files

- `docs/demand/demand_chain_inventory_and_completion.md`
- `docs/demand/demand_chain_inventory_and_completion.yaml`
- `src/demand/normalize_issue.py`
- `src/demand/map_semantics.py`
- `src/demand/match_development_type.py`
- `src/demand/build_demand_card.py`
- `src/demand/validate_demand_card.py`
- `src/demand/run.py`
- `src/demand/stage_registry.py`
- `tests/demand/test_normalize_issue.py`
- `tests/demand/test_map_semantics.py`
- `tests/demand/test_match_development_type.py`
- `tests/demand/test_build_demand_card.py`
- `tests/demand/test_validate_demand_card.py`
- `tests/demand/test_demand_card_e2e.py`
- `tests/demand/test_demand_pipeline.py`
- `tests/demand/test_demand_pipeline_e2e.py`
- `docs/semantic-foundation/semantic/domain-map.yaml`
- `docs/semantic-foundation/semantic/concept-map.yaml`
- `docs/semantic-foundation/semantic/rule-map.yaml`
- `docs/semantic-foundation/semantic/demand-model-map.yaml`

## Overall Judgment

pass_with_gaps

## normalize Assessment

PASS.

`normalize_issue.py` is real and bounded:
- trims whitespace
- rejects empty `issue_id` and `issue_text`
- preserves original issue text semantics
- does not generate explanatory prose fields

Tests explicitly validate these behaviors.

## map Assessment

PASS.

`map_semantics.py` materially derives all four semantic arrays:
- `domains`
- `concepts`
- `rules`
- `invariants`

Behavior is deterministic (scoring + stable ordering), bounded (controlled aliases), and grounded in semantic foundation map artifacts via loader and structured extraction.

No confidence/trace/evidence fields are emitted in mapping outputs.

## match Assessment

PARTIAL.

`match_development_type.py` is implemented and bounded:
- outputs exactly one allowed type
- keeps `open_questions` as array
- deterministic precedence

Grounding improved by:
- semantic mapping context text
- demand model map hints (when explicit model references exist)

Gap:
- in current repository data, `demand-model-map.yaml` is empty, so demand-model grounding path is wired but lightly exercised in real artifact conditions.

## demand_card Assessment

PASS.

Card assembly is complete and canonical:
- built from normalize/map/match outputs
- shape unchanged
- prohibited fields not reintroduced

Both direct and pipeline-level assembly paths are present and tested.

## validate Assessment

PASS.

Validation is strict and complete for V1:
- required fields/type checks
- enum constraints
- non-empty string item checks
- unknown-field rejection at root and nested levels

Malformed cards are rejected; valid cards pass.

## Semantic Foundation Integration Assessment

PARTIAL.

Status by artifact:
- Domain Map: real integration
- Concept Map: real integration
- Rule Map: real integration
- Demand Model Map: partial integration (wired for invariants/hints, but current foundation sample has empty `demand_models`)

Conclusion:
- grounding is real for domain/concept/rule flows
- demand-model integration is functionally present but currently low-signal due sparse source artifact content

## Chain-level Coherence Assessment

PASS.

Chain is coherently connected in `run_demand_pipeline`:
- normalize -> map -> match -> build -> validate
- failure stage surfaced explicitly
- invalid output cannot return success
- realistic e2e path exists and passes

## Test Quality Assessment

PASS.

Coverage includes:
- step-level behavior for normalize/map/match/build/validate
- strict validator checks including unknown fields
- chain-level unit/e2e tests
- semantic foundation integration test using actual foundation artifacts
- failure surfacing tests for normalize/map/build/validate stages

`pytest -q tests/demand` passes (`53 passed`).

## Strengths

- End-to-end demand chain is truly wired and executable.
- Contract strictness is strong (builder + validator + pipeline checks).
- Mapping is deterministic and bounded with explicit integration points.
- Tests are meaningful and go beyond existence checks.

## Gaps

- Demand-model-map contribution is currently low in practice because foundation artifact content is sparse/empty.
- Match stage still primarily text/rule-driven when no demand-model hint is available.

## Blocking Issues

- None.

## Recommended Fixes

- Priority: medium  
  Target: semantic foundation demand-model outputs (`docs/semantic-foundation/semantic/demand-model-map.yaml` generation path)  
  Issue: production artifact is often empty, reducing real grounding impact in match step  
  Recommendation: ensure semantic stage emits minimally useful demand model entries for downstream matching.

- Priority: low  
  Target: `tests/demand/test_match_development_type.py`  
  Issue: demand-model-map integration is tested only with synthetic in-memory fixtures  
  Recommendation: add a fixture-backed test variant that loads a non-empty demand-model-map sample from repository fixtures.

## Final Decision

- demand_main_chain_ready: true
