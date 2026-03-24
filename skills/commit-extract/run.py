#!/usr/bin/env python3
"""commit-extract skill - LLM-only extraction with interactive range selection."""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState
from src.skill_runner import SkillRunner
from src.io_utils import load_json, load_jsonl, append_jsonl, save_json
from src.commit_semantic.git_utils import get_commit_list

_bootstrap_spec = importlib.util.spec_from_file_location(
    "commit_extract_bootstrap",
    str(Path(__file__).with_name("bootstrap.py")),
)
_bootstrap = importlib.util.module_from_spec(_bootstrap_spec)
assert _bootstrap_spec.loader is not None
_bootstrap_spec.loader.exec_module(_bootstrap)
build_bootstrap_context = _bootstrap.build_bootstrap_context
build_reliability_summary = _bootstrap.build_reliability_summary
determine_bootstrap_mode = _bootstrap.determine_bootstrap_mode
extract_shared_hints_for_prompt = _bootstrap.extract_shared_hints_for_prompt
write_bootstrap_context = _bootstrap.write_bootstrap_context

logger = logging.getLogger(__name__)

OUTPUT_BASE = Path("data/commit-extract")
TMP_DIR = OUTPUT_BASE / "tmp"
USE_TASK_AGENTS_ENV = "COMMIT_EXTRACT_USE_TASK_AGENTS"

# Adaptive batching constants
WEIGHT_BUDGET = 3000
MAX_COMMITS_PER_BATCH = 15
BINARY_FILE_WEIGHT = 500


def parse_stat(stat_output: str) -> int:
    """Parse git show --stat output to extract weight."""
    weight = 0
    binary_count = len(re.findall(r'Bin \d+ -> \d+ bytes', stat_output))
    weight += binary_count * BINARY_FILE_WEIGHT

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
    """Split SHAs into batches by weight budget and count cap."""
    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_weight = 0

    for sha, weight in sha_weights:
        if weight > WEIGHT_BUDGET:
            if current_batch:
                batches.append(current_batch)
                current_batch = []
                current_weight = 0
            batches.append([sha])
            continue

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
    """Merge tmp/*.jsonl into YYYY-MM.jsonl files."""
    tmp_files = sorted(tmp_dir.glob("*.jsonl"))
    if not tmp_files:
        return 0

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

    by_month: dict[str, list[dict]] = defaultdict(list)
    for record in all_records.values():
        date_str = record.get("date", "")
        if date_str and len(date_str) >= 7:
            month_key = date_str[:7]
        else:
            month_key = "unknown"
        by_month[month_key].append(record)

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

    for tmp_file in tmp_files:
        tmp_file.unlink()
    try:
        tmp_dir.rmdir()
    except OSError:
        pass

    return total_new


