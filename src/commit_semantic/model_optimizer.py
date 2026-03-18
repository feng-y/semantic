"""
Model-assisted optimization for deduplication and canonical selection.

Provides two key capabilities:
1. Semantic duplicate detection for gray zone pairs (similarity 0.40-0.60)
2. Abstraction quality scoring for canonical selection

Model has final authority when enabled; rule-based logic serves as efficiency pre-filter.
"""

from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .dedup import DedupInput


@dataclass
class SemanticDuplicateResult:
    """Result of semantic duplicate check."""
    case_a_id: str
    case_b_id: str
    is_duplicate: bool
    confidence: float
    reason: str


@dataclass
class QualityScore:
    """Abstraction quality score for a case."""
    case_id: str
    score: float  # 0-10
    reason: str


@dataclass
class ModelOptimizerConfig:
    """Configuration for model optimization."""

    # Retry settings
    max_retries: int = 3
    retry_backoff_base: float = 2.0

    # Confidence thresholds
    duplicate_confidence_threshold: float = 0.8
    quality_score_min: float = 0.0
    quality_score_max: float = 10.0

    # Gray zone bounds
    gray_zone_similarity_min: float = 0.40
    gray_zone_similarity_max: float = 0.60

    # Model settings
    model_name: str = "claude-haiku"
    temperature: float = 0.0  # Deterministic
    max_tokens: int = 500

    # Logging
    audit_log_path: str = "data/exports/model_decisions.jsonl"
    enable_audit_log: bool = True
    log_level: str = "INFO"


