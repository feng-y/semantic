"""E2E tests for commit-extract skill (rewritten architecture).

Tests the new orchestrator + adaptive batching + JSONL output.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def load_commit_extract_module():
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
    """Basic skill structure tests."""

    def test_skill_exists(self):
        mod = load_commit_extract_module()
        runner = mod.CommitExtractRunner()
        assert runner.PIPELINE == "commit-extract"
        assert runner.STAGES == ["collect"]

    def test_collect_produces_manifest(self):
        """Collect stage produces a batch manifest for workers."""
        mod = load_commit_extract_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "T"], cwd=repo_path, capture_output=True, check=True)
            (repo_path / "f.txt").write_text("hello\n")
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "commit", "-m", "feat: initial"], cwd=repo_path, capture_output=True, check=True)

            runner = mod.CommitExtractRunner()
            runner.repo_path = str(repo_path)
            runner.auto_confirm = True  # Skip interactive confirmation

            # Patch output to tmp
            saved_base = mod.OUTPUT_BASE
            saved_tmp = mod.TMP_DIR
            mod.OUTPUT_BASE = Path(tmpdir) / "output"
            mod.TMP_DIR = mod.OUTPUT_BASE / "tmp"

            from src.harness_state import HarnessState
            state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
            result = runner._run_collect(state)

            mod.OUTPUT_BASE = saved_base
            mod.TMP_DIR = saved_tmp

            assert result is True

            manifest_path = Path(tmpdir) / "output" / "tmp" / "manifest.json"
            assert manifest_path.exists()

            manifest = json.loads(manifest_path.read_text())
            assert manifest["total_shas"] == 1
            assert len(manifest["batches"]) == 1
            assert len(manifest["batches"][0]["shas"]) == 1

    def test_collect_local_fallback_writes_monthly_jsonl(self):
        """LLM mode creates manifest and batch files, not direct monthly output."""
        mod = load_commit_extract_module()

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir) / "test_repo"
            repo_path.mkdir()
            subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True, check=True)

            (repo_path / "f.txt").write_text("hello\n")
            subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True, check=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: add login\n\nEnsure auth stays enabled."],
                cwd=repo_path,
                capture_output=True,
                check=True,
            )

            runner = mod.CommitExtractRunner()
            runner.repo_path = str(repo_path)
            runner.auto_confirm = True  # Skip interactive confirmation

            saved_base = mod.OUTPUT_BASE
            saved_tmp = mod.TMP_DIR
            mod.OUTPUT_BASE = Path(tmpdir) / "output"
            mod.TMP_DIR = mod.OUTPUT_BASE / "tmp"

            from src.harness_state import HarnessState
            state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
            result = runner._run_collect(state)

            # LLM mode: manifest created with batch definitions
            # Batch files are written by workers, not orchestrator
            manifest_path = Path(tmpdir) / "output" / "tmp" / "manifest.json"

            mod.OUTPUT_BASE = saved_base
            mod.TMP_DIR = saved_tmp

            assert result is True
            assert manifest_path.exists(), "Manifest should be created"

            # Verify manifest structure
            manifest = json.loads(manifest_path.read_text())
            assert manifest["total_shas"] == 1
            assert len(manifest["batches"]) == 1
            assert manifest["batches"][0]["batch_id"] == "batch_0000"


class TestCommitExtractParseStat:
    """Tests for git show --stat parsing."""

    def setup_method(self):
        self.mod = load_commit_extract_module()

    def test_normal(self):
        assert self.mod.parse_stat(" 3 files changed, 100 insertions(+), 50 deletions(-)") == 150

    def test_insertions_only(self):
        assert self.mod.parse_stat(" 1 file changed, 10 insertions(+)") == 10

    def test_deletions_only(self):
        assert self.mod.parse_stat(" 2 files changed, 30 deletions(-)") == 30

    def test_binary(self):
        assert self.mod.parse_stat(" Bin 0 -> 1024 bytes") == 500

    def test_empty(self):
        assert self.mod.parse_stat("") == 0


class TestCommitExtractAdaptiveBatch:
    """Tests for adaptive batching by weight."""

    def setup_method(self):
        self.mod = load_commit_extract_module()

    def test_within_budget(self):
        batches = self.mod.adaptive_batch([("a", 500), ("b", 500), ("c", 500)])
        assert batches == [["a", "b", "c"]]

    def test_budget_overflow(self):
        batches = self.mod.adaptive_batch([("a", 1000), ("b", 1000), ("c", 1000), ("d", 500)])
        assert batches == [["a", "b", "c"], ["d"]]

    def test_count_cap(self):
        sha_weights = [(f"s{i}", 1) for i in range(20)]
        batches = self.mod.adaptive_batch(sha_weights)
        assert len(batches[0]) == 15
        assert len(batches[1]) == 5

    def test_oversized_solo(self):
        batches = self.mod.adaptive_batch([("a", 100), ("b", 5000), ("c", 100)])
        assert ["b"] in batches

    def test_empty(self):
        assert self.mod.adaptive_batch([]) == []


class TestCommitExtractMerge:
    """Tests for merge_tmp_files."""

    def setup_method(self):
        self.mod = load_commit_extract_module()

    def test_dedup_by_sha(self, tmp_path):
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        with open(tmp_dir / "b0.jsonl", "w") as f:
            f.write(json.dumps({"sha": "aaa", "date": "2026-03-01"}) + "\n")
        with open(tmp_dir / "b1.jsonl", "w") as f:
            f.write(json.dumps({"sha": "aaa", "date": "2026-03-01", "extra": True}) + "\n")
            f.write(json.dumps({"sha": "bbb", "date": "2026-03-01"}) + "\n")

        merged = self.mod.merge_tmp_files(tmp_path, tmp_dir)
        assert merged == 2  # aaa (deduped) + bbb

    def test_skip_invalid_json(self, tmp_path):
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        with open(tmp_dir / "b0.jsonl", "w") as f:
            f.write(json.dumps({"sha": "aaa", "date": "2026-03-01"}) + "\n")
            f.write("TRUNCATED{invalid\n")

        merged = self.mod.merge_tmp_files(tmp_path, tmp_dir)
        assert merged == 1

    def test_incremental_append(self, tmp_path):
        from src.io_utils import save_jsonl, load_jsonl
        tmp_dir = tmp_path / "tmp"
        tmp_dir.mkdir()

        save_jsonl([{"sha": "existing", "date": "2026-03-01"}], str(tmp_path / "2026-03.jsonl"))

        with open(tmp_dir / "b0.jsonl", "w") as f:
            f.write(json.dumps({"sha": "existing", "date": "2026-03-01"}) + "\n")
            f.write(json.dumps({"sha": "new_one", "date": "2026-03-01"}) + "\n")

        merged = self.mod.merge_tmp_files(tmp_path, tmp_dir)
        assert merged == 1

        records = load_jsonl(str(tmp_path / "2026-03.jsonl"))
        assert len(records) == 2


class TestCommitExtractWorkerPrompt:
    """Tests for worker prompt construction."""

    def test_prompt_includes_sha_list(self):
        mod = load_commit_extract_module()
        runner = mod.CommitExtractRunner()
        prompt = runner._build_worker_prompt(["abc123", "def456"])
        assert "abc123" in prompt
        assert "def456" in prompt

    def test_prompt_includes_generate_commit_content(self):
        mod = load_commit_extract_module()
        runner = mod.CommitExtractRunner()
        prompt = runner._build_worker_prompt(["abc123"])
        # Should include content from docs/generate_commit.md
        assert "sections" in prompt.lower() or "json" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
