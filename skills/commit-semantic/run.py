#!/usr/bin/env python3
"""commit-semantic skill implementation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill

EXTRACT_OUTPUT = Path(".harness/outputs/commit-extract")


class CommitSemanticRunner(SkillRunner):
    """Runner for commit-semantic pipeline."""

    STAGES = ["analyze", "domain-map", "feed"]
    PIPELINE = "commit-semantic"

    def _check_prerequisites(self) -> tuple[bool, str]:
        """Check if commit-extract output exists."""
        if not EXTRACT_OUTPUT.exists():
            return False, f"commit-extract output not found at {EXTRACT_OUTPUT}. Run /commit-extract first."
        return True, ""

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"[{self.PIPELINE}] Running stage: {stage}")

        artifacts = self.get_artifacts(state)

        if stage == "analyze":
            print("  → Analyzing commit patterns")
            artifacts.append("patterns/pattern-analysis.yaml")

        elif stage == "domain-map":
            print("  → Mapping patterns to semantic domains")
            artifacts.append("domains/domain-mapping.yaml")

        elif stage == "feed":
            print("  → Preparing demand pipeline feed")
            artifacts.append("domains/demand-feed.yaml")

        state.metadata["artifacts_written"] = artifacts
        return True

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
    run_skill(CommitSemanticRunner)
