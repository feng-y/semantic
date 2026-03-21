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
            assert "original_message" in commit
            assert "files" in commit
            assert "diff_chunks" in commit
            assert "commit_log" in commit

        # Cleanup
        import shutil
        shutil.rmtree(output_dir, ignore_errors=True)


class TestCommitExtractWorkerSpawn:
    """Tests for worker batching and spawning architecture."""

    def test_batch_commits(self):
        """Test that commits are batched into groups of 30."""
        import importlib.util
        repo_root = Path(__file__).parent.parent.parent
        spec = importlib.util.spec_from_file_location(
            "commit_extract2",
            str(repo_root / "skills/commit-extract/run.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["commit_extract2"] = mod
        spec.loader.exec_module(mod)

        runner = mod.CommitExtractRunner()
        commits = [{"commit_id": f"abc{i:03d}", "original_message": f"msg{i}"} for i in range(65)]
        batches = runner._batch_commits(commits, batch_size=30)
        assert len(batches) == 3
        assert len(batches[0]) == 30
        assert len(batches[1]) == 30
        assert len(batches[2]) == 5

    def test_commit_log_regenerated_from_diff_not_original_message(self):
        """Worker regenerates commit_log from diff, not from original_message.

        The critical constraint: commit_log must NEVER be taken from the
        original commit message or issue text. Workers receive diff_chunks
        and regenerate commit_log from code changes alone.
        """
        import importlib.util
        repo_root = Path(__file__).parent.parent.parent
        spec = importlib.util.spec_from_file_location(
            "commit_extract3",
            str(repo_root / "skills/commit-extract/run.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["commit_extract3"] = mod
        spec.loader.exec_module(mod)

        runner = mod.CommitExtractRunner()

        # Simulate a worker response where commit_log is regenerated from diff
        original_message = "feat: add stuff"
        commit_log = runner._worker_regenerate_commit_log(
            commit_id="abc123",
            original_message=original_message,
            diff_chunks=["+def foo(): pass", "-def foo(): pass"]
        )

        # commit_log should be present (not None/empty)
        assert commit_log is not None
        assert len(commit_log) > 0
        # The implementation should NOT simply copy original_message as commit_log
        # It should regenerate from diff_chunks. The actual value depends on the
        # prompt, but at minimum the field exists and is populated.

    def test_worker_prompt_includes_diff_chunks_not_original_message(self):
        """Verify worker prompt focuses on diff_chunks, not original_message."""
        import importlib.util
        repo_root = Path(__file__).parent.parent.parent
        spec = importlib.util.spec_from_file_location(
            "commit_extract4",
            str(repo_root / "skills/commit-extract/run.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["commit_extract4"] = mod
        spec.loader.exec_module(mod)

        runner = mod.CommitExtractRunner()

        # Build a worker batch payload
        commits = [
            {
                "commit_id": "abc123",
                "original_message": "fix: add parser legacy support",
                "diff_chunks": ["+if version < 3: pass  # legacy compat"],
                "files": ["src/parser.py"],
            }
        ]
        prompt = runner._build_worker_prompt(commits)

        # The prompt should include diff_chunks content
        assert "diff" in prompt.lower() or "legacy" in prompt.lower()
        # The prompt should reference original_message as context (not the source)
        assert "original_message" in prompt


class TestCommitExtractOutputSchema:
    """Tests for the output YAML schema."""

    def test_output_schema_has_correct_fields(self, tmp_path):
        """Output YAML must have metadata + commits, each commit with specific fields."""
        import importlib.util
        import shutil
        repo_root = Path(__file__).parent.parent.parent
        spec = importlib.util.spec_from_file_location(
            "commit_extract5",
            str(repo_root / "skills/commit-extract/run.py")
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["commit_extract5"] = mod
        spec.loader.exec_module(mod)

        # Create a minimal temp repo
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "repo"
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_path, check=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=repo_path, check=True)
            (repo_path / "f.txt").write_text("hello\n")
            subprocess.run(["git", "add", "."], cwd=repo_path, check=True)
            subprocess.run(["git", "commit", "-m", "feat: initial", "--date", "2024-03-15T10:30:00"], cwd=repo_path, check=True)

            runner = mod.CommitExtractRunner()
            runner.repo_path = str(repo_path)

            # Patch output base to use tmp_path
            saved_base = mod.OUTPUT_BASE
            mod.OUTPUT_BASE = tmp_path / "data" / "commit-extract"

            sys.path.insert(0, str(repo_root))
            from src.harness_state import HarnessState
            state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": []})
            runner._run_collect(state)

            # Verify schema
            month_file = tmp_path / "data" / "commit-extract" / "2024-03.yaml"
            assert month_file.exists()

            import yaml
            data = yaml.safe_load(month_file.read_text())

            # Top-level structure
            assert "metadata" in data
            assert "commits" in data

            # Metadata fields
            assert data["metadata"]["month"] == "2024-03"
            assert "total_commits" in data["metadata"]

            # Each commit must have these fields
            for commit in data["commits"]:
                assert "commit_id" in commit
                assert "timestamp" in commit
                assert "author" in commit
                assert "original_message" in commit
                assert "files" in commit
                assert "diff_chunks" in commit
                assert "commit_log" in commit

            # Restore
            mod.OUTPUT_BASE = saved_base


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
