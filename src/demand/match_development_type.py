"""Development type matching for demand analysis."""

from __future__ import annotations

import re
from typing import Any

_ALLOWED_DEVELOPMENT_TYPES = (
    "feature",
    "bugfix",
    "refactor",
    "migration",
    "optimize",
)

_CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
    "bugfix": (
        r"\bbug\b",
        r"\bfix\b",
        r"\berror\b",
        r"\bcrash\b",
        r"\bregression\b",
        r"\bfail(?:ure|ing)?\b",
        r"\bbroken\b",
        r"\bcompatibility bug\b",
    ),
    "migration": (
        r"\bmigrate\b",
        r"\bmigration\b",
        r"\bupgrade\b",
        r"\bport\b",
        r"\breplace\b",
        r"\bmove to\b",
    ),
    "refactor": (
        r"\brefactor\b",
        r"\brestructure\b",
        r"\bcleanup\b",
        r"\breorganize\b",
        r"\brename\b",
    ),
    "optimize": (
        r"\boptimi[sz]e\b",
        r"\bperformance\b",
        r"\blatency\b",
        r"\bthroughput\b",
        r"\bcpu\b",
        r"\bmemory\b",
        r"\boverhead\b",
        r"\bfaster\b",
    ),
    "feature": (
        r"\badd\b",
        r"\bintroduce\b",
        r"\bnew\b",
        r"\bimplement\b",
        r"\bsupport\b",
        r"\bcreate\b",
    ),
}

_PRIORITY = ("bugfix", "migration", "refactor", "optimize", "feature")


def _normalize_string(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _semantic_context_text(semantic_mapping: dict[str, Any] | None) -> str:
    if not isinstance(semantic_mapping, dict):
        return ""

    context_parts: list[str] = []
    for key in ("domains", "concepts", "rules", "invariants"):
        values = semantic_mapping.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            text = _normalize_string(value)
            if text:
                context_parts.append(text)
    return " ".join(context_parts)


def _extract_model_hint(issue_text: str, demand_model_map: dict[str, Any] | None) -> str | None:
    """Extract development_type hint from demand model map when explicitly referenced."""
    if not isinstance(demand_model_map, dict):
        return None

    issue_text_lower = issue_text.lower()
    models = demand_model_map.get("demand_models", [])
    if not isinstance(models, list):
        return None

    for model in models:
        if not isinstance(model, dict):
            continue

        references: list[str] = []
        for key in ("name", "id", "summary", "description"):
            value = _normalize_string(model.get(key))
            if value:
                references.append(value.lower())

        if references and not any(ref in issue_text_lower for ref in references):
            continue

        explicit_type = _normalize_string(model.get("development_type")).lower()
        if explicit_type in _ALLOWED_DEVELOPMENT_TYPES:
            return explicit_type

        hint_values: list[str] = []
        hints = model.get("development_types", [])
        if isinstance(hints, list):
            hint_values.extend(_normalize_string(value).lower() for value in hints)
        hints = model.get("hints", [])
        if isinstance(hints, list):
            hint_values.extend(_normalize_string(value).lower() for value in hints)

        for hint in hint_values:
            if hint in _ALLOWED_DEVELOPMENT_TYPES:
                return hint

    return None


def _matched_categories(issue_text: str) -> list[str]:
    lowered = issue_text.lower()
    matches: list[str] = []
    for category in _ALLOWED_DEVELOPMENT_TYPES:
        patterns = _CATEGORY_PATTERNS[category]
        if any(re.search(pattern, lowered) for pattern in patterns):
            matches.append(category)
    return matches


def match_development_type(
    *,
    issue_text: str,
    semantic_mapping: dict[str, Any] | None = None,
    demand_model_map: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Choose one development type and derive open questions."""
    context_text = _semantic_context_text(semantic_mapping)
    combined_text = issue_text if not context_text else f"{issue_text} {context_text}"
    matches = _matched_categories(combined_text)
    open_questions: list[str] = []
    model_hint = _extract_model_hint(issue_text, demand_model_map)

    if model_hint:
        if matches and model_hint not in matches:
            open_questions.append(
                "Demand model hint conflicts with textual intent; confirm primary type is "
                f"'{model_hint}'."
            )
        return {
            "development_type": model_hint,
            "open_questions": open_questions,
        }

    if not matches:
        return {
            "development_type": "feature",
            "open_questions": [
                "Issue intent is unclear; confirm whether this is feature, bugfix, refactor, migration, or optimize."
            ],
        }

    if len(matches) == 1:
        return {
            "development_type": matches[0],
            "open_questions": [],
        }

    chosen = next(category for category in _PRIORITY if category in matches)
    open_questions.append(
        "Multiple development intents detected ("
        + ", ".join(sorted(matches))
        + f"); confirm primary type is '{chosen}'."
    )

    return {
        "development_type": chosen,
        "open_questions": open_questions,
    }
