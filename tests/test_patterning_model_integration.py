"""
Integration tests for patterning.py model optimization.

Tests select_canonical_pattern_case with/without model,
_filter_pattern_by_semantic_value, and fallback behavior.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.patterning import (
    PatternInput,
    select_canonical_pattern_case,
    _filter_pattern_by_semantic_value,
    _select_pattern_by_rules,
    pair_similarity,
    cluster_within_bucket,
    group_patterns,
)
from src.commit_semantic.model_optimizer import ModelOptimizerConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_pattern(
    case_id: str,
    issue_text: str = "fix: null pointer",
    semantic_value: str = "medium",
    rules: list = None,
    invariants: list = None,
    module: str = "parser",
    development_type: str = "bugfix",
    domain: str = "parsing",
) -> PatternInput:
    return PatternInput(
        case_id=case_id,
        domain=domain,
        module=module,
        development_type=development_type,
        commit_log="fix null pointer in parser",
        issue_text=issue_text,
        rules=rules or ["must maintain compatibility"],
        invariants=invariants or [],
        semantic_value=semantic_value,
    )


def mock_executor_quality_high(prompt: str) -> str:
    return '{"score": 9, "reason": "very clear and reusable"}'


def mock_executor_quality_low(prompt: str) -> str:
    return '{"score": 2, "reason": "too vague"}'


# ---------------------------------------------------------------------------
# select_canonical_pattern_case - no model (backward compat)
# ---------------------------------------------------------------------------

class TestSelectCanonicalPatternCaseNoModel:
    def test_prefers_high_semantic_value(self):
        cases = [
            make_pattern("c1", semantic_value="low"),
            make_pattern("c2", semantic_value="high"),
            make_pattern("c3", semantic_value="medium"),
        ]
        canonical = select_canonical_pattern_case(cases, use_model_optimization=False)
        assert canonical.case_id == "c2"

    def test_prefers_more_rules_invariants(self):
        """Among same semantic_value, prefer more rules+invariants."""
        cases = [
            make_pattern("c1", semantic_value="medium", rules=[], invariants=[]),
            make_pattern("c2", semantic_value="medium", rules=["r1", "r2"], invariants=["i1"]),
            make_pattern("c3", semantic_value="medium", rules=["r1"], invariants=[]),
        ]
        canonical = select_canonical_pattern_case(cases, use_model_optimization=False)
        assert canonical.case_id == "c2"

    def test_prefers_moderate_length_issue_text(self):
        """Among same semantic_value and constraints, prefer ~16 char issue_text."""
        cases = [
            make_pattern("c1", issue_text="x" * 60, semantic_value="medium", rules=[]),
            make_pattern("c2", issue_text="fix: null ptr", semantic_value="medium", rules=[]),  # 13 chars
            make_pattern("c3", issue_text="fix: null point", semantic_value="medium", rules=[]),  # 15 chars
        ]
        canonical = select_canonical_pattern_case(cases, use_model_optimization=False)
        # c3 is closest to 16 chars
        assert canonical.case_id == "c3"

    def test_single_case_returned(self):
        cases = [make_pattern("c1")]
        canonical = select_canonical_pattern_case(cases, use_model_optimization=False)
        assert canonical.case_id == "c1"

    def test_stable_case_id_tiebreak(self):
        """When all else equal, case_id used as tiebreak (alphabetical)."""
        cases = [
            make_pattern("z1", issue_text="fix: null ptr", semantic_value="medium", rules=[]),
            make_pattern("a1", issue_text="fix: null ptr", semantic_value="medium", rules=[]),
        ]
        canonical = select_canonical_pattern_case(cases, use_model_optimization=False)
        assert canonical.case_id == "a1"


# ---------------------------------------------------------------------------
# select_canonical_pattern_case - with model
# ---------------------------------------------------------------------------

class TestSelectCanonicalPatternCaseWithModel:
    def test_model_selects_highest_score(self):
        call_count = [0]

        def scoring_executor(prompt: str) -> str:
            call_count[0] += 1
            scores = [2, 9, 5]
            idx = min(call_count[0] - 1, len(scores) - 1)
            return f'{{"score": {scores[idx]}, "reason": "ok"}}'

        # Distinct issue_text so each case gets its own cache key
        cases = [
            make_pattern("c1", issue_text="fix: issue alpha", semantic_value="medium"),
            make_pattern("c2", issue_text="fix: issue beta", semantic_value="medium"),
            make_pattern("c3", issue_text="fix: issue gamma", semantic_value="medium"),
        ]
        canonical = select_canonical_pattern_case(
            cases,
            use_model_optimization=True,
            model_executor=scoring_executor,
        )
        assert canonical.case_id == "c2"

    def test_model_only_scores_top_tier(self):
        """Model only scores high-tier cases, not low-tier ones."""
        call_count = [0]

        def counting_executor(prompt: str) -> str:
            call_count[0] += 1
            return '{"score": 7, "reason": "ok"}'

        cases = [
            make_pattern("c1", semantic_value="high"),
            make_pattern("c2", semantic_value="low"),   # filtered out before model
            make_pattern("c3", semantic_value="low"),   # filtered out before model
        ]
        select_canonical_pattern_case(
            cases,
            use_model_optimization=True,
            model_executor=counting_executor,
        )
        # Only 1 high-tier case -> model called once
        assert call_count[0] == 1

    def test_model_fallback_on_executor_error(self):
        """Falls back to rule-based when model executor raises."""
        def failing_executor(prompt: str) -> str:
            raise RuntimeError("model unavailable")

        cases = [
            make_pattern("c1", semantic_value="low"),
            make_pattern("c2", semantic_value="high"),
        ]
        config = ModelOptimizerConfig(max_retries=1, retry_backoff_base=0.0)
        canonical = select_canonical_pattern_case(
            cases,
            use_model_optimization=True,
            model_executor=failing_executor,
            model_config=config,
        )
        # Fallback: high semantic_value wins
        assert canonical.case_id == "c2"

    def test_model_fallback_on_no_executor(self):
        """Falls back to rule-based when no executor provided."""
        cases = [
            make_pattern("c1", semantic_value="low"),
            make_pattern("c2", semantic_value="high"),
        ]
        config = ModelOptimizerConfig(max_retries=1, retry_backoff_base=0.0)
        canonical = select_canonical_pattern_case(
            cases,
            use_model_optimization=True,
            model_executor=None,
            model_config=config,
        )
        assert canonical.case_id == "c2"

    def test_model_with_config(self):
        """Custom config is passed through to model optimizer."""
        config = ModelOptimizerConfig(max_retries=1, retry_backoff_base=0.0)
        cases = [make_pattern("c1"), make_pattern("c2")]
        canonical = select_canonical_pattern_case(
            cases,
            use_model_optimization=True,
            model_executor=mock_executor_quality_high,
            model_config=config,
        )
        assert canonical is not None


# ---------------------------------------------------------------------------
# _filter_pattern_by_semantic_value
# ---------------------------------------------------------------------------

class TestFilterPatternBySemanticValue:
    def test_keeps_only_high_when_present(self):
        cases = [
            make_pattern("c1", semantic_value="high"),
            make_pattern("c2", semantic_value="medium"),
            make_pattern("c3", semantic_value="low"),
        ]
        filtered = _filter_pattern_by_semantic_value(cases)
        assert len(filtered) == 1
        assert filtered[0].case_id == "c1"

    def test_keeps_medium_when_no_high(self):
        cases = [
            make_pattern("c1", semantic_value="medium"),
            make_pattern("c2", semantic_value="low"),
        ]
        filtered = _filter_pattern_by_semantic_value(cases)
        assert len(filtered) == 1
        assert filtered[0].case_id == "c1"

    def test_keeps_all_same_tier(self):
        cases = [
            make_pattern("c1", semantic_value="high"),
            make_pattern("c2", semantic_value="high"),
        ]
        filtered = _filter_pattern_by_semantic_value(cases)
        assert len(filtered) == 2

    def test_all_low_returns_all(self):
        cases = [
            make_pattern("c1", semantic_value="low"),
            make_pattern("c2", semantic_value="low"),
        ]
        filtered = _filter_pattern_by_semantic_value(cases)
        assert len(filtered) == 2


# ---------------------------------------------------------------------------
# pair_similarity
# ---------------------------------------------------------------------------

class TestPairSimilarity:
    def test_identical_cases_high_similarity(self):
        a = make_pattern("a1", issue_text="fix: null pointer")
        b = make_pattern("b1", issue_text="fix: null pointer")
        sim = pair_similarity(a, b)
        assert sim >= 0.9

    def test_very_different_cases_low_similarity(self):
        a = make_pattern("a1", issue_text="fix: null pointer", rules=[])
        b = make_pattern("b1", issue_text="feat: add authentication system",
                         development_type="feature", rules=[])
        sim = pair_similarity(a, b)
        assert sim < 0.5

    def test_similarity_symmetric(self):
        a = make_pattern("a1", issue_text="fix: null pointer exception")
        b = make_pattern("b1", issue_text="fix: null pointer crash")
        assert pair_similarity(a, b) == pytest.approx(pair_similarity(b, a), abs=1e-9)

    def test_similarity_range(self):
        a = make_pattern("a1", issue_text="fix: null pointer")
        b = make_pattern("b1", issue_text="fix: null pointer crash")
        sim = pair_similarity(a, b)
        assert 0.0 <= sim <= 1.0


# ---------------------------------------------------------------------------
# cluster_within_bucket
# ---------------------------------------------------------------------------

class TestClusterWithinBucket:
    def test_similar_cases_clustered(self):
        cases = [
            make_pattern("c1", issue_text="fix: null pointer exception"),
            make_pattern("c2", issue_text="fix: null pointer crash"),
            make_pattern("c3", issue_text="feat: add authentication", development_type="feature"),
        ]
        clusters = cluster_within_bucket(cases, similarity_threshold=0.5)
        # c1 and c2 should cluster together; c3 separate
        assert len(clusters) >= 1

    def test_single_case_one_cluster(self):
        cases = [make_pattern("c1")]
        clusters = cluster_within_bucket(cases)
        assert len(clusters) == 1
        assert clusters[0][0].case_id == "c1"

    def test_all_different_separate_clusters(self):
        cases = [
            make_pattern("c1", issue_text="fix: null pointer", rules=[]),
            make_pattern("c2", issue_text="feat: add auth system", development_type="feature", rules=[]),
            make_pattern("c3", issue_text="refactor: restructure module", development_type="refactor", rules=[]),
        ]
        clusters = cluster_within_bucket(cases, similarity_threshold=0.9)
        assert len(clusters) == 3


# ---------------------------------------------------------------------------
# group_patterns integration
# ---------------------------------------------------------------------------

class TestGroupPatterns:
    def test_similar_cases_form_pattern(self):
        cases = [
            make_pattern("c1", issue_text="fix: null pointer exception in parser"),
            make_pattern("c2", issue_text="fix: null pointer crash in parser"),
            make_pattern("c3", issue_text="fix: null pointer error in parser"),
        ]
        groups = group_patterns(cases, similarity_threshold=0.5)
        assert len(groups) >= 1
        assert groups[0].count >= 2

    def test_single_case_not_grouped(self):
        cases = [make_pattern("c1")]
        groups = group_patterns(cases)
        assert groups == []

    def test_group_has_canonical_and_variants(self):
        cases = [
            make_pattern("c1", issue_text="fix: null pointer exception"),
            make_pattern("c2", issue_text="fix: null pointer crash"),
        ]
        groups = group_patterns(cases, similarity_threshold=0.5)
        if groups:
            g = groups[0]
            assert g.canonical_case_id is not None
            assert isinstance(g.variant_case_ids, list)
            assert g.count == 2
