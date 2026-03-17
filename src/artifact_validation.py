"""Artifact Validation

Validates semantic artifacts using two validation strategies:

1. Required Sections (AND logic): All sections must be present
   - Used for critical artifacts like repo-facts, repo-understanding
   - Ensures completeness of essential information
   - Example: repo-facts requires ALL of: Repository, Modules, Entrypoints, etc.

2. Optional Sections (OR logic): At least one section must be present
   - Used for flexible artifacts like domain-candidates
   - Allows alternative structures
   - Example: domain-candidates needs ANY of: Candidate Domains, Domain Analysis, etc.

Functions:
- _has_required_sections: Validates ALL sections present (AND logic)
- _has_any_optional_section: Validates ANY section present (OR logic)
- validate_*: Artifact-specific validators that apply the appropriate strategy

Each validator returns a list of error messages (empty list if valid).
"""

from __future__ import annotations

import re


# Schema-defined sections for each artifact type
# Required sections (ALL must be present) - Use _has_required_sections with AND logic
REPO_FACTS_REQUIRED = ("Repository", "Modules", "Entrypoints", "Core Entities", "Configuration")
REPO_UNDERSTANDING_REQUIRED = ("System Purpose", "Pipelines", "Concepts", "Candidate Domains")
KNOWLEDGE_CONFIDENCE_REQUIRED = ("Confirmed Knowledge", "Inferred Knowledge", "Uncertain Knowledge")
# Optional sections (ANY must be present) - Use _has_any_optional_section with OR logic
DOMAIN_CANDIDATES_SECTIONS = ("Candidate Domains",)
# Required sections (ALL must be present) - Use _has_required_sections with AND logic
REVIEW_SUMMARY_REQUIRED = ("System Summary", "Pipelines", "Concepts", "Candidate Domains", "Assumptions", "Questions for Architect")

# Baseline section headings and their required schema keywords
BASELINE_SECTIONS: dict[str, str] = {
    "purpose": "Primary Purpose",
    "domains": "Domain Name",
    "concepts": "Concept Name",
    "pipelines": "Pipeline Name",
}


def _has_required_sections(content: str, required: tuple[str, ...]) -> bool:
    """Check if content has ALL required section headings (AND logic).

    Use this for critical artifacts where completeness is essential.
    All sections must be present for validation to pass.

    Args:
        content: The artifact content to check
        required: Tuple of required section heading names

    Returns:
        True if ALL required sections are present, False otherwise

    Example:
        >>> content = "## Repository\\n...\\n## Modules\\n..."
        >>> _has_required_sections(content, ("Repository", "Modules"))
        True
        >>> _has_required_sections(content, ("Repository", "Missing"))
        False
    """
    for heading in required:
        pattern = re.compile(rf"^##\s+{re.escape(heading)}\b", re.MULTILINE | re.IGNORECASE)
        if pattern.search(content) is None:
            return False  # Missing required section
    return True


def _has_any_optional_section(content: str, optional: tuple[str, ...]) -> bool:
    """Check if content has ANY of the optional section headings (OR logic).

    Use this for flexible artifacts where alternative structures are acceptable.
    At least one section must be present for validation to pass.

    Args:
        content: The artifact content to check
        optional: Tuple of optional section heading names

    Returns:
        True if at least one optional section is present, False otherwise

    Example:
        >>> content = "## Candidate Domains\\n..."
        >>> _has_any_optional_section(content, ("Candidate Domains", "Domain Analysis"))
        True
        >>> _has_any_optional_section(content, ("Missing1", "Missing2"))
        False
    """
    for heading in optional:
        pattern = re.compile(rf"^##\s+{re.escape(heading)}\b", re.MULTILINE | re.IGNORECASE)
        if pattern.search(content) is not None:
            return True
    return False


