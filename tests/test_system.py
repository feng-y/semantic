"""System Test Suite — 13 categories from semantic_harness_system_test_features.md.

Covers all test categories. Some delegate to existing Step 7/8 tests via shared
helpers; others add new coverage for gaps.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import artifact_writer, context_builder
from src.artifact_writer import (
    check_semantic_snapshot,
    commit_staged,
    get_latest_version_path,
    get_latest_working_version_path,
    prune_old_versions,
    stage_artifact,
    write_artifact,
    write_baseline,
    write_semantic_snapshot,
)
from src.refine_executor import (
    BASELINE_SECTIONS,
    KNOWLEDGE_CONFIDENCE_SECTIONS,
    REPO_UNDERSTANDING_SECTIONS,
    _check_acceptance,
    _has_any_section_heading,
    evaluate_acceptance,
    parse_baseline_output,
    run_refine,
    validate_baseline_artifact,
    validate_refined_artifact,
)
from src.discovery_executor import validate_artifact_content
from tests.fake_executors import stub_executor


# ---------------------------------------------------------------------------
# Fixtures & Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Minimal repo scaffold with manifest, skills, and prompts."""
    (tmp_path / "manifest.yaml").write_text(
        "name: semantic-harness\nversion: 1.0.0\ntarget: claude-code\n"
        "skills:\n"
        "  orchestrator: skills/semantic-harness.skill\n"
        "  discovery: skills/repo-semantic-discovery.skill\n"
        "  refinement: skills/semantic-refinement.skill\n"
    )
    for name, content in {
        "semantic-harness.skill": "name: semantic-harness\npurpose: orchestrator\n",
        "repo-semantic-discovery.skill": "name: repo-semantic-discovery\npurpose: discovery\nsteps: []\n",
        "semantic-refinement.skill": (
            "name: semantic-refinement\npurpose: refinement\n"
            "steps:\n"
            "  - run: prompts/refine/semantic-refine.patch.prompt\n"
            "  - run: prompts/refine/semantic-change-log.prompt\n"
            "  - run: prompts/validation/validate-artifact.prompt\n"
            "  - apply: protocols/artifact-versioning.md\n"
            "  - if: architect acceptance detected\n"
            "    run: prompts/refine/baseline-synthesis.prompt\n"
        ),
    }.items():
        d = tmp_path / "skills"
        d.mkdir(exist_ok=True)
        (d / name).write_text(content)
    for p in (
        "prompts/refine/semantic-refine.patch.prompt",
        "prompts/refine/semantic-change-log.prompt",
        "prompts/refine/baseline-synthesis.prompt",
        "prompts/validation/validate-artifact.prompt",
    ):
        fp = tmp_path / p
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(f"Goal: stub prompt for {fp.name}\n")
    return tmp_path


def _write_disc(repo: Path, name: str, content: str, version: int = 1) -> Path:
    d = repo / "docs" / "semantic" / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.v{version}.md"
    p.write_text(content)
    return p


def _write_review(repo: Path, name: str, content: str) -> Path:
    d = repo / "docs" / "semantic" / "review"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    p.write_text(content)
    return p


def _seed_all(repo: Path) -> None:
    for name in ("repo-understanding", "knowledge-confidence", "domain-candidates"):
        _write_disc(repo, name, stub_executor("", {}, artifact_name=name))
    _write_review(repo, "review-summary", stub_executor("", {}, artifact_name="review-summary"))


def _make_executor(overrides: dict[str, str] | None = None):
    ov = overrides or {}
    def executor(prompt_text, context, *, artifact_name, sampling_mode="auto"):
        if artifact_name in ov:
            return ov[artifact_name]
        return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)
    return executor


def _clean_semantic(repo: Path) -> None:
    for d in ("discovery", "review", "baseline"):
        dd = repo / "docs" / "semantic" / d
        if dd.exists():
            shutil.rmtree(dd)
    snap = repo / "docs" / "semantic" / "semantic_snapshot.json"
    if snap.exists():
        snap.unlink()


# ===========================================================================
# Category 1 — Pipeline Determinism
# ===========================================================================


