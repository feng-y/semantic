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
    harness = tmp_path / ".harness"
    (harness / "state/commit-extract").mkdir(parents=True)
    (harness / "state/commit-semantic").mkdir(parents=True)

    # Create mock commit-extract output where the skill expects it (JSONL format)
    extract_dir = tmp_path / "data" / "commit-extract"
    extract_dir.mkdir(parents=True)
    (extract_dir / "2024-01.jsonl").write_text("")

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
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repo with sample commits."""
    repo_dir = tmp_path / "git-repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir, capture_output=True
    )

    # Create a sample file
    (repo_dir / "README.md").write_text("# Test\n")

    # Create commits with different types
    commits = [
        ("feat: add user authentication module", "feat: add user authentication module\n\nImplement login/logout with JWT."),
        ("fix: correct parser edge case", "fix: correct parser edge case\n\nHandle empty input gracefully."),
        ("refactor: simplify reader logic", "refactor: simplify reader logic\n\nExtract helper functions."),
        ("test: add unit tests for client", "test: add unit tests for client\n\nCover happy and error paths."),
        ("config: add CI pipeline", "config: add CI pipeline\n\nGitHub Actions workflow."),
        ("feat: optimize database queries", "feat: optimize database queries\n\nAdd index on user_id."),
        ("bugfix: fix memory leak in server", "bugfix: fix memory leak in server\n\nClose connections properly."),
        ("cleanup: remove dead code", "cleanup: remove dead code\n\nDelete unused helper functions."),
    ]

    for msg, body in commits:
        (repo_dir / "README.md").write_text((repo_dir / "README.md").read_text() + f"\n{msg[:10]}")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"{msg}\n\n{body}"],
            cwd=repo_dir, capture_output=True
        )

    return repo_dir


@pytest.fixture
def load_state():
    """Load state JSON from workspace."""
    def _load(workspace: Path, skill: str) -> dict | None:
        path = workspace / ".harness" / "state" / skill / "state.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())
    return _load