class CommitExtractRunner(SkillRunner):
    """Runner for commit-extract pipeline - LLM only, no git fallback."""

    STAGES = ["collect"]
    PIPELINE = "commit-extract"

    def __init__(self):
        super().__init__()
        self.repo_path: str = "."
        self.commit_range: str | None = None
        self._prompt_content: str | None = None
        self._pending_shas: list[str] = []
        self.auto_confirm: bool = False
        self._shared_hints: dict | None = None
        self.skip_bootstrap: bool = False

    def _repo_context_file(self) -> Path:
        return OUTPUT_BASE / "repo-context.json"

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        if stage == "collect":
            return self._run_collect(state)
        return True

    def _get_prompt(self) -> str:
        """Load prompt from skill directory (prompt.md) or fallback to docs/."""
        if self._prompt_content is None:
            # Priority 1: skill directory
            skill_prompt = Path(__file__).parent / "prompt.md"
            if skill_prompt.exists():
                self._prompt_content = skill_prompt.read_text(encoding="utf-8")
            else:
                # Priority 2: docs directory (backward compatibility)
                docs_prompt = Path("docs/generate_commit.md")
                if docs_prompt.exists():
                    self._prompt_content = docs_prompt.read_text(encoding="utf-8")
                else:
                    raise FileNotFoundError(
                        "prompt.md not found in skill directory and "
                        "docs/generate_commit.md not found. "
                        "This file is required for LLM extraction."
                    )
        return self._prompt_content

    def _build_worker_prompt(self, shas: list[str]) -> str:
        """Build the full worker prompt: shared hints + instructions + generate_commit.md."""
        prompt = self._get_prompt()
        sha_list = "\n".join(f"- {sha}" for sha in shas)
        shared_hints_block = ""
        if self._shared_hints is not None:
            shared_hints_block = (
                "## Shared Hints\n\n"
                f"{json.dumps(self._shared_hints, indent=2, sort_keys=True)}\n\n"
            )
        prefix = (
            "You are a commit analysis worker. Process the following SHA list one by one.\n"
            "For each SHA:\n"
            "1. Run: git show --stat --summary {sha}\n"
            "2. Run: git show {sha}\n"
            "3. Analyze the patch according to the prompt rules below\n"
            "4. Output exactly one JSON object\n"
            "5. Append the JSON object as one line to the output file\n\n"
            "Process each SHA independently. Do not accumulate patch content in context.\n\n"
            f"{shared_hints_block}"
            f"## SHA List\n\n{sha_list}\n\n"
            "## Analysis Prompt\n\n"
        )
        return prefix + prompt

    def _select_range_interactive(self) -> str | None:
        """Interactive range selection. Returns commit range string or None."""
        print("\n  Select commit range:")
        print("    1) Last 30 commits")
        print("    2) Last 90 commits")
        print("    3) Last 30 days")
        print("    4) Last 90 days")
        print("    5) All commits")
        print("    6) Custom range (e.g., HEAD~50..HEAD)")
        print("    7) Date range (YYYY-MM-DD to YYYY-MM-DD)")
        print()

        choice = input("  Choice [1-7]: ").strip()

        if choice == "1":
            return "HEAD~30..HEAD"
        elif choice == "2":
            return "HEAD~90..HEAD"
        elif choice == "3":
            since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            return f"--since={since}"
        elif choice == "4":
            since = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            return f"--since={since}"
        elif choice == "5":
            return None  # all commits
        elif choice == "6":
            custom = input("  Enter range (e.g., HEAD~50..HEAD): ").strip()
            return custom if custom else None
        elif choice == "7":
            start = input("  Start date (YYYY-MM-DD): ").strip()
            end = input("  End date (YYYY-MM-DD): ").strip()
            if start and end:
                return f"--since={start} --until={end}"
            elif start:
                return f"--since={start}"
            return None
        else:
            print("  Invalid choice, using all commits")
            return None

    def _confirm_extraction(self, count: int) -> bool:
        """Ask user to confirm before LLM extraction."""
        if self.auto_confirm:
            print(f"  Auto-confirming extraction of {count} commits (--yes)")
            return True

        # Non-TTY without --yes: cannot prompt, require explicit confirmation
        if not sys.stdin.isatty():
            print(f"\n  Error: Non-interactive mode requires --yes flag to confirm")
            print(f"  (About to extract {count} commits)")
            return False

        print(f"\n  About to extract {count} commits using LLM analysis.")
        print("  This will:")
        print("    - Read docs/generate_commit.md as the analysis prompt")
        print("    - Use Claude to analyze each commit diff")
        print("    - Take approximately ~30s per commit")
        print(f"    - Estimated time: ~{count * 30 // 60} minutes")
        print()

        confirm = input("  Continue? [Y/n]: ").strip().lower()
        return confirm in ("y", "yes", "")

    def _run_collect(self, state: HarnessState) -> bool:
        """Orchestrator: SHA collection → stat estimation → adaptive batching → worker manifest."""
        print(f"\n[{self.PIPELINE}] Collecting commits")
        print(f"  Repo: {self.repo_path}")

        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

        repo_context_path = self._repo_context_file()
        current_fingerprint = _bootstrap.compute_bootstrap_fingerprint(Path(self.repo_path))
        existing_repo_context = None
        if repo_context_path.exists():
            try:
                existing_repo_context = load_json(str(repo_context_path))
            except Exception:
                existing_repo_context = None

        mode = determine_bootstrap_mode(
            existing_repo_context,
            current_fingerprint=current_fingerprint,
            skip_bootstrap=self.skip_bootstrap,
        )

        if self.skip_bootstrap:
            repo_context = build_bootstrap_context(Path(self.repo_path))
            repo_context["summary"] = build_reliability_summary(
                repo_context["shared_hints"],
                fingerprint=current_fingerprint,
                bootstrap_status="bypass",
                used_cached_context=False,
                degraded_reasons=[],
                bypass_reason="skip-bootstrap",
            )
            self._shared_hints = None
        else:
            if mode["bootstrap_status"] == "full" and isinstance(existing_repo_context, dict):
                repo_context = existing_repo_context
            elif mode["bootstrap_status"] == "degraded" and isinstance(existing_repo_context, dict):
                repo_context = existing_repo_context
            else:
                repo_context = build_bootstrap_context(Path(self.repo_path))
                built_mode = determine_bootstrap_mode(
                    repo_context,
                    current_fingerprint=current_fingerprint,
                    skip_bootstrap=False,
                )
                repo_context["summary"] = build_reliability_summary(
                    repo_context["shared_hints"],
                    fingerprint=current_fingerprint,
                    bootstrap_status=built_mode["bootstrap_status"],
                    used_cached_context=built_mode["used_cached_context"],
                    degraded_reasons=built_mode["degraded_reasons"],
                    bypass_reason=built_mode["bypass_reason"],
                )
                mode = built_mode

            if mode["bootstrap_status"] == "full":
                self._shared_hints = extract_shared_hints_for_prompt(repo_context)
            elif mode["bootstrap_status"] == "degraded":
                if "empty-shared-hints" in mode.get("degraded_reasons", []):
                    self._shared_hints = None
                else:
                    shared_hints = extract_shared_hints_for_prompt(repo_context)
                    shared_hints["local_capabilities"] = shared_hints.get("local_capabilities", [])[:1]
                    self._shared_hints = shared_hints
            else:
                self._shared_hints = None

        write_bootstrap_context(repo_context_path, repo_context)
        self.add_artifact(state, str(repo_context_path))

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
        self._pending_shas = new_shas

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
            existing_shas = get_existing_shas(OUTPUT_BASE)
            new_shas = [s for s in all_shas if s not in existing_shas]
            self._pending_shas = new_shas
            if not new_shas:
                print("  All commits now processed after merge")
                return True

        # 4. Confirm before LLM extraction
        if not self._confirm_extraction(len(new_shas)):
            print("  Cancelled — non-interactive mode requires --yes flag")
            return False

        # 5. Weight estimation via git show --stat
        print(f"  Estimating weights for {len(new_shas)} commits...")
        sha_weights = []
        for sha in new_shas:
            weight = get_stat_weight(self.repo_path, sha)
            sha_weights.append((sha, weight))

        # 6. Adaptive batching
        batches = adaptive_batch(sha_weights)
        print(f"  Created {len(batches)} batches")

        # 7. Create batch manifest for workers
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        manifest = {
            "repo_path": self.repo_path,
            "total_shas": len(new_shas),
            "total_batches": len(batches),
            "prompt": self._build_worker_prompt(new_shas),
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

        # 8. Enable LLM extraction (task-agent mode)
        print(f"  Task-agent orchestration enabled (LLM extraction)")
        print(f"  Workers should write to {TMP_DIR}/batch_NNNN.jsonl")
        print("  After all workers complete, run merge to consolidate.")
        os.environ[USE_TASK_AGENTS_ENV] = "1"

        self.add_artifact(state, str(OUTPUT_BASE))
        return True

    def handle_status(self) -> int:
        """Show current extraction status and progress."""
        print(f"\n[{self.PIPELINE}] Status")
        print(f"  Repo: {self.repo_path}")

        # 1. Check existing output
        output_files = sorted(OUTPUT_BASE.glob("*.jsonl"))
        total_extracted = 0
        for f in output_files:
            if f.name != "tmp":
                records = list(load_jsonl(str(f), skip_errors=True))
                total_extracted += len(records)
                print(f"  ✓ {f.name}: {len(records)} commits")

        # 2. Check manifest and workers
        manifest_path = TMP_DIR / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text())
            total_batches = manifest.get("total_batches", 0)
            total_shas = manifest.get("total_shas", 0)

            # Count completed batches by actual SHA count, not file existence.
            # - Before merge: batch_*.jsonl files exist; count JSONL lines
            # - After merge: batch files are deleted by merge_tmp_files();
            #   count SHAs from merged YYYY-MM.jsonl files instead
            pending_batch_files = list(TMP_DIR.glob("batch_*.jsonl"))
            if pending_batch_files:
                # Batch files still exist — count lines per batch
                completed = 0
                for batch in manifest.get("batches", []):
                    output_file = Path(batch.get("output_path", ""))
                    if output_file.exists():
                        sha_count = sum(1 for _ in load_jsonl(str(output_file), skip_errors=True))
                        # A batch is complete when it has all its SHAs
                        if sha_count >= batch.get("sha_count", 1):
                            completed += 1
            else:
                # Batch files deleted — merge already ran; use merged output
                completed = total_batches
                total_shas = sum(
                    1 for _ in load_jsonl(str(f), skip_errors=True)
                    for f in OUTPUT_BASE.glob("*.jsonl")
                )

            print(f"\n  Workers:")
            print(f"    Total batches: {total_batches}")
            print(f"    Completed: {completed}/{total_batches}")
            print(f"    Pending: {total_batches - completed}")
            print(f"    Total SHAs to extract: {total_shas}")
            if not pending_batch_files:
                print(f"    SHAs merged into output: {total_shas}")

            if completed < total_batches:
                print(f"\n  Run workers to process pending batches:")
                print(f"    Workers read: {TMP_DIR}/manifest.json")
                print(f"    Workers write: {TMP_DIR}/batch_*.jsonl")
                print(f"    Then merge: python skills/commit-extract/run.py --merge")
        else:
            print(f"\n  No active extraction. Run with:")
            print(f"    python skills/commit-extract/run.py")

        print(f"\n  Output directory: {OUTPUT_BASE}")
        return 0

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
        parser.add_argument("--status", action="store_true", help="Show extraction status")
        parser.add_argument("--interactive", "-i", action="store_true",
                          help="Interactive mode: select range and confirm")
        parser.add_argument("--yes", "-y", action="store_true",
                          help="Auto-confirm extraction without prompting")
        parser.add_argument("--skip-bootstrap", action="store_true",
                          help="Bypass shared bootstrap context for this run")
        args = parser.parse_args(argv)

        if args.merge:
            return self.handle_merge()
        if args.status:
            return self.handle_status()

        self.repo_path = args.repo
        self.auto_confirm = args.yes
        self.skip_bootstrap = args.skip_bootstrap

        if args.interactive:
            # Interactive mode
            self.commit_range = self._select_range_interactive()
            if self.commit_range:
                print(f"  Selected range: {self.commit_range}")
        elif args.range:
            # Specified range but still need confirmation (unless --yes)
            self.commit_range = args.range
            print(f"  Using specified range: {self.commit_range}")
        elif not sys.stdin.isatty():
            # Non-TTY without range: error out, don't auto-run
            print("Error: Non-interactive mode requires --range flag")
            print("  --range='HEAD~30..HEAD'")
            return 1
        else:
            # TTY but no args: enter interactive mode
            self.commit_range = self._select_range_interactive()
            if self.commit_range:
                print(f"  Selected range: {self.commit_range}")

        return super().handle_run()


def run_commit_extract() -> None:
    """Entry point for the commit-extract skill."""
    raise SystemExit(CommitExtractRunner().main())


if __name__ == "__main__":
    run_commit_extract()