class TestCat1Determinism:
    def test_three_runs_identical_baselines(self, repo: Path) -> None:
        baselines: list[dict[str, str]] = []
        for _ in range(3):
            _clean_semantic(repo)
            _seed_all(repo)
            _write_review(repo, "architect-feedback", "acceptance: true\n\nLGTM.\n")
            result = run_refine(repo, executor=_make_executor())
            assert result.status == "ok" and result.baseline_generated
            bl_dir = repo / "docs" / "semantic" / "baseline"
            baselines.append({n: (bl_dir / f"{n}.md").read_text() for n in BASELINE_SECTIONS})
        for name in BASELINE_SECTIONS:
            assert all(b[name] == baselines[0][name] for b in baselines)

    def test_version_numbers_deterministic(self, repo: Path) -> None:
        versions: list[dict] = []
        for _ in range(2):
            _clean_semantic(repo)
            _seed_all(repo)
            _write_review(repo, "architect-feedback", "acceptance: true\n")
            run_refine(repo, executor=_make_executor())
            cp = json.loads((repo / "docs" / "semantic" / "baseline" / "checkpoint.json").read_text())
            versions.append(cp["source_versions"])
        assert versions[0] == versions[1]


# ===========================================================================
# Category 2 — Artifact Validation Coverage
# ===========================================================================


class TestCat2ValidationCoverage:
    @pytest.mark.parametrize("name", [
        "repo-understanding", "knowledge-confidence", "domain-candidates", "review-summary",
    ])
    def test_empty_artifact_rejected(self, name: str) -> None:
        errors = validate_artifact_content("", name)
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    @pytest.mark.parametrize("name", [
        "repo-understanding", "knowledge-confidence", "domain-candidates", "review-summary",
    ])
    def test_missing_section_rejected(self, name: str) -> None:
        bad = f"# {name}\n\nSome text but no schema headings.\n"
        errors = validate_artifact_content(bad, name)
        assert len(errors) > 0

    @pytest.mark.parametrize("name", [
        "repo-understanding", "knowledge-confidence",
    ])
    def test_malformed_heading_rejected(self, name: str) -> None:
        # ### instead of ##
        if name == "repo-understanding":
            bad = f"# {name}\n\n### System Purpose\nContent.\n"
        else:
            bad = f"# {name}\n\n### Confirmed Knowledge\nContent.\n"
        errors = validate_artifact_content(bad, name)
        assert len(errors) > 0

    @pytest.mark.parametrize("name", [
        "repo-facts", "repo-understanding", "knowledge-confidence",
        "domain-candidates", "review-summary",
    ])
    def test_valid_stub_passes(self, name: str) -> None:
        content = stub_executor("", {}, artifact_name=name)
        assert validate_artifact_content(content, name) == []


# ===========================================================================
# Category 3 — Executor Repair Behavior
# ===========================================================================


class TestCat3ExecutorRepair:
    def test_good_executor_repairs_bad_source(self, repo: Path) -> None:
        _seed_all(repo)
        _write_disc(repo, "repo-understanding", "# repo-understanding\n\n(corrupted)")
        _write_review(repo, "architect-feedback", "Some feedback.\n")
        result = run_refine(repo, executor=_make_executor())
        assert result.status == "ok"
        # New version written with valid content
        assert len(result.artifacts_written) > 0


# ===========================================================================
# Category 4 — Executor Failure Handling
# ===========================================================================


class TestCat4ExecutorFailure:
    def test_bad_executor_halts_pipeline(self, repo: Path) -> None:
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "feedback.\n")

        def bad_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return f"# {artifact_name}\n\nGarbage.\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=bad_exec)
        assert result.status == "validation_failed"

    def test_no_new_artifact_on_failure(self, repo: Path) -> None:
        _seed_all(repo)
        original_ru = (repo / "docs" / "semantic" / "discovery" / "repo-understanding.v1.md").read_text()
        _write_review(repo, "architect-feedback", "feedback.\n")

        def bad_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return "broken\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        run_refine(repo, executor=bad_exec)
        # No v2 written
        v2 = repo / "docs" / "semantic" / "discovery" / "repo-understanding.v2.md"
        assert not v2.exists()
        # v1 intact
        assert (repo / "docs" / "semantic" / "discovery" / "repo-understanding.v1.md").read_text() == original_ru


