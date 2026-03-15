"""Validation helpers for IBS Core baseline outputs."""

from __future__ import annotations

import re

from . import artifact_validation


IBS_CORE_NAMES = ("purpose", "pipelines", "domains", "concepts")

REQUIRED_FIELD_LABELS: dict[str, tuple[str, ...]] = {
    "purpose": ("Primary Purpose", "Supported Scenarios", "Non Goals"),
    "pipelines": (
        "Pipeline Name", "Purpose", "Flow", "Inputs",
        "Outputs", "Concepts", "Evidence", "Confidence",
    ),
    "domains": ("Domain Name", "Description", "Related Pipelines"),
    "concepts": ("Concept Name", "Description", "Role", "Used By", "Evidence", "Confidence"),
}


def _has_labeled_field(content: str, label: str) -> bool:
    pattern = re.compile(
        rf"^\s*[-*]?\s*{re.escape(label)}\s*:\s*.*$",
        re.IGNORECASE | re.MULTILINE,
    )
    return pattern.search(content) is not None


def _count_labeled_field(content: str, label: str) -> int:
    pattern = re.compile(
        rf"^\s*[-*]?\s*{re.escape(label)}\s*:\s*.*$",
        re.IGNORECASE | re.MULTILINE,
    )
    return len(pattern.findall(content))


def _has_list_item_after_label(content: str, label: str) -> bool:
    """Require at least one bullet item following a section-like label line."""
    lines = content.splitlines()
    label_pattern = re.compile(rf"^\s*[-*]?\s*{re.escape(label)}\s*:\s*$", re.IGNORECASE)
    bullet_pattern = re.compile(r"^\s*[-*]\s+\S+")

    for i, raw in enumerate(lines):
        if not label_pattern.match(raw.strip()):
            continue
        for next_line in lines[i + 1:]:
            stripped = next_line.strip()
            if not stripped:
                continue
            if bullet_pattern.match(next_line):
                return True
            if re.match(r"^\s*[-*]?\s*[A-Za-z].*:\s*", next_line):
                break
        return False
    return False


def _validate_required_structure(name: str, content: str) -> list[str]:
    errors: list[str] = []
    required = REQUIRED_FIELD_LABELS.get(name, ())
    for label in required:
        if not _has_labeled_field(content, label):
            errors.append(f"missing required field label: {label}")

    # Artifact-specific minimal section checks
    if name == "purpose":
        if not _has_list_item_after_label(content, "Supported Scenarios"):
            errors.append("purpose: 'Supported Scenarios' must include at least one list item")
        if not _has_list_item_after_label(content, "Non Goals"):
            errors.append("purpose: 'Non Goals' must include at least one list item")
    elif name == "pipelines":
        if _count_labeled_field(content, "Pipeline Name") < 1:
            errors.append("pipelines: must contain at least one pipeline section")
    elif name == "domains":
        if _count_labeled_field(content, "Domain Name") < 1:
            errors.append("domains: must contain at least one domain section")
        if not _has_list_item_after_label(content, "Related Pipelines"):
            errors.append("domains: 'Related Pipelines' must include at least one list item")
    elif name == "concepts":
        if _count_labeled_field(content, "Concept Name") < 1:
            errors.append("concepts: must contain at least one concept section")
    return errors


def validate_ibs_core_artifact(name: str, content: str) -> list[str]:
    """Validate a single IBS Core artifact with baseline + structure checks."""
    errors: list[str] = []
    if name not in IBS_CORE_NAMES:
        return [f"unknown ibs core artifact: {name}"]

    errors.extend(artifact_validation.validate_baseline_files({name: content}))
    if not content or not content.strip():
        return errors
    errors.extend(_validate_required_structure(name, content))
    return errors


def validate_ibs_core_outputs(outputs: dict[str, str]) -> list[str]:
    """Validate all required IBS Core outputs."""
    errors: list[str] = []
    for name in IBS_CORE_NAMES:
        content = outputs.get(name)
        if content is None:
            errors.append(f"missing ibs core output: {name}")
            continue
        artifact_errors = validate_ibs_core_artifact(name, content)
        for err in artifact_errors:
            errors.append(f"{name}: {err}")
    return errors
