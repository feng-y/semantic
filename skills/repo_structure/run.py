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
import re
import shutil
import subprocess
import sys
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import save_yaml, load_yaml
from src.skill_runner import SkillRunner, run_skill
from src.harness_state import HarnessState
from .preflight import check as preflight_check, REQUIRED_GSD_FILES


OUTPUT_BASE = Path("data/repo-structure")
BATCH_SIZE = 20

# Compiled once at module load
_SECTION_HEADING_RE = re.compile(r"(?=^##\s+)", flags=re.MULTILINE)

# Compiled regex patterns for fact extraction (avoid re-compilation per section)
_RE_PATTERNS = {
    "backtick_symbols": re.compile(r'`([A-Z][a-zA-Z0-9_]+)`'),
    "class_def": re.compile(r'class\s+([A-Z][a-zA-Z0-9_]+)'),
    "fn_def": re.compile(r'def\s+([a-z][a-zA-Z0-9_]+)'),
    "backtick_path": re.compile(r'`([a-z_/]+\.py)`'),
    "slash_path": re.compile(r'(?:src|tests|lib)/[a-z_/]+\.py'),
    "backtick_key": re.compile(r'`([a-z_][a-zA-Z0-9_]*)`'),
    "class_or_fn": re.compile(r'(?:class|function)\s+(\w+)'),
    "test_name": re.compile(r'(?:def |test_)([a-z_][a-zA-Z0-9_]*)'),
}

# Valid locator types per spec
VALID_LOCATOR_TYPES = frozenset({
    "file_path", "symbol", "config_key",
    "section_ref", "test_case", "ast_pattern",
})