# ===========================================================================
# Category 5 — Version Integrity
# ===========================================================================


class TestCat5VersionIntegrity:
    def test_pruning_preserves_valid_when_newer_invalid(self, repo: Path) -> None:
        """v1 valid, v2 valid, v3 invalid (empty), v4 invalid (empty) — pruning safe."""
        d = repo / "docs" / "semantic" / "discovery"
        d.mkdir(parents=True, exist_ok=True)
        (d / "repo-understanding.v1.md").write_text(stub_executor("", {}, artifact_name="repo-understanding"))
        (d / "repo-understanding.v2.md").write_text(stub_executor("", {}, artifact_name="repo-understanding"))
        (d / "repo-understanding.v3.md").write_text("")  # invalid (empty)
        (d / "repo-understanding.v4.md").write_text("")  # invalid (empty)

        # Protect v2 as accepted
        removed = prune_old_versions(
            repo, "discovery", "repo-understanding", keep=2, accepted_versions={2},
        )
        # v1 may be pruned, but v2 (accepted) must survive
        assert (d / "repo-understanding.v2.md").exists()
        assert "repo-understanding.v2.md" not in {p.name for p in removed}

    def test_latest_version_resolution_skips_empty(self, repo: Path) -> None:
        d = repo / "docs" / "semantic" / "discovery"
        d.mkdir(parents=True, exist_ok=True)
        (d / "repo-understanding.v1.md").write_text("valid v1\n")
        (d / "repo-understanding.v2.md").write_text("valid v2\n")
        (d / "repo-understanding.v3.md").write_text("")  # empty
        (d / "repo-understanding.v4.md").write_text("")  # empty

        latest = get_latest_version_path(repo, "discovery", "repo-understanding")
        assert latest is not None
        assert latest.name == "repo-understanding.v2.md"

    def test_version_numbers_always_increase(self, repo: Path) -> None:
        d = repo / "docs" / "semantic" / "discovery"
        d.mkdir(parents=True, exist_ok=True)
        (d / "repo-understanding.v1.md").write_text("v1\n")
        (d / "repo-understanding.v3.md").write_text("v3\n")
        # Next version should be 4 (max + 1)
        p = write_artifact(repo, "discovery", "repo-understanding", "v4\n")
        assert "v4" in p.name


# ===========================================================================
# Category 6 — Version Skew Detection
# ===========================================================================


class TestCat6VersionSkew:
    def test_skew_detected(self, repo: Path) -> None:
        _write_disc(repo, "repo-understanding",
                    stub_executor("", {}, artifact_name="repo-understanding"), version=3)
        _write_disc(repo, "knowledge-confidence",
                    stub_executor("", {}, artifact_name="knowledge-confidence"), version=1)
        _write_disc(repo, "domain-candidates",
                    stub_executor("", {}, artifact_name="domain-candidates"), version=1)
        write_artifact(repo, "review", "review-summary",
                       stub_executor("", {}, artifact_name="review-summary"))
        write_semantic_snapshot(repo)

        # Advance only repo-understanding
        _write_disc(repo, "repo-understanding",
                    stub_executor("", {}, artifact_name="repo-understanding"), version=4)

        warnings = check_semantic_snapshot(repo)
        assert any("repo-understanding" in w for w in warnings)

    def test_skew_halts_pipeline(self, repo: Path) -> None:
        _seed_all(repo)
        write_semantic_snapshot(repo)
        _write_disc(repo, "repo-understanding",
                    stub_executor("", {}, artifact_name="repo-understanding"), version=2)
        _write_review(repo, "architect-feedback", "acceptance: true\n")
        result = run_refine(repo, executor=_make_executor())
        assert result.status == "version_skew"


# ===========================================================================
# Category 7 — Multi-Artifact Atomicity
# ===========================================================================


