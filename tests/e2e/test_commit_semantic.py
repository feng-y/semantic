"""E2E tests for commit-semantic V1 capability-first pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import save_jsonl, load_jsonl, load_json, save_json


class FakeHostExecutor:
    """Deterministic host executor for commit-semantic V1 tests."""

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

        if artifact_name == "repo-hints":
            return json.dumps(
                {
                    "local_capabilities": ["commit-extract", "commit-semantic", "demand"],
                    "aliases": [
                        {"alias": "repo-structure", "canonical": "fact"},
                        {"alias": "semantic-fact", "canonical": "fact"},
                    ],
                    "ownership_hints": [
                        {"path_prefix": "skills/commit-extract/", "capability": "commit-extract"},
                        {"path_prefix": "skills/commit-semantic/", "capability": "commit-semantic"},
                    ],
                    "seed_concepts": ["canonical-demand", "semantic-unit", "invariant"],
                    "doc_sources": ["README.md"],
                    "confidence": "high",
                }
            )

        if artifact_name == "capability-signals":
            return json.dumps(
                {
                    "signals": [
                        {
                            "kind": "capability",
                            "name": "domain aggregation",
                            "description": "Aggregate commit-derived semantic units into stable semantic groupings",
                            "source_commit": "aaa111",
                            "evidence_refs": ["sha:aaa111", "summary:aaa111:0:0"],
                            "confidence": "high",
                            "flags": [],
                            "related_capability_names": [],
                        },
                        {
                            "kind": "capability",
                            "name": "domain aggregation",
                            "description": "Continue refining capability-first semantic grouping",
                            "source_commit": "bbb222",
                            "evidence_refs": ["sha:bbb222", "summary:bbb222:0:0"],
                            "confidence": "medium",
                            "flags": ["mixed"],
                            "related_capability_names": ["review hardening"],
                        },
                        {
                            "kind": "capability",
                            "name": "review hardening",
                            "description": "Harden review and validation behavior for semantic output",
                            "source_commit": "ccc333",
                            "evidence_refs": ["sha:ccc333", "summary:ccc333:0:0"],
                            "confidence": "medium",
                            "flags": ["low_signal"],
                            "related_capability_names": [],
                        },
                    ]
                }
            )

        if artifact_name == "capability-candidates":
            return json.dumps(
                {
                    "capabilities": [
                        {
                            "capability_id": "cap-domain-aggregation",
                            "canonical_name": "domain-aggregation",
                            "observed_names": ["domain aggregation", "capability-first semantic grouping"],
                            "description": "Aggregate commit-first semantic signals into stable capability groupings",
                            "evidence_refs": ["sha:aaa111", "sha:bbb222"],
                            "repo_context_refs": ["commit-semantic"],
                            "confidence": "high",
                            "status": "stable",
                            "naming_source": "synthesized",
                            "flags": [],
                        },
                        {
                            "capability_id": "cap-review-hardening",
                            "canonical_name": "review-hardening",
                            "observed_names": ["review hardening"],
                            "description": "Improve semantic review strictness and validation quality",
                            "evidence_refs": ["sha:ccc333"],
                            "repo_context_refs": ["commit-semantic"],
                            "confidence": "low",
                            "status": "candidate",
                            "naming_source": "observed-pattern",
                            "flags": ["low_signal"],
                        },
                    ]
                }
            )

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
    return [
        {
            "sha": "aaa111", "author": "yan.", "date": "2026-03-01T10:00:00",
            "is_large_aggregate": False, "is_mixed": False,
            "sections": [
                {"name": "Semantic aggregation", "theme": "domain-aggregation", "importance": "primary",
                 "items": [{"op": "feat", "summary": "Add capability-first semantic grouping"}]},
                {"name": "Validation", "theme": "review-hardening", "importance": "secondary",
                 "items": [{"op": "bugfix", "summary": "Tighten semantic validation"}]},
            ],
            "rules_invariants": [
                {"kind": "semantic", "statement": "Capabilities require evidence refs", "enforced_by_commit": True}
            ],
        },
        {
            "sha": "bbb222", "author": "yan.", "date": "2026-03-02T11:00:00",
            "is_large_aggregate": True, "is_mixed": True,
            "sections": [
                {"name": "Mixed review flow", "theme": "domain-aggregation", "importance": "primary",
                 "items": [{"op": "feat", "summary": "Refine capability grouping under mixed commits"}]},
            ],
            "rules_invariants": [],
        },
        {
            "sha": "ccc333", "author": "bob", "date": "2026-03-05T09:00:00",
            "is_large_aggregate": False, "is_mixed": False,
            "sections": [
                {"name": "Review", "theme": "review-hardening", "importance": "primary",
                 "items": [{"op": "feat", "summary": "Add stricter semantic review gates"}]},
                {"name": "Config", "theme": "config-mgmt", "importance": "secondary",
                 "items": [{"op": "config", "summary": "Add review config flags"}]},
            ],
            "rules_invariants": [
                {"kind": "semantic", "statement": "Capabilities require evidence refs", "enforced_by_commit": True}
            ],
        },
    ]


V1_STAGES = ["context", "extract-signals", "synthesize-capabilities", "validate", "export"]


def _setup_and_run(tmp_path, sample_jsonl_records, stages=None, executor=None):
    mod = load_commit_semantic_module()
    extract_dir = tmp_path / "data" / "commit-extract"
    semantic_dir = tmp_path / "data" / "commit-semantic"
    extract_dir.mkdir(parents=True)

    save_jsonl(sample_jsonl_records, str(extract_dir / "2026-03.jsonl"))

    mod.EXTRACT_OUTPUT = extract_dir
    mod.SEMANTIC_OUTPUT = semantic_dir

    from src.harness_state import HarnessState
    runner = mod.CommitSemanticRunner(executor=executor)
    state = HarnessState(stage="init", metadata={"completed_stages": [], "artifacts_written": [], "status": "ok"})

    for stage in (stages or V1_STAGES):
        assert runner.run_stage(stage, state)

    return mod, semantic_dir, state, runner


class TestCommitSemanticSkill:
    def test_skill_exists(self):
        mod = load_commit_semantic_module()
        runner = mod.CommitSemanticRunner()
        assert runner.PIPELINE == "commit-semantic"
        assert runner.STAGES == V1_STAGES


class TestCommitSemanticContext:
    def test_context_stage_writes_repo_hints_and_context(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, _, runner = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            ["context"],
            executor=FakeHostExecutor(),
        )
        hints = load_json(str(semantic_dir / "repo-hints.json"))
        context = load_json(str(semantic_dir / "repo-context.json"))
        assert hints["local_capabilities"] == ["commit-extract", "commit-semantic", "demand"]
        assert context["local_capabilities"] == ["commit-extract", "commit-semantic", "demand"]
        assert context["confidence"] == "high"
        assert len(runner.get_artifacts(runner.init_state())) == 0  # smoke: method exists

    def test_context_requires_orchestration(self, tmp_path, sample_jsonl_records):
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
        assert runner._run_context(state) is False
        assert not (semantic_dir / "repo-hints.json").exists()


class TestCommitSemanticSignals:
    def test_extract_signals_writes_capability_candidates_jsonl(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, state, _ = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            ["context", "extract-signals"],
            executor=FakeHostExecutor(),
        )
        signals = load_jsonl(str(semantic_dir / "capabilities-candidates.jsonl"))
        assert len(signals) == 3
        assert {signal["kind"] for signal in signals} == {"capability"}
        assert state.metadata["signal_count"] == 3
        assert all("source_commit" in signal for signal in signals)
        assert all("evidence_refs" in signal for signal in signals)


class TestCommitSemanticCapabilities:
    def test_synthesize_capabilities_overwrites_candidate_file_with_capabilities(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, state, _ = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            ["context", "extract-signals", "synthesize-capabilities"],
            executor=FakeHostExecutor(),
        )
        candidates = load_jsonl(str(semantic_dir / "capabilities-candidates.jsonl"))
        assert len(candidates) == 2
        assert candidates[0]["capability_id"] == "cap-domain-aggregation"
        assert candidates[0]["status"] == "stable"
        assert state.metadata["capability_candidate_count"] == 2

    def test_validate_writes_stable_capabilities(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, state, _ = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            ["context", "extract-signals", "synthesize-capabilities", "validate"],
            executor=FakeHostExecutor(),
        )
        capabilities = load_jsonl(str(semantic_dir / "capabilities.jsonl"))
        assert len(capabilities) == 2
        stable = [cap for cap in capabilities if cap["capability_id"] == "cap-domain-aggregation"][0]
        assert stable["canonical_name"] == "domain-aggregation"
        assert stable["confidence"] == "high"
        assert stable["status"] == "stable"
        review = [cap for cap in capabilities if cap["capability_id"] == "cap-review-hardening"][0]
        assert review["status"] == "candidate"
        assert review["confidence"] == "low"
        assert state.metadata["stable_capability_count"] == 2


class TestCommitSemanticExport:
    def test_export_summary_reports_v1_health_fields(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, _, _ = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            V1_STAGES,
            executor=FakeHostExecutor(),
        )
        summary = load_json(str(semantic_dir / "summary.json"))
        assert summary["signal_count"] == 3
        assert summary["capability_candidate_count"] == 2
        assert summary["stable_capability_count"] == 2
        assert "mixed_ratio" in summary
        assert "low_signal_ratio" in summary
        assert "evidence_coverage" in summary
        assert "naming_drift_count" in summary
        assert summary["evidence_coverage"] > 0

    def test_export_removes_legacy_domain_first_artifacts(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, state, runner = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            ["context", "extract-signals", "synthesize-capabilities", "validate"],
            executor=FakeHostExecutor(),
        )
        save_jsonl([{"domain": "legacy"}], str(semantic_dir / "domains-aggregated.jsonl"))
        save_jsonl([{"domain": "legacy"}], str(semantic_dir / "canonical-demands.jsonl"))
        save_json({"domain": "legacy"}, str(semantic_dir / "domains.json"))
        assert runner._run_export(state)
        assert not (semantic_dir / "domains-aggregated.jsonl").exists()
        assert not (semantic_dir / "canonical-demands.jsonl").exists()
        assert not (semantic_dir / "domains.json").exists()


class TestCommitSemanticFullPipeline:
    def test_all_v1_stages_produce_v1_outputs(self, tmp_path, sample_jsonl_records):
        _, semantic_dir, _, _ = _setup_and_run(
            tmp_path,
            sample_jsonl_records,
            V1_STAGES,
            executor=FakeHostExecutor(),
        )
        assert (semantic_dir / "repo-hints.json").exists()
        assert (semantic_dir / "repo-context.json").exists()
        assert (semantic_dir / "capabilities-candidates.jsonl").exists()
        assert (semantic_dir / "capabilities.jsonl").exists()
        assert (semantic_dir / "summary.json").exists()

    def test_local_run_without_orchestration_fails_cleanly(self, tmp_path):
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
                        "name": "Semantic extraction",
                        "theme": "capability-first",
                        "importance": "primary",
                        "items": [{"op": "feat", "summary": "Introduce commit-first capability extraction"}],
                    }
                ],
                "rules_invariants": [],
            }
        ]
        save_jsonl(records, str(extract_dir / "2026-03.jsonl"))
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent.parent.parent / "skills/commit-semantic/run.py"), "run"],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )
        assert result.returncode == 1
        semantic_dir = tmp_path / "data" / "commit-semantic"
        assert not (semantic_dir / "summary.json").exists()
        assert "orchestration unavailable" in (result.stderr + result.stdout).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
