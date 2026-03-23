"""Full pipeline E2E: commit-extract → commit-semantic with real git repo.

Updated for new architecture: JSONL output, 4-stage semantic pipeline.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))


class TestFullPipelineE2E:
    """Test full pipeline with temp git repo."""

    def test_commit_extract_produces_manifest(self, temp_git_repo: Path, tmp_path: Path):
        """commit-extract run completes locally and writes monthly JSONL output."""
        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-extract/run.py"), "run",
             "--repo", str(temp_git_repo)],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 0, f"commit-extract failed: {result.stderr}\n{result.stdout}"

        extract_dir = tmp_path / "data" / "commit-extract"
        manifest = extract_dir / "tmp" / "manifest.json"
        monthly_files = sorted(extract_dir.glob("????-??.jsonl"))

        assert manifest.exists(), f"manifest.json not found at {manifest}"
        assert monthly_files, f"monthly JSONL not found in {extract_dir}"

        data = json.loads(manifest.read_text())
        assert data["total_shas"] >= 1
        assert len(data["batches"]) >= 1

        records = [json.loads(line) for line in monthly_files[0].read_text().splitlines() if line.strip()]
        assert records, "monthly JSONL should contain at least one record"
        assert {"sha", "author", "date", "sections", "rules_invariants"}.issubset(records[0])

    def test_commit_semantic_ingest_stage(self, temp_git_repo: Path, tmp_path: Path):
        """commit-semantic ingest reads JSONL and produces units."""
        # Create fixture JSONL (simulating worker output)
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        from src.io_utils import save_jsonl
        save_jsonl([
            {
                "sha": "abc123", "author": "test", "date": "2026-03-01T10:00:00",
                "is_large_aggregate": False, "is_mixed": False,
                "sections": [
                    {"name": "Auth", "theme": "auth", "importance": "primary",
                     "items": [{"op": "feat", "summary": "Add login"}]}
                ],
                "rules_invariants": [],
            }
        ], str(extract_dir / "2026-03.jsonl"))

        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-semantic/run.py"),
             "run", "--stage", "ingest"],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 0, f"ingest failed: {result.stderr}\n{result.stdout}"

        units_file = tmp_path / "data" / "commit-semantic" / "units" / "all.jsonl"
        assert units_file.exists()

    def test_pipeline_produces_correct_output_structure(self, temp_git_repo: Path, tmp_path: Path):
        """Full semantic pipeline produces expected JSONL structure."""
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        from src.io_utils import save_jsonl
        records = [
            {"sha": f"sha{i}", "author": "t", "date": f"2026-03-0{i+1}T10:00:00",
             "is_large_aggregate": False, "is_mixed": False,
             "sections": [{"name": "X", "theme": "common-theme", "importance": "primary",
                           "items": [{"op": "feat", "summary": f"Change {i}"}]}],
             "rules_invariants": []}
            for i in range(4)
        ]
        save_jsonl(records, str(extract_dir / "2026-03.jsonl"))

        for stage in ["ingest", "aggregate", "distill", "export"]:
            result = subprocess.run(
                [sys.executable, str(repo_root / "skills/commit-semantic/run.py"),
                 "run", "--stage", stage],
                capture_output=True, text=True, cwd=tmp_path,
            )
            assert result.returncode == 0, f"{stage} failed: {result.stderr}\n{result.stdout}"

        semantic_dir = tmp_path / "data" / "commit-semantic"
        assert (semantic_dir / "units" / "all.jsonl").exists()
        assert (semantic_dir / "invariants.jsonl").exists()
        assert (semantic_dir / "domains-aggregated.jsonl").exists()
        assert (semantic_dir / "canonical-demands.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()
