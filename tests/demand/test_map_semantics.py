from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.map_semantics import load_semantic_foundation_assets, map_semantics

_PROHIBITED_FIELDS = {
    "summary",
    "explanation",
    "trace",
    "evidence_refs",
    "confidence",
    "metadata",
    "card_id",
    "schema_version",
}


def test_map_semantics_returns_all_arrays() -> None:
    mapped = map_semantics(
        issue_text="Add hash_to_context operator in FS DSL parser",
        semantic_assets={},
    )
    assert mapped == {
        "domains": [],
        "concepts": [],
        "rules": [],
        "invariants": [],
    }


def test_map_semantics_matches_expected_fields_deterministically() -> None:
    assets = {
        "domain_map": {
            "domains": [
                {"name": "FS DSL"},
                {"name": "Redis Discovery"},
            ]
        },
        "concept_map": {
            "concepts": [
                {"name": "hash_to_context operator"},
                {"name": "feature extraction"},
            ]
        },
        "rule_map": {
            "rules": [
                {"name": "parser compatibility", "statement": "legacy syntax must remain parseable"},
                {"name": "cache safety"},
            ]
        },
        "invariants": ["legacy syntax must remain parseable"],
    }

    issue_text = "Add hash_to_context operator to FS DSL while keeping parser compatibility"
    first = map_semantics(issue_text=issue_text, semantic_assets=assets)
    second = map_semantics(issue_text=issue_text, semantic_assets=assets)

    assert first == second
    assert first["domains"] == ["FS DSL"]
    assert first["concepts"] == ["hash_to_context operator"]
    assert first["rules"] == ["parser compatibility"]
    assert first["invariants"] == ["legacy syntax must remain parseable"]


def test_map_semantics_output_has_no_extra_families() -> None:
    mapped = map_semantics(
        issue_text="Fix parser compatibility bug",
        semantic_assets={
            "domain_map": {"domains": [{"name": "Parser"}]},
            "concept_map": {"concepts": [{"name": "syntax parser"}]},
            "rule_map": {"rules": [{"name": "parser compatibility"}]},
        },
    )
    assert set(mapped.keys()) == {"domains", "concepts", "rules", "invariants"}
    assert not any(field in mapped for field in _PROHIBITED_FIELDS)


def test_map_semantics_recovers_domain_from_non_literal_wording() -> None:
    mapped = map_semantics(
        issue_text="Integrate a service registry backend for lookup flow",
        semantic_assets={
            "domain_map": {"domains": [{"name": "Redis Discovery"}]},
        },
    )
    assert mapped["domains"] == ["Redis Discovery"]


def test_map_semantics_recovers_concept_from_non_literal_wording() -> None:
    mapped = map_semantics(
        issue_text="Need a context hashing op in the DSL pipeline",
        semantic_assets={
            "concept_map": {"concepts": [{"name": "hash_to_context operator"}]},
        },
    )
    assert mapped["concepts"] == ["hash_to_context operator"]


def test_map_semantics_recovers_rule_and_invariant_from_non_literal_wording() -> None:
    mapped = map_semantics(
        issue_text="Avoid breaking existing interfaces and ensure old syntax should continue to work",
        semantic_assets={
            "rule_map": {"rules": [{"name": "api stability"}]},
            "invariants": ["legacy syntax must remain parseable"],
        },
    )
    assert mapped["rules"] == ["api stability"]
    assert mapped["invariants"] == ["legacy syntax must remain parseable"]


def test_map_semantics_integrates_real_semantic_foundation_assets() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    assets = load_semantic_foundation_assets(repo_root)
    mapped = map_semantics(
        issue_text="Repository Structure Core Entities Validation Rules",
        semantic_assets=assets,
    )
    assert mapped["domains"] == ["Repository Structure"]
    assert mapped["concepts"] == ["Core Entities"]
    assert mapped["rules"] == ["Validation Rules"]
    assert isinstance(mapped["invariants"], list)