def _has_any_section_heading(content: str, headings: tuple[str, ...]) -> bool:
    """Check if content contains at least one ## heading from the given list.

    DEPRECATED: Use _has_required_sections or _has_any_optional_section instead.
    """
    for heading in headings:
        pattern = re.compile(rf"^##\s+{re.escape(heading)}\b", re.MULTILINE | re.IGNORECASE)
        if pattern.search(content) is not None:
            return True
    return False


def validate_repo_facts(content: str) -> list[str]:
    """Validate repo-facts artifact against schema-defined sections.

    All sections are required (AND logic).

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("repo-facts: artifact content is empty")
        return errors

    if not _has_required_sections(content, REPO_FACTS_REQUIRED):
        # Find which sections are missing
        missing = []
        for section in REPO_FACTS_REQUIRED:
            pattern = re.compile(rf"^##\s+{re.escape(section)}\b", re.MULTILINE | re.IGNORECASE)
            if pattern.search(content) is None:
                missing.append(section)

        errors.append(
            f"repo-facts: missing required sections. "
            f"ALL sections are required. Missing: {', '.join(missing)}"
        )

    return errors


def validate_repo_understanding(content: str) -> list[str]:
    """Validate repo-understanding artifact against schema-defined sections.

    All sections are required (AND logic).

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("repo-understanding: artifact content is empty")
        return errors

    if not _has_required_sections(content, REPO_UNDERSTANDING_REQUIRED):
        # Find which sections are missing
        missing = []
        for section in REPO_UNDERSTANDING_REQUIRED:
            pattern = re.compile(rf"^##\s+{re.escape(section)}\b", re.MULTILINE | re.IGNORECASE)
            if pattern.search(content) is None:
                missing.append(section)

        errors.append(
            f"repo-understanding: missing required sections. "
            f"ALL sections are required. Missing: {', '.join(missing)}"
        )

    return errors


def validate_knowledge_confidence(content: str) -> list[str]:
    """Validate knowledge-confidence artifact against schema-defined sections.

    All sections are required (AND logic).

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("knowledge-confidence: artifact content is empty")
        return errors

    if not _has_required_sections(content, KNOWLEDGE_CONFIDENCE_REQUIRED):
        # Find which sections are missing
        missing = []
        for section in KNOWLEDGE_CONFIDENCE_REQUIRED:
            pattern = re.compile(rf"^##\s+{re.escape(section)}\b", re.MULTILINE | re.IGNORECASE)
            if pattern.search(content) is None:
                missing.append(section)

        errors.append(
            f"knowledge-confidence: missing required sections. "
            f"ALL sections are required. Missing: {', '.join(missing)}"
        )

    return errors


def validate_domain_candidates(content: str) -> list[str]:
    """Validate domain-candidates artifact against schema-defined sections.

    All sections are required (AND logic).

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("domain-candidates: artifact content is empty")
        return errors

    if not _has_required_sections(content, DOMAIN_CANDIDATES_SECTIONS):
        # Find which sections are missing
        missing = []
        for section in DOMAIN_CANDIDATES_SECTIONS:
            pattern = re.compile(rf"^##\s+{re.escape(section)}\b", re.MULTILINE | re.IGNORECASE)
            if pattern.search(content) is None:
                missing.append(section)

        errors.append(
            f"domain-candidates: missing required sections. "
            f"ALL sections are required. Missing: {', '.join(missing)}"
        )

    return errors


def validate_review_summary(content: str) -> list[str]:
    """Validate review-summary artifact against schema-defined sections.

    All sections are required (AND logic).

    Args:
        content: The artifact content to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []

    if not content or not content.strip():
        errors.append("review-summary: artifact content is empty")
        return errors

    if not _has_required_sections(content, REVIEW_SUMMARY_REQUIRED):
        # Find which sections are missing
        missing = []
        for section in REVIEW_SUMMARY_REQUIRED:
            pattern = re.compile(rf"^##\s+{re.escape(section)}\b", re.MULTILINE | re.IGNORECASE)
            if pattern.search(content) is None:
                missing.append(section)

        errors.append(
            f"review-summary: missing required sections. "
            f"ALL sections are required. Missing: {', '.join(missing)}"
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
