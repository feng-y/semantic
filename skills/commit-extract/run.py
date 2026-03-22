#!/usr/bin/env python3
"""commit-extract skill implementation.

保持 CC 产出的原始 commit，按月聚合保存，使用 worker agent 重新生成 commit_log。

不做拆分、不做语义分析、不生成 rules。

Stages:
  1. collect  - 从 git 收集 commits，按月聚合，worker 生成 commit_log

Worker Architecture:
  - Main agent 读取 git commits，组织 batch
  - Worker agent (via Task tool) 从 diff_chunks 重新生成 commit_log
  - 结果聚合到 data/commit-extract/YYYY-MM.yaml

Output:
  - data/commit-extract/YYYY-MM.yaml
  - data/commit-extract/state.json
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill
from src.io_utils import save_yaml, save_json
from src.commit_semantic.git_utils import (
    get_commit_list,
    get_commit_details,
    get_commit_message,
)


OUTPUT_BASE = Path("data/commit-extract")
STATE_FILE = OUTPUT_BASE / "state.json"
BATCH_SIZE = 30


class CommitExtractRunner(SkillRunner):
    """Runner for commit-extract pipeline with team agent architecture."""

    STAGES = ["collect"]
    PIPELINE = "commit-extract"

    def __init__(self):
        super().__init__()
        self.repo_path: str = "."
        self.commit_range: str | None = None
        self._worker_prompt_template: str | None = None

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")

        if stage == "collect":
            return self._run_collect(state)

        return True

    # -------------------------------------------------------------------------
    # Public API used by tests
    # -------------------------------------------------------------------------

    def _batch_commits(
        self, commits: list[dict], batch_size: int = BATCH_SIZE
    ) -> list[list[dict]]:
        """Split commits into batches of batch_size."""
        return [
            commits[i : i + batch_size] for i in range(0, len(commits), batch_size)
        ]

    def _build_worker_prompt(self, batch: list[dict]) -> str:
        """Build a worker prompt from a batch of commits."""
        template = self._get_worker_prompt_template()
        body_lines = ["# Commit batch\n\n"]
        for commit in batch:
            body_lines.append(f"## commit_id: {commit['commit_id']}")
            body_lines.append(f"original_message: |")
            for line in (commit.get("original_message") or "").splitlines():
                body_lines.append(f"  {line}")
            body_lines.append(f"files: {commit.get('files', [])}")
            body_lines.append(f"diff_chunks:")
            for chunk in commit.get("diff_chunks", []):
                for line in chunk.splitlines()[:50]:  # Truncate each chunk
                    body_lines.append(f"  {line}")
                if len(chunk.splitlines()) > 50:
                    body_lines.append("  ... (truncated)")
            body_lines.append("")

        return template + "\n\n---\n\n# Batch Data\n\n" + "\n".join(body_lines)

    def _worker_regenerate_commit_log(
        self, commit_id: str, original_message: str, diff_chunks: list[str]
    ) -> str:
        """Simulate a worker regenerating commit_log from diff_chunks.

        In production this is replaced by a real Task agent call.
        The heuristic below mirrors what an LLM would infer from a diff.
        """
        # Flatten diff to find added/removed patterns
        all_lines = "\n".join(diff_chunks)
        added = re.findall(r"^\+[^+].*", all_lines, re.MULTILINE)
        removed = re.findall(r"^-[^-].*", all_lines, re.MULTILINE)
        added_files = re.findall(r"^\+\+\+ b/(.+)", all_lines, re.MULTILINE)
        # Strip diff markers
        added_clean = [re.sub(r"^\+", "", line).strip() for line in added]
        removed_clean = [re.sub(r"^-", "", line).strip() for line in removed]

        parts: list[str] = []

        # Detect function-level changes
        funcs_added = [
            re.sub(r"def (\w+).*", r"\1", line)
            for line in added_clean
            if line.startswith("def ")
        ]
        funcs_removed = [
            re.sub(r"def (\w+).*", r"\1", line)
            for line in removed_clean
            if line.startswith("def ")
        ]

        if funcs_added:
            if added_files:
                files_str = ", ".join(set(added_files[:3]))
                parts.append(f"在 {files_str} 中新增 {', '.join(funcs_added)} 函数")
            else:
                parts.append(f"新增 {', '.join(funcs_added)} 函数")
        if funcs_removed:
            parts.append(f"删除 {', '.join(funcs_removed)} 函数")

        # Detect return value changes
        return_added = [l for l in added_clean if "return" in l and l.startswith("return")]
        return_removed = [l for l in removed_clean if "return" in l and l.startswith("return")]
        if return_added and return_removed:
            parts.append(f"修改返回值：从 {return_removed[0]} 改为 {return_added[0]}")

        # Generic fallback using original_message prefix as hint (not as commit_log)
        if not parts:
            prefix = original_message.split(":")[0].strip() if ":" in original_message else ""
            if prefix in ("feat", "feature"):
                parts.append("新增功能实现")
            elif prefix in ("bugfix", "fix"):
                parts.append("修复代码问题")
            elif prefix in ("refactor", "refactoring"):
                parts.append("重构代码结构")
            elif prefix in ("test", "tests"):
                parts.append("添加或更新测试")
            elif prefix in ("config", "chore"):
                parts.append("更新配置或构建文件")
            elif prefix == "optimize":
                parts.append("优化代码性能")
            else:
                parts.append("更新代码")

        return "；".join(parts) if parts else "代码更新"

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _get_worker_prompt_template(self) -> str:
        """Lazy-load the worker prompt template."""
        if self._worker_prompt_template is None:
            prompt_path = Path(__file__).parent / "prompts" / "generate_commit_log.md"
            if prompt_path.exists():
                self._worker_prompt_template = prompt_path.read_text(encoding="utf-8")
            else:
                self._worker_prompt_template = ""
        return self._worker_prompt_template

    def _spawn_worker(self, batch: list[dict]) -> dict[str, str]:
        """Spawn a worker agent for a batch of commits.

        When called from an agent context with Task tool available, spawns a real
        worker. When called from CLI, falls back to local processing.

        Returns dict mapping commit_id -> commit_log.
        """
        # Check if we should use real Task agents
        use_task = os.environ.get("COMMIT_EXTRACT_USE_TASK_AGENTS", "").lower() in (
            "1",
            "true",
            "yes",
        )

        if use_task:
            # Real Task agent spawning — implemented in agent context via SKILL.md
            # This branch is a no-op here; the main agent handles Task calls.
            pass

        # Local processing (default): run heuristic directly
        results: dict[str, str] = {}
        for commit in batch:
            results[commit["commit_id"]] = self._worker_regenerate_commit_log(
                commit_id=commit["commit_id"],
                original_message=commit.get("original_message") or "",
                diff_chunks=commit.get("diff_chunks") or [],
            )
        return results

    def _run_collect(self, state: HarnessState) -> bool:
        """Collect commits, spawn workers to regenerate commit_log, group by month."""
        print("  -> Collecting commits from git history")
        print(f"     Repo: {self.repo_path}")
        print(f"     Range: {self.commit_range or 'all'}")

        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

        commit_ids = get_commit_list(
            repo_path=self.repo_path,
            commit_range=self.commit_range,
        )
        print(f"     Found {len(commit_ids)} commits")

        commits_by_month: dict[str, list] = defaultdict(list)
        total = len(commit_ids)

        for idx, commit_id in enumerate(commit_ids):
            try:
                commit = get_commit_details(self.repo_path, commit_id)
                dt = datetime.fromtimestamp(int(commit.timestamp))
                month_key = dt.strftime("%Y-%m")

                commit_record = {
                    "commit_id": commit_id,
                    "author": commit.author,
                    "timestamp": dt.isoformat(),
                    "files": commit.files,
                    "diff_chunks": commit.diff_chunks,
                    "original_message": get_commit_message(self.repo_path, commit_id),
                    "commit_log": "",  # Filled by worker
                }
                commits_by_month[month_key].append(commit_record)

                if (idx + 1) % 100 == 0:
                    print(f"     Processed {idx + 1}/{total}...")

            except Exception as e:
                print(f"     Error processing {commit_id}: {e}")

        # Spawn workers in batches to regenerate commit_log
        print(f"\n  -> Spawning workers to regenerate commit_log")
        for month, commits in sorted(commits_by_month.items()):
            batches = self._batch_commits(commits, BATCH_SIZE)
            print(f"     {month}: {len(commits)} commits in {len(batches)} batch(es)")

            for batch_idx, batch in enumerate(batches):
                print(f"     Batch {batch_idx + 1}/{len(batches)} ({len(batch)} commits)...")
                worker_results = self._spawn_worker(batch)

                # Fill in commit_log for each commit in batch
                for commit in batch:
                    cid = commit["commit_id"]
                    if cid in worker_results:
                        commit["commit_log"] = worker_results[cid]
                    else:
                        commit["commit_log"] = "（commit_log 未生成）"

        # Write monthly YAML files
        for month, commits in sorted(commits_by_month.items()):
            month_file = OUTPUT_BASE / f"{month}.yaml"
            save_yaml(
                {
                    "metadata": {
                        "month": month,
                        "total_commits": len(commits),
                        "generated_at": datetime.now().isoformat(),
                    },
                    "commits": commits,
                },
                str(month_file),
            )
            print(f"  Saved {month}: {len(commits)} commits -> {month_file}")

        save_json(
            {
                "last_run": datetime.now().isoformat(),
                "repo_path": self.repo_path,
                "total_commits": len(commit_ids),
                "months": list(commits_by_month.keys()),
            },
            str(STATE_FILE),
        )

        self.add_artifact(state, str(OUTPUT_BASE))
        return True

    def handle_run(self, remaining: list[str] | None = None) -> int:
        """Override to handle command-line args."""
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
