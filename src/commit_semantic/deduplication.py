"""
Deduplication wrapper for backward compatibility.

This module provides Dict-based interface while using the new P4 architecture
(dedup.py with dataclasses) internally.
"""

from typing import Dict, List, Tuple

from .dedup import DedupInput, build_dedup_key as _build_dedup_key, group_strict_duplicates


def generate_dedup_key(case: Dict) -> str:
    """
    Generate deduplication key based on:
    - module
    - normalized issue_text
    - development_type

    Note: commit_log is NOT included per P2/P3 spec.
    """
    dedup_input = DedupInput(
        case_id=case.get("case_id", ""),
        module=case.get("module", ""),
        development_type=case.get("development_type", ""),
        issue_text=case.get("issue_text", ""),
        rules=case.get("rules", []),
        invariants=case.get("invariants", []),
        semantic_value=case.get("semantic_value", "medium"),
    )
    return _build_dedup_key(dedup_input, use_constraint_signature=False)


def deduplicate_cases(
    cases: List[Dict],
    use_model_optimization: bool = False
) -> Tuple[List[Dict], List[Dict]]:
    """
    Deduplicate cases based on dedup_key.

    Args:
        cases: List of case dictionaries
        use_model_optimization: Enable model-assisted semantic duplicate detection

    Returns:
        (unique_cases, duplicate_groups)

        duplicate_groups format:
        [
            {
                "dedup_key": "abc123",
                "canonical_case_id": "case_001",
                "duplicate_case_ids": ["case_018", "case_042"]
            },
            ...
        ]
    """
    # Convert to DedupInput
    dedup_inputs = []
    case_map = {}
    for case in cases:
        dedup_input = DedupInput(
            case_id=case.get("case_id", ""),
            module=case.get("module", ""),
            development_type=case.get("development_type", ""),
            issue_text=case.get("issue_text", ""),
            rules=case.get("rules", []),
            invariants=case.get("invariants", []),
            semantic_value=case.get("semantic_value", "medium"),
        )
        dedup_inputs.append(dedup_input)
        case_map[case["case_id"]] = case

    # Group duplicates
    dup_groups = group_strict_duplicates(
        dedup_inputs,
        use_constraint_signature=False,
        use_model_optimization=use_model_optimization
    )

    # Build unique cases list and duplicate groups
    unique_case_ids = set()
    duplicate_groups = []

    for group in dup_groups:
        # Add canonical to unique set
        unique_case_ids.add(group.canonical_case_id)

        # Convert to dict format
        duplicate_groups.append({
            "dedup_key": group.dedup_key,
            "canonical_case_id": group.canonical_case_id,
            "duplicate_case_ids": group.duplicate_case_ids,
        })

    # Add all cases that aren't duplicates
    for case in cases:
        case_id = case["case_id"]
        # Generate and attach dedup_key
        case["dedup_key"] = generate_dedup_key(case)

        # Check if this case is a duplicate (not canonical)
        is_duplicate = any(
            case_id in group["duplicate_case_ids"]
            for group in duplicate_groups
        )

        if not is_duplicate:
            unique_case_ids.add(case_id)

    # Build unique cases list
    unique_cases = [case for case in cases if case["case_id"] in unique_case_ids]

    return unique_cases, duplicate_groups
