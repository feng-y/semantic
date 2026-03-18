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
    - normalized commit_log
    """
    module = case.get("module", "")
    issue_text = normalize_text(case.get("issue_text", ""))
    dev_type = case.get("development_type", "")
    commit_log = normalize_text(case.get("commit_log", ""))

    # Combine into key
    key_parts = [module, issue_text, dev_type, commit_log]
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
        (unique_cases, duplicate_cases)
    """
    seen_keys = {}
    unique_cases = []
    duplicate_cases = []

    for case in cases:
        # Generate dedup key
        dedup_key = generate_dedup_key(case)
        case["dedup_key"] = dedup_key

        if dedup_key in seen_keys:
            # Duplicate found
            duplicate_cases.append(case)
        else:
            # First occurrence
            seen_keys[dedup_key] = case
            unique_cases.append(case)

    return unique_cases, duplicate_cases


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
