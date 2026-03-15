"""Repository state inspector — checks semantic state to guide routing."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SemanticState:
    """Snapshot of the current semantic construction state."""

    has_discovery_artifacts: bool = False
    discovery_versions: dict[str, list[int]] = field(default_factory=dict)
    has_review_summary: bool = False
    has_architect_feedback: bool = False
    has_accepted_baseline: bool = False
    has_sampling_report: bool = False
    feedback_has_acceptance: bool = False
    baseline_files: list[str] = field(default_factory=list)


def inspect(root: str | Path) -> SemanticState:
    """Inspect the repository for current semantic state.

    Checks:
      - docs/semantic/discovery/ for versioned artifacts
      - docs/semantic/review/ for review-summary, architect-feedback
      - docs/semantic/baseline/ for accepted baseline files
      - architect-feedback.md for acceptance signal
    """
    root = Path(root)
    state = SemanticState()

    discovery_dir = root / "docs" / "semantic" / "discovery"
    review_dir = root / "docs" / "semantic" / "review"
    baseline_dir = root / "docs" / "semantic" / "baseline"

    # Check discovery artifacts
    if discovery_dir.exists():
        state.discovery_versions = _scan_versions(discovery_dir)
        state.has_discovery_artifacts = bool(state.discovery_versions)
        state.has_sampling_report = (discovery_dir / "sampling-report.md").exists()

    # Check review artifacts
    if review_dir.exists():
        # Check for versioned review-summary files
        review_versions = _scan_versions(review_dir)
        state.has_review_summary = "review-summary" in review_versions and bool(
            review_versions["review-summary"]
        )
        state.has_architect_feedback = _has_content(
            review_dir / "architect-feedback.md"
        )
        if state.has_architect_feedback:
            state.feedback_has_acceptance = _check_acceptance(
                review_dir / "architect-feedback.md"
            )

    # Check baseline
    if baseline_dir.exists():
        state.baseline_files = [
            f.name
            for f in baseline_dir.iterdir()
            if f.is_file() and f.suffix == ".md" and f.name != ".keep"
        ]
        state.has_accepted_baseline = bool(state.baseline_files)

    return state


def recommend_action(state: SemanticState) -> str:
    """Recommend the next action based on current semantic state.

    Routing logic (from semantic-init / semantic-discover / semantic-refine skills):
      - no versioned discovery artifacts -> run discovery
      - no accepted baseline -> run refinement
      - else -> report baseline exists, wait for new feedback
    """
    if not state.has_discovery_artifacts:
        return "discover"
    if not state.has_accepted_baseline:
        return "refine"
    return "done"


def _scan_versions(directory: Path) -> dict[str, list[int]]:
    """Scan a directory for versioned artifacts.

    Returns dict mapping artifact name to sorted list of version numbers.
    """
    pattern = re.compile(r"^(.+)\.v(\d+)\.md$")
    versions: dict[str, list[int]] = {}
    for f in directory.iterdir():
        m = pattern.match(f.name)
        if m:
            name = m.group(1)
            ver = int(m.group(2))
            versions.setdefault(name, []).append(ver)
    for v_list in versions.values():
        v_list.sort()
    return versions


def _has_content(path: Path) -> bool:
    """Check if a file exists and has non-trivial content."""
    if not path.exists():
        return False
    text = path.read_text().strip()
    return len(text) > 0


def _check_acceptance(feedback_path: Path) -> bool:
    """Check if architect-feedback.md contains structured acceptance field.

    Requires the exact field `acceptance: true` (case-insensitive value).
    Free-text mentions of acceptance are not sufficient.
    """
    for line in feedback_path.read_text().splitlines():
        stripped = line.strip().lower()
        if stripped == "acceptance: true":
            return True
    return False
