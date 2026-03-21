"""
Executor bridge for Claude API integration.

This module provides the bridge between prompt_runner and the host
environment's Claude API executor.
"""

from collections.abc import Callable

# Global executor reference (set by host environment)
_global_executor: Callable[[str], str] | None = None


def set_executor(executor: Callable[[str], str]) -> None:
    """
    Set the global executor for prompt execution.

    Args:
        executor: Callable that takes a prompt string and returns response string
    """
    global _global_executor
    _global_executor = executor


def get_executor() -> Callable[[str], str] | None:
    """Get the current global executor."""
    return _global_executor


def clear_executor() -> None:
    """Clear the global executor."""
    global _global_executor
    _global_executor = None
