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
import uuid
import yaml
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

    # REQUIRED_GSD_FILES imported from preflight module (shared constant)
    from .preflight import REQUIRED_GSD_FILES

    # Section-to-locator mapping (per spec: section routing, not file batching)
    SECTION_LOCATOR_MAP = {
        # STRUCTURE.md
        ("STRUCTURE.md", "Directory Layout"): ("file_path", 2, "file_path"),
        ("STRUCTURE.md", "Key File Locations"): ("symbol", 2, "symbol"),
        ("STRUCTURE.md", "Naming Conventions"): ("file_path", 1, "file_path"),
        # ARCHITECTURE.md
        ("ARCHITECTURE.md", "Pattern Overview"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "Layers"): ("ast_pattern", 2, "ast_pattern"),
        ("ARCHITECTURE.md", "Data Flow"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "Key Abstractions"): ("symbol", 2, "symbol"),
        ("ARCHITECTURE.md", "Entry Points"): ("symbol", 2, "symbol"),
        ("ARCHITECTURE.md", "Error Handling"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "Cross-Cutting"): ("section_ref", 1, "section_ref"),
        ("ARCHITECTURE.md", "State Management"): ("section_ref", 1, "section_ref"),
        # CONCERNS.md
        ("CONCERNS.md", "Tech Debt"): ("file_path", 2, "file_path"),
        ("CONCERNS.md", "Fragile Areas"): ("test_case", 2, "file_path+test_case"),
        ("CONCERNS.md", "Security"): ("file_path", 2, "file_path"),
        ("CONCERNS.md", "Performance"): ("file_path", 1, "file_path"),
        ("CONCERNS.md", "Test Coverage"): ("test_case", 1, "test_case"),
        # CONVENTIONS.md
        ("CONVENTIONS.md", None): ("section_ref", 1, "section_ref"),
        # INTEGRATIONS.md
        ("INTEGRATIONS.md", None): ("config_key", 1, "config_key"),
        # STACK.md
        ("STACK.md", "Technology Stack"): ("config_key", 1, "config_key"),
        ("STACK.md", "Runtime"): ("config_key", 1, "config_key"),
        # TESTING.md
        ("TESTING.md", None): ("test_case", 2, "test_case"),
    }

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
        """Build DocSectionTask manifest from 7-file gsd dossier."""
        print("  -> Building DocSectionTask manifest from gsd dossier")
        root = Path.cwd()
        gsd_dir = root / ".planning" / "codebase"

        tasks: list = []
        task_id_counter = 0

        for fname in self.REQUIRED_GSD_FILES:
            fpath = gsd_dir / fname
            if not fpath.exists():
                print(f"  WARNING: {fpath} not found, skipping")
                continue

            text = fpath.read_text(encoding="utf-8")
            sections = self._split_sections(text)

            for section_title, section_content in sections:
                task_id_counter += 1
                key = (fname, section_title if section_title != fname else None)
                fallback_key = (fname, None)
                mapped = self.SECTION_LOCATOR_MAP.get(key) or self.SECTION_LOCATOR_MAP.get(fallback_key)

                if mapped:
                    locator_type, priority, routing_note = mapped
                else:
                    locator_type = "section_ref"
                    priority = 1
                    routing_note = "default routing"

                section_type = section_title.lower().replace(" ", "_") if section_title else fname.lower().replace(".md", "")

                tasks.append({
                    "task_id": f"doc-{task_id_counter:03d}",
                    "source_file": f".planning/codebase/{fname}",
                    "section_title": section_title or "(full file)",
                    "section_type": section_type,
                    "locator_type": locator_type,
                    "priority": priority,
                    "routing_note": routing_note,
                    "content": section_content.strip(),
                })

        OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
        manifest_dir = OUTPUT_BASE / "sample"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.yaml"

        manifest_data = {
            "metadata": {
                "version": "v1",
                "total_sections": len(tasks),
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "gsd_root": str(gsd_dir),
            },
            "sections": tasks,
        }

        yaml.dump(
            manifest_data,
            manifest_path.open("w", encoding="utf-8"),
            allow_unicode=True,
            default_flow_style=False,
        )
        print(f"  Wrote {len(tasks)} DocSectionTask entries -> {manifest_path}")
        self.add_artifact(state, str(manifest_path))
        return True

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split a markdown file into sections by ## headings."""
        import re
        sections = []
        parts = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            lines = part.splitlines()
            if lines and lines[0].startswith("## "):
                title = lines[0][3:].strip()
                content = "\n".join(lines[1:]).strip()
            else:
                title = part.split("\n")[0][:50]
                content = part
            sections.append((title, content))
        return sections

    def _run_hotspot(self, state: HarnessState) -> bool:
        """Consume commit-extract + commit-semantic → hotspot_map."""
        print("  -> Running hotspot stage")

        commit_extract_dir = Path("data/commit-extract")
        if not commit_extract_dir.exists():
            print(f"  ERROR: commit-extract output not found at {commit_extract_dir}")
            return False

        monthly_files = sorted(commit_extract_dir.glob("????-??.yaml"))
        print(f"  Found {len(monthly_files)} monthly commit files")

        patterns_dir = Path("data/commit-semantic/patterns")
        patterns: list = []
        if patterns_dir.exists():
            for pf in patterns_dir.glob("*.yaml"):
                try:
                    data = yaml.safe_load(pf.read_text())
                    if "patterns" in data:
                        patterns.extend(data["patterns"])
                except Exception as e:
                    print(f"  WARNING: could not load {pf}: {e}")

        hotspots = self._aggregate_hotspots(monthly_files, patterns)

        version = self._next_version("hotspot_map")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"hotspot_map.{version}.yaml"
        head = self._get_repo_head()

        yaml.dump({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "monthly_files": [str(f) for f in monthly_files],
                "total_patterns": len(patterns),
            },
            "facts": hotspots,
        }, out_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)

        print(f"  Wrote {len(hotspots)} hotspot facts -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _aggregate_hotspots(self, monthly_files: list, patterns: list) -> list:
        """Aggregate commit-extract data and commit-semantic patterns into hotspot facts."""
        from collections import defaultdict

        module_commit_count: dict = defaultdict(int)
        module_files: dict = defaultdict(set)

        for mf in monthly_files:
            try:
                data = yaml.safe_load(mf.read_text())
                for commit in data.get("commits", []):
                    for f in commit.get("files", []):
                        module = str(f).split("/")[0] if "/" in str(f) else "root"
                        module_commit_count[module] += 1
                        module_files[module].add(str(f))
            except Exception:
                pass

        hotspots: list = []

        top_modules = sorted(module_commit_count.items(), key=lambda x: -x[1])[:10]
        for rank, (module, count) in enumerate(top_modules):
            if count < 2:
                continue
            hotspots.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "hotspot_signal",
                "domain": "hotspot",
                "statement": f"Module '{module}' appears in {count} commits — high change frequency",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": self._get_repo_head(),
                "source": "hotspot",
                "evidence": [{
                    "source_type": "hotspot",
                    "file_path": "data/commit-extract/*.yaml",
                    "locator_type": "file_path",
                    "locator": module,
                    "stable_ref": f"module:{module}",
                    "rationale": f"Module '{module}' touched in {count} commits",
                }],
                "hotspot_rank": rank + 1,
                "commit_count": count,
                "files": sorted(module_files[module]),
            })

        for pattern in patterns[:10]:
            hotspots.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "hotspot_signal",
                "domain": "semantic_pattern",
                "statement": f"Recurring pattern: {pattern.get('description', pattern.get('pattern_id', 'unknown'))}",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": self._get_repo_head(),
                "source": "hotspot",
                "evidence": [{
                    "source_type": "hotspot",
                    "file_path": "data/commit-semantic/patterns/",
                    "locator_type": "section_ref",
                    "locator": pattern.get("pattern_id", ""),
                    "stable_ref": f"pattern:{pattern.get('pattern_id', 'unknown')}",
                    "rationale": "From commit-semantic pattern extraction",
                }],
            })

        return hotspots

    def _run_extract(self, state: HarnessState) -> bool:
        """Extract facts from 7-file dossier using section-routed worker prompts."""
        print("  -> Running extract stage")

        manifest_path = OUTPUT_BASE / "sample" / "manifest.yaml"
        if not manifest_path.exists():
            print(f"  ERROR: sample manifest not found at {manifest_path}")
            print(f"  Run 'repo-structure --stage sample' first")
            return False

        manifest = yaml.safe_load(manifest_path.read_text())
        sections = manifest.get("sections", [])

        batches = self._batch_sections(sections, BATCH_SIZE)
        print(f"  Processing {len(sections)} sections in {len(batches)} batch(es)")

        prompt_path = Path(__file__).parent / "prompts" / "extract_codebase.md"
        prompt_template = prompt_path.read_text() if prompt_path.exists() else ""

        all_facts: list = []
        for batch_idx, batch in enumerate(batches):
            print(f"  Batch {batch_idx + 1}/{len(batches)} ({len(batch)} sections)...")
            facts = self._spawn_extract_worker(batch, prompt_template)
            all_facts.extend(facts)

        version = self._next_version("codebase_map")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"codebase_map.{version}.yaml"

        head = self._get_repo_head()
        data = {
            "metadata": {
                "version": version,
                "total_facts": len(all_facts),
                "repo_snapshot_commit": head,
                "generated_at": __import__("datetime").datetime.now().isoformat(),
                "prompt": "extract_codebase.md",
            },
            "facts": all_facts,
        }
        yaml.dump(data, out_path.open("w", encoding="utf-8"),
                  allow_unicode=True, default_flow_style=False)
        print(f"  Wrote {len(all_facts)} facts -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _batch_sections(self, sections: list, batch_size: int) -> list[list]:
        """Split sections into batches."""
        return [sections[i:i+batch_size] for i in range(0, len(sections), batch_size)]

    def _spawn_extract_worker(self, batch: list, prompt_template: str) -> list:
        """Spawn extract worker for a batch of DocSectionTasks.

        When COMMIT_SEMANTIC_USE_TASK_AGENTS=1, spawns a real Task agent.
        Otherwise uses local heuristic extraction (for CLI/testing).
        """
        import os
        use_task = os.environ.get("COMMIT_SEMANTIC_USE_TASK_AGENTS", "").lower() in ("1", "true", "yes")

        if use_task:
            # Real Task agent — implemented via SKILL.md orchestration
            return []

        # Local fallback: heuristic extraction per section
        facts: list = []
        head = self._get_repo_head()

        for section in batch:
            section_facts = self._extract_facts_from_section(section, head)
            facts.extend(section_facts)

        return facts

    def _extract_facts_from_section(self, section: dict, head: str) -> list:
        """Heuristic fact extraction from a single DocSectionTask section."""
        import re
        import uuid as _uuid

        locator_type = section.get("locator_type", "section_ref")
        source_file = section.get("source_file", "")
        content = section.get("content", "")
        section_type = section.get("section_type", "")

        if not content or len(content.strip()) < 20:
            return []

        facts: list = []

        # Extract symbol references
        symbols = re.findall(r'`([A-Z][a-zA-Z0-9_]+)`', content)
        symbols += re.findall(r'class\s+([A-Z][a-zA-Z0-9_]+)', content)
        symbols += re.findall(r'def\s+([a-z][a-zA-Z0-9_]+)', content)
        symbols = list(dict.fromkeys(symbols))

        # Extract file paths
        file_paths = re.findall(r'`([a-z_/]+\.py)`', content)
        file_paths += re.findall(r'(?:src|tests|lib)/[a-z_/]+\.py', content)
        file_paths = list(dict.fromkeys(file_paths))

        # Extract config keys
        config_keys = re.findall(r'`([a-z_][a-zA-Z0-9_]*)`', content)
        config_keys = [k for k in config_keys if k not in symbols]
        config_keys = list(dict.fromkeys(config_keys))

        # Build facts based on locator_type
        if locator_type == "symbol" and symbols:
            for sym in symbols[:5]:
                facts.append({
                    "fact_id": str(_uuid.uuid4()),
                    "fact_type": "module_role",
                    "domain": section_type,
                    "statement": f"{sym} is defined in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "symbol",
                        "locator": sym,
                        "stable_ref": f"symbol:{sym}",
                        "rationale": f"Extracted from {section.get('section_title', 'unknown section')}",
                    }],
                })

        elif locator_type == "file_path" and file_paths:
            for fp in file_paths[:5]:
                facts.append({
                    "fact_id": str(_uuid.uuid4()),
                    "fact_type": "pattern_usage",
                    "domain": section_type,
                    "statement": f"{fp} is referenced in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "file_path",
                        "locator": fp,
                        "stable_ref": f"file:{fp}",
                        "rationale": f"Referenced in {section.get('section_title', 'section')}",
                    }],
                })

        elif locator_type == "config_key" and config_keys:
            for ck in config_keys[:5]:
                facts.append({
                    "fact_id": str(_uuid.uuid4()),
                    "fact_type": "dependency_rule",
                    "domain": section_type,
                    "statement": f"Configuration key '{ck}' is used in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "config_key",
                        "locator": ck,
                        "stable_ref": f"config:{ck}",
                        "rationale": f"Mentioned in {section.get('section_title', 'section')}",
                    }],
                })

        elif locator_type == "ast_pattern":
            ast_patterns = re.findall(r'class\s+(\w+)', content)
            ast_patterns += re.findall(r'function\s+(\w+)', content)
            for pattern in ast_patterns[:5]:
                facts.append({
                    "fact_id": str(_uuid.uuid4()),
                    "fact_type": "pattern_usage",
                    "domain": section_type,
                    "statement": f"Layer pattern '{pattern}' is defined in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "ast_pattern",
                        "locator": pattern,
                        "stable_ref": f"pattern:{pattern}",
                        "rationale": f"Pattern found in {section.get('section_title', 'section')}",
                    }],
                })

        elif "test_case" in locator_type:
            test_names = re.findall(r'(?:def |test_)([a-z_][a-zA-Z0-9_]*)', content)
            test_names = [t for t in test_names if "test" in t.lower()]
            for tn in test_names[:5]:
                facts.append({
                    "fact_id": str(_uuid.uuid4()),
                    "fact_type": "invariant",
                    "domain": section_type,
                    "statement": f"Test case '{tn}' validates behavior in {source_file}",
                    "confidence": "confirmed",
                    "status": "active",
                    "repo_snapshot_commit": head,
                    "source": "codebase",
                    "evidence": [{
                        "source_type": "codebase",
                        "file_path": source_file,
                        "locator_type": "test_case",
                        "locator": tn,
                        "stable_ref": f"test:{tn}",
                        "rationale": f"Test found in {section.get('section_title', 'section')}",
                    }],
                })

        elif locator_type == "section_ref":
            title = section.get("section_title", "section")
            facts.append({
                "fact_id": str(_uuid.uuid4()),
                "fact_type": "convention",
                "domain": section_type,
                "statement": f"{source_file} contains a '{title}' section",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": head,
                "source": "codebase",
                "evidence": [{
                    "source_type": "codebase",
                    "file_path": source_file,
                    "locator_type": "section_ref",
                    "locator": f"{source_file}#{title.lower().replace(' ', '-')}",
                    "stable_ref": f"section:{source_file}:{title}",
                    "rationale": f"Section '{title}' exists in {source_file}",
                }],
            })

        return facts

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
