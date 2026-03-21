"""E2E tests for commit-semantic skill."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_commit_semantic_module():
    """Load commit-semantic skill module."""
    import importlib.util
    repo_root = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "commit_semantic",
        str(repo_root / "skills/commit-semantic/run.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_semantic"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_semantic_fails_without_extract_output(workspace: Path, run_skill):
    """没有 commit-extract 输出时应失败并提示."""
    result = run_skill("commit-semantic", "run", cwd=workspace)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "commit-extract" in output.lower() or "prerequisites" in output.lower()


def test_semantic_status_no_state(workspace: Path, run_skill):
    """Status reports no state before run."""
    result = run_skill("commit-semantic", "status", cwd=workspace)
    assert result.returncode == 0
    assert "No state found" in result.stdout


def test_semantic_step_with_extract_output(workspace_with_extract_output: Path, run_skill, load_state):
    """有 commit-extract 输出时 step 应运行 analyze 并停在 breakpoint."""
    run_skill("commit-semantic", "step", cwd=workspace_with_extract_output)
    state = load_state(workspace_with_extract_output, "commit-semantic")
    assert state is not None
    # Should have attempted analyze
    assert state["metadata"].get("current_stage") is not None or state["metadata"].get("status") == "breakpoint"


def test_semantic_reset_clears_progress(workspace_with_extract_output: Path, run_skill, load_state):
    """reset 应清除进度但保留 artifacts."""
    # First try to run (may fail on dispatcher, but creates state)
    run_skill("commit-semantic", "step", cwd=workspace_with_extract_output)

    # Reset
    result = run_skill("commit-semantic", "reset", cwd=workspace_with_extract_output)
    assert result.returncode == 0
    assert "reset" in result.stdout.lower()

    state = load_state(workspace_with_extract_output, "commit-semantic")
    assert state["metadata"]["completed_stages"] == []


def test_semantic_prerequisite_error_includes_helpful_message(workspace: Path, run_skill):
    """依赖错误应包含有用的提示信息."""
    result = run_skill("commit-semantic", "run", cwd=workspace)
    assert result.returncode != 0
    # Should mention what user needs to do
    output = result.stdout + result.stderr
    assert "commit-extract" in output.lower() or "prerequisites" in output.lower()


class TestCommitSemanticClassification:
    """Tests for commit classification logic."""

    def test_classify_type_functional(self):
        """Test functional commit classification."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert runner._classify_type("feat: add parser") == "functional"
        assert runner._classify_type("bugfix: fix parser") == "functional"
        assert runner._classify_type("optimize: improve perf") == "functional"
        assert runner._classify_type("refactor+bugfix: fix and cleanup") == "functional"

    def test_classify_type_non_functional(self):
        """Test non-functional commit classification."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert runner._classify_type("refactor: cleanup") == "non-functional"
        assert runner._classify_type("test: add tests") == "non-functional"
        assert runner._classify_type("config: update config") == "non-functional"

    def test_detect_modules(self):
        """Test module detection from commit message."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        assert "parser" in runner._detect_modules("feat: add parser module")
        assert "config" in runner._detect_modules("fix config loading")
        assert "schedule" in runner._detect_modules("update schedule timer")


class TestCommitSemanticScoring:
    """Tests for commit scoring logic."""

    def test_score_unit_with_module(self):
        """Unit with identified module scores higher."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        unit_with_module = {
            "commit_log": "feat: add parser module with clear description",
            "module": "parser"
        }
        unit_unknown = {
            "commit_log": "feat: add parser module with clear description",
            "module": "unknown"
        }

        score_with = runner._score_unit(unit_with_module)
        score_without = runner._score_unit(unit_unknown)

        assert score_with > score_without

    def test_score_unit_clear_log(self):
        """Clear commit log scores higher."""
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()

        clear_unit = {
            "commit_log": "feat: add parser module with proper description",
            "module": "parser"
        }

        score = runner._score_unit(clear_unit)
        assert 5 <= score <= 10  # Base 5 + bonuses
