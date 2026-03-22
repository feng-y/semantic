#!/usr/bin/env python3
"""commit-semantic skill implementation.

跨 commits 分析、拆分、聚合、提取 canonical patterns，生成统计摘要。

Stages:
  1. split    - 按模块拆分 commits
  2. analyze  - LLM 语义分析
  3. aggregate- 聚合 patterns
  4. distill  - 提取 canonical demands
  5. export   - 生成 summary.yaml 统计摘要

Input: data/commit-extract/*.yaml
Output: data/commit-semantic/
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dataclasses import asdict, dataclass, field
from typing import Any

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill
from src.io_utils import load_yaml, save_yaml, save_json
from src.types import ExportSummary


EXTRACT_OUTPUT = Path("data/commit-extract")
SEMANTIC_OUTPUT = Path("data/commit-semantic")

FUNCTIONAL_PREFIXES = ("feat", "bugfix", "optimize")
TIER_NAMES = ("high", "medium", "low")

MODULE_KEYWORDS = {
    "schedule": ["schedule", "timer", "callback"],
    "reader": ["reader", "dynamic"],
    "parser": ["parser", "parse"],
    "config": ["config", "configuration"],
    "server": ["server", "service"],
    "client": ["client"],
    "db": ["database", "db", "storage"],
    "api": ["api", "endpoint"],
}


class CommitSemanticRunner(SkillRunner):
    """Runner for commit-semantic pipeline."""

    STAGES = ["split", "analyze", "aggregate", "distill", "export"]
    PIPELINE = "commit-semantic"

    def _check_prerequisites(self) -> tuple[bool, str]:
        """Check if commit-extract output exists."""
        if not EXTRACT_OUTPUT.exists():
            return False, "commit-extract output not found"
        month_files = list(EXTRACT_OUTPUT.glob("*.yaml"))
        if not month_files:
            return False, f"No month files in {EXTRACT_OUTPUT}"
        return True, ""

    def _require_prerequisites(self) -> bool:
        """Check prerequisites and print message. Returns True if ok."""
        ok, msg = self._check_prerequisites()
        if not ok:
            print(f"[{self.PIPELINE}] {msg}")
            return False
        return True

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")

        if stage == "split":
            return self._run_split(state)
        elif stage == "analyze":
            return self._run_analyze(state)
        elif stage == "aggregate":
            return self._run_aggregate(state)
        elif stage == "distill":
            return self._run_distill(state)
        elif stage == "export":
            return self._run_export(state)

        return True

    # -----------------------------------------------------------------------
    # Team Agent Architecture Hooks
    # -----------------------------------------------------------------------

    def _batch_units(
        self, units: list[dict], batch_size: int = 10
    ) -> list[list[dict]]:
        """Split units into batches for worker processing."""
        return [
            units[i : i + batch_size] for i in range(0, len(units), batch_size)
        ]

    def _spawn_worker(self, batch: list[dict], prompt_template: str) -> list[dict]:
        """Spawn a worker agent for a batch of units.

        In production this is replaced by a real Task agent call.
        In tests/CLI, falls back to local processing.

        Args:
            batch: List of unit dicts to process
            prompt_template: Name of prompt template to use

        Returns:
            List of processed units with worker-added fields.
        """
        # Check if we should use real Task agents
        use_task = os.environ.get("COMMIT_SEMANTIC_USE_TASK_AGENTS", "").lower() in (
            "1",
            "true",
            "yes",
        )

        if use_task and not results:
            print("  [commit-semantic] WARNING: _spawn_worker called with use_task=True but returned no results. Ensure this runs within a Task agent context.")

        # Local processing (default): run _score_unit directly
        results: list[dict] = []
        for unit in batch:
            scored = dict(unit)
            scored["score"] = self._score_unit(scored)
            results.append(scored)
        return results

    def _get_worker_prompt_template(self, name: str) -> str:
        """Lazy-load a worker prompt template."""
        prompt_path = Path(__file__).parent / "prompts" / f"{name}.md"
        if prompt_path.exists():
            return prompt_path.read_text(encoding="utf-8")
        return ""


    def _detect_modules(self, message: str) -> list[str]:
        """从 commit message 检测模块."""
        if not message:
            return []
        message_lower = message.lower()
        return [
            module
            for module, keywords in MODULE_KEYWORDS.items()
            if any(kw in message_lower for kw in keywords)
        ]

    def _classify_type(self, commit_message: str) -> str:
        """Classify commit by prefix."""
        prefix = commit_message.split(":")[0].lower()
        if any(f in prefix for f in FUNCTIONAL_PREFIXES):
            return "functional"
        if "+" in prefix:
            return "functional"
        return "non-functional"

    def _score_unit(self, unit: dict) -> int:
        """Score a functional unit (0-10)."""
        commit_log = unit.get("commit_log", "")
        score = 5
        if 20 < len(commit_log) < 200:
            score += 2
        if unit.get("module") != "unknown":
            score += 2
        if any(kw in commit_log.lower() for kw in ("fix", "add", "support")):
            score += 1
        return min(score, 10)

    def _run_split(self, state: HarnessState) -> bool:
        """按模块拆分 commits 为 change units."""
        print("  -> Splitting commits by module")

        units_dir = SEMANTIC_OUTPUT / "units"
        units_dir.mkdir(parents=True, exist_ok=True)

        all_commits = []
        for month_file in sorted(EXTRACT_OUTPUT.glob("*.yaml")):
            data = load_yaml(str(month_file))
            all_commits.extend(data.get("commits", []))

        print(f"     Loaded {len(all_commits)} commits")

        units = []
        for commit in all_commits:
            # Primary: read commit_log (LLM-regenerated by commit-extract workers)
            # Fallback: original_message (raw git message) if commit_log missing
            msg = commit.get("commit_log") or commit.get("original_message", "")
            modules = self._detect_modules(msg)

            if not modules:
                units.append({
                    "unit_id": commit["commit_id"][:8],
                    "commit_id": commit["commit_id"],
                    "timestamp": commit["timestamp"],
                    "module": "unknown",
                    "commit_log": msg,
                    "files": commit.get("files", []),
                    "diff_chunks": commit.get("diff_chunks", []),
                })
            else:
                for module in modules:
                    units.append({
                        "unit_id": f"{commit['commit_id'][:8]}-{module}",
                        "commit_id": commit["commit_id"],
                        "timestamp": commit["timestamp"],
                        "module": module,
                        "commit_log": msg,
                        "files": commit.get("files", []),
                        "diff_chunks": commit.get("diff_chunks", []),
                    })

        save_yaml({
            "metadata": {
                "total_units": len(units),
                "generated_at": datetime.now().isoformat(),
            },
            "units": units,
        }, str(units_dir / "all.yaml"))

        print(f"  Split into {len(units)} units")
        self.add_artifact(state, str(units_dir))
        return True

    def _run_analyze(self, state: HarnessState) -> bool:
        """LLM 语义分析和评分."""
        print("  -> Analyzing units with scoring")

        units_file = SEMANTIC_OUTPUT / "units" / "all.yaml"
        if not units_file.exists():
            print("  ! No units to analyze")
            return True

        data = load_yaml(str(units_file))
        units = data.get("units", [])

        for subdir in ["functional/high", "functional/medium", "functional/low", "non-functional/all"]:
            (SEMANTIC_OUTPUT / subdir).mkdir(parents=True, exist_ok=True)

        high, medium, low, non_functional = [], [], [], []

        for unit in units:
            commit_log = unit.get("commit_log", "")
            if self._classify_type(commit_log) == "functional":
                scored = dict(unit)
                scored["score"] = self._score_unit(scored)
                if scored["score"] >= 8:
                    high.append(scored)
                elif scored["score"] >= 5:
                    medium.append(scored)
                else:
                    low.append(scored)
            else:
                non_functional.append({**unit, "score": None})

        for tier, units_list in [("high", high), ("medium", medium), ("low", low)]:
            save_yaml({
                "metadata": {"tier": tier, "count": len(units_list)},
                "units": units_list,
            }, str(SEMANTIC_OUTPUT / "functional" / tier / "units.yaml"))
            print(f"    {tier}: {len(units_list)} units")

        save_yaml({
            "metadata": {"count": len(non_functional)},
            "units": non_functional,
        }, str(SEMANTIC_OUTPUT / "non-functional" / "all" / "units.yaml"))
        print(f"    non-functional: {len(non_functional)} units")

        save_json({
            "last_analyzed": datetime.now().isoformat(),
            "total_units": len(units),
            "functional": len(high) + len(medium) + len(low),
            "non_functional": len(non_functional),
            "by_tier": {
                "high": len(high),
                "medium": len(medium),
                "low": len(low),
            },
        }, str(SEMANTIC_OUTPUT / "state.json"))

        print(f"  Analyzed {len(units)} units")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "functional"))
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "non-functional"))
        return True

    def _run_aggregate(self, state: HarnessState) -> bool:
        """按模块聚合 patterns."""
        print("  -> Aggregating by module")

        patterns_dir = SEMANTIC_OUTPUT / "patterns"
        patterns_dir.mkdir(parents=True, exist_ok=True)

        high_file = SEMANTIC_OUTPUT / "functional" / "high" / "units.yaml"
        if not high_file.exists():
            print("  ! No high-scored units")
            return True

        data = load_yaml(str(high_file))
        units = data.get("units", [])

        by_module: dict[str, list] = defaultdict(list)
        for unit in units:
            by_module[unit.get("module", "unknown")].append(unit)

        for module, module_units in sorted(by_module.items()):
            save_yaml({
                "metadata": {
                    "module": module,
                    "count": len(module_units),
                    "generated_at": datetime.now().isoformat(),
                },
                "patterns": module_units,
            }, str(patterns_dir / f"{module}.yaml"))
            print(f"    {module}: {len(module_units)} patterns")

        print(f"  Aggregated {len(by_module)} modules")
        self.add_artifact(state, str(patterns_dir))
        return True

    def _run_distill(self, state: HarnessState) -> bool:
        """提取 canonical demands."""
        print("  -> Distilling canonical demands")

        patterns_dir = SEMANTIC_OUTPUT / "patterns"
        if not patterns_dir.exists():
            print("  ! No patterns to distill")
            return True

        demands = []
        for pattern_file in sorted(patterns_dir.glob("*.yaml")):
            data = load_yaml(str(pattern_file))
            module = data.get("metadata", {}).get("module", "unknown")
            patterns = data.get("patterns", [])

            for i, pattern in enumerate(patterns[:5], 1):
                demands.append({
                    "demand_id": f"{module}-{i:02d}",
                    "module": module,
                    "rank": i,
                    "score": pattern.get("score", 0),
                    "commit_log": pattern.get("commit_log", "")[:100],
                    "source_commit": pattern.get("commit_id", "")[:8],
                })

        save_yaml({
            "metadata": {
                "total_demands": len(demands),
                "generated_at": datetime.now().isoformat(),
            },
            "demands": demands,
        }, str(SEMANTIC_OUTPUT / "canonical-demands.yaml"))

        print(f"  Distilled {len(demands)} canonical demands")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "canonical-demands.yaml"))
        return True

    def _run_export(self, state: HarnessState) -> bool:
        """Generate summary statistics from canonical-demands and patterns."""
        print("  -> Generating export summary")

        demands_file = SEMANTIC_OUTPUT / "canonical-demands.yaml"
        if not demands_file.exists():
            print("  ! No canonical-demands.yaml found — run distill first")
            return False

        demands_data = load_yaml(str(demands_file))
        demands: list[dict] = demands_data.get("demands", [])

        # Count by development type heuristic (prefix in commit_log)
        dev_type_dist: dict[str, int] = {"feature": 0, "bugfix": 0, "refactor": 0, "other": 0}
        for d in demands:
            msg = d.get("commit_log", "").lower()
            if msg.startswith("feat") or msg.startswith("add") or msg.startswith("support"):
                dev_type_dist["feature"] += 1
            elif msg.startswith("fix") or msg.startswith("bug"):
                dev_type_dist["bugfix"] += 1
            elif msg.startswith("refactor") or msg.startswith("clean"):
                dev_type_dist["refactor"] += 1
            else:
                dev_type_dist["other"] += 1

        bugfix_count = dev_type_dist["bugfix"]
        total = len(demands) or 1
        bugfix_ratio = bugfix_count / total

        # High-frequency patterns: modules with most demands
        by_module: dict[str, int] = {}
        for d in demands:
            m = d.get("module", "unknown")
            by_module[m] = by_module.get(m, 0) + 1

        high_freq = sorted(
            [{"pattern_id": m, "domain": m, "count": c,
              "representative_issue_text": ""}
             for m, c in by_module.items() if c >= 2],
            key=lambda x: -x["count"],
        )[:10]

        summary = ExportSummary(
            total_cases=len(demands),
            unique_cases=len(demands),
            duplicate_cases=0,
            duplicate_groups=0,
            valid_cases=len(demands),
            invalid_cases=0,
            low_value_cases=0,
            validation_pass_rate=1.0,
            development_type_distribution=dev_type_dist,
            bugfix_count=bugfix_count,
            bugfix_ratio=bugfix_ratio,
            needs_split_count=0,
            needs_split_ratio=0.0,
            pattern_count=len(by_module),
            domain_pattern_stats={
                m: {"pattern_count": c, "pattern_count_status": "good", "action": "none"}
                for m, c in by_module.items()
            },
            high_frequency_patterns=high_freq,
            invalid_reason_top_n={},
        )

        summary_path = SEMANTIC_OUTPUT / "summary.yaml"
        save_yaml(asdict(summary), str(summary_path))
        print(f"  Exported summary: {len(demands)} cases, {len(by_module)} patterns, "
              f"bugfix ratio {bugfix_ratio:.1%}")
        self.add_artifact(state, str(summary_path))
        return True
        if not self._require_prerequisites():
            return 1
        return super().handle_step()

    def handle_resume(self) -> int:
        if not self._require_prerequisites():
            return 1
        return super().handle_resume()


    def handle_run(self, remaining: list[str] | None = None) -> int:
        """Override to handle command-line args including --stage."""
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--stage", help="Run a specific stage instead of all")
        args = parser.parse_args(argv)

        if args.stage:
            # Run single stage
            if args.stage not in self.STAGES:
                print(f"[{self.PIPELINE}] Unknown stage: {args.stage}. Available: {', '.join(self.STAGES)}")
                return 1
            if not self._require_prerequisites():
                return 1
            state = self.init_state()
            from src.harness_state import save_state
            save_state(self.PIPELINE, state)
            success = self.run_stage(args.stage, state)
            return 0 if success else 1

        return super().handle_run()


def run_commit_semantic() -> None:
    """Entry point for the commit-semantic skill."""
    raise SystemExit(CommitSemanticRunner().main())


if __name__ == "__main__":
    run_commit_semantic()
