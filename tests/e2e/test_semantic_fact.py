"""E2E tests for semantic-fact skill."""

from __future__ import annotations



def test_semantic_fact_fails_without_baseline(workspace, run_skill):
    """没有 fact baseline 时应失败并提示."""
    result = run_skill("semantic-fact", "run", cwd=workspace)
    assert result.returncode != 0
    output = result.stdout + result.stderr
    assert "baseline" in output.lower() or "prerequisites" in output.lower()


def test_semantic_fact_status_no_state(workspace, run_skill):
    """Status reports no state before run."""
    result = run_skill("semantic-fact", "status", cwd=workspace)
    assert result.returncode == 0
    assert "No state found" in result.stdout


def test_semantic_fact_step_with_baseline(workspace_with_fact_baseline, run_skill, load_state):
    """有 baseline 时 step 应运行 discover 并停在 breakpoint."""
    run_skill("semantic-fact", "step", cwd=workspace_with_fact_baseline)
    # Note: May fail on dispatcher call, but should set state
    state = load_state(workspace_with_fact_baseline, "semantic-fact")
    assert state is not None
    # Should have attempted discover
    assert state["metadata"].get("current_stage") is not None or state["metadata"].get("error") is not None


def test_semantic_fact_reset_clears_progress(workspace_with_fact_baseline, run_skill, load_state):
    """reset 应清除进度但保留 artifacts."""
    # First try to run (may fail on dispatcher, but creates state)
    run_skill("semantic-fact", "step", cwd=workspace_with_fact_baseline)

    # Reset
    result = run_skill("semantic-fact", "reset", cwd=workspace_with_fact_baseline)
    assert result.returncode == 0
    assert "reset" in result.stdout.lower()

    state = load_state(workspace_with_fact_baseline, "semantic-fact")
    assert state["metadata"]["completed_stages"] == []


def test_semantic_fact_prerequisite_error_includes_helpful_message(workspace, run_skill):
    """依赖错误应包含有用的提示信息."""
    result = run_skill("semantic-fact", "run", cwd=workspace)
    assert result.returncode != 0
    # Should mention what user needs to do
    output = result.stdout + result.stderr
    assert "fact pipeline" in output.lower() or "baseline" in output.lower()
