"""Step 7 hardening verification tests.

Covers:
  1. Artifact atomicity — staged patches fail atomically
  2. Schema alignment — acceptance evaluator uses schema-defined headings
  3. Stub alignment — fake_executors output passes validation + acceptance
  4. Baseline parsing — already strict (smoke test)
  5. Checkpoint metadata — feedback_hash present
  6. End-to-end refine with acceptance → baseline generated
  7. Discovery/refine validation consistency
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import pytest

# Ensure src is importable
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import artifact_writer
from src.refine_executor import (
    KNOWLEDGE_CONFIDENCE_SECTIONS,
    REPO_UNDERSTANDING_SECTIONS,
    _has_any_section_heading,
    evaluate_acceptance,
    parse_baseline_output,
    run_refine,
    validate_refined_artifact,
)
from src.discovery_executor import validate_artifact_content
from tests.fake_executors import stub_executor


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """Create a minimal repo scaffold with prompts, skills, and manifest."""
    # manifest
    (tmp_path / "manifest.yaml").write_text(
        "name: semantic-harness\nversion: 1.0.0\ntarget: claude-code\n"
        "skills:\n"
        "  init: skills/semantic-init.skill\n"
        "  discover: skills/semantic-discover.skill\n"
        "  refine: skills/semantic-refine.skill\n"
    )
    # skills
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "semantic-init.skill").write_text(
        "name: semantic-init\npurpose: workspace initialization\n"
    )
    (skills_dir / "semantic-discover.skill").write_text(
        "name: semantic-discover\npurpose: discovery\nsteps: []\n"
    )
    (skills_dir / "semantic-refine.skill").write_text(
        "name: semantic-refine\npurpose: refinement\n"
        "steps:\n"
        "  - run: prompts/refine/semantic-refine.patch.prompt\n"
        "  - run: prompts/refine/semantic-change-log.prompt\n"
        "  - run: prompts/validation/validate-artifact.prompt\n"
        "  - apply: protocols/artifact-versioning.md\n"
        "  - if: architect acceptance detected\n"
        "    run: prompts/refine/baseline-synthesis.prompt\n"
    )

    # prompts
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


# ---- helpers ----

def _write_discovery_artifact(repo: Path, name: str, content: str, version: int = 1) -> Path:
    """Write a versioned discovery artifact."""
    d = repo / "docs" / "fact" / "discovery"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.v{version}.md"
    p.write_text(content)
    return p


def _write_review_artifact(repo: Path, name: str, content: str) -> Path:
    d = repo / "docs" / "fact" / "review"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{name}.md"
    p.write_text(content)
    return p


def _write_feedback(repo: Path, content: str) -> Path:
    return _write_review_artifact(repo, "architect-feedback", content)


def _make_executor(artifact_overrides: dict[str, str] | None = None):
    """Return a fake executor that delegates to stub_executor with optional overrides."""
    overrides = artifact_overrides or {}

    def executor(
        prompt_text: str,
        context: dict[str, str],
        *,
        artifact_name: str,
        sampling_mode: str = "auto",
    ) -> str:
        if artifact_name in overrides:
            return overrides[artifact_name]
        return stub_executor(
            prompt_text, context,
            artifact_name=artifact_name,
            sampling_mode=sampling_mode,
        )

    return executor


def _seed_discovery_artifacts(repo: Path) -> None:
    """Write all discovery artifacts needed for refine preconditions."""
    _write_discovery_artifact(
        repo, "repo-understanding",
        stub_executor("", {}, artifact_name="repo-understanding"),
    )
    _write_discovery_artifact(
        repo, "knowledge-confidence",
        stub_executor("", {}, artifact_name="knowledge-confidence"),
    )
    _write_discovery_artifact(
        repo, "domain-candidates",
        stub_executor("", {}, artifact_name="domain-candidates"),
    )
    _write_review_artifact(
        repo, "review-summary",
        stub_executor("", {}, artifact_name="review-summary"),
    )


# ===========================================================================
# 1. Artifact Atomicity
# ===========================================================================


class TestArtifactAtomicity:
    """Staged patches fail atomically — neither artifact written on partial failure."""

    def test_both_pass_both_written(self, repo: Path) -> None:
        good_ru = stub_executor("", {}, artifact_name="repo-understanding")
        good_kc = stub_executor("", {}, artifact_name="knowledge-confidence")

        path_ru, content_ru, err_ru = artifact_writer.stage_artifact(
            repo, "discovery", "repo-understanding", good_ru,
            validate_fn=validate_refined_artifact,
        )
        path_kc, content_kc, err_kc = artifact_writer.stage_artifact(
            repo, "discovery", "knowledge-confidence", good_kc,
            validate_fn=validate_refined_artifact,
        )

        assert err_ru == []
        assert err_kc == []

        written = artifact_writer.commit_staged([(path_ru, content_ru), (path_kc, content_kc)])
        assert len(written) == 2
        for p in written:
            assert p.exists()

    def test_second_fails_neither_written(self, repo: Path) -> None:
        good_ru = stub_executor("", {}, artifact_name="repo-understanding")
        bad_kc = "# knowledge-confidence\n\nNo schema headings here.\n"

        path_ru, content_ru, err_ru = artifact_writer.stage_artifact(
            repo, "discovery", "repo-understanding", good_ru,
            validate_fn=validate_refined_artifact,
        )
        _path_kc, _content_kc, err_kc = artifact_writer.stage_artifact(
            repo, "discovery", "knowledge-confidence", bad_kc,
            validate_fn=validate_refined_artifact,
        )

        assert err_ru == []
        assert len(err_kc) > 0  # validation failed

        # Do NOT call commit_staged — simulating the staged flow in run_refine
        # Verify neither file exists on disk
        disc = repo / "docs" / "fact" / "discovery"
        ru_files = list(disc.glob("repo-understanding.v*.md")) if disc.exists() else []
        kc_files = list(disc.glob("knowledge-confidence.v*.md")) if disc.exists() else []
        assert ru_files == []
        assert kc_files == []

    def test_first_fails_neither_written(self, repo: Path) -> None:
        bad_ru = "# repo-understanding\n\nEmpty, no schema sections.\n"
        good_kc = stub_executor("", {}, artifact_name="knowledge-confidence")

        _path_ru, _content_ru, err_ru = artifact_writer.stage_artifact(
            repo, "discovery", "repo-understanding", bad_ru,
            validate_fn=validate_refined_artifact,
        )

        assert len(err_ru) > 0  # first failed, don't even stage second

        disc = repo / "docs" / "fact" / "discovery"
        assert not list(disc.glob("*.md")) if disc.exists() else True


# ===========================================================================
# 2. Schema Alignment — acceptance evaluator
# ===========================================================================


class TestSchemaAlignment:
    """Acceptance gates use schema-defined headings, not old-style ones."""

    def test_schema_headings_pass_gates(self, repo: Path) -> None:
        _seed_discovery_artifacts(repo)
        feedback = "acceptance: true\n\nLooks good.\n"
        _write_feedback(repo, feedback)

        passed, failures = evaluate_acceptance(repo, feedback)
        assert passed, f"Expected pass, got failures: {failures}"

    def test_old_style_headings_fail_gates(self, repo: Path) -> None:
        """Old-style ## Evidence / ## Confidence headings should NOT pass."""
        old_ru = "# repo-understanding\n\n## Evidence\nSome evidence\n\n## Confidence\nHigh\n"
        old_kc = "# knowledge-confidence\n\n## Evidence\nSome evidence\n\n## Confidence\nHigh\n"

        _write_discovery_artifact(repo, "repo-understanding", old_ru)
        _write_discovery_artifact(repo, "knowledge-confidence", old_kc)
        _write_discovery_artifact(
            repo, "domain-candidates",
            stub_executor("", {}, artifact_name="domain-candidates"),
        )

        feedback = "acceptance: true\n"
        passed, failures = evaluate_acceptance(repo, feedback)
        assert not passed
        assert any("repo-understanding" in f for f in failures)
        assert any("knowledge-confidence" in f for f in failures)

    def test_validate_refined_artifact_schema_sections(self) -> None:
        """validate_refined_artifact checks for schema-defined sections."""
        good_ru = "# repo-understanding\n\n## System Purpose\nA system.\n"
        assert validate_refined_artifact(good_ru, "repo-understanding") == []

        good_kc = "# kc\n\n## Confirmed Knowledge\nSomething confirmed.\n"
        assert validate_refined_artifact(good_kc, "knowledge-confidence") == []

        bad_ru = "# repo-understanding\n\n## Evidence\nOld style.\n"
        assert len(validate_refined_artifact(bad_ru, "repo-understanding")) > 0

        bad_kc = "# kc\n\n## Confidence\nOld style.\n"
        assert len(validate_refined_artifact(bad_kc, "knowledge-confidence")) > 0


