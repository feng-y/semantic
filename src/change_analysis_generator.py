"""Generate change-analysis from baseline artifacts."""

from __future__ import annotations

import re


def generate_change_analysis(
    *,
    purpose: str,
    pipelines: str,
    domains: str,
    concepts: str,
) -> str:
    """Generate deterministic change-analysis content from baseline artifacts."""
    primary_purpose = _first_or_default(
        _find_labeled_values(purpose, "Primary Purpose"),
        "Preserve semantic intent while applying targeted repository changes.",
    )
    supported = _find_bullets_after_label(purpose, "Supported Scenarios")
    non_goals = _find_bullets_after_label(purpose, "Non Goals")

    pipeline_names = _find_labeled_values(pipelines, "Pipeline Name")
    domain_names = _find_labeled_values(domains, "Domain Name")
    concept_names = _find_labeled_values(concepts, "Concept Name")
    low_confidence = _collect_low_confidence_signals(pipelines, concepts)

    if not pipeline_names:
        pipeline_names = ["Semantic Baseline Synthesis"]
    if not domain_names:
        domain_names = ["Repository Semantics"]
    if not concept_names:
        concept_names = ["Semantic Artifact"]

    lines: list[str] = [
        "# change-analysis",
        "",
        "## Change Intent",
        f"- Intent: Evolve behavior while preserving primary purpose: {primary_purpose}",
        (
            f"- Boundaries: {', '.join(non_goals[:2])}"
            if non_goals
            else "- Boundaries: Respect existing semantic contracts and non-goals."
        ),
        "",
        "## Affected Pipelines",
    ]
    lines.extend([f"- Pipeline: {name}" for name in pipeline_names[:5]])

    lines.extend([
        "",
        "## Affected Domains and Concepts",
        "- Domains:",
    ])
    lines.extend([f"  - {name}" for name in domain_names[:5]])
    lines.append("- Concepts:")
    lines.extend([f"  - {name}" for name in concept_names[:8]])

    lines.extend([
        "",
        "## Impact and Risks",
        "- Impact:",
        f"  - Primary impact surface includes pipelines: {', '.join(pipeline_names[:3])}",
        f"  - Related domain coverage: {', '.join(domain_names[:3])}",
        "- Risks:",
    ])
    if low_confidence:
        lines.extend([f"  - {risk}" for risk in low_confidence[:5]])
    else:
        lines.append("  - No explicit low-confidence signals found in baseline artifacts.")

    lines.extend([
        "",
        "## Suggested Next Changes",
    ])
    if supported:
        lines.append(f"- Prioritize changes supporting: {supported[0]}")
    lines.append(f"- Start with pipeline updates in: {pipeline_names[0]}")
    lines.append("- Add focused tests for affected domains and concepts before implementation.")
    lines.append("- Re-run semantic refine after change-analysis review feedback.")

    return "\n".join(lines).strip() + "\n"


def _find_labeled_values(content: str, label: str) -> list[str]:
    if not content:
        return []
    pattern = re.compile(
        rf"^\s*[-*]?\s*{re.escape(label)}\s*:\s*(.+?)\s*$",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = [m.strip() for m in pattern.findall(content) if m.strip()]
    return _unique(matches)


def _find_bullets_after_label(content: str, label: str) -> list[str]:
    if not content:
        return []
    lines = content.splitlines()
    label_re = re.compile(rf"^\s*[-*]?\s*{re.escape(label)}\s*:\s*$", re.IGNORECASE)
    bullet_re = re.compile(r"^\s*[-*]\s+(.+)$")

    out: list[str] = []
    for i, raw in enumerate(lines):
        if not label_re.match(raw.strip()):
            continue
        for nxt in lines[i + 1:]:
            if not nxt.strip():
                continue
            bullet = bullet_re.match(nxt)
            if bullet:
                val = bullet.group(1).strip()
                if val:
                    out.append(val)
                continue
            if re.match(r"^\s*[-*]?\s*[A-Za-z].*:\s*", nxt):
                break
            break
        break
    return _unique(out)


def _collect_low_confidence_signals(pipelines: str, concepts: str) -> list[str]:
    signals: list[str] = []
    for text in (pipelines, concepts):
        if not text:
            continue
        lines = text.splitlines()
        for idx, raw in enumerate(lines):
            line = raw.strip().lower()
            if "confidence:" in line and "low" in line:
                prev = lines[idx - 1].strip() if idx > 0 else ""
                context = prev if prev else raw.strip()
                signals.append(f"Low confidence marker near: {context}")
    return _unique(signals)


def _first_or_default(values: list[str], default: str) -> str:
    return values[0] if values else default


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out

