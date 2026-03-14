"""Discovery executor — runs the repo-semantic-discovery skill step by step."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import artifact_writer, prompt_loader, skill_loader


@dataclass
class StepResult:
    """Result of executing a single discovery step."""

    step_index: int
    action: str
    target: str
    status: str  # "ok", "skipped", "validation_failed", "error"
    artifact_path: str | None = None
    errors: list[str] = field(default_factory=list)
    prompt_data: dict[str, Any] | None = None


@dataclass
class DiscoveryResult:
    """Aggregate result of the full discovery execution."""

    status: str  # "ok", "timeout_switched", "error"
    sampling_mode: str = "auto"
    sampling_mode_switched: bool = False
    steps: list[StepResult] = field(default_factory=list)
    artifacts_written: list[str] = field(default_factory=list)
    pruned_versions: list[str] = field(default_factory=list)
    validation_failures: list[dict[str, Any]] = field(default_factory=list)


# Maps prompt paths to the artifact name and category they produce.
# This is the contract between prompts and the artifact store.
PROMPT_ARTIFACT_MAP: dict[str, tuple[str, str]] = {
    "prompts/discover/repo-sampling.prompt": ("sampling-report", "discovery"),
    "prompts/discover/repo-facts.prompt": ("repo-facts", "discovery"),
    "prompts/discover/domain-candidates.prompt": ("domain-candidates", "discovery"),
    "prompts/discover/repo-understanding.prompt": ("repo-understanding", "discovery"),
    "prompts/discover/knowledge-confidence.prompt": ("knowledge-confidence", "discovery"),
    "prompts/discover/review-summary.prompt": ("review-summary", "review"),
}

# Prompts that produce unversioned artifacts (overwrite in place)
UNVERSIONED_ARTIFACTS = {"sampling-report"}

# Prompts that augment an existing artifact rather than creating from scratch.
# Maps prompt path -> artifact name to read-then-augment.
AUGMENT_PROMPTS: dict[str, tuple[str, str]] = {
    "prompts/discover/evidence-extraction.prompt": ("repo-facts", "discovery"),
}

# Steps after which validation runs (0-indexed step positions of validate-artifact)
# From the skill: step 3 validates after evidence-extraction, step 6 validates after repo-understanding
VALIDATION_STEP_TARGETS = {
    3: "repo-facts",        # validate repo-facts after evidence-extraction
    6: "repo-understanding",  # validate repo-understanding after repo-understanding
}


def validate_artifact_content(content: str, name: str) -> list[str]:
    """Basic structural validation matching validate-artifact.prompt rules.

    Checks:
    - content is non-empty
    - evidence markers exist (for artifacts that require them)
    - confidence markers exist (for semantic inference artifacts)
    """
    errors: list[str] = []
    if not content or not content.strip():
        errors.append(f"{name}: artifact content is empty")
        return errors

    text_lower = content.lower()

    # Artifacts that require evidence
    evidence_required = {"repo-facts", "repo-understanding", "knowledge-confidence"}
    if name in evidence_required and "evidence" not in text_lower:
        errors.append(f"{name}: missing required evidence section")

    # Artifacts that require confidence
    confidence_required = {"repo-understanding", "knowledge-confidence"}
    if name in confidence_required and "confidence" not in text_lower:
        errors.append(f"{name}: missing required confidence section")

    return errors


def _check_sampling_timeout(
    start_time: float,
    sampling_timeout: int | None,
    sampling_mode: str,
) -> tuple[str, bool]:
    """Check if sampling timeout has been exceeded.

    Returns (effective_mode, switched) where switched is True if
    auto mode was forced to confirm mode due to timeout.
    """
    if sampling_timeout is None:
        return sampling_mode, False
    if sampling_mode != "auto":
        return sampling_mode, False

    elapsed = time.monotonic() - start_time
    if elapsed > sampling_timeout:
        return "confirm", True
    return "auto", False


def _execute_prompt_step(
    root: Path,
    step_index: int,
    target: str,
    sampling_mode: str,
) -> StepResult:
    """Execute a single 'run' step by loading the prompt and producing an artifact.

    The prompt is loaded and its structured data is captured. The actual
    semantic content generation is stubbed — a real implementation would
    feed the prompt to an LLM. The stub produces a placeholder artifact
    that records which prompt was executed and what inputs were available.
    """
    prompt_path = prompt_loader.resolve_prompt_path(target, root)
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="error",
            errors=[f"Prompt file not found: {target}"],
        )

    artifact_info = PROMPT_ARTIFACT_MAP.get(target)
    if artifact_info is None:
        # Prompt doesn't produce a persisted artifact (e.g. validation prompt)
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="ok",
            prompt_data=prompt_data,
        )

    artifact_name, category = artifact_info
    versioned = artifact_name not in UNVERSIONED_ARTIFACTS

    # Build stub content from prompt structure.
    # A real implementation replaces this with LLM output.
    content = _build_stub_content(prompt_data, artifact_name, sampling_mode)

    if versioned:
        path, errors = artifact_writer.safe_write_artifact(
            root, category, artifact_name, content,
            validate_fn=validate_artifact_content,
        )
    else:
        # Unversioned (sampling-report): write directly, no validation gate
        path = artifact_writer.write_artifact(
            root, category, artifact_name, content, versioned=False,
        )
        errors = []

    if errors:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="validation_failed",
            errors=errors,
            prompt_data=prompt_data,
        )

    return StepResult(
        step_index=step_index,
        action="run",
        target=target,
        status="ok",
        artifact_path=str(path),
        prompt_data=prompt_data,
    )


def _execute_augment_step(
    root: Path,
    step_index: int,
    target: str,
    artifact_name: str,
    category: str,
    sampling_mode: str,
) -> StepResult:
    """Execute an augmentation step: read latest artifact, augment, write next version.

    Evidence-extraction reads the latest repo-facts, adds evidence annotations,
    and writes the result as the next repo-facts version. This keeps the artifact
    lineage continuous rather than creating a logically independent artifact.
    """
    prompt_path = prompt_loader.resolve_prompt_path(target, root)
    try:
        prompt_data = prompt_loader.load_prompt(str(prompt_path))
    except FileNotFoundError:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="error",
            errors=[f"Prompt file not found: {target}"],
        )

    # Read the latest version of the artifact to augment
    latest = artifact_writer.get_latest_version_path(root, category, artifact_name)
    if latest is None:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="error",
            errors=[f"No existing '{artifact_name}' artifact to augment"],
        )

    base_content = latest.read_text()

    # Stub: augment the existing content with evidence markers.
    # A real implementation feeds base_content + prompt to an LLM.
    augmented = _build_augmented_stub(base_content, prompt_data, artifact_name)

    path, errors = artifact_writer.safe_write_artifact(
        root, category, artifact_name, augmented,
        validate_fn=validate_artifact_content,
    )

    if errors:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="validation_failed",
            errors=errors,
            prompt_data=prompt_data,
        )

    return StepResult(
        step_index=step_index,
        action="run",
        target=target,
        status="ok",
        artifact_path=str(path),
        prompt_data=prompt_data,
    )


def _execute_validation_step(
    root: Path,
    step_index: int,
    target: str,
    artifact_name: str,
) -> StepResult:
    """Execute a validation step against the latest version of an artifact.

    If validation fails, the artifact is not replaced — the last valid
    version remains as-is per artifact-validation.md rule 5.
    """
    latest = artifact_writer.get_latest_version_path(root, "discovery", artifact_name)
    if latest is None:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="error",
            errors=[f"No versioned artifact found for '{artifact_name}' to validate"],
        )

    content = latest.read_text()
    errors = validate_artifact_content(content, artifact_name)

    if errors:
        return StepResult(
            step_index=step_index,
            action="run",
            target=target,
            status="validation_failed",
            artifact_path=str(latest),
            errors=errors,
        )

    return StepResult(
        step_index=step_index,
        action="run",
        target=target,
        status="ok",
        artifact_path=str(latest),
    )


def _apply_versioning_protocol(root: Path) -> list[str]:
    """Apply artifact-versioning.md: prune old versions beyond retention window.

    Runs pruning for all known versioned artifact names in both
    discovery/ and review/ directories.
    """
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


def _build_stub_content(
    prompt_data: dict[str, Any],
    artifact_name: str,
    sampling_mode: str,
) -> str:
    """Build placeholder artifact content from prompt metadata.

    This is the stub that will be replaced by real LLM generation in Step 5.
    It produces structurally valid content so validation passes.
    """
    goal = prompt_data.get("goal", "No goal specified")
    lines = [
        f"# {artifact_name}",
        "",
        f"Generated by: {prompt_data.get('_path', 'unknown')}",
        f"Goal: {goal}",
        "",
    ]

    if artifact_name == "sampling-report":
        lines.extend([
            f"## Sampling Mode",
            f"{sampling_mode}",
            "",
            "## Selected Areas",
            "- (stub: areas pending real sampling)",
            "",
            "## Selected Files",
            "- (stub: files pending real sampling)",
            "",
            "## Selection Rationale",
            "(stub: rationale pending real sampling)",
            "",
            "## Likely Blind Spots",
            "- (stub: blind spots pending real sampling)",
            "",
            "## Suggested Expansions",
            "- (stub: expansions pending real sampling)",
        ])
    elif artifact_name in ("repo-facts", "repo-understanding"):
        lines.extend([
            "## Evidence",
            "- (stub: evidence pending real extraction)",
            "",
            "## Confidence",
            "- (stub: confidence pending real assessment)",
        ])
    elif artifact_name == "knowledge-confidence":
        lines.extend([
            "## Evidence",
            "- (stub: evidence from repo-understanding)",
            "",
            "## Confidence",
            "- overall: low (stub: pending real assessment)",
        ])
    elif artifact_name == "domain-candidates":
        lines.extend([
            "## Candidate Domains",
            "- (stub: domains pending real extraction)",
        ])
    elif artifact_name == "review-summary":
        lines.extend([
            "## System Summary",
            "(stub: pending real generation)",
            "",
            "## Main Pipelines",
            "- (stub: pending)",
            "",
            "## Core Concepts",
            "- (stub: pending)",
            "",
            "## Candidate Domains",
            "- (stub: pending)",
            "",
            "## Assumptions",
            "- (stub: pending)",
            "",
            "## Questions for Architect",
            "- (stub: pending)",
        ])

    return "\n".join(lines) + "\n"


def _build_augmented_stub(
    base_content: str,
    prompt_data: dict[str, Any],
    artifact_name: str,
) -> str:
    """Augment existing artifact content with evidence stub.

    This is the stub that will be replaced by real LLM augmentation in Step 5.
    It appends evidence annotations to the existing content.
    """
    augmentation = [
        "",
        "## Evidence Annotations",
        f"Augmented by: {prompt_data.get('_path', 'unknown')}",
        "- (stub: file/symbol/line evidence pending real extraction)",
    ]
    return base_content.rstrip() + "\n" + "\n".join(augmentation) + "\n"


def run_discovery(
    root: str | Path,
    sampling_mode: str = "auto",
    sampling_timeout: int | None = None,
) -> DiscoveryResult:
    """Execute the full repo-semantic-discovery skill.

    Follows the declared step order exactly:
      0. repo-sampling.prompt
      1. repo-facts.prompt
      2. evidence-extraction.prompt
      3. validate-artifact.prompt  (validates repo-facts)
      4. domain-candidates.prompt
      5. repo-understanding.prompt
      6. validate-artifact.prompt  (validates repo-understanding)
      7. knowledge-confidence.prompt
      8. review-summary.prompt
      9. apply: artifact-versioning.md

    Sampling mode and timeout are honored per sampling-policy.md:
    - auto: continue automatically after sampling
    - confirm: pause after sampling (returns with status for caller to handle)
    - timeout: if auto exceeds timeout, switch to confirm mode
    """
    root = Path(root).resolve()
    result = DiscoveryResult(status="ok", sampling_mode=sampling_mode)
    start_time = time.monotonic()

    # Load the skill to get the canonical step list
    skills = skill_loader.load_all_skills(root / "manifest.yaml")
    discovery_skill = skills.get("discovery")
    if discovery_skill is None:
        result.status = "error"
        return result

    steps = skill_loader.get_skill_steps(discovery_skill)

    for i, step in enumerate(steps):
        action = step["action"]
        target = step["target"]

        # Check timeout before each step (sampling policy)
        effective_mode, switched = _check_sampling_timeout(
            start_time, sampling_timeout, result.sampling_mode,
        )
        if switched:
            result.sampling_mode = effective_mode
            result.sampling_mode_switched = True

        if action == "run":
            # Is this a validation step?
            if target == "prompts/validation/validate-artifact.prompt":
                artifact_to_validate = VALIDATION_STEP_TARGETS.get(i)
                if artifact_to_validate:
                    step_result = _execute_validation_step(
                        root, i, target, artifact_to_validate,
                    )
                else:
                    step_result = StepResult(
                        step_index=i, action="run", target=target,
                        status="skipped",
                        errors=["No validation target mapped for this step"],
                    )
            # Is this an augmentation step?
            elif target in AUGMENT_PROMPTS:
                aug_name, aug_category = AUGMENT_PROMPTS[target]
                step_result = _execute_augment_step(
                    root, i, target, aug_name, aug_category,
                    result.sampling_mode,
                )
            else:
                step_result = _execute_prompt_step(
                    root, i, target, result.sampling_mode,
                )

            result.steps.append(step_result)

            if step_result.artifact_path:
                result.artifacts_written.append(step_result.artifact_path)

            if step_result.status == "validation_failed":
                result.validation_failures.append({
                    "step": i,
                    "target": target,
                    "errors": step_result.errors,
                })
                # Critical validation failure stops the pipeline
                result.status = "validation_failed"
                return result

            # After sampling step (step 0), check if we need to pause
            if i == 0 and result.sampling_mode == "confirm":
                result.status = "awaiting_confirmation"
                return result

        elif action == "apply":
            # apply: protocols/artifact-versioning.md
            pruned = _apply_versioning_protocol(root)
            result.pruned_versions = pruned
            result.steps.append(StepResult(
                step_index=i,
                action="apply",
                target=target,
                status="ok",
            ))

    return result
