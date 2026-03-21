"""
Unit tests for model_optimizer.py.

Tests ModelOptimizer class, dataclasses, retry logic, caching,
audit logging, metrics, and convenience functions.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.dedup import DedupInput
from src.commit_semantic.model_optimizer import (
    ModelOptimizer,
    ModelOptimizerConfig,
    QualityScore,
    SemanticDuplicateResult,
    check_semantic_duplicates,
    score_abstraction_quality,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_case(case_id: str, issue_text: str = "fix: null pointer", semantic_value: str = "medium") -> DedupInput:
    return DedupInput(
        case_id=case_id,
        module="parser",
        development_type="bugfix",
        issue_text=issue_text,
        rules=["must maintain compatibility"],
        invariants=["inputs remain parseable"],
        semantic_value=semantic_value,
    )


def mock_executor_dup_true(prompt: str) -> str:
    return '{"is_duplicate": true, "confidence": 0.9, "reason": "paraphrase"}'


def mock_executor_dup_false(prompt: str) -> str:
    return '{"is_duplicate": false, "confidence": 0.85, "reason": "different semantics"}'


def mock_executor_quality(prompt: str) -> str:
    return '{"score": 8, "reason": "clear and reusable"}'


def mock_executor_combined(prompt: str) -> str:
    if "Compare these two" in prompt:
        return '{"is_duplicate": true, "confidence": 0.9, "reason": "paraphrase"}'
    if "Rate the abstraction quality" in prompt:
        return '{"score": 8, "reason": "clear and reusable"}'
    return "{}"


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------

class TestSemanticDuplicateResult:
    def test_fields(self):
        r = SemanticDuplicateResult(
            case_a_id="a1",
            case_b_id="b1",
            is_duplicate=True,
            confidence=0.9,
            reason="paraphrase",
        )
        assert r.case_a_id == "a1"
        assert r.case_b_id == "b1"
        assert r.is_duplicate is True
        assert r.confidence == 0.9
        assert r.reason == "paraphrase"

    def test_not_duplicate(self):
        r = SemanticDuplicateResult(
            case_a_id="a1", case_b_id="b1",
            is_duplicate=False, confidence=0.1, reason="different"
        )
        assert r.is_duplicate is False


class TestQualityScore:
    def test_fields(self):
        qs = QualityScore(case_id="c1", score=7.5, reason="good abstraction")
        assert qs.case_id == "c1"
        assert qs.score == 7.5
        assert qs.reason == "good abstraction"


# ---------------------------------------------------------------------------
# check_semantic_duplicates
# ---------------------------------------------------------------------------

class TestCheckSemanticDuplicates:
    def test_returns_duplicate_true(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_true)
        case_a = make_case("a1", "fix: null pointer crash")
        case_b = make_case("b1", "fix: null pointer exception")
        results = optimizer.check_semantic_duplicates([(case_a, case_b)])
        assert len(results) == 1
        assert results[0].is_duplicate is True
        assert results[0].confidence == 0.9
        assert results[0].case_a_id == "a1"
        assert results[0].case_b_id == "b1"

    def test_returns_duplicate_false(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_false)
        case_a = make_case("a1", "fix: null pointer")
        case_b = make_case("b1", "feat: add parser")
        results = optimizer.check_semantic_duplicates([(case_a, case_b)])
        assert results[0].is_duplicate is False

    def test_multiple_pairs(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_true)
        pairs = [
            (make_case("a1"), make_case("b1")),
            (make_case("a2"), make_case("b2")),
        ]
        results = optimizer.check_semantic_duplicates(pairs)
        assert len(results) == 2

    def test_empty_pairs(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_true)
        results = optimizer.check_semantic_duplicates([])
        assert results == []

    def test_updates_metrics(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_true)
        case_a = make_case("a1")
        case_b = make_case("b1")
        optimizer.check_semantic_duplicates([(case_a, case_b)])
        assert optimizer.metrics.duplicate_checks["total_pairs"] == 1
        assert optimizer.metrics.duplicate_checks["duplicates_found"] == 1

    def test_updates_avg_confidence(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_true)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert optimizer.metrics.duplicate_checks["avg_confidence"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# score_abstraction_quality
# ---------------------------------------------------------------------------

class TestScoreAbstractionQuality:
    def test_returns_score(self):
        optimizer = ModelOptimizer(executor=mock_executor_quality)
        case = make_case("c1", "fix: null pointer in parser")
        results = optimizer.score_abstraction_quality([case])
        assert len(results) == 1
        assert results[0].score == 8.0
        assert results[0].case_id == "c1"

    def test_multiple_cases(self):
        optimizer = ModelOptimizer(executor=mock_executor_quality)
        cases = [make_case(f"c{i}") for i in range(3)]
        results = optimizer.score_abstraction_quality(cases)
        assert len(results) == 3

    def test_empty_cases(self):
        optimizer = ModelOptimizer(executor=mock_executor_quality)
        results = optimizer.score_abstraction_quality([])
        assert results == []

    def test_updates_metrics(self):
        optimizer = ModelOptimizer(executor=mock_executor_quality)
        optimizer.score_abstraction_quality([make_case("c1")])
        assert optimizer.metrics.quality_scoring["total_cases"] == 1

    def test_score_clamped_to_max(self):
        def executor_over(prompt: str) -> str:
            return '{"score": 15, "reason": "over max"}'
        optimizer = ModelOptimizer(executor=executor_over)
        results = optimizer.score_abstraction_quality([make_case("c1")])
        assert results[0].score == 10.0

    def test_score_clamped_to_min(self):
        def executor_under(prompt: str) -> str:
            return '{"score": -5, "reason": "under min"}'
        optimizer = ModelOptimizer(executor=executor_under)
        results = optimizer.score_abstraction_quality([make_case("c1")])
        assert results[0].score == 0.0


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------

class TestRetryLogic:
    def test_retry_then_success(self):
        """Executor fails twice then succeeds on third attempt."""
        call_count = [0]

        def flaky_executor(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] < 3:
                raise RuntimeError("transient error")
            return '{"is_duplicate": true, "confidence": 0.9, "reason": "ok"}'

        config = ModelOptimizerConfig(max_retries=3, retry_backoff_base=0.0)
        optimizer = ModelOptimizer(executor=flaky_executor, config=config)
        results = optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert results[0].is_duplicate is True
        assert call_count[0] == 3

    def test_safe_default_on_max_retries_exceeded_dup(self):
        """Returns is_duplicate=False after all retries fail."""
        def always_fail(prompt: str) -> str:
            raise RuntimeError("always fails")

        config = ModelOptimizerConfig(max_retries=2, retry_backoff_base=0.0)
        optimizer = ModelOptimizer(executor=always_fail, config=config)
        results = optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert results[0].is_duplicate is False
        assert results[0].confidence == 0.0
        assert "Error after" in results[0].reason
        assert optimizer.metrics.failed_calls == 1

    def test_safe_default_on_max_retries_exceeded_quality(self):
        """Returns score=5.0 after all retries fail."""
        def always_fail(prompt: str) -> str:
            raise RuntimeError("always fails")

        config = ModelOptimizerConfig(max_retries=2, retry_backoff_base=0.0)
        optimizer = ModelOptimizer(executor=always_fail, config=config)
        results = optimizer.score_abstraction_quality([make_case("c1")])
        assert results[0].score == 5.0
        assert "Error after" in results[0].reason
        assert optimizer.metrics.failed_calls == 1

    def test_no_sleep_with_zero_backoff(self):
        """Verify retry loop completes quickly with zero backoff."""
        call_count = [0]

        def fail_once(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("first fail")
            return '{"is_duplicate": false, "confidence": 0.5, "reason": "ok"}'

        config = ModelOptimizerConfig(max_retries=3, retry_backoff_base=0.0)
        optimizer = ModelOptimizer(executor=fail_once, config=config)
        results = optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert results[0].is_duplicate is False
        assert call_count[0] == 2


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    def test_duplicate_check_cached(self):
        call_count = [0]

        def counting_executor(prompt: str) -> str:
            call_count[0] += 1
            return '{"is_duplicate": true, "confidence": 0.9, "reason": "cached"}'

        optimizer = ModelOptimizer(executor=counting_executor)
        pair = (make_case("a1"), make_case("b1"))
        optimizer.check_semantic_duplicates([pair])
        optimizer.check_semantic_duplicates([pair])
        # Second call should hit cache, not call executor again
        assert call_count[0] == 1
        assert optimizer.metrics.cache_hits == 1

    def test_quality_score_cached(self):
        call_count = [0]

        def counting_executor(prompt: str) -> str:
            call_count[0] += 1
            return '{"score": 7, "reason": "cached"}'

        optimizer = ModelOptimizer(executor=counting_executor)
        case = make_case("c1", "fix: same issue text")
        optimizer.score_abstraction_quality([case])
        optimizer.score_abstraction_quality([case])
        assert call_count[0] == 1
        assert optimizer.metrics.cache_hits == 1

    def test_different_cases_not_cached(self):
        call_count = [0]

        def counting_executor(prompt: str) -> str:
            call_count[0] += 1
            return '{"score": 7, "reason": "ok"}'

        optimizer = ModelOptimizer(executor=counting_executor)
        optimizer.score_abstraction_quality([make_case("c1", "issue text A")])
        optimizer.score_abstraction_quality([make_case("c2", "issue text B")])
        assert call_count[0] == 2
        assert optimizer.metrics.cache_hits == 0


# ---------------------------------------------------------------------------
# JSON parsing (_extract_json)
# ---------------------------------------------------------------------------

class TestExtractJson:
    def setup_method(self):
        self.optimizer = ModelOptimizer()

    def test_raw_json(self):
        result = self.optimizer._extract_json('{"is_duplicate": true, "confidence": 0.9, "reason": "ok"}')
        assert result["is_duplicate"] is True

    def test_json_code_block(self):
        response = '```json\n{"score": 8, "reason": "good"}\n```'
        result = self.optimizer._extract_json(response)
        assert result["score"] == 8

    def test_json_embedded_in_text(self):
        response = 'Here is my analysis: {"is_duplicate": false, "confidence": 0.3, "reason": "different"} end.'
        result = self.optimizer._extract_json(response)
        assert result["is_duplicate"] is False

    def test_invalid_json_raises(self):
        with pytest.raises(Exception):
            self.optimizer._extract_json("not json at all")

    def test_json_with_whitespace(self):
        result = self.optimizer._extract_json('  {"score": 5, "reason": "neutral"}  ')
        assert result["score"] == 5


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

class TestAuditLogging:
    def test_log_written_for_dup_check(self, tmp_path):
        log_path = tmp_path / "decisions.jsonl"
        config = ModelOptimizerConfig(
            audit_log_path=str(log_path),
            enable_audit_log=True,
            retry_backoff_base=0.0,
        )
        optimizer = ModelOptimizer(executor=mock_executor_dup_true, config=config)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])

        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["decision_type"] == "duplicate_check"
        assert entry["output"]["is_duplicate"] is True
        assert "timestamp" in entry

    def test_log_written_for_quality_score(self, tmp_path):
        log_path = tmp_path / "decisions.jsonl"
        config = ModelOptimizerConfig(
            audit_log_path=str(log_path),
            enable_audit_log=True,
            retry_backoff_base=0.0,
        )
        optimizer = ModelOptimizer(executor=mock_executor_quality, config=config)
        optimizer.score_abstraction_quality([make_case("c1")])

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["decision_type"] == "quality_score"
        assert entry["output"]["score"] == 8.0

    def test_log_disabled(self, tmp_path):
        log_path = tmp_path / "decisions.jsonl"
        config = ModelOptimizerConfig(
            audit_log_path=str(log_path),
            enable_audit_log=False,
            retry_backoff_base=0.0,
        )
        optimizer = ModelOptimizer(executor=mock_executor_dup_true, config=config)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert not log_path.exists()

    def test_multiple_entries_appended(self, tmp_path):
        log_path = tmp_path / "decisions.jsonl"
        config = ModelOptimizerConfig(
            audit_log_path=str(log_path),
            enable_audit_log=True,
            retry_backoff_base=0.0,
        )
        optimizer = ModelOptimizer(executor=mock_executor_combined, config=config)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        optimizer.score_abstraction_quality([make_case("c1")])

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2


# ---------------------------------------------------------------------------
# Metrics tracking
# ---------------------------------------------------------------------------

class TestMetrics:
    def test_successful_calls_tracked(self):
        optimizer = ModelOptimizer(executor=mock_executor_dup_true)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert optimizer.metrics.total_calls == 1
        assert optimizer.metrics.successful_calls == 1
        assert optimizer.metrics.failed_calls == 0

    def test_failed_calls_tracked(self):
        def always_fail(prompt: str) -> str:
            raise RuntimeError("fail")

        config = ModelOptimizerConfig(max_retries=1, retry_backoff_base=0.0)
        optimizer = ModelOptimizer(executor=always_fail, config=config)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        assert optimizer.metrics.failed_calls == 1

    def test_metrics_report_contains_key_fields(self):
        optimizer = ModelOptimizer(executor=mock_executor_combined)
        optimizer.check_semantic_duplicates([(make_case("a1"), make_case("b1"))])
        optimizer.score_abstraction_quality([make_case("c1")])
        report = optimizer.get_metrics_report()
        assert "Total calls" in report
        assert "Cache hits" in report
        assert "Duplicate Checks" in report
        assert "Quality Scoring" in report


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

class TestConvenienceFunctions:
    def test_check_semantic_duplicates_module_level(self):
        results = check_semantic_duplicates(
            [(make_case("a1"), make_case("b1"))],
            executor=mock_executor_dup_true,
        )
        assert len(results) == 1
        assert results[0].is_duplicate is True

    def test_score_abstraction_quality_module_level(self):
        results = score_abstraction_quality(
            [make_case("c1")],
            executor=mock_executor_quality,
        )
        assert len(results) == 1
        assert results[0].score == 8.0

    def test_convenience_with_config(self):
        config = ModelOptimizerConfig(max_retries=1, retry_backoff_base=0.0)
        results = check_semantic_duplicates(
            [(make_case("a1"), make_case("b1"))],
            executor=mock_executor_dup_false,
            config=config,
        )
        assert results[0].is_duplicate is False

    def test_no_executor_raises_on_call(self):
        """Without executor, model call raises RuntimeError (caught as safe default)."""
        results = check_semantic_duplicates(
            [(make_case("a1"), make_case("b1"))],
            executor=None,
        )
        # Safe default: is_duplicate=False
        assert results[0].is_duplicate is False
