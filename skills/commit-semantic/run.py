#!/usr/bin/env python3
"""commit-semantic skill implementation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state, get_next_stage
from src.intent_router import parse_intent

STAGES = ["analyze", "domain-map", "feed"]
STATE_PATH = Path(".harness/state/commit-semantic/run-state.json")
OUTPUT_DIR = Path(".harness/outputs/commit-semantic")
EXTRACT_OUTPUT = Path(".harness/outputs/commit-extract")


def check_prerequisites() -> tuple[bool, str]:
    """Check if commit-extract output exists."""
    if not EXTRACT_OUTPUT.exists():
        return False, f"commit-extract output not found at {EXTRACT_OUTPUT}. Run /commit-extract first."
    return True, ""


def get_completed_stages(state: HarnessState) -> list[str]:
    """Get completed stages from state metadata."""
    return state.metadata.get("completed_stages", [])


def get_status(state: HarnessState) -> str:
    """Get status from state metadata."""
    return state.metadata.get("status", "ok")


def get_current_stage(state: HarnessState) -> str | None:
    """Get current stage from state metadata."""
    return state.metadata.get("current_stage")


def get_artifacts_written(state: HarnessState) -> list[str]:
    """Get artifacts written from state metadata."""
    return state.metadata.get("artifacts_written", [])


def summary(state: HarnessState) -> str:
    """Generate human-readable summary."""
    completed = get_completed_stages(state)
    status = get_status(state)
    current = get_current_stage(state)
    stage_num = len(completed)
    total = len(STAGES)

    if status == "breakpoint":
        return (
            f"[commit-semantic] Breakpoint at stage {stage_num+1}/{total} ({current}).\n"
            f"Done: {', '.join(completed) or 'none'}\n"
            f"Next: /commit-semantic step or /commit-semantic resume"
        )
    elif status == "ok" and stage_num == total:
        return (
            f"[commit-semantic] Complete. All {total} stages done.\n"
            f"Artifacts: {len(get_artifacts_written(state))} written."
        )
    elif status == "error":
        reason = state.metadata.get("breakpoint_reason", "unknown error")
        return f"[commit-semantic] Error at {current}: {reason}"
    else:
        return f"[commit-semantic] Status: {status}, Stage: {state.stage}"


def init_state() -> HarnessState:
    """Create fresh state."""
    state = HarnessState(
        stage="init",
        metadata={
            "command": "commit-semantic",
            "status": "ok",
            "completed_stages": [],
            "artifacts_written": [],
            "current_stage": None,
        }
    )
    return state


def handle_status() -> int:
    """Handle status intent."""
    if not STATE_PATH.exists():
        print("[commit-semantic] No state found. Run /commit-semantic run to start.")
        return 0

    # Load state directly since the API expects pipeline name
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            import json
            data = json.load(f)
        from src.harness_state import HarnessState
        state = HarnessState.from_dict(data)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[commit-semantic] No state found. Run /commit-semantic run to start.")
        return 0

    print(summary(state))
    return 0


def handle_reset() -> int:
    """Handle reset intent."""
    if not STATE_PATH.exists():
        print("[commit-semantic] No state to reset.")
        return 0

    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            import json
            data = json.load(f)
        from src.harness_state import HarnessState
        old_state = HarnessState.from_dict(data)

        # Keep artifacts, clear state
        new_state = init_state()
        new_state.metadata["artifacts_written"] = get_artifacts_written(old_state)

        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(new_state.to_dict(), f, indent=2, ensure_ascii=False)

        print("[commit-semantic] State reset. Artifacts preserved.")
    except (FileNotFoundError, json.JSONDecodeError):
        print("[commit-semantic] No state to reset.")

    return 0


def run_stage(stage: str, state: HarnessState) -> bool:
    """Run a single stage. Returns True on success."""
    print(f"[commit-semantic] Running stage: {stage}")

    # TODO: Integrate with src/commit_semantic/ logic

    if stage == "analyze":
        print("  → Analyzing commit patterns")
        artifacts = get_artifacts_written(state)
        artifacts.append("patterns/pattern-analysis.yaml")
        state.metadata["artifacts_written"] = artifacts

    elif stage == "domain-map":
        print("  → Mapping patterns to semantic domains")
        artifacts = get_artifacts_written(state)
        artifacts.append("domains/domain-mapping.yaml")
        state.metadata["artifacts_written"] = artifacts

    elif stage == "feed":
        print("  → Preparing demand pipeline feed")
        artifacts = get_artifacts_written(state)
        artifacts.append("domains/demand-feed.yaml")
        state.metadata["artifacts_written"] = artifacts

    completed = get_completed_stages(state)
    completed.append(stage)
    state.metadata["completed_stages"] = completed
    state.metadata["current_stage"] = None
    state.last_updated = datetime.now(timezone.utc).isoformat()

    return True


def handle_step() -> int:
    """Handle step intent - run single next stage."""
    ok, msg = check_prerequisites()
    if not ok:
        print(f"[commit-semantic] Prerequisites not met: {msg}")
        return 1

    # Load state
    import json
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        state = HarnessState.from_dict(data)
    else:
        state = init_state()

    completed = get_completed_stages(state)
    next_stage = None
    for stage in STAGES:
        if stage not in completed:
            next_stage = stage
            break

    if next_stage is None:
        state.metadata["status"] = "ok"
        print(summary(state))
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
        return 0

    state.metadata["current_stage"] = next_stage
    success = run_stage(next_stage, state)

    if success:
        # Set breakpoint after each step
        state.metadata["status"] = "breakpoint"
        # Calculate next stage for resume token
        remaining = [s for s in STAGES if s not in get_completed_stages(state)]
        next_remaining = remaining[0] if remaining else "done"
        state.metadata["resume_token"] = f"step{len(get_completed_stages(state))+1}_{next_remaining}"
        state.metadata["breakpoint_reason"] = f"Stage {next_stage} complete. Run step to continue or resume for all."
    else:
        state.metadata["status"] = "error"
        state.metadata["breakpoint_reason"] = f"Stage {next_stage} failed"

    print(summary(state))
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

    return 0 if success else 1


def handle_resume() -> int:
    """Handle resume intent - run all remaining stages."""
    ok, msg = check_prerequisites()
    if not ok:
        print(f"[commit-semantic] Prerequisites not met: {msg}")
        return 1

    import json
    if STATE_PATH.exists():
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
        state = HarnessState.from_dict(data)
    else:
        state = init_state()

    while True:
        completed = get_completed_stages(state)
        next_stage = None
        for stage in STAGES:
            if stage not in completed:
                next_stage = stage
                break

        if next_stage is None:
            break

        state.metadata["current_stage"] = next_stage
        success = run_stage(next_stage, state)

        if not success:
            state.metadata["status"] = "error"
            state.metadata["breakpoint_reason"] = f"Stage {next_stage} failed"
            print(summary(state))
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            return 1

    state.metadata["status"] = "ok"
    state.metadata["current_stage"] = None
    state.metadata["resume_token"] = None
    state.metadata["breakpoint_reason"] = None

    print(summary(state))
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

    return 0


def handle_run() -> int:
    """Handle run intent - full pipeline."""
    # Reset state for fresh run
    state = init_state()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
    return handle_resume()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commit semantic skill")
    parser.add_argument("intent", nargs="?", default="run")
    args = parser.parse_args(argv)

    # Parse intent from args
    intent = parse_intent(["commit-semantic", args.intent])

    # Route to handler
    handlers = {
        "status": handle_status,
        "reset": handle_reset,
        "step": handle_step,
        "resume": handle_resume,
        "run": handle_run,
    }

    handler = handlers.get(intent, handle_run)
    return handler()


if __name__ == "__main__":
    raise SystemExit(main())