# ===========================================================================
# 3. Stub Alignment — fake_executors pass validation + acceptance
# ===========================================================================


class TestStubAlignment:
    """stub_executor output passes both validate_refined_artifact and evaluate_acceptance."""

    def test_stub_repo_understanding_passes_validation(self) -> None:
        content = stub_executor("", {}, artifact_name="repo-understanding")
        assert validate_refined_artifact(content, "repo-understanding") == []

    def test_stub_knowledge_confidence_passes_validation(self) -> None:
        content = stub_executor("", {}, artifact_name="knowledge-confidence")
        assert validate_refined_artifact(content, "knowledge-confidence") == []

    def test_stub_repo_understanding_passes_discovery_validation(self) -> None:
        content = stub_executor("", {}, artifact_name="repo-understanding")
        assert validate_artifact_content(content, "repo-understanding") == []

    def test_stub_knowledge_confidence_passes_discovery_validation(self) -> None:
        content = stub_executor("", {}, artifact_name="knowledge-confidence")
        assert validate_artifact_content(content, "knowledge-confidence") == []

    def test_stubs_pass_acceptance_gates(self, repo: Path) -> None:
        _seed_discovery_artifacts(repo)
        feedback = "acceptance: true\n"
        passed, failures = evaluate_acceptance(repo, feedback)
        assert passed, f"Stub artifacts failed acceptance: {failures}"


