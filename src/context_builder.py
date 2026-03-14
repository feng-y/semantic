"""Context builder — assembles prompt context per 009-prompt-context-contract.md."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from . import artifact_writer


def build_context(
    root: Path,
    prompt_target: str,
    *,
    sampling_mode: str = "auto",
    base_artifact_content: str | None = None,
) -> dict[str, str]:
    """Assemble context for a discovery prompt per the context contract.

    Returns a dict of named context sections. Each value is a string
    ready to be included in the prompt sent to the host executor.
    """
    builders: dict[str, Any] = {
        "prompts/discover/repo-sampling.prompt": _ctx_repo_sampling,
        "prompts/discover/repo-facts.prompt": _ctx_repo_facts,
        "prompts/discover/evidence-extraction.prompt": _ctx_evidence_extraction,
        "prompts/discover/domain-candidates.prompt": _ctx_domain_candidates,
        "prompts/discover/repo-understanding.prompt": _ctx_repo_understanding,
        "prompts/discover/knowledge-confidence.prompt": _ctx_knowledge_confidence,
        "prompts/discover/review-summary.prompt": _ctx_review_summary,
    }

    builder = builders.get(prompt_target)
    if builder is None:
        return {}

    return builder(
        root,
        sampling_mode=sampling_mode,
        base_artifact_content=base_artifact_content,
    )


# ---------------------------------------------------------------------------
# Per-prompt context builders
# ---------------------------------------------------------------------------


def _ctx_repo_sampling(
    root: Path, *, sampling_mode: str, **_: Any,
) -> dict[str, str]:
    """repo-sampling: repository tree summary."""
    return {
        "repo_tree_summary": build_repo_tree_summary(root),
        "sampling_mode": sampling_mode,
    }


def _ctx_repo_facts(
    root: Path, *, sampling_mode: str, **_: Any,
) -> dict[str, str]:
    """repo-facts: sampling-report + selected files + repo tree."""
    ctx: dict[str, str] = {
        "repo_tree_summary": build_repo_tree_summary(root),
    }
    sampling = _read_discovery_artifact(root, "sampling-report", versioned=False)
    if sampling:
        ctx["sampling_report"] = sampling
        ctx["selected_files"] = read_selected_files(root, sampling)
    return ctx


def _ctx_evidence_extraction(
    root: Path, *, base_artifact_content: str | None = None, **_: Any,
) -> dict[str, str]:
    """evidence-extraction: latest repo-facts + selected files."""
    ctx: dict[str, str] = {}
    if base_artifact_content:
        ctx["repo_facts"] = base_artifact_content
    sampling = _read_discovery_artifact(root, "sampling-report", versioned=False)
    if sampling:
        ctx["selected_files"] = read_selected_files(root, sampling)
    return ctx


def _ctx_domain_candidates(root: Path, **_: Any) -> dict[str, str]:
    """domain-candidates: repo-facts artifact."""
    ctx: dict[str, str] = {}
    facts = _read_latest_artifact(root, "discovery", "repo-facts")
    if facts:
        ctx["repo_facts"] = facts
    return ctx


def _ctx_repo_understanding(root: Path, **_: Any) -> dict[str, str]:
    """repo-understanding: repo-facts + domain-candidates."""
    ctx: dict[str, str] = {}
    facts = _read_latest_artifact(root, "discovery", "repo-facts")
    if facts:
        ctx["repo_facts"] = facts
    domains = _read_latest_artifact(root, "discovery", "domain-candidates")
    if domains:
        ctx["domain_candidates"] = domains
    return ctx


def _ctx_knowledge_confidence(root: Path, **_: Any) -> dict[str, str]:
    """knowledge-confidence: repo-understanding artifact."""
    ctx: dict[str, str] = {}
    understanding = _read_latest_artifact(root, "discovery", "repo-understanding")
    if understanding:
        ctx["repo_understanding"] = understanding
    return ctx


def _ctx_review_summary(root: Path, **_: Any) -> dict[str, str]:
    """review-summary: repo-understanding + knowledge-confidence."""
    ctx: dict[str, str] = {}
    understanding = _read_latest_artifact(root, "discovery", "repo-understanding")
    if understanding:
        ctx["repo_understanding"] = understanding
    confidence = _read_latest_artifact(root, "discovery", "knowledge-confidence")
    if confidence:
        ctx["knowledge_confidence"] = confidence
    return ctx


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def build_repo_tree_summary(root: Path) -> str:
    """Build a bounded repository tree summary.

    Uses `git ls-files` if inside a git repo, otherwise walks the directory
    tree with exclusions. Output is capped to prevent token explosion.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().splitlines()
            if len(lines) > 200:
                return "\n".join(lines[:200]) + f"\n... ({len(lines)} files total)"
            return "\n".join(lines)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: walk directory, skip common noise
    skip = {".git", "__pycache__", "node_modules", ".omc", ".venv", "venv"}
    files: list[str] = []
    for p in sorted(root.rglob("*")):
        if any(part in skip for part in p.parts):
            continue
        if p.is_file():
            files.append(str(p.relative_to(root)))
            if len(files) >= 200:
                break
    return "\n".join(files)


