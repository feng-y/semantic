#!/usr/bin/env python3
"""commit-semantic skill implementation.

V1 pipeline, commit-first and capability-first:
  0. context                 - synthesize repo hints/context from local docs
  1. extract-signals         - extract commit-level semantic signals via LLM
  2. synthesize-capabilities - group signals into capability candidates
  3. validate                - normalize candidates into stable capabilities
  4. export                  - write summary.json

Input: data/commit-extract/*.jsonl
Output: data/commit-semantic/
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.harness_state import HarnessState, load_state, save_state
from src.host_executor import HostExecutor
from src.skill_runner import SkillRunner
from src.io_utils import load_jsonl, save_jsonl, save_json, load_json

logger = logging.getLogger(__name__)

EXTRACT_OUTPUT = Path("data/commit-extract")
SEMANTIC_OUTPUT = Path("data/commit-semantic")
CONTEXT_DOC_CANDIDATES = [
    Path("README.md"),
    Path("docs/superpowers/ARCHITECTURE.md"),
    Path("docs/ARCHITECTURE.md"),
    Path("ARCHITECTURE.md"),
    Path("docs/superpowers/specs/2026-03-24-commit-semantic-general-semantic-asset-extraction-design.md"),
]
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def _repo_hints_file() -> Path:
    return SEMANTIC_OUTPUT / "repo-hints.json"


def _repo_context_file() -> Path:
    return SEMANTIC_OUTPUT / "repo-context.json"


def _shared_repo_context_file() -> Path:
    return EXTRACT_OUTPUT / "repo-context.json"


def _capability_candidates_file() -> Path:
    return SEMANTIC_OUTPUT / "capabilities-candidates.jsonl"


def _capabilities_file() -> Path:
    return SEMANTIC_OUTPUT / "capabilities.jsonl"


def _summary_file() -> Path:
    return SEMANTIC_OUTPUT / "summary.json"


def _legacy_artifact_paths() -> list[Path]:
    return [
        SEMANTIC_OUTPUT / "domains.json",
        SEMANTIC_OUTPUT / "domains-aggregated.jsonl",
        SEMANTIC_OUTPUT / "canonical-demands.jsonl",
        SEMANTIC_OUTPUT / "units",
        SEMANTIC_OUTPUT / "invariants.jsonl",
        SEMANTIC_OUTPUT / "patterns",
        SEMANTIC_OUTPUT / "canonical-demands.yaml",
        SEMANTIC_OUTPUT / "functional",
        SEMANTIC_OUTPUT / "non-functional",
    ]


def _safe_read(path: Path, limit: int = 3000) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except OSError:
        return ""


def _json_only(raw: str) -> str:
    text = (raw or "").strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = _json_only(raw)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


def _parse_json_array(raw: str) -> list[dict[str, Any]]:
    text = _json_only(raw)
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array")
    return [item for item in data if isinstance(item, dict)]


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / name
    return path.read_text(encoding="utf-8")


def _normalize_aliases(raw_aliases: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(raw_aliases, list):
        return normalized
    for item in raw_aliases:
        if not isinstance(item, dict):
            continue
        canonical = str(item.get("canonical") or item.get("domain") or "").strip()
        alias = str(item.get("alias") or item.get("name") or "").strip()
        if not canonical or not alias:
            continue
        kind = str(item.get("kind") or "term").strip() or "term"
        normalized.append({"canonical": canonical, "alias": alias, "kind": kind})
    return normalized


def _normalize_ownership_hints(raw_hints: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(raw_hints, list):
        return normalized
    for item in raw_hints:
        if not isinstance(item, dict):
            continue
        scope = str(item.get("scope") or item.get("path_prefix") or item.get("capability") or "").strip()
        owner = str(item.get("owner") or item.get("capability") or item.get("path_prefix") or "").strip()
        note = str(item.get("note") or item.get("description") or item.get("path_prefix") or owner).strip()
        if not scope or not owner or not note:
            continue
        normalized.append({"scope": scope, "owner": owner, "note": note})
    return normalized


def _normalize_seed_concepts(raw_concepts: Any) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    if not isinstance(raw_concepts, list):
        return normalized
    for item in raw_concepts:
        if isinstance(item, str):
            name = item.strip()
            if name:
                normalized.append({"name": name, "description": name})
            continue
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("concept") or item.get("title") or "").strip()
        description = str(item.get("description") or item.get("summary") or name).strip()
        if not name or not description:
            continue
        normalized.append({"name": name, "description": description})
    return normalized


class CommitSemanticRunner(SkillRunner):
    """Runner for commit-semantic capability-first pipeline."""

    STAGES = ["context", "extract-signals", "synthesize-capabilities", "validate", "export"]
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

    def _load_extract_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for jsonl_file in sorted(EXTRACT_OUTPUT.glob("*.jsonl")):
            records.extend(load_jsonl(str(jsonl_file), skip_errors=True))
        return records

    def _collect_context_docs(self) -> list[dict[str, str]]:
        docs: list[dict[str, str]] = []
        for path in CONTEXT_DOC_CANDIDATES:
            content = _safe_read(path)
            if content:
                docs.append({"path": str(path), "content": content})
        return docs

    def _build_context_prompt(self, records: list[dict[str, Any]], docs: list[dict[str, str]]) -> str:
        prompt_template = _load_prompt("context.md")
        record_preview = json.dumps(
            [
                {
                    "sha": r.get("sha", ""),
                    "date": r.get("date", ""),
                    "is_mixed": r.get("is_mixed", False),
                    "is_large_aggregate": r.get("is_large_aggregate", False),
                    "sections": r.get("sections", []),
                    "rules_invariants": r.get("rules_invariants", []),
                }
                for r in records[:20]
            ],
            ensure_ascii=False,
            indent=2,
        )
        docs_text = "\n\n".join(
            f"## {doc['path']}\n{doc['content']}" for doc in docs
        ) or "(no repo-local understanding docs found)"
        return f"{prompt_template}\n\n## Repo Docs\n{docs_text}\n\n## Commit Extract Preview\n{record_preview}\n"

    def _build_signal_prompt(self, records: list[dict[str, Any]], repo_hints: dict[str, Any]) -> str:
        prompt_template = _load_prompt("extract-signals.md")
        records_json = json.dumps(records, ensure_ascii=False, indent=2)
        hints_json = json.dumps(repo_hints, ensure_ascii=False, indent=2)
        return f"{prompt_template}\n\n## Repo Hints\n{hints_json}\n\n## Commit Records\n{records_json}\n"

    def _build_capability_prompt(self, signals: list[dict[str, Any]], repo_context: dict[str, Any]) -> str:
        prompt_template = _load_prompt("synthesize-capabilities.md")
        signals_json = json.dumps(signals, ensure_ascii=False, indent=2)
        context_json = json.dumps(repo_context, ensure_ascii=False, indent=2)
        return f"{prompt_template}\n\n## Repo Context\n{context_json}\n\n## Signals\n{signals_json}\n"

    def _load_repo_hints(self) -> dict[str, Any]:
        if not _repo_hints_file().exists():
            return {}
        return load_json(str(_repo_hints_file()))

    def _load_repo_context(self) -> dict[str, Any]:
        shared_context_file = _shared_repo_context_file()
        for path in (shared_context_file, _repo_context_file()):
            if not path.exists():
                continue
            payload = load_json(str(path))
            if not isinstance(payload, dict):
                continue
            semantic_context = payload.get("semantic_context")
            if isinstance(semantic_context, dict) and any(semantic_context.values()):
                return semantic_context
            if path == shared_context_file:
                continue
            return payload
        return {}

    def _load_capability_candidates(self) -> list[dict[str, Any]]:
        if not _capability_candidates_file().exists():
            return []
        return load_jsonl(str(_capability_candidates_file()), skip_errors=True)

    def run_stage(self, stage: str, state: HarnessState) -> bool:
        print(f"\n[{self.PIPELINE}] Running stage: {stage}")
        dispatch = {
            "context": self._run_context,
            "extract-signals": self._run_extract_signals,
            "synthesize-capabilities": self._run_synthesize_capabilities,
            "validate": self._run_validate,
            "export": self._run_export,
        }
        handler = dispatch.get(stage)
        if handler:
            return handler(state)
        return True

    def _run_context(self, state: HarnessState) -> bool:
        SEMANTIC_OUTPUT.mkdir(parents=True, exist_ok=True)
        records = self._load_extract_records()
        docs = self._collect_context_docs()
        if self.executor is None:
            print("  ! Context orchestration unavailable")
            return False
        prompt = self._build_context_prompt(records, docs)
        try:
            response = self.executor(
                prompt,
                {"record_count": str(len(records)), "doc_count": str(len(docs))},
                artifact_name="repo-hints",
                sampling_mode="auto",
            )
        except Exception as exc:
            print(f"  ! Context orchestration failed: {exc}")
            return False
        try:
            hints = _parse_json_object(response)
        except Exception as exc:
            print(f"  ! Invalid repo hints output: {exc}")
            return False
        hints.setdefault("local_capabilities", [])
        hints.setdefault("aliases", [])
        hints.setdefault("ownership_hints", [])
        hints.setdefault("seed_concepts", [])
        hints.setdefault("doc_sources", [doc["path"] for doc in docs])
        hints.setdefault("confidence", "medium")
        normalized_aliases = _normalize_aliases(hints.get("aliases", []))
        normalized_ownership_hints = _normalize_ownership_hints(hints.get("ownership_hints", []))
        normalized_seed_concepts = _normalize_seed_concepts(hints.get("seed_concepts", []))
        semantic_context = {
            "local_capabilities": hints.get("local_capabilities", []),
            "ownership_hints": hints.get("ownership_hints", []),
            "aliases": hints.get("aliases", []),
            "seed_concepts": hints.get("seed_concepts", []),
            "confidence": hints.get("confidence", "medium"),
        }
        shared_hints = {
            "local_capabilities": hints.get("local_capabilities", []),
            "aliases": normalized_aliases,
            "ownership_hints": normalized_ownership_hints,
            "seed_concepts": normalized_seed_concepts,
            "source_provenance": {},
            "hint_confidence": {},
            "conflicts": [],
            "source_snapshot": {
                "docs": hints.get("doc_sources", []),
                "codebase_map": [],
            },
        }
        repo_context = {
            "shared_hints": shared_hints,
            "semantic_context": semantic_context,
            "summary": {
                "bootstrap_status": "degraded",
                "hint_count": (
                    len(shared_hints["local_capabilities"])
                    + len(shared_hints["ownership_hints"])
                    + len(shared_hints["aliases"])
                    + len(shared_hints["seed_concepts"])
                ),
                "source_counts": {
                    "docs": len(shared_hints["source_snapshot"]["docs"]),
                    "codebase_map": len(shared_hints["source_snapshot"]["codebase_map"]),
                },
            },
        }
        save_json(hints, str(_repo_hints_file()))
        save_json(repo_context, str(_repo_context_file()))
        self.add_artifact(state, str(_repo_hints_file()))
        self.add_artifact(state, str(_repo_context_file()))
        return True

    def _run_extract_signals(self, state: HarnessState) -> bool:
        records = self._load_extract_records()
        repo_hints = self._load_repo_hints()
        if self.executor is None:
            print("  ! Signal extraction orchestration unavailable")
            return False
        prompt = self._build_signal_prompt(records, repo_hints)
        try:
            response = self.executor(
                prompt,
                {"record_count": str(len(records))},
                artifact_name="capability-signals",
                sampling_mode="auto",
            )
        except Exception as exc:
            print(f"  ! Signal extraction failed: {exc}")
            return False
        try:
            payload = _parse_json_object(response)
        except Exception as exc:
            print(f"  ! Invalid signal output: {exc}")
            return False
        signals = payload.get("signals", [])
        if not isinstance(signals, list):
            print("  ! Signal output missing 'signals' array")
            return False
        save_jsonl(signals, str(_capability_candidates_file()))
        state.metadata["signal_count"] = len(signals)
        self.add_artifact(state, str(_capability_candidates_file()))
        return True

    def _run_synthesize_capabilities(self, state: HarnessState) -> bool:
        signals = self._load_capability_candidates()
        repo_context = self._load_repo_context()
        if self.executor is None:
            print("  ! Capability synthesis orchestration unavailable")
            return False
        prompt = self._build_capability_prompt(signals, repo_context)
        try:
            response = self.executor(
                prompt,
                {"signal_count": str(len(signals))},
                artifact_name="capability-candidates",
                sampling_mode="auto",
            )
        except Exception as exc:
            print(f"  ! Capability synthesis failed: {exc}")
            return False
        try:
            payload = _parse_json_object(response)
        except Exception as exc:
            print(f"  ! Invalid capability candidate output: {exc}")
            return False
        candidates = payload.get("capabilities", [])
        if not isinstance(candidates, list):
            print("  ! Capability candidate output missing 'capabilities' array")
            return False
        save_jsonl(candidates, str(_capability_candidates_file()))
        state.metadata["capability_candidate_count"] = len(candidates)
        return True

    def _run_validate(self, state: HarnessState) -> bool:
        candidates = self._load_capability_candidates()
        stable: list[dict[str, Any]] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            capability_id = candidate.get("capability_id")
            evidence_refs = candidate.get("evidence_refs") or []
            confidence = candidate.get("confidence", "low")
            if not capability_id or not isinstance(evidence_refs, list) or not evidence_refs:
                continue
            if confidence in {"high", "medium"} and len(evidence_refs) < 2:
                continue
            stable.append(candidate)
        save_jsonl(stable, str(_capabilities_file()))
        state.metadata["stable_capability_count"] = len(stable)
        self.add_artifact(state, str(_capabilities_file()))
        return True

    def _run_export(self, state: HarnessState) -> bool:
        candidates = self._load_capability_candidates()
        stable = load_jsonl(str(_capabilities_file()), skip_errors=True) if _capabilities_file().exists() else []
        signal_count = state.metadata.get("signal_count", len(candidates))
        mixed_ratio = 0.0
        low_signal_ratio = 0.0
        naming_drift_count = 0
        if candidates:
            mixed_count = 0
            low_signal_count = 0
            for candidate in candidates:
                flags = candidate.get("flags") or []
                if isinstance(flags, list):
                    if any(flag in {"mixed", "shared_support"} for flag in flags):
                        mixed_count += 1
                    if any(flag in {"low_signal", "low-signal", "low-signal-summary"} for flag in flags):
                        low_signal_count += 1
                observed_names = candidate.get("observed_names") or []
                canonical_name = candidate.get("canonical_name")
                if canonical_name and isinstance(observed_names, list):
                    normalized = {str(name).strip().lower() for name in observed_names if str(name).strip()}
                    if normalized and str(canonical_name).strip().lower() not in normalized:
                        naming_drift_count += 1
            mixed_ratio = round(mixed_count / len(candidates), 4)
            low_signal_ratio = round(low_signal_count / len(candidates), 4)
        evidence_coverage = 0.0
        if stable:
            covered = sum(1 for item in stable if item.get("evidence_refs"))
            evidence_coverage = round(covered / len(stable), 4)
        summary = {
            "signal_count": signal_count,
            "capability_candidate_count": len(candidates),
            "stable_capability_count": len(stable),
            "mixed_ratio": mixed_ratio,
            "low_signal_ratio": low_signal_ratio,
            "evidence_coverage": evidence_coverage,
            "naming_drift_count": naming_drift_count,
        }
        save_json(summary, str(_summary_file()))
        self.add_artifact(state, str(_summary_file()))
        self._remove_legacy_artifacts()
        return True

    def _remove_legacy_artifacts(self) -> None:
        for path in _legacy_artifact_paths():
            if not path.exists():
                continue
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()

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
                print(f"[{self.PIPELINE}] Unknown stage: {args.stage}. Available: {', '.join(self.STAGES)}")
                return 1
            if not self._require_prerequisites():
                return 1
            state = self.init_state()
            save_state(self.PIPELINE, state)
            success = self.run_stage(args.stage, state)
            return 0 if success else 1

        if not self._require_prerequisites():
            return 1

        old_state = load_state(self.PIPELINE)
        if not self.is_fresh(old_state):
            save_state(self.PIPELINE, old_state)

        state = self.init_state()
        save_state(self.PIPELINE, state)
        return self.handle_resume()


def run_commit_semantic() -> None:
    raise SystemExit(CommitSemanticRunner().main())


if __name__ == "__main__":
    run_commit_semantic()
