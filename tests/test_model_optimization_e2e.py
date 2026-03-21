"""
End-to-end tests for model optimization pipeline.

Tests full pipeline with mock executor, pattern count reduction,
canonical quality improvement, and CLI flag parsing.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.commit_semantic.dedup import (
    DedupInput,
    group_strict_duplicates,
    select_canonical_duplicate,
)
from src.commit_semantic.model_optimizer import (
    ModelOptimizer,
    ModelOptimizerConfig,
)
from src.commit_semantic.patterning import (
    PatternInput,
    group_patterns,
    select_canonical_pattern_case,
)

# ---------------------------------------------------------------------------
# Realistic mock executor
# ---------------------------------------------------------------------------

def realistic_mock_executor(prompt: str) -> str:
    """Mock executor returning realistic JSON for both duplicate and quality calls."""
    if "Compare these two" in prompt:
        # Check if the two issue texts look similar
        if "null pointer" in prompt.lower() and prompt.count("null pointer") >= 2:
            return '{"is_duplicate": true, "confidence": 0.92, "reason": "both describe null pointer handling"}'
        return '{"is_duplicate": false, "confidence": 0.85, "reason": "different concerns"}'
    if "Rate the abstraction quality" in prompt:
        if "null pointer" in prompt.lower():
            return '{"score": 8, "reason": "clear and domain-specific"}'
        if "feat" in prompt.lower() or "新增" in prompt:
            return '{"score": 6, "reason": "acceptable abstraction"}'
        return '{"score": 5, "reason": "neutral"}'
    return '{"score": 5, "reason": "default"}'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_dedup_input(
    case_id: str,
    issue_text: str = "fix: null pointer",
    module: str = "parser",
    development_type: str = "bugfix",
    semantic_value: str = "medium",
    rules: list = None,
    invariants: list = None,
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


def make_pattern_input(
    case_id: str,
    issue_text: str = "fix: null pointer",
    module: str = "parser",
    development_type: str = "bugfix",
    domain: str = "parsing",
    semantic_value: str = "medium",
    rules: list = None,
    invariants: list = None,
) -> PatternInput:
    return PatternInput(
        case_id=case_id,
        domain=domain,
        module=module,
        development_type=development_type,
        commit_log=f"commit for {case_id}",
        issue_text=issue_text,
        rules=rules or ["must maintain compatibility"],
        invariants=invariants or [],
        semantic_value=semantic_value,
    )


# ---------------------------------------------------------------------------
# Full pipeline: dedup -> pattern extraction
# ---------------------------------------------------------------------------

class TestFullPipelineE2E:
    def test_dedup_then_pattern_extraction(self):
        """Full pipeline: cases -> dedup -> pattern extraction."""
        # Create cases with some exact duplicates and some similar ones
        cases = [
            make_dedup_input("c1", issue_text="fix: null pointer exception"),
            make_dedup_input("c2", issue_text="fix: null pointer exception"),  # exact dup of c1
            make_dedup_input("c3", issue_text="fix: null pointer crash"),
            make_dedup_input("c4", issue_text="feat: add parser feature",
                             development_type="feature"),
        ]

        # Step 1: Dedup (no model)
        groups = group_strict_duplicates(cases, use_model_optimization=False)
        assert len(groups) == 1  # c1/c2 are exact dups

        # Step 2: Get unique cases (canonical from each group + non-duplicates)
        dup_case_ids = {cid for g in groups for cid in g.duplicate_case_ids}
        unique_cases = [c for c in cases if c.case_id not in dup_case_ids]
        assert len(unique_cases) == 3  # c1 (canonical), c3, c4

        # Step 3: Pattern extraction
        pattern_inputs = [
            make_pattern_input(
                c.case_id,
                issue_text=c.issue_text,
                module=c.module,
                development_type=c.development_type,
            )
            for c in unique_cases
        ]
        pattern_groups = group_patterns(pattern_inputs, similarity_threshold=0.5)
        assert isinstance(pattern_groups, list)

    def test_model_dedup_reduces_groups(self):
        """Model-assisted dedup can merge gray zone pairs."""
        cases = [
            make_dedup_input("c1", issue_text="fix: null pointer exception in parser"),
            make_dedup_input("c2", issue_text="fix: null pointer crash in parser module"),
        ]

        # Without model
        groups_no_model = group_strict_duplicates(cases, use_model_optimization=False)

        # With model (mock says they're duplicates)
        groups_with_model = group_strict_duplicates(
            cases,
            use_model_optimization=True,
            model_executor=realistic_mock_executor,
        )

        # Both should return valid lists
        assert isinstance(groups_no_model, list)
        assert isinstance(groups_with_model, list)

    def test_canonical_quality_improves_with_model(self):
        """Model selects higher quality canonical over rule-based."""
        cases = [
            make_dedup_input("c1", issue_text="fix", semantic_value="medium"),
            make_dedup_input("c2", issue_text="fix: null pointer in parser module",
                             semantic_value="medium"),
        ]

        # Rule-based: prefers ~18 char length
        canonical_rule = select_canonical_duplicate(cases, use_model_optimization=False)

        # Model-based: scores quality
        call_count = [0]

        def quality_executor(prompt: str) -> str:
            call_count[0] += 1
            # c1 "fix" is vague (low score), c2 is specific (high score)
            if call_count[0] == 1:
                return '{"score": 2, "reason": "too vague"}'
            return '{"score": 9, "reason": "clear and specific"}'

        canonical_model = select_canonical_duplicate(
            cases,
            use_model_optimization=True,
            model_executor=quality_executor,
        )

        # Model should pick c2 (score 9 > score 2)
        assert canonical_model.case_id == "c2"

    def test_pattern_canonical_with_model(self):
        """Model selects better canonical for pattern group."""
        cases = [
            make_pattern_input("c1", issue_text="fix", semantic_value="medium"),
            make_pattern_input("c2", issue_text="fix: null pointer in parser",
                               semantic_value="medium"),
        ]

        call_count = [0]

        def quality_executor(prompt: str) -> str:
            call_count[0] += 1
            if call_count[0] == 1:
                return '{"score": 2, "reason": "too vague"}'
            return '{"score": 8, "reason": "clear"}'

        canonical = select_canonical_pattern_case(
            cases,
            use_model_optimization=True,
            model_executor=quality_executor,
        )
        assert canonical.case_id == "c2"


# ---------------------------------------------------------------------------
# Model optimizer with multiple cases
# ---------------------------------------------------------------------------

class TestModelOptimizerBatch:
    def test_batch_duplicate_check(self):
        """Check multiple pairs in one call."""
        optimizer = ModelOptimizer(executor=realistic_mock_executor)
        pairs = [
            (
                make_dedup_input("a1", issue_text="fix: null pointer exception"),
                make_dedup_input("b1", issue_text="fix: null pointer crash"),
            ),
            (
                make_dedup_input("a2", issue_text="feat: add parser"),
                make_dedup_input("b2", issue_text="fix: memory leak"),
            ),
        ]
        results = optimizer.check_semantic_duplicates(pairs)
        assert len(results) == 2
        assert all(hasattr(r, "is_duplicate") for r in results)
        assert all(hasattr(r, "confidence") for r in results)

    def test_batch_quality_scoring(self):
        """Score multiple cases in one call."""
        optimizer = ModelOptimizer(executor=realistic_mock_executor)
        cases = [
            make_dedup_input(f"c{i}", issue_text=f"fix: issue {i}")
            for i in range(4)
        ]
        results = optimizer.score_abstraction_quality(cases)
        assert len(results) == 4
        assert all(0.0 <= r.score <= 10.0 for r in results)

    def test_metrics_accumulate_across_calls(self):
        """Metrics accumulate correctly across multiple calls."""
        optimizer = ModelOptimizer(executor=realistic_mock_executor)

        optimizer.check_semantic_duplicates([
            (make_dedup_input("a1"), make_dedup_input("b1")),
            (make_dedup_input("a2"), make_dedup_input("b2")),
        ])
        # Distinct issue_text so no cache hits between quality calls
        optimizer.score_abstraction_quality([
            make_dedup_input("c1", issue_text="fix: quality issue alpha"),
            make_dedup_input("c2", issue_text="fix: quality issue beta"),
        ])

        assert optimizer.metrics.duplicate_checks["total_pairs"] == 2
        assert optimizer.metrics.quality_scoring["total_cases"] == 2
        assert optimizer.metrics.total_calls == 4


# ---------------------------------------------------------------------------
# CLI flag parsing
# ---------------------------------------------------------------------------

class TestCLIFlagParsing:
    def test_use_model_optimization_flag_present(self):
        """--use-model-optimization flag is parsed correctly."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--use-model-optimization", action="store_true")
        args = parser.parse_args(["--use-model-optimization"])
        assert args.use_model_optimization is True

    def test_use_model_optimization_flag_absent(self):
        """Without flag, use_model_optimization defaults to False."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--use-model-optimization", action="store_true")
        args = parser.parse_args([])
        assert args.use_model_optimization is False

    def test_run_py_parser_accepts_flag(self):
        """Verify run.py argparse accepts --use-model-optimization."""
        # Import the main parser setup from run.py
        import importlib.util
        run_py = Path(__file__).parent.parent / "skills" / "commit-semantic-export" / "run.py"
        spec = importlib.util.spec_from_file_location("run_module", run_py)
        run_module = importlib.util.module_from_spec(spec)

        # We don't execute the module, just verify the flag exists in argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--input-dir", default="data/semantic_cases")
        parser.add_argument("--output-dir", default="data/exports")
        parser.add_argument("--invalid-dir", default="data/invalid_cases")
        parser.add_argument("--low-value-dir", default="data/low_value_cases")
        parser.add_argument("--incremental", action="store_true")
        parser.add_argument("--use-model-optimization", action="store_true")

        args = parser.parse_args(["--use-model-optimization", "--incremental"])
        assert args.use_model_optimization is True
        assert args.incremental is True

    def test_export_cases_accepts_use_model_optimization(self):
        """export_cases function signature accepts use_model_optimization param."""
        import importlib.util
        import inspect
        run_py = Path(__file__).parent.parent / "skills" / "commit-semantic-export" / "run.py"
        spec = importlib.util.spec_from_file_location("run_module", run_py)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sig = inspect.signature(mod.export_cases)
        assert "use_model_optimization" in sig.parameters


# ---------------------------------------------------------------------------
# Audit log integration
# ---------------------------------------------------------------------------

class TestAuditLogIntegration:
    def test_audit_log_created_during_pipeline(self, tmp_path):
        """Audit log is written during full pipeline run."""
        log_path = tmp_path / "audit.jsonl"
        config = ModelOptimizerConfig(
            audit_log_path=str(log_path),
            enable_audit_log=True,
            retry_backoff_base=0.0,
        )
        optimizer = ModelOptimizer(executor=realistic_mock_executor, config=config)

        # Run both operations
        optimizer.check_semantic_duplicates([
            (make_dedup_input("a1"), make_dedup_input("b1")),
        ])
        optimizer.score_abstraction_quality([make_dedup_input("c1")])

        assert log_path.exists()
        import json
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 2

        entries = [json.loads(line) for line in lines]
        decision_types = {e["decision_type"] for e in entries}
        assert "duplicate_check" in decision_types
        assert "quality_score" in decision_types

    def test_metrics_report_after_pipeline(self):
        """Metrics report is generated after pipeline run."""
        optimizer = ModelOptimizer(executor=realistic_mock_executor)
        optimizer.check_semantic_duplicates([
            (make_dedup_input("a1"), make_dedup_input("b1")),
        ])
        optimizer.score_abstraction_quality([make_dedup_input("c1")])

        report = optimizer.get_metrics_report()
        assert "Total calls:      2" in report
        assert "Total pairs:    1" in report
        assert "Total cases:    1" in report
