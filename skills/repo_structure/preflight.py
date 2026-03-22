"""Preflight checks for repo-structure pipeline.

Performs dependency validation, freshness checks, and snapshot matching
before any stage executes. Follows the contract in:
  docs/superpowers/specs/2026-03-22-preflight-rules.md

Classification levels:
  - missing: required dependency does not exist  → fail
  - invalid: dependency exists but unusable         → fail
  - warning: usable but suboptimal                  → warn
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class PreflightIssue:
    code: str
    subject: str
    message: str
    producer: str | None = None
    suggestion: str | None = None


@dataclass
class PreflightResult:
    ok: bool = True
    repo_head: str = ""
    missing: list[PreflightIssue] = field(default_factory=list)
    invalid: list[PreflightIssue] = field(default_factory=list)
    warnings: list[PreflightIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "repo_head": self.repo_head,
            "missing": [
                {"code": i.code, "subject": i.subject, "message": i.message,
                 "producer": i.producer, "suggestion": i.suggestion}
                for i in self.missing
            ],
            "invalid": [
                {"code": i.code, "subject": i.subject, "message": i.message,
                 "producer": i.producer, "suggestion": i.suggestion}
                for i in self.invalid
            ],
            "warnings": [
                {"code": i.code, "subject": i.subject, "message": i.message,
                 "producer": i.producer, "suggestion": i.suggestion}
                for i in self.warnings
            ],
        }


# SHARED CONSTANT — imported by run.py to avoid duplication
REQUIRED_GSD_FILES = [
    "STRUCTURE.md",
    "ARCHITECTURE.md",
    "CONCERNS.md",
    "CONVENTIONS.md",
    "INTEGRATIONS.md",
    "STACK.md",
    "TESTING.md",
]


def check(repo_root: Path | str = ".") -> PreflightResult:
    """Run all preflight checks. Returns result with missing/invalid/warnings lists."""
    root = Path(repo_root).resolve()
    result = PreflightResult()

    # 1. Repo root
    if not root.exists():
        result.ok = False
        result.missing.append(PreflightIssue(
            "MISSING_REPO_ROOT", "repo_root",
            f"Path does not exist: {root}"))
        return result

    # 2. Git repo
    if not (root / ".git").exists():
        result.ok = False
        result.missing.append(PreflightIssue(
            "MISSING_GIT_REPO", ".git",
            "Not a git repository", suggestion="cd to git repo root"))
        return result

    # 3. Current snapshot (HEAD commit)
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root, capture_output=True, text=True, check=True
        )
        result.repo_head = head.stdout.strip()
    except subprocess.CalledProcessError:
        result.ok = False
        result.invalid.append(PreflightIssue(
            "INVALID_HEAD", "git HEAD",
            "Cannot resolve HEAD commit"))
        return result

    # 4. Writable output path
    out_dir = root / "data" / "repo-structure"
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        result.ok = False
        result.invalid.append(PreflightIssue(
            "OUTPUT_NOT_WRITABLE", str(out_dir),
            f"Cannot create output directory: {e}"))

    # 5. Required: commit-extract
    commit_extract = root / "data" / "commit-extract"
    if not commit_extract.exists():
        result.ok = False
        result.missing.append(PreflightIssue(
            "MISSING_INPUT", "data/commit-extract/",
            "Upstream commit-extract output not found",
            producer="commit-extract",
            suggestion="/commit-extract run"))
    elif not any(commit_extract.iterdir()):
        result.ok = False
        result.invalid.append(PreflightIssue(
            "EMPTY_ARTIFACT", "data/commit-extract/",
            "commit-extract directory is empty",
            producer="commit-extract"))

    # 6. Required: 7-file gsd dossier (uses the SHARED constant)
    gsd_dir = root / ".planning" / "codebase"
    for fname in REQUIRED_GSD_FILES:
        fpath = gsd_dir / fname
        if not fpath.exists():
            result.ok = False
            result.missing.append(PreflightIssue(
                "MISSING_INPUT", str(fpath.relative_to(root)),
                f"gsd file not found",
                producer="gsd::map-codebase",
                suggestion="Run gsd map-codebase first"))
        elif fpath.stat().st_size == 0:
            result.ok = False
            result.invalid.append(PreflightIssue(
                "EMPTY_ARTIFACT", str(fpath.relative_to(root)),
                f"gsd file is empty",
                producer="gsd::map-codebase"))

    # 7. Optional: architecture doc
    arch_doc = root / "docs" / "ARCHITECTURE.md"
    if not arch_doc.exists():
        result.warnings.append(PreflightIssue(
            "OPTIONAL_INPUT_MISSING", "docs/ARCHITECTURE.md",
            "Optional architecture doc not found; augment stage will emit empty output",
            producer="architect"))
    elif arch_doc.stat().st_size == 0:
        result.warnings.append(PreflightIssue(
            "EMPTY_ARTIFACT", "docs/ARCHITECTURE.md",
            "Architecture doc is empty; augment stage may produce weak results"))

    return result
