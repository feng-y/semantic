"""E2E tests for commit-semantic skill - 4-stage JSONL pipeline.

Tests:
- ingest: JSONL expansion, rules_invariants collection, fault tolerance
- aggregate: theme grouping, op_distribution, importance_ratio, high-frequency threshold
- distill: scoring formula, tiebreaking, invariant extra weight
- export: summary stats computation
- prerequisites: checks for .jsonl files
- full pipeline: ingest -> aggregate -> distill -> export
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import save_jsonl as _save_jsonl, load_jsonl


def load_module():
    """Load commit-semantic skill module."""
    import importlib.util
    repo_root = Path(__file__).parent.parent.parent
    spec = importlib.util.spec_from_file_location(
        "commit_semantic_run",
        str(repo_root / "skills/commit-semantic/run.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules["commit_semantic_run"] = mod
    spec.loader.exec_module(mod)
    return mod


def make_commit(
    sha="abc123",
    author="Test",
    date="2024-01-15T10:00:00",
    is_large_aggregate=False,
    is_mixed=False,
    sections=None,
    rules_invariants=None,
):
    return {
        "sha": sha,
        "author": author,
        "date": date,
        "is_large_aggregate": is_large_aggregate,
        "is_mixed": is_mixed,
        "sections": sections or [],
        "rules_invariants": rules_invariants or [],
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    _save_jsonl(records, str(path))


def read_jsonl(path: Path) -> list[dict]:
    return load_jsonl(str(path), skip_errors=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SECTION_BATCH = {
    "name": "Inference path",
    "theme": "batch processing",
    "importance": "primary",
    "summary": "batch inference improvements",
    "items": [
        {"op": "feat", "summary": "add batch inference"},
        {"op": "optimize", "summary": "reduce batch latency"},
    ],
}

SECTION_CONFIG = {
    "name": "Config layer",
    "theme": "configuration management",
    "importance": "secondary",
    "summary": "config updates",
    "items": [
        {"op": "config", "summary": "update default batch size"},
    ],
}

INVARIANT_ORDERING = {
    "kind": "ordering",
    "statement": "batch must complete before flush",
    "enforced_by_commit": True,
}


# ---------------------------------------------------------------------------
# Stage 1: ingest
# ---------------------------------------------------------------------------

class TestIngest:
    def _setup_extract(self, tmp_path, commits):
        extract_dir = tmp_path / "data" / "commit-extract"
        write_jsonl(extract_dir / "2024-01.jsonl", commits)
        return extract_dir

    def _run(self, mod, tmp_path, commits):
        extract_dir = self._setup_extract(tmp_path, commits)
        semantic_dir = tmp_path / "data" / "commit-semantic"
        saved_e, saved_s = mod.EXTRACT_OUTPUT, mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})
        result = mod.CommitSemanticRunner()._run_ingest(state)
        mod.EXTRACT_OUTPUT = saved_e
        mod.SEMANTIC_OUTPUT = saved_s
        return result, semantic_dir

    def test_expands_items_into_units(self, tmp_path):
        mod = load_module()
        commit = make_commit(
            sha="sha001",
            sections=[SECTION_BATCH],
        )
        ok, sem = self._run(mod, tmp_path, [commit])
        assert ok is True
        units = read_jsonl(sem / "units" / "all.jsonl")
        assert len(units) == 2  # two items in SECTION_BATCH
        for u in units:
            assert u["sha"] == "sha001"
            assert u["theme"] == "batch processing"
            assert u["section_name"] == "Inference path"
            assert u["importance"] == "primary"
            assert u["is_large_aggregate"] is False
            assert u["is_mixed"] is False

    def test_inherits_commit_flags(self, tmp_path):
        mod = load_module()
        commit = make_commit(
            sha="sha002",
            is_large_aggregate=True,
            is_mixed=True,
            sections=[SECTION_CONFIG],
        )
        ok, sem = self._run(mod, tmp_path, [commit])
        assert ok is True
        units = read_jsonl(sem / "units" / "all.jsonl")
        assert len(units) == 1
        assert units[0]["is_large_aggregate"] is True
        assert units[0]["is_mixed"] is True

    def test_collects_rules_invariants(self, tmp_path):
        mod = load_module()
        commit = make_commit(
            sha="sha003",
            sections=[SECTION_BATCH],
            rules_invariants=[INVARIANT_ORDERING],
        )
        ok, sem = self._run(mod, tmp_path, [commit])
        assert ok is True
        invs = read_jsonl(sem / "invariants.jsonl")
        assert len(invs) == 1
        assert invs[0]["kind"] == "ordering"
        assert invs[0]["sha"] == "sha003"

    def test_fault_tolerance_skips_invalid_json(self, tmp_path, capsys):
        mod = load_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)
        path = extract_dir / "2024-01.jsonl"
        good = make_commit(sha="sha004", sections=[SECTION_CONFIG])
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("NOT VALID JSON\n")
            fh.write(json.dumps(good) + "\n")
            fh.write("{broken\n")

        semantic_dir = tmp_path / "data" / "commit-semantic"
        saved_e, saved_s = mod.EXTRACT_OUTPUT, mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})
        result = mod.CommitSemanticRunner()._run_ingest(state)
        mod.EXTRACT_OUTPUT = saved_e
        mod.SEMANTIC_OUTPUT = saved_s

        assert result is True
        units = read_jsonl(semantic_dir / "units" / "all.jsonl")
        # Only the good commit's item should appear
        assert len(units) == 1
        assert units[0]["sha"] == "sha004"

    def test_empty_sections_produces_no_units(self, tmp_path):
        mod = load_module()
        commit = make_commit(sha="sha005", sections=[])
        ok, sem = self._run(mod, tmp_path, [commit])
        assert ok is True
        units = read_jsonl(sem / "units" / "all.jsonl")
        assert len(units) == 0

    def test_multiple_months(self, tmp_path):
        mod = load_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        write_jsonl(
            extract_dir / "2024-01.jsonl",
            [make_commit(sha="jan1", sections=[SECTION_BATCH])],
        )
        write_jsonl(
            extract_dir / "2024-02.jsonl",
            [make_commit(sha="feb1", sections=[SECTION_CONFIG])],
        )
        semantic_dir = tmp_path / "data" / "commit-semantic"
        saved_e, saved_s = mod.EXTRACT_OUTPUT, mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})
        mod.CommitSemanticRunner()._run_ingest(state)
        mod.EXTRACT_OUTPUT = saved_e
        mod.SEMANTIC_OUTPUT = saved_s

        units = read_jsonl(semantic_dir / "units" / "all.jsonl")
        shas = {u["sha"] for u in units}
        assert "jan1" in shas
        assert "feb1" in shas


# ---------------------------------------------------------------------------
# Stage 2: aggregate
# ---------------------------------------------------------------------------

class TestAggregate:
    def _run(self, mod, tmp_path, units):
        semantic_dir = tmp_path / "data" / "commit-semantic"
        write_jsonl(semantic_dir / "units" / "all.jsonl", units)
        saved_s = mod.SEMANTIC_OUTPUT
        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})
        result = mod.CommitSemanticRunner()._run_aggregate(state)
        mod.SEMANTIC_OUTPUT = saved_s
        return result, semantic_dir

    def _make_unit(self, sha, theme, op="feat", importance="primary"):
        return {
            "sha": sha,
            "date": "2024-01-01",
            "author": "Test",
            "section_name": "S",
            "theme": theme,
            "importance": importance,
            "op": op,
            "summary": f"{theme} via {op}",
            "is_large_aggregate": False,
            "is_mixed": False,
        }

    def test_groups_by_theme(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit("s1", "batch processing"),
            self._make_unit("s2", "batch processing"),
            self._make_unit("s3", "config management"),
        ]
        ok, sem = self._run(mod, tmp_path, units)
        assert ok is True
        patterns = read_jsonl(sem / "patterns.jsonl")
        themes = {p["theme"] for p in patterns}
        assert "batch processing" in themes
        assert "config management" in themes

    def test_merges_same_theme_different_section_names(self, tmp_path):
        mod = load_module()
        units = [
            {**self._make_unit("s1", "auth"), "section_name": "Login"},
            {**self._make_unit("s2", "auth"), "section_name": "Logout"},
        ]
        ok, sem = self._run(mod, tmp_path, units)
        assert ok is True
        patterns = read_jsonl(sem / "patterns.jsonl")
        auth = next(p for p in patterns if p["theme"] == "auth")
        assert auth["distinct_commits"] == 2
        assert auth["count"] == 2

    def test_op_distribution(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit("s1", "theme-x", op="feat"),
            self._make_unit("s2", "theme-x", op="bugfix"),
            self._make_unit("s3", "theme-x", op="feat"),
        ]
        ok, sem = self._run(mod, tmp_path, units)
        assert ok is True
        patterns = read_jsonl(sem / "patterns.jsonl")
        p = next(x for x in patterns if x["theme"] == "theme-x")
        assert p["op_distribution"]["feat"] == 2
        assert p["op_distribution"]["bugfix"] == 1

    def test_importance_ratio(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit("s1", "theme-y", importance="primary"),
            self._make_unit("s2", "theme-y", importance="secondary"),
            self._make_unit("s3", "theme-y", importance="primary"),
        ]
        ok, sem = self._run(mod, tmp_path, units)
        assert ok is True
        patterns = read_jsonl(sem / "patterns.jsonl")
        p = next(x for x in patterns if x["theme"] == "theme-y")
        assert p["importance_ratio"]["primary"] == 2
        assert p["importance_ratio"]["secondary"] == 1

    def test_representative_summaries_capped_at_3(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit(f"s{i}", "theme-z") for i in range(6)
        ]
        ok, sem = self._run(mod, tmp_path, units)
        assert ok is True
        patterns = read_jsonl(sem / "patterns.jsonl")
        p = next(x for x in patterns if x["theme"] == "theme-z")
        assert len(p["representative_summaries"]) <= 3

    def test_high_frequency_threshold(self, tmp_path):
        mod = load_module()
        # theme-hf appears in 3 distinct commits -> high frequency
        # theme-lf appears in 2 distinct commits -> not high frequency
        units = [
            self._make_unit("c1", "theme-hf"),
            self._make_unit("c2", "theme-hf"),
            self._make_unit("c3", "theme-hf"),
            self._make_unit("c1", "theme-lf"),
            self._make_unit("c2", "theme-lf"),
        ]
        ok, sem = self._run(mod, tmp_path, units)
        assert ok is True
        patterns = read_jsonl(sem / "patterns.jsonl")
        hf = next(p for p in patterns if p["theme"] == "theme-hf")
        lf = next(p for p in patterns if p["theme"] == "theme-lf")
        assert hf["distinct_commits"] >= 3
        assert lf["distinct_commits"] < 3


# ---------------------------------------------------------------------------
# Stage 3: distill
# ---------------------------------------------------------------------------

class TestDistill:
    def _make_pattern(self, theme, distinct_commits, primary=2, secondary=1, op_dist=None):
        return {
            "theme": theme,
            "count": distinct_commits,
            "distinct_commits": distinct_commits,
            "op_distribution": op_dist or {"feat": distinct_commits},
            "importance_ratio": {"primary": primary, "secondary": secondary},
            "representative_summaries": [f"{theme} summary"],
        }

    def _run(self, mod, tmp_path, patterns, invariants=None):
        semantic_dir = tmp_path / "data" / "commit-semantic"
        write_jsonl(semantic_dir / "patterns.jsonl", patterns)
        if invariants is not None:
            write_jsonl(semantic_dir / "invariants.jsonl", invariants)
        saved_s = mod.SEMANTIC_OUTPUT
        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})
        result = mod.CommitSemanticRunner()._run_distill(state)
        mod.SEMANTIC_OUTPUT = saved_s
        return result, semantic_dir

    def test_scoring_formula(self, tmp_path):
        """score = distinct_commits * importance_weight; all-primary > all-secondary."""
        mod = load_module()
        patterns = [
            self._make_pattern("all-primary", 5, primary=5, secondary=0),
            self._make_pattern("all-secondary", 5, primary=0, secondary=5),
        ]
        ok, sem = self._run(mod, tmp_path, patterns)
        assert ok is True
        demands = read_jsonl(sem / "canonical-demands.jsonl")
        scores = {d["theme"]: d["score"] for d in demands}
        assert scores["all-primary"] > scores["all-secondary"]

    def test_sorted_by_score_descending(self, tmp_path):
        mod = load_module()
        patterns = [
            self._make_pattern("low", 1),
            self._make_pattern("high", 10),
            self._make_pattern("mid", 5),
        ]
        ok, sem = self._run(mod, tmp_path, patterns)
        assert ok is True
        demands = read_jsonl(sem / "canonical-demands.jsonl")
        scores = [d["score"] for d in demands]
        assert scores == sorted(scores, reverse=True)

    def test_tiebreak_by_distinct_commits_then_theme(self, tmp_path):
        """Equal score: higher distinct_commits first; then alphabetical theme."""
        mod = load_module()
        # Same importance ratio (all primary), different distinct_commits
        patterns = [
            self._make_pattern("zebra", 3, primary=3, secondary=0),
            self._make_pattern("alpha", 3, primary=3, secondary=0),
            self._make_pattern("beta", 5, primary=5, secondary=0),
        ]
        ok, sem = self._run(mod, tmp_path, patterns)
        assert ok is True
        demands = read_jsonl(sem / "canonical-demands.jsonl")
        themes = [d["theme"] for d in demands]
        # beta (5 commits) should come before alpha/zebra (3 commits)
        assert themes.index("beta") < themes.index("alpha")
        assert themes.index("beta") < themes.index("zebra")
        # alpha before zebra (alphabetical tiebreak)
        assert themes.index("alpha") < themes.index("zebra")

    def test_invariant_extra_weight(self, tmp_path):
        """Theme matching a high-frequency invariant gets a score bonus."""
        mod = load_module()
        # Two patterns with same base score
        patterns = [
            self._make_pattern("batch flush", 3, primary=3, secondary=0),
            self._make_pattern("unrelated topic", 3, primary=3, secondary=0),
        ]
        # Invariant mentioning "batch flush" appears in 3 commits
        invariants = [
            {"statement": "batch flush must complete before flush", "sha": f"s{i}", "kind": "ordering"}
            for i in range(3)
        ]
        ok, sem = self._run(mod, tmp_path, patterns, invariants)
        assert ok is True
        demands = read_jsonl(sem / "canonical-demands.jsonl")
        scores = {d["theme"]: d["score"] for d in demands}
        assert scores["batch flush"] > scores["unrelated topic"]

    def test_rank_field_present(self, tmp_path):
        mod = load_module()
        patterns = [self._make_pattern("t1", 2), self._make_pattern("t2", 4)]
        ok, sem = self._run(mod, tmp_path, patterns)
        assert ok is True
        demands = read_jsonl(sem / "canonical-demands.jsonl")
        assert all("rank" in d for d in demands)
        assert demands[0]["rank"] == 1


# ---------------------------------------------------------------------------
# Stage 4: export
# ---------------------------------------------------------------------------

class TestExport:
    def _setup(self, tmp_path, units, demands, invariants=None):
        semantic_dir = tmp_path / "data" / "commit-semantic"
        write_jsonl(semantic_dir / "units" / "all.jsonl", units)
        write_jsonl(semantic_dir / "canonical-demands.jsonl", demands)
        if invariants is not None:
            write_jsonl(semantic_dir / "invariants.jsonl", invariants)
        return semantic_dir

    def _make_unit(self, sha, op, date="2024-01-01"):
        return {"sha": sha, "date": date, "op": op, "theme": "t", "importance": "primary",
                "summary": "", "author": "", "section_name": "", "is_large_aggregate": False,
                "is_mixed": False}

    def _make_demand(self, theme, distinct_commits=2, score=4.0):
        return {"rank": 1, "theme": theme, "score": score, "distinct_commits": distinct_commits,
                "count": distinct_commits, "op_distribution": {"feat": distinct_commits},
                "importance_ratio": {"primary": distinct_commits, "secondary": 0},
                "representative_summaries": []}

    def _run(self, mod, tmp_path, units, demands, invariants=None):
        semantic_dir = self._setup(tmp_path, units, demands, invariants)
        saved_s = mod.SEMANTIC_OUTPUT
        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})
        result = mod.CommitSemanticRunner()._run_export(state)
        mod.SEMANTIC_OUTPUT = saved_s
        return result, semantic_dir

    def test_summary_json_created(self, tmp_path):
        mod = load_module()
        units = [self._make_unit("s1", "feat"), self._make_unit("s2", "bugfix")]
        demands = [self._make_demand("theme-a")]
        ok, sem = self._run(mod, tmp_path, units, demands)
        assert ok is True
        assert (sem / "summary.json").exists()

    def test_total_units_and_patterns(self, tmp_path):
        mod = load_module()
        units = [self._make_unit(f"s{i}", "feat") for i in range(5)]
        demands = [self._make_demand(f"t{i}") for i in range(3)]
        ok, sem = self._run(mod, tmp_path, units, demands)
        assert ok is True
        import json as _json
        summary = _json.loads((sem / "summary.json").read_text())
        assert summary["total_units"] == 5
        assert summary["total_patterns"] == 3

    def test_bugfix_ratio(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit("s1", "bugfix"),
            self._make_unit("s2", "bugfix"),
            self._make_unit("s3", "feat"),
            self._make_unit("s4", "feat"),
        ]
        demands = [self._make_demand("t")]
        ok, sem = self._run(mod, tmp_path, units, demands)
        assert ok is True
        import json as _json
        summary = _json.loads((sem / "summary.json").read_text())
        assert abs(summary["bugfix_ratio"] - 0.5) < 0.01

    def test_op_distribution_in_summary(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit("s1", "feat"),
            self._make_unit("s2", "feat"),
            self._make_unit("s3", "bugfix"),
        ]
        demands = [self._make_demand("t")]
        ok, sem = self._run(mod, tmp_path, units, demands)
        assert ok is True
        import json as _json
        summary = _json.loads((sem / "summary.json").read_text())
        assert summary["op_distribution"]["feat"] == 2
        assert summary["op_distribution"]["bugfix"] == 1

    def test_date_range(self, tmp_path):
        mod = load_module()
        units = [
            self._make_unit("s1", "feat", date="2024-01-01"),
            self._make_unit("s2", "feat", date="2024-06-15"),
            self._make_unit("s3", "feat", date="2024-03-10"),
        ]
        demands = [self._make_demand("t")]
        ok, sem = self._run(mod, tmp_path, units, demands)
        assert ok is True
        import json as _json
        summary = _json.loads((sem / "summary.json").read_text())
        assert summary["date_range"]["from"] == "2024-01-01"
        assert summary["date_range"]["to"] == "2024-06-15"

    def test_invariant_count(self, tmp_path):
        mod = load_module()
        units = [self._make_unit("s1", "feat")]
        demands = [self._make_demand("t")]
        invariants = [
            {"statement": "inv1", "sha": "s1", "kind": "ordering"},
            {"statement": "inv2", "sha": "s2", "kind": "boundary"},
        ]
        ok, sem = self._run(mod, tmp_path, units, demands, invariants)
        assert ok is True
        import json as _json
        summary = _json.loads((sem / "summary.json").read_text())
        assert summary["invariant_count"] == 2

    def test_top_patterns_capped_at_10(self, tmp_path):
        mod = load_module()
        units = [self._make_unit("s1", "feat")]
        demands = [self._make_demand(f"theme-{i}", score=float(20 - i)) for i in range(15)]
        ok, sem = self._run(mod, tmp_path, units, demands)
        assert ok is True
        import json as _json
        summary = _json.loads((sem / "summary.json").read_text())
        assert len(summary["top_patterns"]) <= 10


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

class TestPrerequisites:
    def test_fails_when_no_extract_dir(self):
        mod = load_module()
        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = Path("/nonexistent/path/does/not/exist")
        ok, msg = mod.CommitSemanticRunner()._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved
        assert ok is False
        assert "commit-extract" in msg.lower() or "not found" in msg.lower()

    def test_fails_when_no_jsonl_files(self, tmp_path):
        mod = load_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)
        # Put a yaml file there — should not count
        (extract_dir / "2024-01.yaml").write_text("metadata: {}\ncommits: []\n")
        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        ok, msg = mod.CommitSemanticRunner()._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved
        assert ok is False

    def test_passes_with_jsonl_files(self, tmp_path):
        mod = load_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        write_jsonl(extract_dir / "2024-01.jsonl", [])
        saved = mod.EXTRACT_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        ok, msg = mod.CommitSemanticRunner()._check_prerequisites()
        mod.EXTRACT_OUTPUT = saved
        assert ok is True


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_ingest_aggregate_distill_export(self, tmp_path):
        mod = load_module()

        commits = [
            make_commit(
                sha=f"sha{i:03d}",
                date=f"2024-0{(i % 3) + 1}-01T10:00:00",
                sections=[
                    {
                        "name": "Core",
                        "theme": "batch processing" if i < 4 else "config management",
                        "importance": "primary",
                        "summary": "core change",
                        "items": [{"op": "feat", "summary": f"change {i}"}],
                    }
                ],
                rules_invariants=[
                    {"kind": "ordering", "statement": "flush after batch", "enforced_by_commit": True}
                ] if i < 3 else [],
            )
            for i in range(6)
        ]

        extract_dir = tmp_path / "data" / "commit-extract"
        write_jsonl(extract_dir / "2024-01.jsonl", commits)

        semantic_dir = tmp_path / "data" / "commit-semantic"
        saved_e, saved_s = mod.EXTRACT_OUTPUT, mod.SEMANTIC_OUTPUT
        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(metadata={"completed_stages": [], "artifacts_written": []})

        assert runner._run_ingest(state) is True
        assert runner._run_aggregate(state) is True
        assert runner._run_distill(state) is True
        assert runner._run_export(state) is True

        mod.EXTRACT_OUTPUT = saved_e
        mod.SEMANTIC_OUTPUT = saved_s

        assert (semantic_dir / "units" / "all.jsonl").exists()
        assert (semantic_dir / "invariants.jsonl").exists()
        assert (semantic_dir / "patterns.jsonl").exists()
        assert (semantic_dir / "canonical-demands.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()

        import json as _json
        summary = _json.loads((semantic_dir / "summary.json").read_text())
        assert summary["total_units"] == 6
        assert summary["total_patterns"] >= 1
        assert "date_range" in summary

    def test_stages_constant(self):
        mod = load_module()
        assert mod.CommitSemanticRunner.STAGES == ["ingest", "aggregate", "distill", "export"]
        assert mod.CommitSemanticRunner.PIPELINE == "commit-semantic"
