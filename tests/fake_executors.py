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
            f"## Sampling Mode",
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
    elif artifact_name in ("repo-facts", "repo-understanding"):
        lines.extend([
            "## Evidence",
            "- (stub: evidence pending real extraction)",
            "",
            "## Confidence",
            "- (stub: confidence pending real assessment)",
        ])
    elif artifact_name == "knowledge-confidence":
        lines.extend([
            "## Evidence",
            "- (stub: evidence from repo-understanding)",
            "",
            "## Confidence",
            "- overall: low (stub: pending real assessment)",
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
            "## Main Pipelines",
            "- (stub: pending)",
            "",
            "## Core Concepts",
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
