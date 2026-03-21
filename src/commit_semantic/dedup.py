"""
Strict deduplication logic for semantic cases.

Identifies exact duplicates based on:
- module
- development_type
- normalized issue_text
- optional constraint signature

Note: commit_log is NOT included in dedup key per P2/P3/P4 spec.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from .model_optimizer import (
    ModelOptimizerConfig,
    check_semantic_duplicates,
    score_abstraction_quality,
)
from .normalize import build_constraint_signature, normalize_text


@dataclass
class DedupInput:
    """Input case for deduplication."""
    case_id: str
    module: str
    development_type: str
    issue_text: str
    rules: list[str]
    invariants: list[str]
    semantic_value: str = "medium"


@dataclass
class DedupGroup:
    """Group of duplicate cases with canonical selection."""
    dedup_key: str
    canonical_case_id: str
    duplicate_case_ids: list[str] = field(default_factory=list)


def build_dedup_key(case: DedupInput, *, use_constraint_signature: bool = False) -> str:
    """
    Build strict deduplication key.

    Key components:
    - module + development_type + normalized_issue_text (always)
    - constraint_signature (optional)

    Note: commit_log is NOT part of the key - same pattern applied to
    different objects/paths naturally has different commit_log.

    Args:
        case: Input case to generate key for
        use_constraint_signature: Include constraint signature in key

    Returns:
        SHA1 hash of normalized key components
    """
    parts = [
        normalize_text(case.module),
        normalize_text(case.development_type),
        normalize_text(case.issue_text, normalize_numbers=True),
    ]

    if use_constraint_signature:
        parts.append(build_constraint_signature(case.rules, case.invariants))

    raw = "||".join(parts)
    return _sha1(raw)


def group_strict_duplicates(
    cases: Iterable[DedupInput],
    *,
    use_constraint_signature: bool = False,
    use_model_optimization: bool = False,
    model_executor: Callable[[str], str] | None = None,
    model_config: ModelOptimizerConfig | None = None,
) -> list[DedupGroup]:
    """
    Group cases by strict deduplication key.

    Only returns groups with 2+ cases (actual duplicates).
    Single cases are not included in output.

    Args:
        cases: Input cases to deduplicate
        use_constraint_signature: Include constraint signature in dedup key
        use_model_optimization: Enable model-assisted semantic duplicate detection
        model_executor: Callable for model API calls (required if use_model_optimization=True)
        model_config: Configuration for model optimization

    Returns:
        List of duplicate groups with canonical case selected
    """
    # Phase 1: Rule-based pre-filter (efficiency)
    buckets: dict[str, list[DedupInput]] = {}

    for case in cases:
        key = build_dedup_key(case, use_constraint_signature=use_constraint_signature)
        buckets.setdefault(key, []).append(case)

    if not use_model_optimization:
        # Stop here if model disabled - use rule-based grouping only
        return _finalize_groups(buckets)

    # Phase 2: Model-driven gray zone resolution
    gray_pairs = _extract_gray_zone_pairs(buckets, model_config)

    if gray_pairs:
        # Phase 3: Model decides which pairs are semantic duplicates
        dup_results = check_semantic_duplicates(
            gray_pairs,
            executor=model_executor,
            config=model_config
        )

        # Phase 4: Apply model decisions (merge groups)
        buckets = _apply_semantic_merges(buckets, dup_results, model_config)

    return _finalize_groups(buckets)


def select_canonical_duplicate(
    cases: list[DedupInput],
    *,
    use_model_optimization: bool = False,
    model_executor: Callable[[str], str] | None = None,
    model_config: ModelOptimizerConfig | None = None,
) -> DedupInput:
    """
    Select canonical case from duplicate group.

    Selection criteria (in order):
    1. Higher semantic_value (high > medium > low)
    2. Model quality scoring (if enabled) OR clearer issue_text (moderate length preferred, ~18 chars)
    3. Stable case_id (for deterministic results)

    Args:
        cases: List of duplicate cases
        use_model_optimization: Enable model-assisted quality scoring
        model_executor: Callable for model API calls (required if use_model_optimization=True)
        model_config: Configuration for model optimization

    Returns:
        Selected canonical case
    """
    if not use_model_optimization:
        # Fallback to rule-based selection
        return _select_by_rules(cases)

    # Phase 1: Filter by semantic_value (keep only top tier)
    top_tier = _filter_by_semantic_value(cases)

    # Phase 2: Model scores abstraction quality for all candidates
    try:
        quality_scores = score_abstraction_quality(
            top_tier,
            executor=model_executor,
            config=model_config
        )

        # Phase 3: Select highest quality score
        best_idx = 0
        best_score = quality_scores[0].score
        for i, qs in enumerate(quality_scores):
            if qs.score > best_score:
                best_score = qs.score
                best_idx = i

        return top_tier[best_idx]

    except Exception:
        # Fallback to rule-based selection on model errors
        return _select_by_rules(cases)


def _sha1(text: str) -> str:
    """Generate SHA1 hash of text."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _finalize_groups(buckets: dict[str, list[DedupInput]]) -> list[DedupGroup]:
    """Convert buckets to DedupGroup list."""
    groups: list[DedupGroup] = []
    for key, bucket in buckets.items():
        if len(bucket) <= 1:
            continue
        canonical = select_canonical_duplicate(bucket)
        duplicate_ids = [c.case_id for c in bucket if c.case_id != canonical.case_id]
        groups.append(
            DedupGroup(
                dedup_key=key,
                canonical_case_id=canonical.case_id,
                duplicate_case_ids=duplicate_ids,
            )
        )
    return groups


