#!/usr/bin/env python3
"""commit-semantic skill implementation.

5 阶段管道，从 commit-extract JSONL 构建领域知识：
  0. discover   - 从 units 语义内容聚类出领域（自底向上，首次运行时）
  1. ingest     - 展开 sections 为 semantic units + 按领域归入
  2. aggregate  - 按领域聚合，统计 op 分布 + importance 分布
  3. distill    - 多维评分排序
  4. export     - 汇总统计，生成 summary.json

Input: data/commit-extract/*.jsonl
Output: data/commit-semantic/
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
import re

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state
from src.host_executor import HostExecutor
from src.skill_runner import SkillRunner
from src.io_utils import load_jsonl, save_jsonl, save_json
from src.commit_semantic.domain_utils import (
    build_sha_file_map,
    assign_domain_by_path,
    classify_unit_locally,
    normalize_domains,
    parse_llm_domains,
    parse_llm_classifications,
    compute_fingerprint,
    fingerprint_matches,
    build_units_summary,
)

logger = logging.getLogger(__name__)

EXTRACT_OUTPUT = Path("data/commit-extract")
SEMANTIC_OUTPUT = Path("data/commit-semantic")
ARCH_CANDIDATES = [
    Path("docs/superpowers/ARCHITECTURE.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("ARCHITECTURE.md"),
]
PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"
LLM_CLASSIFY_BATCH = 50
LEGACY_EXPORT_PATHS = [
    Path("patterns"),
    Path("canonical-demands.yaml"),
    Path("functional"),
    Path("non-functional"),
]


def _domains_file():
    return SEMANTIC_OUTPUT / "domains.json"


def _units_file():
    return SEMANTIC_OUTPUT / "units" / "all.jsonl"


def _invariants_file():
    return SEMANTIC_OUTPUT / "invariants.jsonl"


class CommitSemanticRunner(SkillRunner):
    """Runner for commit-semantic pipeline (5 stages)."""

    STAGES = ["discover", "ingest", "aggregate", "distill", "export"]
    PIPELINE = "commit-semantic"

    def __init__(self, executor: HostExecutor | None = None) -> None:
        super().__init__()
        self.executor = executor

    def _check_prerequisites(self) -> tuple[bool, str]:
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

    def _find_arch_file(self) -> Path | None:
        for p in ARCH_CANDIDATES:
            if p.exists():
                return p
        return None

    def _tokenize_text(self, value: str) -> list[str]:
        return re.findall(r"[a-z0-9_/-]+", (value or "").lower())

    def _build_local_domains(self, units: list[dict]) -> list[dict]:
        token_counts: Counter[str] = Counter()
        path_counts: dict[str, Counter[str]] = defaultdict(Counter)

        for unit in units:
            for field in ("section_name", "theme", "summary"):
                for token in self._tokenize_text(unit.get(field, "")):
                    if len(token) >= 4 and token not in {"with", "from", "into", "flow", "local"}:
                        token_counts[token] += 1
            for path in unit.get("file_paths", []):
                parts = [part for part in path.split("/") if part]
                for prefix_len in range(1, min(len(parts), 3) + 1):
                    prefix = "/".join(parts[:prefix_len]) + "/"
                    path_counts[prefix][path] += 1

        domains: list[dict] = []
        used_names: set[str] = set()
        for token, count in token_counts.most_common(8):
            if count < 1 or token in used_names:
                continue
            keywords = [candidate for candidate, _ in token_counts.most_common() if token in candidate or candidate in token][:5]
            matching_prefixes = [
                prefix for prefix, counter in path_counts.items()
                if any(token in fp.lower() for fp in counter)
            ]
            domains.append({
                "domain": token.replace("_", "-").replace("/", "-"),
                "description": f"Local heuristic domain for {token}",
                "paths": sorted(matching_prefixes)[:5],
                "keywords": keywords or [token],
            })
            used_names.add(token)
            if len(domains) >= 6:
                break

        if not domains:
            domains.append({
                "domain": "core",
                "description": "Fallback domain inferred locally",
                "paths": [],
                "keywords": ["core"],
            })
        return domains


    def _assign_domains_locally(self, units: list[dict], domains: list[dict], *, allow_path_scoring: bool = True) -> int:
        assigned = 0
        for unit in units:
            if unit.get("domain") and unit["domain"] != "uncategorized":
                continue
            best_domain = classify_unit_locally(
                unit,
                domains,
                allow_path_scoring=allow_path_scoring and not unit.get("path_scoring_disabled", False),
            )
            if best_domain:
                unit["domain"] = best_domain
                assigned += 1
        return assigned

    def _use_local_fallback(self, state: HarnessState) -> bool:
        return self.executor is None and not state.metadata.get("external_orchestration", False)

    def _build_discover_context(self, units_summary: str, arch_content: str) -> dict[str, str]:
        return {
            "units_summary": units_summary,
            "architecture_content": arch_content or "(none)",
        }

    def _execute_discover(self, state: HarnessState, prompt: str, context: dict[str, str]) -> bool:
        if self.executor is None:
            print("  ! Discover orchestration unavailable")
            return False
        try:
            response = self.executor(
                prompt,
                context,
                artifact_name="domains",
                sampling_mode="auto",
            )
        except Exception as exc:
            print(f"  ! Discover orchestration failed: {exc}")
            return False
        return self.complete_discover(response, state)

    def _build_classify_batches(self, needs_llm: list[dict], domains: list[dict]) -> list[dict[str, str]]:
        prompt_template = (PROMPT_DIR / "classify_units.md").read_text(encoding="utf-8")
        batches: list[dict[str, str]] = []
        for start in range(0, len(needs_llm), LLM_CLASSIFY_BATCH):
            batch_units = needs_llm[start:start + LLM_CLASSIFY_BATCH]
            context = {
                "domains_json": json.dumps(domains, ensure_ascii=False, indent=2),
                "units_json": json.dumps(
                    [
                        {
                            "id": str(i),
                            "section_name": unit.get("section_name", ""),
                            "theme": unit.get("theme", ""),
                            "summary": unit.get("summary", ""),
                            "op": unit.get("op", ""),
                        }
                        for i, unit in enumerate(batch_units, start=start)
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
            }
            prompt = prompt_template.replace("{domains_json}", context["domains_json"])
            prompt = prompt.replace("{units_json}", context["units_json"])
            batches.append({"prompt": prompt, "context": context})
        return batches

    def _execute_classify_batches(
        self,
        state: HarnessState,
        needs_llm: list[dict],
        domains: list[dict],
        units: list[dict],
    ) -> bool:
        if self.executor is None:
            print("  ! Classify orchestration unavailable")
            return False

        responses: list[str] = []
        for batch in self._build_classify_batches(needs_llm, domains):
            try:
                response = self.executor(
                    batch["prompt"],
                    batch["context"],
                    artifact_name="classify-units",
                    sampling_mode="auto",
                )
            except Exception as exc:
                print(f"  ! LLM classification batch failed: {exc}")
                return False
            responses.append(response)

        return self._apply_classify_responses(responses, state, units=units)

    def _set_discover_mode(self, state: HarnessState, mode: str) -> None:
        state.metadata["discover_mode"] = mode

    def _set_classify_mode(self, state: HarnessState, mode: str) -> None:
        state.metadata["classify_mode"] = mode

    def _refresh_orchestration_mode(self, state: HarnessState) -> None:
        discover_mode = state.metadata.get("discover_mode")
        classify_mode = state.metadata.get("classify_mode")

        if not discover_mode and not classify_mode:
            return

        discover_family = (
            "fallback" if discover_mode in {"fallback", "cached_fallback"}
            else "llm" if discover_mode in {"llm", "cached_llm"}
            else None
        )
        classify_family = (
            "fallback" if classify_mode == "fallback"
            else "llm" if classify_mode in {"llm", "cached"}
            else "mixed" if classify_mode == "mixed"
            else None
        )

        if discover_family == "fallback" and classify_family in {None, "fallback", "llm"}:
            state.metadata["orchestration_mode"] = "local_fallback"
            return
        if discover_family == "llm" and classify_family in {None, "llm"}:
            state.metadata["orchestration_mode"] = "llm_preferred"
            return
        state.metadata["orchestration_mode"] = "mixed_degraded"

    def _persist_domains(self, *, fingerprint: dict, domains: list[dict], discover_mode: str, orchestration_mode_at_discover: str) -> None:
        save_json(
            {
                "_fingerprint": fingerprint,
                "discover_mode": discover_mode,
                "orchestration_mode_at_discover": orchestration_mode_at_discover,
                "domains": domains,
            },
            str(_domains_file()),
        )

    def _write_local_domains(self, units: list[dict], fingerprint: dict, state: HarnessState) -> list[dict]:
        domains = normalize_domains(self._build_local_domains(units))
        self._set_discover_mode(state, "fallback")
        self._refresh_orchestration_mode(state)
        self._persist_domains(
            fingerprint=fingerprint,
            domains=domains,
            discover_mode="fallback",
            orchestration_mode_at_discover=state.metadata.get("orchestration_mode", "local_fallback"),
        )
        return domains

    def _check_state_compat(self, state: HarnessState) -> HarnessState:
        """Detect old 4-stage state and reset if incompatible."""
        completed = state.metadata.get("completed_stages", [])
        if completed and "discover" not in self.STAGES[:1]:
            return state
        # If state has completed stages but none match new STAGES[0],
        # it's from the old 4-stage pipeline
        if completed and all(s in ["ingest", "aggregate", "distill", "export"] for s in completed):
            if "discover" not in completed:
                logger.warning(
                    "Detected old 4-stage state (completed: %s). "
                    "Resetting for new 5-stage pipeline.", completed
                )
                return self.init_state()
        return state


    def run_stage(self, stage: str, state: HarnessState) -> bool:
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        dispatch = {
            "discover": self._run_discover,
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
    # Stage 0: discover
    # -------------------------------------------------------------------

    def _run_discover(self, state: HarnessState) -> bool:
        """Cluster units into domains (bottom-up). Only runs on init or fingerprint change."""
        print("  -> Running domain discovery")
        SEMANTIC_OUTPUT.mkdir(parents=True, exist_ok=True)

        # If units don't exist yet, we need ingest first (first-run bootstrap)
        if not _units_file().exists():
            print("  Units not found — running ingest first (no domain assignment)")
            if not self._run_ingest_raw(state):
                return False

        units = load_jsonl(str(_units_file()), skip_errors=True)
        if not units:
            print("  ! No units to cluster")
            return True

        arch_file = self._find_arch_file()
        current_fp = compute_fingerprint(_units_file(), arch_file)

        # Check cache
        force = state.metadata.get("force", False)
        if _domains_file().exists() and not force:
            try:
                with open(_domains_file()) as f:
                    cached = json.load(f)
                if fingerprint_matches(cached, current_fp):
                    n = len(cached.get("domains", []))
                    cached_mode = cached.get("discover_mode")
                    if cached_mode == "llm":
                        self._set_discover_mode(state, "cached_llm")
                        if "orchestration_mode_at_discover" in cached:
                            state.metadata["orchestration_mode_at_discover"] = cached["orchestration_mode_at_discover"]
                        self._refresh_orchestration_mode(state)
                        print(f"  Cache hit ({n} domains, fingerprint matches). Skipping discovery.")
                        return True
                    print("  Non-LLM discovery cache incompatible — re-running discovery")
                else:
                    print("  Fingerprint changed — re-running discovery")
            except (json.JSONDecodeError, OSError):
                print("  Invalid cache — re-running discovery")

        # Build prompt input
        units_summary = build_units_summary(units)
        arch_content = ""
        if arch_file and arch_file.exists():
            arch_content = arch_file.read_text(encoding="utf-8")[:3000]

        prompt_template = (PROMPT_DIR / "discover_domains.md").read_text(encoding="utf-8")
        context = self._build_discover_context(units_summary, arch_content)
        prompt = prompt_template.replace("{units_summary}", context["units_summary"])
        prompt = prompt.replace("{architecture_content}", context["architecture_content"])

        state.metadata["discover_prompt"] = prompt
        state.metadata["discover_fingerprint"] = current_fp
        print(f"  Prepared discovery prompt ({len(units)} units, {len(units_summary)} chars)")
        if self.executor is not None:
            return self._execute_discover(state, prompt, context)
        if self._use_local_fallback(state):
            print("  ! Discover orchestration unavailable")
            return False
        print("  [ORCHESTRATOR] Send discover_prompt to LLM, then call complete_discover()")
        return True

    def complete_discover(self, llm_response: str, state: HarnessState) -> bool:
        """Called by orchestrator after LLM returns domain list."""
        domains = normalize_domains(parse_llm_domains(llm_response))
        if not domains:
            print("  ! LLM returned no valid domains")
            return False

        if len(domains) > 20:
            logger.warning("LLM returned %d domains (>20), truncating to 20", len(domains))
            domains = domains[:20]

        fp = state.metadata.get("discover_fingerprint", {})
        self._set_discover_mode(state, "llm")
        self._refresh_orchestration_mode(state)
        self._persist_domains(
            fingerprint=fp,
            domains=domains,
            discover_mode="llm",
            orchestration_mode_at_discover=state.metadata.get("orchestration_mode", "llm_preferred"),
        )
        print(f"  Discovered {len(domains)} domains → {_domains_file()}")
        return True

    # -------------------------------------------------------------------
    # Stage 1: ingest (raw — no domain assignment)
    # -------------------------------------------------------------------

    def _run_ingest_raw(self, state: HarnessState) -> bool:
        """Expand sections into units WITHOUT domain assignment. Used for bootstrap."""
        print("  -> Ingesting commit-extract JSONL (raw, no domain assignment)")
        units_dir = SEMANTIC_OUTPUT / "units"
        units_dir.mkdir(parents=True, exist_ok=True)

        all_units, all_invariants = self._expand_records()

        save_jsonl(all_units, str(_units_file()))
        save_jsonl(all_invariants, str(_invariants_file()))
        print(f"  Raw ingest: {len(all_units)} units, {len(all_invariants)} invariants")
        return True

    # -------------------------------------------------------------------
    # Stage 1: ingest (with domain assignment)
    # -------------------------------------------------------------------

    def _run_ingest(self, state: HarnessState) -> bool:
        """Expand sections into units + assign domains."""
        print("  -> Ingesting commit-extract JSONL")
        units_dir = SEMANTIC_OUTPUT / "units"
        units_dir.mkdir(parents=True, exist_ok=True)

        all_units, all_invariants = self._expand_records()

        # Domain assignment (only if domains.json exists)
        domains = self._load_domains()
        file_paths_available = True
        if domains and "discover_mode" not in state.metadata:
            cached_discover_mode = self._load_domains_data().get("discover_mode")
            if cached_discover_mode == "llm":
                self._set_discover_mode(state, "cached_llm")
            elif cached_discover_mode == "fallback":
                self._set_discover_mode(state, "cached_fallback")

        if domains:
            # Build SHA → file_paths map
            shas = list(set(u["sha"] for u in all_units if u.get("sha")))
            repo_path = str(Path.cwd())
            sha_file_map, git_ok = build_sha_file_map(repo_path, shas)
            file_paths_available = git_ok

            # Group units by commit SHA
            by_sha: dict[str, list[dict]] = defaultdict(list)
            for u in all_units:
                by_sha[u.get("sha", "")].append(u)

            # Assign domains at commit level
            needs_llm: list[dict] = []
            for sha, units in by_sha.items():
                file_paths = sha_file_map.get(sha, [])
                is_mixed = any(u.get("is_mixed", False) for u in units)

                # Attach file_paths to each unit
                for u in units:
                    u["file_paths"] = file_paths

                if not file_paths or is_mixed:
                    # Mixed commit or no paths → needs LLM
                    needs_llm.extend(units)
                else:
                    domain = assign_domain_by_path(file_paths, domains)
                    if domain:
                        for u in units:
                            u["domain"] = domain
                    else:
                        # Paths span multiple domains → needs LLM
                        for u in units:
                            u["path_scoring_disabled"] = True
                        needs_llm.extend(units)

            # Store units needing LLM classification for orchestrator
            if needs_llm:
                state.metadata["needs_llm_classify"] = len(needs_llm)
                state.metadata["classify_units"] = [
                    {"id": str(i), "section_name": u.get("section_name", ""),
                     "theme": u.get("theme", ""), "summary": u.get("summary", ""),
                     "op": u.get("op", "")}
                    for i, u in enumerate(needs_llm)
                ]
                state.metadata["classify_unit_indices"] = [
                    all_units.index(u) for u in needs_llm
                ]
                if self.executor is not None:
                    if not self._execute_classify_batches(state, needs_llm, domains, all_units):
                        return False
                elif self._use_local_fallback(state):
                    print("  ! Classify orchestration unavailable")
                    return False
                else:
                    self._set_classify_mode(state, "llm")
                    print(f"  {len(needs_llm)} units need LLM classification")
                    print("  [ORCHESTRATOR] Send classify batches to LLM, then call complete_classify()")
            else:
                self._set_classify_mode(state, "cached")
                state.metadata["needs_llm_classify"] = 0

            # Mark uncategorized for units without domain
            for u in all_units:
                if "domain" not in u:
                    u["domain"] = "uncategorized"
        else:
            print("  No domains.json — skipping domain assignment")

        self._refresh_orchestration_mode(state)
        state.metadata["file_paths_available"] = file_paths_available

        save_jsonl(all_units, str(_units_file()))
        save_jsonl(all_invariants, str(_invariants_file()))

        categorized = sum(1 for u in all_units if u.get("domain", "uncategorized") != "uncategorized")
        total = len(all_units) or 1
        print(f"  Ingested {len(all_units)} units, {len(all_invariants)} invariants")
        if domains:
            print(f"  Domain assignment: {categorized}/{total} ({categorized/total:.0%}) categorized")
        self.add_artifact(state, str(units_dir))
        return True

    def _apply_classify_responses(
        self,
        llm_responses: list[str],
        state: HarnessState,
        *,
        units: list[dict] | None = None,
    ) -> bool:
        indices = state.metadata.get("classify_unit_indices", [])
        current_units = units if units is not None else load_jsonl(str(_units_file()), skip_errors=True)

        classified = 0
        classified_ids: set[int] = set()
        staged_units = [dict(unit) for unit in current_units]
        allowed_domains = {
            domain.get("domain")
            for domain in self._load_domains()
            if domain.get("domain")
        }
        for response in llm_responses:
            mapping = parse_llm_classifications(response)
            if not mapping:
                try:
                    parsed = json.loads(response.strip())
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    mapping = {str(k): v for k, v in parsed.items() if isinstance(v, str)}
            if not mapping:
                print("  ! LLM classification batch returned invalid output")
                return False
            for id_str, domain in mapping.items():
                if not isinstance(domain, str) or domain not in allowed_domains:
                    print(f"  ! LLM classification returned unknown domain: {domain}")
                    return False
                try:
                    idx = int(id_str)
                except (TypeError, ValueError):
                    print(f"  ! LLM classification returned malformed id: {id_str}")
                    return False
                if 0 <= idx < len(indices) and indices[idx] < len(staged_units):
                    staged_units[indices[idx]]["domain"] = domain
                    classified += 1
                    classified_ids.add(idx)

        unresolved_count = sum(
            1 for idx, unit_idx in enumerate(indices)
            if idx not in classified_ids and unit_idx < len(staged_units)
        )
        if unresolved_count:
            print(f"  ! LLM classification incomplete: {unresolved_count} units unresolved")
            return False

        if units is None:
            save_jsonl(staged_units, str(_units_file()))
        else:
            units[:] = staged_units
        self._set_classify_mode(state, "llm")
        self._refresh_orchestration_mode(state)
        print(f"  LLM classified {classified} units")
        return True

    def complete_classify(self, llm_responses: list[str], state: HarnessState) -> bool:
        """Called by orchestrator after LLM classification batches return."""
        return self._apply_classify_responses(llm_responses, state)

    def _expand_records(self) -> tuple[list[dict], list[dict]]:
        """Read JSONL and expand sections into units + collect invariants."""
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

                for inv in record.get("rules_invariants", []):
                    all_invariants.append({
                        "sha": sha,
                        "date": date,
                        "kind": inv.get("kind", "other"),
                        "statement": inv.get("statement", ""),
                        "enforced_by_commit": inv.get("enforced_by_commit", False),
                    })

        return all_units, all_invariants

    def _load_domains_data(self) -> dict:
        """Load raw domains.json payload. Returns empty dict if not available."""
        if not _domains_file().exists():
            return {}
        try:
            with open(_domains_file()) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_domains(self) -> list[dict]:
        """Load domains from cache. Returns empty list if not available."""
        return self._load_domains_data().get("domains", [])

    def _remove_legacy_export_artifacts(self) -> list[str]:
        """Remove legacy export artifacts from previous commit-semantic output."""
        removed: list[str] = []
        for relative_path in LEGACY_EXPORT_PATHS:
            legacy_path = SEMANTIC_OUTPUT / relative_path
            if not legacy_path.exists():
                continue
            if legacy_path.is_dir():
                shutil.rmtree(legacy_path)
            else:
                legacy_path.unlink()
            removed.append(str(relative_path))
        return removed

    # -------------------------------------------------------------------
    # Stage 2: aggregate
    # -------------------------------------------------------------------

    def _run_aggregate(self, state: HarnessState) -> bool:
        """Group units by domain, compute statistics."""
        print("  -> Aggregating by domain")

        if not _units_file().exists():
            print("  ! No units to aggregate")
            return True

        units = load_jsonl(str(_units_file()))

        # Group by domain
        by_domain: dict[str, list[dict]] = defaultdict(list)
        for unit in units:
            domain = unit.get("domain", "uncategorized")
            by_domain[domain].append(unit)

        aggregated: list[dict] = []
        for domain, domain_units in sorted(by_domain.items()):
            distinct_commits = len(set(u["sha"] for u in domain_units))

            # Op distribution
            op_dist: dict[str, int] = defaultdict(int)
            importance_counts = {"primary": 0, "secondary": 0}

            # Date range
            min_date = ""
            max_date = ""

            # Sub-themes
            by_theme: dict[str, int] = defaultdict(int)
            summaries: list[str] = []

            for u in domain_units:
                op_dist[u.get("op", "other")] += 1
                imp = u.get("importance", "secondary")
                if imp in importance_counts:
                    importance_counts[imp] += 1
                d = u.get("date", "")
                if d:
                    if not min_date or d < min_date:
                        min_date = d
                    if not max_date or d > max_date:
                        max_date = d
                theme = u.get("theme", "unknown")
                by_theme[theme] += 1
                if u.get("summary") and len(summaries) < 3:
                    summaries.append(u["summary"])

            aggregated.append({
                "domain": domain,
                "is_uncategorized": domain == "uncategorized",
                "count": len(domain_units),
                "distinct_commits": distinct_commits,
                "op_distribution": dict(op_dist),
                "importance_ratio": importance_counts,
                "date_range": {"from": min_date, "to": max_date} if min_date else {},
                "sub_themes": dict(sorted(by_theme.items(), key=lambda x: -x[1])[:10]),
                "representative_summaries": summaries,
            })

        save_jsonl(aggregated, str(SEMANTIC_OUTPUT / "domains-aggregated.jsonl"))
        print(f"  Aggregated {len(aggregated)} domains")
        self.add_artifact(state, str(SEMANTIC_OUTPUT / "domains-aggregated.jsonl"))
        return True

    # -------------------------------------------------------------------
    # Stage 3: distill
    # -------------------------------------------------------------------

    def _run_distill(self, state: HarnessState) -> bool:
        """Score and rank domains with multi-dimensional formula."""
        print("  -> Distilling canonical demands")

        agg_file = SEMANTIC_OUTPUT / "domains-aggregated.jsonl"
        if not agg_file.exists():
            print("  ! No aggregated domains to distill")
            return True

        aggregated = load_jsonl(str(agg_file))

        # Load invariants for SHA-based association
        invariants = load_jsonl(str(_invariants_file())) if _invariants_file().exists() else []
        units = load_jsonl(str(_units_file())) if _units_file().exists() else []

        # Build domain → set of SHAs
        domain_shas: dict[str, set[str]] = defaultdict(set)
        for u in units:
            domain = u.get("domain", "uncategorized")
            sha = u.get("sha", "")
            if sha:
                domain_shas[domain].add(sha)

        # Build invariant SHA set
        inv_by_sha: dict[str, list[dict]] = defaultdict(list)
        for inv in invariants:
            sha = inv.get("sha", "")
            if sha:
                inv_by_sha[sha].append(inv)

        from datetime import datetime, timedelta
        now = datetime.now()
        cutoff_90d = (now - timedelta(days=90)).strftime("%Y-%m-%d")

        demands: list[dict] = []
        for entry in aggregated:
            domain = entry["domain"]
            distinct = entry.get("distinct_commits", 0)
            imp_ratio = entry.get("importance_ratio", {})
            primary = imp_ratio.get("primary", 0)
            secondary = imp_ratio.get("secondary", 0)
            total_imp = primary + secondary
            importance_weight = (primary * 2 + secondary * 1) / total_imp if total_imp > 0 else 1.0

            base_score = distinct * importance_weight

            # Diversity bonus
            op_dist = entry.get("op_distribution", {})
            total_ops = sum(op_dist.values()) or 1
            unique_ops = len(op_dist)
            diversity_bonus = unique_ops / total_ops

            # Invariant bonus (SHA association, cap=5)
            shas = domain_shas.get(domain, set())
            domain_invariants: set[str] = set()
            for sha in shas:
                for inv in inv_by_sha.get(sha, []):
                    domain_invariants.add(inv.get("statement", ""))
            invariant_bonus = min(len(domain_invariants), 5)

            # Recency weight
            recent = 0
            for u in units:
                if u.get("domain") == domain and u.get("date", "") >= cutoff_90d:
                    recent += 1
            total_domain = entry.get("count", 1) or 1
            recency_weight = recent / total_domain

            final_score = (
                base_score
                * (1 + diversity_bonus)
                * (1 + invariant_bonus * 0.3)
                * (1 + recency_weight * 0.2)
            )

            demands.append({
                "domain": domain,
                "is_uncategorized": entry.get("is_uncategorized", False),
                "final_score": round(final_score, 2),
                "base_score": round(base_score, 2),
                "diversity_bonus": round(diversity_bonus, 4),
                "invariant_bonus": invariant_bonus,
                "recency_weight": round(recency_weight, 4),
                "distinct_commits": distinct,
                "importance_weight": round(importance_weight, 2),
                "op_distribution": op_dist,
                "representative_summaries": entry.get("representative_summaries", []),
            })

        demands.sort(key=lambda d: (-d["final_score"], -d["distinct_commits"], d["domain"]))
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

        units = load_jsonl(str(_units_file())) if _units_file().exists() else []
        invariants = load_jsonl(str(_invariants_file())) if _invariants_file().exists() else []

        agg_file = SEMANTIC_OUTPUT / "domains-aggregated.jsonl"
        aggregated = load_jsonl(str(agg_file)) if agg_file.exists() else []

        demands_file = SEMANTIC_OUTPUT / "canonical-demands.jsonl"
        demands = load_jsonl(str(demands_file)) if demands_file.exists() else []

        # Op distribution
        op_dist: dict[str, int] = defaultdict(int)
        min_date = ""
        max_date = ""
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

        # Uncategorized ratio
        uncategorized = sum(1 for u in units if u.get("domain", "uncategorized") == "uncategorized")
        uncategorized_ratio = round(uncategorized / total, 4)

        # Top domains
        top_domains = [
            {"domain": d["domain"], "final_score": d["final_score"],
             "distinct_commits": d["distinct_commits"]}
            for d in demands[:10]
        ]

        removed_legacy_paths = self._remove_legacy_export_artifacts()
        summary = {
            "total_units": len(units),
            "domain_count": len(aggregated),
            "uncategorized_ratio": uncategorized_ratio,
            "op_distribution": dict(op_dist),
            "top_domains": top_domains,
            "bugfix_ratio": bugfix_ratio,
            "invariant_count": len(invariants),
            "date_range": {"from": min_date, "to": max_date} if min_date else {},
            "file_paths_available": state.metadata.get("file_paths_available", True),
            "orchestration_mode": state.metadata.get("orchestration_mode", "local_fallback"),
            "discover_mode": state.metadata.get("discover_mode", "fallback"),
            "classify_mode": state.metadata.get("classify_mode", "cached"),
        }
        if removed_legacy_paths:
            summary["removed_legacy_paths"] = removed_legacy_paths

        save_json(summary, str(SEMANTIC_OUTPUT / "summary.json"))
        print(f"  Exported: {len(units)} units, {len(aggregated)} domains, "
              f"uncategorized {uncategorized_ratio:.1%}, bugfix {bugfix_ratio:.1%}")
        if removed_legacy_paths:
            print(f"  Removed legacy artifacts: {', '.join(removed_legacy_paths)}")
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
        parser.add_argument("--force", action="store_true", help="Force re-discovery")
        args = parser.parse_args(argv)

        if args.stage:
            if args.stage not in self.STAGES:
                print(f"[{self.PIPELINE}] Unknown stage: {args.stage}. "
                      f"Available: {', '.join(self.STAGES)}")
                return 1
            if not self._require_prerequisites():
                return 1
            state = self.init_state()
            if args.force:
                state.metadata["force"] = True
            save_state(self.PIPELINE, state)
            success = self.run_stage(args.stage, state)
            return 0 if success else 1

        if not self._require_prerequisites():
            return 1

        # Check state compatibility
        old_state = load_state(self.PIPELINE)
        if not self.is_fresh(old_state):
            old_state = self._check_state_compat(old_state)
            save_state(self.PIPELINE, old_state)

        state = self.init_state()
        if args.force:
            state.metadata["force"] = True
        save_state(self.PIPELINE, state)
        return self.handle_resume()


def run_commit_semantic() -> None:
    """Entry point for the commit-semantic skill."""
    raise SystemExit(CommitSemanticRunner().main())


if __name__ == "__main__":
    run_commit_semantic()
