"""E2E tests for commit-semantic skill (4-stage JSONL pipeline).

Tests: ingest → aggregate → distill → export consuming JSONL from commit-extract.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import save_jsonl, load_jsonl, load_json


def load_commit_semantic_module():
    import importlib.util
    repo_root = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "commit_semantic_test",
        str(repo_root / "skills/commit-semantic/run.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_semantic_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sample_jsonl_records():
    """Sample JSONL records matching new commit-extract output schema."""
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


def _setup_and_run(tmp_path, sample_jsonl_records, stages=None):
    """Helper: write fixture, run stages, return (mod, semantic_dir)."""
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)

    save_jsonl(sample_jsonl_records, str(extract_dir / "2026-03.jsonl"))

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir

    from src.harness_state import HarnessState
    runner = mod.CommitSemanticRunner()
    state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

    for stage in (stages or runner.STAGES):
        runner.run_stage(stage, state)

    return mod, semantic_dir


class TestCommitSemanticSkill:
    """Basic skill structure."""

    def test_skill_exists(self):
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()
        assert runner.PIPELINE == "commit-semantic"
        assert runner.STAGES == ["ingest", "aggregate", "distill", "export"]


class TestCommitSemanticPrerequisites:
    """Prerequisite checking."""

    def test_fails_without_extract_output(self):
        mod = load_commit_semantic_module()
        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = Path("/nonexistent")
        ok, msg = mod.CommitSemanticRunner()._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved
        assert ok is False

    def test_passes_with_jsonl(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        save_jsonl([{"sha": "a"}], str(extract_dir / "2026-03.jsonl"))

        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        ok, _ = mod.CommitSemanticRunner()._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved
        assert ok is True


class TestCommitSemanticIngest:
    """Stage 1: ingest."""

    def test_expand_sections_to_units(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest"])
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        # 2 + 1 + 2 + 1 = 6 items
        assert len(units) == 6

    def test_carry_is_large_aggregate(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest"])
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        large = [u for u in units if u["is_large_aggregate"]]
        assert len(large) == 1
        assert large[0]["sha"] == "bbb222"

    def test_carry_is_mixed(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest"])
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        mixed = [u for u in units if u["is_mixed"]]
        assert len(mixed) == 1

    def test_collect_invariants(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest"])
        invariants = load_jsonl(str(semantic_dir / "invariants.jsonl"))
        assert len(invariants) == 2
        assert all("statement" in inv for inv in invariants)

    def test_skip_invalid_json(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)

        with open(extract_dir / "2026-03.jsonl", "w") as f:
            f.write(json.dumps({"sha": "a", "date": "2026-03-01", "sections": [], "rules_invariants": []}) + "\n")
            f.write("INVALID\n")

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
        ok = runner._run_ingest(state)
        assert ok

    def test_zero_sections_commit(self, tmp_path):
        """Commit with 0 sections produces 0 units."""
        records = [{"sha": "empty", "date": "2026-03-01", "sections": [], "rules_invariants": []}]
        _, semantic_dir = _setup_and_run(tmp_path, records, ["ingest"])
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        assert len(units) == 0


class TestCommitSemanticAggregate:
    """Stage 2: aggregate."""

    def test_theme_threshold(self, tmp_path, sample_jsonl_records):
        """Only themes with >= 3 distinct commits become patterns."""
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest", "aggregate"])
        patterns = load_jsonl(str(semantic_dir / "patterns.jsonl"))

        themes = [p["theme"] for p in patterns]
        assert "auth-flow" in themes  # 4 distinct commits
        assert "config-mgmt" not in themes  # 1 commit
        assert "retry-logic" not in themes  # 1 commit

    def test_op_distribution(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest", "aggregate"])
        patterns = load_jsonl(str(semantic_dir / "patterns.jsonl"))
        auth = [p for p in patterns if p["theme"] == "auth-flow"][0]
        assert auth["op_distribution"]["feat"] == 3
        assert auth["op_distribution"]["refactor"] == 1

    def test_importance_ratio(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest", "aggregate"])
        patterns = load_jsonl(str(semantic_dir / "patterns.jsonl"))
        auth = [p for p in patterns if p["theme"] == "auth-flow"][0]
        assert auth["importance_ratio"]["primary"] == 3
        assert auth["importance_ratio"]["secondary"] == 1

    def test_theme_below_threshold(self, tmp_path):
        """Theme with exactly 2 commits should NOT be a pattern."""
        records = [
            {"sha": "a", "date": "2026-03-01", "sections": [
                {"name": "X", "theme": "two-commit-theme", "importance": "primary",
                 "items": [{"op": "feat", "summary": "s1"}]}
            ], "rules_invariants": []},
            {"sha": "b", "date": "2026-03-02", "sections": [
                {"name": "X", "theme": "two-commit-theme", "importance": "primary",
                 "items": [{"op": "feat", "summary": "s2"}]}
            ], "rules_invariants": []},
        ]
        _, semantic_dir = _setup_and_run(tmp_path, records, ["ingest", "aggregate"])
        patterns = load_jsonl(str(semantic_dir / "patterns.jsonl"))
        assert len(patterns) == 0


class TestCommitSemanticDistill:
    """Stage 3: distill."""

    def test_scoring_formula(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest", "aggregate", "distill"])
        demands = load_jsonl(str(semantic_dir / "canonical-demands.jsonl"))
        assert len(demands) >= 1
        d = demands[0]
        # auth-flow: 4 distinct, importance_weight = (3*2+1*1)/4 = 1.75, score = 7.0
        assert d["theme"] == "auth-flow"
        assert d["score"] == 7.0
        assert d["rank"] == 1

    def test_tiebreak_order(self, tmp_path):
        """Same score → distinct_commits desc → theme alpha."""
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        semantic_dir.mkdir(parents=True)

        patterns = [
            {"theme": "zebra", "count": 6, "distinct_commits": 3,
             "op_distribution": {"feat": 6}, "importance_ratio": {"primary": 3, "secondary": 3},
             "representative_summaries": []},
            {"theme": "alpha", "count": 6, "distinct_commits": 3,
             "op_distribution": {"feat": 6}, "importance_ratio": {"primary": 3, "secondary": 3},
             "representative_summaries": []},
        ]
        save_jsonl(patterns, str(semantic_dir / "patterns.jsonl"))
        save_jsonl([], str(semantic_dir / "invariants.jsonl"))

        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
        runner._run_distill(state)

        demands = load_jsonl(str(semantic_dir / "canonical-demands.jsonl"))
        assert demands[0]["theme"] == "alpha"
        assert demands[1]["theme"] == "zebra"


class TestCommitSemanticExport:
    """Stage 4: export."""

    def test_summary_json(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)
        summary = load_json(str(semantic_dir / "summary.json"))

        assert summary["total_units"] == 6
        assert summary["total_patterns"] >= 1
        assert 0 <= summary["bugfix_ratio"] <= 1
        assert summary["invariant_count"] == 2
        assert summary["date_range"]["from"] == "2026-03-01T10:00:00"
        assert summary["date_range"]["to"] == "2026-03-10T14:00:00"

    def test_op_distribution_in_summary(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)
        summary = load_json(str(semantic_dir / "summary.json"))
        assert "feat" in summary["op_distribution"]
        assert summary["op_distribution"]["feat"] == 3


class TestCommitSemanticFullPipeline:
    """Full pipeline integration."""

    def test_all_stages_produce_output(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)

        assert (semantic_dir / "units" / "all.jsonl").exists()
        assert (semantic_dir / "invariants.jsonl").exists()
        assert (semantic_dir / "patterns.jsonl").exists()
        assert (semantic_dir / "canonical-demands.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
