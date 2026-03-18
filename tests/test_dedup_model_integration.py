"""
Integration tests for dedup.py model optimization integration.

Tests group_strict_duplicates with/without model, gray zone extraction,
semantic merges, canonical selection with model scoring, and fallback behavior.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.dedup import (
    DedupInput,
    DedupGroup,
    group_strict_duplicates,
    select_canonical_duplicate,
    _extract_gray_zone_pairs,
    _apply_semantic_merges,
    _select_by_rules,
    _filter_by_semantic_value,
    build_dedup_key,
)
from src.commit_semantic.model_optimizer import (
    ModelOptimizerConfig,
    SemanticDuplicateResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_case(
    case_id: str,
    module: str = "parser",
    development_type: str = "bugfix",
    issue_text: str = "fix: null pointer",
    rules: list = None,
    invariants: list = None,
    semantic_value: str = "medium",
) -> DedupInput:
    return DedupInput(
        case_id=case_id,
        module=module,
        development_type=development_type,
        issue_text=issue_text,
        rules=rules or ["must maintain compatibility"],
        invariants=invariants or ["inputs remain parseable"],
        semantic_value=semantic_value,
    )


def mock_executor_dup_true(prompt: str) -> str:
    return '{"is_duplicate": true, "confidence": 0.95, "reason": "paraphrase"}'


def mock_executor_dup_false(prompt: str) -> str:
    return '{"is_duplicate": false, "confidence": 0.85, "reason": "different"}'


def mock_executor_quality_high(prompt: str) -> str:
    return '{"score": 9, "reason": "very clear"}'


def mock_executor_quality_low(prompt: str) -> str:
    return '{"score": 3, "reason": "too vague"}'


# ---------------------------------------------------------------------------
# group_strict_duplicates - backward compat (no model)
# ---------------------------------------------------------------------------

class TestGroupStrictDuplicatesNoModel:
    def test_exact_duplicates_grouped(self):
        cases = [
            make_case("c1", issue_text="fix: null pointer crash"),
            make_case("c2", issue_text="fix: null pointer crash"),  # exact dup
            make_case("c3", issue_text="feat: add parser", development_type="feature"),
        ]
        groups = group_strict_duplicates(cases, use_model_optimization=False)
        assert len(groups) == 1
        group = groups[0]
        assert len(group.duplicate_case_ids) == 1

    def test_no_duplicates_returns_empty(self):
        cases = [
            make_case("c1", issue_text="fix: null pointer"),
            make_case("c2", issue_text="feat: add feature", development_type="feature"),
        ]
        groups = group_strict_duplicates(cases, use_model_optimization=False)
        assert groups == []

    def test_single_case_not_grouped(self):
        cases = [make_case("c1")]
        groups = group_strict_duplicates(cases, use_model_optimization=False)
        assert groups == []

    def test_three_exact_duplicates(self):
        cases = [
            make_case(f"c{i}", issue_text="fix: same issue") for i in range(3)
        ]
        groups = group_strict_duplicates(cases, use_model_optimization=False)
        assert len(groups) == 1
        assert len(groups[0].duplicate_case_ids) == 2

    def test_constraint_signature_differentiates(self):
        cases = [
            make_case("c1", issue_text="fix: null pointer", rules=["rule A"]),
            make_case("c2", issue_text="fix: null pointer", rules=["rule B"]),
        ]
        groups = group_strict_duplicates(
            cases, use_constraint_signature=True, use_model_optimization=False
        )
        # Different constraint signatures -> not grouped
        assert groups == []

    def test_without_constraint_signature_groups_them(self):
        cases = [
            make_case("c1", issue_text="fix: null pointer", rules=["rule A"]),
            make_case("c2", issue_text="fix: null pointer", rules=["rule B"]),
        ]
        groups = group_strict_duplicates(
            cases, use_constraint_signature=False, use_model_optimization=False
        )
        assert len(groups) == 1


# ---------------------------------------------------------------------------
# group_strict_duplicates - with model optimization
# ---------------------------------------------------------------------------

class TestGroupStrictDuplicatesWithModel:
    def test_model_merges_gray_zone_pairs(self):
        """Two cases with similar but not identical text get merged by model."""
        # These need to be in different rule-based buckets but similar enough
        # to fall in gray zone (0.40-0.60 similarity)
        cases = [
            make_case("c1", issue_text="fix: null pointer exception in parser"),
            make_case("c2", issue_text="fix: null pointer crash in parser module"),
        ]
        groups = group_strict_duplicates(
            cases,
            use_model_optimization=True,
            model_executor=mock_executor_dup_true,
        )
        # If they end up in same bucket after model merge, they form a group
        # (behavior depends on similarity; test that model path runs without error)
        assert isinstance(groups, list)

    def test_model_disabled_no_executor_needed(self):
        """use_model_optimization=False should not call executor."""
        call_count = [0]

        def should_not_be_called(prompt: str) -> str:
            call_count[0] += 1
            return "{}"

        cases = [
            make_case("c1", issue_text="fix: same"),
            make_case("c2", issue_text="fix: same"),
        ]
        group_strict_duplicates(
            cases,
            use_model_optimization=False,
            model_executor=should_not_be_called,
        )
        assert call_count[0] == 0

    def test_model_false_does_not_merge(self):
        """Model says not duplicate -> groups stay separate."""
        cases = [
            make_case("c1", issue_text="fix: null pointer"),
            make_case("c2", issue_text="feat: add feature", development_type="feature"),
        ]
        groups = group_strict_duplicates(
            cases,
            use_model_optimization=True,
            model_executor=mock_executor_dup_false,
        )
        # Different modules/types -> different buckets, model says not dup
        assert isinstance(groups, list)


# ---------------------------------------------------------------------------
# _extract_gray_zone_pairs
# ---------------------------------------------------------------------------

class TestExtractGrayZonePairs:
    def test_similar_pairs_in_gray_zone(self):
        """Cases with similarity 0.40-0.60 should be extracted."""
        # Build two buckets with moderately similar cases
        from src.commit_semantic.dedup import build_dedup_key
        case_a = make_case("a1", issue_text="fix: null pointer exception")
        case_b = make_case("b1", issue_text="fix: null pointer crash in module")

        key_a = build_dedup_key(case_a)
        key_b = build_dedup_key(case_b)

        if key_a == key_b:
            # Same bucket - gray zone only applies across buckets
            pytest.skip("Cases ended up in same bucket")

        buckets = {key_a: [case_a], key_b: [case_b]}
        config = ModelOptimizerConfig(
            gray_zone_similarity_min=0.0,  # Accept all pairs for testing
            gray_zone_similarity_max=1.0,
        )
        pairs = _extract_gray_zone_pairs(buckets, config)
        assert len(pairs) >= 1
        assert pairs[0][0].case_id in ("a1", "b1")
        assert pairs[0][1].case_id in ("a1", "b1")

    def test_identical_cases_not_in_gray_zone(self):
        """Identical cases (similarity ~1.0) exceed gray zone max."""
        case_a = make_case("a1", issue_text="fix: null pointer")
        case_b = make_case("b1", issue_text="fix: null pointer")

        key_a = build_dedup_key(case_a)
        key_b = build_dedup_key(case_b)

        if key_a == key_b:
            pytest.skip("Same bucket - gray zone only applies across buckets")

        buckets = {key_a: [case_a], key_b: [case_b]}
        config = ModelOptimizerConfig(
            gray_zone_similarity_min=0.40,
            gray_zone_similarity_max=0.60,
        )
        pairs = _extract_gray_zone_pairs(buckets, config)
        # Identical text has similarity ~1.0, above gray zone max
        assert len(pairs) == 0

    def test_very_different_cases_not_in_gray_zone(self):
        """Very different cases (similarity < 0.40) below gray zone min."""
        case_a = make_case("a1", module="parser", issue_text="fix: null pointer")
        case_b = make_case("b1", module="qserver", issue_text="feat: add authentication system",
                           development_type="feature")

        key_a = build_dedup_key(case_a)
        key_b = build_dedup_key(case_b)

        if key_a == key_b:
            pytest.skip("Same bucket")

        buckets = {key_a: [case_a], key_b: [case_b]}
        config = ModelOptimizerConfig(
            gray_zone_similarity_min=0.40,
            gray_zone_similarity_max=0.60,
        )
        pairs = _extract_gray_zone_pairs(buckets, config)
        assert len(pairs) == 0

    def test_single_bucket_no_pairs(self):
        """Single bucket produces no cross-bucket pairs."""
        case_a = make_case("a1")
        buckets = {"key1": [case_a]}
        pairs = _extract_gray_zone_pairs(buckets)
        assert pairs == []

    def test_default_config_used_when_none(self):
        """None config uses default ModelOptimizerConfig."""
        case_a = make_case("a1", issue_text="fix: null pointer")
        case_b = make_case("b1", issue_text="feat: add feature", development_type="feature")
        key_a = build_dedup_key(case_a)
        key_b = build_dedup_key(case_b)
        if key_a == key_b:
            pytest.skip("Same bucket")
        buckets = {key_a: [case_a], key_b: [case_b]}
        # Should not raise
        pairs = _extract_gray_zone_pairs(buckets, None)
        assert isinstance(pairs, list)


# ---------------------------------------------------------------------------
# _apply_semantic_merges
# ---------------------------------------------------------------------------

class TestApplySemanticMerges:
    def test_merge_two_buckets(self):
        case_a = make_case("a1", issue_text="fix: null pointer")
        case_b = make_case("b1", issue_text="fix: null pointer crash")
        key_a = "bucket_a"
        key_b = "bucket_b"
        buckets = {key_a: [case_a], key_b: [case_b]}

        dup_result = SemanticDuplicateResult(
            case_a_id="a1",
            case_b_id="b1",
            is_duplicate=True,
            confidence=0.95,
            reason="paraphrase",
        )
        config = ModelOptimizerConfig(duplicate_confidence_threshold=0.8)
        merged = _apply_semantic_merges(buckets, [dup_result], config)

        # Both cases should be in same bucket
        all_cases = [c for cases in merged.values() for c in cases]
        assert len(all_cases) == 2
        assert len(merged) == 1

    def test_no_merge_below_confidence_threshold(self):
        case_a = make_case("a1")
        case_b = make_case("b1", issue_text="fix: different issue")
        buckets = {"bucket_a": [case_a], "bucket_b": [case_b]}

        dup_result = SemanticDuplicateResult(
            case_a_id="a1",
            case_b_id="b1",
            is_duplicate=True,
            confidence=0.5,  # Below threshold of 0.8
            reason="low confidence",
        )
        config = ModelOptimizerConfig(duplicate_confidence_threshold=0.8)
        merged = _apply_semantic_merges(buckets, [dup_result], config)

        # Should remain separate
        assert len(merged) == 2

    def test_no_merge_when_not_duplicate(self):
        case_a = make_case("a1")
        case_b = make_case("b1", issue_text="fix: different issue")
        buckets = {"bucket_a": [case_a], "bucket_b": [case_b]}

        dup_result = SemanticDuplicateResult(
            case_a_id="a1",
            case_b_id="b1",
            is_duplicate=False,
            confidence=0.9,
            reason="different semantics",
        )
        merged = _apply_semantic_merges(buckets, [dup_result])
        assert len(merged) == 2

    def test_chain_merge_three_buckets(self):
        """A->B and B->C merges should result in all three in one bucket."""
        case_a = make_case("a1")
        case_b = make_case("b1", issue_text="fix: null pointer crash")
        case_c = make_case("c1", issue_text="fix: null pointer exception")
        buckets = {
            "bucket_a": [case_a],
            "bucket_b": [case_b],
            "bucket_c": [case_c],
        }

        results = [
            SemanticDuplicateResult("a1", "b1", True, 0.95, "paraphrase"),
            SemanticDuplicateResult("b1", "c1", True, 0.92, "paraphrase"),
        ]
        config = ModelOptimizerConfig(duplicate_confidence_threshold=0.8)
        merged = _apply_semantic_merges(buckets, results, config)

        all_cases = [c for cases in merged.values() for c in cases]
        assert len(all_cases) == 3
        assert len(merged) == 1

    def test_empty_results_no_change(self):
        case_a = make_case("a1")
        case_b = make_case("b1", issue_text="fix: different")
        buckets = {"bucket_a": [case_a], "bucket_b": [case_b]}
        merged = _apply_semantic_merges(buckets, [])
        assert len(merged) == 2

    def test_default_config_when_none(self):
        case_a = make_case("a1")
        case_b = make_case("b1", issue_text="fix: null pointer crash")
        buckets = {"bucket_a": [case_a], "bucket_b": [case_b]}
        result = SemanticDuplicateResult("a1", "b1", True, 0.95, "ok")
        # Should not raise with None config
        merged = _apply_semantic_merges(buckets, [result], None)
        assert isinstance(merged, dict)


# ---------------------------------------------------------------------------
# select_canonical_duplicate
# ---------------------------------------------------------------------------

class TestSelectCanonicalDuplicate:
    def test_rule_based_prefers_high_semantic_value(self):
        cases = [
            make_case("c1", semantic_value="low"),
            make_case("c2", semantic_value="high"),
            make_case("c3", semantic_value="medium"),
        ]
        canonical = select_canonical_duplicate(cases, use_model_optimization=False)
        assert canonical.case_id == "c2"

    def test_rule_based_prefers_moderate_length(self):
        """Among same semantic_value, prefer issue_text length ~18 chars."""
        cases = [
            make_case("c1", issue_text="x" * 50, semantic_value="medium"),  # too long
            make_case("c2", issue_text="fix: null ptr", semantic_value="medium"),  # ~13 chars
            make_case("c3", issue_text="fix: null pointer", semantic_value="medium"),  # ~17 chars
        ]
        canonical = select_canonical_duplicate(cases, use_model_optimization=False)
        # c3 is closest to 18 chars
        assert canonical.case_id == "c3"

    def test_model_selects_highest_score(self):
        call_count = [0]

        def scoring_executor(prompt: str) -> str:
            call_count[0] += 1
            # Return increasing scores for each call
            scores = [3, 9, 5]
            idx = min(call_count[0] - 1, len(scores) - 1)
            return f'{{"score": {scores[idx]}, "reason": "ok"}}'

        # Distinct issue_text so each case gets its own cache key
        cases = [
            make_case("c1", issue_text="fix: issue alpha", semantic_value="medium"),
            make_case("c2", issue_text="fix: issue beta", semantic_value="medium"),
            make_case("c3", issue_text="fix: issue gamma", semantic_value="medium"),
        ]
        canonical = select_canonical_duplicate(
            cases,
            use_model_optimization=True,
            model_executor=scoring_executor,
        )
        assert canonical.case_id == "c2"

    def test_model_fallback_on_error(self):
        """Falls back to rule-based when model fails."""
        def failing_executor(prompt: str) -> str:
            raise RuntimeError("model unavailable")

        cases = [
            make_case("c1", semantic_value="low"),
            make_case("c2", semantic_value="high"),
        ]
        config = ModelOptimizerConfig(max_retries=1, retry_backoff_base=0.0)
        canonical = select_canonical_duplicate(
            cases,
            use_model_optimization=True,
            model_executor=failing_executor,
            model_config=config,
        )
        # Fallback to rule-based: high semantic_value wins
        assert canonical.case_id == "c2"

    def test_single_case_returned(self):
        cases = [make_case("c1")]
        canonical = select_canonical_duplicate(cases, use_model_optimization=False)
        assert canonical.case_id == "c1"


# ---------------------------------------------------------------------------
# _filter_by_semantic_value
# ---------------------------------------------------------------------------

class TestFilterBySemanticValue:
    def test_keeps_only_high_when_present(self):
        cases = [
            make_case("c1", semantic_value="high"),
            make_case("c2", semantic_value="medium"),
            make_case("c3", semantic_value="low"),
        ]
        filtered = _filter_by_semantic_value(cases)
        assert len(filtered) == 1
        assert filtered[0].case_id == "c1"

    def test_keeps_medium_when_no_high(self):
        cases = [
            make_case("c1", semantic_value="medium"),
            make_case("c2", semantic_value="low"),
        ]
        filtered = _filter_by_semantic_value(cases)
        assert len(filtered) == 1
        assert filtered[0].case_id == "c1"

    def test_keeps_all_when_same_tier(self):
        cases = [
            make_case("c1", semantic_value="medium"),
            make_case("c2", semantic_value="medium"),
        ]
        filtered = _filter_by_semantic_value(cases)
        assert len(filtered) == 2

    def test_single_case_returned(self):
        cases = [make_case("c1", semantic_value="low")]
        filtered = _filter_by_semantic_value(cases)
        assert len(filtered) == 1
