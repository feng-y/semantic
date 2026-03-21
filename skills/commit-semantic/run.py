#!/usr/bin/env python3
"""commit-semantic skill implementation.

跨 commits 分析、拆分、聚合、提取 canonical patterns。

Stages:
  1. split    - 按模块拆分 commits
  2. analyze  - LLM 语义分析
  3. aggregate- 聚合 patterns
  4. distill  - 提取 canonical demands

Input: data/commit-extract/*.yaml
Output: data/commit-semantic/
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner, run_skill
from src.io_utils import load_yaml, save_yaml, save_json


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

    STAGES = ["split", "analyze", "aggregate", "distill"]
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

        return True

    def _extract_module_log(self, message: str, module: str) -> str:
        """Extract the commit log portion relevant to a module."""
        return message

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
            msg = commit.get("commit_message", "")
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
                        "commit_log": self._extract_module_log(msg, module),
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
                non_functional.append(unit)

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

    def handle_step(self) -> int:
        if not self._require_prerequisites():
            return 1
        return super().handle_step()

    def handle_resume(self) -> int:
        if not self._require_prerequisites():
            return 1
        return super().handle_resume()


if __name__ == "__main__":
    run_skill(CommitSemanticRunner)
