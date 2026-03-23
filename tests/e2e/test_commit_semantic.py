"""E2E tests for commit-semantic skill (5-stage domain pipeline).

Tests: discover → ingest → aggregate → distill → export consuming JSONL from commit-extract.
Note: discover stage requires LLM, so most tests skip it and run ingest→export directly.
Without domains.json, all units are "uncategorized" — this is expected behavior.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import save_jsonl, load_jsonl, load_json, save_json


class FakeHostExecutor:
    """Deterministic host executor for commit-semantic tests."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def __call__(
        self,
        prompt_text: str,
        context: dict[str, str],
        *,
        artifact_name: str,
        sampling_mode: str = "auto",
    ) -> str:
        self.calls.append(
            {
                "prompt_text": prompt_text,
                "context": context,
                "artifact_name": artifact_name,
                "sampling_mode": sampling_mode,
            }
        )

        if artifact_name == "domains":
            return json.dumps(
                [
                    {
                        "domain": "auth",
                        "description": "Authentication and session flows",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "demand",
                        "description": "Issue and demand mapping",
                        "paths": ["src/demand/"],
                        "keywords": ["demand", "issue", "requirement", "card"],
                    },
                ]
            )

        if artifact_name == "classify-units":
            units = json.loads(context["units_json"])
            classifications = []
            for unit in units:
                text = " ".join(
                    [
                        unit.get("section_name", ""),
                        unit.get("theme", ""),
                        unit.get("summary", ""),
                    ]
                ).lower()
                domain = "demand" if "demand" in text or "issue" in text else "auth"
                classifications.append({"id": unit["id"], "domain": domain})
            return json.dumps(classifications)

        raise AssertionError(f"Unexpected artifact_name: {artifact_name}")


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


# Skip discover in tests (requires LLM). Run ingest→aggregate→distill→export.
NON_LLM_STAGES = ["ingest", "aggregate", "distill", "export"]


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

    for stage in (stages or NON_LLM_STAGES):
        runner.run_stage(stage, state)

    return mod, semantic_dir


def _write_semantic_inputs(semantic_dir, *, units=None, invariants=None, aggregated=None):
    """Write semantic stage fixtures directly for aggregate/distill tests."""
    units_dir = semantic_dir / "units"
    units_dir.mkdir(parents=True, exist_ok=True)
    save_jsonl(units or [], str(units_dir / "all.jsonl"))
    save_jsonl(invariants or [], str(semantic_dir / "invariants.jsonl"))
    if aggregated is not None:
        save_jsonl(aggregated, str(semantic_dir / "domains-aggregated.jsonl"))


