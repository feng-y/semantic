from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.io_utils import save_json

FIXED_DOC_FILENAMES = [
    "README.md",
    "ARCHITECTURE.md",
    "CLAUDE.md",
    "AGENTS.md",
]
BOOTSTRAP_SCHEMA_VERSION = "v1"
RELIABILITY_MODES = {"full", "degraded", "bypass"}


def _validate_bootstrap_status(value: str) -> str:
    if value not in RELIABILITY_MODES:
        raise ValueError(f"Invalid bootstrap_status: {value}")
    return value


def _relative_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def collect_bootstrap_doc_paths(repo_root: Path) -> dict[str, list[Path]]:
    repo_root = Path(repo_root)

    docs: list[Path] = []
    for filename in FIXED_DOC_FILENAMES:
        path = repo_root / filename
        if path.is_file():
            docs.append(path)

    codebase_root = repo_root / ".planning" / "codebase"
    codebase_map: list[Path] = []
    if codebase_root.is_dir():
        codebase_map = sorted(path for path in codebase_root.iterdir() if path.is_file())

    return {
        "docs": docs,
        "codebase_map": codebase_map,
    }


def read_bootstrap_sources(repo_root: Path) -> dict[str, list[dict[str, str]]]:
    repo_root = Path(repo_root)
    paths = collect_bootstrap_doc_paths(repo_root)

    def read_bucket(items: list[Path]) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        for path in items:
            results.append(
                {
                    "path": _relative_path(repo_root, path),
                    "content": path.read_text(encoding="utf-8"),
                }
            )
        return results

    return {
        "docs": read_bucket(paths["docs"]),
        "codebase_map": read_bucket(paths["codebase_map"]),
    }


def compute_bootstrap_fingerprint(repo_root: Path) -> str:
    repo_root = Path(repo_root)
    paths = collect_bootstrap_doc_paths(repo_root)
    snapshot = {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "docs": [
            {
                "path": _relative_path(repo_root, path),
                "content_sha256": hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            }
            for path in paths["docs"]
        ],
        "codebase_map": [
            {
                "path": _relative_path(repo_root, path),
                "content_sha256": hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest(),
            }
            for path in paths["codebase_map"]
        ],
    }
    serialized = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def compute_bootstrap_summary(shared_hints: dict[str, Any]) -> dict[str, Any]:
    source_snapshot = shared_hints.get("source_snapshot", {})
    docs = source_snapshot.get("docs", [])
    codebase_map = source_snapshot.get("codebase_map", [])

    hint_count = (
        len(shared_hints.get("local_capabilities", []))
        + len(shared_hints.get("aliases", []))
        + len(shared_hints.get("ownership_hints", []))
        + len(shared_hints.get("seed_concepts", []))
    )

    return {
        "bootstrap_status": "full",
        "hint_count": hint_count,
        "source_counts": {
            "docs": len(docs),
            "codebase_map": len(codebase_map),
        },
    }


def build_reliability_summary(
    shared_hints: dict[str, Any],
    *,
    fingerprint: str,
    bootstrap_status: str,
    used_cached_context: bool,
    degraded_reasons: list[str] | None = None,
    bypass_reason: str | None = None,
) -> dict[str, Any]:
    summary = compute_bootstrap_summary(shared_hints)
    summary["bootstrap_status"] = _validate_bootstrap_status(bootstrap_status)
    summary["used_cached_context"] = used_cached_context
    summary["degraded_reasons"] = list(degraded_reasons or [])
    summary["bypass_reason"] = bypass_reason
    summary["fingerprint"] = fingerprint
    return summary


