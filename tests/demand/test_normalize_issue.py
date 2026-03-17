from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.demand.normalize_issue import normalize_issue


def test_normalize_issue_trims_whitespace() -> None:
    normalized = normalize_issue(issue_id="  ISSUE-900  ", issue_text="  Add new DSL operator  ")
    assert normalized == {
        "issue_id": "ISSUE-900",
        "issue_text": "Add new DSL operator",
    }


def test_normalize_issue_rejects_empty_issue_id() -> None:
    with pytest.raises(ValueError, match="issue_id"):
        normalize_issue(issue_id="  ", issue_text="Valid text")


def test_normalize_issue_rejects_empty_issue_text() -> None:
    with pytest.raises(ValueError, match="issue_text"):
        normalize_issue(issue_id="ISSUE-901", issue_text="")


def test_normalize_issue_keeps_original_meaning_text() -> None:
    source_text = "Fix parser compatibility bug for legacy syntax"
    normalized = normalize_issue(issue_id="ISSUE-902", issue_text=source_text)
    assert normalized["issue_text"] == source_text
