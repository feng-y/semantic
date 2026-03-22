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
from src.skill_runner import SkillRunner
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
            body_lines.append("original_message: |")
            for line in (commit.get("original_message") or "").splitlines():
                body_lines.append(f"  {line}")
            body_lines.append(f"files: {commit.get('files', [])}")
            body_lines.append("diff_chunks:")
            for chunk in commit.get("diff_chunks", []):
                for line in chunk.splitlines()[:50]:  # Truncate each chunk
                    body_lines.append(f"  {line}")
                if len(chunk.splitlines()) > 50:
                    body_lines.append("  ... (truncated)")
            body_lines.append("")

        return template + "\n\n---\n\n# Batch Data\n\n" + "\n".join(body_lines)

    # Map from file path prefix to readable module name
    _MODULE_ALIASES = {
        "skills/": "技能模块",
        "src/": "核心模块",
        "tests/": "测试模块",
        "docs/": "文档模块",
        ".github/": "CI配置",
        ".claude-plugin/": "插件配置",
    }
    _META_PREFIXES = {
        "chore", "ci", "docs", "style", "build", "perf", "typo",
        "merge", "release",
    }
    _CODE_PREFIXES = {
        "feat", "feature", "fix", "bugfix", "refactor", "test",
        "perf", "optimize", "security",
    }

    def _worker_regenerate_commit_log(
        self, commit_id: str, original_message: str, diff_chunks: list[str]
    ) -> str:
        """Regenerate commit_log from diff_chunks using heuristics.

        Better heuristic approach:
        1. Extract structural patterns (classes, decorators, imports, constants)
        2. Summarize by file category rather than listing every function
        3. Use original_message prefix only as supplementary signal
        4. Truncate aggressively to keep output concise
        """
        all_lines = "\n".join(diff_chunks)
        added_lines = [
            re.sub(r"^\+", "", ln).strip()
            for ln in all_lines.split("\n")
            if ln.startswith("+") and not ln.startswith("++")
        ]
        removed_lines = [
            re.sub(r"^-", "", ln).strip()
            for ln in all_lines.split("\n")
            if ln.startswith("-") and not ln.startswith("--")
        ]
        added_files = re.findall(r"^\+\+\+ b/(.+)", all_lines, re.MULTILINE)

        # Categorize files
        modules: dict[str, list[str]] = {}  # module_name -> [file_paths]
        for f in added_files:
            for prefix, alias in self._MODULE_ALIASES.items():
                if f.startswith(prefix):
                    modules.setdefault(alias, []).append(f)
                    break
            else:
                # Extract top-level directory as module
                top = f.split("/")[0] if "/" in f else f
                modules.setdefault(top, []).append(f)

        # Detect structural patterns
        classes_added = list(set(re.findall(
            r"^class\s+(\w+)", "\n".join(added_lines), re.MULTILINE,
        )))
        funcs_added = list(set(re.findall(
            r"^def\s+(\w+)", "\n".join(added_lines), re.MULTILINE,
        )))
        funcs_removed = list(set(re.findall(
            r"^def\s+(\w+)", "\n".join(removed_lines), re.MULTILINE,
        )))
        decorators = list(set(re.findall(
            r"^@(\w+)", "\n".join(added_lines), re.MULTILINE,
        )))
        imports_added = [
            ln for ln in added_lines
            if ln.startswith("import ") or ln.startswith("from ")
        ]
        constants_added = list(set(re.findall(
            r"^([A-Z][A-Z0-9_]*)\s*=", "\n".join(added_lines), re.MULTILINE
        )))
        constants_removed = list(set(re.findall(
            r"^([A-Z][A-Z0-9_]*)\s*=", "\n".join(removed_lines), re.MULTILINE
        )))

        # Detect meta-file changes
        md_added = sum(
            1 for f in added_files if f.endswith(".md") or f.endswith(".mdx")
        )
        yaml_files = [
            f for f in added_files if f.endswith(".yaml") or f.endswith(".yml")
        ]

        parts: list[str] = []

        # --- Class-level ---
        if classes_added:
            cls = classes_added[:2]
            module_str = modules.get("核心模块", modules.get("技能模块", []))
            if module_str:
                parts.append(f"新增 {', '.join(cls)} 类")
            else:
                parts.append(f"新增 {', '.join(cls)} 类")

        # --- Function-level (truncate to 3) ---
        if funcs_added:
            test_funcs = [f for f in funcs_added if f.startswith("test_")]
            non_test_funcs = [f for f in funcs_added if not f.startswith("test_")]

            if test_funcs and not (non_test_funcs or classes_added):
                # Test-only commit: summarize
                count = len(test_funcs)
                if count == 1:
                    parts.append(f"新增 {test_funcs[0]} 测试")
                elif count == 2:
                    parts.append(f"新增 {test_funcs[0]}, {test_funcs[1]} 测试")
                else:
                    t1, t2 = test_funcs[0], test_funcs[1]
                    parts.append(f"新增 {t1}, {t2} 等 {count} 个测试")
            else:
                # Code commit with functions
                meaningful_funcs = non_test_funcs[:3]
                if len(non_test_funcs) > 3:
                    n = len(non_test_funcs)
                    parts.append(f"新增 {', '.join(meaningful_funcs)} 等 {n} 个函数")
                elif meaningful_funcs:
                    parts.append(f"新增 {', '.join(meaningful_funcs)} 函数")
        if funcs_removed and not parts:
            test_funcs = [f for f in funcs_removed if f.startswith("test_")]
            non_test_funcs = [f for f in funcs_removed if not f.startswith("test_")]
            if test_funcs:
                parts.append(f"删除 {len(test_funcs)} 个测试函数")
            elif non_test_funcs:
                truncated = non_test_funcs[:3]
                if len(non_test_funcs) > 3:
                    n = len(non_test_funcs)
                    parts.append(f"删除 {', '.join(truncated)} 等 {n} 个函数")
                else:
                    parts.append(f"删除 {', '.join(truncated)} 函数")

        # --- Constant/enum changes ---
        if constants_added and not parts:
            parts.append(f"新增 {', '.join(constants_added[:3])} 常量")
        if constants_removed and not parts:
            parts.append(f"删除 {', '.join(constants_removed[:3])} 常量")

        # --- Import-only changes ---
        if imports_added and not parts and not (funcs_added or classes_added):
            # Detect what kind of imports (e.g., pytest, yaml, dataclasses)
            libs = list(set(re.findall(
                r"^import\s+(\w+)|^from\s+(\w+)",
                "\n".join(imports_added), re.MULTILINE,
            )))
            libs = [ln[0] or ln[1] for ln in libs if ln[0] or ln[1]]
            if libs:
                parts.append(f"新增 {', '.join(libs[:3])} 依赖")

        # --- Decorator patterns ---
        if decorators and not parts:
            if "dataclass" in decorators:
                parts.append("新增数据类定义")
            elif "property" in decorators:
                parts.append("新增属性装饰器")
            elif "staticmethod" in decorators or "classmethod" in decorators:
                parts.append("新增静态/类方法")

        # --- File/path level summary (for meta-prefixes or no-pattern commits) ---
        if not parts and modules:
            file_modules = list(modules.keys())
            file_count = sum(len(v) for v in modules.values())
            module_str = ", ".join(file_modules[:3])
            if file_count > len(file_modules):
                parts.append(f"更新 {module_str} 等 {file_count} 个文件")

        # --- YAML/config files ---
        if yaml_files and not parts:
            parts.append(f"更新 {', '.join(yaml_files[:2])} 配置")

        # --- Markdown/docs files ---
        if md_added and not parts:
            parts.append(f"更新 {md_added} 个文档文件")

        # --- Parse prefix (lowercase, strip scope) ---
        if ":" in original_message:
            prefix = original_message.split(":")[0].strip().lower()
            prefix = re.sub(r"\([^)]*\)", "", prefix).strip()
        else:
            prefix = ""

        # --- Fallback: use prefix + module info ---
        if not parts:
            prefix_desc: dict[str, str] = {
                "feat": "新增功能", "feature": "新增功能",
                "fix": "修复问题", "bugfix": "修复问题",
                "refactor": "重构代码", "refactoring": "重构代码",
                "test": "添加测试", "tests": "添加测试",
                "chore": "更新构建", "ci": "更新CI配置",
                "docs": "更新文档", "doc": "更新文档",
                "style": "优化代码风格",
                "build": "更新构建配置",
                "perf": "优化性能", "optimize": "优化性能",
                "security": "修复安全问题",
                "typo": "修正拼写",
                "merge": "合并分支",
                "release": "版本发布",
                "simplify": "简化代码",
                "cleanup": "清理代码",
            }
            desc = prefix_desc.get(prefix, "更新代码")
            if modules:
                module_str = ", ".join(list(modules.keys())[:2])
                parts.append(f"{desc}（{module_str}）")
            else:
                parts.append(desc)

        # --- Decorator note (append, not replace) ---
        if decorators and parts and not any("类" in p or "装饰" in p for p in parts):
            if "property" in decorators:
                parts.append("含属性装饰器")

        result = "；".join(parts) if parts else "更新代码"
        # Hard cap at 200 chars
        if len(result) > 200:
            result = result[:197] + "..."
        return result

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
        print("\n  -> Spawning workers to regenerate commit_log")
        for month, commits in sorted(commits_by_month.items()):
            batches = self._batch_commits(commits, BATCH_SIZE)
            print(f"     {month}: {len(commits)} commits in {len(batches)} batch(es)")

            total_batches = len(batches)
            for batch_idx, batch in enumerate(batches):
                n_commits = len(batch)
                msg = f"     Batch {batch_idx + 1}/{total_batches} ({n_commits}c)"
                print(msg)
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
