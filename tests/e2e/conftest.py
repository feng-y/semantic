"""Shared fixtures for E2E tests."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create isolated workspace with .harness structure."""
    harness = tmp_path / ".harness"
    (harness / "state/commit-extract").mkdir(parents=True)
    (harness / "state/commit-semantic").mkdir(parents=True)
    (harness / "outputs/commit-extract/commits").mkdir(parents=True)
    (harness / "outputs/commit-semantic/patterns").mkdir(parents=True)
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
