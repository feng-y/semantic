"""Issue normalization for demand analysis."""

from __future__ import annotations

from typing import Any


def normalize_issue(*, issue_id: Any, issue_text: Any) -> dict[str, str]:
    """Normalize raw issue input into a stable minimal object.

    Rules:
    - trim whitespace
    - reject empty issue_id
    - reject empty issue_text
    - preserve original meaning (no summary generation)
    """
    normalized_issue_id = str(issue_id or "").strip()
    normalized_issue_text = str(issue_text or "").strip()

    if not normalized_issue_id:
        raise ValueError("issue_id must be a non-empty string")
    if not normalized_issue_text:
        raise ValueError("issue_text must be a non-empty string")

    return {
        "issue_id": normalized_issue_id,
        "issue_text": normalized_issue_text,
    }
