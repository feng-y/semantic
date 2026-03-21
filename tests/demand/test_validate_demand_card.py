from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.validate_demand_card import is_valid_demand_card, validate_demand_card


def _valid_card() -> dict:
    return {
        "demand_card": {
            "request_source": {
                "issue_id": "ISSUE-123",
                "issue_text": "Add a new operator",
            },
            "semantic_mapping": {
                "domains": ["dsl"],
                "concepts": ["operator"],
                "rules": ["backward-compatibility"],
                "invariants": ["old syntax remains parseable"],
            },
            "development_type": "feature",
            "uncertainties": {
                "open_questions": [],
            },
        }
    }


def test_validate_demand_card_accepts_valid_card() -> None:
    card = _valid_card()
    assert validate_demand_card(card) == []
    assert is_valid_demand_card(card) is True


def test_validate_demand_card_rejects_missing_issue_id() -> None:
    card = _valid_card()
    del card["demand_card"]["request_source"]["issue_id"]

    errors = validate_demand_card(card)
    assert any("issue_id" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_missing_issue_text() -> None:
    card = _valid_card()
    del card["demand_card"]["request_source"]["issue_text"]

    errors = validate_demand_card(card)
    assert any("issue_text" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_invalid_development_type() -> None:
    card = _valid_card()
    card["demand_card"]["development_type"] = "analysis"

    errors = validate_demand_card(card)
    assert any("development_type" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_non_list_domains() -> None:
    card = _valid_card()
    card["demand_card"]["semantic_mapping"]["domains"] = "dsl"

    errors = validate_demand_card(card)
    assert any("domains must be a list" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_empty_string_in_rules() -> None:
    card = _valid_card()
    card["demand_card"]["semantic_mapping"]["rules"] = ["backward-compatibility", "  "]

    errors = validate_demand_card(card)
    assert any("rules[1]" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_non_string_open_questions() -> None:
    card = _valid_card()
    card["demand_card"]["uncertainties"]["open_questions"] = [123]

    errors = validate_demand_card(card)
    assert any("open_questions[0]" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_non_list_open_questions() -> None:
    card = _valid_card()
    card["demand_card"]["uncertainties"]["open_questions"] = "need clarification"

    errors = validate_demand_card(card)
    assert any("open_questions" in err for err in errors)
    assert is_valid_demand_card(card) is False


def test_validate_demand_card_rejects_unknown_field_under_demand_card() -> None:
    card = _valid_card()
    card["demand_card"]["extra"] = "x"

    errors = validate_demand_card(card)
    assert any("demand_card.extra" in err for err in errors)


def test_validate_demand_card_rejects_unknown_field_under_request_source() -> None:
    card = _valid_card()
    card["demand_card"]["request_source"]["unknown"] = "x"

    errors = validate_demand_card(card)
    assert any("request_source.unknown" in err for err in errors)


def test_validate_demand_card_rejects_unknown_field_under_semantic_mapping() -> None:
    card = _valid_card()
    card["demand_card"]["semantic_mapping"]["extra"] = "x"

    errors = validate_demand_card(card)
    assert any("semantic_mapping.extra" in err for err in errors)


def test_validate_demand_card_rejects_unknown_field_under_uncertainties() -> None:
    card = _valid_card()
    card["demand_card"]["uncertainties"]["extra"] = "x"

    errors = validate_demand_card(card)
    assert any("uncertainties.extra" in err for err in errors)


def test_validate_demand_card_rejects_unknown_field_at_root() -> None:
    card = _valid_card()
    card["extra"] = "x"

    errors = validate_demand_card(card)
    assert any("root.extra" in err for err in errors)
