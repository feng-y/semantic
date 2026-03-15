"""Refine executor — runs the semantic-refinement skill step by step.

Patches semantic artifacts using architect feedback, generates a change log,
validates results, and applies versioning. Baseline synthesis runs only
when explicit architect acceptance is detected.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import artifact_writer, context_builder, prompt_loader, skill_loader, state_inspector
from . import artifact_validation
from .host_executor import HostExecutor

# Re-export constants for backward compatibility
BASELINE_SECTIONS = artifact_validation.BASELINE_SECTIONS
REPO_UNDERSTANDING_SECTIONS = artifact_validation.REPO_UNDERSTANDING_SECTIONS
KNOWLEDGE_CONFIDENCE_SECTIONS = artifact_validation.KNOWLEDGE_CONFIDENCE_SECTIONS
REPO_FACTS_SECTIONS = artifact_validation.REPO_FACTS_SECTIONS
DOMAIN_CANDIDATES_SECTIONS = artifact_validation.DOMAIN_CANDIDATES_SECTIONS
REVIEW_SUMMARY_SECTIONS = artifact_validation.REVIEW_SUMMARY_SECTIONS


@dataclass
class RefineStepResult:
    """Result of executing a single refine step."""

    step_index: int
    action: str
    target: str
    status: str  # "ok", "skipped", "validation_failed", "acceptance_failed", "error"
    artifact_path: str | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class RefineResult:
    """Aggregate result of the full refine execution."""

    status: str  # "ok", "error", "execution_unavailable", "validation_failed",
                 # "no_discovery_artifacts", "no_architect_feedback"
    steps: list[RefineStepResult] = field(default_factory=list)
    artifacts_written: list[str] = field(default_factory=list)
    pruned_versions: list[str] = field(default_factory=list)
    validation_failures: list[dict[str, Any]] = field(default_factory=list)
    acceptance_detected: bool = False
    baseline_generated: bool = False


# Re-export helper for backward compatibility
_has_any_section_heading = artifact_validation._has_any_section_heading


def validate_refined_artifact(content: str, name: str) -> list[str]:
    """Validate a refined artifact against schema-defined structural checks."""
    if name == "repo-understanding":
        return artifact_validation.validate_repo_understanding(content)
    elif name == "knowledge-confidence":
        return artifact_validation.validate_knowledge_confidence(content)
    elif name == "domain-candidates":
        return artifact_validation.validate_domain_candidates(content)
    elif name == "review-summary":
        return artifact_validation.validate_review_summary(content)
    elif name == "repo-facts":
        return artifact_validation.validate_repo_facts(content)
    else:
        # Unknown artifact type - no validation
        return []


def _read_architect_feedback(root: Path) -> str | None:
    """Read architect-feedback.md if it exists and has content."""
    path = root / "docs" / "semantic" / "review" / "architect-feedback.md"
    if path.exists():
        text = path.read_text().strip()
        if text:
            return text
    return None


def _check_acceptance(feedback: str) -> bool:
    """Check if architect feedback contains structured acceptance field.

    Requires the exact field `acceptance: true` (case-insensitive value).
    Free-text mentions of acceptance are not sufficient.
    """
    for line in feedback.splitlines():
        stripped = line.strip().lower()
        if stripped == "acceptance: true":
            return True
    return False


def run_refine(
    root: str | Path,
    executor: HostExecutor | None = None,
) -> RefineResult:
    """Execute the semantic-refinement skill.

    Follows the declared step order:
      0. semantic-refine.patch.prompt  (patch repo-understanding + knowledge-confidence)
      1. semantic-change-log.prompt    (generate change log)
      2. validate-artifact.prompt      (validate patched artifacts)
      3. apply: artifact-versioning.md (prune old versions)
      4. if: acceptance -> baseline-synthesis.prompt (generates baseline artifacts)

    Requires:
      - Discovery artifacts must exist
      - Architect feedback must exist and have content
      - Host executor must be provided
    """
    root = Path(root).resolve()
    result = RefineResult(status="ok")

    # Check semantic snapshot for version skew before starting
    skew_warnings = artifact_writer.check_semantic_snapshot(root)
    if skew_warnings:
        result.status = "version_skew"
        result.validation_failures.append({
            "step": -1,
            "target": "semantic_snapshot.json",
            "errors": skew_warnings,
        })
        return result

    # Host executor required (runtime purity)
    if executor is None:
        result.status = "execution_unavailable"
        return result

    # Check preconditions
    state = state_inspector.inspect(root)

    if not state.has_discovery_artifacts:
        result.status = "no_discovery_artifacts"
        return result

    feedback = _read_architect_feedback(root)
    if feedback is None:
        result.status = "no_architect_feedback"
        return result

    result.acceptance_detected = _check_acceptance(feedback)

    # --- Steps 0 + 0b: Staged patch of repo-understanding + knowledge-confidence ---
    staged_result = _execute_staged_patches(root, executor, feedback)
    result.steps.extend(staged_result["steps"])
    result.artifacts_written.extend(staged_result["artifacts_written"])

    if staged_result["status"] == "validation_failed":
        result.validation_failures.extend(staged_result["validation_failures"])
        result.status = "validation_failed"
        return result

    if staged_result["status"] == "error":
        result.status = "error"
        return result

    # --- Step 1: Generate semantic change log ---
    changelog_result = _execute_changelog_step(root, executor, feedback)
    result.steps.append(changelog_result)

    if changelog_result.artifact_path:
        result.artifacts_written.append(changelog_result.artifact_path)

    if changelog_result.status == "error":
        result.status = "error"
        return result

    # --- Step 2: Validate patched artifacts ---
    validation_result = _execute_validation_step(root)
    result.steps.append(validation_result)

    if validation_result.status == "validation_failed":
        result.validation_failures.append({
            "step": 2, "target": "prompts/validation/validate-artifact.prompt",
            "errors": validation_result.errors,
        })
        result.status = "validation_failed"
        return result

    # --- Step 3: Apply versioning protocol ---
    pruned = _apply_versioning_protocol(root)
    result.pruned_versions = pruned
    result.steps.append(RefineStepResult(
        step_index=3, action="apply",
        target="protocols/artifact-versioning.md", status="ok",
    ))

    # --- Step 4: Baseline synthesis (only on acceptance) ---
    if result.acceptance_detected:
        passed, failures = evaluate_acceptance(root, feedback)
        if not passed:
            result.steps.append(RefineStepResult(
                step_index=4, action="conditional",
                target="prompts/refine/baseline-synthesis.prompt",
                status="acceptance_failed", errors=failures,
            ))
        else:
            baseline_result = _execute_baseline_step(root, executor)
            result.steps.append(baseline_result)
            if baseline_result.status == "ok":
                result.baseline_generated = True
                result.artifacts_written.append(baseline_result.artifact_path)
                _write_baseline_checkpoint(root, result, feedback)

    # Write semantic snapshot after successful completion
    if result.status == "ok":
        artifact_writer.write_semantic_snapshot(root)

    return result


def _execute_staged_patches(
    root: Path,
    executor: HostExecutor,
    feedback: str,
) -> dict:
    """Execute patch steps for repo-understanding and knowledge-confidence atomically.

    Both patches are validated before either is written to disk. If either
    fails validation or errors, nothing is written.

    Returns dict with keys: status, steps, artifacts_written, validation_failures.
    """
    result: dict = {
        "status": "ok",
        "steps": [],
        "artifacts_written": [],
        "validation_failures": [],
    }

    prompt_path = root / "prompts" / "refine" / "semantic-refine.patch.prompt"
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        error_step = RefineStepResult(
            step_index=0, action="run",
            target="prompts/refine/semantic-refine.patch.prompt",
            status="error", errors=["Prompt file not found"],
        )
        result["steps"].append(error_step)
        result["status"] = "error"
        return result

    staged: list[tuple[str, str]] = []
    step_results: list[RefineStepResult] = []

    for artifact_name in ("repo-understanding", "knowledge-confidence"):
        ctx = context_builder.build_refine_context(root, "patch", feedback=feedback)
        patched = executor(
            prompt_data["_raw"], ctx,
            artifact_name=artifact_name,
            sampling_mode="auto",
        )

        target_path, content, errors = artifact_writer.stage_artifact(
            root, "discovery", artifact_name, patched,
            validate_fn=validate_refined_artifact,
        )

        step = RefineStepResult(
            step_index=0, action="run",
            target="prompts/refine/semantic-refine.patch.prompt",
            status="ok" if not errors else "validation_failed",
            artifact_path=target_path if not errors else None,
            errors=errors,
        )
        step_results.append(step)

        if errors:
            result["steps"].extend(step_results)
            result["validation_failures"].append({
                "step": 0,
                "target": "prompts/refine/semantic-refine.patch.prompt",
                "errors": errors,
            })
            result["status"] = "validation_failed"
            return result

        staged.append((target_path, content))

    # Both passed validation — commit atomically
    written_paths = artifact_writer.commit_staged(staged)
    for step, path in zip(step_results, written_paths):
        step.artifact_path = str(path)

    result["steps"] = step_results
    result["artifacts_written"] = [str(p) for p in written_paths]
    return result


def _execute_patch_step(
    root: Path,
    executor: HostExecutor,
    feedback: str,
    *,
    artifact_name: str = "repo-understanding",
    step_index: int = 0,
) -> RefineStepResult:
    """Execute semantic-refine.patch.prompt for a specific artifact.

    Reads the latest working version of the target artifact, sends it
    with architect feedback to the host executor, validates the patched
    output, and writes the next version.
    """
    prompt_path = root / "prompts" / "refine" / "semantic-refine.patch.prompt"
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        return RefineStepResult(
            step_index=step_index, action="run",
            target="prompts/refine/semantic-refine.patch.prompt",
            status="error",
            errors=["Prompt file not found"],
        )

    ctx = context_builder.build_refine_context(root, "patch", feedback=feedback)

    patched = executor(
        prompt_data["_raw"], ctx,
        artifact_name=artifact_name,
        sampling_mode="auto",
    )

    path, errors = artifact_writer.safe_write_artifact(
        root, "discovery", artifact_name, patched,
        validate_fn=validate_refined_artifact,
    )

    if errors:
        return RefineStepResult(
            step_index=step_index, action="run",
            target="prompts/refine/semantic-refine.patch.prompt",
            status="validation_failed", errors=errors,
        )

    return RefineStepResult(
        step_index=step_index, action="run",
        target="prompts/refine/semantic-refine.patch.prompt",
        status="ok", artifact_path=str(path),
    )


def _execute_changelog_step(
    root: Path,
    executor: HostExecutor,
    feedback: str,
) -> RefineStepResult:
    """Execute semantic-change-log.prompt: generate change log.

    Writes to docs/semantic/review/semantic-change-log.md (unversioned).
    """
    prompt_path = root / "prompts" / "refine" / "semantic-change-log.prompt"
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        return RefineStepResult(
            step_index=1, action="run",
            target="prompts/refine/semantic-change-log.prompt",
            status="error", errors=["Prompt file not found"],
        )

    ctx = context_builder.build_refine_context(root, "changelog", feedback=feedback)

    content = executor(
        prompt_data["_raw"], ctx,
        artifact_name="semantic-change-log",
        sampling_mode="auto",
    )

    out_path = root / "docs" / "semantic" / "review" / "semantic-change-log.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_writer._atomic_write(out_path, content)

    return RefineStepResult(
        step_index=1, action="run",
        target="prompts/refine/semantic-change-log.prompt",
        status="ok", artifact_path=str(out_path),
    )


def _execute_validation_step(root: Path) -> RefineStepResult:
    """Validate the latest patched repo-understanding and knowledge-confidence."""
    all_errors: list[str] = []
    validated_paths: list[str] = []

    for name in ("repo-understanding", "knowledge-confidence"):
        latest = artifact_writer.get_latest_working_version_path(
            root, "discovery", name,
        )
        if latest is None:
            all_errors.append(f"No {name} artifact to validate")
            continue

        content = latest.read_text()
        errors = validate_refined_artifact(content, name)
        if errors:
            all_errors.extend(errors)
        else:
            validated_paths.append(str(latest))

    if all_errors:
        return RefineStepResult(
            step_index=2, action="run",
            target="prompts/validation/validate-artifact.prompt",
            status="validation_failed",
            artifact_path=validated_paths[0] if validated_paths else None,
            errors=all_errors,
        )

    return RefineStepResult(
        step_index=2, action="run",
        target="prompts/validation/validate-artifact.prompt",
        status="ok",
        artifact_path=validated_paths[0] if validated_paths else None,
    )


def _apply_versioning_protocol(root: Path) -> list[str]:
    """Prune old versions for discovery and review artifacts.

    The latest version and any accepted baseline versions are always
    protected from pruning.
    """
    pruned: list[str] = []
    versioned_artifacts = [
        ("discovery", "repo-facts"),
        ("discovery", "repo-understanding"),
        ("discovery", "knowledge-confidence"),
        ("discovery", "domain-candidates"),
        ("review", "review-summary"),
    ]

    # Load accepted versions from baseline checkpoint
    checkpoint_accepted = artifact_writer.get_accepted_versions(root)

    for category, name in versioned_artifacts:
        latest = artifact_writer.get_latest_working_version_path(root, category, name)
        accepted: set[int] = checkpoint_accepted.get(name, set()).copy()

        # Also protect the latest version
        if latest is not None:
            m = re.search(r"\.v(\d+)\.md$", latest.name)
            if m:
                accepted.add(int(m.group(1)))

        removed = artifact_writer.prune_old_versions(
            root, category, name, accepted_versions=accepted,
        )
        pruned.extend(str(p) for p in removed)
    return pruned


# ---------------------------------------------------------------------------
# Baseline synthesis (Step 7)
# ---------------------------------------------------------------------------


def evaluate_acceptance(root: Path, feedback: str) -> tuple[bool, list[str]]:
    """Evaluate 4 structural runtime gates for baseline synthesis.

    Gates (all must pass):
      1. acceptance: true in feedback (structured field)
      2. knowledge-confidence is non-empty and contains expected confidence structure
      3. repo-understanding is non-empty and contains Evidence sections
      4. domain-candidates is non-empty

    Returns (passed, failures).
    """
    failures: list[str] = []

    # Gate 1: structured acceptance field
    if not _check_acceptance(feedback):
        failures.append("acceptance: true not found in feedback")

    # Gate 2: knowledge-confidence with schema-defined sections
    kc = _read_latest_working(root, "knowledge-confidence")
    if kc is None:
        failures.append("knowledge-confidence artifact not found")
    elif not kc.strip():
        failures.append("knowledge-confidence artifact is empty")
    elif not _has_any_section_heading(kc, KNOWLEDGE_CONFIDENCE_SECTIONS):
        failures.append(
            "knowledge-confidence missing schema-defined section "
            f"(expected one of: {', '.join(KNOWLEDGE_CONFIDENCE_SECTIONS)})"
        )

    # Gate 3: repo-understanding with schema-defined sections
    ru = _read_latest_working(root, "repo-understanding")
    if ru is None:
        failures.append("repo-understanding artifact not found")
    elif not ru.strip():
        failures.append("repo-understanding artifact is empty")
    elif not _has_any_section_heading(ru, REPO_UNDERSTANDING_SECTIONS):
        failures.append(
            "repo-understanding missing schema-defined section "
            f"(expected one of: {', '.join(REPO_UNDERSTANDING_SECTIONS)})"
        )

    # Gate 4: domain-candidates non-empty
    dc = _read_latest_working(root, "domain-candidates")
    if dc is None or not dc.strip():
        failures.append("domain-candidates artifact is empty or missing")

    return (len(failures) == 0, failures)


def _read_latest_working(root: Path, name: str) -> str | None:
    """Shorthand: read latest working discovery artifact."""
    path = artifact_writer.get_latest_working_version_path(root, "discovery", name)
    if path is not None and path.exists():
        return path.read_text()
    return None


def _execute_baseline_step(root: Path, executor: HostExecutor) -> RefineStepResult:
    """Execute baseline-synthesis.prompt and write baseline artifacts."""
    prompt_path = root / "prompts" / "refine" / "baseline-synthesis.prompt"
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        return RefineStepResult(
            step_index=4, action="run",
            target="prompts/refine/baseline-synthesis.prompt",
            status="error", errors=["Prompt file not found"],
        )

    ctx = context_builder.build_baseline_context(root)

    raw_output = executor(
        prompt_data["_raw"], ctx,
        artifact_name="baseline",
        sampling_mode="auto",
    )

    sections = parse_baseline_output(raw_output)

    # Validate all sections
    all_errors: list[str] = []
    for name in BASELINE_SECTIONS:
        if name not in sections:
            all_errors.append(f"missing section: {name}")
            continue
        errors = validate_baseline_artifact(sections[name], name)
        all_errors.extend(errors)

    if all_errors:
        return RefineStepResult(
            step_index=4, action="run",
            target="prompts/refine/baseline-synthesis.prompt",
            status="validation_failed", errors=all_errors,
        )

    # Write all 4 baseline files
    written_paths: list[str] = []
    for name, content in sections.items():
        path = artifact_writer.write_baseline(root, name, content)
        written_paths.append(str(path))

    return RefineStepResult(
        step_index=4, action="run",
        target="prompts/refine/baseline-synthesis.prompt",
        status="ok",
        artifact_path=written_paths[0] if written_paths else None,
    )


def parse_baseline_output(content: str) -> dict[str, str]:
    """Parse host executor output into 4 baseline sections by heading.

    Expected headings: ## Purpose, ## Domains, ## Concepts, ## Pipelines.
    Returns dict mapping section name to content.
    Duplicate headings cause the section to be omitted (treated as invalid).
    """
    section_pattern = re.compile(r"^##\s+(Purpose|Domains|Concepts|Pipelines)\s*$", re.IGNORECASE)
    sections: dict[str, str] = {}
    duplicates: set[str] = set()
    current_name: str | None = None
    current_lines: list[str] = []

    def _flush():
        if current_name is not None:
            if current_name in sections:
                duplicates.add(current_name)
            sections[current_name] = "\n".join(current_lines).strip()

    for line in content.splitlines():
        m = section_pattern.match(line.strip())
        if m:
            _flush()
            current_name = m.group(1).lower()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    _flush()

    # Remove duplicated sections — they indicate malformed output
    for name in duplicates:
        del sections[name]

    return sections


def validate_baseline_artifact(content: str, name: str) -> list[str]:
    """Validate a baseline artifact against its schema's required keyword."""
    return artifact_validation.validate_baseline_files({name: content})


def _write_baseline_checkpoint(root: Path, result: RefineResult, feedback: str) -> None:
    """Write checkpoint.json metadata after successful baseline synthesis."""
    checkpoint_dir = root / "docs" / "semantic" / "baseline"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Collect source version numbers from latest working artifacts
    source_versions: dict[str, int | None] = {}
    for name in ("repo-understanding", "knowledge-confidence", "domain-candidates", "review-summary"):
        category = "review" if name == "review-summary" else "discovery"
        path = artifact_writer.get_latest_working_version_path(root, category, name)
        if path is not None:
            m = re.search(r"\.v(\d+)\.md$", path.name)
            source_versions[name] = int(m.group(1)) if m else None
        else:
            source_versions[name] = None

    baseline_files = [
        f"{name}.md" for name in BASELINE_SECTIONS
    ]

    checkpoint = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_versions": source_versions,
        "baseline_files": baseline_files,
        "feedback_hash": hashlib.sha256(feedback.encode()).hexdigest()[:16],
    }

    checkpoint_path = checkpoint_dir / "checkpoint.json"
    artifact_writer._atomic_write(
        checkpoint_path, json.dumps(checkpoint, indent=2) + "\n",
    )
