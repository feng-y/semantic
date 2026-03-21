"""E2E tests for commit-extract skill."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_extract_run_full_pipeline(workspace: Path, run_skill):
    """Run full pipeline completes with artifacts."""
    result = run_skill("commit-extract", "run", cwd=workspace)

    assert result.returncode == 0
    assert "Complete" in result.stdout or "breakpoint" in result.stdout

    # Check state file created
    state_path = workspace / ".harness/state/commit-extract/run-state.json"
    assert state_path.exists()

    state = json.loads(state_path.read_text())
    assert state["command"] == "commit-extract"
    assert "collect" in state["completed_stages"]


def test_extract_status_no_state(workspace: Path, run_skill):
    """Status reports no state before run."""
    result = run_skill("commit-extract", "status", cwd=workspace)

    assert result.returncode == 0
    assert "No state found" in result.stdout


def test_extract_step_and_breakpoint(workspace: Path, run_skill, load_state):
    """Step runs single stage and sets breakpoint."""
    # First step
    result = run_skill("commit-extract", "step", cwd=workspace)
    assert result.returncode == 0

    state = load_state(workspace, "commit-extract")
    assert state is not None
    assert state["status"] == "breakpoint"
    assert "collect" in state["completed_stages"]
    assert state["current_stage"] is None  # Completed, not running


def test_extract_resume_continues(workspace: Path, run_skill, load_state):
    """Resume continues from breakpoint to completion."""
    # Set up partial state
    run_skill("commit-extract", "step", cwd=workspace)  # Does one stage

    # Resume should complete remaining stages
    result = run_skill("commit-extract", "resume", cwd=workspace)
    assert result.returncode == 0

    state = load_state(workspace, "commit-extract")
    assert state["status"] == "ok"
    assert len(state["completed_stages"]) == 3  # All stages


def test_extract_reset_clears_state(workspace: Path, run_skill, load_state):
    """Reset clears state but preserves artifacts."""
    # Run to create state
    run_skill("commit-extract", "run", cwd=workspace)

    # Reset
    result = run_skill("commit-extract", "reset", cwd=workspace)
    assert result.returncode == 0
    assert "reset" in result.stdout.lower()

    state = load_state(workspace, "commit-extract")
    assert state["completed_stages"] == []


def test_extract_status_reports_correctly(workspace: Path, run_skill):
    """Status reports current stage and artifacts."""
    run_skill("commit-extract", "step", cwd=workspace)

    result = run_skill("commit-extract", "status", cwd=workspace)
    assert result.returncode == 0
    assert "breakpoint" in result.stdout.lower() or "stage" in result.stdout.lower()
