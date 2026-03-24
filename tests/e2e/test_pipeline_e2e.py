"""Full pipeline E2E: commit-extract → commit-semantic V1 capability-first contract."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


repo_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(repo_root))


class TestFullPipelineE2E:
    """Test full pipeline with temp git repo and V1 semantic outputs."""

    def test_commit_extract_produces_manifest(self, temp_git_repo: Path, tmp_path: Path):
        result = subprocess.run(
            [sys.executable, str(repo_root / "skills/commit-extract/run.py"), "run",
             "--repo", str(temp_git_repo), "--range", "HEAD", "--yes"],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 0, f"commit-extract failed: {result.stderr}\n{result.stdout}"

        extract_dir = tmp_path / "data" / "commit-extract"
        manifest = extract_dir / "tmp" / "manifest.json"
        assert manifest.exists(), f"manifest.json not found at {manifest}"

        data = json.loads(manifest.read_text())
        assert data["total_shas"] >= 1
        assert len(data["batches"]) >= 1

    def test_commit_semantic_context_stage_requires_orchestration(self, temp_git_repo: Path, tmp_path: Path):
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
            [sys.executable, str(repo_root / "skills/commit-semantic/run.py"), "run", "--stage", "context"],
            capture_output=True, text=True, cwd=tmp_path,
        )
        assert result.returncode == 1, f"context unexpectedly succeeded: {result.stderr}\n{result.stdout}"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        assert not (semantic_dir / "repo-hints.json").exists()

    def test_v1_pipeline_produces_expected_artifacts_with_injected_executor(self, temp_git_repo: Path, tmp_path: Path):
        import importlib.util
        from src.harness_state import HarnessState
        from src.io_utils import save_jsonl, load_json, load_jsonl

        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)

        records = [
            {"sha": f"sha{i}", "author": "t", "date": f"2026-03-0{i+1}T10:00:00",
             "is_large_aggregate": i == 1, "is_mixed": i == 1,
             "sections": [{"name": "X", "theme": "common-theme", "importance": "primary",
                           "items": [{"op": "feat", "summary": f"Change {i}"}]}],
             "rules_invariants": []}
            for i in range(4)
        ]
        save_jsonl(records, str(extract_dir / "2026-03.jsonl"))

        module_path = repo_root / "skills" / "commit-semantic" / "run.py"
        spec = importlib.util.spec_from_file_location("commit_semantic_e2e_run", module_path)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        def executor(prompt_text: str, context: dict[str, str], *, artifact_name: str, sampling_mode: str = "auto") -> str:
            if artifact_name == "repo-hints":
                return json.dumps({
                    "local_capabilities": ["commit-extract", "commit-semantic"],
                    "aliases": [],
                    "ownership_hints": [{"path_prefix": "skills/commit-semantic/", "capability": "commit-semantic"}],
                    "seed_concepts": ["semantic-unit"],
                    "doc_sources": ["README.md"],
                    "confidence": "medium",
                })
            if artifact_name == "capability-signals":
                return json.dumps({
                    "signals": [
                        {
                            "kind": "capability",
                            "name": "semantic-grouping",
                            "description": "Group semantic signals into stable capability candidates",
                            "source_commit": f"sha{i}",
                            "evidence_refs": [f"sha:sha{i}", f"summary:sha{i}"],
                            "confidence": "high" if i < 2 else "medium",
                            "flags": ["mixed"] if i == 1 else [],
                            "related_capability_names": [],
                        }
                        for i in range(4)
                    ]
                })
            if artifact_name == "capability-candidates":
                return json.dumps({
                    "capabilities": [
                        {
                            "capability_id": "cap-semantic-grouping",
                            "canonical_name": "semantic-grouping",
                            "observed_names": ["semantic grouping", "semantic-grouping"],
                            "description": "Group commit-first signals into stable capability views",
                            "evidence_refs": ["sha:sha0", "sha:sha1", "sha:sha2"],
                            "repo_context_refs": ["commit-semantic"],
                            "confidence": "high",
                            "status": "stable",
                            "naming_source": "synthesized",
                            "flags": [],
                        }
                    ]
                })
            raise AssertionError(f"Unexpected artifact_name: {artifact_name}")

        runner = mod.CommitSemanticRunner(executor=executor)
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
        for stage in mod.CommitSemanticRunner.STAGES:
            assert runner.run_stage(stage, state), stage

        assert (semantic_dir / "repo-hints.json").exists()
        assert (semantic_dir / "repo-context.json").exists()
        assert (semantic_dir / "capabilities-candidates.jsonl").exists()
        assert (semantic_dir / "capabilities.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()
        assert not (semantic_dir / "domains-aggregated.jsonl").exists()
        assert not (semantic_dir / "canonical-demands.jsonl").exists()

        caps = load_jsonl(str(semantic_dir / "capabilities.jsonl"))
        summary = load_json(str(semantic_dir / "summary.json"))
        assert len(caps) == 1
        assert caps[0]["capability_id"] == "cap-semantic-grouping"
        assert summary["stable_capability_count"] == 1
        assert summary["evidence_coverage"] > 0
