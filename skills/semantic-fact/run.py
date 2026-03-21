#!/usr/bin/env python3
"""semantic-fact skill implementation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill

BASELINE_DIR = Path("docs/fact/baseline")


class SemanticFactRunner(SkillRunner):
    """Runner for semantic-fact pipeline."""

    STAGES = ["discover", "review", "refine", "baseline"]
    PIPELINE = "semantic-fact"

    def _check_prerequisites(self) -> tuple[bool, str]:
        """Check if fact baseline exists."""
        if not BASELINE_DIR.exists():
            return False, f"Fact baseline not found at {BASELINE_DIR}. Run fact pipeline first."

        baseline_files = list(BASELINE_DIR.glob("*.md"))
        if not baseline_files:
            return False, f"No accepted baseline found in {BASELINE_DIR}. Complete fact pipeline first."

        return True, ""

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage via dispatcher."""
        print(f"[{self.PIPELINE}] Running stage: {stage}")

        # Import here to avoid circular dependency
        from src.dispatcher import dispatch

        try:
            if stage == "discover":
                print("  → Discovering repo facts")
                result = dispatch("discover", ".")
                if result.get("status") != "ok":
                    state.metadata["error"] = result.get("error", "discover failed")
                    return False
                self.add_artifact(state, "discovery/repo-facts.yaml")

            elif stage == "review":
                print("  → Reviewing extracted facts")
                # Review is human-in-the-loop, set breakpoint
                self.add_artifact(state, "review/architect-feedback.md")

            elif stage == "refine":
                print("  → Refining based on feedback")
                result = dispatch("refine", ".")
                if result.get("status") != "ok":
                    state.metadata["error"] = result.get("error", "refine failed")
                    return False
                self.add_artifact(state, "refine/repo-understanding.patch")

            elif stage == "baseline":
                print("  → Accepting baseline")
                self.add_artifact(state, "baseline/accepted-baseline.md")

            state.metadata["dispatcher_result"] = {"stage": stage, "status": "ok"}
            return True

        except Exception as e:
            state.metadata["error"] = str(e)
            return False

    def handle_step(self) -> int:
        """Override to add prerequisites check."""
        ok, msg = self._check_prerequisites()
        if not ok:
            print(f"[{self.PIPELINE}] Prerequisites not met: {msg}")
            return 1
        return super().handle_step()

    def handle_resume(self) -> int:
        """Override to add prerequisites check."""
        ok, msg = self._check_prerequisites()
        if not ok:
            print(f"[{self.PIPELINE}] Prerequisites not met: {msg}")
            return 1
        return super().handle_resume()


if __name__ == "__main__":
    run_skill(SemanticFactRunner)
