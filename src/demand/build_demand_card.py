"""Demand Card V1 builder."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml

from .map_semantics import load_semantic_foundation_assets, map_semantics
from .match_development_type import match_development_type
from .models import DemandCard, DemandCardBody, RequestSource, SemanticMapping, Uncertainties
from .normalize_issue import normalize_issue
from .validate_demand_card import validate_demand_card

_ALLOWED_DEVELOPMENT_TYPES = {
    "feature",
    "bugfix",
    "refactor",
    "migration",
    "optimize",
}


def _normalize_str_list(values: Iterable[Any] | None) -> list[str]:
    """Normalize an iterable into a clean list[str]."""
    if values is None:
        return []

    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value is None:
            continue
        item = str(value).strip()
        if not item:
            continue
        if item in seen:
            continue
        seen.add(item)
        result.append(item)

    return result


def build_demand_card(
    *,
    issue_id: str,
    issue_text: str,
    domains: Iterable[Any] | None = None,
    concepts: Iterable[Any] | None = None,
    rules: Iterable[Any] | None = None,
    invariants: Iterable[Any] | None = None,
    development_type: str,
    open_questions: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build a Demand Card V1 artifact."""
    issue_id = issue_id.strip()
    issue_text = issue_text.strip()
    development_type = development_type.strip()

    if not issue_id:
        raise ValueError("issue_id must be a non-empty string")
    if not issue_text:
        raise ValueError("issue_text must be a non-empty string")
    if development_type not in _ALLOWED_DEVELOPMENT_TYPES:
        raise ValueError(
            f"development_type must be one of "
            f"{sorted(_ALLOWED_DEVELOPMENT_TYPES)}, got: {development_type!r}"
        )

    card = DemandCard(
        demand_card=DemandCardBody(
            request_source=RequestSource(issue_id=issue_id, issue_text=issue_text),
            semantic_mapping=SemanticMapping(
                domains=_normalize_str_list(domains),
                concepts=_normalize_str_list(concepts),
                rules=_normalize_str_list(rules),
                invariants=_normalize_str_list(invariants),
            ),
            development_type=development_type,
            uncertainties=Uncertainties(open_questions=_normalize_str_list(open_questions)),
        ),
    )
    return card.to_dict()


def write_demand_card(card: dict[str, object], output_path: str | Path) -> Path:
    """Write demand card YAML to the target path."""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump(card, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return output


def build_and_write_demand_card(
    *,
    issue_id: str,
    issue_text: str,
    development_type: str,
    output_path: str | Path,
    domains: Iterable[Any] | None = None,
    concepts: Iterable[Any] | None = None,
    rules: Iterable[Any] | None = None,
    invariants: Iterable[Any] | None = None,
    open_questions: Iterable[Any] | None = None,
) -> dict[str, Any]:
    """Build and persist demand card YAML."""
    card = build_demand_card(
        issue_id=issue_id,
        issue_text=issue_text,
        development_type=development_type,
        domains=domains,
        concepts=concepts,
        rules=rules,
        invariants=invariants,
        open_questions=open_questions,
    )
    write_demand_card(card=card, output_path=output_path)
    return card


def analyze_and_build_demand_card(
    *,
    issue_id: str,
    issue_text: str,
    semantic_assets: dict[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a demand card by running normalize -> map -> match -> assemble -> validate."""
    normalized = normalize_issue(issue_id=issue_id, issue_text=issue_text)

    assets = semantic_assets
    if assets is None and repo_root is not None:
        assets = load_semantic_foundation_assets(repo_root)

    mapping = map_semantics(
        issue_text=normalized["issue_text"],
        semantic_assets=assets,
    )
    matched = match_development_type(
        issue_text=normalized["issue_text"],
        semantic_mapping=mapping,
        demand_model_map=(assets or {}).get("demand_model_map", {}),
    )

    card = build_demand_card(
        issue_id=normalized["issue_id"],
        issue_text=normalized["issue_text"],
        domains=mapping["domains"],
        concepts=mapping["concepts"],
        rules=mapping["rules"],
        invariants=mapping["invariants"],
        development_type=matched["development_type"],
        open_questions=matched["open_questions"],
    )

    errors = validate_demand_card(card)
    if errors:
        raise ValueError("generated demand card is invalid: " + "; ".join(errors))

    return card


def analyze_build_and_write_demand_card(
    *,
    issue_id: str,
    issue_text: str,
    output_path: str | Path,
    semantic_assets: dict[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    """Analyze issue input into demand fields, build card, and write YAML."""
    card = analyze_and_build_demand_card(
        issue_id=issue_id,
        issue_text=issue_text,
        semantic_assets=semantic_assets,
        repo_root=repo_root,
    )
    write_demand_card(card=card, output_path=output_path)
    return card
