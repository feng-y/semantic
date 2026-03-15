"""Step 4 — Documentation Alignment tests."""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DOCS = ["README.md", "INSTALL.md", "USER_GUIDE.md", "CHANGELOG.md"]

README_SECTIONS = [
    "What It Does",
    "Quickstart",
    "Installation",
    "Core Commands",
    "Architecture Overview",
    "Documentation",
    "Release Status",
]


class TestDocsStep4:
    @pytest.mark.parametrize("doc", REQUIRED_DOCS)
    def test_doc_exists(self, doc: str) -> None:
        assert (REPO_ROOT / doc).exists(), f"Missing doc: {doc}"

    @pytest.mark.parametrize("doc", REQUIRED_DOCS)
    def test_doc_not_empty(self, doc: str) -> None:
        content = (REPO_ROOT / doc).read_text()
        assert len(content.strip()) > 50, f"Doc too short: {doc}"

    def test_readme_has_required_sections(self) -> None:
        content = (REPO_ROOT / "README.md").read_text()
        for section in README_SECTIONS:
            assert section in content, f"README missing section: {section}"

    def test_readme_mentions_plugin(self) -> None:
        content = (REPO_ROOT / "README.md").read_text()
        assert "Claude Code" in content

    def test_changelog_mentions_version(self) -> None:
        content = (REPO_ROOT / "CHANGELOG.md").read_text()
        assert "1.0.0" in content
