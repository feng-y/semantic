"""Base class for harness skills with unified state management."""

from __future__ import annotations

import argparse
import sys
from abc import ABC, abstractmethod
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.harness_state import HarnessState, load_state, save_state
from src.intent_router import parse_intent


class SkillRunner(ABC):
    """Base class for harness skills.

    Subclasses define STAGES and implement run_stage().
    Handles: status, reset, step, resume, run intents.
    """

    STAGES: list[str] = []
    PIPELINE: str = ""

    def __init__(self) -> None:
        if not self.PIPELINE:
            raise ValueError(f"{self.__class__.__name__}.PIPELINE must be set")
        if not self.STAGES:
            raise ValueError(f"{self.__class__.__name__}.STAGES must be set")

    def get_completed(self, state: HarnessState) -> list[str]:
        return state.metadata.get("completed_stages", [])

    def get_status(self, state: HarnessState) -> str:
        return state.metadata.get("status", "ok")

    def get_current(self, state: HarnessState) -> str | None:
        return state.metadata.get("current_stage")

    def get_artifacts(self, state: HarnessState) -> list[str]:
        return state.metadata.get("artifacts_written", [])

    def add_artifact(self, state: HarnessState, path: str) -> None:
        """Add an artifact path to state. Modifies in-place."""
        self.get_artifacts(state).append(path)

    @abstractmethod
    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Run a single stage. Subclasses implement this."""
        ...

    def summary(self, state: HarnessState) -> str:
        """Generate human-readable summary."""
        completed = self.get_completed(state)
        status = self.get_status(state)
        current = self.get_current(state)
        total = len(self.STAGES)
        done = len(completed)

        if status == "breakpoint":
            return (
                f"[{self.PIPELINE}] Breakpoint at stage {done+1}/{total} ({current}).\n"
                f"Done: {', '.join(completed) or 'none'}\n"
                f"Next: /{self.PIPELINE} step or /{self.PIPELINE} resume"
            )
        elif status == "ok" and done >= total:
            return (
                f"[{self.PIPELINE}] Complete. All {total} stages done.\n"
                f"Artifacts: {len(self.get_artifacts(state))} written."
            )
        elif status == "error":
            reason = state.metadata.get("breakpoint_reason", "unknown error")
            return f"[{self.PIPELINE}] Error at {current}: {reason}"
        else:
            return f"[{self.PIPELINE}] Status: {status}"

    def init_state(self) -> HarnessState:
        return HarnessState(
            stage="init",
            metadata={
                "completed_stages": [],
                "artifacts_written": [],
                "status": "ok",
            },
        )

    def is_fresh(self, state: HarnessState) -> bool:
        return state.stage == "init" and not self.get_completed(state)

    def get_next_stage(self, state: HarnessState) -> str | None:
        completed = self.get_completed(state)
        for s in self.STAGES:
            if s not in completed:
                return s
        return None

    def handle_status(self) -> int:
        state = load_state(self.PIPELINE)
        if self.is_fresh(state):
            print(f"[{self.PIPELINE}] No state found. Run /{self.PIPELINE} run to start.")
            return 0
        print(self.summary(state))
        return 0

    def handle_reset(self) -> int:
        state = load_state(self.PIPELINE)
        if not self.is_fresh(state):
            old_artifacts = self.get_artifacts(state)
            new_state = self.init_state()
            new_state.metadata["artifacts_written"] = old_artifacts
            save_state(self.PIPELINE, new_state)
            print(f"[{self.PIPELINE}] State reset. Artifacts preserved.")
        else:
            print(f"[{self.PIPELINE}] No state to reset.")
        return 0

    def _advance(self, state: HarnessState) -> tuple[bool, str]:
        """Run next stage. Returns (success, error_message)."""
        next_stage = self.get_next_stage(state)
        if next_stage is None:
            return True, ""

        state.metadata["current_stage"] = next_stage
        try:
            success = self.run_stage(next_stage, state)
            if success:
                # Append directly - get_completed returns the list reference
                self.get_completed(state).append(next_stage)
                state.metadata["current_stage"] = None
                state.stage = next_stage
            return success, f"Stage {next_stage} failed"
        except Exception as e:
            return False, str(e)

    def handle_step(self) -> int:
        state = load_state(self.PIPELINE)
        if self.is_fresh(state):
            state = self.init_state()

        next_stage = self.get_next_stage(state)
        if next_stage is None:
            state.metadata["status"] = "ok"
            print(self.summary(state))
            save_state(self.PIPELINE, state)
            return 0

        success, error = self._advance(state)

        if success:
            # Cache completed count to avoid repeated lookups
            completed_count = len(self.get_completed(state))
            state.metadata["status"] = "breakpoint"
            next_remaining = self.STAGES[completed_count] if completed_count < len(self.STAGES) else "done"
            state.metadata["resume_token"] = f"step{completed_count}_{next_remaining}"
            state.metadata["breakpoint_reason"] = f"Stage {next_stage} complete. Run step to continue or resume for all."
        else:
            state.metadata["status"] = "error"
            state.metadata["breakpoint_reason"] = error

        print(self.summary(state))
        save_state(self.PIPELINE, state)
        return 0 if success else 1

    def handle_resume(self) -> int:
        state = load_state(self.PIPELINE)
        if self.is_fresh(state):
            state = self.init_state()

        while True:
            success, error = self._advance(state)
            if not success:
                state.metadata["status"] = "error"
                state.metadata["breakpoint_reason"] = error
                print(self.summary(state))
                save_state(self.PIPELINE, state)
                return 1

            if self.get_next_stage(state) is None:
                break

        state.metadata["status"] = "ok"
        state.metadata["current_stage"] = None
        state.metadata["resume_token"] = None
        state.metadata["breakpoint_reason"] = None
        state.stage = "complete"

        print(self.summary(state))
        save_state(self.PIPELINE, state)
        return 0

    def handle_run(self) -> int:
        state = self.init_state()
        save_state(self.PIPELINE, state)
        return self.handle_resume()

    def main(self, argv: list[str] | None = None) -> int:
        parser = argparse.ArgumentParser(description=f"{self.PIPELINE} skill")
        parser.add_argument("intent", nargs="?", default="run")
        args = parser.parse_args(argv)

        intent = parse_intent([self.PIPELINE, args.intent])

        handlers = {
            "status": self.handle_status,
            "reset": self.handle_reset,
            "step": self.handle_step,
            "resume": self.handle_resume,
            "run": self.handle_run,
        }

        handler = handlers.get(intent, self.handle_run)
        return handler()


def run_skill(skill_class: type[SkillRunner]) -> None:
    """Entry point for skill scripts."""
    raise SystemExit(skill_class().main())
