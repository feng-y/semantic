"""Validation for change-analysis artifacts."""

from __future__ import annotations

import re


CHANGE_ANALYSIS_SECTIONS = (
    "Change Intent",
    "Affected Pipelines",
    "Affected Domains and Concepts",
    "Impact and Risks",
    "Suggested Next Changes",
)


def validate_change_analysis(content: str) -> list[str]:
    """Validate change-analysis structure and minimal content."""
    errors: list[str] = []
    if not content or not content.strip():
        return ["change-analysis: artifact content is empty"]

    sections = _parse_sections(content)
    for name in CHANGE_ANALYSIS_SECTIONS:
        if name not in sections:
            errors.append(f"change-analysis: missing required section '{name}'")
            continue
        body = sections[name].strip()
        if not body:
            errors.append(f"change-analysis: section '{name}' is empty")
            continue
        if not _has_meaningful_line(body):
            errors.append(f"change-analysis: section '{name}' has no meaningful content")

    if "Affected Pipelines" in sections:
        if "pipeline:" not in sections["Affected Pipelines"].lower():
            errors.append("change-analysis: 'Affected Pipelines' must list at least one pipeline")

    if "Affected Domains and Concepts" in sections:
        body = sections["Affected Domains and Concepts"].lower()
        if "domains:" not in body or "concepts:" not in body:
            errors.append(
                "change-analysis: 'Affected Domains and Concepts' must include both domains and concepts blocks"
            )

    return errors


def _parse_sections(content: str) -> dict[str, str]:
    heading_re = re.compile(r"^##\s+(.+?)\s*$")
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for raw in content.splitlines():
        m = heading_re.match(raw.strip())
        if m:
            current = m.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(raw)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


def _has_meaningful_line(body: str) -> bool:
    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        return True
    return False

