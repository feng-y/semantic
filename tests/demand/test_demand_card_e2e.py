from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.build_demand_card import analyze_and_build_demand_card
from src.demand.validate_demand_card import validate_demand_card

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


def test_demand_card_e2e_builds_valid_card() -> None:
    semantic_assets = {
        "domain_map": {"domains": [{"name": "FS DSL"}, {"name": "Discovery Backend"}]},
        "concept_map": {"concepts": [{"name": "hash_to_context operator"}, {"name": "service discovery"}]},
        "rule_map": {"rules": [{"name": "parser compatibility"}, {"name": "api stability"}]},
        "invariants": ["legacy syntax must remain parseable"],
    }

    card = analyze_and_build_demand_card(
        issue_id="ISSUE-1200",
        issue_text="Add hash_to_context operator in FS DSL parser",
        semantic_assets=semantic_assets,
    )

    assert validate_demand_card(card) == []
    assert card["demand_card"]["development_type"] == "feature"
    assert card["demand_card"]["semantic_mapping"]["domains"] == ["FS DSL"]
    assert card["demand_card"]["semantic_mapping"]["concepts"] == ["hash_to_context operator"]


def test_demand_card_e2e_stays_minimal() -> None:
    card = analyze_and_build_demand_card(
        issue_id="ISSUE-1201",
        issue_text="Fix parser compatibility bug",
        semantic_assets={},
    )

    body = card["demand_card"]
    assert not any(field in body for field in _PROHIBITED_FIELDS)
    assert set(body.keys()) == {
        "request_source",
        "semantic_mapping",
        "development_type",
        "uncertainties",
    }


def test_demand_card_e2e_handles_non_literal_semantic_wording() -> None:
    semantic_assets = {
        "domain_map": {"domains": [{"name": "Redis Discovery"}]},
        "concept_map": {"concepts": [{"name": "hash_to_context operator"}]},
        "rule_map": {"rules": [{"name": "api stability"}]},
        "invariants": ["legacy syntax must remain parseable"],
    }

    card = analyze_and_build_demand_card(
        issue_id="ISSUE-1202",
        issue_text="Add context hashing op and avoid breaking existing interfaces in service registry backend",
        semantic_assets=semantic_assets,
    )

    assert validate_demand_card(card) == []
    mapping = card["demand_card"]["semantic_mapping"]
    assert mapping["domains"] == ["Redis Discovery"]
    assert mapping["concepts"] == ["hash_to_context operator"]
    assert mapping["rules"] == ["api stability"]
    assert not any(field in card["demand_card"] for field in _PROHIBITED_FIELDS)
