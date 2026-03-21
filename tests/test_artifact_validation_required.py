"""Comprehensive tests for required/optional validation logic.

Tests the AND/OR logic for section validation and ensures proper error reporting
for missing required sections.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.artifact_validation import (
    REPO_FACTS_REQUIRED,
    REPO_UNDERSTANDING_REQUIRED,
    _has_any_optional_section,
    _has_required_sections,
    validate_repo_facts,
    validate_repo_understanding,
)


class TestHasRequiredSections:
    """Test _has_required_sections (AND logic)."""

    def test_all_sections_present(self) -> None:
        """All required sections present should return True."""
        content = "## Section1\n## Section2\n## Section3"
        assert _has_required_sections(content, ("Section1", "Section2", "Section3"))

    def test_one_section_missing(self) -> None:
        """Missing one required section should return False."""
        content = "## Section1\n## Section3"
        assert not _has_required_sections(content, ("Section1", "Section2", "Section3"))

    def test_multiple_sections_missing(self) -> None:
        """Missing multiple required sections should return False."""
        content = "## Section1"
        assert not _has_required_sections(content, ("Section1", "Section2", "Section3"))

    def test_all_sections_missing(self) -> None:
        """Missing all required sections should return False."""
        content = "## Other\n## Unrelated"
        assert not _has_required_sections(content, ("Section1", "Section2", "Section3"))

    def test_empty_content(self) -> None:
        """Empty content should return False."""
        assert not _has_required_sections("", ("Section1",))

    def test_case_insensitive_matching(self) -> None:
        """Section matching should be case-insensitive."""
        content = "## section1\n## SECTION2\n## SeCtion3"
        assert _has_required_sections(content, ("Section1", "Section2", "Section3"))

    def test_sections_with_extra_content(self) -> None:
        """Sections with content after heading should match."""
        content = """## Section1
Some content here

## Section2
More content

## Section3
Final content
"""
        assert _has_required_sections(content, ("Section1", "Section2", "Section3"))


class TestHasAnyOptionalSection:
    """Test _has_any_optional_section (OR logic)."""

    def test_one_section_present(self) -> None:
        """Having one optional section should return True."""
        content = "## Section2"
        assert _has_any_optional_section(content, ("Section1", "Section2", "Section3"))

    def test_multiple_sections_present(self) -> None:
        """Having multiple optional sections should return True."""
        content = "## Section1\n## Section3"
        assert _has_any_optional_section(content, ("Section1", "Section2", "Section3"))

    def test_all_sections_present(self) -> None:
        """Having all optional sections should return True."""
        content = "## Section1\n## Section2\n## Section3"
        assert _has_any_optional_section(content, ("Section1", "Section2", "Section3"))

    def test_no_sections_present(self) -> None:
        """Having no optional sections should return False."""
        content = "## Other"
        assert not _has_any_optional_section(content, ("Section1", "Section2", "Section3"))

    def test_empty_content(self) -> None:
        """Empty content should return False."""
        assert not _has_any_optional_section("", ("Section1",))

    def test_case_insensitive_matching(self) -> None:
        """Section matching should be case-insensitive."""
        content = "## SECTION2"
        assert _has_any_optional_section(content, ("Section1", "Section2", "Section3"))


class TestRepoFactsValidation:
    """Test repo-facts validation with all 5 required sections."""

    def test_all_five_sections_present_passes(self) -> None:
        """All 5 required sections present should pass."""
        content = """# Repo Facts

## Repository
Repository info

## Modules
Module info

## Entrypoints
Entry info

## Core Entities
Entity info

## Configuration
Config info
"""
        errors = validate_repo_facts(content)
        assert errors == []

    def test_missing_one_section_fails(self) -> None:
        """Missing one required section should fail."""
        content = """# Repo Facts

## Repository
Repository info

## Modules
Module info

## Entrypoints
Entry info

## Core Entities
Entity info
"""
        # Missing: Configuration
        errors = validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Configuration" in errors[0]

    def test_missing_multiple_sections_fails(self) -> None:
        """Missing multiple required sections should fail."""
        content = """# Repo Facts

## Repository
Repository info

