#!/usr/bin/env python3
"""commit-semantic skill implementation.

4-stage pipeline consuming JSONL from commit-extract output.

Stages:
  1. ingest    - expand sections/items into semantic units
  2. aggregate - group by theme, compute distributions
  3. distill   - score and rank canonical demands
  4. export    - summary statistics

Input: data/commit-extract/YYYY-MM.jsonl
Output: data/commit-semantic/
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner
from src.io_utils import load_jsonl, save_jsonl, save_json


EXTRACT_OUTPUT = Path("data/commit-extract")
SEMANTIC_OUTPUT = Path("data/commit-semantic")


class CommitSemanticRunner(SkillRunner):
    """Runner for commit-semantic pipeline."""

    STAGES = ["ingest", "aggregate", "distill", "export"]
    PIPELINE = "commit-semantic"

    def _check_prerequisites(self) -> tuple[bool, str]:
        """Check if commit-extract JSONL output exists."""
        if not EXTRACT_OUTPUT.exists():
            return False, "commit-extract output not found"
        month_files = list(EXTRACT_OUTPUT.glob("*.jsonl"))
        if not month_files:
            return False, f"No .jsonl month files in {EXTRACT_OUTPUT}"
        return True, ""

    def _require_prerequisites(self) -> bool:
        ok, msg = self._check_prerequisites()
        if not ok:
            print(f"[{self.PIPELINE}] {msg}")
            return False
        return True

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        if stage == "ingest":
            return self._run_ingest(state)
        elif stage == "aggregate":
            return self._run_aggregate(state)
        elif stage == "distill":
            return self._run_distill(state)
        elif stage == "export":
            return self._run_export(state)
        return True

    # ------------------------------------------------------------------
    # Stage implementations
    # ------------------------------------------------------------------

    def _run_ingest(self, state: HarnessState) -> bool:
        """Expand sections/items into semantic units; collect rules_invariants."""
        print("  -> Ingesting JSONL commit-extract output")

        units_dir = SEMANTIC_OUTPUT / "units"
        units_dir.mkdir(parents=True, exist_ok=True)

        units: list[dict] = []
        invariants: list[dict] = []
        skipped = 0

        for month_file in sorted(EXTRACT_OUTPUT.glob("*.jsonl")):
            with open(month_file, encoding="utf-8") as fh:
                for lineno, raw in enumerate(fh, 1):
                    raw = raw.strip()
                    if not raw:
                        continue
                    try:
                        commit = json.loads(raw)
                    except json.JSONDecodeError as exc:
                        print(
                            f"  [ingest] WARNING: skipping invalid JSON in "
                            f"{month_file.name}:{lineno}: {exc}",
                            file=sys.stderr,
                        )
                        skipped += 1
                        continue

                    sha = commit.get("sha", "")
                    date = commit.get("date", "")
                    author = commit.get("author", "")
                    is_large = commit.get("is_large_aggregate", False)
                    is_mixed = commit.get("is_mixed", False)

                    for section in commit.get("sections", []):
                        section_name = section.get("name", "")
                        theme = section.get("theme", "")
                        importance = section.get("importance", "")
                        for item in section.get("items", []):
                            units.append({
                                "sha": sha,
                                "date": date,
                                "author": author,
                                "section_name": section_name,
                                "theme": theme,
                                "importance": importance,
                                "op": item.get("op", ""),
                                "summary": item.get("summary", ""),
                                "is_large_aggregate": is_large,
                                "is_mixed": is_mixed,
                            })

                    for inv in commit.get("rules_invariants", []):
                        invariants.append({**inv, "sha": sha, "date": date})

        save_jsonl(units, str(units_dir / "all.jsonl"))
        save_jsonl(invariants, str(SEMANTIC_OUTPUT / "invariants.jsonl"))

        if skipped:
            print(f"  Skipped {skipped} invalid JSON lines")
        print(f"  Ingested {len(units)} units, {len(invariants)} invariants")
        self.add_artifact(state, str(units_dir / "all.jsonl"))
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "invariants.jsonl"))
        return True

    def _run_aggregate(self, state: HarnessState) -> bool:
        """Group units by theme, compute distributions."""
        print("  -> Aggregating by theme")

        units_file = SEMANTIC_OUTPUT / "units" / "all.jsonl"
        if not units_file.exists():
            print("  ! No units file — run ingest first")
            return False

        units = load_jsonl(str(units_file))

        # theme -> {shas, op_dist, importance_dist, summaries}
        by_theme: dict[str, dict] = {}
        for unit in units:
            theme = unit.get("theme", "") or "unknown"
            if theme not in by_theme:
                by_theme[theme] = {
                    "shas": set(),
                    "op_dist": defaultdict(int),
                    "importance_dist": defaultdict(int),
                    "summaries": [],
                }
            entry = by_theme[theme]
            entry["shas"].add(unit.get("sha", ""))
            op = unit.get("op", "other") or "other"
            entry["op_dist"][op] += 1
            imp = unit.get("importance", "secondary") or "secondary"
            entry["importance_dist"][imp] += 1
            summary = unit.get("summary", "")
            if summary and len(entry["summaries"]) < 3:
                entry["summaries"].append(summary)

        patterns: list[dict] = []
        for theme, data in by_theme.items():
            distinct = len(data["shas"])
            patterns.append({
                "theme": theme,
                "count": sum(data["op_dist"].values()),
                "distinct_commits": distinct,
                "op_distribution": dict(data["op_dist"]),
                "importance_ratio": dict(data["importance_dist"]),
                "representative_summaries": data["summaries"],
            })

        save_jsonl(patterns, str(SEMANTIC_OUTPUT / "patterns.jsonl"))
        high_freq = sum(1 for p in patterns if p["distinct_commits"] >= 3)
        print(f"  Aggregated {len(patterns)} themes, {high_freq} high-frequency (>=3 commits)")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "patterns.jsonl"))
        return True

    def _run_distill(self, state: HarnessState) -> bool:
        """Score patterns and produce canonical demands."""
        print("  -> Distilling canonical demands")

        patterns_file = SEMANTIC_OUTPUT / "patterns.jsonl"
        if not patterns_file.exists():
            print("  ! No patterns file — run aggregate first")
            return False

        patterns = load_jsonl(str(patterns_file))

        # Load invariants for extra weight
        invariants_file = SEMANTIC_OUTPUT / "invariants.jsonl"
        invariant_sha_counts: dict[str, set] = defaultdict(set)
        if invariants_file.exists():
            for inv in load_jsonl(str(invariants_file)):
                stmt = inv.get("statement", "")
                sha = inv.get("sha", "")
                if stmt and sha:
                    invariant_sha_counts[stmt].add(sha)
        high_freq_invariants = {
            stmt for stmt, shas in invariant_sha_counts.items() if len(shas) >= 3
        }

        def _score(pattern: dict) -> float:
            imp = pattern.get("importance_ratio", {})
            primary = imp.get("primary", 0)
            secondary = imp.get("secondary", 0)
            total = max(primary + secondary, 1)
            # primary items weighted 2x: they represent core functional changes
            importance_weight = (primary * 2 + secondary * 1) / total
            base = pattern["distinct_commits"] * importance_weight
            theme = pattern.get("theme", "").lower()
            bonus = 0.5 if any(theme in inv.lower() for inv in high_freq_invariants) else 0.0
            return base + bonus

        # Pre-compute scores to avoid redundant calls during sort + build
        pattern_scores = [(p, _score(p)) for p in patterns]
        pattern_scores.sort(key=lambda ps: (-ps[1], -ps[0]["distinct_commits"], ps[0]["theme"]))

        demands: list[dict] = []
        for rank, (pattern, score) in enumerate(pattern_scores, 1):
            demands.append({
                "rank": rank,
                "theme": pattern["theme"],
                "score": round(score, 4),
                "distinct_commits": pattern["distinct_commits"],
                "count": pattern["count"],
                "op_distribution": pattern["op_distribution"],
                "importance_ratio": pattern["importance_ratio"],
                "representative_summaries": pattern["representative_summaries"],
            })

        save_jsonl(demands, str(SEMANTIC_OUTPUT / "canonical-demands.jsonl"))
        print(f"  Distilled {len(demands)} canonical demands")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "canonical-demands.jsonl"))
        return True

    def _run_export(self, state: HarnessState) -> bool:
        """Compute summary statistics and write summary.json."""
        print("  -> Generating export summary")

        demands_file = SEMANTIC_OUTPUT / "canonical-demands.jsonl"
        if not demands_file.exists():
            print("  ! No canonical-demands.jsonl — run distill first")
            return False

        demands = load_jsonl(str(demands_file))

        units_file = SEMANTIC_OUTPUT / "units" / "all.jsonl"
        units = load_jsonl(str(units_file)) if units_file.exists() else []

        invariants_file = SEMANTIC_OUTPUT / "invariants.jsonl"
        invariant_count = 0
        if invariants_file.exists():
            invariant_count = len(load_jsonl(str(invariants_file)))

        # Aggregate op distribution across all units
        op_dist: dict[str, int] = defaultdict(int)
        dates: list[str] = []
        for unit in units:
            op = unit.get("op", "other") or "other"
            op_dist[op] += 1
            d = unit.get("date", "")
            if d:
                dates.append(d)

        total_ops = sum(op_dist.values()) or 1
        bugfix_count = op_dist.get("bugfix", 0)
        bugfix_ratio = round(bugfix_count / total_ops, 4)

        top_patterns = [
            {
                "theme": d["theme"],
                "distinct_commits": d["distinct_commits"],
                "score": d["score"],
            }
            for d in demands[:10]
        ]

        date_range = {}
        if dates:
            sorted_dates = sorted(dates)
            date_range = {"from": sorted_dates[0], "to": sorted_dates[-1]}

        summary = {
            "total_units": len(units),
            "total_patterns": len(demands),
            "op_distribution": dict(op_dist),
            "top_patterns": top_patterns,
            "bugfix_ratio": bugfix_ratio,
            "invariant_count": invariant_count,
            "date_range": date_range,
        }

        save_json(summary, str(SEMANTIC_OUTPUT / "summary.json"))
        print(
            f"  Exported summary: {len(units)} units, {len(demands)} patterns, "
            f"bugfix ratio {bugfix_ratio:.1%}"
        )
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "summary.json"))
        return True

    # ------------------------------------------------------------------
    # CLI entry
    # ------------------------------------------------------------------

    def handle_run(self, remaining: list[str] | None = None) -> int:
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--stage", help="Run a specific stage instead of all")
        args = parser.parse_args(argv)

        if args.stage:
            if args.stage not in self.STAGES:
                print(
                    f"[{self.PIPELINE}] Unknown stage: {args.stage}. "
                    f"Available: {', '.join(self.STAGES)}"
                )
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
