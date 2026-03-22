"""
Shared state utilities for the .harness directory structure.

Provides unified state management for commit-extract and commit-semantic pipelines.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HarnessState:
    """Unified state container for harness operations.

    Attributes:
        version: Schema version for state compatibility
        stage: Current processing stage (e.g., 'extract', 'semantic', 'complete')
        repo_path: Absolute path to the git repository being analyzed
        last_updated: ISO timestamp of last state update
        metadata: Arbitrary metadata dictionary for pipeline-specific data
    """

    version: str = "1.0"
    stage: str = "init"
    repo_path: str = ""
    last_updated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "version": self.version,
            "stage": self.stage,
            "repo_path": self.repo_path,
            "last_updated": self.last_updated,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HarnessState:
        """Create state from dictionary."""
        return cls(
            version=data.get("version", "1.0"),
            stage=data.get("stage", "init"),
            repo_path=data.get("repo_path", ""),
            last_updated=data.get(
                "last_updated", datetime.now(timezone.utc).isoformat()
            ),
            metadata=data.get("metadata", {}),
        )


def get_harness_root() -> Path:
    """Get the root .harness directory path.

    Returns:
        Path to .harness directory (relative to current working directory)
    """
    return Path(".harness")


def get_state_path(pipeline: str) -> Path:
    """Get state file path for a pipeline.

    Args:
        pipeline: Pipeline name ('commit-extract' or 'commit-semantic')

    Returns:
        Path to state.json file for the pipeline
    """
    return get_harness_root() / "state" / pipeline / "state.json"


def get_output_path(pipeline: str, artifact_type: str) -> Path:
    """Get output directory path for a pipeline artifact type.

    Args:
        pipeline: Pipeline name ('commit-extract' or 'commit-semantic')
        artifact_type: Type of artifact (e.g., 'commits', 'rules', 'patterns')

    Returns:
        Path to output directory for the artifact type
    """
    return get_harness_root() / "outputs" / pipeline / artifact_type


def load_state(pipeline: str) -> HarnessState:
    """Load state for a pipeline.

    Args:
        pipeline: Pipeline name ('commit-extract' or 'commit-semantic')

    Returns:
        Loaded HarnessState or fresh state if file doesn't exist
    """
    state_path = get_state_path(pipeline)

    if not state_path.exists():
        return HarnessState()

    try:
        with open(state_path, encoding="utf-8") as f:
            data = json.load(f)
        return HarnessState.from_dict(data)
    except (json.JSONDecodeError, OSError):
        return HarnessState()


def save_state(pipeline: str, state: HarnessState) -> None:
    """Save state for a pipeline.

    Args:
        pipeline: Pipeline name ('commit-extract' or 'commit-semantic')
        state: HarnessState to save
    """
    state_path = get_state_path(pipeline)
    state.last_updated = datetime.now(timezone.utc).isoformat()

    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: write to temp then rename
    tmp_path = state_path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
    tmp_path.rename(state_path)


# Stage transition definitions
STAGE_ORDER = ["init", "extract", "semantic", "complete"]

STAGE_TRANSITIONS: dict[str, list[str]] = {
    "init": ["extract"],
    "extract": ["semantic", "complete"],
    "semantic": ["complete"],
    "complete": [],
}


def get_next_stage(current_stage: str) -> str | None:
    """Get the next logical stage in the pipeline.

    Args:
        current_stage: Current stage name

    Returns:
        Next stage name or None if at terminal stage
    """
    if current_stage not in STAGE_ORDER:
        return None

    idx = STAGE_ORDER.index(current_stage)
    if idx >= len(STAGE_ORDER) - 1:
        return None

    return STAGE_ORDER[idx + 1]


def is_valid_transition(from_stage: str, to_stage: str) -> bool:
    """Check if a stage transition is valid.

    Args:
        from_stage: Current stage
        to_stage: Desired next stage

    Returns:
        True if transition is allowed
    """
    valid = STAGE_TRANSITIONS.get(from_stage, [])
    return to_stage in valid


def transition_state(pipeline: str, to_stage: str) -> HarnessState:
    """Transition pipeline to a new stage.

    Args:
        pipeline: Pipeline name
        to_stage: Target stage

    Returns:
        Updated HarnessState

    Raises:
        ValueError: If transition is invalid
    """
    state = load_state(pipeline)

    if not is_valid_transition(state.stage, to_stage):
        raise ValueError(f"Invalid transition: {state.stage} -> {to_stage}")

    state.stage = to_stage
    save_state(pipeline, state)
    return state
