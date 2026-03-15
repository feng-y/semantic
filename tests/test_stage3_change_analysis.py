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
    assert "IBS Core" in text
    assert "change-analysis" in text


def test_change_analysis_template_passes_validator() -> None:
    path = REPO_ROOT / "docs" / "semantic" / "templates" / "change-analysis.template.md"
    assert path.exists(), "missing change-analysis template"
    content = path.read_text()
    errors = validate_change_analysis(content)
    assert errors == [], f"template should pass validation, got: {errors}"


def test_generator_maps_ibs_core_fields() -> None:
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
    assert "## Change Intent" in content
    assert "Preserve semantic model integrity" in content
    assert "Pipeline: Intake" in content
    assert "Semantic Core" in content
    assert "Semantic Artifact" in content
    assert "Low confidence marker" in content


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


def test_refine_generates_change_analysis_from_ibs_core(semantic_root: Path) -> None:
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

