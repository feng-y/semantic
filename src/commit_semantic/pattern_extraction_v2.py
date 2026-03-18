"""
Pattern extraction wrapper for backward compatibility.

This module provides Dict-based interface while using the new P4 architecture
(patterning.py with dataclasses) internally.
"""

from typing import Dict, List, Tuple

from .patterning import (
    PatternInput,
    build_pattern_fingerprint as _build_pattern_fingerprint,
    group_patterns,
    check_pattern_count as _check_pattern_count,
    infer_action_class,
    infer_object_class,
    infer_constraint_class,
    select_canonical_pattern_case,
)
from .normalize import normalize_text as normalize_for_similarity


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts.

    Wrapper that converts strings to PatternInput for compatibility.
    """
    from .patterning import pair_similarity

    # Create minimal PatternInput objects
    input1 = PatternInput(
        case_id="temp1",
        domain="",
        module="",
        development_type="",
        commit_log="",
        issue_text=text1,
        rules=[],
        invariants=[],
    )
    input2 = PatternInput(
        case_id="temp2",
        domain="",
        module="",
        development_type="",
        commit_log="",
        issue_text=text2,
        rules=[],
        invariants=[],
    )

    return pair_similarity(input1, input2)


def group_by_similarity(cases: List[Dict], threshold: float = 0.75) -> List[List[Dict]]:
    """
    Group cases by similarity within a bucket.

    Wrapper that converts Dict to PatternInput for compatibility.
    """
    from .patterning import cluster_within_bucket

    # Convert to PatternInput
    pattern_inputs = []
    for case in cases:
        pattern_input = PatternInput(
            case_id=case.get("case_id", ""),
            domain=case.get("domain", ""),
            module=case.get("module", ""),
            development_type=case.get("development_type", ""),
            commit_log=case.get("commit_log", ""),
            issue_text=case.get("issue_text", ""),
            rules=case.get("rules", []),
            invariants=case.get("invariants", []),
            semantic_value=case.get("semantic_value", "medium"),
        )
        pattern_inputs.append(pattern_input)

    # Cluster
    clusters = cluster_within_bucket(pattern_inputs, similarity_threshold=threshold)

    # Convert back to Dict format
    result = []
    for cluster in clusters:
        dict_cluster = []
        for pattern_input in cluster:
            # Find original dict by case_id
            for case in cases:
                if case.get("case_id") == pattern_input.case_id:
                    dict_cluster.append(case)
                    break
        if dict_cluster:
            result.append(dict_cluster)

    return result


def extract_domain(case: Dict) -> str:
    """
    DEPRECATED: Extract domain from case module.

    This function is deprecated. Use case.get("domain") directly instead.
    The explicit domain field should be used rather than re-guessing from module.
    """
    module = case.get("module", "unknown")

    # Map common module patterns to domains
    domain_mapping = {
        "parser": "parsing",
        "qserver": "query-service",
        "feature-extraction": "feature-engineering",
        "config": "configuration",
        "registry": "service-registry",
        "demand": "demand-analysis",
        "semantic": "semantic-analysis"
    }

    # Check if module matches any domain
    module_lower = module.lower()
    for key, domain in domain_mapping.items():
        if key in module_lower:
            return domain

    return module


def generate_pattern_fingerprint_v2(case: Dict) -> str:
    """Generate P2/P3 pattern fingerprint."""
    # Use explicit domain field from case, not re-guessed from module
    domain = case.get("domain", "")
    pattern_input = PatternInput(
        case_id=case.get("case_id", ""),
        domain=domain,
        module=case.get("module", ""),
        development_type=case.get("development_type", ""),
        commit_log=case.get("commit_log", ""),
        issue_text=case.get("issue_text", ""),
        rules=case.get("rules", []),
        invariants=case.get("invariants", []),
        semantic_value=case.get("semantic_value", "medium"),
    )
    return _build_pattern_fingerprint(pattern_input)


def extract_patterns_v2(
    cases: List[Dict],
    similarity_threshold: float = 0.50
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Extract patterns with P2/P3 enhancements.

    Returns:
        (patterns, domain_pattern_counts)
    """
    # Convert to PatternInput
    pattern_inputs = []
    for case in cases:
        # Use explicit domain field from case, not re-guessed from module
        domain = case.get("domain", "")
        pattern_input = PatternInput(
            case_id=case.get("case_id", ""),
            domain=domain,
            module=case.get("module", ""),
            development_type=case.get("development_type", ""),
            commit_log=case.get("commit_log", ""),
            issue_text=case.get("issue_text", ""),
            rules=case.get("rules", []),
            invariants=case.get("invariants", []),
            semantic_value=case.get("semantic_value", "medium"),
        )
        pattern_inputs.append(pattern_input)

    # Group patterns
    pattern_groups = group_patterns(pattern_inputs, similarity_threshold=similarity_threshold)

    # Convert to dict format
    patterns = []
    domain_counts: Dict[str, int] = {}

    for group in pattern_groups:
        # Count by domain
        domain_counts[group.domain] = domain_counts.get(group.domain, 0) + 1

        # Convert to dict
        pattern = {
            "pattern_id": group.pattern_id,
            "pattern_fingerprint": group.pattern_fingerprint,
            "domain": group.domain,
            "count": group.count,
            "canonical_case_id": group.canonical_case_id,
            "variant_case_ids": group.variant_case_ids,
            "representative_issue_text": group.representative_issue_text,
            "representative_rules": group.representative_rules,
            "representative_invariants": group.representative_invariants,
            "development_type": group.development_type,
            "action_class": group.action_class,
            "object_class": group.object_class,
            "constraint_class": group.constraint_class,
        }
        patterns.append(pattern)

    # Sort by count (most frequent first)
    patterns.sort(key=lambda p: p["count"], reverse=True)

    return patterns, domain_counts


