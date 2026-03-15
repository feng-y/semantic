"""Artifact validation module.

Provides structured validators that enforce schema-defined sections for all
semantic artifact types. Each validator returns a list of error messages.
"""

from __future__ import annotations

import re


# Schema-defined sections for each artifact type
REPO_FACTS_SECTIONS = ("Repository", "Modules", "Entrypoints", "Core Entities", "Configuration")
REPO_UNDERSTANDING_SECTIONS = ("System Purpose", "Pipelines", "Concepts", "Candidate Domains")
KNOWLEDGE_CONFIDENCE_SECTIONS = ("Confirmed Knowledge", "Inferred Knowledge", "Uncertain Knowledge")
DOMAIN_CANDIDATES_SECTIONS = ("Candidate Domains",)
REVIEW_SUMMARY_SECTIONS = ("System Summary", "Pipelines", "Concepts", "Candidate Domains", "Assumptions", "Questions for Architect")

# Baseline section headings and their required schema keywords
BASELINE_SECTIONS: dict[str, str] = {
    "purpose": "Primary Purpose",
    "domains": "Domain Name",
    "concepts": "Concept Name",
    "pipelines": "Pipeline Name",
}


def _has_any_section_heading(content: str, headings: tuple[str, ...]) -> bool:
    """Check if content contains at least one ## heading from the given list."""
    for heading in headings:
        pattern = re.compile(rf"^##\s+{re.escape(heading)}\b", re.MULTILINE | re.IGNORECASE)
        if pattern.search(content) is not None:
            return True
    return False


def validate_repo_facts(content: str) -> list[str]:
    """Validate repo-facts artifact against schema-defined sections.

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("repo-facts: artifact content is empty")
        return errors

    if not _has_any_section_heading(content, REPO_FACTS_SECTIONS):
        errors.append(
            f"repo-facts: missing required schema sections. "
            f"Expected at least one of: {', '.join(REPO_FACTS_SECTIONS)}"
        )

    return errors


def validate_repo_understanding(content: str) -> list[str]:
    """Validate repo-understanding artifact against schema-defined sections.

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("repo-understanding: artifact content is empty")
        return errors

    if not _has_any_section_heading(content, REPO_UNDERSTANDING_SECTIONS):
        errors.append(
            f"repo-understanding: missing required schema sections. "
            f"Expected at least one of: {', '.join(REPO_UNDERSTANDING_SECTIONS)}"
        )

    return errors


def validate_knowledge_confidence(content: str) -> list[str]:
    """Validate knowledge-confidence artifact against schema-defined sections.

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("knowledge-confidence: artifact content is empty")
        return errors

    if not _has_any_section_heading(content, KNOWLEDGE_CONFIDENCE_SECTIONS):
        errors.append(
            f"knowledge-confidence: missing required schema sections. "
            f"Expected at least one of: {', '.join(KNOWLEDGE_CONFIDENCE_SECTIONS)}"
        )

    return errors


def validate_domain_candidates(content: str) -> list[str]:
    """Validate domain-candidates artifact against schema-defined sections.

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("domain-candidates: artifact content is empty")
        return errors

    if not _has_any_section_heading(content, DOMAIN_CANDIDATES_SECTIONS):
        errors.append(
            f"domain-candidates: missing required schema sections. "
            f"Expected at least one of: {', '.join(DOMAIN_CANDIDATES_SECTIONS)}"
        )

    return errors


def validate_review_summary(content: str) -> list[str]:
    """Validate review-summary artifact against schema-defined sections.

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("review-summary: artifact content is empty")
        return errors

    if not _has_any_section_heading(content, REVIEW_SUMMARY_SECTIONS):
        errors.append(
            f"review-summary: missing required schema sections. "
            f"Expected at least one of: {', '.join(REVIEW_SUMMARY_SECTIONS)}"
        )

    return errors


def validate_baseline_files(baseline_dict: dict[str, str]) -> list[str]:
    """Validate baseline files against required schema keywords.

    Args:
        baseline_dict: Dictionary mapping baseline file names to their content

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    for name, content in baseline_dict.items():
        if not content or not content.strip():
            errors.append(f"{name}: artifact content is empty")
            continue

        required_keyword = BASELINE_SECTIONS.get(name)
        if required_keyword and required_keyword.lower() not in content.lower():
            errors.append(f"{name}: missing required keyword '{required_keyword}'")

    return errors
