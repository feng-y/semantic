"""
Deduplication logic for semantic cases.

Generates dedup keys and identifies duplicate cases.
"""

import hashlib
import re
from typing import Dict, List, Tuple


def generate_dedup_key(case: Dict) -> str:
    """
    Generate deduplication key based on:
    - module
    - normalized issue_text
    - development_type

    Note: commit_log is NOT included per P2/P3 spec, as it naturally differs
    for the same pattern applied to different objects/paths/modules.
    """
    module = case.get("module", "")
    issue_text = normalize_text(case.get("issue_text", ""))
    dev_type = case.get("development_type", "")

    # Combine into key
    key_parts = [module, issue_text, dev_type]
    key_string = "|".join(key_parts)

    # Hash for consistent length
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison:
    - Remove extra whitespace
    - Lowercase
    - Remove punctuation
    - Remove numbers (for more aggressive dedup)
    """
    # Remove prefix (feat：, bugfix：, etc.)
    text = re.sub(r'^(feat|bugfix|refactor|migration|optimize)：', '', text)

    # Lowercase
    text = text.lower()

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)

    # Strip
    text = text.strip()

    return text


def deduplicate_cases(cases: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Deduplicate cases based on dedup_key.

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
    dedup_groups = {}

    for case in cases:
        # Generate dedup key
        dedup_key = generate_dedup_key(case)
        case["dedup_key"] = dedup_key

        if dedup_key not in dedup_groups:
            dedup_groups[dedup_key] = []

        dedup_groups[dedup_key].append(case)

    # Separate unique cases and duplicate groups
    unique_cases = []
    duplicate_groups = []

    for dedup_key, group in dedup_groups.items():
        if len(group) == 1:
            # Unique case
            unique_cases.append(group[0])
        else:
            # Duplicate group - select canonical case
            canonical = select_canonical_case(group)
            unique_cases.append(canonical)

            # Record duplicate group
            duplicate_group = {
                "dedup_key": dedup_key,
                "canonical_case_id": canonical["case_id"],
                "duplicate_case_ids": [c["case_id"] for c in group if c["case_id"] != canonical["case_id"]]
            }
            duplicate_groups.append(duplicate_group)

    return unique_cases, duplicate_groups


def select_canonical_case(cases: List[Dict]) -> Dict:
    """
    Select canonical case from duplicate group.

    Priority:
    1. Higher semantic_value
    2. Clearer issue_text (not empty, not too vague)
    3. More rules + invariants
    4. First case_id (stable tiebreaker)
    """
    if not cases:
        return {}

    scored_cases = []

    for case in cases:
        score = 0

        # Prefer higher semantic_value
        semantic_value = case.get("semantic_value", "medium")
        if semantic_value == "high":
            score += 10
        elif semantic_value == "medium":
            score += 5

        # Prefer more rules/invariants
        score += len(case.get("rules", []))
        score += len(case.get("invariants", []))

        # Prefer moderate issue_text length (not too short, not too long)
        issue_len = len(case.get("issue_text", ""))
        if 20 < issue_len < 80:
            score += 5

        scored_cases.append((score, case))

    # Sort by score (highest first)
    scored_cases.sort(key=lambda x: x[0], reverse=True)

    return scored_cases[0][1]


def find_near_duplicates(cases: List[Dict], similarity_threshold: float = 0.9) -> List[List[str]]:
    """
    Find near-duplicate groups using text similarity.

    Returns:
        List of duplicate groups (each group is a list of case_ids)
    """
    # Simple implementation: group by normalized issue_text
    groups = {}

    for case in cases:
        normalized = normalize_text(case.get("issue_text", ""))

        if normalized not in groups:
            groups[normalized] = []

        groups[normalized].append(case["case_id"])

    # Return groups with more than 1 member
    duplicate_groups = [group for group in groups.values() if len(group) > 1]

    return duplicate_groups
