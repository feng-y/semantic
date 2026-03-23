#!/usr/bin/env python3
"""commit-semantic skill implementation.

4 阶段消费 commit-extract JSONL 输出：
  1. ingest    - 展开 sections 为 semantic units + 收集 rules_invariants
  2. aggregate - 按 theme 聚合，统计 op 分布 + importance 分布
  3. distill   - 提取 canonical demands，评分排序
  4. export    - 汇总统计，生成 summary.json

Input: data/commit-extract/*.jsonl
Output: data/commit-semantic/
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, save_state
from src.skill_runner import SkillRunner, run_skill
from src.io_utils import load_jsonl, save_jsonl, save_json

logger = logging.getLogger(__name__)

EXTRACT_OUTPUT = Path("data/commit-extract")
SEMANTIC_OUTPUT = Path("data/commit-semantic")


class CommitSemanticRunner(SkillRunner):
    """Runner for commit-semantic pipeline (4 stages)."""

    STAGES = ["ingest", "aggregate", "distill", "export"]
    PIPELINE = "commit-semantic"

    def _check_prerequisites(self) -> tuple[bool, str]:
        """Check if commit-extract JSONL output exists."""
        if not EXTRACT_OUTPUT.exists():
            return False, "commit-extract output not found"
        jsonl_files = list(EXTRACT_OUTPUT.glob("*.jsonl"))
        if not jsonl_files:
            return False, f"No JSONL files in {EXTRACT_OUTPUT}"
        return True, ""

    def _require_prerequisites(self) -> bool:
        ok, msg = self._check_prerequisites()
        if not ok:
            print(f"[{self.PIPELINE}] {msg}")
            return False
        return True

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        dispatch = {
            "ingest": self._run_ingest,
            "aggregate": self._run_aggregate,
            "distill": self._run_distill,
            "export": self._run_export,
        }
        handler = dispatch.get(stage)
        if handler:
            return handler(state)
        return True

    # -------------------------------------------------------------------
    # Stage 1: ingest
    # -------------------------------------------------------------------

    def _run_ingest(self, state: HarnessState) -> bool:
        """Read JSONL → expand sections into semantic units + collect invariants."""
        print("  -> Ingesting commit-extract JSONL")

        units_dir = SEMANTIC_OUTPUT / "units"
        units_dir.mkdir(parents=True, exist_ok=True)

        all_units: list[dict] = []
        all_invariants: list[dict] = []

        for jsonl_file in sorted(EXTRACT_OUTPUT.glob("*.jsonl")):
            for record in load_jsonl(str(jsonl_file), skip_errors=True):
                sha = record.get("sha", "")
                date = record.get("date", "")
                author = record.get("author", "")
                is_large = record.get("is_large_aggregate", False)
                is_mixed = record.get("is_mixed", False)
                sections = record.get("sections", [])

                # Expand each section's items into units
                for section in sections:
                    section_name = section.get("name", "")
                    theme = section.get("theme", "")
                    importance = section.get("importance", "secondary")

                    for item in section.get("items", []):
                        all_units.append({
                            "sha": sha,
                            "date": date,
                            "author": author,
                            "section_name": section_name,
                            "theme": theme,
                            "importance": importance,
                            "op": item.get("op", "other"),
                            "summary": item.get("summary", ""),
                            "is_large_aggregate": is_large,
                            "is_mixed": is_mixed,
                        })

                # Collect rules_invariants
                for inv in record.get("rules_invariants", []):
                    all_invariants.append({
                        "sha": sha,
                        "date": date,
                        "kind": inv.get("kind", "other"),
                        "statement": inv.get("statement", ""),
                        "enforced_by_commit": inv.get("enforced_by_commit", False),
                    })

        save_jsonl(all_units, str(units_dir / "all.jsonl"))
        save_jsonl(all_invariants, str(SEMANTIC_OUTPUT / "invariants.jsonl"))

        print(f"  Ingested {len(all_units)} units, {len(all_invariants)} invariants")
        self.add_artifact(state, str(units_dir))
        return True

    # -------------------------------------------------------------------
    # Stage 2: aggregate
    # -------------------------------------------------------------------

    def _run_aggregate(self, state: HarnessState) -> bool:
        """Group units by theme, compute op distribution + importance ratio."""
        print("  -> Aggregating by theme")

        units_file = SEMANTIC_OUTPUT / "units" / "all.jsonl"
        if not units_file.exists():
            print("  ! No units to aggregate")
            return True

        units = load_jsonl(str(units_file))

        # Group by theme
        by_theme: dict[str, list[dict]] = defaultdict(list)
        for unit in units:
            theme = unit.get("theme", "unknown")
            by_theme[theme].append(unit)

        patterns: list[dict] = []
        for theme, theme_units in sorted(by_theme.items()):
            distinct_commits = len(set(u["sha"] for u in theme_units))

            # Threshold: >= 3 distinct commits
            if distinct_commits < 3:
                continue

            # Op distribution
            op_dist: dict[str, int] = defaultdict(int)
            importance_counts = {"primary": 0, "secondary": 0}
            summaries: list[str] = []

            for u in theme_units:
                op_dist[u.get("op", "other")] += 1
                imp = u.get("importance", "secondary")
                if imp in importance_counts:
                    importance_counts[imp] += 1
                if u.get("summary") and len(summaries) < 3:
                    summaries.append(u["summary"])

            patterns.append({
                "theme": theme,
                "count": len(theme_units),
                "distinct_commits": distinct_commits,
                "op_distribution": dict(op_dist),
                "importance_ratio": importance_counts,
                "representative_summaries": summaries,
            })

        save_jsonl(patterns, str(SEMANTIC_OUTPUT / "patterns.jsonl"))
        print(f"  Found {len(patterns)} patterns (threshold >= 3 distinct commits)")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "patterns.jsonl"))
        return True

    # -------------------------------------------------------------------
    # Stage 3: distill
    # -------------------------------------------------------------------

    def _run_distill(self, state: HarnessState) -> bool:
        """Extract canonical demands from patterns, scored and ranked."""
        print("  -> Distilling canonical demands")

        patterns_file = SEMANTIC_OUTPUT / "patterns.jsonl"
        if not patterns_file.exists():
            print("  ! No patterns to distill")
            return True

        patterns = load_jsonl(str(patterns_file))

        # Score each pattern
        demands: list[dict] = []
        for pattern in patterns:
            distinct = pattern.get("distinct_commits", 0)
            imp_ratio = pattern.get("importance_ratio", {})
            primary = imp_ratio.get("primary", 0)
            secondary = imp_ratio.get("secondary", 0)
            total_imp = primary + secondary
            if total_imp > 0:
                importance_weight = (primary * 2 + secondary * 1) / total_imp
            else:
                importance_weight = 1.0

            score = distinct * importance_weight

            demands.append({
                "theme": pattern["theme"],
                "score": round(score, 2),
                "distinct_commits": distinct,
                "op_distribution": pattern.get("op_distribution", {}),
                "importance_weight": round(importance_weight, 2),
                "representative_summaries": pattern.get("representative_summaries", []),
            })

        # Sort: score desc → distinct_commits desc → theme alpha
        demands.sort(key=lambda d: (-d["score"], -d["distinct_commits"], d["theme"]))

        # Add rank
        for i, d in enumerate(demands, 1):
            d["rank"] = i

        save_jsonl(demands, str(SEMANTIC_OUTPUT / "canonical-demands.jsonl"))
        print(f"  Distilled {len(demands)} canonical demands")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "canonical-demands.jsonl"))
        return True

    # -------------------------------------------------------------------
    # Stage 4: export
    # -------------------------------------------------------------------

    def _run_export(self, state: HarnessState) -> bool:
        """Generate summary statistics."""
        print("  -> Generating export summary")

        # Load units for stats
        units_file = SEMANTIC_OUTPUT / "units" / "all.jsonl"
        units = load_jsonl(str(units_file)) if units_file.exists() else []

        patterns_file = SEMANTIC_OUTPUT / "patterns.jsonl"
        patterns = load_jsonl(str(patterns_file)) if patterns_file.exists() else []

        invariants_file = SEMANTIC_OUTPUT / "invariants.jsonl"
        invariants = load_jsonl(str(invariants_file)) if invariants_file.exists() else []

        # Op distribution across all units
        op_dist: dict[str, int] = defaultdict(int)
        min_date: str = ""
        max_date: str = ""
        for u in units:
            op_dist[u.get("op", "other")] += 1
            d = u.get("date", "")
            if d:
                if not min_date or d < min_date:
                    min_date = d
                if not max_date or d > max_date:
                    max_date = d

        bugfix_count = op_dist.get("bugfix", 0)
        total = len(units) or 1
        bugfix_ratio = round(bugfix_count / total, 4)

        # Top patterns by score
        demands_file = SEMANTIC_OUTPUT / "canonical-demands.jsonl"
        demands = load_jsonl(str(demands_file)) if demands_file.exists() else []
        top_patterns = [
            {"theme": d["theme"], "score": d["score"], "distinct_commits": d["distinct_commits"]}
            for d in demands[:10]
        ]

        # Date range
        date_range = {}
        if min_date:
            date_range = {"from": min_date, "to": max_date}

        summary = {
            "total_units": len(units),
            "total_patterns": len(patterns),
            "op_distribution": dict(op_dist),
            "top_patterns": top_patterns,
            "bugfix_ratio": bugfix_ratio,
            "invariant_count": len(invariants),
            "date_range": date_range,
        }

        save_json(summary, str(SEMANTIC_OUTPUT / "summary.json"))
        print(f"  Exported: {len(units)} units, {len(patterns)} patterns, "
              f"bugfix ratio {bugfix_ratio:.1%}")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "summary.json"))
        return True

    # -------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------

    def handle_step(self) -> int:
        if not self._require_prerequisites():
            return 1
        return super().handle_step()

    def handle_resume(self) -> int:
        if not self._require_prerequisites():
            return 1
        return super().handle_resume()

    def handle_run(self, remaining: list[str] | None = None) -> int:
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--stage", help="Run a specific stage")
        args = parser.parse_args(argv)

        if args.stage:
            if args.stage not in self.STAGES:
                print(f"[{self.PIPELINE}] Unknown stage: {args.stage}. "
                      f"Available: {', '.join(self.STAGES)}")
                return 1
            if not self._require_prerequisites():
                return 1
            state = self.init_state()
            save_state(self.PIPELINE, state)
            success = self.run_stage(args.stage, state)
            return 0 if success else 1

        return super().handle_run()


def run_commit_semantic() -> None:
    """Entry point for the commit-semantic skill."""
    raise SystemExit(CommitSemanticRunner().main())


if __name__ == "__main__":
    run_commit_semantic()