# ===========================================================================
# 4. Baseline Parsing (smoke test — already strict)
# ===========================================================================


class TestBaselineParsing:
    """parse_baseline_output rejects missing/malformed sections."""

    def test_valid_output_parses_all_sections(self) -> None:
        content = stub_executor("", {}, artifact_name="baseline")
        sections = parse_baseline_output(content)
        assert set(sections.keys()) == {"purpose", "domains", "concepts", "pipelines"}

    def test_missing_section_not_in_result(self) -> None:
        content = "## Purpose\nSome purpose\n\n## Domains\nSome domains\n"
        sections = parse_baseline_output(content)
        assert "purpose" in sections
        assert "domains" in sections
        assert "concepts" not in sections
        assert "pipelines" not in sections

    def test_empty_content_returns_empty(self) -> None:
        assert parse_baseline_output("") == {}


# ===========================================================================
# 5. Checkpoint Metadata — feedback_hash present
# ===========================================================================


class TestCheckpointMetadata:
    """checkpoint.json contains feedback_hash field after baseline synthesis."""

    def test_e2e_checkpoint_has_feedback_hash(self, repo: Path) -> None:
        _seed_discovery_artifacts(repo)
        feedback = "acceptance: true\n\nAll looks good.\n"
        _write_feedback(repo, feedback)

        executor = _make_executor()
        result = run_refine(repo, executor=executor)

        assert result.baseline_generated, (
            f"Baseline not generated. status={result.status}, "
            f"steps={[(s.status, s.errors) for s in result.steps]}"
        )

        checkpoint_path = repo / "docs" / "fact" / "baseline" / "checkpoint.json"
        assert checkpoint_path.exists(), "checkpoint.json not written"

        checkpoint = json.loads(checkpoint_path.read_text())
        assert "feedback_hash" in checkpoint
        assert isinstance(checkpoint["feedback_hash"], str)
        assert len(checkpoint["feedback_hash"]) == 16  # sha256[:16]

    def test_checkpoint_has_required_fields(self, repo: Path) -> None:
        _seed_discovery_artifacts(repo)
        feedback = "acceptance: true\n"
        _write_feedback(repo, feedback)

        result = run_refine(repo, executor=_make_executor())
        assert result.baseline_generated

        checkpoint = json.loads(
            (repo / "docs" / "fact" / "baseline" / "checkpoint.json").read_text()
        )
        assert "timestamp" in checkpoint
        assert "source_versions" in checkpoint
        assert "baseline_files" in checkpoint
        assert "feedback_hash" in checkpoint


