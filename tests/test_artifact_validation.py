"""Tests for artifact_validation module.

Validates that structured validators correctly enforce schema-defined sections
for all artifact types.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import artifact_validation


class TestRepoFactsValidation:
    """Test validate_repo_facts()."""

    def test_valid_repo_facts(self) -> None:
        content = """# Repo Facts

## Repository
Some info

## Modules
Module info

## Entrypoints
Entry info

## Core Entities
Entity info

## Configuration
Config info
"""
        errors = artifact_validation.validate_repo_facts(content)
        assert errors == []

    def test_missing_all_sections(self) -> None:
        content = "# Repo Facts\n\nNo sections here.\n"
        errors = artifact_validation.validate_repo_facts(content)
        assert len(errors) > 0
        assert "repo-facts" in errors[0].lower()

    def test_empty_content(self) -> None:
        errors = artifact_validation.validate_repo_facts("")
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_partial_sections(self) -> None:
        content = """# Repo Facts

## Repository
Info here
"""
        # Should FAIL - not all required sections present (AND logic)
        errors = artifact_validation.validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Modules" in errors[0]  # Should list missing sections

    def test_missing_multiple_required_sections(self) -> None:
        content = """# Repo Facts

## Repository
Info here

## Modules
Module info
"""
        # Missing: Entrypoints, Core Entities, Configuration
        errors = artifact_validation.validate_repo_facts(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Entrypoints" in errors[0]
        assert "Core Entities" in errors[0]
        assert "Configuration" in errors[0]


class TestRepoUnderstandingValidation:
    """Test validate_repo_understanding()."""

    def test_valid_repo_understanding(self) -> None:
        content = """# Repo Understanding

## System Purpose
Purpose here

## Pipelines
Pipeline info

## Concepts
Concept info

## Candidate Domains
Domain info
"""
        errors = artifact_validation.validate_repo_understanding(content)
        assert errors == []

    def test_missing_all_sections(self) -> None:
        content = "# Repo Understanding\n\nNo sections.\n"
        errors = artifact_validation.validate_repo_understanding(content)
        assert len(errors) > 0
        assert "repo-understanding" in errors[0].lower()

    def test_empty_content(self) -> None:
        errors = artifact_validation.validate_repo_understanding("")
        assert len(errors) > 0

    def test_partial_sections(self) -> None:
        content = """# Repo Understanding

## System Purpose
Purpose here
"""
        # Should FAIL - not all required sections present (AND logic)
        errors = artifact_validation.validate_repo_understanding(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Pipelines" in errors[0]

    def test_missing_multiple_required_sections(self) -> None:
        content = """# Repo Understanding

## System Purpose
Purpose here

## Pipelines
Pipeline info
"""
        # Missing: Concepts, Candidate Domains
        errors = artifact_validation.validate_repo_understanding(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Concepts" in errors[0]
        assert "Candidate Domains" in errors[0]


class TestKnowledgeConfidenceValidation:
    """Test validate_knowledge_confidence()."""

    def test_valid_knowledge_confidence(self) -> None:
        content = """# Knowledge Confidence

## Confirmed Knowledge
Confirmed info

## Inferred Knowledge
Inferred info

## Uncertain Knowledge
Uncertain info
"""
        errors = artifact_validation.validate_knowledge_confidence(content)
        assert errors == []

    def test_missing_all_sections(self) -> None:
        content = "# Knowledge Confidence\n\nNo sections.\n"
        errors = artifact_validation.validate_knowledge_confidence(content)
        assert len(errors) > 0
        assert "knowledge-confidence" in errors[0].lower()

    def test_empty_content(self) -> None:
        errors = artifact_validation.validate_knowledge_confidence("")
        assert len(errors) > 0

    def test_partial_sections(self) -> None:
        content = """# Knowledge Confidence

## Confirmed Knowledge
Confirmed info
"""
        # Should FAIL - not all required sections present (AND logic)
        errors = artifact_validation.validate_knowledge_confidence(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Inferred Knowledge" in errors[0]

    def test_missing_multiple_required_sections(self) -> None:
        content = """# Knowledge Confidence

