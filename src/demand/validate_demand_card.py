"""Demand Card V1 validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ALLOWED_DEVELOPMENT_TYPES = {
    "feature",
    "bugfix",
    "refactor",
    "migration",
    "optimize",
}

_ROOT_ALLOWED_FIELDS = {"demand_card"}
_CARD_ALLOWED_FIELDS = {
    "request_source",
    "semantic_mapping",
    "development_type",
    "uncertainties",
}
_REQUEST_SOURCE_ALLOWED_FIELDS = {"issue_id", "issue_text"}
_SEMANTIC_MAPPING_ALLOWED_FIELDS = {"domains", "concepts", "rules", "invariants"}
_UNCERTAINTIES_ALLOWED_FIELDS = {"open_questions"}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_string_list(
    parent_name: str,
    field_name: str,
    value: Any,
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{parent_name}.{field_name} must be a list")
        return

    for idx, item in enumerate(value):
        if not _is_non_empty_string(item):
            errors.append(
                f"{parent_name}.{field_name}[{idx}] must be a non-empty string"
            )


def _validate_unknown_fields(
    object_name: str,
    value: Any,
    allowed_fields: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        return
    for key in value:
        if key not in allowed_fields:
            errors.append(f"{object_name}.{key} is not allowed")


def validate_demand_card(card: dict[str, Any]) -> list[str]:
    """Validate Demand Card V1."""
    errors: list[str] = []

    if not isinstance(card, dict):
        return ["root must be an object"]

    _validate_unknown_fields("root", card, _ROOT_ALLOWED_FIELDS, errors)

    body = card.get("demand_card")
    if not isinstance(body, dict):
        return ["demand_card must exist and be an object"]

    _validate_unknown_fields("demand_card", body, _CARD_ALLOWED_FIELDS, errors)

    request_source = body.get("request_source")
    if not isinstance(request_source, dict):
        errors.append("demand_card.request_source must exist and be an object")
    else:
        _validate_unknown_fields(
            "demand_card.request_source",
            request_source,
            _REQUEST_SOURCE_ALLOWED_FIELDS,
            errors,
        )
        if not _is_non_empty_string(request_source.get("issue_id")):
            errors.append(
                "demand_card.request_source.issue_id must be a non-empty string"
            )
        if not _is_non_empty_string(request_source.get("issue_text")):
            errors.append(
                "demand_card.request_source.issue_text must be a non-empty string"
            )

    semantic_mapping = body.get("semantic_mapping")
    if not isinstance(semantic_mapping, dict):
        errors.append("demand_card.semantic_mapping must exist and be an object")
    else:
        _validate_unknown_fields(
            "demand_card.semantic_mapping",
            semantic_mapping,
            _SEMANTIC_MAPPING_ALLOWED_FIELDS,
            errors,
        )
        _validate_string_list(
            "demand_card.semantic_mapping",
            "domains",
            semantic_mapping.get("domains"),
            errors,
        )
        _validate_string_list(
            "demand_card.semantic_mapping",
            "concepts",
            semantic_mapping.get("concepts"),
            errors,
        )
        _validate_string_list(
            "demand_card.semantic_mapping",
            "rules",
            semantic_mapping.get("rules"),
            errors,
        )
        _validate_string_list(
            "demand_card.semantic_mapping",
            "invariants",
            semantic_mapping.get("invariants"),
            errors,
        )

    development_type = body.get("development_type")
    if not _is_non_empty_string(development_type):
        errors.append("demand_card.development_type must be a non-empty string")
    elif development_type not in _ALLOWED_DEVELOPMENT_TYPES:
        errors.append(
            "demand_card.development_type must be one of "
            f"{sorted(_ALLOWED_DEVELOPMENT_TYPES)}"
        )

    uncertainties = body.get("uncertainties")
    if not isinstance(uncertainties, dict):
        errors.append("demand_card.uncertainties must exist and be an object")
    else:
        _validate_unknown_fields(
            "demand_card.uncertainties",
            uncertainties,
            _UNCERTAINTIES_ALLOWED_FIELDS,
            errors,
        )
        _validate_string_list(
            "demand_card.uncertainties",
            "open_questions",
            uncertainties.get("open_questions"),
            errors,
        )

    return errors


def is_valid_demand_card(card: dict[str, Any]) -> bool:
    return not validate_demand_card(card)


def validate_demand_card_file(path: str | Path) -> list[str]:
    """Validate demand card from YAML file."""
    file_path = Path(path)
    if not file_path.exists():
        return [f"file not found: {file_path}"]

    try:
        loaded = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"invalid YAML: {exc}"]

    if not isinstance(loaded, dict):
        return ["root must be an object"]

    return validate_demand_card(loaded)
