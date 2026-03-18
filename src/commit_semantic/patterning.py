"""
Pattern extraction with domain-aware aggregation.

Groups similar cases into patterns using:
- High-level pattern fingerprinting (domain|dev_type|action|object|constraint)
- In-bucket similarity comparison (Jaccard + SequenceMatcher)
- Pattern count control (<10 excellent, 10-20 acceptable, >20 too high)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Iterable, Optional, Callable

from .normalize import build_constraint_signature, normalize_text
from .model_optimizer import score_abstraction_quality, ModelOptimizerConfig
from .dedup import DedupInput


@dataclass
class PatternInput:
    """Input case for pattern extraction."""
    case_id: str
    domain: str
    module: str
    development_type: str
    commit_log: str
    issue_text: str
    rules: list[str]
    invariants: list[str]
    semantic_value: str = "medium"


@dataclass
class PatternGroup:
    """Group of similar cases forming a pattern."""
    pattern_id: str
    pattern_fingerprint: str
    domain: str
    canonical_case_id: str
    variant_case_ids: list[str]
    count: int
    representative_issue_text: str
    representative_rules: list[str]
    representative_invariants: list[str]
    development_type: str = ""
    action_class: str = ""
    object_class: str = ""
    constraint_class: str = ""


@dataclass
class PatternCheckResult:
    """Pattern count check result for a domain."""
    domain: str
    pattern_count: int
    pattern_count_status: str
    action: str


def build_pattern_fingerprint(case: PatternInput) -> str:
    """
    Build high-level pattern fingerprint.

    Format: domain|dev_type|action_class|object_class|constraint_class

    Note: Does NOT depend on commit_log being identical.
    Same pattern can apply to different objects/paths.

    Args:
        case: Input case to generate fingerprint for

    Returns:
        Pattern fingerprint string
    """
    action_class = infer_action_class(case.issue_text, case.development_type)
    object_class = infer_object_class(case.issue_text, case.commit_log, case.rules, case.invariants)
    constraint_class = infer_constraint_class(case.rules, case.invariants)
    return "|".join(
        [
            normalize_text(case.domain),
            normalize_text(case.development_type),
            action_class,
            object_class,
            constraint_class,
        ]
    )


def group_patterns(
    cases: Iterable[PatternInput],
    *,
    similarity_threshold: float = 0.50,
    use_model_optimization: bool = False,
    model_executor: Optional[Callable[[str], str]] = None,
    model_config: Optional[ModelOptimizerConfig] = None,
) -> list[PatternGroup]:
    """
    Group cases into patterns.

    Process:
    1. Bucket by pattern fingerprint
    2. Within each bucket, cluster by similarity
    3. Select canonical case for each cluster
    4. Generate pattern groups

    Args:
        cases: Input cases to group
        similarity_threshold: Minimum similarity for grouping (default 0.50)
        use_model_optimization: Enable model-assisted canonical selection
        model_executor: Callable for model API calls (required if use_model_optimization=True)
        model_config: Configuration for model optimization

    Returns:
        List of pattern groups
    """
    # Bucket by fingerprint
    buckets: dict[str, list[PatternInput]] = {}
    for case in cases:
        fp = build_pattern_fingerprint(case)
        buckets.setdefault(fp, []).append(case)

    groups: list[PatternGroup] = []
    pattern_seq = 1

    for fingerprint, bucket in buckets.items():
        # Skip if only 1 case (not a pattern)
        if len(bucket) < 2:
            continue

        # Cluster within bucket by similarity
        clustered = cluster_within_bucket(bucket, similarity_threshold=similarity_threshold)

        for cluster in clustered:
            # Skip if cluster has only 1 case
            if len(cluster) < 2:
                continue

            canonical = select_canonical_pattern_case(
                cluster,
                use_model_optimization=use_model_optimization,
                model_executor=model_executor,
                model_config=model_config,
            )

            # Extract domain from canonical case
            domain = canonical.domain

            # Parse fingerprint components
            fp_parts = fingerprint.split("|")
            dev_type = fp_parts[1] if len(fp_parts) > 1 else ""
            action_class = fp_parts[2] if len(fp_parts) > 2 else ""
            object_class = fp_parts[3] if len(fp_parts) > 3 else ""
            constraint_class = fp_parts[4] if len(fp_parts) > 4 else ""

            group = PatternGroup(
                pattern_id=f"{fingerprint}#{pattern_seq:03d}",
                pattern_fingerprint=fingerprint,
                domain=domain,
                canonical_case_id=canonical.case_id,
                variant_case_ids=[c.case_id for c in cluster if c.case_id != canonical.case_id],
                count=len(cluster),
                representative_issue_text=canonical.issue_text,
                representative_rules=canonical.rules,
                representative_invariants=canonical.invariants,
                development_type=dev_type,
                action_class=action_class,
                object_class=object_class,
                constraint_class=constraint_class,
            )
            groups.append(group)
            pattern_seq += 1

    return groups


def cluster_within_bucket(
    cases: list[PatternInput],
    *,
    similarity_threshold: float = 0.50,
) -> list[list[PatternInput]]:
    """
    Cluster cases within same fingerprint bucket by similarity.

    Uses greedy clustering:
    - Compare with first case in each cluster (anchor)
    - Use issue_text as primary, constraint_signature as secondary
    - Threshold tuned for Chinese text (0.50 default)

    Args:
        cases: Cases in same fingerprint bucket
        similarity_threshold: Minimum similarity for clustering

    Returns:
        List of clusters (each cluster is a list of cases)
    """
    clusters: list[list[PatternInput]] = []

    for case in cases:
        placed = False
        for cluster in clusters:
            anchor = cluster[0]
            sim = pair_similarity(anchor, case)
            if sim >= similarity_threshold:
                cluster.append(case)
                placed = True
                break
        if not placed:
            clusters.append([case])

    return clusters


def pair_similarity(a: PatternInput, b: PatternInput) -> float:
    """
    Calculate similarity between two cases.

    Formula: 0.5*sequence + 0.3*jaccard + 0.2*constraint
    - issue_text dominates (0.5 + 0.3 = 0.8)
    - constraint assists (0.2)

    Args:
        a: First case
        b: Second case

    Returns:
        Similarity score [0.0, 1.0]
    """
    issue_a = normalize_text(a.issue_text, normalize_numbers=True)
    issue_b = normalize_text(b.issue_text, normalize_numbers=True)

    rule_a = build_constraint_signature(a.rules, a.invariants)
    rule_b = build_constraint_signature(b.rules, b.invariants)

    s1 = _sequence_ratio(issue_a, issue_b)
    s2 = _jaccard(issue_a, issue_b)
    s3 = _sequence_ratio(rule_a, rule_b) if rule_a or rule_b else 0.5

    # Issue dominates, constraint assists
    return 0.5 * s1 + 0.3 * s2 + 0.2 * s3


def select_canonical_pattern_case(
    cases: list[PatternInput],
    *,
    use_model_optimization: bool = False,
    model_executor: Optional[Callable[[str], str]] = None,
    model_config: Optional[ModelOptimizerConfig] = None,
) -> PatternInput:
    """
    Select canonical case for pattern.

    Selection criteria (in order):
    1. Higher semantic_value
    2. Model quality scoring (if enabled) OR more abstract but not vague issue_text (~16 chars preferred)
    3. More stable rules/invariants (more is better)
    4. Stable case_id

    Args:
        cases: Cases in pattern cluster
        use_model_optimization: Enable model-assisted quality scoring
        model_executor: Callable for model API calls (required if use_model_optimization=True)
        model_config: Configuration for model optimization

    Returns:
        Selected canonical case
    """
    if not use_model_optimization:
        # Fallback to rule-based selection
        return _select_pattern_by_rules(cases)

    # Phase 1: Filter by semantic_value (keep only top tier)
    top_tier = _filter_pattern_by_semantic_value(cases)

    # Phase 2: Model scores abstraction quality for all candidates
    try:
        # Convert PatternInput to DedupInput for model scoring
        dedup_cases = [
            DedupInput(
                case_id=c.case_id,
                module=c.module,
                development_type=c.development_type,
                issue_text=c.issue_text,
                rules=c.rules,
                invariants=c.invariants,
                semantic_value=c.semantic_value
            )
            for c in top_tier
        ]

        quality_scores = score_abstraction_quality(
            dedup_cases,
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
        return _select_pattern_by_rules(cases)


def check_pattern_count(groups: list[PatternGroup], domain: str) -> PatternCheckResult:
    """
    Check pattern count for a domain and generate alert if needed.

    Thresholds:
    - <10: excellent (good)
    - 10-20: acceptable (observe)
    - 21-30: too_high (review abstraction)
    - >30: critical (review abstraction and dedup)

    Args:
        groups: Pattern groups for the domain
        domain: Domain name

    Returns:
        Pattern count check result with status and action
    """
    count = len(groups)
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
        action = "review_pattern_abstraction_and_dedup"

    return PatternCheckResult(
        domain=domain,
        pattern_count=count,
        pattern_count_status=status,
        action=action,
    )


def infer_action_class(issue_text: str, development_type: str) -> str:
    """
    Infer high-level action class from issue_text and development_type.

    Categories: fix, add, refactor, migrate, optimize, control, align

    Args:
        issue_text: Issue text
        development_type: Development type (bugfix, feature, etc.)

    Returns:
        Action class string
    """
    text = normalize_text(issue_text)

    # Check specific actions first (before generic feature/add)
    if development_type == "bugfix" or "bugfix" in text or "修复" in text or "fix" in text:
        return "fix"
    if development_type == "refactor" or "重构" in text or "refactor" in text:
        return "refactor"
    if development_type == "migration" or "迁移" in text or "migrate" in text:
        return "migrate"
    if development_type == "optimize" or "优化" in text or "调整" in text or "optimize" in text:
        return "optimize"
    if "control" in text or "控制" in text:
        return "control"
    if "align" in text or "对齐" in text:
        return "align"

    # Generic feature/add check last
    if development_type == "feature" or "新增" in text or "add" in text or "添加" in text:
        return "add"

    return "general"


def infer_object_class(issue_text: str, commit_log: str, rules: list[str], invariants: list[str]) -> str:
    """
    Infer high-level object class from all available text.

    Keep categories broad (<15) to prevent pattern explosion.

    Categories:
    - parser
    - request-response-alignment
    - feature-extraction
    - config-control
    - registry
    - compatibility-path
    - concurrency-control
    - demand-analysis
    - semantic-processing

    Args:
        issue_text: Issue text
        commit_log: Commit log
        rules: Rules list
        invariants: Invariants list

    Returns:
        Object class string
    """
    text = " ".join([issue_text, commit_log, " ".join(rules), " ".join(invariants)])
    text = normalize_text(text)

    if any(k in text for k in ["parser", "dsl", "parse", "解析"]):
        return "parser"
    if any(k in text for k in ["qserver", "request", "response", "score", "item", "打分", "alignment", "对齐"]):
        return "request-response-alignment"
    if any(k in text for k in ["feature", "extract", "worker", "特征抽取", "特征"]):
        return "feature-extraction"
    if any(k in text for k in ["config", "flag", "配置", "开关", "control"]):
        return "config-control"
    if any(k in text for k in ["registry", "register", "注册"]):
        return "registry"
    if any(k in text for k in ["compatibility", "legacy", "兼容"]):
        return "compatibility-path"
    if any(k in text for k in ["concurrency", "thread", "worker count", "并发", "线程"]):
        return "concurrency-control"
    if any(k in text for k in ["demand", "需求", "requirement"]):
        return "demand-analysis"
    if any(k in text for k in ["semantic", "语义"]):
        return "semantic-processing"

    return "general"


def infer_constraint_class(rules: list[str], invariants: list[str]) -> str:
    """
    Infer constraint class from rules and invariants.

    Returns sorted constraint categories joined with '+'.

    Categories:
    - compatibility
    - alignment
    - concurrency
    - mapping
    - contract
    - migration
    - boundedness
    - validation

    Args:
        rules: Rules list
        invariants: Invariants list

    Returns:
        Constraint class string (may be multiple joined with '+')
    """
    if not rules and not invariants:
        return "none"

    text = normalize_text(" ".join(rules + invariants))

    categories = set()

    if any(k in text for k in ["compatibility", "legacy", "parseable", "兼容", "backward"]):
        categories.add("compatibility")
    if any(k in text for k in ["aligned", "alignment", "对齐", "consistency", "sync"]):
        categories.add("alignment")
    if any(k in text for k in ["concurrency", "worker", "bounded", "thread", "并发"]):
        categories.add("concurrency")
    if any(k in text for k in ["mapping", "schema", "映射", "map"]):
        categories.add("mapping")
    if any(k in text for k in ["contract", "abstraction", "契约", "interface"]):
        categories.add("contract")
    if any(k in text for k in ["migration", "transition", "迁移", "migrate"]):
        categories.add("migration")
    if any(k in text for k in ["boundary", "bound", "limit", "边界"]):
        categories.add("boundedness")
    if any(k in text for k in ["validation", "check", "验证", "validate"]):
        categories.add("validation")

    if not categories:
        return "general"

    return "+".join(sorted(categories))


def _sequence_ratio(a: str, b: str) -> float:
    """Calculate sequence similarity ratio."""
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b).ratio()


def _jaccard(a: str, b: str) -> float:
    """Calculate Jaccard similarity of word sets."""
    sa = set(a.split())
    sb = set(b.split())
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _select_pattern_by_rules(cases: list[PatternInput]) -> PatternInput:
    """
    Select canonical case using rule-based logic.

    Fallback when model optimization is disabled or fails.

    Args:
        cases: Cases in pattern cluster

    Returns:
        Selected canonical case
    """
    def score(case: PatternInput) -> tuple[int, int, int, str]:
        semantic_rank = {"high": 0, "medium": 1, "low": 2}.get(case.semantic_value, 1)
        issue_penalty = abs(len(case.issue_text) - 16)
        constraint_penalty = -(len(case.rules) + len(case.invariants))  # More is better
        return (semantic_rank, issue_penalty, constraint_penalty, case.case_id)

    return sorted(cases, key=score)[0]


def _filter_pattern_by_semantic_value(cases: list[PatternInput]) -> list[PatternInput]:
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
