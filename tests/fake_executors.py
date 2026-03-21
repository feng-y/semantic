"""Test-only fake executors for discovery pipeline testing.

These produce structurally valid placeholder content that passes
validation. They must NEVER be used in core runtime — only in tests.
"""

from __future__ import annotations


def stub_executor(
    prompt_text: str,
    context: dict[str, str],
    *,
    artifact_name: str,
    sampling_mode: str = "auto",
) -> str:
    """Fake executor that produces valid placeholder artifacts."""
    lines = [f"# {artifact_name}", ""]

    if artifact_name == "sampling-report":
        lines.extend([
            "## Sampling Mode",
            f"{sampling_mode}",
            "",
            "## Selected Areas",
            "- (stub: areas pending real sampling)",
            "",
            "## Selected Files",
            "- (stub: files pending real sampling)",
            "",
            "## Selection Rationale",
            "(stub: rationale pending real sampling)",
            "",
            "## Likely Blind Spots",
            "- (stub: blind spots pending real sampling)",
            "",
            "## Suggested Expansions",
            "- (stub: expansions pending real sampling)",
        ])
    elif artifact_name == "repo-facts":
        lines.extend([
            "## Repository",
            "- Primary Language: Python",
            "- Evidence: pyproject.toml",
            "",
            "## Modules",
            "- Name: src",
            "- Evidence: directory listing",
            "",
            "## Entrypoints",
            "- Entrypoint: main.py",
            "- Evidence: (stub: pending)",
            "",
            "## Core Entities",
            "- Entity: (stub: pending)",
            "- Evidence: (stub: pending)",
            "",
            "## Configuration",
            "- Config: (stub: pending)",
            "- Evidence: (stub: pending)",
        ])
    elif artifact_name == "repo-understanding":
        lines.extend([
            "## System Purpose",
            "- Purpose: (stub: pending real extraction)",
            "- Evidence: (stub: pending)",
            "- Confidence: high",
            "",
            "## Pipelines",
            "- Pipeline Name: (stub: pending)",
            "- Evidence: (stub: pending)",
            "- Confidence: medium",
            "",
            "## Concepts",
            "- Concept Name: (stub: pending)",
            "- Evidence: (stub: pending)",
            "- Confidence: medium",
            "",
            "## Candidate Domains",
            "- Domain Name: (stub: pending)",
        ])
    elif artifact_name == "knowledge-confidence":
        lines.extend([
            "## Confirmed Knowledge",
            "- Item: (stub: confirmed item pending real assessment)",
            "- Evidence: (stub: pending)",
            "",
            "## Inferred Knowledge",
            "- Item: (stub: inferred item pending real assessment)",
            "- Evidence: (stub: pending)",
            "",
            "## Uncertain Knowledge",
            "- Item: (stub: uncertain item pending real assessment)",
            "- Reason: (stub: pending)",
        ])
    elif artifact_name == "domain-candidates":
        lines.extend([
            "## Candidate Domains",
            "- (stub: domains pending real extraction)",
        ])
    elif artifact_name == "review-summary":
        lines.extend([
            "## System Summary",
            "(stub: pending real generation)",
            "",
            "## Pipelines",
            "- (stub: pending)",
            "",
            "## Concepts",
            "- (stub: pending)",
            "",
            "## Candidate Domains",
            "- (stub: pending)",
            "",
            "## Assumptions",
            "- (stub: pending)",
            "",
            "## Questions for Architect",
            "- (stub: pending)",
        ])
    elif artifact_name == "baseline":
        lines = [
            "## Purpose",
            "Primary Purpose: (stub: system purpose pending real synthesis)",
            "Supported Scenarios: (stub: pending)",
            "Non Goals: (stub: pending)",
            "",
            "## Domains",
            "Domain Name: (stub: primary domain pending real synthesis)",
            "Description: (stub: pending)",
            "Related Pipelines: (stub: pending)",
            "",
            "## Concepts",
            "Concept Name: (stub: core concept pending real synthesis)",
            "Description: (stub: pending)",
            "Role: (stub: pending)",
            "",
            "## Pipelines",
            "Pipeline Name: (stub: main pipeline pending real synthesis)",
            "Purpose: (stub: pending)",
            "Flow: (stub: pending)",
        ]
    elif artifact_name == "change-analysis":
        lines.extend([
            "## Change Intent",
            "- Intent: (stub: change intent pending real analysis)",
            "",
            "## Affected Pipelines",
            "- Pipeline: (stub: affected pipeline pending real analysis)",
            "",
            "## Affected Domains and Concepts",
            "Domains:",
            "- Domain: (stub: affected domain pending real analysis)",
            "",
            "Concepts:",
            "- Concept: (stub: affected concept pending real analysis)",
            "",
            "## Impact and Risks",
            "- Impact: (stub: impact pending real analysis)",
            "",
            "## Suggested Next Changes",
            "- Suggestion: (stub: next change pending real analysis)",
        ])

    return "\n".join(lines) + "\n"


def stub_augment_executor(
    prompt_text: str,
    context: dict[str, str],
    *,
    artifact_name: str,
    sampling_mode: str = "auto",
) -> str:
    """Fake augment executor — appends evidence annotations to base content."""
    base = context.get("repo_facts", "")
    augmentation = [
        "",
        "## Evidence Annotations",
        "- (stub: file/symbol/line evidence pending real extraction)",
    ]
    return base.rstrip() + "\n" + "\n".join(augmentation) + "\n"
