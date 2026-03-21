"""E2E tests for commit-semantic skill."""

from __future__ import annotations

import json
from pathlib import Path



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
