"""repo-structure skill — extract structured facts from codebase + git history.

Stages:
  1. sample    - Build sampling manifest from gsd dossier
  2. hotspot  - Consume commit-extract/commit-semantic → hotspot_map
  3. extract  - LLM workers extract facts from 7-file dossier (section-routed)
  4. augment  - LLM workers adjudicate architecture claims vs repo evidence
  5. validate - Schema + deduplication + conflict detection
  6. baseline - Source-aware arbitration → facts.vN.yaml

Output:
  data/repo-structure/baseline/facts.vN.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.skill_runner import SkillRunner, run_skill
from src.harness_state import HarnessState, load_state, save_state
from .preflight import check as preflight_check


OUTPUT_BASE = Path("data/repo-structure")
BATCH_SIZE = 20


class RepoStructureRunner(SkillRunner):
    """Runner for repo-structure pipeline."""

    STAGES = ["sample", "hotspot", "extract", "augment", "validate", "baseline"]
    PIPELINE = "repo-structure"

    def __init__(self):
        super().__init__()
        self.gsd_root: str | None = None

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        method_name = f"_run_{stage}"
        method = getattr(self, method_name, None)
        if method is None:
            print(f"  Stage '{stage}' not yet implemented")
            return True
        return method(state)

    # -------------------------------------------------------------------------
    # Preflight
    # -------------------------------------------------------------------------

    def handle_check(self) -> int:
        """Run preflight checks and print structured report."""
        result = preflight_check()
        self._print_preflight_report(result)
        return 0 if result.ok else 1

    def _print_preflight_report(self, result) -> None:
        """Print preflight result in human-readable format."""
        if result.ok and not result.warnings:
            print("[repo-structure] preflight OK — all required inputs present")
            return

        print(f"[repo-structure] preflight: repo HEAD = {result.repo_head[:8]}")

        if result.missing:
            print("\n  MISSING (required):")
            for m in result.missing:
                print(f"    [{m.code}] {m.subject}: {m.message}")
                if m.producer:
                    print(f"               producer: {m.producer}")
                if m.suggestion:
                    print(f"               suggestion: {m.suggestion}")

        if result.invalid:
            print("\n  INVALID:")
            for m in result.invalid:
                print(f"    [{m.code}] {m.subject}: {m.message}")

        if result.warnings:
            print("\n  WARNINGS:")
            for w in result.warnings:
                print(f"    [{w.code}] {w.subject}: {w.message}")

        if result.missing or result.invalid:
            print("\n[repo-structure] preflight FAILED")
        else:
            print("\n[repo-structure] preflight OK (with warnings)")

    # -------------------------------------------------------------------------
    # Stage implementations (stubs — filled in Tasks 4-8)
    # -------------------------------------------------------------------------

    def _run_sample(self, state: HarnessState) -> bool:
        """Stage 1: Build sampling manifest from gsd dossier."""
        print("  [TODO] sample stage not yet implemented")
        return True

    def _run_hotspot(self, state: HarnessState) -> bool:
        """Stage 2: Consume commit-extract + commit-semantic → hotspot_map."""
        print("  [TODO] hotspot stage not yet implemented")
        return True

    def _run_extract(self, state: HarnessState) -> bool:
        """Stage 3: LLM workers extract facts from 7-file dossier."""
        print("  [TODO] extract stage not yet implemented")
        return True

    def _run_augment(self, state: HarnessState) -> bool:
        """Stage 4: LLM workers adjudicate arch claims vs repo evidence."""
        print("  [TODO] augment stage not yet implemented")
        return True

    def _run_validate(self, state: HarnessState) -> bool:
        """Stage 5: Schema checks, deduplication, conflict detection."""
        print("  [TODO] validate stage not yet implemented")
        return True

    def _run_baseline(self, state: HarnessState) -> bool:
        """Stage 6: Arbitration → facts.vN.yaml."""
        print("  [TODO] baseline stage not yet implemented")
        return True

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_repo_head(self) -> str:
        """Get current HEAD commit."""
        import subprocess
        try:
            r = subprocess.run(["git", "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True)
            return r.stdout.strip()
        except subprocess.CalledProcessError:
            return "unknown"

    def _next_version(self, artifact_name: str) -> str:
        """Get next version number for an artifact."""
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(maps_dir.glob(f"{artifact_name}.v*.yaml"))
        if not existing:
            return "v0"
        last = existing[-1].stem.split(".")[-1]
        num = int(last[1:]) + 1
        return f"v{num}"

    # -------------------------------------------------------------------------
    # Override run to inject preflight
    # -------------------------------------------------------------------------

    def handle_run(self, remaining: list[str] | None = None) -> int:
        """Override to parse gsd-root arg and run preflight before execution."""
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--gsd-root", default=None)
        args, extra = parser.parse_known_args(argv)
        self.gsd_root = args.gsd_root

        # Run preflight first
        print("[repo-structure] Running preflight checks...")
        result = preflight_check()
        self._print_preflight_report(result)
        if not result.ok:
            print("\n[repo-structure] Aborting due to preflight failure.")
            return 1

        return super().handle_run(extra if extra else None)

    def main(self, argv: list[str] | None = None) -> int:
        """Extended main to support 'check' command."""
        import sys as _sys
        if argv is None:
            raw = _sys.argv[1:]
        else:
            raw = argv
        if len(raw) == 1 and isinstance(raw[0], str) and " " in raw[0]:
            raw = raw[0].split()

        parser = argparse.ArgumentParser(description="repo-structure skill")
        parser.add_argument("intent", nargs="?", default="run")
        args, extra = parser.parse_known_args(raw)

        if args.intent == "check":
            return self.handle_check()

        handlers = {
            "status": self.handle_status,
            "reset": self.handle_reset,
            "step": self.handle_step,
            "resume": self.handle_resume,
            "run": lambda: self.handle_run(extra if extra else []),
        }
        handler = handlers.get(args.intent, handlers["run"])
        return handler()


if __name__ == "__main__":
    run_skill(RepoStructureRunner)