def check_pattern_count(domain_counts: Dict[str, int]) -> Dict[str, Dict]:
    """
    Check pattern counts per domain and generate alerts.

    Returns:
        {domain: {count, status, action}}
    """
    results = {}

    for domain, count in domain_counts.items():
        check_result = _check_pattern_count([], domain)
        check_result.pattern_count = count

        # Recalculate status based on actual count
        if count < 10:
            status = "excellent"
            action = "none"
        elif count <= 20:
            status = "acceptable"
            action = "none"
        elif count <= 30:
            status = "too_high"
            action = "review_pattern_abstraction"
        else:
            status = "critical"
            action = "review_pattern_abstraction_urgently"

        results[domain] = {
            "pattern_count": count,
            "pattern_count_status": status,
            "action": action
        }

    return results


def extract_action_class(issue_text: str, dev_type: str) -> str:
    """Extract action class - wrapper for backward compatibility."""
    return infer_action_class(issue_text, dev_type)


def extract_object_class(case: Dict) -> str:
    """Extract object class - wrapper for backward compatibility."""
    return infer_object_class(
        case.get("issue_text", ""),
        case.get("commit_log", ""),
        case.get("rules", []),
        case.get("invariants", [])
    )


def extract_constraint_class(rules: List[str], invariants: List[str]) -> str:
    """Extract constraint class - wrapper for backward compatibility."""
    return infer_constraint_class(rules, invariants)


def select_canonical_pattern_case_wrapper(cases: List[Dict]) -> Dict:
    """
    Select canonical pattern case - wrapper for backward compatibility.
    """
    from .patterning import select_canonical_pattern_case as _select_canonical

    # Convert to PatternInput
    pattern_inputs = []
    for case in cases:
        pattern_input = PatternInput(
            case_id=case.get("case_id", ""),
            domain=case.get("domain", ""),
            module=case.get("module", ""),
            development_type=case.get("development_type", ""),
            commit_log=case.get("commit_log", ""),
            issue_text=case.get("issue_text", ""),
            rules=case.get("rules", []),
            invariants=case.get("invariants", []),
            semantic_value=case.get("semantic_value", "medium"),
        )
        pattern_inputs.append(pattern_input)

    # Select canonical
    canonical_input = _select_canonical(pattern_inputs)

    # Find and return original dict
    for case in cases:
        if case.get("case_id") == canonical_input.case_id:
            return case

    return cases[0] if cases else {}


# Alias for backward compatibility
select_canonical_pattern_case = select_canonical_pattern_case_wrapper