@dataclass
class ModelMetrics:
    """Metrics for model optimization calls."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    cache_hits: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0

    duplicate_checks: dict = field(default_factory=lambda: {
        "total_pairs": 0,
        "duplicates_found": 0,
        "avg_confidence": 0.0
    })

    quality_scoring: dict = field(default_factory=lambda: {
        "total_cases": 0,
        "avg_score": 0.0
    })


class ModelOptimizer:
    """Model-assisted optimization for dedup and canonical selection."""

    def __init__(
        self,
        executor: Optional[Callable[[str], str]] = None,
        config: Optional[ModelOptimizerConfig] = None
    ):
        """
        Initialize model optimizer.

        Args:
            executor: Callable that takes prompt string and returns response
            config: Configuration for model optimization
        """
        self.executor = executor
        self.config = config or ModelOptimizerConfig()
        self.metrics = ModelMetrics()
        self._cache: dict[str, dict] = {}

    def check_semantic_duplicates(
        self,
        pairs: list[tuple["DedupInput", "DedupInput"]]
    ) -> list[SemanticDuplicateResult]:
        """
        Check if pairs are semantic duplicates using model.

        Args:
            pairs: List of (case_a, case_b) tuples to check

        Returns:
            List of semantic duplicate results
        """
        results = []

        for case_a, case_b in pairs:
            result = self._check_pair_with_retry(case_a, case_b)
            results.append(result)

            # Update metrics
            self.metrics.duplicate_checks["total_pairs"] += 1
            if result.is_duplicate:
                self.metrics.duplicate_checks["duplicates_found"] += 1

            # Log decision
            if self.config.enable_audit_log:
                self._log_decision("duplicate_check", {
                    "case_a_id": case_a.case_id,
                    "case_a_issue": case_a.issue_text,
                    "case_b_id": case_b.case_id,
                    "case_b_issue": case_b.issue_text
                }, {
                    "is_duplicate": result.is_duplicate,
                    "confidence": result.confidence,
                    "reason": result.reason
                })

        # Update average confidence
        if results:
            avg_conf = sum(r.confidence for r in results) / len(results)
            self.metrics.duplicate_checks["avg_confidence"] = avg_conf

        return results

    def score_abstraction_quality(
        self,
        cases: list["DedupInput"]
    ) -> list[QualityScore]:
        """
        Score abstraction quality of issue_text using model.

        Args:
            cases: List of cases to score

        Returns:
            List of quality scores
        """
        results = []

        for case in cases:
            result = self._score_case_with_retry(case)
            results.append(result)

            # Update metrics
            self.metrics.quality_scoring["total_cases"] += 1

            # Log decision
            if self.config.enable_audit_log:
                self._log_decision("quality_score", {
                    "case_id": case.case_id,
                    "issue_text": case.issue_text,
                    "rules": case.rules,
                    "invariants": case.invariants
                }, {
                    "score": result.score,
                    "reason": result.reason
                })

        # Update average score
        if results:
            avg_score = sum(r.score for r in results) / len(results)
            self.metrics.quality_scoring["avg_score"] = avg_score

        return results

    def _check_pair_with_retry(
        self,
        case_a: "DedupInput",
        case_b: "DedupInput"
    ) -> SemanticDuplicateResult:
        """Check pair with exponential backoff retry."""
        cache_key = self._make_cache_key("dup", case_a.case_id, case_b.case_id)

        # Check cache
        if cache_key in self._cache:
            self.metrics.cache_hits += 1
            cached = self._cache[cache_key]
            return SemanticDuplicateResult(**cached)

        # Try with retry
        for attempt in range(self.config.max_retries):
            try:
                result = self._check_pair(case_a, case_b)

                # Cache result
                self._cache[cache_key] = {
                    "case_a_id": result.case_a_id,
                    "case_b_id": result.case_b_id,
                    "is_duplicate": result.is_duplicate,
                    "confidence": result.confidence,
                    "reason": result.reason
                }

                self.metrics.successful_calls += 1
                return result

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_base ** attempt
                    time.sleep(wait_time)
                else:
                    # Max retries exceeded, use safe default
                    self.metrics.failed_calls += 1
                    return SemanticDuplicateResult(
                        case_a_id=case_a.case_id,
                        case_b_id=case_b.case_id,
                        is_duplicate=False,  # Conservative default
                        confidence=0.0,
                        reason=f"Error after {self.config.max_retries} retries: {str(e)}"
                    )

        # Should not reach here
        raise RuntimeError("Unexpected retry loop exit")

    def _check_pair(
        self,
        case_a: "DedupInput",
        case_b: "DedupInput"
    ) -> SemanticDuplicateResult:
        """Check if pair is semantic duplicate (single attempt)."""
        if self.executor is None:
            raise RuntimeError("No executor provided for model calls")

        prompt = self._build_duplicate_check_prompt(case_a, case_b)

        self.metrics.total_calls += 1
        response = self.executor(prompt)

        # Parse response
        try:
            # Extract JSON from response
            result_data = self._extract_json(response)

            return SemanticDuplicateResult(
                case_a_id=case_a.case_id,
                case_b_id=case_b.case_id,
                is_duplicate=result_data.get("is_duplicate", False),
                confidence=float(result_data.get("confidence", 0.0)),
                reason=result_data.get("reason", "")
            )
        except Exception as e:
            # Parse error, use safe default
            return SemanticDuplicateResult(
                case_a_id=case_a.case_id,
                case_b_id=case_b.case_id,
                is_duplicate=False,
                confidence=0.0,
                reason=f"Parse error: {str(e)}"
            )

    def _score_case_with_retry(
        self,
        case: "DedupInput"
    ) -> QualityScore:
        """Score case with exponential backoff retry."""
        cache_key = self._make_cache_key("quality", self._hash_text(case.issue_text))

        # Check cache
        if cache_key in self._cache:
            self.metrics.cache_hits += 1
            cached = self._cache[cache_key]
            return QualityScore(**cached)

        # Try with retry
        for attempt in range(self.config.max_retries):
            try:
                result = self._score_case(case)

                # Cache result
                self._cache[cache_key] = {
                    "case_id": result.case_id,
                    "score": result.score,
                    "reason": result.reason
                }

                self.metrics.successful_calls += 1
                return result

            except Exception as e:
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_backoff_base ** attempt
                    time.sleep(wait_time)
                else:
                    # Max retries exceeded, use safe default
                    self.metrics.failed_calls += 1
                    return QualityScore(
                        case_id=case.case_id,
                        score=5.0,  # Neutral default
                        reason=f"Error after {self.config.max_retries} retries: {str(e)}"
                    )

        # Should not reach here
        raise RuntimeError("Unexpected retry loop exit")

    def _score_case(
        self,
        case: "DedupInput"
    ) -> QualityScore:
        """Score case abstraction quality (single attempt)."""
        if self.executor is None:
            raise RuntimeError("No executor provided for model calls")

        prompt = self._build_quality_score_prompt(case)

        self.metrics.total_calls += 1
        response = self.executor(prompt)

        # Parse response
        try:
            # Extract JSON from response
            result_data = self._extract_json(response)

            score = float(result_data.get("score", 5.0))
            # Clamp score to valid range
            score = max(self.config.quality_score_min, min(self.config.quality_score_max, score))

            return QualityScore(
                case_id=case.case_id,
                score=score,
                reason=result_data.get("reason", "")
            )
        except Exception as e:
            # Parse error, use safe default
            return QualityScore(
                case_id=case.case_id,
                score=5.0,
                reason=f"Parse error: {str(e)}"
            )

    def _build_duplicate_check_prompt(
        self,
        case_a: "DedupInput",
        case_b: "DedupInput"
    ) -> str:
        """Build prompt for semantic duplicate check."""
        return f"""Compare these two issue descriptions:

A: {case_a.issue_text}
B: {case_b.issue_text}

