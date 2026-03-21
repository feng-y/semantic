"""Command dispatcher — routes init/discover/refine to the appropriate handler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import state_inspector
from .discovery_executor import run_discovery
from .refine_executor import run_refine

# Directory structure required by init
REQUIRED_DIRS = [
    "docs/fact/schemas",
    "docs/fact/discovery",
    "docs/fact/review",
    "docs/fact/baseline",
]

# Default files created by init (only if missing)
DEFAULT_FILES: dict[str, str] = {
    "docs/fact/review/architect-feedback.md": "",
    "docs/fact/review/semantic-change-log.md": "",
    "docs/fact/discovery/sampling-report.md": "",
}


def dispatch(command: str, root: str | Path, **kwargs: Any) -> dict[str, Any]:
    """Dispatch a command and return a result dict.

    Supported commands: init, discover, refine, status

    Keyword Args:
        executor: Optional HostExecutor passed to discover/refine handlers.

    Returns:
        Dict with 'command', 'status', and command-specific results.
    """
    root = Path(root).resolve()
    handlers = {
        "init": _handle_init,
        "discover": _handle_discover,
        "refine": _handle_refine,
        "status": _handle_status,
        "reset": _handle_reset,
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
    executor = kwargs.get("executor")

    result = run_discovery(
        root,
        sampling_mode=sampling_mode,
        sampling_timeout=sampling_timeout,
        executor=executor,
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
    """Run the refinement skill by executing each step in declared order."""
    executor = kwargs.get("executor")
    result = run_refine(root, executor=executor)

    return {
        "command": "refine",
        "status": result.status,
        "acceptance_detected": result.acceptance_detected,
        "baseline_generated": result.baseline_generated,
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


def _handle_reset(root: Path, **kwargs: Any) -> dict[str, Any]:
    """Reset working semantic state. Preserves baseline and schemas."""

    removed: list[str] = []

    # Clear current FACT working directories
    for d in ("discovery", "review"):
        dd = root / "docs" / "fact" / d
        if dd.exists():
            for f in dd.iterdir():
                if f.is_file():
                    f.unlink()
                    removed.append(str(f.relative_to(root)))

    # Clear current FACT snapshot
    fact_snap = root / "docs" / "fact" / "semantic_snapshot.json"
    if fact_snap.exists():
        fact_snap.unlink()
        removed.append(str(fact_snap.relative_to(root)))

    # Legacy cleanup: also clear old semantic paths if they exist
    for d in ("discovery", "review"):
        dd = root / "docs" / "semantic" / d
        if dd.exists():
            for f in dd.iterdir():
                if f.is_file():
                    f.unlink()
                    removed.append(str(f.relative_to(root)))

    snap = root / "docs" / "semantic" / "semantic_snapshot.json"
    if snap.exists():
        snap.unlink()
        removed.append(str(snap.relative_to(root)))

    return {
        "command": "reset",
        "status": "ok",
        "removed": removed,
    }