# ===========================================================================
# 6. End-to-end refine with acceptance → baseline generated
# ===========================================================================


class TestE2ERefineBaseline:
    """Full refine cycle: patches + changelog + validation + baseline."""

    def test_acceptance_produces_baseline_files(self, repo: Path) -> None:
        _seed_discovery_artifacts(repo)
        feedback = "acceptance: true\n\nShip it.\n"
        _write_feedback(repo, feedback)

        result = run_refine(repo, executor=_make_executor())

        assert result.status == "ok"
        assert result.acceptance_detected is True
        assert result.baseline_generated is True

        baseline_dir = repo / "docs" / "fact" / "baseline"
        assert baseline_dir.exists()
        baseline_files = {f.name for f in baseline_dir.iterdir() if f.suffix == ".md"}
        assert baseline_files == {"purpose.md", "domains.md", "concepts.md", "pipelines.md"}

    def test_no_acceptance_skips_baseline(self, repo: Path) -> None:
        _seed_discovery_artifacts(repo)
        feedback = "Some feedback without acceptance field.\n"
        _write_feedback(repo, feedback)

        result = run_refine(repo, executor=_make_executor())

        assert result.status == "ok"
        assert result.acceptance_detected is False
        assert result.baseline_generated is False

        baseline_dir = repo / "docs" / "fact" / "baseline"
        md_files = list(baseline_dir.glob("*.md")) if baseline_dir.exists() else []
        assert md_files == []


# ===========================================================================
# 7. Discovery/refine validation consistency
# ===========================================================================


class TestValidationConsistency:
    """validate_artifact_content and validate_refined_artifact accept the same formats."""

    @pytest.mark.parametrize("name", ["repo-understanding", "knowledge-confidence"])
    def test_same_content_same_result(self, name: str) -> None:
        content = stub_executor("", {}, artifact_name=name)
        discovery_errors = validate_artifact_content(content, name)
        refine_errors = validate_refined_artifact(content, name)
        assert discovery_errors == refine_errors == []

    @pytest.mark.parametrize("name", ["repo-understanding", "knowledge-confidence"])
    def test_bad_content_both_reject(self, name: str) -> None:
        bad = f"# {name}\n\nNo schema headings at all.\n"
        discovery_errors = validate_artifact_content(bad, name)
        refine_errors = validate_refined_artifact(bad, name)
        assert len(discovery_errors) > 0
        assert len(refine_errors) > 0

    def test_has_any_section_heading_helper(self) -> None:
        content = "# Title\n\n## System Purpose\nSomething.\n"
        assert _has_any_section_heading(content, REPO_UNDERSTANDING_SECTIONS)
        assert not _has_any_section_heading(content, KNOWLEDGE_CONFIDENCE_SECTIONS)

    def test_discovery_validates_all_artifact_types(self) -> None:
        """All stub artifacts pass discovery validation."""
        for name in ("repo-facts", "repo-understanding", "knowledge-confidence",
                      "domain-candidates", "review-summary"):
            content = stub_executor("", {}, artifact_name=name)
            errors = validate_artifact_content(content, name)
            assert errors == [], f"{name} failed discovery validation: {errors}"
