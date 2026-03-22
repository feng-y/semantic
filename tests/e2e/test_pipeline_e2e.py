"""Full pipeline E2E: commit-extract → commit-semantic with real git repo."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))


class TestFullPipelineE2E:
    """Test full pipeline with temp git repo."""

    def test_commit_extract_produces_batch_manifest(self, temp_git_repo: Path, tmp_path: Path):
        """commit-extract orchestrator prints a batch manifest with SHAs."""
        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-extract/run.py"),
             "run", "--repo", str(temp_git_repo)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"commit-extract failed: {result.stderr}"

        # Should print a batch manifest
        assert "BATCH MANIFEST" in result.stdout

        # Extract manifest JSON
        start = result.stdout.index("=== BATCH MANIFEST ===") + len("=== BATCH MANIFEST ===")
        end = result.stdout.index("=== END MANIFEST ===")
        manifest = json.loads(result.stdout[start:end].strip())

        assert len(manifest) >= 1, "Should have at least one batch"
        for batch in manifest:
            assert "batch_id" in batch
            assert "shas" in batch
            assert "output_path" in batch
            assert len(batch["shas"]) >= 1

        # tmp/ directory should be created
        assert (tmp_path / "data" / "commit-extract" / "tmp").exists()

    def test_commit_semantic_reads_jsonl_and_produces_output(self, tmp_path: Path):
        """commit-semantic ingest reads JSONL and produces units."""
        # Create mock JSONL extract output
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        records = [
            {
                "sha": "abc123",
                "author": "Test",
                "date": "2024-01-15T10:00:00",
                "is_large_aggregate": False,
                "is_mixed": False,
                "sections": [{
                    "name": "Request lifecycle",
                    "theme": "auth flow",
                    "importance": "primary",
                    "summary": "Add auth",
                    "items": [{"op": "feat", "summary": "add login endpoint"}],
                }],
                "rules_invariants": [],
            },
            {
                "sha": "def456",
                "author": "Test",
                "date": "2024-01-16T10:00:00",
                "is_large_aggregate": False,
                "is_mixed": False,
                "sections": [{
                    "name": "Failure handling",
                    "theme": "error recovery",
                    "importance": "secondary",
                    "summary": "Fix crash",
                    "items": [{"op": "bugfix", "summary": "handle null input"}],
                }],
                "rules_invariants": [],
            },
        ]

        with open(extract_dir / "2024-01.jsonl", "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        # Run ingest
        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-semantic/run.py"),
             "run", "--stage", "ingest"],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 0, f"ingest failed: {result.stderr}"

        # Verify units JSONL
        units_file = tmp_path / "data" / "commit-semantic" / "units" / "all.jsonl"
        assert units_file.exists()
        units = [json.loads(line) for line in units_file.read_text().splitlines() if line.strip()]
        assert len(units) == 2

    def test_pipeline_produces_correct_output_structure(self, tmp_path: Path):
        """Full 4-stage pipeline produces expected output files."""
        # Create mock JSONL extract output with enough data for aggregation
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        records = [
            {
                "sha": f"sha{i:03d}",
                "author": "Test",
                "date": f"2024-01-{10+i}T10:00:00",
                "is_large_aggregate": False,
                "is_mixed": False,
                "sections": [{
                    "name": "Runtime behavior",
                    "theme": "batch processing",
                    "importance": "primary",
                    "items": [{"op": "feat", "summary": f"feature {i}"}],
                }],
                "rules_invariants": [],
            }
            for i in range(5)
        ]

        with open(extract_dir / "2024-01.jsonl", "w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        # Run all 4 stages
        for stage in ["ingest", "aggregate", "distill", "export"]:
            result = subprocess.run(
                [sys.executable, str(repo_root / "skills/commit-semantic/run.py"),
                 "run", "--stage", stage],
                capture_output=True, text=True, cwd=tmp_path,
            )
            assert result.returncode == 0, f"commit-semantic {stage} failed: {result.stderr}"

        # Verify output structure
        semantic_dir = tmp_path / "data" / "commit-semantic"
        assert (semantic_dir / "units" / "all.jsonl").exists()
        assert (semantic_dir / "invariants.jsonl").exists()
        assert (semantic_dir / "patterns.jsonl").exists()
        assert (semantic_dir / "canonical-demands.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()

        # Verify summary.json is valid
        summary = json.loads((semantic_dir / "summary.json").read_text())
        assert "total_units" in summary
        assert "total_patterns" in summary
        assert "bugfix_ratio" in summary
