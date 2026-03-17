from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.run import run_demand_pipeline
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


@pytest.mark.parametrize(
    "issue_text,expected_type",
    [
        ("Add hash_to_context operator in FS DSL", "feature"),
        ("Fix parser compatibility bug in legacy syntax", "bugfix"),
        ("Reduce latency and CPU overhead in feature extraction", "optimize"),
    ],
)
def test_demand_pipeline_e2e_scenarios(issue_text: str, expected_type: str) -> None:
    semantic_assets = {
        "domain_map": {"domains": [{"name": "FS DSL"}, {"name": "Parser"}]},
        "concept_map": {"concepts": [{"name": "hash_to_context operator"}, {"name": "feature extraction"}]},
        "rule_map": {"rules": [{"name": "parser compatibility"}, {"name": "api stability"}]},
        "invariants": ["legacy syntax must remain parseable"],
    }

    result = run_demand_pipeline(
        issue_id="ISSUE-E2E-1",
        issue_text=issue_text,
        semantic_assets=semantic_assets,
    )

    assert result["ok"] is True
    card = result["demand_card"]
    assert validate_demand_card(card) == []

    body = card["demand_card"]
    assert body["development_type"] == expected_type
    assert set(body.keys()) == {
        "request_source",
        "semantic_mapping",
        "development_type",
        "uncertainties",
    }
    assert not any(field in body for field in _PROHIBITED_FIELDS)
