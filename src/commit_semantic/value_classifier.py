"""
Semantic value classifier for commit cases.

Classifies semantic cases as high/medium/low value based on:
- File type distribution
- Diff patterns
- Change group quality
- Ability to form stable semantic package
"""

from typing import List
from dataclasses import dataclass, field
from src.types import RawCommit, ChangeGroup, SemanticCaseInput


@dataclass
class ValueClassifierConfig:
    """Configurable thresholds for semantic value classification."""
    # Minimum diff size (chars) for a focused change to be high-value
    high_value_focused_min_diff: int = 100
    # Minimum diff size (chars) for a multi-file new implementation to be high-value
    high_value_impl_min_diff: int = 500
    # Max files for a "focused" change
    high_value_max_files: int = 10
    # Max groups for a "focused" change
    high_value_max_groups: int = 5
    # Min code files for multi-file new implementation path
    high_value_impl_min_code_files: int = 2
    # Min files to trigger multi-file implementation check
    high_value_impl_min_files: int = 3


_DEFAULT_CONFIG = ValueClassifierConfig()


def classify_semantic_value(
    commit: RawCommit,
    groups: List[ChangeGroup],
    case: SemanticCaseInput,
    config: ValueClassifierConfig = _DEFAULT_CONFIG,
) -> str:
    """
    Classify semantic value: high/medium/low

    Returns:
        "high", "medium", or "low"
    """
    # Check low value indicators first
    if _is_low_value(commit, groups, case):
        return "low"

    # Check high value indicators
    if _is_high_value(commit, groups, case, config):
        return "high"

    # Default to medium
    return "medium"


def _is_low_value(commit: RawCommit, groups: List[ChangeGroup], case: SemanticCaseInput) -> bool:
    """Check if case has low semantic value."""

    # A. Format/lint/doc only
    if _is_format_only(commit):
        return True

    # B. Test maintenance only
    if _is_test_maintenance_only(commit):
        return True

    # C. Trivial wiring only
    if _is_trivial_wiring_only(commit, case):
        return True

    # D. Pure threshold tweak only
    if _is_pure_threshold_tweak(commit, case):
        return True

    # E. Cannot form stable semantic package
    if _cannot_form_stable_semantic(groups, case):
        return True

    return False


def _is_high_value(
    commit: RawCommit,
    groups: List[ChangeGroup],
    case: SemanticCaseInput,
    config: ValueClassifierConfig = _DEFAULT_CONFIG,
) -> bool:
    """Check if case has high semantic value."""

    # Has clear main object and action
    if len(groups) > 0 and len(case.files) > 0:
        # Has focused change (not too scattered)
        if len(case.files) <= config.high_value_max_files and len(groups) <= config.high_value_max_groups:
            # Has meaningful module
            if case.module and case.module != "unknown":
                # Has substantial diff
                total_diff_size = sum(len(chunk) for chunk in case.diff_chunks)
                if total_diff_size > config.high_value_focused_min_diff:
                    return True

    # New feature implementation (many new files with code)
    if len(case.files) >= config.high_value_impl_min_files:
        code_extensions = {'.py', '.js', '.ts', '.tsx', '.go', '.rs', '.java', '.c', '.cpp'}
        code_files = [f for f in case.files if any(f.endswith(ext) for ext in code_extensions)]

        if len(code_files) >= config.high_value_impl_min_code_files:
            total_diff_size = sum(len(chunk) for chunk in case.diff_chunks)
            if total_diff_size > config.high_value_impl_min_diff:
                return True

    return False


def _is_format_only(commit: RawCommit) -> bool:
    """Check if commit is format/lint/doc/import only."""

    # Check file extensions
    non_code_extensions = {'.md', '.txt', '.json', '.yaml', '.yml', '.toml'}
    code_files = [f for f in commit.files if not any(f.endswith(ext) for ext in non_code_extensions)]

    if not code_files:
        return True

    # Check diff patterns for format-only changes
    all_diffs = '\n'.join(commit.diff_chunks)

    # Format-only indicators
    format_indicators = [
        'prettier',
        'eslint',
        'black',
        'autopep8',
        'import sort',
        'import order',
        'whitespace',
        'trailing space'
    ]

    # If diff is very small and contains format keywords
    if len(all_diffs) < 500:
        if any(indicator in all_diffs.lower() for indicator in format_indicators):
            return True

    return False


def _is_test_maintenance_only(commit: RawCommit) -> bool:
    """Check if commit is test maintenance only."""

    # All files are test files
    if commit.files and all('test' in f.lower() for f in commit.files):
        all_diffs = '\n'.join(commit.diff_chunks)

        # Snapshot update indicators
        snapshot_indicators = [
            'snapshot',
            'expect(',
            'toMatchSnapshot',
            'assert_equal',
            'assertEqual'
        ]

        # If only updating test assertions/snapshots
        if any(indicator in all_diffs for indicator in snapshot_indicators):
            # And no new test logic
            if 'def test_' not in all_diffs and 'it(' not in all_diffs and 'test(' not in all_diffs:
                return True

    return False


def _is_trivial_wiring_only(commit: RawCommit, case: SemanticCaseInput) -> bool:
    """Check if commit is trivial config/flag wiring only."""

    # Check if only config files
    config_patterns = ['config', 'settings', 'constants', 'flags', 'feature_flags']

    if len(case.files) <= 2:
        if all(any(pattern in f.lower() for pattern in config_patterns) for f in case.files):
            all_diffs = '\n'.join(case.diff_chunks)

            # Very small change
            if len(all_diffs) < 300:
                # Just adding/removing config entries
                if all_diffs.count('+') < 5 and all_diffs.count('-') < 5:
                    return True

    return False


def _is_pure_threshold_tweak(commit: RawCommit, case: SemanticCaseInput) -> bool:
    """Check if commit is pure threshold/timeout/retry tweak only."""

    all_diffs = '\n'.join(case.diff_chunks)

    # Threshold tweak indicators
    threshold_keywords = [
        'timeout',
        'retry',
        'max_retries',
        'sleep',
        'delay',
        'interval',
        'threshold',
        'limit',
        'max_',
        'min_'
    ]

    # Check if diff only contains number changes with threshold keywords
    if len(all_diffs) < 200:
        has_threshold_keyword = any(keyword in all_diffs.lower() for keyword in threshold_keywords)

        # Count numeric changes
        import re
        numeric_changes = re.findall(r'[-+]\s*\w+\s*=\s*\d+', all_diffs)

        if has_threshold_keyword and len(numeric_changes) > 0 and len(numeric_changes) <= 3:
            # No substantial logic change
            if 'def ' not in all_diffs and 'class ' not in all_diffs and 'function ' not in all_diffs:
                return True

    return False


def _cannot_form_stable_semantic(groups: List[ChangeGroup], case: SemanticCaseInput) -> bool:
    """Check if case cannot form stable semantic package."""

    # Too scattered (very high threshold)
    if len(case.files) > 30:
        return True

    # Too many unrelated groups (very high threshold)
    if len(groups) > 15:
        return True

    # No clear module AND too many files
    if not case.module or case.module == "unknown":
        if len(case.files) > 10:
            return True

    # Too many split hints (need at least 3 hints to reject)
    hints = case.split_hints
    hint_count = sum([
        hints.too_many_files,
        hints.too_many_diff_themes,
        hints.mixed_feature_and_bugfix,
        hints.unrelated_objects_detected
    ])

    if hint_count >= 4:  # Changed from 3 to 4
        return True

    return False
