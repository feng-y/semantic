"""Shared fixtures for E2E tests."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create isolated workspace with .harness structure (no outputs)."""
    harness = tmp_path / ".harness"
    (harness / "state/commit-extract").mkdir(parents=True)
    (harness / "state/commit-semantic").mkdir(parents=True)
    (harness / "state/semantic-fact").mkdir(parents=True)
    # Note: outputs are created by specific fixtures as needed
    return tmp_path


@pytest.fixture
def workspace_with_fact_baseline(tmp_path: Path) -> Path:
    """Create workspace with mock fact baseline."""
    # Create baseline directory
    baseline_dir = tmp_path / "docs" / "fact" / "baseline"
    baseline_dir.mkdir(parents=True)

    # Create mock baseline file
    (baseline_dir / "repo-facts.v1.md").write_text("# Mock Baseline\n\nTest content.\n")

    # Create .harness structure
    harness = tmp_path / ".harness"
    (harness / "state/semantic-fact").mkdir(parents=True)
    (harness / "outputs/semantic-fact/discovery").mkdir(parents=True)

    return tmp_path


@pytest.fixture
def workspace_with_extract_output(tmp_path: Path) -> Path:
    """Create workspace with mock commit-extract output for commit-semantic tests."""
    # Create .harness structure
    harness = tmp_path / ".harness"
    (harness / "state/commit-extract").mkdir(parents=True)
    (harness / "state/commit-semantic").mkdir(parents=True)

    # Create mock commit-extract output directory
    (harness / "outputs/commit-extract").mkdir(parents=True)
    # Create a mock patterns file
    (harness / "outputs/commit-extract/patterns.yaml").write_text("# Mock patterns\n")

    return tmp_path


@pytest.fixture
def run_skill():
    """Factory for running skills in test workspace."""
    repo_root = Path(__file__).parent.parent.parent
    def _run(skill: str, args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(repo_root / f"skills/{skill}/run.py")] + args.split()
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
        )
    return _run


@pytest.fixture
def load_state():
    """Load state JSON from workspace."""
    def _load(workspace: Path, skill: str) -> dict | None:
        path = workspace / ".harness" / "state" / skill / "state.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())
    return _load
