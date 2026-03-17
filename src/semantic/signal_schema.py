"""
Signal schema validation for the semantic cache.
"""
from typing import Dict, Any, List, Tuple

KNOWN_CATEGORIES = frozenset([
    'domain_signals',
    'concept_signals',
    'rule_signals',
    'demand_pattern_signals',
])


def validate_signals(signals: Any) -> Tuple[bool, List[str]]:
    """
    Validate a signals dict against the expected schema.

    Returns:
        (is_valid, errors) where errors is a list of human-readable error strings.
        is_valid is True iff errors is empty.
    """
    errors = []

    if signals is None:
        errors.append("signals must not be None")
        return False, errors

    if not isinstance(signals, dict):
        errors.append(f"signals must be a dict, got {type(signals).__name__}")
        return False, errors

    for category in KNOWN_CATEGORIES:
        if category not in signals:
            continue  # missing categories are OK
        value = signals[category]
        if not isinstance(value, list):
            errors.append(f"{category} must be a list, got {type(value).__name__}")
            continue
        for i, item in enumerate(value):
            if not isinstance(item, dict):
                errors.append(f"{category}[{i}] must be a dict, got {type(item).__name__}")

    return len(errors) == 0, errors
