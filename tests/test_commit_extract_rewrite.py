"""Tests for commit-extract rewrite and commit-semantic 4-stage pipeline."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.io_utils import append_jsonl, load_jsonl, save_jsonl


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_path_clean(tmp_path):
    """Provide a clean tmp_path."""
    return tmp_path


@pytest.fixture
def sample_commit_records():
    """Sample JSONL records matching commit-extract output schema."""
    return [
        {
            "sha": "aaa111", "author": "yan.", "date": "2026-03-01T10:00:00",
            "is_large_aggregate": False, "is_mixed": False,
            "sections": [
                {"name": "Request lifecycle", "theme": "auth-flow", "importance": "primary",
                 "items": [{"op": "feat", "summary": "Add OAuth2 token refresh"}]},
                {"name": "Error handling", "theme": "retry-logic", "importance": "secondary",
                 "items": [{"op": "bugfix", "summary": "Fix retry backoff overflow"}]},
            ],
            "rules_invariants": [
                {"kind": "lifecycle", "statement": "Tokens refreshed before expiry",
                 "enforced_by_commit": True}
            ],
        },
        {
            "sha": "bbb222", "author": "yan.", "date": "2026-03-02T11:00:00",
            "is_large_aggregate": True, "is_mixed": True,
            "sections": [
                {"name": "Auth module", "theme": "auth-flow", "importance": "primary",
                 "items": [{"op": "feat", "summary": "Add SAML SSO support"}]},
            ],
            "rules_invariants": [],
        },
        {
            "sha": "ccc333", "author": "bob", "date": "2026-03-05T09:00:00",
            "is_large_aggregate": False, "is_mixed": False,
            "sections": [
                {"name": "Auth", "theme": "auth-flow", "importance": "primary",
                 "items": [{"op": "feat", "summary": "Add MFA enrollment flow"}]},
                {"name": "Config", "theme": "config-mgmt", "importance": "secondary",
                 "items": [{"op": "config", "summary": "Add MFA config flags"}]},
            ],
            "rules_invariants": [
                {"kind": "lifecycle", "statement": "Tokens refreshed before expiry",
                 "enforced_by_commit": True}
            ],
        },
        {
            "sha": "ddd444", "author": "yan.", "date": "2026-03-10T14:00:00",
            "is_large_aggregate": False, "is_mixed": False,
            "sections": [
                {"name": "Auth", "theme": "auth-flow", "importance": "secondary",
                 "items": [{"op": "refactor", "summary": "Simplify auth middleware"}]},
            ],
            "rules_invariants": [],
        },
    ]


# ---------------------------------------------------------------------------
# commit-extract: parse_stat
# ---------------------------------------------------------------------------

def _load_extract_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ce_run", str(Path(__file__).parent.parent / "skills" / "commit-extract" / "run.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestParseStat:
    def setup_method(self):
        self.mod = _load_extract_module()

    def test_normal_stat(self):
        output = " 3 files changed, 100 insertions(+), 50 deletions(-)"
        assert self.mod.parse_stat(output) == 150

    def test_insertions_only(self):
        output = " 1 file changed, 10 insertions(+)"
        assert self.mod.parse_stat(output) == 10

    def test_deletions_only(self):
        output = " 2 files changed, 30 deletions(-)"
        assert self.mod.parse_stat(output) == 30

    def test_binary_file(self):
        output = " Bin 0 -> 1024 bytes"
        assert self.mod.parse_stat(output) == 500

    def test_binary_plus_text(self):
        output = " 1 file changed, 5 insertions(+), 3 deletions(-)\n Bin 0 -> 100 bytes"
        assert self.mod.parse_stat(output) == 508

    def test_empty_commit(self):
        assert self.mod.parse_stat("") == 0

    def test_multiple_binaries(self):
        output = " Bin 0 -> 100 bytes\n Bin 200 -> 300 bytes"
        assert self.mod.parse_stat(output) == 1000


# ---------------------------------------------------------------------------
# commit-extract: adaptive_batch
# ---------------------------------------------------------------------------

class TestAdaptiveBatch:
    def setup_method(self):
        self.mod = _load_extract_module()

    def test_within_budget(self):
        sha_weights = [("a", 500), ("b", 500), ("c", 500)]
        batches = self.mod.adaptive_batch(sha_weights)
        assert batches == [["a", "b", "c"]]

    def test_budget_overflow(self):
        sha_weights = [("a", 1000), ("b", 1000), ("c", 1000), ("d", 500)]
        batches = self.mod.adaptive_batch(sha_weights)
        assert batches == [["a", "b", "c"], ["d"]]

    def test_count_cap(self):
        sha_weights = [(f"s{i}", 1) for i in range(20)]
        batches = self.mod.adaptive_batch(sha_weights)
        assert len(batches[0]) == 15
        assert len(batches[1]) == 5

    def test_oversized_commit_solo(self):
        sha_weights = [("a", 100), ("b", 5000), ("c", 100)]
        batches = self.mod.adaptive_batch(sha_weights)
        assert ["b"] in batches

    def test_empty_input(self):
        assert self.mod.adaptive_batch([]) == []

    def test_all_oversized(self):
        sha_weights = [("a", 4000), ("b", 5000)]
        batches = self.mod.adaptive_batch(sha_weights)
        assert batches == [["a"], ["b"]]


# ---------------------------------------------------------------------------
# io_utils: append_jsonl
# ---------------------------------------------------------------------------

class TestAppendJsonl:
    def test_create_new(self, tmp_path_clean):
        path = str(tmp_path_clean / "test.jsonl")
        append_jsonl([{"a": 1}], path)
        records = load_jsonl(path)
        assert len(records) == 1
        assert records[0]["a"] == 1

    def test_append_existing(self, tmp_path_clean):
        path = str(tmp_path_clean / "test.jsonl")
        append_jsonl([{"a": 1}], path)
        append_jsonl([{"b": 2}], path)
        records = load_jsonl(path)
        assert len(records) == 2
        assert records[0]["a"] == 1
        assert records[1]["b"] == 2

    def test_unicode(self, tmp_path_clean):
        path = str(tmp_path_clean / "test.jsonl")
        append_jsonl([{"msg": "新增功能"}], path)
        records = load_jsonl(path)
        assert records[0]["msg"] == "新增功能"


# ---------------------------------------------------------------------------
# commit-extract: merge
# ---------------------------------------------------------------------------

class TestMerge:
    def setup_method(self):
        self.mod = _load_extract_module()

    def test_dedup_by_sha(self, tmp_path_clean):
        tmp_dir = tmp_path_clean / "tmp"
        tmp_dir.mkdir()
        output_base = tmp_path_clean

        # Two files with overlapping SHA
        with open(tmp_dir / "batch_0000.jsonl", "w") as f:
            f.write(json.dumps({"sha": "aaa", "date": "2026-03-01"}) + "\n")
            f.write(json.dumps({"sha": "bbb", "date": "2026-03-01"}) + "\n")
        with open(tmp_dir / "batch_0001.jsonl", "w") as f:
            f.write(json.dumps({"sha": "aaa", "date": "2026-03-01", "extra": True}) + "\n")
            f.write(json.dumps({"sha": "ccc", "date": "2026-03-02"}) + "\n")

        merged = self.mod.merge_tmp_files(output_base, tmp_dir)
        assert merged == 3  # aaa (deduped), bbb, ccc

        # aaa should have the later version (with extra field)
        records = load_jsonl(str(output_base / "2026-03.jsonl"))
        aaa = [r for r in records if r["sha"] == "aaa"][0]
        assert aaa.get("extra") is True

    def test_skip_invalid_json(self, tmp_path_clean):
        tmp_dir = tmp_path_clean / "tmp"
        tmp_dir.mkdir()
        output_base = tmp_path_clean

        with open(tmp_dir / "batch_0000.jsonl", "w") as f:
            f.write(json.dumps({"sha": "aaa", "date": "2026-03-01"}) + "\n")
            f.write("TRUNCATED{invalid\n")
            f.write(json.dumps({"sha": "bbb", "date": "2026-03-01"}) + "\n")

        merged = self.mod.merge_tmp_files(output_base, tmp_dir)
        assert merged == 2

    def test_incremental_append(self, tmp_path_clean):
        tmp_dir = tmp_path_clean / "tmp"
        tmp_dir.mkdir()
        output_base = tmp_path_clean

        # Pre-existing file
        save_jsonl([{"sha": "existing", "date": "2026-03-01"}],
                   str(output_base / "2026-03.jsonl"))

        with open(tmp_dir / "batch_0000.jsonl", "w") as f:
            f.write(json.dumps({"sha": "existing", "date": "2026-03-01"}) + "\n")
            f.write(json.dumps({"sha": "new_one", "date": "2026-03-01"}) + "\n")

        merged = self.mod.merge_tmp_files(output_base, tmp_dir)
        assert merged == 1  # only new_one

        records = load_jsonl(str(output_base / "2026-03.jsonl"))
        assert len(records) == 2

    def test_cleanup_tmp(self, tmp_path_clean):
        tmp_dir = tmp_path_clean / "tmp"
        tmp_dir.mkdir()
        output_base = tmp_path_clean

        with open(tmp_dir / "batch_0000.jsonl", "w") as f:
            f.write(json.dumps({"sha": "a", "date": "2026-01-01"}) + "\n")

        self.mod.merge_tmp_files(output_base, tmp_dir)
        assert not tmp_dir.exists()


# ---------------------------------------------------------------------------
# commit-semantic: ingest
# ---------------------------------------------------------------------------

def _load_semantic_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cs_run", str(Path(__file__).parent.parent / "skills" / "commit-semantic" / "run.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class TestSchemaValidation:
    def test_worker_output_required_fields(self):
        """Worker JSON must contain sha, date, sections."""
        valid = {"sha": "abc", "date": "2026-01-01", "sections": []}
        assert "sha" in valid
        assert "date" in valid
        assert "sections" in valid

        # Missing sha → would be skipped by merge
        mod = _load_extract_module()
        tmp = Path("/tmp/test_schema_validation")
        tmp.mkdir(parents=True, exist_ok=True)
        tmp_dir = tmp / "tmp"
        tmp_dir.mkdir(exist_ok=True)

        with open(tmp_dir / "batch.jsonl", "w") as f:
            f.write(json.dumps({"date": "2026-01-01", "sections": []}) + "\n")  # no sha
            f.write(json.dumps({"sha": "abc", "date": "2026-01-01", "sections": []}) + "\n")

        merged = mod.merge_tmp_files(tmp, tmp_dir)
        assert merged == 1  # only the one with sha

        # Cleanup
        for f in tmp.glob("**/*"):
            if f.is_file():
                f.unlink()
        for d in sorted(tmp.glob("**"), reverse=True):
            if d.is_dir():
                d.rmdir()
