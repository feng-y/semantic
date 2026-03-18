"""
Enhanced pattern extraction with domain-aware aggregation and pattern count control.

P2/P3 Implementation:
- Domain-based pattern fingerprinting
- Action/object/constraint class abstraction
- In-bucket similarity comparison (Jaccard/SequenceMatcher)
- Pattern count control (<10-20 per domain)
- Pattern count alerts
"""

import hashlib
import re
from typing import Dict, List, Tuple
from collections import defaultdict
from difflib import SequenceMatcher


def extract_domain(case: Dict) -> str:
    """
    Extract domain from case.

    For now, use module as domain.
    In production, this should map modules to business domains.
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


def extract_action_class(issue_text: str, dev_type: str) -> str:
    """
    Extract action class from issue_text.

    Keep abstraction level HIGH to reduce pattern count.
    """
    text_lower = issue_text.lower()

    # Map to high-level action classes
    if dev_type == "bugfix" or "fix" in text_lower or "修复" in text_lower:
        return "fix"
    elif dev_type == "refactor" or "refactor" in text_lower or "重构" in text_lower:
        return "refactor"
    elif dev_type == "optimize" or "optimize" in text_lower or "优化" in text_lower:
        return "optimize"
    elif dev_type == "migration" or "migrate" in text_lower or "迁移" in text_lower:
        return "migrate"
    elif "control" in text_lower or "控制" in text_lower:
        return "control"
    elif "align" in text_lower or "对齐" in text_lower:
        return "align"
    else:
        return "add"  # Default for feature


def extract_object_class(case: Dict) -> str:
    """
    Extract object class from issue_text + rules + invariants.

    Keep abstraction level HIGH - prefer broad categories.
    """
    issue_text = case.get("issue_text", "").lower()
    rules = " ".join(case.get("rules", [])).lower()
    invariants = " ".join(case.get("invariants", [])).lower()

    combined = f"{issue_text} {rules} {invariants}"

    # High-level object classes (keep < 15 categories)
    if any(kw in combined for kw in ["parser", "parse", "解析"]):
        return "parser"
    elif any(kw in combined for kw in ["feature", "特征"]):
        return "feature-extraction"
    elif any(kw in combined for kw in ["request", "response", "请求", "响应", "alignment", "对齐"]):
        return "request-response-alignment"
    elif any(kw in combined for kw in ["config", "配置", "setting"]):
        return "config-control"
    elif any(kw in combined for kw in ["registry", "注册", "register"]):
        return "registry"
    elif any(kw in combined for kw in ["compatibility", "兼容", "legacy"]):
        return "compatibility-path"
    elif any(kw in combined for kw in ["concurrency", "并发", "thread", "worker"]):
        return "concurrency-control"
    elif any(kw in combined for kw in ["demand", "需求", "requirement"]):
        return "demand-analysis"
    elif any(kw in combined for kw in ["semantic", "语义"]):
        return "semantic-processing"
    else:
        return "general"


def extract_constraint_class(rules: List[str], invariants: List[str]) -> str:
    """
    Extract constraint class from rules and invariants.

    Returns sorted constraint categories.
    """
    all_items = rules + invariants

    if not all_items:
        return "none"

    categories = set()

    for item in all_items:
        item_lower = item.lower()

        if any(kw in item_lower for kw in ["compatibility", "backward", "legacy", "兼容"]):
            categories.add("compatibility")
        if any(kw in item_lower for kw in ["alignment", "align", "对齐", "consistency", "sync"]):
            categories.add("alignment")
        if any(kw in item_lower for kw in ["concurrency", "thread", "lock", "并发"]):
            categories.add("concurrency")
        if any(kw in item_lower for kw in ["mapping", "map", "映射"]):
            categories.add("mapping")
        if any(kw in item_lower for kw in ["contract", "interface", "约定"]):
            categories.add("contract")
        if any(kw in item_lower for kw in ["migration", "migrate", "迁移"]):
            categories.add("migration")
        if any(kw in item_lower for kw in ["boundary", "bound", "limit", "边界"]):
            categories.add("boundedness")
        if any(kw in item_lower for kw in ["validation", "check", "验证"]):
            categories.add("validation")

    if not categories:
        categories.add("general")

    return "+".join(sorted(categories))


def generate_pattern_fingerprint_v2(case: Dict) -> str:
    """
    Generate P2/P3 pattern fingerprint.

    Format: domain|dev_type|action_class|object_class|constraint_class
    """
    domain = extract_domain(case)
    dev_type = case.get("development_type", "unknown")
    action_class = extract_action_class(case.get("issue_text", ""), dev_type)
    object_class = extract_object_class(case)
    constraint_class = extract_constraint_class(
        case.get("rules", []),
        case.get("invariants", [])
    )

    parts = [domain, dev_type, action_class, object_class, constraint_class]
    return "|".join(parts)


def normalize_for_similarity(text: str) -> str:
    """Normalize text for similarity comparison."""
    # Remove prefix
    text = re.sub(r'^(feat|bugfix|refactor|migration|optimize)：', '', text)

    # Lowercase
    text = text.lower()

    # Remove punctuation
    text = re.sub(r'[^\w\s]', ' ', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def calculate_similarity(text1: str, text2: str) -> float:
    """
    Calculate similarity between two texts.

    Uses combination of Jaccard and SequenceMatcher.
    """
    # Normalize
    norm1 = normalize_for_similarity(text1)
    norm2 = normalize_for_similarity(text2)

    # Token Jaccard
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())

    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0

    jaccard = len(tokens1 & tokens2) / len(tokens1 | tokens2)

    # SequenceMatcher
    seq_sim = SequenceMatcher(None, norm1, norm2).ratio()

    # Weighted average (favor Jaccard for semantic similarity)
    return 0.6 * jaccard + 0.4 * seq_sim


def group_by_similarity(cases: List[Dict], threshold: float = 0.75) -> List[List[Dict]]:
    """
    Group cases by similarity within a bucket.

    Uses greedy clustering approach.
    """
    if not cases:
        return []

    groups = []
    remaining = cases.copy()

    while remaining:
        # Start new group with first remaining case
        seed = remaining.pop(0)
        group = [seed]

        # Find similar cases
        i = 0
        while i < len(remaining):
            candidate = remaining[i]

            # Check similarity with seed
            sim = calculate_similarity(
                seed.get("issue_text", ""),
                candidate.get("issue_text", "")
            )

            if sim >= threshold:
                group.append(candidate)
                remaining.pop(i)
            else:
                i += 1

        groups.append(group)

    return groups


def select_canonical_pattern_case(cases: List[Dict]) -> Dict:
    """
    Select canonical case for a pattern.

    Prefer:
    1. Most abstract but not vague issue_text
    2. Highest information density in rules/invariants
    3. Higher semantic_value
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

        # Prefer cases without specific numbers
        issue_text = case.get("issue_text", "")
        if not re.search(r'\d+', issue_text):
            score += 3

        scored_cases.append((score, case))

    # Sort by score (highest first)
    scored_cases.sort(key=lambda x: x[0], reverse=True)

    return scored_cases[0][1]