class TestCat7Atomicity:
    def test_both_pass_both_committed(self, repo: Path) -> None:
        good_ru = stub_executor("", {}, artifact_name="repo-understanding")
        good_kc = stub_executor("", {}, artifact_name="knowledge-confidence")
        p1, c1, e1 = stage_artifact(repo, "discovery", "repo-understanding", good_ru,
                                     validate_fn=validate_refined_artifact)
        p2, c2, e2 = stage_artifact(repo, "discovery", "knowledge-confidence", good_kc,
                                     validate_fn=validate_refined_artifact)
        assert e1 == [] and e2 == []
        written = commit_staged([(p1, c1), (p2, c2)])
        assert len(written) == 2
        assert all(p.exists() for p in written)

    def test_one_fails_none_committed(self, repo: Path) -> None:
        good_ru = stub_executor("", {}, artifact_name="repo-understanding")
        bad_kc = "# kc\n\nNo schema headings.\n"
        _, _, e1 = stage_artifact(repo, "discovery", "repo-understanding", good_ru,
                                   validate_fn=validate_refined_artifact)
        _, _, e2 = stage_artifact(repo, "discovery", "knowledge-confidence", bad_kc,
                                   validate_fn=validate_refined_artifact)
        assert e1 == []
        assert len(e2) > 0
        # Don't commit — verify nothing on disk
        disc = repo / "docs" / "semantic" / "discovery"
        assert not list(disc.glob("*.md")) if disc.exists() else True


# ===========================================================================
# Category 8 — Baseline Parser Contract
# ===========================================================================


class TestCat8BaselineParser:
    def test_valid_output_parses(self) -> None:
        content = stub_executor("", {}, artifact_name="baseline")
        sections = parse_baseline_output(content)
        assert set(sections.keys()) == {"purpose", "domains", "concepts", "pipelines"}

    def test_missing_section_fails(self) -> None:
        content = "## Purpose\nPrimary Purpose: test\n\n## Domains\nDomain Name: test\n"
        sections = parse_baseline_output(content)
        assert "concepts" not in sections and "pipelines" not in sections

    def test_duplicate_section_fails(self) -> None:
        content = (
            "## Purpose\nPrimary Purpose: first\n\n"
            "## Purpose\nPrimary Purpose: second\n\n"
            "## Domains\nDomain Name: test\n\n"
            "## Concepts\nConcept Name: test\n\n"
            "## Pipelines\nPipeline Name: test\n"
        )
        sections = parse_baseline_output(content)
        assert "purpose" not in sections

    def test_malformed_heading_ignored(self) -> None:
        content = "### Purpose\nPrimary Purpose: test\n"
        sections = parse_baseline_output(content)
        assert "purpose" not in sections

    def test_incomplete_baseline_not_written(self, repo: Path) -> None:
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "acceptance: true\n")

        def partial_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name == "baseline":
                return "## Purpose\nPrimary Purpose: test\n\n## Domains\nDomain Name: test\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=partial_exec)
        assert not result.baseline_generated


# ===========================================================================
# Category 9 — Acceptance Gate Safety
# ===========================================================================


class TestCat9AcceptanceGate:
    def test_acceptance_true_required(self) -> None:
        assert _check_acceptance("acceptance: true\n")
        assert not _check_acceptance("I accept this.\n")
        assert not _check_acceptance("acceptance: false\n")
        assert not _check_acceptance("")

    def test_no_acceptance_blocks_baseline(self, repo: Path) -> None:
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "Looks good but no acceptance field.\n")
        result = run_refine(repo, executor=_make_executor())
        assert result.acceptance_detected is False
        assert result.baseline_generated is False

    def test_structural_gates_block_baseline(self, repo: Path) -> None:
        """acceptance: true present but artifacts invalid → baseline blocked."""
        _write_disc(repo, "repo-understanding", "# ru\n\nNo schema headings.\n")
        _write_disc(repo, "knowledge-confidence", "# kc\n\nNo schema headings.\n")
        _write_disc(repo, "domain-candidates", stub_executor("", {}, artifact_name="domain-candidates"))
        feedback = "acceptance: true\n"
        passed, failures = evaluate_acceptance(repo, feedback)
        assert not passed
        assert len(failures) >= 2


# ===========================================================================
# Category 10 — Baseline Immutability
# ===========================================================================