def determine_bootstrap_mode(
    repo_context: dict[str, Any] | None,
    *,
    current_fingerprint: str,
    skip_bootstrap: bool = False,
) -> dict[str, Any]:
    if skip_bootstrap:
        return {
            "bootstrap_status": "bypass",
            "used_cached_context": False,
            "degraded_reasons": [],
            "bypass_reason": "skip-bootstrap",
        }

    if not isinstance(repo_context, dict):
        return {
            "bootstrap_status": "bypass",
            "used_cached_context": False,
            "degraded_reasons": [],
            "bypass_reason": "missing-context",
        }

    shared_hints = repo_context.get("shared_hints")
    semantic_context = repo_context.get("semantic_context")
    summary = repo_context.get("summary")
    if not isinstance(shared_hints, dict) or not isinstance(semantic_context, dict) or not isinstance(summary, dict):
        return {
            "bootstrap_status": "bypass",
            "used_cached_context": False,
            "degraded_reasons": [],
            "bypass_reason": "invalid-context",
        }

    if summary.get("fingerprint") != current_fingerprint:
        return {
            "bootstrap_status": "bypass",
            "used_cached_context": False,
            "degraded_reasons": [],
            "bypass_reason": "stale-context",
        }

    summary_status = summary.get("bootstrap_status")
    if summary_status not in RELIABILITY_MODES:
        return {
            "bootstrap_status": "bypass",
            "used_cached_context": False,
            "degraded_reasons": [],
            "bypass_reason": "invalid-bootstrap-status",
        }

    if summary_status == "bypass":
        return {
            "bootstrap_status": "bypass",
            "used_cached_context": bool(summary.get("used_cached_context", True)),
            "degraded_reasons": [],
            "bypass_reason": summary.get("bypass_reason"),
        }

    degraded_reasons = list(summary.get("degraded_reasons") or [])
    hint_count = compute_bootstrap_summary(shared_hints)["hint_count"]
    if summary_status == "degraded" or hint_count == 0:
        if hint_count == 0 and "empty-shared-hints" not in degraded_reasons:
            degraded_reasons.append("empty-shared-hints")
        return {
            "bootstrap_status": "degraded",
            "used_cached_context": True,
            "degraded_reasons": degraded_reasons,
            "bypass_reason": None,
        }

    return {
        "bootstrap_status": "full",
        "used_cached_context": True,
        "degraded_reasons": [],
        "bypass_reason": None,
    }


def build_repo_context(sources: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    shared_hints = {
        "local_capabilities": [],
        "aliases": [],
        "ownership_hints": [],
        "seed_concepts": [],
        "source_provenance": {},
        "hint_confidence": {},
        "conflicts": [],
        "source_snapshot": {
            "docs": [item["path"] for item in sources.get("docs", [])],
            "codebase_map": [item["path"] for item in sources.get("codebase_map", [])],
        },
    }

    semantic_context = {
        "local_capabilities": list(shared_hints["local_capabilities"]),
        "ownership_hints": list(shared_hints["ownership_hints"]),
        "aliases": list(shared_hints["aliases"]),
        "seed_concepts": list(shared_hints["seed_concepts"]),
        "confidence": "medium",
    }

    return {
        "shared_hints": shared_hints,
        "semantic_context": semantic_context,
        "summary": compute_bootstrap_summary(shared_hints),
    }


def build_bootstrap_context(repo_root: Path) -> dict[str, Any]:
    repo_root = Path(repo_root)
    repo_context = build_repo_context(read_bootstrap_sources(repo_root))
    repo_context["summary"] = build_reliability_summary(
        repo_context["shared_hints"],
        fingerprint=compute_bootstrap_fingerprint(repo_root),
        bootstrap_status="full",
        used_cached_context=False,
    )
    return repo_context


def extract_shared_hints(repo_context: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(repo_context.get("shared_hints", {}))


def extract_shared_hints_for_prompt(repo_context: dict[str, Any]) -> dict[str, Any]:
    return extract_shared_hints(repo_context)


def write_repo_context(output_path: Path, repo_context: dict[str, Any]) -> None:
    save_json(repo_context, str(output_path))


def write_bootstrap_context(output_path: Path, repo_context: dict[str, Any]) -> None:
    write_repo_context(output_path, repo_context)
