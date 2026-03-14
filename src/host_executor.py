"""Host executor — interface for prompt execution by the host environment.

Semantic Harness never imports an LLM SDK directly. Instead, it defines
a callable protocol that the host environment (Claude Code) satisfies.

The host must provide an executor at runtime. If no executor is available,
the discovery pipeline returns execution_unavailable status.
"""

from __future__ import annotations

from typing import Protocol


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