## Modules
Module info
"""
        # Missing: Entrypoints, Core Entities, Configuration
        errors = validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Entrypoints" in errors[0]
        assert "Core Entities" in errors[0]
        assert "Configuration" in errors[0]

    def test_missing_all_sections_fails(self) -> None:
        """Missing all required sections should fail."""
        content = "# Repo Facts\n\nNo sections here."
        errors = validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        # Should list all 5 missing sections
        for section in REPO_FACTS_REQUIRED:
            assert section in errors[0]

    def test_wrong_sections_fails(self) -> None:
        """Having wrong sections should fail."""
        content = """# Repo Facts

## Wrong Section 1
Content

## Wrong Section 2
Content
"""
        errors = validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()


class TestRepoUnderstandingValidation:
    """Test repo-understanding validation with all 3 required sections."""

    def test_all_three_sections_present_passes(self) -> None:
        """All 3 required sections present should pass."""
        content = """# Repo Understanding

## System Purpose
Purpose info

## Pipelines
Pipeline info

## Concepts
Concept info

## Candidate Domains
Domain info
"""
        errors = validate_repo_understanding(content)
        assert errors == []

    def test_missing_one_section_fails(self) -> None:
        """Missing one required section should fail."""
        content = """# Repo Understanding

## System Purpose
Purpose info

## Pipelines
Pipeline info

## Candidate Domains
Domain info
"""
        # Missing: Concepts
        errors = validate_repo_understanding(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Concepts" in errors[0]

    def test_missing_multiple_sections_fails(self) -> None:
        """Missing multiple required sections should fail."""
        content = """# Repo Understanding

## System Purpose
Purpose info
"""
        # Missing: Pipelines, Concepts
        errors = validate_repo_understanding(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Pipelines" in errors[0]
        assert "Concepts" in errors[0]

    def test_missing_all_required_sections_fails(self) -> None:
        """Missing all required sections should fail."""
        content = """# Repo Understanding

## Some Other Section
Random content
"""
        errors = validate_repo_understanding(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        # Should list all 4 missing required sections
        for section in REPO_UNDERSTANDING_REQUIRED:
            assert section in errors[0]


class TestRegressionValidation:
    """Regression tests to ensure existing valid artifacts still pass."""

    def test_valid_repo_facts_still_passes(self) -> None:
        """Previously valid repo-facts should still pass."""
        content = """# Repo Facts

## Repository
Name: test-repo
URL: https://github.com/test/repo

## Modules
- module1
- module2

## Entrypoints
- main.py
- cli.py

## Core Entities
- User
- Product

## Configuration
- config.yaml
- .env
"""
        errors = validate_repo_facts(content)
        assert errors == []

    def test_valid_repo_understanding_still_passes(self) -> None:
        """Previously valid repo-understanding should still pass."""
        content = """# Repo Understanding

## System Purpose
This system manages user data.

## Pipelines
1. Data ingestion pipeline
2. Processing pipeline

## Concepts
- User management
- Data validation

## Candidate Domains
- User domain
- Data domain
"""
        errors = validate_repo_understanding(content)
        assert errors == []

    def test_invalid_repo_facts_now_fails(self) -> None:
        """Previously invalid repo-facts should now fail with clear errors."""
        content = """# Repo Facts

## Repository
Some info
"""
        errors = validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        # Should clearly indicate which sections are missing
        assert "Modules" in errors[0]
        assert "Entrypoints" in errors[0]
        assert "Core Entities" in errors[0]
        assert "Configuration" in errors[0]

    def test_invalid_repo_understanding_now_fails(self) -> None:
        """Previously invalid repo-understanding should now fail with clear errors."""
        content = """# Repo Understanding

## System Purpose
Purpose only
"""
        errors = validate_repo_understanding(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        # Should clearly indicate which sections are missing
        assert "Pipelines" in errors[0]
        assert "Concepts" in errors[0]

    def test_empty_artifacts_fail(self) -> None:
        """Empty artifacts should fail validation."""
        assert len(validate_repo_facts("")) > 0
        assert len(validate_repo_understanding("")) > 0

    def test_whitespace_only_artifacts_fail(self) -> None:
        """Whitespace-only artifacts should fail validation."""
        assert len(validate_repo_facts("   \n\n  ")) > 0
        assert len(validate_repo_understanding("   \n\n  ")) > 0
