"""E2E tests for commit-extract skill."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Helper to load skill module
def load_commit_extract_module():
    """Load commit-extract skill module."""
    import importlib.util
    repo_root = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "commit_extract",
        str(repo_root / "skills/commit-extract/run.py")
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_extract"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestCommitExtractSkill:
    """E2E tests for commit-extract skill."""

    @pytest.fixture
    def mock_repo(self):
        """Create a temporary git repo with test commits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()

            # Init git repo
            subprocess.run(["git", "init"], cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, check=True)

            # Create initial commit (last month)
            (repo_path / "README.md").write_text("# Test Repo\n")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit", "--date", "2024-01-15T10:00:00"], cwd=repo_path, check=True)

            # Create feature commit
            (repo_path / "src").mkdir()
            (repo_path / "src/parser.py").write_text("def parse(): pass\n")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", "feat: add parser module", "--date", "2024-01-16T11:00:00"], cwd=repo_path, check=True)

            # Create bugfix commit
            (repo_path / "src/parser.py").write_text("def parse(input): return input.strip()\n")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", "bugfix: fix parser boundary", "--date", "2024-01-17T12:00:00"], cwd=repo_path, check=True)

            yield repo_path

    def test_skill_exists(self):
        """Test that commit-extract skill exists."""
        mod = load_commit_extract_module()
        runner = mod.CommitExtractRunner()
        assert runner.PIPELINE == "commit-extract"
        assert runner.STAGES == ["collect"]

    def test_collect_groups_by_month(self, mock_repo, tmp_path):
        """Test that commits are grouped by month."""
        mod = load_commit_extract_module()

        # Setup sys.path for src imports
        repo_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(repo_root))

        from src.harness_state import HarnessState

        runner = mod.CommitExtractRunner()
        runner.repo_path = str(mock_repo)

        state = HarnessState(
            stage="init",
            metadata={"completed_stages": [], "artifacts_written": []}
        )

        # Run collect stage
        result = runner._run_collect(state)
        assert result is True

        # Check output exists
        output_dir = Path("data/commit-extract")
        assert output_dir.exists()

        # Check month file exists
        month_file = output_dir / "2024-01.yaml"
        assert month_file.exists()

        # Load and verify structure
        import yaml
        with open(month_file) as f:
            data = yaml.safe_load(f)

        assert "metadata" in data
        assert "commits" in data
        assert data["metadata"]["month"] == "2024-01"
        assert data["metadata"]["total_commits"] == 3

        # Verify commit structure
        commits = data["commits"]
        assert len(commits) == 3
        for commit in commits:
            assert "commit_id" in commit
            assert "timestamp" in commit
            assert "author" in commit
            assert "commit_message" in commit
            assert "files" in commit
            assert "diff_chunks" in commit

        # Cleanup
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
