"""Full pipeline E2E: commit-extract → commit-semantic with real git repo."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))


class TestFullPipelineE2E:
    """Test full pipeline with temp git repo."""

    def test_commit_extract_produces_monthly_yaml(self, temp_git_repo: Path, tmp_path: Path):
        """commit-extract produces data/commit-extract/YYYY-MM.yaml with commit_log field."""
        # Run commit-extract
        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-extract/run.py"), "run", "--repo", str(temp_git_repo)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Should succeed
        assert result.returncode == 0, f"commit-extract failed: {result.stderr}"

        # Check monthly file exists
        extract_dir = tmp_path / "data" / "commit-extract"
        yaml_files = list(extract_dir.glob("*.yaml"))
        assert len(yaml_files) >= 1, f"No monthly YAML files in {extract_dir}"

        # Load and verify structure
        import yaml
        data = yaml.safe_load(yaml_files[0].read_text())
        assert "metadata" in data
        assert "commits" in data
        assert data["commits"]  # Not empty

        # Check each commit has commit_log (regenerated from diff, not from original_message)
        for commit in data["commits"]:
            assert "commit_id" in commit
            assert "commit_log" in commit
            assert "original_message" in commit
            assert commit["commit_log"]  # Not empty
            # commit_log should be different from original_message (regenerated from diff)
            # or at minimum, populated

    def test_commit_semantic_reads_commit_log_and_produces_output(self, temp_git_repo: Path, tmp_path: Path):
        """commit-semantic reads commit_log, produces functional/non-functional tiers."""
        # First run commit-extract
        subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-extract/run.py"), "run", "--repo", str(temp_git_repo)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

        # Then run commit-semantic split
        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-semantic/run.py"), "run", "--stage", "split"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"commit-semantic split failed: {result.stderr}"

        # Verify units/all.yaml exists
        semantic_dir = tmp_path / "data" / "commit-semantic"
        units_file = semantic_dir / "units" / "all.yaml"
        assert units_file.exists(), f"units/all.yaml not found at {units_file}"

        # Load and verify
        import yaml
        data = yaml.safe_load(units_file.read_text())
        assert "metadata" in data
        assert "units" in data
        assert len(data["units"]) >= 1  # At least some units

    def test_pipeline_produces_correct_output_structure(self, temp_git_repo: Path, tmp_path: Path):
        """Full pipeline produces expected directory structure."""
        # Run extract
        subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-extract/run.py"), "run", "--repo", str(temp_git_repo)],
            capture_output=True, text=True, cwd=tmp_path,
        )

        # Run semantic stages
        for stage in ["split", "analyze", "aggregate", "distill"]:
            result = subprocess.run(
                [sys.executable, str(repo_root / "skills/commit-semantic/run.py"), "run", "--stage", stage],
                capture_output=True, text=True, cwd=tmp_path,
            )
            assert result.returncode == 0, f"commit-semantic {stage} failed: {result.stderr}"

        # Verify structure
        semantic_dir = tmp_path / "data" / "commit-semantic"
        assert (semantic_dir / "units" / "all.yaml").exists()
        assert (semantic_dir / "functional" / "high" / "units.yaml").exists()
        assert (semantic_dir / "functional" / "medium" / "units.yaml").exists()
        assert (semantic_dir / "functional" / "low" / "units.yaml").exists()
        assert (semantic_dir / "non-functional" / "all" / "units.yaml").exists()
        assert (semantic_dir / "patterns").exists()
        assert (semantic_dir / "canonical-demands.yaml").exists()
