from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.match_development_type import match_development_type

_ALLOWED_TYPES = {"feature", "bugfix", "refactor", "migration", "optimize"}


def _assert_result_shape(matched: dict) -> None:
    assert matched["development_type"] in _ALLOWED_TYPES
    assert isinstance(matched["open_questions"], list)


def test_match_development_type_feature() -> None:
    matched = match_development_type(issue_text="Add hash_to_context operator in FS DSL")
    assert matched["development_type"] == "feature"
    assert matched["open_questions"] == []
    _assert_result_shape(matched)


def test_match_development_type_bugfix() -> None:
    matched = match_development_type(issue_text="Fix parser compatibility bug in DSL parser")
    assert matched["development_type"] == "bugfix"
    _assert_result_shape(matched)


def test_match_development_type_refactor() -> None:
    matched = match_development_type(issue_text="Refactor feature extraction internals")
    assert matched["development_type"] == "refactor"
    _assert_result_shape(matched)


def test_match_development_type_migration() -> None:
    matched = match_development_type(issue_text="Migrate redis discovery backend under abstraction")
    assert matched["development_type"] == "migration"
    _assert_result_shape(matched)


def test_match_development_type_optimize() -> None:
    matched = match_development_type(issue_text="Reduce latency and CPU overhead in extraction path")
    assert matched["development_type"] == "optimize"
    _assert_result_shape(matched)


def test_match_development_type_ambiguous_has_open_question() -> None:
    matched = match_development_type(issue_text="Fix and optimize parser performance")
    assert matched["development_type"] == "bugfix"
    assert len(matched["open_questions"]) == 1
    _assert_result_shape(matched)


def test_match_development_type_uses_semantic_mapping_context() -> None:
    matched = match_development_type(
        issue_text="Need to update module",
        semantic_mapping={
            "domains": [],
            "concepts": [],
            "rules": ["bug regression handling"],
            "invariants": [],
        },
    )
    assert matched["development_type"] == "bugfix"
    _assert_result_shape(matched)


def test_match_development_type_uses_demand_model_map_hint() -> None:
    matched = match_development_type(
        issue_text="Apply migration blueprint for discovery backend",
        semantic_mapping={},
        demand_model_map={
            "demand_models": [
                {
                    "name": "migration blueprint",
                    "development_type": "migration",
                }
            ]
        },
    )
    assert matched["development_type"] == "migration"
    _assert_result_shape(matched)
