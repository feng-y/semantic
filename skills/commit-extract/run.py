#!/usr/bin/env python3
"""commit-extract skill implementation.

三角色单向数据流：Main Agent (orchestrator) → Worker Agent ×N → Merge (orchestrator)

Main agent 的 context 只有 SHA 列表 + stat 数字 + worker 完成状态。不接触任何 patch 内容。
Worker 逐个处理 SHA，按 docs/generate_commit.md prompt 分析，产出 JSON object 后立即 append。

Output:
  - data/commit-extract/YYYY-MM.jsonl
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner
from src.io_utils import load_jsonl, append_jsonl, save_json
from src.commit_semantic.git_utils import get_commit_list

logger = logging.getLogger(__name__)

OUTPUT_BASE = Path("data/commit-extract")
TMP_DIR = OUTPUT_BASE / "tmp"

# Adaptive batching constants
WEIGHT_BUDGET = 3000
MAX_COMMITS_PER_BATCH = 15
BINARY_FILE_WEIGHT = 500


def parse_stat(stat_output: str) -> int:
    """Parse git show --stat output to extract weight (insertions + deletions).

    Handles:
    - Normal: "N files changed, X insertions(+), Y deletions(-)"
    - Binary: "Bin X -> Y bytes" → fixed weight 500 per binary file
    - Empty commit: no summary line → weight 0
    - Missing insertions or deletions → treat as 0
    """
    weight = 0

    # Count binary files
    binary_count = len(re.findall(r'Bin \d+ -> \d+ bytes', stat_output))
    weight += binary_count * BINARY_FILE_WEIGHT

    # Parse summary line
    summary_match = re.search(
        r'(\d+) files? changed(?:, (\d+) insertions?\(\+\))?(?:, (\d+) deletions?\(-\))?',
        stat_output
    )
    if summary_match:
        insertions = int(summary_match.group(2) or 0)
        deletions = int(summary_match.group(3) or 0)
        weight += insertions + deletions

    return weight


def get_stat_weight(repo_path: str, sha: str) -> int:
    """Run git show --stat for a SHA and return its weight."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "show", "--stat", "--summary", sha],
            capture_output=True, text=True, check=True,
        )
        return parse_stat(result.stdout)
    except subprocess.CalledProcessError:
        return 0


def adaptive_batch(sha_weights: list[tuple[str, int]]) -> list[list[str]]:
    """Split SHAs into batches by weight budget and count cap.

    - accumulated_weight + next_weight > budget → flush
    - count >= max → flush
    - single commit > budget → solo batch
    """
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_weight = 0

    for sha, weight in sha_weights:
        # Single commit exceeds budget → solo batch
        if weight > WEIGHT_BUDGET:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_weight = 0
            batches.append([sha])
            continue

        # Would exceed budget or count cap → flush
        if (current_weight + weight > WEIGHT_BUDGET
                or len(current_batch) >= MAX_COMMITS_PER_BATCH):
            if current_batch:
                batches.append(current_batch)
            current_batch = [sha]
            current_weight = weight
        else:
            current_batch.append(sha)
            current_weight += weight

    if current_batch:
        batches.append(current_batch)

    return batches


def get_existing_shas(output_base: Path) -> set[str]:
    """Scan existing YYYY-MM.jsonl files to get already-processed SHAs."""
    existing = set()
    for jsonl_file in output_base.glob("*.jsonl"):
        if jsonl_file.parent.name == "tmp":
            continue
        try:
            for record in load_jsonl(str(jsonl_file)):
                if "sha" in record:
                    existing.add(record["sha"])
        except Exception as e:
            logger.warning("Error reading %s: %s", jsonl_file, e)
    return existing


def merge_tmp_files(output_base: Path, tmp_dir: Path) -> int:
    """Merge tmp/*.jsonl into YYYY-MM.jsonl files.

    - Dedup by sha (later overwrites earlier)
    - Skip invalid JSON lines
    - Incremental append to existing YYYY-MM.jsonl
    - Clean up tmp/
    """
    tmp_files = sorted(tmp_dir.glob("*.jsonl"))
    if not tmp_files:
        return 0

    # Collect all records, dedup by sha
    all_records: dict[str, dict] = {}
    for tmp_file in tmp_files:
        try:
            for record in load_jsonl(str(tmp_file), skip_errors=True):
                sha = record.get("sha")
                if sha:
                    all_records[sha] = record
        except Exception as e:
            logger.warning("Error reading tmp file %s: %s", tmp_file, e)

    if not all_records:
        return 0

    # Group by YYYY-MM from date field
    by_month: dict[str, list[dict]] = defaultdict(list)
    for record in all_records.values():
        date_str = record.get("date", "")
        if date_str and len(date_str) >= 7:
            month_key = date_str[:7]  # YYYY-MM
        else:
            month_key = "unknown"
        by_month[month_key].append(record)

    # Append to existing YYYY-MM.jsonl (skip already-existing SHAs)
    total_new = 0
    for month_key, records in sorted(by_month.items()):
        month_file = output_base / f"{month_key}.jsonl"
        existing_shas = set()
        if month_file.exists():
            for existing in load_jsonl(str(month_file), skip_errors=True):
                if "sha" in existing:
                    existing_shas.add(existing["sha"])

        new_records = [r for r in records if r["sha"] not in existing_shas]
        if new_records:
            append_jsonl(new_records, str(month_file))
            total_new += len(new_records)

    # Clean up tmp
    for tmp_file in tmp_files:
        tmp_file.unlink()
    try:
        tmp_dir.rmdir()
    except OSError:
        pass

    return total_new