def _extract_gray_zone_pairs(
    buckets: dict[str, list[DedupInput]],
    config: ModelOptimizerConfig | None = None
) -> list[tuple[DedupInput, DedupInput]]:
    """
    Extract gray zone pairs with similarity 0.40-0.60.

    Compares all pairs across different rule-based buckets.
    This is where model judgment is most valuable.

    Args:
        buckets: Rule-based dedup buckets
        config: Model optimizer config (for gray zone bounds)

    Returns:
        List of (case_a, case_b) tuples in gray zone
    """
    from .patterning import PatternInput, pair_similarity

    if config is None:
        config = ModelOptimizerConfig()

    gray_pairs: list[tuple[DedupInput, DedupInput]] = []
    bucket_list = list(buckets.values())

    # Compare across different buckets
    for i in range(len(bucket_list)):
        for j in range(i + 1, len(bucket_list)):
            bucket_a = bucket_list[i]
            bucket_b = bucket_list[j]

            # Compare all pairs between buckets
            for case_a in bucket_a:
                for case_b in bucket_b:
                    # Convert to PatternInput for similarity calculation
                    pattern_a = PatternInput(
                        case_id=case_a.case_id,
                        domain="",  # Not used in similarity
                        module=case_a.module,
                        development_type=case_a.development_type,
                        commit_log="",  # Not used in similarity
                        issue_text=case_a.issue_text,
                        rules=case_a.rules,
                        invariants=case_a.invariants,
                        semantic_value=case_a.semantic_value
                    )
                    pattern_b = PatternInput(
                        case_id=case_b.case_id,
                        domain="",
                        module=case_b.module,
                        development_type=case_b.development_type,
                        commit_log="",
                        issue_text=case_b.issue_text,
                        rules=case_b.rules,
                        invariants=case_b.invariants,
                        semantic_value=case_b.semantic_value
                    )

                    sim = pair_similarity(pattern_a, pattern_b)

                    # Check if in gray zone
                    if config.gray_zone_similarity_min <= sim <= config.gray_zone_similarity_max:
                        gray_pairs.append((case_a, case_b))

    return gray_pairs


def _apply_semantic_merges(
    buckets: dict[str, list[DedupInput]],
    dup_results: list,
    config: ModelOptimizerConfig | None = None
) -> dict[str, list[DedupInput]]:
    """
    Apply model decisions to merge groups.

    Only merge if model says "yes" AND confidence > threshold.

    Args:
        buckets: Original rule-based buckets
        dup_results: Semantic duplicate results from model
        config: Model optimizer config (for confidence threshold)

    Returns:
        Updated buckets with semantic merges applied
    """
    if config is None:
        config = ModelOptimizerConfig()

    # Build case_id -> bucket_key mapping
    case_to_bucket: dict[str, str] = {}
    for key, bucket in buckets.items():
        for case in bucket:
            case_to_bucket[case.case_id] = key

    # Build merge groups (union-find style)
    merge_map: dict[str, str] = {}  # bucket_key -> canonical_bucket_key

    def find_root(key: str) -> str:
        if key not in merge_map:
            return key
        root = find_root(merge_map[key])
        merge_map[key] = root  # Path compression
        return root

    # Process duplicate results
    for result in dup_results:
        if result.is_duplicate and result.confidence >= config.duplicate_confidence_threshold:
            # Merge the two buckets
            bucket_a = case_to_bucket.get(result.case_a_id)
            bucket_b = case_to_bucket.get(result.case_b_id)

            if bucket_a and bucket_b and bucket_a != bucket_b:
                root_a = find_root(bucket_a)
                root_b = find_root(bucket_b)

                if root_a != root_b:
                    # Merge b into a
                    merge_map[root_b] = root_a

    # Apply merges
    merged_buckets: dict[str, list[DedupInput]] = {}
    for key, bucket in buckets.items():
        root = find_root(key)
        if root not in merged_buckets:
            merged_buckets[root] = []
        merged_buckets[root].extend(bucket)

    return merged_buckets


def _select_by_rules(cases: list[DedupInput]) -> DedupInput:
    """
    Select canonical case using rule-based logic.

    Fallback when model optimization is disabled or fails.

    Args:
        cases: List of duplicate cases

    Returns:
        Selected canonical case
    """
    def score(case: DedupInput) -> tuple[int, int, str]:
        semantic_rank = {"high": 0, "medium": 1, "low": 2}.get(case.semantic_value, 1)
        length_penalty = abs(len(case.issue_text) - 18)  # Prefer moderate length
        return (semantic_rank, length_penalty, case.case_id)

    return sorted(cases, key=score)[0]


def _filter_by_semantic_value(cases: list[DedupInput]) -> list[DedupInput]:
    """
    Filter cases to keep only top semantic_value tier.

    Args:
        cases: List of cases

    Returns:
        Cases with highest semantic_value
    """
    # Find highest semantic value
    value_rank = {"high": 0, "medium": 1, "low": 2}
    best_rank = min(value_rank.get(c.semantic_value, 1) for c in cases)

    # Filter to keep only best tier
    return [c for c in cases if value_rank.get(c.semantic_value, 1) == best_rank]
