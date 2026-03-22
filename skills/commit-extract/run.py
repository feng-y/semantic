#!/usr/bin/env python3
"""commit-extract skill implementation.

Orchestrator for the Team Agent pattern:
  - Collects SHAs from git history
  - Estimates patch weight via git show --stat
  - Produces adaptive batches (weight budget + count cap)
  - Prints batch manifest for the main agent to spawn workers

Workers (spawned by SKILL.md via Task tool) write to data/commit-extract/tmp/{batch_id}.jsonl.
Merge Agent (spawned after workers) deduplicates and groups by month into YYYY-MM.jsonl.

Stages:
  1. collect  - SHA collection + stat estimation + adaptive batching
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner

from src.commit_semantic.git_utils import get_commit_list
from src.io_utils import load_jsonl


EXTRACT_OUTPUT = Path("data/commit-extract")

WEIGHT_BUDGET = 3000
MAX_COMMITS_PER_BATCH = 15


def _parse_stat_weight(stat_output: str) -> int:
    """Parse git show --stat output and return total weight (insertions + deletions).

    Rules:
    - Summary line: "N files changed, X insertions(+), Y deletions(-)" -> X + Y
    - Missing insertions or deletions -> treat as 0
    - Binary files "Bin X -> Y bytes" -> fixed weight 500 each
    - No summary line (empty commit) -> weight 0
    """
    lines = stat_output.splitlines()

    # Count binary file lines
    binary_count = sum(
        1 for line in lines if re.search(r'\bBin\b.*->', line)
    )

    # Find summary line (last non-empty line typically)
    summary_line = ""
    for line in reversed(lines):
        line = line.strip()
        if "file" in line and "changed" in line:
            summary_line = line
            break

    if not summary_line:
        return binary_count * 500

    insertions = 0
    deletions = 0

    m = re.search(r'(\d+)\s+insertion', summary_line)
    if m:
        insertions = int(m.group(1))

    m = re.search(r'(\d+)\s+deletion', summary_line)
    if m:
        deletions = int(m.group(1))

    return insertions + deletions + binary_count * 500


def _get_stat_weight(repo_path: str, sha: str) -> int:
    """Run git show --stat for a SHA and return its weight."""
    cmd = ["git", "-C", repo_path, "show", "--stat", sha]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return _parse_stat_weight(result.stdout)
    except subprocess.CalledProcessError:
        return 0


def _collect_processed_shas(output_dir: Path) -> set[str]:
    """Scan existing YYYY-MM.jsonl files and return all already-processed SHAs."""
    processed: set[str] = set()
    for jsonl_file in output_dir.glob("????-??.jsonl"):
        try:
            for record in load_jsonl(str(jsonl_file), skip_errors=True):
                sha = record.get("sha")
                if sha:
                    processed.add(sha)
        except OSError:
            pass
    return processed


def _make_batches(
    shas: list[str],
    weights: dict[str, int],
    weight_budget: int = WEIGHT_BUDGET,
    max_per_batch: int = MAX_COMMITS_PER_BATCH,
) -> list[list[str]]:
    """Adaptive batching: group SHAs by weight budget and count cap."""
    batches: list[list[str]] = []
    current: list[str] = []
    accumulated = 0

    for sha in shas:
        w = weights.get(sha, 0)

        # Flush current batch if adding this SHA would exceed budget or count cap
        if current and (accumulated + w > weight_budget or len(current) >= max_per_batch):
            batches.append(current)
            current = []
            accumulated = 0

        current.append(sha)
        accumulated += w

    if current:
        batches.append(current)

    return batches


class CommitExtractRunner(SkillRunner):
    """Orchestrator for commit-extract pipeline (Team Agent pattern)."""

    STAGES = ["collect"]
    PIPELINE = "commit-extract"

    def __init__(self):
        super().__init__()
        self.repo_path: str = "."
        self.commit_range: str | None = None

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        if stage == "collect":
            return self._run_collect(state)
        return True

    def _run_collect(self, state: HarnessState) -> bool:
        """Collect SHAs, estimate weights, produce adaptive batch manifest."""
        print("  -> Collecting commits from git history")
        print(f"     Repo: {self.repo_path}")
        print(f"     Range: {self.commit_range or 'all'}")

        # Ensure output directories exist
        EXTRACT_OUTPUT.mkdir(parents=True, exist_ok=True)
        tmp_dir = EXTRACT_OUTPUT / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)

        # Get full SHA list (no merge commits)
        try:
            all_shas = get_commit_list(
                repo_path=self.repo_path,
                commit_range=self.commit_range,
                no_merges=True,
            )
        except RuntimeError as e:
            if "does not have any commits" in str(e):
                print("     No commits found (empty repository).")
                self.add_artifact(state, str(EXTRACT_OUTPUT))
                return True
            raise
        print(f"     Found {len(all_shas)} commits (excluding merges)")

        if not all_shas:
            print("     No commits to process.")
            self.add_artifact(state, str(EXTRACT_OUTPUT))
            return True

        # Resume: exclude already-processed SHAs
        processed = _collect_processed_shas(EXTRACT_OUTPUT)
        if processed:
            print(f"     Skipping {len(processed)} already-processed SHAs")
        shas = [s for s in all_shas if s not in processed]
        print(f"     New commits to process: {len(shas)}")

        if not shas:
            print("     All commits already processed.")
            self.add_artifact(state, str(EXTRACT_OUTPUT))
            return True

        # Estimate weights via git show --stat
        print("  -> Estimating patch weights...")
        weights: dict[str, int] = {}
        for sha in shas:
            weights[sha] = _get_stat_weight(self.repo_path, sha)

        # Adaptive batching
        batches = _make_batches(shas, weights)
        print(f"  -> Created {len(batches)} batch(es)")

        # Build manifest
        manifest = []
        for batch_shas in batches:
            batch_id = str(uuid.uuid4())[:8]
            output_path = str(tmp_dir / f"{batch_id}.jsonl")
            manifest.append({
                "batch_id": batch_id,
                "shas": batch_shas,
                "output_path": output_path,
            })

        # Print manifest for the main agent to spawn workers
        print("\n=== BATCH MANIFEST ===")
        print(json.dumps(manifest, indent=2))
        print("=== END MANIFEST ===\n")

        self.add_artifact(state, str(EXTRACT_OUTPUT))
        return True

    def handle_run(self, remaining: list[str] | None = None) -> int:
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--repo", default=".")
        parser.add_argument("--range", help="Commit range")
        args = parser.parse_args(argv)

        self.repo_path = args.repo
        self.commit_range = args.range

        return super().handle_run()


def run_commit_extract() -> None:
    """Entry point for the commit-extract skill."""
    raise SystemExit(CommitExtractRunner().main())


if __name__ == "__main__":
    run_commit_extract()
