#!/usr/bin/env python3
"""commit-extract skill implementation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state
from src.intent_router import parse_intent

# Stages in order
STAGES = ["collect", "extract", "pattern"]

PIPELINE = "commit-extract"


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
    stage_num = len(completed)
    total = len(STAGES)
    status = get_status(state)
    current = get_current_stage(state)

    if status == "breakpoint":
        return (
            f"[commit-extract] Breakpoint at stage {stage_num+1}/{total} ({current}).\n"
            f"Done: {', '.join(completed) or 'none'}\n"
            f"Next: /commit-extract step or /commit-extract resume"
        )
    elif status == "ok":
        return (
            f"[commit-extract] Complete. All {total} stages done.\n"
            f"Artifacts: {len(get_artifacts_written(state))} written."
        )
    elif status == "error":
        reason = state.metadata.get("breakpoint_reason", "unknown error")
        return f"[commit-extract] Error at {current}: {reason}"
    else:
        return f"[commit-extract] Status: {status}, Stage: {state.stage}"


def init_state() -> HarnessState:
    """Create fresh state."""
    return HarnessState(
        stage="init",
        metadata={
            "completed_stages": [],
            "artifacts_written": [],
            "status": "ok",
        },
    )


def handle_status() -> int:
    """Handle status intent."""
    state = load_state(PIPELINE)
    if state.stage == "init" and not get_completed_stages(state):
        print("[commit-extract] No state found. Run /commit-extract run to start.")
        return 0

    print(summary(state))
    return 0


def handle_reset() -> int:
    """Handle reset intent."""
    state = load_state(PIPELINE)
    if state.stage != "init" or get_completed_stages(state):
        # Preserve artifacts, clear progress
        old_artifacts = get_artifacts_written(state)
        new_state = init_state()
        new_state.metadata["artifacts_written"] = old_artifacts
        save_state(PIPELINE, new_state)
        print("[commit-extract] State reset. Artifacts preserved.")
    else:
        print("[commit-extract] No state to reset.")
    return 0


def run_stage(stage: str, state: HarnessState) -> bool:
    """Run a single stage. Returns True on success."""
    print(f"[commit-extract] Running stage: {stage}")

    artifacts = get_artifacts_written(state)

    if stage == "collect":
        print("  → Collecting commits from git history")
        artifacts.append("commits/commits.jsonl")

    elif stage == "extract":
        print("  → Extracting rules and invariants")
        artifacts.append("rules/rules.yaml")
        artifacts.append("invariants/invariants.yaml")

    elif stage == "pattern":
        print("  → Identifying patterns")
        artifacts.append("patterns/patterns.yaml")

    completed = get_completed_stages(state)
    completed.append(stage)
    state.metadata["completed_stages"] = completed
    state.metadata["artifacts_written"] = artifacts
    state.metadata["current_stage"] = None
    state.stage = stage

    return True


def get_next_stage_from_state(state: HarnessState) -> str | None:
    """Get next uncompleted stage."""
    completed = get_completed_stages(state)
    for s in STAGES:
        if s not in completed:
            return s
    return None


def handle_step() -> int:
    """Handle step intent - run single next stage."""
    state = load_state(PIPELINE)
    if state.stage == "init" and not get_completed_stages(state):
        state = init_state()

    next_stage = get_next_stage_from_state(state)
    if next_stage is None:
        state.metadata["status"] = "ok"
        print(summary(state))
        save_state(PIPELINE, state)
        return 0

    state.metadata["current_stage"] = next_stage
    success = run_stage(next_stage, state)

    if success:
        state.metadata["status"] = "breakpoint"
        remaining = [s for s in STAGES if s not in get_completed_stages(state)]
        next_remaining = remaining[0] if remaining else "done"
        state.metadata["resume_token"] = f"step{len(get_completed_stages(state))}_{next_remaining}"
        state.metadata["breakpoint_reason"] = f"Stage {next_stage} complete. Run step to continue or resume for all."
    else:
        state.metadata["status"] = "error"
        state.metadata["breakpoint_reason"] = f"Stage {next_stage} failed"

    print(summary(state))
    save_state(PIPELINE, state)
    return 0 if success else 1


def handle_resume() -> int:
    """Handle resume intent - run all remaining stages."""
    state = load_state(PIPELINE)
    if state.stage == "init" and not get_completed_stages(state):
        state = init_state()

    while True:
        next_stage = get_next_stage_from_state(state)
        if next_stage is None:
            break

        state.metadata["current_stage"] = next_stage
        success = run_stage(next_stage, state)

        if not success:
            state.metadata["status"] = "error"
            state.metadata["breakpoint_reason"] = f"Stage {next_stage} failed"
            print(summary(state))
            save_state(PIPELINE, state)
            return 1

    state.metadata["status"] = "ok"
    state.metadata["current_stage"] = None
    state.metadata["resume_token"] = None
    state.metadata["breakpoint_reason"] = None
    state.stage = "complete"

    print(summary(state))
    save_state(PIPELINE, state)
    return 0


def handle_run() -> int:
    """Handle run intent - full pipeline."""
    state = init_state()
    save_state(PIPELINE, state)
    return handle_resume()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Commit extract skill")
    parser.add_argument("intent", nargs="?", default="run")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)

    # Parse intent from args
    intent = parse_intent(["commit-extract", args.intent])

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
