"""Stage 1 FACT foundation tests.

Focuses on FACT-layer artifact contracts and generation stability:
- schemas
- templates
- validators
- discovery generation flow
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import artifact_writer, state_inspector
from src.discovery_executor import run_discovery, validate_artifact_content
from tests.fake_executors import stub_executor

REPO_ROOT = Path(__file__).resolve().parent.parent

FACT_ARTIFACTS = [
    ("discovery", "repo-facts"),
    ("discovery", "repo-understanding"),
    ("discovery", "knowledge-confidence"),
    ("discovery", "domain-candidates"),
    ("review", "review-summary"),
]

FACT_SCHEMAS = [
    "repo-facts.schema.md",
    "repo-understanding.schema.md",
    "knowledge-confidence.schema.md",
    "domain-candidates.schema.md",
    "review-summary.schema.md",
]

FACT_TEMPLATES = [
    ("repo-facts", "repo-facts.template.md"),
    ("repo-understanding", "repo-understanding.template.md"),
    ("knowledge-confidence", "knowledge-confidence.template.md"),
    ("domain-candidates", "domain-candidates.template.md"),
    ("review-summary", "review-summary.template.md"),
]


@pytest.fixture()
def semantic_root(tmp_path: Path) -> Path:
    """Create a runnable semantic harness root for discovery tests."""
    root = tmp_path
    shutil.copytree(REPO_ROOT / "skills", root / "skills")
    shutil.copytree(REPO_ROOT / "prompts", root / "prompts")
    shutil.copytree(REPO_ROOT / "protocols", root / "protocols")
    shutil.copytree(REPO_ROOT / ".claude-plugin", root / ".claude-plugin")
    shutil.copytree(
        REPO_ROOT / "docs" / "fact" / "schemas",
        root / "docs" / "fact" / "schemas",
        dirs_exist_ok=True,
    )

    for d in ("discovery", "review", "baseline"):
        (root / "docs" / "fact" / d).mkdir(parents=True, exist_ok=True)

    # Keep schema files available in the temp root for contract completeness.
    shutil.copytree(REPO_ROOT / "docs" / "fact" / "schemas", root / "docs" / "fact" / "schemas", dirs_exist_ok=True)
    return root


def test_fact_schema_files_exist() -> None:
    schema_dir = REPO_ROOT / "docs" / "fact" / "schemas"
    for schema in FACT_SCHEMAS:
        path = schema_dir / schema
        assert path.exists(), f"missing FACT schema: {schema}"
        assert path.read_text().strip(), f"empty FACT schema: {schema}"


def test_fact_template_files_exist() -> None:
    template_dir = REPO_ROOT / "docs" / "fact" / "templates"
    for _artifact, template in FACT_TEMPLATES:
        path = template_dir / template
        assert path.exists(), f"missing FACT template: {template}"
        assert path.read_text().strip(), f"empty FACT template: {template}"


def test_fact_templates_pass_validators() -> None:
    template_dir = REPO_ROOT / "docs" / "fact" / "templates"
    for artifact, template in FACT_TEMPLATES:
        content = (template_dir / template).read_text()
        errors = validate_artifact_content(content, artifact)
        assert errors == [], f"{template} failed validation: {errors}"


def test_domain_candidates_prompt_declares_schema_contract() -> None:
    prompt = (REPO_ROOT / "prompts" / "discover" / "domain-candidates.prompt").read_text()
    assert "docs/fact/schemas/domain-candidates.schema.md" in prompt


def test_discovery_generates_all_fact_artifacts(semantic_root: Path) -> None:
    result = run_discovery(semantic_root, executor=stub_executor, sampling_mode="auto")
    assert result.status == "ok", f"discovery failed: {result.status}"

    sampling_report = semantic_root / "docs" / "fact" / "discovery" / "sampling-report.md"
    assert sampling_report.exists()
    assert sampling_report.read_text().strip()

    for category, name in FACT_ARTIFACTS:
        latest = artifact_writer.get_latest_version_path(semantic_root, category, name)
        assert latest is not None, f"missing generated artifact: {category}/{name}"
        content = latest.read_text()
        errors = validate_artifact_content(content, name)
        assert errors == [], f"generated artifact invalid: {name}: {errors}"

    state = state_inspector.inspect(semantic_root)
    assert state.has_discovery_artifacts
    assert state.has_review_summary


def test_discovery_generation_is_repeatable(semantic_root: Path) -> None:
    first = run_discovery(semantic_root, executor=stub_executor, sampling_mode="auto")
    second = run_discovery(semantic_root, executor=stub_executor, sampling_mode="auto")

    assert first.status == "ok"
    assert second.status == "ok"

    # All FACT artifacts should have at least 2 versions after two successful runs.
    for category, name in FACT_ARTIFACTS:
        versions = []
        base = semantic_root / "docs" / "fact" / category
        for p in base.glob(f"{name}.v*.md"):
            ver = int(p.stem.split(".v")[-1])
            versions.append(ver)
        versions = sorted(versions)
        assert len(versions) >= 2, f"expected multiple versions for {name}, got {versions}"
        assert versions[-1] >= 2, f"latest version did not advance for {name}: {versions}"
