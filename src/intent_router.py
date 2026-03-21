"""Intent classification for harness skills."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.executor_bridge import HostExecutor


def classify_intent_keyword(text: str) -> str:
    """Fast keyword-based intent classification."""
    text_lower = text.lower()

    # Status patterns
    if any(word in text_lower for word in ["status", "check", "where", "what is"]):
        return "status"

    # Reset patterns
    if any(word in text_lower for word in ["reset", "clear", "start over"]):
        return "reset"

    # Step patterns
    if any(word in text_lower for word in ["step", "next", "continue one", "single step"]):
        return "step"

    # Resume patterns
    if any(word in text_lower for word in ["resume", "continue", "proceed", "go on"]):
        return "resume"

    # Default to run
    return "run"


def classify_intent_llm(text: str, executor: HostExecutor | None = None) -> str:
    """LLM-based intent classification with keyword fallback."""
    # Try keyword first (fast path)
    keyword_result = classify_intent_keyword(text)

    # If no executor available, use keyword result
    if executor is None:
        return keyword_result

    # Use LLM for ambiguous cases or confirmation
    prompt = f'''Classify this command intent into exactly one category:

Command: "{text}"

Categories:
- run: execute full pipeline (default for "run", "execute", "pipeline")
- status: check current state (for "status", "check", "where am i")
- reset: clear state and start over (for "reset", "clear", "restart")
- step: run only next stage (for "step", "next", "single step")
- resume: continue from breakpoint (for "resume", "continue", "proceed")

Reply with ONLY the category word (run/status/reset/step/resume).'''

    try:
        result = executor(prompt).strip().lower()
        # Validate result
        if result in ("run", "status", "reset", "step", "resume"):
            return result
    except Exception:
        pass

    return keyword_result


def parse_intent(argv: list[str], executor: HostExecutor | None = None) -> str:
    """Parse intent from command line arguments."""
    # Join all args into single text for classification
    text = " ".join(argv[1:]) if len(argv) > 1 else "run"
    return classify_intent_llm(text, executor)
