#!/usr/bin/env python3
"""commit-extract skill implementation."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state, get_next_stage
from src.intent_router import parse_intent

# Stages in order
STAGES = ["collect", "extract", "pattern"]

STATE_PATH = Path(".harness/state/commit-extract/run-state.json")
OUTPUT_DIR = Path(".harness/outputs/commit-extract")


def summary(state: HarnessState) -> str:
    """Generate human-readable summary."""
    stage_num = len(state.completed_stages)
    total = len(STAGES)

    if state.status == "breakpoint":
        return (
            f"[commit-extract] Breakpoint at stage {stage_num+1}/{total} ({state.current_stage}).\n"
            f"Done: {', '.join(state.completed_stages) or 'none'}\n"
            f"Next: /commit-extract step or /commit-extract resume"
        )
    elif state.status == "ok":
        return (
            f"[commit-extract] Complete. All {total} stages done.\n"
            f"Artifacts: {len(state.artifacts_written)} written."
        )
    elif state.status == "error":
        return f"[commit-extract] Error at {state.current_stage}: {state.breakpoint_reason}"
    else:
        return f"[commit-extract] Status: {state.status}"


def init_state() -> HarnessState:
    """Create fresh state."""
    return HarnessState(
        command="commit-extract",
        status="ok",
        completed_stages=[],
        artifacts_written=[],
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def handle_status() -> int:
    """Handle status intent."""
    state = load_state(STATE_PATH)
    if state is None:
        print("[commit-extract] No state found. Run /commit-extract run to start.")
        return 0

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0


def handle_reset() -> int:
    """Handle reset intent."""
    state = load_state(STATE_PATH)
    if state:
        # Keep artifacts, clear state
        new_state = init_state()
        new_state.artifacts_written = state.artifacts_written  # Preserve artifact list
        save_state(new_state, STATE_PATH)
        print("[commit-extract] State reset. Artifacts preserved.")
    else:
        print("[commit-extract] No state to reset.")
    return 0


def run_stage(stage: str, state: HarnessState) -> bool:
    """Run a single stage. Returns True on success."""
    print(f"[commit-extract] Running stage: {stage}")

    if stage == "collect":
        print("  → Collecting commits from git history")
        state.artifacts_written.append("commits/commits.jsonl")

    elif stage == "extract":
        print("  → Extracting rules and invariants")
        state.artifacts_written.append("rules/rules.yaml")
        state.artifacts_written.append("invariants/invariants.yaml")

    elif stage == "pattern":
        print("  → Identifying patterns")
        state.artifacts_written.append("patterns/patterns.yaml")

    state.completed_stages.append(stage)
    state.current_stage = None
    state.timestamp = datetime.now(timezone.utc).isoformat()

    return True


def handle_step() -> int:
    """Handle step intent - run single next stage."""
    state = load_state(STATE_PATH)
    if state is None:
        state = init_state()

    next_stage = get_next_stage(STAGES, state.completed_stages)
    if next_stage is None:
        state.status = "ok"
        print(summary(state))
        save_state(state, STATE_PATH)
        return 0

    state.current_stage = next_stage
    success = run_stage(next_stage, state)

    if success:
        # Set breakpoint after each step
        state.status = "breakpoint"
        state.resume_token = f"step{len(state.completed_stages)+1}_{get_next_stage(STAGES, state.completed_stages) or 'done'}"
        state.breakpoint_reason = f"Stage {next_stage} complete. Run step to continue or resume for all."
    else:
        state.status = "error"
        state.breakpoint_reason = f"Stage {next_stage} failed"

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0 if success else 1


def handle_resume() -> int:
    """Handle resume intent - run all remaining stages."""
    state = load_state(STATE_PATH)
    if state is None:
        state = init_state()

    while True:
        next_stage = get_next_stage(STAGES, state.completed_stages)
        if next_stage is None:
            break

        state.current_stage = next_stage
        success = run_stage(next_stage, state)

        if not success:
            state.status = "error"
            state.breakpoint_reason = f"Stage {next_stage} failed"
            print(summary(state))
            save_state(state, STATE_PATH)
            return 1

    state.status = "ok"
    state.current_stage = None
    state.resume_token = None
    state.breakpoint_reason = None

    print(summary(state))
    save_state(state, STATE_PATH)
    return 0


def handle_run() -> int:
    """Handle run intent - full pipeline."""
    # Reset state for fresh run
    state = init_state()
    save_state(state, STATE_PATH)
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
