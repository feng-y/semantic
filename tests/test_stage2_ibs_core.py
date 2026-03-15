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
from src.ibs_core_validation import validate_ibs_core_artifact, validate_ibs_core_outputs
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
        "no direct `knowledge-confidence` overlay",
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


def test_ibs_core_generator_precedence_is_deterministic() -> None:
    repo_facts = "# repo-facts\n\n## Repository\n- Primary Language: Python\n"
    repo_understanding = "# repo-understanding\n\n## System Purpose\n- Purpose: RU purpose\n"
    domain_candidates = "# domain-candidates\n\n## Candidate Domains\n- Domain Name: D\n- Description: DD\n- Related Pipelines: P\n"
    knowledge_confidence = "# knowledge-confidence\n\n## Confirmed Knowledge\n- Item: known\n"
    review_summary = (
        "# review-summary\n\n"
        "## Pipelines\n- Pipeline Name: Preferred Pipeline\n\n"
        "## Main Pipelines\n- Pipeline Name: Secondary Pipeline\n\n"
        "## Concepts\n- Concept Name: Preferred Concept\n\n"
        "## Core Concepts\n- Concept Name: Secondary Concept\n"
    )

    first = generate_ibs_core(
        repo_facts=repo_facts,
        repo_understanding=repo_understanding,
        domain_candidates=domain_candidates,
        knowledge_confidence=knowledge_confidence,
        review_summary=review_summary,
    )
    second = generate_ibs_core(
        repo_facts=repo_facts,
        repo_understanding=repo_understanding,
        domain_candidates=domain_candidates,
        knowledge_confidence=knowledge_confidence,
        review_summary=review_summary,
    )

    assert first == second
    assert "Pipeline Name: Preferred Pipeline" in first["pipelines"]
    assert "Pipeline Name: Secondary Pipeline" not in first["pipelines"]
    assert "Concept Name: Preferred Concept" in first["concepts"]
    assert "Concept Name: Secondary Concept" not in first["concepts"]


def test_ibs_core_field_level_fact_to_mapping() -> None:
    outputs = generate_ibs_core(
        repo_facts=(
            "# repo-facts\n\n"
            "## Repository\n- Primary Language: Python\n\n"
            "## Entrypoints\n- Name: cli\n"
        ),
        repo_understanding=(
            "# repo-understanding\n\n"
            "## System Purpose\n- Purpose: Canonical purpose from RU\n\n"
            "## Pipelines\n- Pipeline Name: Intake\n- Purpose: Intake purpose\n\n"
            "## Concepts\n- Concept Name: Ledger\n- Description: Ledger concept\n- Role: Core role\n- Used By: Intake\n\n"
            "## Candidate Domains\n- Domain Name: RU Domain\n- Description: RU Description\n- Related Pipelines: Intake\n"
        ),
        domain_candidates=(
            "# domain-candidates\n\n"
            "## Candidate Domains\n- Domain Name: DC Domain\n- Description: DC Description\n- Related Pipelines: Intake\n"
        ),
        knowledge_confidence="# knowledge-confidence\n\n## Confirmed Knowledge\n- Item: known\n",
        review_summary="# review-summary\n\n## System Summary\nFallback summary from RS\n",
    )

    assert "Primary Purpose: Canonical purpose from RU" in outputs["purpose"]
    assert "Fallback summary from RS" not in outputs["purpose"]
    assert "Pipeline Name: Intake" in outputs["pipelines"]
    assert "Purpose: Intake purpose" in outputs["pipelines"]
    assert "Domain Name: DC Domain" in outputs["domains"]
    assert "Description: DC Description" in outputs["domains"]
    assert "Concept Name: Ledger" in outputs["concepts"]


def test_ibs_core_validation_rejects_missing_required_structure() -> None:
    bad_outputs = {
        "purpose": "Primary Purpose: only one line\n",
        "pipelines": "Pipeline Name: only\n",
        "domains": "Domain Name: d\nDescription: desc\nRelated Pipelines:\n",
        "concepts": "Concept Name: c\n",
    }
    errors = validate_ibs_core_outputs(bad_outputs)
    assert errors
    joined = "\n".join(errors)
    assert "Supported Scenarios" in joined
    assert "Non Goals" in joined
    assert "pipelines" in joined.lower()
    assert "Related Pipelines" in joined
    assert "Role" in joined


def test_ibs_core_validation_rejects_empty_artifact() -> None:
    errors = validate_ibs_core_artifact("purpose", "")
    assert errors
    assert "empty" in errors[0].lower()


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
