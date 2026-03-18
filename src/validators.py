from typing import Dict, List, Optional
from src.types import SemanticCaseOutput, DevelopmentType


class ValidationError(Exception):
    """Validation error with reason."""
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def validate_structure(case_dict: Dict) -> None:
    """Validate required fields are present."""
    required_fields = [
        'case_id', 'commit_id', 'module', 'commit_log',
        'issue_text', 'development_type', 'rules', 'invariants',
        'split_suggestion'
    ]

    for field in required_fields:
        if field not in case_dict:
            raise ValidationError(f"Missing required field: {field}")

    # Validate split_suggestion structure
    if 'needs_split' not in case_dict['split_suggestion']:
        raise ValidationError("Missing split_suggestion.needs_split")
    if 'split_reasons' not in case_dict['split_suggestion']:
        raise ValidationError("Missing split_suggestion.split_reasons")


def validate_types(case_dict: Dict) -> None:
    """Validate field types."""
    if not isinstance(case_dict['commit_log'], str):
        raise ValidationError("commit_log must be string")
    if not isinstance(case_dict['issue_text'], str):
        raise ValidationError("issue_text must be string")
    if not isinstance(case_dict['development_type'], str):
        raise ValidationError("development_type must be string")
    if not isinstance(case_dict['rules'], list):
        raise ValidationError("rules must be list")
    if not isinstance(case_dict['invariants'], list):
        raise ValidationError("invariants must be list")
    if not isinstance(case_dict['split_suggestion']['needs_split'], bool):
        raise ValidationError("split_suggestion.needs_split must be bool")
    if not isinstance(case_dict['split_suggestion']['split_reasons'], list):
        raise ValidationError("split_suggestion.split_reasons must be list")


def validate_enums(case_dict: Dict) -> None:
    """Validate enum values."""
    valid_types = {'feature', 'bugfix', 'refactor', 'migration', 'optimize'}
    dev_type = case_dict['development_type']

    if dev_type not in valid_types:
        raise ValidationError(f"Invalid development_type: {dev_type}")


def validate_consistency(case_dict: Dict) -> None:
    """Validate consistency rules."""
    issue_text = case_dict['issue_text']
    dev_type = case_dict['development_type']

    # Map development_type to expected prefix
    prefix_map = {
        'feature': 'feat：',
        'bugfix': 'bugfix：',
        'refactor': 'refactor：',
        'migration': 'migration：',
        'optimize': 'optimize：'
    }

    expected_prefix = prefix_map[dev_type]
    if not issue_text.startswith(expected_prefix):
        raise ValidationError(
            f"issue_text prefix mismatch: expected '{expected_prefix}' for type '{dev_type}'"
        )

    # Validate split_suggestion consistency
    needs_split = case_dict['split_suggestion']['needs_split']
    split_reasons = case_dict['split_suggestion']['split_reasons']

    if not needs_split and split_reasons:
        raise ValidationError("needs_split=false but split_reasons is not empty")

    # Check for requirement-style commit_log
    commit_log = case_dict['commit_log']
    forbidden_prefixes = ['feat：', 'bugfix：', 'refactor：', 'migration：', 'optimize：']
    if any(commit_log.startswith(prefix) for prefix in forbidden_prefixes):
        raise ValidationError("commit_log should not use requirement-style prefixes")

    # Check for generic development rules/invariants
    generic_patterns = [
        'null check', 'bounds check', 'exception handling',
        'input validation', 'avoid crash', 'thread-safety',
        'code style', 'defensive programming'
    ]

    all_rules_invariants = case_dict['rules'] + case_dict['invariants']
    for item in all_rules_invariants:
        item_lower = item.lower()
        if any(pattern in item_lower for pattern in generic_patterns):
            raise ValidationError(
                f"Generic development rule/invariant detected: {item}"
            )


def validate_semantic_case(case_dict: Dict) -> None:
    """Run all validation checks on a semantic case."""
    if not isinstance(case_dict, dict):
        raise ValidationError(f"Expected dict, got {type(case_dict)}")

    validate_structure(case_dict)
    validate_types(case_dict)
    validate_enums(case_dict)
    validate_consistency(case_dict)