## Confirmed Knowledge
Confirmed info
"""
        # Missing: Inferred Knowledge, Uncertain Knowledge
        errors = artifact_validation.validate_knowledge_confidence(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Inferred Knowledge" in errors[0]
        assert "Uncertain Knowledge" in errors[0]


class TestDomainCandidatesValidation:
    """Test validate_domain_candidates()."""

    def test_valid_domain_candidates(self) -> None:
        content = """# Domain Candidates

## Candidate Domains
Domain info
"""
        errors = artifact_validation.validate_domain_candidates(content)
        assert errors == []

    def test_missing_section(self) -> None:
        content = "# Domain Candidates\n\nNo sections.\n"
        errors = artifact_validation.validate_domain_candidates(content)
        assert len(errors) > 0
        assert "domain-candidates" in errors[0].lower()

    def test_empty_content(self) -> None:
        errors = artifact_validation.validate_domain_candidates("")
        assert len(errors) > 0


class TestReviewSummaryValidation:
    """Test validate_review_summary()."""

    def test_valid_review_summary(self) -> None:
        content = """# Review Summary

## System Summary
Summary here

## Pipelines
Pipeline info

## Concepts
Concept info

## Candidate Domains
Domain info

## Assumptions
Assumptions here

## Questions for Architect
Questions here
"""
        errors = artifact_validation.validate_review_summary(content)
        assert errors == []

    def test_missing_all_sections(self) -> None:
        content = "# Review Summary\n\nNo sections.\n"
        errors = artifact_validation.validate_review_summary(content)
        assert len(errors) > 0
        assert "review-summary" in errors[0].lower()

    def test_empty_content(self) -> None:
        errors = artifact_validation.validate_review_summary("")
        assert len(errors) > 0

    def test_partial_sections(self) -> None:
        content = """# Review Summary

## System Summary
Summary here
"""
        # Should FAIL - not all required sections present (AND logic)
        errors = artifact_validation.validate_review_summary(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Pipelines" in errors[0]

    def test_missing_multiple_required_sections(self) -> None:
        content = """# Review Summary

## System Summary
Summary here

## Pipelines
Pipeline info
"""
        # Missing: Concepts, Candidate Domains, Assumptions, Questions for Architect
        errors = artifact_validation.validate_review_summary(content)
        assert len(errors) > 0
        assert "missing required sections" in errors[0].lower()
        assert "Concepts" in errors[0]
        assert "Assumptions" in errors[0]


class TestBaselineFilesValidation:
    """Test validate_baseline_files()."""

    def test_valid_baseline_files(self) -> None:
        baseline = {
            "purpose": "## Primary Purpose\nPurpose here",
            "domains": "## Domain Name\nDomain here",
            "concepts": "## Concept Name\nConcept here",
            "pipelines": "## Pipeline Name\nPipeline here",
        }
        errors = artifact_validation.validate_baseline_files(baseline)
        assert errors == []

    def test_missing_required_keyword(self) -> None:
        baseline = {
            "purpose": "## Some Other Heading\nContent here",
        }
        errors = artifact_validation.validate_baseline_files(baseline)
        assert len(errors) > 0
        assert "Primary Purpose" in errors[0]

    def test_empty_content(self) -> None:
        baseline = {
            "purpose": "",
        }
        errors = artifact_validation.validate_baseline_files(baseline)
        assert len(errors) > 0
        assert "empty" in errors[0].lower()

    def test_multiple_files_with_errors(self) -> None:
        baseline = {
            "purpose": "",
            "domains": "No keyword here",
        }
        errors = artifact_validation.validate_baseline_files(baseline)
        assert len(errors) >= 2


class TestCaseInsensitiveMatching:
    """Test that validation is case-insensitive for section headings."""

    def test_lowercase_sections_accepted(self) -> None:
        content = """# Repo Understanding

## system purpose
Purpose here

## pipelines
Pipeline info

## concepts
Concept info

## candidate domains
Domain info
"""
        errors = artifact_validation.validate_repo_understanding(content)
        assert errors == []

    def test_mixed_case_sections_accepted(self) -> None:
        content = """# Knowledge Confidence

## CONFIRMED KNOWLEDGE
Confirmed info

## inferred knowledge
Inferred info

## Uncertain Knowledge
Uncertain info
"""
        errors = artifact_validation.validate_knowledge_confidence(content)
        assert errors == []