class RepoStructureRunner(SkillRunner):
    """Runner for repo-structure pipeline."""

    STAGES = ["sample", "hotspot", "extract", "augment", "validate", "baseline"]
    PIPELINE = "repo-structure"

    VALID_FACT_TYPES = frozenset({
        "module_role", "dependency_rule", "boundary_constraint",
        "pattern_usage", "convention", "invariant", "hotspot_signal",
    })

    # Section-to-locator mapping (per spec: section routing, not file batching)
    SECTION_LOCATOR_MAP = {
        # STRUCTURE.md
        ("STRUCTURE.md", "Directory Layout"): ("file_path", 2),
        ("STRUCTURE.md", "Key File Locations"): ("symbol", 2),
        ("STRUCTURE.md", "Naming Conventions"): ("file_path", 1),
        # ARCHITECTURE.md
        ("ARCHITECTURE.md", "Pattern Overview"): ("section_ref", 1),
        ("ARCHITECTURE.md", "Layers"): ("ast_pattern", 2),
        ("ARCHITECTURE.md", "Data Flow"): ("section_ref", 1),
        ("ARCHITECTURE.md", "Key Abstractions"): ("symbol", 2),
        ("ARCHITECTURE.md", "Entry Points"): ("symbol", 2),
        ("ARCHITECTURE.md", "Error Handling"): ("section_ref", 1),
        ("ARCHITECTURE.md", "Cross-Cutting"): ("section_ref", 1),
        ("ARCHITECTURE.md", "State Management"): ("section_ref", 1),
        # CONCERNS.md
        ("CONCERNS.md", "Tech Debt"): ("file_path", 2),
        ("CONCERNS.md", "Fragile Areas"): ("test_case", 2),
        ("CONCERNS.md", "Security"): ("file_path", 2),
        ("CONCERNS.md", "Performance"): ("file_path", 1),
        ("CONCERNS.md", "Test Coverage"): ("test_case", 1),
        # CONVENTIONS.md
        ("CONVENTIONS.md", None): ("section_ref", 1),
        # INTEGRATIONS.md
        ("INTEGRATIONS.md", None): ("config_key", 1),
        # STACK.md
        ("STACK.md", "Technology Stack"): ("config_key", 1),
        ("STACK.md", "Runtime"): ("config_key", 1),
        # TESTING.md
        ("TESTING.md", None): ("test_case", 2),
    }

    def __init__(self):
        super().__init__()
        self._head: str | None = None  # cached HEAD commit

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        """Execute a single stage."""
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        method = getattr(self, f"_run_{stage}", None)
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
    # Stage implementations
    # -------------------------------------------------------------------------

    def _run_sample(self, state: HarnessState) -> bool:
        """Build DocSectionTask manifest from 7-file gsd dossier."""
        print("  -> Building DocSectionTask manifest from gsd dossier")
        gsd_dir = Path(".planning/codebase")
        tasks: list[dict[str, Any]] = []

        for fname in REQUIRED_GSD_FILES:
            fpath = gsd_dir / fname
            if not fpath.exists():
                print(f"  WARNING: {fpath} not found, skipping")
                continue
            text = fpath.read_text(encoding="utf-8")
            sections = self._split_sections(text)
            for section_title, section_content in sections:
                key = (fname, section_title if section_title != fname else None)
                mapped = self.SECTION_LOCATOR_MAP.get(key)
                if mapped:
                    locator_type, priority = mapped
                else:
                    locator_type, priority = "section_ref", 1
                section_type = (
                    section_title.lower().replace(" ", "_")
                    if section_title else fname.lower().replace(".md", "")
                )
                tasks.append({
                    "task_id": f"doc-{len(tasks) + 1:03d}",
                    "source_file": f".planning/codebase/{fname}",
                    "section_title": section_title or "(full file)",
                    "section_type": section_type,
                    "locator_type": locator_type,
                    "priority": priority,
                    "content": section_content.strip(),
                })

        manifest_dir = OUTPUT_BASE / "sample"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = manifest_dir / "manifest.yaml"
        manifest_data = {
            "metadata": {
                "version": "v1",
                "total_sections": len(tasks),
                "generated_at": datetime.now().isoformat(),
                "gsd_root": str(gsd_dir),
            },
            "sections": tasks,
        }
        save_yaml(manifest_data, str(manifest_path))
        print(f"  Wrote {len(tasks)} DocSectionTask entries -> {manifest_path}")
        self.add_artifact(state, str(manifest_path))
        return True

    def _split_sections(self, text: str) -> list[tuple[str, str]]:
        """Split a markdown file into sections by ## headings."""
        sections = []
        for part in _SECTION_HEADING_RE.split(text):
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
                    data = load_yaml(str(pf))
                    if "patterns" in data:
                        patterns.extend(data["patterns"])
                except Exception as e:
                    print(f"  WARNING: could not load {pf}: {e}")

        head = self._get_repo_head()
        hotspots = self._aggregate_hotspots(monthly_files, patterns, head)

        version = self._next_version("hotspot_map")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"hotspot_map.{version}.yaml"
        save_yaml({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "generated_at": datetime.now().isoformat(),
                "monthly_files": [str(f) for f in monthly_files],
                "total_patterns": len(patterns),
            },
            "facts": hotspots,
        }, str(out_path))
        print(f"  Wrote {len(hotspots)} hotspot facts -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _aggregate_hotspots(
        self, monthly_files: list[Path], patterns: list, head: str
    ) -> list[dict[str, Any]]:
        """Aggregate commit-extract data and commit-semantic patterns into hotspot facts."""
        module_commit_count: dict[str, int] = defaultdict(int)
        module_files: dict[str, set[str]] = defaultdict(set)

        for mf in monthly_files:
            try:
                data = load_yaml(str(mf))
                for commit in data.get("commits", []):
                    for f in commit.get("files", []):
                        module = str(f).split("/")[0] if "/" in str(f) else "root"
                        module_commit_count[module] += 1
                        module_files[module].add(str(f))
            except Exception as e:
                print(f"  WARNING: skipped malformed file {mf}: {e}")

        hotspots: list[dict[str, Any]] = []
        for rank, (module, count) in enumerate(
            sorted(module_commit_count.items(), key=lambda x: -x[1])[:10]
        ):
            if count < 2:
                continue
            hotspots.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "hotspot_signal",
                "domain": "hotspot",
                "statement": f"Module '{module}' appears in {count} commits — high change frequency",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": head,
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
            pid = pattern.get("pattern_id", "unknown")
            hotspots.append({
                "fact_id": str(uuid.uuid4()),
                "fact_type": "hotspot_signal",
                "domain": "semantic_pattern",
                "statement": f"Recurring pattern: {pattern.get('description', pid)}",
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": head,
                "source": "hotspot",
                "evidence": [{
                    "source_type": "hotspot",
                    "file_path": "data/commit-semantic/patterns/",
                    "locator_type": "section_ref",
                    "locator": pid,
                    "stable_ref": f"pattern:{pid}",
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

        manifest = load_yaml(str(manifest_path))
        sections = manifest.get("sections", [])
        batches = [sections[i:i + BATCH_SIZE] for i in range(0, len(sections), BATCH_SIZE)]
        print(f"  Processing {len(sections)} sections in {len(batches)} batch(es)")

        prompt_path = Path(__file__).parent / "prompts" / "extract_codebase.md"
        prompt_template = prompt_path.read_text() if prompt_path.exists() else ""

        head = self._get_repo_head()
        all_facts: list[dict[str, Any]] = []
        for batch_idx, batch in enumerate(batches):
            print(f"  Batch {batch_idx + 1}/{len(batches)} ({len(batch)} sections)...")
            facts = self._spawn_extract_worker(batch, prompt_template, head)
            all_facts.extend(facts)

        version = self._next_version("codebase_map")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"codebase_map.{version}.yaml"
        save_yaml({
            "metadata": {
                "version": version,
                "total_facts": len(all_facts),
                "repo_snapshot_commit": head,
                "generated_at": datetime.now().isoformat(),
                "prompt": "extract_codebase.md",
            },
            "facts": all_facts,
        }, str(out_path))
        print(f"  Wrote {len(all_facts)} facts -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _spawn_extract_worker(
        self, batch: list[dict[str, Any]], prompt_template: str, head: str
    ) -> list[dict[str, Any]]:
        """Spawn extract worker for a batch of DocSectionTasks.

        When COMMIT_SEMANTIC_USE_TASK_AGENTS=1, spawns a real Task agent.
        Otherwise uses local heuristic extraction (for CLI/testing).
        """
        import os
        if os.environ.get("COMMIT_SEMANTIC_USE_TASK_AGENTS", "").lower() in ("1", "true", "yes"):
            return []  # real Task agent via SKILL.md orchestration

        facts: list[dict[str, Any]] = []
        for section in batch:
            facts.extend(self._extract_facts_from_section(section, head))
        return facts

    def _extract_facts_from_section(
        self, section: dict[str, Any], head: str
    ) -> list[dict[str, Any]]:
        """Heuristic fact extraction from a single DocSectionTask section."""
        locator_type = section.get("locator_type", "section_ref")
        source_file = section.get("source_file", "")
        content = section.get("content", "")
        section_type = section.get("section_type", "")
        section_title = section.get("section_title", "section")

        if not content or len(content.strip()) < 20:
            return []

        facts: list[dict[str, Any]] = []
        symbols = _RE_PATTERNS["backtick_symbols"].findall(content)
        symbols += _RE_PATTERNS["class_def"].findall(content)
        symbols += _RE_PATTERNS["fn_def"].findall(content)
        symbols = list(dict.fromkeys(symbols))

        file_paths = _RE_PATTERNS["backtick_path"].findall(content)
        file_paths += _RE_PATTERNS["slash_path"].findall(content)
        file_paths = list(dict.fromkeys(file_paths))

        config_keys = _RE_PATTERNS["backtick_key"].findall(content)
        config_keys = [k for k in config_keys if k not in symbols]
        config_keys = list(dict.fromkeys(config_keys))

        def make_fact(
            fid: str, ftype: str, stmt: str, ltype: str, loc: str, stable: str
        ) -> dict[str, Any]:
            return {
                "fact_id": fid,
                "fact_type": ftype,
                "domain": section_type,
                "statement": stmt,
                "confidence": "confirmed",
                "status": "active",
                "repo_snapshot_commit": head,
                "source": "codebase",
                "evidence": [{
                    "source_type": "codebase",
                    "file_path": source_file,
                    "locator_type": ltype,
                    "locator": loc,
                    "stable_ref": stable,
                    "rationale": f"Extracted from '{section_title}'",
                }],
            }

        if locator_type == "symbol" and symbols:
            for sym in symbols[:5]:
                facts.append(make_fact(
                    str(uuid.uuid4()), "module_role",
                    f"{sym} is defined in {source_file}",
                    "symbol", sym, f"symbol:{sym}",
                ))
        elif locator_type == "file_path" and file_paths:
            for fp in file_paths[:5]:
                facts.append(make_fact(
                    str(uuid.uuid4()), "pattern_usage",
                    f"{fp} is referenced in {source_file}",
                    "file_path", fp, f"file:{fp}",
                ))
        elif locator_type == "config_key" and config_keys:
            for ck in config_keys[:5]:
                facts.append(make_fact(
                    str(uuid.uuid4()), "dependency_rule",
                    f"Configuration key '{ck}' is used in {source_file}",
                    "config_key", ck, f"config:{ck}",
                ))
        elif locator_type == "ast_pattern":
            patterns = _RE_PATTERNS["class_or_fn"].findall(content)
            for pat in patterns[:5]:
                facts.append(make_fact(
                    str(uuid.uuid4()), "pattern_usage",
                    f"Layer pattern '{pat}' is defined in {source_file}",
                    "ast_pattern", pat, f"pattern:{pat}",
                ))
        elif "test_case" in locator_type:
            test_names = _RE_PATTERNS["test_name"].findall(content)
            test_names = [t for t in test_names if "test" in t.lower()]
            for tn in test_names[:5]:
                facts.append(make_fact(
                    str(uuid.uuid4()), "invariant",
                    f"Test case '{tn}' validates behavior in {source_file}",
                    "test_case", tn, f"test:{tn}",
                ))
        elif locator_type == "section_ref":
            title_slug = section_title.lower().replace(" ", "-")
            facts.append(make_fact(
                str(uuid.uuid4()), "convention",
                f"{source_file} contains a '{section_title}' section",
                "section_ref",
                f"{source_file}#{title_slug}",
                f"section:{source_file}:{section_title}",
            ))

        return facts

    def _run_augment(self, state: HarnessState) -> bool:
        """Two-phase architecture augmentation: Python collection + LLM adjudication."""
        print("  -> Running augment stage")
        arch_doc = Path("docs/ARCHITECTURE.md")
        if not arch_doc.exists():
            print("  WARNING: docs/ARCHITECTURE.md not found — emitting empty augment")
            version = self._next_version("architect_augment")
            maps_dir = OUTPUT_BASE / "maps"
            maps_dir.mkdir(parents=True, exist_ok=True)
            out_path = maps_dir / f"architect_augment.{version}.yaml"
            head = self._get_repo_head()
            save_yaml({
                "metadata": {
                    "version": version,
                    "repo_snapshot_commit": head,
                    "generated_at": datetime.now().isoformat(),
                    "status": "skipped_no_arch_doc",
                },
                "adjudications": [],
            }, str(out_path))
            self.add_artifact(state, str(out_path))
            return True

        print("  Phase 1: collecting candidate evidence...")
        evidence = self._collect_evidence_candidates(arch_doc)

        print("  Phase 2: adjudicating claims...")
        prompt_path = Path(__file__).parent / "prompts" / "augment_architect.md"
        prompt_template = prompt_path.read_text() if prompt_path.exists() else ""
        adjudicated = self._spawn_augment_worker(evidence, prompt_template)

        version = self._next_version("architect_augment")
        maps_dir = OUTPUT_BASE / "maps"
        maps_dir.mkdir(parents=True, exist_ok=True)
        out_path = maps_dir / f"architect_augment.{version}.yaml"
        head = self._get_repo_head()
        save_yaml({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "generated_at": datetime.now().isoformat(),
                "status": "complete",
            },
            "adjudications": adjudicated,
        }, str(out_path))
        print(f"  Wrote {len(adjudicated)} adjudicated claims -> {out_path}")
        self.add_artifact(state, str(out_path))
        return True

    def _collect_evidence_candidates(self, arch_doc: Path) -> dict[str, Any]:
        """Phase 1: Collect candidate evidence for architecture claims."""
        root = Path.cwd()
        text = arch_doc.read_text(encoding="utf-8")
        sections = self._split_sections(text)

        candidate_evidence: list[dict[str, Any]] = []
        for idx, (title, content) in enumerate(sections, 1):
            if not content or len(content) < 30:
                continue
            symbols = _RE_PATTERNS["backtick_symbols"].findall(content)
            symbols += _RE_PATTERNS["backtick_key"].findall(content)
            symbols = list(dict.fromkeys(symbols))[:5]

            search_results: list[dict[str, Any]] = []
            for sym in symbols:
                try:
                    r = subprocess.run(
                        ["rg", "-n", "--type", "py", sym, str(root / "src")],
                        capture_output=True, text=True, timeout=5,
                    )
                    matches = []
                    if r.returncode == 0:
                        matches = r.stdout.strip().splitlines()[:3]
                    search_results.append({
                        "type": "symbol", "ref": sym,
                        "found": r.returncode == 0,
                        "matches": matches,
                    })
                except FileNotFoundError:
                    search_results.append({
                        "type": "symbol", "ref": sym,
                        "found": False,
                        "error": "ripgrep not installed",
                    })
                except Exception:
                    pass

            candidate_evidence.append({
                "claim_id": f"arch-{idx:03d}",
                "claim_text": content[:500],
                "claim_title": title,
                "stable_refs": symbols,
                "search_results": search_results,
            })

        return {"claims": candidate_evidence, "total": len(candidate_evidence)}

    def _spawn_augment_worker(self, evidence: dict, prompt_template: str) -> list[dict[str, Any]]:
        """Spawn augment worker for claim adjudication."""
        import os
        if os.environ.get("COMMIT_SEMANTIC_USE_TASK_AGENTS", "").lower() in ("1", "true", "yes"):
            return []  # real Task agent via SKILL.md orchestration

        adjudicated: list[dict[str, Any]] = []
        for claim in evidence.get("claims", []):
            search_results = claim.get("search_results", [])
            num_found = sum(1 for r in search_results if r.get("found"))
            claim_text = claim.get("claim_text", "")
            has_must = "must" in claim_text.lower() or "shall" in claim_text.lower()

            if num_found >= 2:
                status = "evidence_backed"
            elif num_found == 1:
                status = "weakly_backed"
            elif has_must:
                status = "drift"
            else:
                status = "gap"

            stable_refs: list[dict[str, str]] = []
            for r in search_results:
                if r.get("found"):
                    stable_refs.append({
                        "stable_ref": f"symbol:{r['ref']}",
                        "rationale": f"Found '{r['ref']}' in {r['matches'][0] if r['matches'] else 'repo'}",
                        "strength": "strong" if num_found >= 2 else "medium",
                    })

            adjudicated.append({
                "claim_id": claim["claim_id"],
                "claim_text": claim["claim_text"][:300],
                "status": status,
                "matched_evidence": stable_refs,
                "unmatched_claims": [],
                "notes": f"{num_found} evidence matches found",
                "recommendation": "accept" if status == "evidence_backed" else "supplement",
            })

        return adjudicated

    def _run_validate(self, state: HarnessState) -> bool:
        """Validate: schema check, deduplicate, detect conflicts from 3 maps."""
        print("  -> Running validate stage")
        maps_dir = OUTPUT_BASE / "maps"
        if not maps_dir.exists():
            print(f"  ERROR: maps directory not found: {maps_dir}")
            return False

        hotspot_map = self._load_latest_map(maps_dir, "hotspot_map")
        codebase_map = self._load_latest_map(maps_dir, "codebase_map")
        architect_aug = self._load_latest_map(maps_dir, "architect_augment")

        all_facts: list[dict[str, Any]] = []
        all_facts.extend(codebase_map.get("facts", []))
        all_facts.extend(hotspot_map.get("facts", []))

        for adj in architect_aug.get("adjudications", []):
            if adj.get("status") in ("evidence_backed", "weakly_backed"):
                all_facts.append({
                    "fact_id": adj.get("claim_id", str(uuid.uuid4())),
                    "fact_type": "boundary_constraint",
                    "domain": "architecture",
                    "statement": adj.get("claim_text", "")[:200],
                    "confidence": "confirmed" if adj.get("status") == "evidence_backed" else "uncertain",
                    "status": "active",
                    "repo_snapshot_commit": architect_aug.get("metadata", {}).get("repo_snapshot_commit", ""),
                    "source": "architect",
                    "evidence": adj.get("matched_evidence", []),
                })

        validated, invalid = self._schema_validate(all_facts)
        print(f"  Schema: {len(validated)} valid, {len(invalid)} invalid")

        deduplicated, duplicates = self._deduplicate(validated)
        print(f"  Deduplication: {len(deduplicated)} unique, {len(duplicates)} duplicates removed")

        conflicts = self._detect_conflicts(deduplicated)
        print(f"  Conflict detection: {len(conflicts)} conflicts preserved")

        version = self._next_version("validated")
        facts_dir = OUTPUT_BASE / "facts"
        facts_dir.mkdir(parents=True, exist_ok=True)
        validated_path = facts_dir / f"validated.{version}.yaml"
        conflicts_path = facts_dir / f"conflicts.{version}.yaml"
        head = self._get_repo_head()

        save_yaml({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "generated_at": datetime.now().isoformat(),
                "total_validated": len(deduplicated),
                "total_conflicts": len(conflicts),
            },
            "facts": deduplicated,
        }, str(validated_path))
        save_yaml({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "generated_at": datetime.now().isoformat(),
            },
            "conflicts": conflicts,
        }, str(conflicts_path))
        print(f"  Wrote {len(deduplicated)} validated facts -> {validated_path}")
        print(f"  Wrote {len(conflicts)} conflicts -> {conflicts_path}")
        self.add_artifact(state, str(validated_path))
        self.add_artifact(state, str(conflicts_path))
        return True

    def _load_latest_map(self, maps_dir: Path, prefix: str) -> dict[str, Any]:
        """Load the latest version of a map artifact."""
        maps = sorted(maps_dir.glob(f"{prefix}.v*.yaml"), reverse=True)
        if maps:
            return load_yaml(str(maps[0]))
        return {"metadata": {}, "facts": [], "adjudications": []}

    def _schema_validate(self, facts: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
        """Schema validation: required fields + fact_type + locator_type enums + evidence shape."""
        required_fields = {"fact_id", "fact_type", "statement", "source",
                         "repo_snapshot_commit", "evidence"}
        valid, invalid = [], []
        for f in facts:
            missing = required_fields - set(f.keys())
            if missing:
                invalid.append({**f, "_missing_fields": list(missing)})
                continue
            if f.get("fact_type") not in self.VALID_FACT_TYPES:
                invalid.append({**f, "_invalid_fact_type": f.get("fact_type")})
                continue
            evidence = f.get("evidence", [])
            if not isinstance(evidence, list):
                invalid.append({**f, "_invalid_evidence": "not a list"})
                continue
            for ev in evidence:
                if not isinstance(ev, dict):
                    invalid.append({**f, "_invalid_evidence": "evidence item not a dict"})
                    break
                lt = ev.get("locator_type", "")
                if lt not in VALID_LOCATOR_TYPES:
                    invalid.append({**f, "_invalid_locator_type": lt})
                    break
                if "locator" not in ev:
                    invalid.append({**f, "_invalid_evidence": "missing locator"})
                    break
            else:
                valid.append(f)
        return valid, invalid

    def _deduplicate(self, facts: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
        """Deduplicate facts by fact_id, keeping first occurrence."""
        seen: set[str] = set()
        unique, duplicates = [], []
        for f in facts:
            fid = f.get("fact_id", "")
            if fid in seen:
                duplicates.append(f)
            else:
                seen.add(fid)
                unique.append(f)
        return unique, duplicates

    def _detect_conflicts(self, facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Detect contradictory facts based on source + overlapping subject."""
        conflicts: list[dict[str, Any]] = []
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for f in facts:
            key = (f.get("fact_type", ""), f.get("domain", ""))
            groups[str(key)].append(f)

        for group_key, group_facts in groups.items():
            if len(group_facts) < 2:
                continue
            sources = {gf.get("source", "") for gf in group_facts}
            if len(sources) > 1:
                conflicts.append({
                    "fact_ids": [gf["fact_id"] for gf in group_facts],
                    "conflict_type": "source_priority_tie",
                    "explanation": (
                        f"Multiple sources {sources} claim facts with "
                        f"type={group_key[0]}, domain={group_key[1]}"
                    ),
                    "resolution_status": "preserved",
                })
        return conflicts

    def _run_baseline(self, state: HarnessState) -> bool:
        """Baseline: source-aware arbitration → facts.vN.yaml freeze."""
        print("  -> Running baseline stage")
        facts_dir = OUTPUT_BASE / "facts"
        if not facts_dir.exists():
            print(f"  ERROR: facts directory not found: {facts_dir}")
            return False

        validated_files = sorted(facts_dir.glob("validated.v*.yaml"), reverse=True)
        conflicts_files = sorted(facts_dir.glob("conflicts.v*.yaml"), reverse=True)

        if not validated_files:
            print("  ERROR: no validated facts found")
            return False

        validated_data = load_yaml(str(validated_files[0]))
        conflicts_data = load_yaml(str(conflicts_files[0])) if conflicts_files else {"conflicts": []}

        facts = validated_data.get("facts", [])
        conflicts = conflicts_data.get("conflicts", [])

        head = self._get_repo_head()
        source_versions = {
            "hotspot_map": self._find_latest_version("hotspot_map"),
            "codebase_map": self._find_latest_version("codebase_map"),
            "architect_augment": self._find_latest_version("architect_augment"),
        }
        baseline_facts, dropped = self._arbitrate(facts, head)

        print(f"  Arbitration: {len(baseline_facts)} accepted, {len(dropped)} dropped")

        version = self._next_version("baseline_facts")
        baseline_dir = OUTPUT_BASE / "baseline"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        facts_out = baseline_dir / f"facts.{version}.yaml"
        snapshot_ver = f"sf-{date.today().strftime('%Y-%m-%d')}.{version[1:]}"

        save_yaml({
            "metadata": {
                "version": version,
                "repo_snapshot_commit": head,
                "snapshot_version": snapshot_ver,
                "sources": source_versions,
                "generated_at": datetime.now().isoformat(),
                "arbitration": {
                    "total_candidates": len(facts),
                    "accepted": len(baseline_facts),
                    "dropped": len(dropped),
                    "conflicts_preserved": len(conflicts),
                    "source_priority": "architect > hotspot > codebase",
                },
            },
            "facts": baseline_facts,
            "conflicts": conflicts,
            "lineage": {f["fact_id"]: {"source": f["source"]} for f in baseline_facts},
        }, str(facts_out))

        latest = baseline_dir / "facts.latest.yaml"
        shutil.copy(facts_out, latest)

        snapshot_path = baseline_dir / "snapshot.yaml"
        save_yaml({
            "snapshot_version": snapshot_ver,
            "repo_snapshot_commit": head,
            "generated_at": datetime.now().isoformat(),
            "sources": source_versions,
        }, str(snapshot_path))

        print(f"  Wrote baseline facts -> {facts_out}")
        print(f"  facts.latest.yaml -> {latest}")
        print(f"  snapshot.yaml -> {snapshot_path}")
        self.add_artifact(state, str(facts_out))
        self.add_artifact(state, str(latest))
        self.add_artifact(state, str(snapshot_path))
        return True

    def _arbitrate(
        self, facts: list[dict[str, Any]], current_head: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Apply source-aware arbitration rules (source > strength > snapshot)."""
        source_order = {"architect": 0, "hotspot": 1, "codebase": 2}

        def arbitration_key(fact: dict[str, Any]) -> tuple[int, int, int]:
            source_rank = source_order.get(fact.get("source", ""), 99)
            is_hotspot_signal = fact.get("fact_type") == "hotspot_signal"
            strength_rank = 0 if is_hotspot_signal else (0 if fact.get("confidence") == "confirmed" else 1)
            is_current = 0 if fact.get("repo_snapshot_commit") == current_head else 1
            return (source_rank, strength_rank, is_current)

        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for f in facts:
            key = (f.get("fact_type", ""), f.get("statement", "")[:80])
            groups[str(key)].append(f)

        baseline: list[dict[str, Any]] = []
        dropped: list[dict[str, Any]] = []

        for group_key, group_facts in groups.items():
            if len(group_facts) == 1:
                baseline.append(group_facts[0])
                continue

            group_facts.sort(key=arbitration_key)
            winner = group_facts[0]
            losers = group_facts[1:]

            for loser in losers:
                winner_words = set(winner.get("statement", "").lower().split())
                loser_words = set(loser.get("statement", "").lower().split())
                overlap = (
                    len(winner_words & loser_words) /
                    max(len(winner_words), len(loser_words))
                    if winner_words and loser_words else 0
                )
                if overlap < 0.3:
                    baseline.append(winner)
                    baseline.append(loser)
                    break
            else:
                baseline.append(winner)
                for loser in losers:
                    dropped.append({
                        **loser,
                        "_reason": (
                            f"dominated by {winner.get('fact_id')} "
                            f"source={winner.get('source')} "
                            f"snapshot={loser.get('repo_snapshot_commit')}"
                        ),
                    })

        return baseline, dropped

    def _find_latest_version(self, prefix: str) -> str:
        """Find latest version string for a map prefix."""
        maps_dir = OUTPUT_BASE / "maps"
        if not maps_dir.exists():
            return "unknown"
        maps = sorted(maps_dir.glob(f"{prefix}.v*.yaml"), reverse=True)
        return maps[0].stem.split(".")[-1] if maps else "unknown"

    def _get_repo_head(self) -> str:
        """Get current HEAD commit (cached per run)."""
        if self._head is None:
            try:
                r = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    capture_output=True, text=True, check=True,
                )
                self._head = r.stdout.strip()
            except subprocess.CalledProcessError:
                self._head = "unknown"
        return self._head

    def _next_version(self, artifact_name: str) -> str:
        """Get next version number for an artifact."""
        maps_dir = OUTPUT_BASE / "maps"
        existing = sorted(maps_dir.glob(f"{artifact_name}.v*.yaml"))
        return "v0" if not existing else f"v{int(existing[-1].stem.split(".")[-1][1:]) + 1}"

    # -------------------------------------------------------------------------
    # Override run to inject preflight
    # -------------------------------------------------------------------------

    def handle_run(self, remaining: list[str] | None = None) -> int:
        """Run preflight then execute stages."""
        argv = remaining or []
        parser = argparse.ArgumentParser()
        parser.add_argument("--gsd-root", default=None)
        args, extra = parser.parse_known_args(argv)
        del args  # unused; retained for interface compatibility

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
        raw = _sys.argv[1:] if argv is None else list(argv)

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
        return handlers.get(args.intent, handlers["run"])()


if __name__ == "__main__":
    run_skill(RepoStructureRunner)