class CommitExtractRunner(SkillRunner):
    """Runner for commit-extract pipeline with adaptive batching + LLM workers."""

    STAGES = ["collect"]
    PIPELINE = "commit-extract"

    def __init__(self):
        super().__init__()
        self.repo_path: str = "."
        self.commit_range: str | None = None
        self._prompt_content: str | None = None

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        if stage == "collect":
            return self._run_collect(state)
        return True

    def _get_prompt(self) -> str:
        """Load docs/generate_commit.md prompt."""
        if self._prompt_content is None:
            prompt_path = Path("docs/generate_commit.md")
            if prompt_path.exists():
                self._prompt_content = prompt_path.read_text(encoding="utf-8")
            else:
                self._prompt_content = ""
        return self._prompt_content

    def _build_worker_prompt(self, shas: list[str]) -> str:
        """Build the full worker prompt: prefix instructions + generate_commit.md."""
        prompt = self._get_prompt()
        sha_list = "\n".join(f"- {sha}" for sha in shas)
        prefix = (
            "You are a commit analysis worker. Process the following SHA list one by one.\n"
            "For each SHA:\n"
            "1. Run: git show --stat --summary {sha}\n"
            "2. Run: git show {sha}\n"
            "3. Analyze the patch according to the prompt rules below\n"
            "4. Output exactly one JSON object\n"
            "5. Append the JSON object as one line to the output file\n\n"
            "Process each SHA independently. Do not accumulate patch content in context.\n\n"
            f"## SHA List\n\n{sha_list}\n\n"
            "## Analysis Prompt\n\n"
        )
        return prefix + prompt

    def _run_collect(self, state: HarnessState) -> bool:
        """Orchestrator: SHA collection → stat estimation → adaptive batching → worker manifest."""
        print(f"\n[{self.PIPELINE}] Collecting commits")
        print(f"  Repo: {self.repo_path}")
        print(f"  Range: {self.commit_range or 'all'}")

        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

        # 1. Get SHA list (no merges)
        all_shas = get_commit_list(
            repo_path=self.repo_path,
            commit_range=self.commit_range,
            no_merges=True,
        )
        print(f"  Found {len(all_shas)} commits (excluding merges)")

        if not all_shas:
            print("  No commits to process")
            return True

        # 2. Resume: exclude already-processed SHAs
        existing_shas = get_existing_shas(OUTPUT_BASE)
        new_shas = [s for s in all_shas if s not in existing_shas]
        if existing_shas:
            print(f"  Already processed: {len(existing_shas)}, new: {len(new_shas)}")

        if not new_shas:
            print("  All commits already processed")
            return True

        # 3. Check for interrupted tmp files → merge first
        if TMP_DIR.exists() and next(TMP_DIR.glob("*.jsonl"), None) is not None:
            print("  Found interrupted tmp files, merging first...")
            merged = merge_tmp_files(OUTPUT_BASE, TMP_DIR)
            print(f"  Merged {merged} records from previous run")
            # Update existing set incrementally instead of re-scanning
            existing_shas = get_existing_shas(OUTPUT_BASE)
            new_shas = [s for s in all_shas if s not in existing_shas]
            if not new_shas:
                print("  All commits now processed after merge")
                return True

        # 4. Weight estimation via git show --stat
        print(f"  Estimating weights for {len(new_shas)} commits...")
        sha_weights = []
        for sha in new_shas:
            weight = get_stat_weight(self.repo_path, sha)
            sha_weights.append((sha, weight))

        # 5. Adaptive batching
        batches = adaptive_batch(sha_weights)
        print(f"  Created {len(batches)} batches")

        # 6. Create batch manifest for workers
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        prompt_content = self._get_prompt()
        manifest = {
            "repo_path": self.repo_path,
            "total_shas": len(new_shas),
            "total_batches": len(batches),
            "prompt": prompt_content,
            "batches": [],
        }

        for i, batch_shas in enumerate(batches):
            batch_id = f"batch_{i:04d}"
            output_path = str(TMP_DIR / f"{batch_id}.jsonl")

            manifest["batches"].append({
                "batch_id": batch_id,
                "shas": batch_shas,
                "output_path": output_path,
            })

            print(f"  Batch {i}: {len(batch_shas)} SHAs → {output_path}")

        # Save manifest for agent context
        manifest_path = str(TMP_DIR / "manifest.json")
        save_json(manifest, manifest_path)
        print(f"\n  Manifest written to {manifest_path}")
        print(f"  Workers should write to {TMP_DIR}/batch_NNNN.jsonl")
        print(f"  After all workers complete, run merge to consolidate.")

        self.add_artifact(state, str(OUTPUT_BASE))
        return True

    def handle_merge(self) -> int:
        """Merge tmp files after workers complete."""
        if not TMP_DIR.exists():
            print(f"[{self.PIPELINE}] No tmp directory found")
            return 0

        merged = merge_tmp_files(OUTPUT_BASE, TMP_DIR)
        print(f"[{self.PIPELINE}] Merged {merged} new records")
        return 0

    def handle_run(self, remaining: list[str] | None = None) -> int:
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--repo", default=".")
        parser.add_argument("--range", help="Commit range (e.g. HEAD~10..HEAD)")
        parser.add_argument("--merge", action="store_true", help="Merge tmp files only")
        args = parser.parse_args(argv)

        if args.merge:
            return self.handle_merge()

        self.repo_path = args.repo
        self.commit_range = args.range

        return super().handle_run()


def run_commit_extract() -> None:
    """Entry point for the commit-extract skill."""
    raise SystemExit(CommitExtractRunner().main())


if __name__ == "__main__":
    run_commit_extract()
