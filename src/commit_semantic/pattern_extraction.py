"""
Pattern extraction — Dict-based interface over patterning.py (P4 dataclass core).

Kept for export skill code that works with plain dicts.
All logic lives in patterning.py; this module is a thin adapter.
"""

import hashlib
import re
from collections import defaultdict


def generate_pattern_fingerprint(case: dict) -> str:
    """
    Generate pattern fingerprint based on:
    - module
    - development_type
    - normalized issue template
    - modified object class
    - rules/invariants signature
    """
    module = case.get("module", "")
    dev_type = case.get("development_type", "")
    issue_template = extract_issue_template(case.get("issue_text", ""))
    object_class = extract_object_class(case.get("files", []))
    rules_sig = generate_rules_signature(case.get("rules", []), case.get("invariants", []))

    # Combine into fingerprint
    parts = [module, dev_type, issue_template, object_class, rules_sig]
    fingerprint_string = "|".join(parts)

    # Hash for consistent length
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()[:16]


def extract_issue_template(issue_text: str) -> str:
    """
    Extract template from issue_text by removing specific details.

    Example:
    "bugfix：修复旧DSL写法边界检查" -> "bugfix：修复边界检查"
    "feat：实现需求分析流程" -> "feat：实现分析流程"
    """
    # Remove prefix
    text = re.sub(r'^(feat|bugfix|refactor|migration|optimize)：', '', issue_text)

    # Remove specific identifiers (numbers, version strings, etc.)
    text = re.sub(r'\d+', '', text)
    text = re.sub(r'v\d+\.\d+', '', text)

    # Remove adjectives that add specificity
    specific_words = ['旧', '新', '老', '最新', '当前', '原有', 'legacy', 'new', 'old', 'current']
    for word in specific_words:
        text = text.replace(word, '')

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Add prefix back
    prefix = issue_text.split('：')[0] if '：' in issue_text else ''
    if prefix:
        return f"{prefix}：{text}"

    return text


def extract_object_class(files: list[str]) -> str:
    """
    Extract object class from file paths.

    Examples:
    - src/parser/legacy.py -> parser
    - src/qserver/request.py -> qserver
    - config/feature_flags.yaml -> config
    """
    if not files:
        return "unknown"

    # Extract directory names
    dirs = set()
    for file_path in files:
        parts = file_path.split('/')
        if len(parts) > 1:
            # Get first meaningful directory
            for part in parts:
                if part not in ['src', 'lib', 'app', 'tests', 'test']:
                    dirs.add(part)
                    break

    if not dirs:
        return "unknown"

    # Return most common or first
    return sorted(dirs)[0]


def generate_rules_signature(rules: list[str], invariants: list[str]) -> str:
    """
    Generate signature from rules and invariants.

    Groups similar rules/invariants into categories.
    """
    all_items = rules + invariants

    if not all_items:
        return "none"

    # Categorize rules/invariants
    categories = set()

    for item in all_items:
        item_lower = item.lower()

        if any(kw in item_lower for kw in ['compatibility', 'backward', 'legacy']):
            categories.add('compatibility')
        elif any(kw in item_lower for kw in ['boundary', 'check', 'validation']):
            categories.add('validation')
        elif any(kw in item_lower for kw in ['concurrency', 'thread', 'lock']):
            categories.add('concurrency')
        elif any(kw in item_lower for kw in ['performance', 'optimize', 'cache']):
            categories.add('performance')
        elif any(kw in item_lower for kw in ['alignment', 'consistency', 'sync']):
            categories.add('alignment')
        else:
            categories.add('other')

    return '+'.join(sorted(categories))


def extract_patterns(cases: list[dict]) -> list[dict]:
    """
    Extract patterns from cases.

    Returns:
        List of patterns with canonical samples and variants
    """
    # Group cases by pattern fingerprint
    pattern_groups = defaultdict(list)

    for case in cases:
        fingerprint = generate_pattern_fingerprint(case)
        case["pattern_id"] = fingerprint
        pattern_groups[fingerprint].append(case)

    # Build pattern objects
    patterns = []

    for pattern_id, group_cases in pattern_groups.items():
        if len(group_cases) < 2:
            # Not a pattern if only 1 case
            continue

        # Select canonical case (first one, or could use more sophisticated selection)
        canonical_case = select_canonical_case(group_cases)

        pattern = {
            "pattern_id": pattern_id,
            "count": len(group_cases),
            "canonical_case_id": canonical_case["case_id"],
            "variant_case_ids": [c["case_id"] for c in group_cases if c["case_id"] != canonical_case["case_id"]],
            "module": canonical_case.get("module", ""),
            "development_type": canonical_case.get("development_type", ""),
            "issue_template": extract_issue_template(canonical_case.get("issue_text", "")),
            "object_class": extract_object_class(canonical_case.get("files", []))
        }

        patterns.append(pattern)

    # Sort by count (most frequent first)
    patterns.sort(key=lambda p: p["count"], reverse=True)

    return patterns


def select_canonical_case(cases: list[dict]) -> dict:
    """
    Select canonical case from a group.

    Criteria:
    - Prefer cases with more rules/invariants
    - Prefer cases with clearer commit_log
    - Prefer earlier cases (stable)
    """
    if not cases:
        return {}

    # Score each case
    scored_cases = []

    for case in cases:
        score: float = 0

        # More rules/invariants is better
        score += len(case.get("rules", []))
        score += len(case.get("invariants", []))

        # Longer commit_log is better (more detailed)
        score += len(case.get("commit_log", "")) / 100

        # Clearer issue_text (not too short, not too long)
        issue_len = len(case.get("issue_text", ""))
        if 20 < issue_len < 100:
            score += 5

        scored_cases.append((score, case))

    # Sort by score (highest first)
    scored_cases.sort(key=lambda x: x[0], reverse=True)

    return scored_cases[0][1]