Are they semantically equivalent? Consider:
- Paraphrases (新增 vs 添加)
- Translations (Chinese vs English)
- Abstraction level (空值崩溃 vs null pointer异常)

Respond with JSON:
{{
  "is_duplicate": true/false,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}"""

    def _build_quality_score_prompt(
        self,
        case: "DedupInput"
    ) -> str:
        """Build prompt for abstraction quality scoring."""
        rules_str = "\n".join(f"- {r}" for r in case.rules) if case.rules else "None"
        invariants_str = "\n".join(f"- {i}" for i in case.invariants) if case.invariants else "None"

        return f"""Rate the abstraction quality of this issue description (0-10):

Issue: {case.issue_text}

Rules:
{rules_str}

Invariants:
{invariants_str}

Criteria:
- Not too vague (e.g., "feat: 新增功能" = bad, score 2-3)
- Not too specific (e.g., "fix line 42 bug" = bad, score 2-3)
- Clear and reusable (e.g., "feat: 新增parser空值处理" = good, score 8-9)
- Appropriate detail level for the domain

Respond with JSON:
{{
  "score": 0-10 (integer),
  "reason": "brief explanation"
}}"""

    def _extract_json(self, response: str) -> dict:
        """Extract JSON from response text."""
        # Try to find JSON code block
        import re
        json_block_pattern = re.compile(r'```json\s*\n(.*?)\n```', re.DOTALL)
        match = json_block_pattern.search(response)

        if match:
            json_str = match.group(1)
        else:
            # Try to find JSON object directly
            json_obj_pattern = re.compile(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', re.DOTALL)
            match = json_obj_pattern.search(response)
            if match:
                json_str = match.group(0)
            else:
                # Assume entire response is JSON
                json_str = response.strip()

        return json.loads(json_str)

    def _log_decision(
        self,
        decision_type: str,
        input_data: dict,
        output_data: dict
    ) -> None:
        """Log decision to audit log."""
        log_path = Path(self.config.audit_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "decision_type": decision_type,
            "input": input_data,
            "output": output_data,
            "metadata": {
                "model": self.config.model_name,
                "tokens": 0,  # TODO: track actual tokens
                "cost_usd": 0.0  # TODO: track actual cost
            }
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _make_cache_key(self, *parts: str) -> str:
        """Make cache key from parts."""
        return "_".join(str(p) for p in parts)

    def _hash_text(self, text: str) -> str:
        """Hash text for cache key."""
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

    def get_metrics_report(self) -> str:
        """Generate metrics report."""
        m = self.metrics

        success_rate = (m.successful_calls / m.total_calls * 100) if m.total_calls > 0 else 0
        cache_rate = (m.cache_hits / (m.total_calls + m.cache_hits) * 100) if (m.total_calls + m.cache_hits) > 0 else 0

        return f"""Model Optimization Metrics:
---------------------------
Total calls:      {m.total_calls}
Successful:       {m.successful_calls} ({success_rate:.1f}%)
Failed:           {m.failed_calls} ({100-success_rate:.1f}%)
Cache hits:       {m.cache_hits} ({cache_rate:.1f}%)
Total tokens:     {m.total_tokens}
Total cost:       ${m.total_cost_usd:.2f}

Duplicate Checks:
  Total pairs:    {m.duplicate_checks['total_pairs']}
  Duplicates:     {m.duplicate_checks['duplicates_found']}
  Avg confidence: {m.duplicate_checks['avg_confidence']:.2f}

Quality Scoring:
  Total cases:    {m.quality_scoring['total_cases']}
  Avg score:      {m.quality_scoring['avg_score']:.1f}
"""


# Convenience functions for backward compatibility
def check_semantic_duplicates(
    pairs: list[tuple["DedupInput", "DedupInput"]],
    executor: Optional[Callable[[str], str]] = None,
    config: Optional[ModelOptimizerConfig] = None
) -> list[SemanticDuplicateResult]:
    """
    Check if pairs are semantic duplicates using model.

    Args:
        pairs: List of (case_a, case_b) tuples to check
        executor: Callable that takes prompt string and returns response
        config: Configuration for model optimization

    Returns:
        List of semantic duplicate results
    """
    optimizer = ModelOptimizer(executor=executor, config=config)
    return optimizer.check_semantic_duplicates(pairs)


def score_abstraction_quality(
    cases: list["DedupInput"],
    executor: Optional[Callable[[str], str]] = None,
    config: Optional[ModelOptimizerConfig] = None
) -> list[QualityScore]:
    """
    Score abstraction quality of issue_text using model.

    Args:
        cases: List of cases to score
        executor: Callable that takes prompt string and returns response
        config: Configuration for model optimization

    Returns:
        List of quality scores
    """
    optimizer = ModelOptimizer(executor=executor, config=config)
    return optimizer.score_abstraction_quality(cases)