def read_selected_files(root: Path, sampling_report: str) -> str:
    """Read files listed in the sampling report's Selected Files section.

    Parses the '## Selected Files' section for markdown list items,
    reads each file, and returns concatenated content with headers.
    """
    files = _parse_selected_files(sampling_report)
    if not files:
        return "(no selected files found in sampling report)"

    parts: list[str] = []
    for rel_path in files:
        fp = root / rel_path
        if fp.is_file():
            try:
                content = fp.read_text()
                # Cap individual file content
                if len(content) > 10000:
                    content = content[:10000] + "\n... (truncated)"
                parts.append(f"--- {rel_path} ---\n{content}")
            except (OSError, UnicodeDecodeError):
                parts.append(f"--- {rel_path} ---\n(unreadable)")
    return "\n\n".join(parts) if parts else "(no readable files)"


def _parse_selected_files(sampling_report: str) -> list[str]:
    """Extract file paths from the Selected Files section of a sampling report."""
    in_section = False
    files: list[str] = []
    for line in sampling_report.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Selected Files"):
            in_section = True
            continue
        if in_section and stripped.startswith("## "):
            break
        if in_section and stripped.startswith("- "):
            path = stripped[2:].strip()
            # Skip stub markers
            if path.startswith("(stub"):
                continue
            files.append(path)
    return files


def _read_discovery_artifact(
    root: Path, name: str, *, versioned: bool = True,
) -> str | None:
    """Read a discovery artifact's content."""
    if versioned:
        return _read_latest_artifact(root, "discovery", name)
    path = root / "docs" / "semantic" / "discovery" / f"{name}.md"
    if path.exists():
        return path.read_text()
    return None


def _read_latest_artifact(
    root: Path, category: str, name: str,
) -> str | None:
    """Read the latest versioned artifact's content."""
    path = artifact_writer.get_latest_version_path(root, category, name)
    if path is not None and path.exists():
        return path.read_text()
    return None


def _read_latest_working_artifact(
    root: Path, category: str, name: str,
) -> str | None:
    """Read the latest working (non-baseline) versioned artifact's content."""
    path = artifact_writer.get_latest_working_version_path(root, category, name)
    if path is not None and path.exists():
        return path.read_text()
    return None


# ---------------------------------------------------------------------------
# Refine context builders
# ---------------------------------------------------------------------------


def build_refine_context(
    root: Path,
    step: str,
    *,
    feedback: str | None = None,
) -> dict[str, str]:
    """Assemble context for a refine prompt.

    Args:
        step: "patch" or "changelog"
        feedback: Architect feedback content
    """
    if step == "patch":
        return _ctx_refine_patch(root, feedback=feedback)
    elif step == "changelog":
        return _ctx_refine_changelog(root, feedback=feedback)
    return {}


def _ctx_refine_patch(
    root: Path, *, feedback: str | None = None,
) -> dict[str, str]:
    """Context for semantic-refine.patch.prompt.

    Inputs per prompt definition:
    - latest working repo-understanding (excludes baseline)
    - latest working knowledge-confidence (excludes baseline)
    - architect-feedback.md
    """
    ctx: dict[str, str] = {}
    understanding = _read_latest_working_artifact(root, "discovery", "repo-understanding")
    if understanding:
        ctx["repo_understanding"] = understanding
    confidence = _read_latest_working_artifact(root, "discovery", "knowledge-confidence")
    if confidence:
        ctx["knowledge_confidence"] = confidence
    if feedback:
        ctx["architect_feedback"] = feedback
    return ctx


def _ctx_refine_changelog(
    root: Path, *, feedback: str | None = None,
) -> dict[str, str]:
    """Context for semantic-change-log.prompt.

    Inputs: latest working repo-understanding + knowledge-confidence + feedback.
    """
    ctx: dict[str, str] = {}
    understanding = _read_latest_working_artifact(root, "discovery", "repo-understanding")
    if understanding:
        ctx["repo_understanding"] = understanding
    confidence = _read_latest_working_artifact(root, "discovery", "knowledge-confidence")
    if confidence:
        ctx["knowledge_confidence"] = confidence
    if feedback:
        ctx["architect_feedback"] = feedback
    return ctx