class TestCat10BaselineImmutability:
    def test_working_version_excludes_baseline(self, repo: Path) -> None:
        assert get_latest_working_version_path(repo, "baseline", "purpose") is None

    def test_baseline_write_only_by_synthesis(self, repo: Path) -> None:
        p = write_baseline(repo, "purpose", "Primary Purpose: test\n")
        assert "baseline" in str(p)
        assert p.exists()

    def test_refine_context_never_reads_baseline(self, repo: Path) -> None:
        _seed_all(repo)
        # Write a baseline artifact
        write_baseline(repo, "purpose", "Primary Purpose: test\n")
        ctx = context_builder.build_refine_context(repo, "patch", feedback="test")
        # No baseline content should appear
        for key, val in ctx.items():
            assert "Primary Purpose: test" not in val or key == "architect_feedback"


# ===========================================================================
# Category 11 — Context Boundary
# ===========================================================================


class TestCat11ContextBoundary:
    def test_refine_context_artifact_only(self, repo: Path) -> None:
        _seed_all(repo)
        ctx = context_builder.build_refine_context(repo, "patch", feedback="test feedback")
        allowed = {"repo_understanding", "knowledge_confidence", "architect_feedback"}
        for key in ctx:
            assert key in allowed, f"Unexpected context key: {key}"

    def test_baseline_context_artifact_only(self, repo: Path) -> None:
        _seed_all(repo)
        ctx = context_builder.build_baseline_context(repo)
        allowed = {"repo_understanding", "knowledge_confidence", "domain_candidates", "review_summary"}
        for key in ctx:
            assert key in allowed, f"Unexpected context key: {key}"

    def test_refine_context_no_repo_tree(self, repo: Path) -> None:
        _seed_all(repo)
        ctx = context_builder.build_refine_context(repo, "patch", feedback="test")
        assert "repo_tree_summary" not in ctx
        assert "selected_files" not in ctx


# ===========================================================================
# Category 12 — Runtime Purity
# ===========================================================================


class TestCat12RuntimePurity:
    def test_no_stub_imports_in_src(self) -> None:
        src_dir = Path(__file__).resolve().parent.parent / "src"
        violations: list[str] = []
        for py_file in src_dir.glob("*.py"):
            content = py_file.read_text()
            for pattern in ("stub_executor", "fake_executor", "from tests"):
                if pattern in content:
                    violations.append(f"{py_file.name}: contains '{pattern}'")
        assert violations == [], f"Runtime purity violations: {violations}"

    def test_no_llm_sdk_in_src(self) -> None:
        src_dir = Path(__file__).resolve().parent.parent / "src"
        violations: list[str] = []
        for py_file in src_dir.glob("*.py"):
            content = py_file.read_text()
            for sdk in ("import openai", "import anthropic", "import langchain", "import litellm"):
                if sdk in content:
                    violations.append(f"{py_file.name}: contains '{sdk}'")
        assert violations == [], f"SDK violations: {violations}"


# ===========================================================================
# Category 13 — Failure Recovery
# ===========================================================================


class TestCat13FailureRecovery:
    def test_rerun_after_failure_succeeds(self, repo: Path) -> None:
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "feedback.\n")

        def bad_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return f"# {artifact_name}\n\nBroken.\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        r1 = run_refine(repo, executor=bad_exec)
        assert r1.status == "validation_failed"

        r2 = run_refine(repo, executor=_make_executor())
        assert r2.status == "ok"

    def test_prior_artifacts_preserved(self, repo: Path) -> None:
        _seed_all(repo)
        original = (repo / "docs" / "semantic" / "discovery" / "repo-understanding.v1.md").read_text()
        _write_review(repo, "architect-feedback", "feedback.\n")

        def bad_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return "broken\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        run_refine(repo, executor=bad_exec)
        assert (repo / "docs" / "semantic" / "discovery" / "repo-understanding.v1.md").read_text() == original

    def test_baseline_failure_preserves_working_state(self, repo: Path) -> None:
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "acceptance: true\n")

        def bad_baseline_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name == "baseline":
                return "## Purpose\nPrimary Purpose: test\n"  # missing 3 sections
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=bad_baseline_exec)
        assert not result.baseline_generated
        # Working artifacts still exist
        assert get_latest_version_path(repo, "discovery", "repo-understanding") is not None
