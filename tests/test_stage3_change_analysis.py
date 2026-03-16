"""Stage 3 change-analysis tests."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.change_analysis_generator import generate_change_analysis
from src.change_analysis_validation import validate_change_analysis
from src.discovery_executor import run_discovery
from src.refine_executor import run_refine
from tests.fake_executors import stub_executor


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def semantic_root(tmp_path: Path) -> Path:
    """Create runnable root for Stage 3 integration tests."""
    root = tmp_path
    shutil.copytree(REPO_ROOT / "skills", root / "skills")
    shutil.copytree(REPO_ROOT / "prompts", root / "prompts")
    shutil.copytree(REPO_ROOT / "protocols", root / "protocols")
    shutil.copytree(
        REPO_ROOT / "docs" / "semantic" / "schemas",
        root / "docs" / "semantic" / "schemas",
        dirs_exist_ok=True,
    )
    for d in ("discovery", "review", "baseline"):
        (root / "docs" / "semantic" / d).mkdir(parents=True, exist_ok=True)

    (root / "manifest.yaml").write_text(
        "name: semantic-harness\n"
        "version: 0.0.1\n"
        "target: claude-code\n\n"
        "skills:\n"
        "  discovery: skills/semantic-discover.skill\n"
        "  refinement: skills/semantic-refine.skill\n"
        "  init: skills/semantic-init.skill\n"
        "  discover: skills/semantic-discover.skill\n"
        "  review: skills/semantic-review.skill\n"
        "  refine: skills/semantic-refine.skill\n"
        "  baseline: skills/semantic-baseline.skill\n"
        "  status: skills/semantic-status.skill\n"
        "  reset: skills/semantic-reset.skill\n"
    )
    return root


def test_stage3_mapping_doc_exists() -> None:
    path = REPO_ROOT / "docs" / "review" / "stage3_change_analysis_mapping.md"
    assert path.exists(), "missing stage3 mapping doc"
    text = path.read_text()
    for key in (
        "purpose.md",
        "pipelines.md",
        "domains.md",
        "concepts.md",
        "Change Intent",
        "Affected Pipelines",
        "Affected Domains and Concepts",
        "Impact and Risks",
        "Suggested Next Changes",
    ):
        assert key in text


def test_stage3_design_doc_exists() -> None:
    path = REPO_ROOT / "docs" / "semantic-design" / "012-change-analysis-output-model.md"
    assert path.exists(), "missing 012 change-analysis design doc"
    text = path.read_text()
    assert "change-analysis" in text


def test_change_analysis_template_passes_validator() -> None:
    path = REPO_ROOT / "docs" / "semantic" / "templates" / "change-analysis.template.md"
    assert path.exists(), "missing change-analysis template"
    content = path.read_text()
    errors = validate_change_analysis(content)
    assert errors == [], f"template should pass validation, got: {errors}"


def test_generator_maps_baseline_fields() -> None:
    content = generate_change_analysis(
        purpose=(
            "Primary Purpose: Preserve semantic model integrity\n"
            "Supported Scenarios:\n"
            "- Analyze architecture changes\n"
            "Non Goals:\n"
            "- No implementation planning\n"
        ),
        pipelines=(
            "Pipeline Name: Intake\n"
            "Purpose: Collect facts\n"
            "Flow: A->B\n"
            "Inputs: repo\n"
            "Outputs: facts\n"
            "Concepts: Semantic Artifact\n"
            "Evidence: src/\n"
            "Confidence: low\n"
        ),
        domains=(
            "Domain Name: Semantic Core\n"
            "Description: core boundary\n"
            "Related Pipelines:\n"
            "- Intake\n"
        ),
        concepts=(
            "Concept Name: Semantic Artifact\n"
            "Description: reusable semantic unit\n"
            "Role: core\n"
            "Used By: Intake\n"
            "Evidence: docs/\n"
            "Confidence: medium\n"
        ),
    )
    change_intent = _section_body(content, "Change Intent")
    affected_pipelines = _section_body(content, "Affected Pipelines")
    affected_domains_concepts = _section_body(content, "Affected Domains and Concepts")
    impact_risks = _section_body(content, "Impact and Risks")
    suggested_next = _section_body(content, "Suggested Next Changes")

    assert "Preserve semantic model integrity" in change_intent
    assert "No implementation planning" in change_intent

    assert "- Pipeline: Intake" in affected_pipelines
    assert "Flow: A->B" not in affected_pipelines

    assert "- Domains:" in affected_domains_concepts
    assert "- Concepts:" in affected_domains_concepts
    assert "Semantic Core" in affected_domains_concepts
    assert "Semantic Artifact" in affected_domains_concepts

    assert "Primary impact surface includes pipelines: Intake" in impact_risks
    assert "Low confidence marker" in impact_risks

    assert "Start with pipeline updates in: Intake" in suggested_next
    assert "Re-run semantic refine after change-analysis review feedback." in suggested_next


def test_generator_is_repeatable_for_same_baseline_input() -> None:
    inputs = {
        "purpose": (
            "Primary Purpose: Keep semantic outputs stable\n"
            "Supported Scenarios:\n"
            "- Review semantic changes\n"
            "Non Goals:\n"
            "- No runtime redesign\n"
        ),
        "pipelines": (
            "Pipeline Name: Discover\n"
            "Pipeline Name: Refine\n"
            "Purpose: Extract and patch facts\n"
            "Flow: discover->refine\n"
            "Confidence: low\n"
        ),
        "domains": (
            "Domain Name: Discovery\n"
            "Domain Name: Refinement\n"
        ),
        "concepts": (
            "Concept Name: Fact Artifact\n"
            "Concept Name: Baseline Artifact\n"
            "Confidence: low\n"
        ),
    }
    first = generate_change_analysis(**inputs)
    second = generate_change_analysis(**inputs)

    assert first == second
    assert first.find("- Pipeline: Discover") < first.find("- Pipeline: Refine")


def test_validator_rejects_missing_required_structure() -> None:
    bad = (
        "# change-analysis\n\n"
        "## Change Intent\n- Intent: x\n\n"
        "## Affected Pipelines\n- not pipeline label\n\n"
        "## Impact and Risks\n- Impact: x\n\n"
        "## Suggested Next Changes\n- next\n"
    )
    errors = validate_change_analysis(bad)
    assert errors
    joined = "\n".join(errors)
    assert "Affected Domains and Concepts" in joined
    assert "Affected Pipelines" in joined


def test_refine_generates_change_analysis_from_baseline(semantic_root: Path) -> None:
    d = run_discovery(semantic_root, executor=stub_executor, sampling_mode="auto")
    assert d.status == "ok"

    feedback = semantic_root / "docs" / "semantic" / "review" / "architect-feedback.md"
    feedback.write_text("acceptance: true\n")

    r = run_refine(semantic_root, executor=stub_executor)
    assert r.status == "ok"
    assert r.baseline_generated

    ca = semantic_root / "docs" / "semantic" / "review" / "change-analysis.v1.md"
    assert ca.exists(), "expected change-analysis artifact in review/"
    ca_text = ca.read_text()
    assert validate_change_analysis(ca_text) == []

    purpose_text = (semantic_root / "docs" / "semantic" / "baseline" / "purpose.md").read_text()
    m = re.search(r"Primary Purpose:\s*(.+)$", purpose_text, re.MULTILINE)
    assert m is not None
    assert m.group(1).strip() in ca_text


def test_refine_stage3_failure_after_baseline_is_explicit(
    semantic_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    d = run_discovery(semantic_root, executor=stub_executor, sampling_mode="auto")
    assert d.status == "ok"

    feedback = semantic_root / "docs" / "semantic" / "review" / "architect-feedback.md"
    feedback.write_text("acceptance: true\n")

    import src.refine_executor as refine_executor_module

    def _invalid_change_analysis(**_: str) -> str:
        return "# change-analysis\n\n## Change Intent\n- Intent: incomplete\n"

    monkeypatch.setattr(
        refine_executor_module,
        "generate_change_analysis",
        _invalid_change_analysis,
    )

    r = run_refine(semantic_root, executor=stub_executor)
    assert r.status == "validation_failed"
    assert r.baseline_generated is True

    stage4 = [s for s in r.steps if s.step_index == 4]
    stage5 = [s for s in r.steps if s.step_index == 5]
    assert stage4 and stage4[0].status == "ok"
    assert stage5 and stage5[0].status == "validation_failed"

    baseline_dir = semantic_root / "docs" / "semantic" / "baseline"
    for name in ("purpose", "pipelines", "domains", "concepts"):
        assert (baseline_dir / f"{name}.md").exists()

    assert not (semantic_root / "docs" / "semantic" / "review" / "change-analysis.v1.md").exists()
    assert not (baseline_dir / "checkpoint.json").exists()


def _section_body(content: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(content)
    assert match is not None, f"missing section: {heading}"
    return match.group(1).strip()
