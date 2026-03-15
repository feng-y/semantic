"""Stage 2 IBS Core tests.

Covers mapping docs, IBS core templates, synthesis logic, and refine integration.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import artifact_validation
from src.discovery_executor import run_discovery
from src.ibs_core_generator import generate_ibs_core
from src.ibs_core_validation import validate_ibs_core_outputs
from src.refine_executor import run_refine
from tests.fake_executors import stub_executor


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def semantic_root(tmp_path: Path) -> Path:
    """Create a runnable semantic harness root for stage2 integration tests."""
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


def test_stage2_mapping_spec_exists() -> None:
    path = REPO_ROOT / "docs" / "review" / "stage2_ibs_core_mapping.md"
    assert path.exists(), "missing stage2 mapping spec"
    content = path.read_text()
    for key in (
        "purpose",
        "pipelines",
        "domains",
        "concepts",
        "repo-understanding",
        "domain-candidates",
        "IBS Core File Contracts",
        "Primary Purpose",
        "Pipeline Name",
        "Domain Name",
        "Concept Name",
    ):
        assert key in content


def test_ibs_core_templates_exist_and_match_baseline_contract() -> None:
    template_dir = REPO_ROOT / "docs" / "semantic" / "templates"
    templates = {
        "purpose": "purpose.template.md",
        "pipelines": "pipelines.template.md",
        "domains": "domains.template.md",
        "concepts": "concepts.template.md",
    }
    for artifact, filename in templates.items():
        path = template_dir / filename
        assert path.exists(), f"missing IBS template: {filename}"
        content = path.read_text()
        assert content.strip(), f"empty IBS template: {filename}"
        errors = artifact_validation.validate_baseline_files({artifact: content})
        assert errors == [], f"{filename} failed baseline keyword contract: {errors}"


def test_ibs_core_generator_outputs_validate() -> None:
    outputs = generate_ibs_core(
        repo_facts=stub_executor("", {}, artifact_name="repo-facts"),
        repo_understanding=stub_executor("", {}, artifact_name="repo-understanding"),
        domain_candidates=stub_executor("", {}, artifact_name="domain-candidates"),
        knowledge_confidence=stub_executor("", {}, artifact_name="knowledge-confidence"),
        review_summary=stub_executor("", {}, artifact_name="review-summary"),
    )
    assert set(outputs.keys()) == {"purpose", "pipelines", "domains", "concepts"}
    assert validate_ibs_core_outputs(outputs) == []
    for content in outputs.values():
        assert content.strip()


def test_refine_writes_ibs_core_baseline(semantic_root: Path) -> None:
    discovery = run_discovery(semantic_root, executor=stub_executor, sampling_mode="auto")
    assert discovery.status == "ok"

    feedback = semantic_root / "docs" / "semantic" / "review" / "architect-feedback.md"
    feedback.write_text("acceptance: true\n")

    result = run_refine(semantic_root, executor=stub_executor)
    assert result.status == "ok"
    assert result.baseline_generated

    baseline_dir = semantic_root / "docs" / "semantic" / "baseline"
    purpose = (baseline_dir / "purpose.md").read_text()
    pipelines = (baseline_dir / "pipelines.md").read_text()
    domains = (baseline_dir / "domains.md").read_text()
    concepts = (baseline_dir / "concepts.md").read_text()

    assert "Primary Purpose:" in purpose
    assert "Pipeline Name:" in pipelines
    assert "Domain Name:" in domains
    assert "Concept Name:" in concepts
