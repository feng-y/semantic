#!/usr/bin/env python3
"""commit-extract skill implementation.

保持 CC 产出的原始 commit，按月聚合保存。
不做拆分、不做语义分析、不生成 rules。

Stages:
  1. collect  - 从 git 收集 commits，按月聚合

Output:
  - data/commit-extract/YYYY-MM.yaml
      commits: []  # 原始 commit log
  - data/commit-extract/state.json
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill
from src.io_utils import save_yaml, save_json
from src.commit_semantic.git_utils import get_commit_list, get_commit_details
from src.commit_semantic.state_tracker import StateTracker


OUTPUT_BASE = Path("data/commit-extract")
STATE_FILE = OUTPUT_BASE / "state.json"


class CommitExtractRunner(SkillRunner):
    """Runner for commit-extract pipeline."""

    STAGES = ["collect"]
    PIPELINE = "commit-extract"

    def __init__(self):
        super().__init__()
        self.repo_path: str = "."
        self.commit_range: str | None = None
        self.incremental: bool = False

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")

        if stage == "collect":
            return self._run_collect(state)

        return True

    def _run_collect(self, state: HarnessState) -> bool:
        """Collect commits and group by month."""
        print("  → Collecting commits from git history")
        print(f"     Repo: {self.repo_path}")
        print(f"     Range: {self.commit_range or 'all'}")

        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

        # Get commit list
        commit_ids = get_commit_list(
            repo_path=self.repo_path,
            commit_range=self.commit_range
        )
        print(f"     Found {len(commit_ids)} commits")

        # Group by month
        commits_by_month: dict[str, list] = {}

        for idx, commit_id in enumerate(commit_ids):
            try:
                # Get commit details
                commit = get_commit_details(self.repo_path, commit_id)

                # Parse timestamp to month key
                ts = int(commit.timestamp)
                dt = datetime.fromtimestamp(ts)
                month_key = dt.strftime("%Y-%m")

                # Build commit record (保持原始)
                commit_record = {
                    "commit_id": commit_id,
                    "author": commit.author,
                    "timestamp": dt.isoformat(),
                    "files": commit.files,
                    "diff_chunks": commit.diff_chunks,
                    # 原始 commit message（不是 LLM 生成的）
                    "commit_message": commit.message if hasattr(commit, 'message') else "",
                }

                if month_key not in commits_by_month:
                    commits_by_month[month_key] = []
                commits_by_month[month_key].append(commit_record)

                if (idx + 1) % 100 == 0:
                    print(f"     Processed {idx + 1}/{len(commit_ids)}...")

            except Exception as e:
                print(f"     Error processing {commit_id}: {e}")

        # Save by month
        for month, commits in sorted(commits_by_month.items()):
            month_file = OUTPUT_BASE / f"{month}.yaml"
            save_yaml({
                "metadata": {
                    "month": month,
                    "total_commits": len(commits),
                    "generated_at": datetime.now().isoformat()
                },
                "commits": commits
            }, str(month_file))
            print(f"  Saved {month}: {len(commits)} commits → {month_file}")

        # Save state
        save_json({
            "last_run": datetime.now().isoformat(),
            "repo_path": self.repo_path,
            "total_commits": len(commit_ids),
            "months": list(commits_by_month.keys())
        }, str(STATE_FILE))

        self.add_artifact(state, str(OUTPUT_BASE))
        return True

    def handle_run(self, argv: list[str] | None = None) -> int:
        """Override to handle command-line args."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--repo", default=".")
        parser.add_argument("--range", help="Commit range")
        parser.add_argument("--incremental", action="store_true")
        args = parser.parse_args(argv)

        self.repo_path = args.repo
        self.commit_range = args.range
        self.incremental = args.incremental

        return super().handle_run()


if __name__ == "__main__":
    run_skill(CommitExtractRunner)
