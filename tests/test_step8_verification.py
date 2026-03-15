"""Step 8 — System Verification & Failure Hardening Tests.

Part A of the Step 8 execution plan:
  1. End-to-end determinism
  2. Failure injection (truncated, missing section, malformed)
  3. Version integrity (pruning safety, version skew)
  4. Prompt/output contract robustness
  5. Global invariant verification
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import artifact_writer, context_builder
from src.artifact_writer import (
    commit_staged,
    get_latest_version_path,
    get_latest_working_version_path,
    prune_old_versions,
    stage_artifact,
    write_artifact,
    write_baseline,
    check_semantic_snapshot,
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
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Minimal repo scaffold with manifest, skills, and prompts."""
    (tmp_path / "manifest.yaml").write_text(
        "name: semantic-harness\nversion: 1.0.0\ntarget: claude-code\n"
        "skills:\n"
        "  init: skills/semantic-init.skill\n"
        "  discover: skills/semantic-discover.skill\n"
        "  refine: skills/semantic-refine.skill\n"
    )
    for name, content in {
        "semantic-init.skill": "name: semantic-init\npurpose: workspace initialization\n",
        "semantic-discover.skill": "name: semantic-discover\npurpose: discovery\nsteps: []\n",
        "semantic-refine.skill": (
            "name: semantic-refine\npurpose: refinement\n"
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    """Write all discovery + review artifacts needed for refine."""
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


# ===========================================================================
# 1. End-to-End Determinism
# ===========================================================================


class TestDeterminism:
    """Run full refine pipeline multiple times, verify identical results."""

    def test_three_runs_produce_identical_baselines(self, repo: Path) -> None:
        """3 runs with identical input state produce identical baseline artifacts."""
        baselines: list[dict[str, str]] = []

        for run_idx in range(3):
            # Clean working state between runs
            for d in ("discovery", "review", "baseline"):
                dd = repo / "docs" / "semantic" / d
                if dd.exists():
                    import shutil
                    shutil.rmtree(dd)
            # Also remove snapshot
            snap = repo / "docs" / "semantic" / "semantic_snapshot.json"
            if snap.exists():
                snap.unlink()

            _seed_all(repo)
            _write_review(repo, "architect-feedback", "acceptance: true\n\nLGTM.\n")

            result = run_refine(repo, executor=_make_executor())
            assert result.status == "ok", f"Run {run_idx}: status={result.status}"
            assert result.baseline_generated, f"Run {run_idx}: no baseline"

            # Read baseline files
            bl_dir = repo / "docs" / "semantic" / "baseline"
            run_baselines = {}
            for name in BASELINE_SECTIONS:
                p = bl_dir / f"{name}.md"
                assert p.exists(), f"Run {run_idx}: missing {name}.md"
                run_baselines[name] = p.read_text()
            baselines.append(run_baselines)

        # Compare all runs
        for name in BASELINE_SECTIONS:
            contents = [b[name] for b in baselines]
            assert all(c == contents[0] for c in contents), (
                f"Baseline '{name}' differs across runs"
            )

    def test_checkpoint_metadata_consistent_across_runs(self, repo: Path) -> None:
        """Checkpoint source_versions and baseline_files are consistent."""
        checkpoints: list[dict] = []

        for _ in range(2):
            for d in ("discovery", "review", "baseline"):
                dd = repo / "docs" / "semantic" / d
                if dd.exists():
                    import shutil
                    shutil.rmtree(dd)
            snap = repo / "docs" / "semantic" / "semantic_snapshot.json"
            if snap.exists():
                snap.unlink()

            _seed_all(repo)
            _write_review(repo, "architect-feedback", "acceptance: true\n")
            run_refine(repo, executor=_make_executor())

            cp = json.loads((repo / "docs" / "semantic" / "baseline" / "checkpoint.json").read_text())
            checkpoints.append(cp)

        assert checkpoints[0]["source_versions"] == checkpoints[1]["source_versions"]
        assert checkpoints[0]["baseline_files"] == checkpoints[1]["baseline_files"]
        assert checkpoints[0]["feedback_hash"] == checkpoints[1]["feedback_hash"]


# ===========================================================================
# 2. Failure Injection
# ===========================================================================


class TestFailureInjection:
    """Corrupted/malformed artifacts halt the pipeline safely."""

    def test_scenario_a_truncated_artifact_with_bad_executor(self, repo: Path) -> None:
        """Truncated source + executor that echoes it back → validation fails, no baseline."""
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "acceptance: true\n")

        # Executor that returns truncated content (simulating LLM failure on bad input)
        def echo_executor(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name == "repo-understanding":
                return "# repo-understanding\n\n(truncated, no schema headings)\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=echo_executor)
        assert result.status == "validation_failed"
        assert not result.baseline_generated

    def test_scenario_a_truncated_kc_with_bad_executor(self, repo: Path) -> None:
        """Truncated knowledge-confidence from executor → validation fails."""
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "acceptance: true\n")

        def echo_executor(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name == "knowledge-confidence":
                return "# knowledge-confidence\n\n(truncated)\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=echo_executor)
        assert result.status == "validation_failed"
        assert not result.baseline_generated

    def test_scenario_a_good_executor_recovers_from_bad_source(self, repo: Path) -> None:
        """A capable executor that produces valid output from bad source → pipeline succeeds.
        This is correct behavior: the executor is the authority on output quality."""
        _seed_all(repo)
        # Overwrite with truncated content
        _write_disc(repo, "repo-understanding", "# repo-understanding\n\n(truncated)")
        _write_review(repo, "architect-feedback", "acceptance: true\n")

        # Good executor always produces valid output
        result = run_refine(repo, executor=_make_executor())
        assert result.status == "ok"
        # This is expected — the executor produced valid patches

    def test_scenario_b_missing_required_section(self, repo: Path) -> None:
        """Artifact with no schema-defined sections fails validation."""
        bad = "# repo-understanding\n\nSome text but no ## headings.\n"
        errors = validate_refined_artifact(bad, "repo-understanding")
        assert len(errors) > 0
        assert "schema-defined section" in errors[0].lower() or "missing" in errors[0].lower()

    def test_scenario_c_malformed_headings(self, repo: Path) -> None:
        """Malformed headings (wrong level, typos) are rejected."""
        # ### instead of ##
        bad1 = "# repo-understanding\n\n### System Purpose\nSomething.\n"
        assert not _has_any_section_heading(bad1, REPO_UNDERSTANDING_SECTIONS)
        errors1 = validate_refined_artifact(bad1, "repo-understanding")
        assert len(errors1) > 0

        # Typo in heading
        bad2 = "# kc\n\n## Confirmd Knowledge\nSomething.\n"
        assert not _has_any_section_heading(bad2, KNOWLEDGE_CONFIDENCE_SECTIONS)
        errors2 = validate_refined_artifact(bad2, "knowledge-confidence")
        assert len(errors2) > 0

    def test_previous_valid_artifacts_survive_failure(self, repo: Path) -> None:
        """After a failed refine, prior valid artifacts remain on disk."""
        _seed_all(repo)
        ru_path = repo / "docs" / "semantic" / "discovery" / "repo-understanding.v1.md"
        original_content = ru_path.read_text()

        _write_review(repo, "architect-feedback", "Some feedback.\n")

        # Executor that produces invalid output for patches
        def bad_executor(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return f"# {artifact_name}\n\nGarbage with no schema headings.\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=bad_executor)
        assert result.status == "validation_failed"

        # Original v1 artifact should still be intact
        assert ru_path.exists()
        assert ru_path.read_text() == original_content


# ===========================================================================
# 3. Version Integrity
# ===========================================================================


class TestVersionIntegrity:
    """Edge cases in version history: pruning safety, version skew."""

    def test_a_pruning_protects_accepted_versions(self, repo: Path) -> None:
        """Pruning cannot delete accepted/protected versions."""
        d = repo / "docs" / "semantic" / "discovery"
        d.mkdir(parents=True, exist_ok=True)
        for v in range(1, 6):
            (d / f"repo-understanding.v{v}.md").write_text(f"v{v} content\n")

        # Protect v2 as accepted
        removed = prune_old_versions(
            repo, "discovery", "repo-understanding",
            keep=2, accepted_versions={2},
        )
        removed_names = {p.name for p in removed}
        assert "repo-understanding.v2.md" not in removed_names
        # v4 and v5 kept by window, v2 protected
        assert (d / "repo-understanding.v2.md").exists()
        assert (d / "repo-understanding.v4.md").exists()
        assert (d / "repo-understanding.v5.md").exists()

    def test_a_pruning_keeps_latest(self, repo: Path) -> None:
        """Latest version always survives pruning."""
        d = repo / "docs" / "semantic" / "discovery"
        d.mkdir(parents=True, exist_ok=True)
        for v in range(1, 6):
            (d / f"repo-understanding.v{v}.md").write_text(f"v{v}\n")

        prune_old_versions(repo, "discovery", "repo-understanding", keep=1)
        assert (d / "repo-understanding.v5.md").exists()

    def test_b_version_skew_detected_by_snapshot(self, repo: Path) -> None:
        """Semantic snapshot detects cross-artifact version inconsistency."""
        # Write artifacts at different versions
        _write_disc(repo, "repo-understanding",
                    stub_executor("", {}, artifact_name="repo-understanding"), version=3)
        _write_disc(repo, "knowledge-confidence",
                    stub_executor("", {}, artifact_name="knowledge-confidence"), version=2)
        _write_disc(repo, "domain-candidates",
                    stub_executor("", {}, artifact_name="domain-candidates"), version=1)
        # review-summary in review dir
        d = repo / "docs" / "semantic" / "review"
        d.mkdir(parents=True, exist_ok=True)
        write_artifact(repo, "review", "review-summary",
                       stub_executor("", {}, artifact_name="review-summary"))

        # Write snapshot at current state
        write_semantic_snapshot(repo)

        # Now advance only repo-understanding to v4 (skew)
        _write_disc(repo, "repo-understanding",
                    stub_executor("", {}, artifact_name="repo-understanding"), version=4)

        warnings = check_semantic_snapshot(repo)
        assert len(warnings) > 0
        assert any("repo-understanding" in w for w in warnings)

    def test_b_version_skew_blocks_pipeline(self, repo: Path) -> None:
        """Pipeline halts on version skew detection."""
        _seed_all(repo)
        write_semantic_snapshot(repo)

        # Create skew by adding a new version of just one artifact
        _write_disc(repo, "repo-understanding",
                    stub_executor("", {}, artifact_name="repo-understanding"), version=2)

        _write_review(repo, "architect-feedback", "acceptance: true\n")
        result = run_refine(repo, executor=_make_executor())
        assert result.status == "version_skew"


# ===========================================================================
# 4. Prompt/Output Contract Robustness
# ===========================================================================


class TestPromptContract:
    """Malformed host-executor outputs handled correctly."""

    def test_case_a_missing_baseline_section(self) -> None:
        """Missing required heading → parser returns incomplete dict."""
        content = "## Purpose\nSome purpose.\n\n## Concepts\nSome concepts.\n"
        sections = parse_baseline_output(content)
        assert "domains" not in sections
        assert "pipelines" not in sections
        # Validation should catch the missing sections
        for name in ("domains", "pipelines"):
            assert name not in sections

    def test_case_a_missing_section_blocks_baseline_write(self, repo: Path) -> None:
        """Incomplete baseline output → baseline not written."""
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "acceptance: true\n")

        # Executor that produces baseline missing ## Pipelines
        def partial_baseline_executor(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name == "baseline":
                return (
                    "## Purpose\nPrimary Purpose: test\n\n"
                    "## Domains\nDomain Name: test\n\n"
                    "## Concepts\nConcept Name: test\n"
                    # Missing ## Pipelines
                )
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        result = run_refine(repo, executor=partial_baseline_executor)
        # Baseline step should fail validation
        baseline_steps = [s for s in result.steps if s.step_index == 4]
        if baseline_steps:
            assert baseline_steps[0].status == "validation_failed"
        assert not result.baseline_generated

    def test_case_b_reordered_headings_still_parse(self) -> None:
        """Reordered headings are parsed correctly."""
        content = (
            "## Pipelines\nPipeline Name: main\n\n"
            "## Purpose\nPrimary Purpose: test\n\n"
            "## Concepts\nConcept Name: core\n\n"
            "## Domains\nDomain Name: primary\n"
        )
        sections = parse_baseline_output(content)
        assert set(sections.keys()) == {"purpose", "domains", "concepts", "pipelines"}
        assert "Pipeline Name" in sections["pipelines"]
        assert "Primary Purpose" in sections["purpose"]

    def test_case_c_extra_section_ignored(self) -> None:
        """Extra unexpected sections are silently ignored."""
        content = (
            "## Purpose\nPrimary Purpose: test\n\n"
            "## RandomSection\nSome random content.\n\n"
            "## Domains\nDomain Name: test\n\n"
            "## Concepts\nConcept Name: test\n\n"
            "## Pipelines\nPipeline Name: test\n"
        )
        sections = parse_baseline_output(content)
        assert "randomsection" not in sections
        assert set(sections.keys()) == {"purpose", "domains", "concepts", "pipelines"}

    def test_baseline_validation_rejects_empty_section(self) -> None:
        """Empty section content fails validation."""
        errors = validate_baseline_artifact("", "purpose")
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_baseline_validation_requires_keyword(self) -> None:
        """Section missing its required keyword fails."""
        errors = validate_baseline_artifact("Some content without the keyword.", "purpose")
        assert len(errors) > 0
        assert "Primary Purpose" in errors[0]

    def test_duplicate_section_rejected(self) -> None:
        """Duplicate heading causes that section to be omitted from parse result."""
        content = (
            "## Purpose\nPrimary Purpose: first\n\n"
            "## Domains\nDomain Name: test\n\n"
            "## Purpose\nPrimary Purpose: second\n\n"
            "## Concepts\nConcept Name: test\n\n"
            "## Pipelines\nPipeline Name: test\n"
        )
        sections = parse_baseline_output(content)
        assert "purpose" not in sections  # duplicate → removed
        assert "domains" in sections
        assert "concepts" in sections
        assert "pipelines" in sections


# ===========================================================================
# 5. Global Invariant Verification
# ===========================================================================


class TestGlobalInvariants:
    """Core system invariants hold."""

    # --- Invariant 1: Schema alignment ---

    def test_inv1_repo_understanding_sections_match_schema(self) -> None:
        """REPO_UNDERSTANDING_SECTIONS matches repo-understanding.schema.md."""
        expected = ("System Purpose", "Pipelines", "Concepts", "Candidate Domains")
        assert REPO_UNDERSTANDING_SECTIONS == expected

    def test_inv1_knowledge_confidence_sections_match_schema(self) -> None:
        """KNOWLEDGE_CONFIDENCE_SECTIONS matches knowledge-confidence.schema.md."""
        expected = ("Confirmed Knowledge", "Inferred Knowledge", "Uncertain Knowledge")
        assert KNOWLEDGE_CONFIDENCE_SECTIONS == expected

    def test_inv1_baseline_sections_match_schemas(self) -> None:
        """BASELINE_SECTIONS keywords match purpose/domains/concepts/pipelines schemas."""
        assert BASELINE_SECTIONS["purpose"] == "Primary Purpose"
        assert BASELINE_SECTIONS["domains"] == "Domain Name"
        assert BASELINE_SECTIONS["concepts"] == "Concept Name"
        assert BASELINE_SECTIONS["pipelines"] == "Pipeline Name"

    # --- Invariant 2: Semantic state consistency ---

    def test_inv2_staged_patches_prevent_partial_state(self, repo: Path) -> None:
        """Staged write flow prevents partial semantic state."""
        good = stub_executor("", {}, artifact_name="repo-understanding")
        bad = "# kc\n\nNo headings.\n"

        _, _, err1 = stage_artifact(repo, "discovery", "repo-understanding", good,
                                     validate_fn=validate_refined_artifact)
        _, _, err2 = stage_artifact(repo, "discovery", "knowledge-confidence", bad,
                                     validate_fn=validate_refined_artifact)
        assert err1 == []
        assert len(err2) > 0
        # Neither committed
        disc = repo / "docs" / "semantic" / "discovery"
        assert not list(disc.glob("*.md")) if disc.exists() else True

    # --- Invariant 3: Baseline boundary ---

    def test_inv3_get_latest_working_excludes_baseline(self, repo: Path) -> None:
        """get_latest_working_version_path never reads from baseline/."""
        result = get_latest_working_version_path(repo, "baseline", "purpose")
        assert result is None

    def test_inv3_baseline_write_uses_dedicated_function(self, repo: Path) -> None:
        """write_baseline writes to baseline/ directory."""
        p = write_baseline(repo, "purpose", "Primary Purpose: test\n")
        assert "baseline" in str(p)
        assert p.exists()

    # --- Invariant 4: Deterministic gates ---

    def test_inv4_acceptance_requires_exact_field(self) -> None:
        """Acceptance requires exact 'acceptance: true' field."""
        assert _check_acceptance("acceptance: true\n")
        assert _check_acceptance("acceptance: True\n")
        assert not _check_acceptance("I accept this.\n")
        assert not _check_acceptance("acceptance is true\n")
        assert not _check_acceptance("acceptance: false\n")
        assert not _check_acceptance("")

    def test_inv4_validation_is_structural(self) -> None:
        """Validation checks heading structure, not content semantics."""
        # Has correct heading but nonsense content → passes
        content = "## System Purpose\nxyzzy gibberish 12345\n"
        assert validate_refined_artifact(content, "repo-understanding") == []

        # Has meaningful content but wrong heading → fails
        content2 = "## Evidence\nSystem Purpose is to manage data pipelines.\n"
        assert len(validate_refined_artifact(content2, "repo-understanding")) > 0

    # --- Invariant 5: Context boundary ---

    def test_inv5_refine_context_is_artifact_based(self, repo: Path) -> None:
        """Refine context builder reads only artifacts, not raw repo files."""
        _seed_all(repo)
        ctx = context_builder.build_refine_context(repo, "patch", feedback="test feedback")
        # Context keys should be artifact-based
        for key in ctx:
            assert key in ("repo_understanding", "knowledge_confidence", "architect_feedback"), (
                f"Unexpected context key: {key}"
            )

    def test_inv5_baseline_context_is_artifact_based(self, repo: Path) -> None:
        """Baseline context reads only semantic artifacts."""
        _seed_all(repo)
        ctx = context_builder.build_baseline_context(repo)
        allowed = {"repo_understanding", "knowledge_confidence", "domain_candidates", "review_summary"}
        for key in ctx:
            assert key in allowed, f"Unexpected context key: {key}"


# ===========================================================================
# 6. Recovery Behavior
# ===========================================================================


class TestRecoveryBehavior:
    """System recovers safely after failures."""

    def test_rerun_after_failure_succeeds(self, repo: Path) -> None:
        """After a failed refine, a subsequent run with good input succeeds."""
        _seed_all(repo)
        _write_review(repo, "architect-feedback", "Some feedback.\n")

        # First run: bad executor → failure
        def bad_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return f"# {artifact_name}\n\nBroken.\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        r1 = run_refine(repo, executor=bad_exec)
        assert r1.status == "validation_failed"

        # Second run: good executor → success
        r2 = run_refine(repo, executor=_make_executor())
        assert r2.status == "ok"

    def test_valid_prior_artifacts_usable_after_failure(self, repo: Path) -> None:
        """Prior valid artifacts remain readable after pipeline failure."""
        _seed_all(repo)
        ru_v1 = repo / "docs" / "semantic" / "discovery" / "repo-understanding.v1.md"
        original = ru_v1.read_text()

        _write_review(repo, "architect-feedback", "feedback.\n")

        def bad_exec(prompt_text, context, *, artifact_name, sampling_mode="auto"):
            if artifact_name in ("repo-understanding", "knowledge-confidence"):
                return "broken\n"
            return stub_executor(prompt_text, context, artifact_name=artifact_name, sampling_mode=sampling_mode)

        run_refine(repo, executor=bad_exec)

        # v1 still intact and readable
        assert ru_v1.read_text() == original
        latest = get_latest_version_path(repo, "discovery", "repo-understanding")
        assert latest is not None
