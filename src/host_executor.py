"""Host executor — interface for prompt execution by the host environment.

Semantic Harness never imports an LLM SDK directly. Instead, it defines
a callable protocol that the host environment (Claude Code) satisfies.

The default executor is a stub that produces structurally valid placeholder
content, used for testing and offline runs. A real host executor is injected
at runtime by the calling environment.
"""

from __future__ import annotations

from typing import Any, Protocol


class HostExecutor(Protocol):
    """Protocol for host-provided prompt execution.

    The host receives the full prompt text and assembled context,
    and returns the artifact content as a string.
    """

    def __call__(
        self,
        prompt_text: str,
        context: dict[str, str],
        *,
        artifact_name: str,
        sampling_mode: str = "auto",
    ) -> str: ...


def assemble_prompt_message(
    prompt_text: str,
    context: dict[str, str],
    artifact_name: str,
) -> str:
    """Assemble the full message sent to the host executor.

    Combines the raw prompt text with structured context sections
    into a single string the host can execute.
    """
    parts = [prompt_text, ""]

    for key, value in context.items():
        header = key.replace("_", " ").title()
        parts.append(f"--- {header} ---")
        parts.append(value)
        parts.append("")

    parts.append(f"Produce the artifact: {artifact_name}")
    return "\n".join(parts)


def stub_executor(
    prompt_text: str,
    context: dict[str, str],
    *,
    artifact_name: str,
    sampling_mode: str = "auto",
) -> str:
    """Default stub executor for testing and offline runs.

    Produces structurally valid placeholder content that passes
    validation, using the same logic as the Step 4 stubs.
    """
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
    """Stub augment executor — appends evidence annotations to base content."""
    base = context.get("repo_facts", "")
    augmentation = [
        "",
        "## Evidence Annotations",
        "- (stub: file/symbol/line evidence pending real extraction)",
    ]
    return base.rstrip() + "\n" + "\n".join(augmentation) + "\n"