def extract_patterns_v2(cases: List[Dict], similarity_threshold: float = 0.75) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Extract patterns with P2/P3 enhancements.

    Returns:
        (patterns, domain_pattern_counts)
    """
    # Group by pattern fingerprint
    fingerprint_buckets = defaultdict(list)

    for case in cases:
        fingerprint = generate_pattern_fingerprint_v2(case)
        case["pattern_fingerprint"] = fingerprint
        fingerprint_buckets[fingerprint].append(case)

    # Within each bucket, group by similarity
    patterns = []
    domain_counts = defaultdict(int)

    for fingerprint, bucket_cases in fingerprint_buckets.items():
        if len(bucket_cases) < 2:
            # Not a pattern if only 1 case
            continue

        # Group by similarity within bucket
        similarity_groups = group_by_similarity(bucket_cases, similarity_threshold)

        for group in similarity_groups:
            if len(group) < 2:
                continue

            # Select canonical case
            canonical = select_canonical_pattern_case(group)

            # Extract domain for counting
            domain = extract_domain(canonical)
            domain_counts[domain] += 1

            # Create pattern
            pattern_id = f"{fingerprint}#{len(patterns):03d}"

            pattern = {
                "pattern_id": pattern_id,
                "pattern_fingerprint": fingerprint,
                "domain": domain,
                "count": len(group),
                "canonical_case_id": canonical["case_id"],
                "variant_case_ids": [c["case_id"] for c in group if c["case_id"] != canonical["case_id"]],
                "representative_issue_text": canonical.get("issue_text", ""),
                "representative_rules": canonical.get("rules", []),
                "representative_invariants": canonical.get("invariants", []),
                "development_type": canonical.get("development_type", ""),
                "action_class": extract_action_class(canonical.get("issue_text", ""), canonical.get("development_type", "")),
                "object_class": extract_object_class(canonical),
                "constraint_class": extract_constraint_class(canonical.get("rules", []), canonical.get("invariants", []))
            }

            patterns.append(pattern)

            # Mark all cases in group with pattern_id
            for case in group:
                case["pattern_id"] = pattern_id

    # Sort patterns by count (most frequent first)
    patterns.sort(key=lambda p: p["count"], reverse=True)

    return patterns, dict(domain_counts)


def check_pattern_count(domain_counts: Dict[str, int]) -> Dict[str, Dict]:
    """
    Check pattern counts per domain and generate alerts.

    Returns:
        {domain: {count, status, action}}
    """
    results = {}

    for domain, count in domain_counts.items():
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