class TestCommitSemanticSkill:
    """Basic skill structure."""

    def test_skill_exists(self):
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()
        assert runner.PIPELINE == "commit-semantic"
        assert runner.STAGES == ["discover", "ingest", "aggregate", "distill", "export"]


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
    """Stage 2: aggregate by domain with audit fields."""

    def test_uncategorized_without_domains(self, tmp_path, sample_jsonl_records):
        """Without domains.json, all units aggregate into uncategorized."""
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest", "aggregate"])
        aggregated = load_jsonl(str(semantic_dir / "domains-aggregated.jsonl"))
        assert len(aggregated) == 1
        assert aggregated[0]["domain"] == "uncategorized"
        assert aggregated[0]["is_uncategorized"] is True
        assert aggregated[0]["count"] == 6

    def test_groups_by_domain_and_preserves_sub_themes(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        _write_semantic_inputs(
            semantic_dir,
            units=[
                {
                    "sha": "a1",
                    "date": "2026-03-01T10:00:00",
                    "domain": "auth",
                    "theme": "login",
                    "importance": "primary",
                    "op": "feat",
                    "summary": "Add password login",
                },
                {
                    "sha": "a2",
                    "date": "2026-03-02T10:00:00",
                    "domain": "auth",
                    "theme": "login",
                    "importance": "secondary",
                    "op": "bugfix",
                    "summary": "Fix login redirect",
                },
                {
                    "sha": "a3",
                    "date": "2026-03-03T10:00:00",
                    "domain": "auth",
                    "theme": "session",
                    "importance": "primary",
                    "op": "refactor",
                    "summary": "Simplify session middleware",
                },
                {
                    "sha": "u1",
                    "date": "2026-03-04T10:00:00",
                    "domain": "uncategorized",
                    "theme": "misc-cleanup",
                    "importance": "secondary",
                    "op": "chore",
                    "summary": "Clean up misc paths",
                },
            ],
        )

        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        runner._run_aggregate(state)

        aggregated = load_jsonl(str(semantic_dir / "domains-aggregated.jsonl"))
        assert [entry["domain"] for entry in aggregated] == ["auth", "uncategorized"]

        auth = aggregated[0]
        assert auth["is_uncategorized"] is False
        assert auth["distinct_commits"] == 3
        assert auth["op_distribution"] == {"feat": 1, "bugfix": 1, "refactor": 1}
        assert auth["importance_ratio"] == {"primary": 2, "secondary": 1}
        assert auth["sub_themes"] == {"login": 2, "session": 1}

        uncat = aggregated[1]
        assert uncat["is_uncategorized"] is True
        assert uncat["sub_themes"] == {"misc-cleanup": 1}


class TestCommitSemanticDistill:
    """Stage 3: distill with domain scoring and ranking."""

    def test_scoring_produces_audit_breakdown(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records, ["ingest", "aggregate", "distill"])
        demands = load_jsonl(str(semantic_dir / "canonical-demands.jsonl"))
        assert len(demands) >= 1
        demand = demands[0]
        assert demand["rank"] == 1
        assert set(demand.keys()) >= {
            "domain",
            "is_uncategorized",
            "final_score",
            "base_score",
            "diversity_bonus",
            "invariant_bonus",
            "recency_weight",
            "distinct_commits",
            "importance_weight",
            "op_distribution",
            "representative_summaries",
        }

    def test_invariant_bonus_uses_same_sha_association_and_caps_at_five(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        aggregated = [
            {
                "domain": "auth",
                "is_uncategorized": False,
                "count": 2,
                "distinct_commits": 2,
                "op_distribution": {"feat": 1, "bugfix": 1},
                "importance_ratio": {"primary": 1, "secondary": 1},
                "date_range": {"from": "2026-03-01T00:00:00", "to": "2026-03-02T00:00:00"},
                "sub_themes": {"login": 2},
                "representative_summaries": ["Add login", "Fix login"],
            }
        ]
        units = [
            {"sha": "sha-1", "date": "2026-03-01T00:00:00", "domain": "auth"},
            {"sha": "sha-2", "date": "2026-03-02T00:00:00", "domain": "auth"},
        ]
        invariants = [
            {"sha": "sha-1", "statement": "inv-1"},
            {"sha": "sha-1", "statement": "inv-2"},
            {"sha": "sha-1", "statement": "inv-3"},
            {"sha": "sha-2", "statement": "inv-4"},
            {"sha": "sha-2", "statement": "inv-5"},
            {"sha": "sha-2", "statement": "inv-6"},
            {"sha": "other-sha", "statement": "ignored"},
            {"sha": "sha-2", "statement": "inv-6"},
        ]
        _write_semantic_inputs(semantic_dir, units=units, invariants=invariants, aggregated=aggregated)

        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
        runner._run_distill(state)

        demands = load_jsonl(str(semantic_dir / "canonical-demands.jsonl"))
        assert len(demands) == 1
        assert demands[0]["domain"] == "auth"
        assert demands[0]["invariant_bonus"] == 5

    def test_ranking_uses_score_then_distinct_commits_then_domain(self, tmp_path):
        """Same score -> distinct_commits desc -> domain alpha."""
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        aggregated = [
            {
                "domain": "zebra",
                "is_uncategorized": False,
                "count": 6,
                "distinct_commits": 3,
                "op_distribution": {"feat": 6},
                "importance_ratio": {"primary": 3, "secondary": 3},
                "date_range": {},
                "sub_themes": {},
                "representative_summaries": [],
            },
            {
                "domain": "alpha",
                "is_uncategorized": False,
                "count": 6,
                "distinct_commits": 3,
                "op_distribution": {"feat": 6},
                "importance_ratio": {"primary": 3, "secondary": 3},
                "date_range": {},
                "sub_themes": {},
                "representative_summaries": [],
            },
            {
                "domain": "bravo",
                "is_uncategorized": False,
                "count": 6,
                "distinct_commits": 4,
                "op_distribution": {"feat": 6},
                "importance_ratio": {"primary": 2, "secondary": 4},
                "date_range": {},
                "sub_themes": {},
                "representative_summaries": [],
            },
        ]
        _write_semantic_inputs(semantic_dir, units=[], invariants=[], aggregated=aggregated)

        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
        runner._run_distill(state)

        demands = load_jsonl(str(semantic_dir / "canonical-demands.jsonl"))
        assert [d["domain"] for d in demands] == ["bravo", "alpha", "zebra"]
        assert [d["rank"] for d in demands] == [1, 2, 3]

    def test_guardrail_top_three_vs_bottom_three_gap(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        aggregated = [
            {
                "domain": "auth",
                "is_uncategorized": False,
                "count": 10,
                "distinct_commits": 5,
                "op_distribution": {"feat": 4, "bugfix": 3, "refactor": 3},
                "importance_ratio": {"primary": 8, "secondary": 2},
                "date_range": {},
                "sub_themes": {"login": 6, "session": 4},
                "representative_summaries": [],
            },
            {
                "domain": "billing",
                "is_uncategorized": False,
                "count": 9,
                "distinct_commits": 4,
                "op_distribution": {"feat": 3, "bugfix": 3, "config": 3},
                "importance_ratio": {"primary": 6, "secondary": 3},
                "date_range": {},
                "sub_themes": {"invoice": 5, "refund": 4},
                "representative_summaries": [],
            },
            {
                "domain": "search",
                "is_uncategorized": False,
                "count": 8,
                "distinct_commits": 4,
                "op_distribution": {"feat": 4, "refactor": 4},
                "importance_ratio": {"primary": 5, "secondary": 3},
                "date_range": {},
                "sub_themes": {"query": 8},
                "representative_summaries": [],
            },
            {
                "domain": "docs",
                "is_uncategorized": False,
                "count": 6,
                "distinct_commits": 2,
                "op_distribution": {"docs": 6},
                "importance_ratio": {"primary": 0, "secondary": 6},
                "date_range": {},
                "sub_themes": {"guides": 6},
                "representative_summaries": [],
            },
            {
                "domain": "tooling",
                "is_uncategorized": False,
                "count": 5,
                "distinct_commits": 1,
                "op_distribution": {"chore": 5},
                "importance_ratio": {"primary": 0, "secondary": 5},
                "date_range": {},
                "sub_themes": {"ci": 5},
                "representative_summaries": [],
            },
            {
                "domain": "misc",
                "is_uncategorized": True,
                "count": 4,
                "distinct_commits": 1,
                "op_distribution": {"chore": 4},
                "importance_ratio": {"primary": 0, "secondary": 4},
                "date_range": {},
                "sub_themes": {"misc": 4},
                "representative_summaries": [],
            },
        ]
        _write_semantic_inputs(semantic_dir, units=[], invariants=[], aggregated=aggregated)

        mod.SEMANTIC_OUTPUT = semantic_dir
        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})
        runner._run_distill(state)

        demands = load_jsonl(str(semantic_dir / "canonical-demands.jsonl"))
        top_three = [d["final_score"] for d in demands[:3]]
        bottom_three = [d["final_score"] for d in demands[-3:]]
        assert min(top_three) >= max(bottom_three) * 2


class TestCommitSemanticExport:
    """Stage 4: export."""

    def test_summary_json(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)
        summary = load_json(str(semantic_dir / "summary.json"))

        assert summary["total_units"] == 6
        assert summary["domain_count"] >= 1
        assert 0 <= summary["bugfix_ratio"] <= 1
        assert summary["invariant_count"] == 2
        assert summary["date_range"]["from"] == "2026-03-01T10:00:00"
        assert summary["date_range"]["to"] == "2026-03-10T14:00:00"
        assert "uncategorized_ratio" in summary
        assert "file_paths_available" in summary

    def test_op_distribution_in_summary(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)
        summary = load_json(str(semantic_dir / "summary.json"))
        assert "feat" in summary["op_distribution"]
        assert summary["op_distribution"]["feat"] == 3

    def test_top_domains_in_summary(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)
        summary = load_json(str(semantic_dir / "summary.json"))
        assert "top_domains" in summary
        assert len(summary["top_domains"]) >= 1


class TestCommitSemanticDiscoverNormalization:
    """Discover stage normalization behavior."""

    def test_complete_discover_normalizes_combined_domains_json(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        semantic_dir.mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="discover",
            metadata={
                "discover_fingerprint": {"units_hash": "abc123", "arch_hash": None},
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
            },
        )

        llm_response = json.dumps([
            {
                "domain": "test",
                "description": "Single test utilities",
                "paths": ["tests/unit/", "tests/e2e/"],
                "keywords": ["pytest", "fixture"],
            },
            {
                "domain": "tests",
                "description": "Test infrastructure and end-to-end flows",
                "paths": ["tests/e2e/", "tests/integration/"],
                "keywords": ["pytest", "integration", "fixture"],
            },
            {
                "domain": "quality",
                "description": "Quality checks and validation",
                "paths": ["tests/e2e/", "tests/integration/"],
                "keywords": ["pytest", "integration", "validation"],
            },
            {
                "domain": "misc",
                "description": "Catch-all bucket",
                "paths": [],
                "keywords": ["misc"],
            },
        ])

        assert runner.complete_discover(llm_response, state) is True

        domains = load_json(str(semantic_dir / "domains.json"))
        assert domains["_fingerprint"] == {"units_hash": "abc123", "arch_hash": None}
        assert domains["discover_mode"] == "llm"
        assert domains["orchestration_mode_at_discover"] == "llm_preferred"
        assert domains["domains"] == [
            {
                "domain": "tests",
                "description": "Test infrastructure and end-to-end flows",
                "paths": ["tests/e2e/", "tests/integration/", "tests/unit/"],
                "keywords": ["fixture", "integration", "pytest", "validation"],
            }
        ]

    def test_discover_cache_hit_restores_provenance(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        units_dir = semantic_dir / "units"
        units_dir.mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        units = [
            {
                "sha": "a1",
                "date": "2026-03-01T10:00:00",
                "section_name": "Auth",
                "theme": "login",
                "summary": "Add login flow",
                "op": "feat",
            }
        ]
        save_jsonl(units, str(units_dir / "all.jsonl"))
        fingerprint = mod.compute_fingerprint(units_dir / "all.jsonl", None)
        save_json(
            {
                "_fingerprint": fingerprint,
                "discover_mode": "llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login"],
                    }
                ],
            },
            str(semantic_dir / "domains.json"),
        )

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        runner._find_arch_file = lambda: None
        state = HarnessState(stage="discover", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        assert runner._run_discover(state) is True
        assert state.metadata["discover_mode"] == "cached_llm"
        assert state.metadata["orchestration_mode_at_discover"] == "llm_preferred"

    def test_complete_discover_invalid_or_empty_output_fails_without_fallback(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        units_dir = semantic_dir / "units"
        units_dir.mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        units = [
            {
                "sha": "a1",
                "date": "2026-03-01T10:00:00",
                "section_name": "Auth",
                "theme": "login",
                "summary": "Add login flow",
                "op": "feat",
            }
        ]
        save_jsonl(units, str(units_dir / "all.jsonl"))

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="discover",
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
                "discover_fingerprint": mod.compute_fingerprint(units_dir / "all.jsonl", None),
                "external_orchestration": True,
            },
        )

        assert runner.complete_discover("not json", state) is False
        assert runner.complete_discover("[]", state) is False
        assert not (semantic_dir / "domains.json").exists()
        assert "discover_mode" not in state.metadata

    def test_run_discover_executes_host_executor_and_persists_domains(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        units_dir = semantic_dir / "units"
        units_dir.mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        save_jsonl(
            [
                {
                    "sha": "a1",
                    "date": "2026-03-01T10:00:00",
                    "section_name": "Auth rollout",
                    "theme": "auth-session",
                    "summary": "Add login session refresh token flow",
                    "op": "feat",
                }
            ],
            str(units_dir / "all.jsonl"),
        )

        from src.harness_state import HarnessState
        executor = FakeHostExecutor()
        runner = mod.CommitSemanticRunner(executor=executor)
        runner._find_arch_file = lambda: None
        state = HarnessState(stage="discover", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        assert runner._run_discover(state) is True
        domains_payload = load_json(str(semantic_dir / "domains.json"))

        assert len(executor.calls) == 1
        assert executor.calls[0]["artifact_name"] == "domains"
        assert "units_json" not in executor.calls[0]["context"]
        assert domains_payload["discover_mode"] == "llm"
        assert [domain["domain"] for domain in domains_payload["domains"]] == ["auth", "demand"]
        assert state.metadata["discover_mode"] == "llm"

    def test_run_ingest_executes_host_executor_for_classify_batches(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "a" * 40,
                    "author": "yan.",
                    "date": "2026-03-01T10:00:00",
                    "is_large_aggregate": False,
                    "is_mixed": True,
                    "sections": [
                        {
                            "name": "Auth rollout",
                            "theme": "auth-session",
                            "importance": "primary",
                            "items": [
                                {"op": "feat", "summary": "Add login session refresh token flow"},
                                {"op": "feat", "summary": "Map issue inputs into demand cards"},
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "discover_mode": "llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "demand",
                        "description": "Issue and demand mapping",
                        "paths": ["src/demand/"],
                        "keywords": ["demand", "issue", "requirement", "card"],
                    },
                ],
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        executor = FakeHostExecutor()
        runner = mod.CommitSemanticRunner(executor=executor)
        state = HarnessState(
            stage="ingest",
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
                "external_orchestration": True,
            },
        )

        assert runner._run_ingest(state) is True
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))

        classify_calls = [call for call in executor.calls if call["artifact_name"] == "classify-units"]
        assert len(classify_calls) == 1
        assert len(json.loads(classify_calls[0]["context"]["units_json"])) == 2
        assert [unit["domain"] for unit in units] == ["auth", "demand"]
        assert state.metadata["classify_mode"] == "llm"
        assert state.metadata["needs_llm_classify"] == 2


class TestCommitSemanticFullPipeline:
    """Full pipeline integration (without discover)."""

    def test_all_stages_produce_output(self, tmp_path, sample_jsonl_records):
        _, semantic_dir = _setup_and_run(tmp_path, sample_jsonl_records)

        assert (semantic_dir / "units" / "all.jsonl").exists()
        assert (semantic_dir / "invariants.jsonl").exists()
        assert (semantic_dir / "domains-aggregated.jsonl").exists()
        assert (semantic_dir / "canonical-demands.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()

    def test_local_run_without_orchestration_fails_cleanly_instead_of_succeeding_via_fallback(self, tmp_path):
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        records = [
            {
                "sha": "a" * 40,
                "author": "yan.",
                "date": "2026-03-01T10:00:00",
                "is_large_aggregate": False,
                "is_mixed": False,
                "sections": [
                    {
                        "name": "Commit semantic pipeline",
                        "theme": "domain-classification",
                        "importance": "primary",
                        "items": [
                            {"op": "feat", "summary": "Add local domain classification fallback"}
                        ],
                    }
                ],
                "rules_invariants": [],
            }
        ]
        save_jsonl(records, str(extract_dir / "2026-03.jsonl"))

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent.parent / "skills/commit-semantic/run.py"), "run"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 1
        assert not (tmp_path / "data" / "commit-semantic" / "summary.json").exists()
        assert "discover orchestration unavailable" in (result.stderr + result.stdout).lower()

    def test_ingest_needing_classify_with_no_orchestration_fails(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "c" * 40,
                    "author": "yan.",
                    "date": "2026-03-03T10:00:00",
                    "is_large_aggregate": False,
                    "is_mixed": True,
                    "sections": [
                        {
                            "name": "Auth rollout",
                            "theme": "auth-session",
                            "importance": "primary",
                            "items": [
                                {"op": "feat", "summary": "Add login session refresh token flow"}
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "discover_mode": "cached_llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": [],
                        "keywords": ["auth", "login", "session", "token"],
                    }
                ]
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        ok = runner._run_ingest(state)
        assert ok is False
        assert not (semantic_dir / "units" / "all.jsonl").exists()
        assert state.metadata["needs_llm_classify"] == 1


    def test_summary_includes_truthful_mode_fields(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        semantic_dir.mkdir(parents=True)
        (semantic_dir / "units").mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        save_jsonl(
            [
                {
                    "sha": "a",
                    "date": "2026-03-01T10:00:00",
                    "op": "feat",
                    "summary": "add login",
                    "domain": "auth",
                }
            ],
            str(semantic_dir / "units" / "all.jsonl"),
        )
        save_jsonl([], str(semantic_dir / "domains-aggregated.jsonl"))
        save_jsonl([], str(semantic_dir / "canonical-demands.jsonl"))
        save_jsonl([], str(semantic_dir / "invariants.jsonl"))

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
                "orchestration_mode": "mixed_degraded",
                "discover_mode": "cached_llm",
                "classify_mode": "fallback",
                "file_paths_available": False,
            }
        )

        assert runner._run_export(state) is True
        summary = load_json(str(semantic_dir / "summary.json"))
        assert summary["orchestration_mode"] == "mixed_degraded"
        assert summary["discover_mode"] == "cached_llm"
        assert summary["classify_mode"] == "fallback"
        assert summary["file_paths_available"] is False

    def test_complete_classify_partial_failure_fails_overall_instead_of_degrading(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        (semantic_dir / "units").mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        save_jsonl(
            [
                {
                    "sha": "a",
                    "date": "2026-03-01T10:00:00",
                    "section_name": "Auth rollout",
                    "theme": "auth-session",
                    "summary": "Add login session refresh token flow",
                },
                {
                    "sha": "b",
                    "date": "2026-03-02T10:00:00",
                    "section_name": "Demand cards",
                    "theme": "issue-mapping",
                    "summary": "Map issue inputs into demand cards",
                },
            ],
            str(semantic_dir / "units" / "all.jsonl"),
        )
        save_json(
            {
                "discover_mode": "llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": [],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "demand",
                        "description": "Issue and demand mapping",
                        "paths": [],
                        "keywords": ["issue", "demand", "cards"],
                    },
                ],
            },
            str(semantic_dir / "domains.json"),
        )

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
                "external_orchestration": True,
                "discover_mode": "cached_llm",
                "classify_unit_indices": [0, 1],
                "classify_units": [
                    {"id": "0", "section_name": "Auth rollout", "theme": "auth-session", "summary": "Add login session refresh token flow", "op": "feat"},
                    {"id": "1", "section_name": "Demand cards", "theme": "issue-mapping", "summary": "Map issue inputs into demand cards", "op": "feat"},
                ],
            }
        )

        assert runner.complete_classify([json.dumps({"0": "auth"}), "not json"], state) is False
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        assert all("domain" not in unit for unit in units)
        assert "classify_mode" not in state.metadata

    def test_classify_total_failure_fails_instead_of_leaving_uncategorized(self, tmp_path):
        mod = load_commit_semantic_module()
        semantic_dir = tmp_path / "data" / "commit-semantic"
        (semantic_dir / "units").mkdir(parents=True)
        mod.SEMANTIC_OUTPUT = semantic_dir

        save_jsonl(
            [
                {
                    "sha": "a",
                    "date": "2026-03-01T10:00:00",
                    "section_name": "Infra cleanup",
                    "theme": "maintenance",
                    "summary": "Refactor helper wiring",
                }
            ],
            str(semantic_dir / "units" / "all.jsonl"),
        )
        save_json(
            {
                "discover_mode": "llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": [],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "demand",
                        "description": "Issue and demand mapping",
                        "paths": [],
                        "keywords": ["issue", "demand", "requirement"],
                    },
                ],
            },
            str(semantic_dir / "domains.json"),
        )

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
                "external_orchestration": True,
                "discover_mode": "cached_llm",
                "classify_unit_indices": [0],
                "classify_units": [
                    {"id": "0", "section_name": "Infra cleanup", "theme": "maintenance", "summary": "Refactor helper wiring", "op": "refactor"},
                ],
            }
        )

        assert runner.complete_classify(["not json"], state) is False
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        assert all("domain" not in unit for unit in units)
        assert "classify_mode" not in state.metadata

    def test_default_run_prefers_llm_semantics_when_orchestration_available(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "h" * 40,
                    "author": "yan.",
                    "date": "2026-03-03T10:00:00",
                    "is_large_aggregate": False,
                    "is_mixed": True,
                    "sections": [
                        {
                            "name": "Auth rollout",
                            "theme": "auth-session",
                            "importance": "primary",
                            "items": [
                                {"op": "feat", "summary": "Add login session refresh token flow"}
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "discover_mode": "llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": [],
                        "keywords": ["auth", "login", "session", "token"],
                    }
                ],
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(
            stage="init",
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
                "external_orchestration": True,
            },
        )

        assert runner._run_ingest(state) is True
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        assert units[0]["domain"] == "uncategorized"
        assert state.metadata["discover_mode"] == "cached_llm"
        assert state.metadata["classify_mode"] == "llm"
        assert state.metadata["needs_llm_classify"] == 1
        assert state.metadata["orchestration_mode"] == "llm_preferred"


    def test_local_run_without_orchestration_does_not_emit_degraded_summary(self, tmp_path):
        extract_dir = tmp_path / "data" / "commit-extract"
        extract_dir.mkdir(parents=True)

        records = [
            {
                "sha": "a" * 40,
                "author": "yan.",
                "date": "2026-03-01T10:00:00",
                "is_large_aggregate": False,
                "is_mixed": False,
                "sections": [
                    {
                        "name": "Commit semantic pipeline",
                        "theme": "domain-classification",
                        "importance": "primary",
                        "items": [
                            {"op": "feat", "summary": "Add local domain classification fallback"}
                        ],
                    }
                ],
                "rules_invariants": [],
            }
        ]
        save_jsonl(records, str(extract_dir / "2026-03.jsonl"))

        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent.parent / "skills/commit-semantic/run.py"), "run"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 1, result.stderr + "\n" + result.stdout

        semantic_dir = tmp_path / "data" / "commit-semantic"
        assert not (semantic_dir / "domains.json").exists()
        assert not (semantic_dir / "summary.json").exists()


    def test_local_classify_keeps_single_domain_path_fast_path(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "d" * 40,
                    "author": "yan.",
                    "date": "2026-03-03T10:00:00",
                    "is_large_aggregate": False,
                    "is_mixed": False,
                    "sections": [
                        {
                            "name": "Unrelated section",
                            "theme": "maintenance",
                            "importance": "primary",
                            "items": [
                                {"op": "feat", "summary": "Refactor helper wiring"}
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login", "session", "token"],
                    }
                ]
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        original_build_sha_file_map = mod.build_sha_file_map
        mod.build_sha_file_map = lambda repo_path, shas: ({"d" * 40: ["src/auth/login.py"]}, True)
        try:
            ok = runner._run_ingest(state)
        finally:
            mod.build_sha_file_map = original_build_sha_file_map

        assert ok is True
        units = load_jsonl(str(semantic_dir / "units" / "all.jsonl"))
        assert units[0]["domain"] == "auth"
        assert state.metadata["needs_llm_classify"] == 0

    def test_multi_domain_commit_requires_orchestration_instead_of_unit_scoring(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "e" * 40,
                    "author": "yan.",
                    "date": "2026-03-03T10:00:00",
                    "is_large_aggregate": False,
                    "is_mixed": False,
                    "sections": [
                        {
                            "name": "Auth rollout",
                            "theme": "auth-session",
                            "importance": "primary",
                            "items": [
                                {"op": "feat", "summary": "Add login session refresh token flow"}
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "demand",
                        "description": "Issue and demand mapping",
                        "paths": ["src/demand/"],
                        "keywords": ["demand", "issue", "requirement"],
                    },
                ]
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        original_build_sha_file_map = mod.build_sha_file_map
        mod.build_sha_file_map = lambda repo_path, shas: ({"e" * 40: ["src/auth/login.py", "src/demand/card.py"]}, True)
        try:
            ok = runner._run_ingest(state)
        finally:
            mod.build_sha_file_map = original_build_sha_file_map

        assert ok is False
        assert state.metadata["needs_llm_classify"] == 1
        assert not (semantic_dir / "units" / "all.jsonl").exists()

    def test_after_multi_domain_failure_requires_orchestration_instead_of_degrading(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "f" * 40,
                    "author": "yan.",
                    "date": "2026-03-03T10:00:00",
                    "is_large_aggregate": False,
                    "is_mixed": False,
                    "sections": [
                        {
                            "name": "Infra cleanup",
                            "theme": "maintenance",
                            "importance": "primary",
                            "items": [
                                {"op": "refactor", "summary": "Refactor helper wiring"}
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "discover_mode": "cached_llm",
                "orchestration_mode_at_discover": "llm_preferred",
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "demand",
                        "description": "Issue and demand mapping",
                        "paths": ["src/demand/"],
                        "keywords": ["demand", "issue", "requirement"],
                    },
                ]
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        original_build_sha_file_map = mod.build_sha_file_map
        mod.build_sha_file_map = lambda repo_path, shas: ({"f" * 40: ["src/auth/login.py", "src/demand/card.py"]}, True)
        try:
            ok = runner._run_ingest(state)
        finally:
            mod.build_sha_file_map = original_build_sha_file_map

        assert ok is False
        assert state.metadata["needs_llm_classify"] == 1
        assert not (semantic_dir / "units" / "all.jsonl").exists()

    def test_ambiguous_non_path_signals_require_orchestration(self, tmp_path):
        mod = load_commit_semantic_module()
        extract_dir = tmp_path / "data" / "commit-extract"
        semantic_dir = tmp_path / "data" / "commit-semantic"
        extract_dir.mkdir(parents=True)
        semantic_dir.mkdir(parents=True)

        save_jsonl(
            [
                {
                    "sha": "g" * 40,
                    "author": "yan.",
                    "date": "2026-03-03T10:00:00",
                    "is_large_aggregate": True,
                    "is_mixed": True,
                    "sections": [
                        {
                            "name": "Update",
                            "theme": "auth issue",
                            "importance": "primary",
                            "items": [
                                {"op": "feat", "summary": "Refine handling"}
                            ],
                        }
                    ],
                    "rules_invariants": [],
                }
            ],
            str(extract_dir / "2026-03.jsonl"),
        )
        save_json(
            {
                "domains": [
                    {
                        "domain": "auth",
                        "description": "Authentication and sessions",
                        "paths": ["src/auth/"],
                        "keywords": ["auth", "login", "session", "token"],
                    },
                    {
                        "domain": "issue-triage",
                        "description": "Issue processing",
                        "paths": [],
                        "keywords": ["issue", "routing", "auth"],
                    },
                ]
            },
            str(semantic_dir / "domains.json"),
        )

        mod.EXTRACT_OUTPUT = extract_dir
        mod.SEMANTIC_OUTPUT = semantic_dir

        from src.harness_state import HarnessState
        runner = mod.CommitSemanticRunner()
        state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

        ok = runner._run_ingest(state)

        assert ok is False
        assert state.metadata["needs_llm_classify"] == 1
        assert not (semantic_dir / "units" / "all.jsonl").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
