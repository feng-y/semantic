from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src.demand.build_demand_card import build_demand_card


@pytest.mark.parametrize(
    "development_type",
    ["feature", "bugfix", "refactor", "migration", "optimize"],
)
def test_build_demand_card_accepts_all_allowed_development_types(development_type: str) -> None:
    card = build_demand_card(
        issue_id="ISSUE-101",
        issue_text="Valid demand card input",
        development_type=development_type,
    )
    assert card["demand_card"]["development_type"] == development_type


def test_build_demand_card_minimal_shape() -> None:
    card = build_demand_card(
        issue_id="ISSUE-123",
        issue_text="Add a new operator",
        development_type="feature",
    )

    assert "demand_card" in card
    body = card["demand_card"]

    assert body["request_source"]["issue_id"] == "ISSUE-123"
    assert body["request_source"]["issue_text"] == "Add a new operator"
    assert body["development_type"] == "feature"

    assert body["semantic_mapping"]["domains"] == []
    assert body["semantic_mapping"]["concepts"] == []
    assert body["semantic_mapping"]["rules"] == []
    assert body["semantic_mapping"]["invariants"] == []
    assert body["uncertainties"]["open_questions"] == []


def test_build_demand_card_normalizes_lists() -> None:
    card = build_demand_card(
        issue_id="ISSUE-123",
        issue_text="Add a new operator",
        development_type="feature",
        domains=["dsl", "dsl", "  ", None, "runtime"],
        concepts=["operator", "operator", "slot"],
        rules=["backward-compatibility", "", "thread-safety"],
        invariants=["old syntax remains parseable", None],
        open_questions=["Need new slot?", "Need new slot?", " "],
    )

    mapping = card["demand_card"]["semantic_mapping"]
    uncertainties = card["demand_card"]["uncertainties"]

    assert mapping["domains"] == ["dsl", "runtime"]
    assert mapping["concepts"] == ["operator", "slot"]
    assert mapping["rules"] == ["backward-compatibility", "thread-safety"]
    assert mapping["invariants"] == ["old syntax remains parseable"]
    assert uncertainties["open_questions"] == ["Need new slot?"]


def test_build_demand_card_rejects_empty_issue_id() -> None:
    with pytest.raises(ValueError, match="issue_id"):
        build_demand_card(
            issue_id="",
            issue_text="Add a new operator",
            development_type="feature",
        )


def test_build_demand_card_rejects_empty_issue_text() -> None:
    with pytest.raises(ValueError, match="issue_text"):
        build_demand_card(
            issue_id="ISSUE-123",
            issue_text="   ",
            development_type="feature",
        )


def test_build_demand_card_rejects_invalid_development_type() -> None:
    with pytest.raises(ValueError, match="development_type"):
        build_demand_card(
            issue_id="ISSUE-123",
            issue_text="Add a new operator",
            development_type="integration",
        )
