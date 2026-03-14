"""Refine executor — runs the semantic-refinement skill step by step.

Patches semantic artifacts using architect feedback, generates a change log,
validates results, and applies versioning. Baseline synthesis runs only
when explicit architect acceptance is detected.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import artifact_writer, context_builder, prompt_loader, skill_loader, state_inspector
from .host_executor import HostExecutor


@dataclass
class RefineStepResult:
    """Result of executing a single refine step."""

    step_index: int
    action: str
    target: str
    status: str  # "ok", "skipped", "validation_failed", "error"
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


def validate_refined_artifact(content: str, name: str) -> list[str]:
    """Validate a refined artifact — same rules as discovery validation."""
    errors: list[str] = []
    if not content or not content.strip():
        errors.append(f"{name}: artifact content is empty")
        return errors

    text_lower = content.lower()

    evidence_required = {"repo-understanding", "knowledge-confidence"}
    if name in evidence_required and "evidence" not in text_lower:
        errors.append(f"{name}: missing required evidence section")

    confidence_required = {"repo-understanding", "knowledge-confidence"}
    if name in confidence_required and "confidence" not in text_lower:
        errors.append(f"{name}: missing required confidence section")

    return errors


def _read_architect_feedback(root: Path) -> str | None:
    """Read architect-feedback.md if it exists and has content."""
    path = root / "docs" / "semantic" / "review" / "architect-feedback.md"
    if path.exists():
        text = path.read_text().strip()
        if text:
            return text
    return None


def _check_acceptance(feedback: str) -> bool:
    """Check if architect feedback contains the acceptance signal."""
    return "acceptance: semantic baseline accepted" in feedback.lower()


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
      4. if: acceptance -> baseline-synthesis.prompt (not implemented in Step 6)

    Requires:
      - Discovery artifacts must exist
      - Architect feedback must exist and have content
      - Host executor must be provided
    """
    root = Path(root).resolve()
    result = RefineResult(status="ok")

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

    # --- Step 0: Patch semantic artifacts ---
    patch_result = _execute_patch_step(root, executor, feedback)
    result.steps.append(patch_result)

    if patch_result.artifact_path:
        result.artifacts_written.append(patch_result.artifact_path)

    if patch_result.status == "validation_failed":
        result.validation_failures.append({
            "step": 0, "target": "prompts/refine/semantic-refine.patch.prompt",
            "errors": patch_result.errors,
        })
        result.status = "validation_failed"
        return result

    if patch_result.status == "error":
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
        # Baseline synthesis is not implemented in Step 6.
        # Return a marker so the caller knows acceptance was detected
        # but baseline generation is deferred to Step 7.
        result.steps.append(RefineStepResult(
            step_index=4, action="conditional",
            target="prompts/refine/baseline-synthesis.prompt",
            status="skipped",
            errors=["Baseline synthesis deferred to Step 7"],
        ))

    return result


def _execute_patch_step(
    root: Path,
    executor: HostExecutor,
    feedback: str,
) -> RefineStepResult:
    """Execute semantic-refine.patch.prompt: patch artifacts using feedback.

    Reads latest repo-understanding and knowledge-confidence, sends them
    with architect feedback to the host executor, validates the patched
    output, and writes the next version.
    """
    prompt_path = root / "prompts" / "refine" / "semantic-refine.patch.prompt"
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        return RefineStepResult(
            step_index=0, action="run",
            target="prompts/refine/semantic-refine.patch.prompt",
            status="error",
            errors=["Prompt file not found"],
        )

    ctx = context_builder.build_refine_context(root, "patch", feedback=feedback)

    patched = executor(
        prompt_data["_raw"], ctx,
        artifact_name="repo-understanding",
        sampling_mode="auto",
    )

    path, errors = artifact_writer.safe_write_artifact(
        root, "discovery", "repo-understanding", patched,
        validate_fn=validate_refined_artifact,
    )

    if errors:
        return RefineStepResult(
            step_index=0, action="run",
            target="prompts/refine/semantic-refine.patch.prompt",
            status="validation_failed", errors=errors,
        )

    return RefineStepResult(
        step_index=0, action="run",
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
    out_path.write_text(content)

    return RefineStepResult(
        step_index=1, action="run",
        target="prompts/refine/semantic-change-log.prompt",
        status="ok", artifact_path=str(out_path),
    )


def _execute_validation_step(root: Path) -> RefineStepResult:
    """Validate the latest patched repo-understanding artifact."""
    latest = artifact_writer.get_latest_version_path(root, "discovery", "repo-understanding")
    if latest is None:
        return RefineStepResult(
            step_index=2, action="run",
            target="prompts/validation/validate-artifact.prompt",
            status="error",
            errors=["No repo-understanding artifact to validate"],
        )

    content = latest.read_text()
    errors = validate_refined_artifact(content, "repo-understanding")

    if errors:
        return RefineStepResult(
            step_index=2, action="run",
            target="prompts/validation/validate-artifact.prompt",
            status="validation_failed", artifact_path=str(latest),
            errors=errors,
        )

    return RefineStepResult(
        step_index=2, action="run",
        target="prompts/validation/validate-artifact.prompt",
        status="ok", artifact_path=str(latest),
    )


def _apply_versioning_protocol(root: Path) -> list[str]:
    """Prune old versions for discovery and review artifacts."""
    pruned: list[str] = []
    versioned_artifacts = [
        ("discovery", "repo-facts"),
        ("discovery", "repo-understanding"),
        ("discovery", "knowledge-confidence"),
        ("discovery", "domain-candidates"),
        ("review", "review-summary"),
    ]
    for category, name in versioned_artifacts:
        removed = artifact_writer.prune_old_versions(root, category, name)
        pruned.extend(str(p) for p in removed)
    return pruned
