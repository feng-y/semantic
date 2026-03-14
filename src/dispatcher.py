"""Command dispatcher — routes init/discover/refine to the appropriate handler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import skill_loader, state_inspector
from .discovery_executor import run_discovery

# Directory structure required by init
REQUIRED_DIRS = [
    "docs/semantic/schemas",
    "docs/semantic/discovery",
    "docs/semantic/review",
    "docs/semantic/baseline",
]

# Default files created by init (only if missing)
DEFAULT_FILES: dict[str, str] = {
    "docs/semantic/review/architect-feedback.md": "",
    "docs/semantic/review/semantic-change-log.md": "",
    "docs/semantic/discovery/sampling-report.md": "",
}


def dispatch(command: str, root: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Dispatch a command and return a result dict.

    Supported commands: init, discover, refine, status

    Returns:
        Dict with 'command', 'status', and command-specific results.
    """
    root = Path(root).resolve()
    handlers = {
        "init": _handle_init,
        "discover": _handle_discover,
        "refine": _handle_refine,
        "status": _handle_status,
    }

    handler = handlers.get(command)
    if handler is None:
        return {
            "command": command,
            "status": "error",
            "error": f"Unknown command: {command}. Valid: {', '.join(handlers)}",
        }

    return handler(root, **kwargs)


def _handle_init(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Create required directories and default files without overwriting."""
    created_dirs: list[str] = []
    created_files: list[str] = []
    skipped_files: list[str] = []

    for d in REQUIRED_DIRS:
        p = root / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            created_dirs.append(d)

    for filepath, default_content in DEFAULT_FILES.items():
        p = root / filepath
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text(default_content)
            created_files.append(filepath)
        else:
            skipped_files.append(filepath)

    return {
        "command": "init",
        "status": "ok",
        "created_dirs": created_dirs,
        "created_files": created_files,
        "skipped_files": skipped_files,
    }


def _handle_discover(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Run the discovery skill by executing each step in declared order."""
    sampling_mode = kwargs.get("sampling_mode", "auto")
    sampling_timeout = kwargs.get("sampling_timeout")

    result = run_discovery(
        root,
        sampling_mode=sampling_mode,
        sampling_timeout=sampling_timeout,
    )

    return {
        "command": "discover",
        "status": result.status,
        "sampling_mode": result.sampling_mode,
        "sampling_mode_switched": result.sampling_mode_switched,
        "steps": [
            {
                "index": s.step_index,
                "action": s.action,
                "target": s.target,
                "status": s.status,
                "artifact_path": s.artifact_path,
                "errors": s.errors,
            }
            for s in result.steps
        ],
        "artifacts_written": result.artifacts_written,
        "pruned_versions": result.pruned_versions,
        "validation_failures": result.validation_failures,
    }


def _handle_refine(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Run the refinement skill.

    Stub: loads the skill definition and reports steps.
    Real patch logic is not implemented yet.
    """
    skills = skill_loader.load_all_skills(root / "manifest.yaml")
    refine_skill = skills.get("refinement")
    if refine_skill is None:
        return {
            "command": "refine",
            "status": "error",
            "error": "Refinement skill not found in manifest.yaml",
        }

    steps = skill_loader.get_skill_steps(refine_skill)

    # Check if architect feedback exists
    state = state_inspector.inspect(root)

    return {
        "command": "refine",
        "status": "stub",
        "skill": refine_skill.get("name"),
        "has_architect_feedback": state.has_architect_feedback,
        "has_discovery_artifacts": state.has_discovery_artifacts,
        "steps": steps,
        "message": "Refinement skill loaded. Patch execution is stubbed.",
    }


def _handle_status(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Report current semantic state and recommended next action."""
    state = state_inspector.inspect(root)
    action = state_inspector.recommend_action(state)

    return {
        "command": "status",
        "status": "ok",
        "recommended_action": action,
        "has_discovery_artifacts": state.has_discovery_artifacts,
        "discovery_versions": state.discovery_versions,
        "has_review_summary": state.has_review_summary,
        "has_architect_feedback": state.has_architect_feedback,
        "has_accepted_baseline": state.has_accepted_baseline,
        "has_sampling_report": state.has_sampling_report,
        "feedback_has_acceptance": state.feedback_has_acceptance,
        "baseline_files": state.baseline_files,
    }
