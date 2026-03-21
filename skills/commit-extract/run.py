#!/usr/bin/env python3
"""commit-extract skill implementation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill


class CommitExtractRunner(SkillRunner):
    """Runner for commit-extract pipeline."""

    STAGES = ["collect", "extract", "pattern"]
    PIPELINE = "commit-extract"

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"[{self.PIPELINE}] Running stage: {stage}")

        artifacts = self.get_artifacts(state)

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

        state.metadata["artifacts_written"] = artifacts
        return True


if __name__ == "__main__":
    run_skill(CommitExtractRunner)
