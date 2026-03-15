"""Synthesize IBS Core baseline artifacts from FACT artifacts."""

from __future__ import annotations

import re


def generate_ibs_core(
    *,
    repo_facts: str,
    repo_understanding: str,
    domain_candidates: str,
    knowledge_confidence: str,
    review_summary: str,
) -> dict[str, str]:
    """Generate purpose/pipelines/domains/concepts from FACT artifacts."""
    purpose = _generate_purpose(
        repo_facts=repo_facts,
        repo_understanding=repo_understanding,
        knowledge_confidence=knowledge_confidence,
        review_summary=review_summary,
    )
    pipelines = _generate_pipelines(
        repo_facts=repo_facts,
        repo_understanding=repo_understanding,
        domain_candidates=domain_candidates,
        knowledge_confidence=knowledge_confidence,
        review_summary=review_summary,
    )
    domains = _generate_domains(
        domain_candidates=domain_candidates,
        repo_understanding=repo_understanding,
        review_summary=review_summary,
    )
    concepts = _generate_concepts(
        repo_facts=repo_facts,
        repo_understanding=repo_understanding,
        knowledge_confidence=knowledge_confidence,
        review_summary=review_summary,
    )
    return {
        "purpose": purpose,
        "pipelines": pipelines,
        "domains": domains,
        "concepts": concepts,
    }


def _generate_purpose(
    *,
    repo_facts: str,
    repo_understanding: str,
    knowledge_confidence: str,
    review_summary: str,
) -> str:
    ru_system = _extract_section(repo_understanding, ("System Purpose",))
    rs_system = _extract_section(review_summary, ("System Summary",))
    rf_repo = _extract_section(repo_facts, ("Repository",))

    purpose_text = _first_non_empty(
        _first_key_value(ru_system, "Purpose"),
        _first_meaningful_line(rs_system),
        _first_meaningful_line(ru_system),
        "Maintain a stable semantic understanding of the repository and produce IBS core outputs.",
    )
    scenario_a = _first_non_empty(
        _first_meaningful_line(_extract_section(repo_understanding, ("Pipelines",))),
        "Synthesize purpose/pipelines/domains/concepts from validated FACT artifacts.",
    )
    scenario_b = _first_non_empty(
        _first_meaningful_line(rf_repo),
        "Keep semantic baseline artifacts consistent across refine runs.",
    )
    lines = [
        "Primary Purpose: " + purpose_text,
        "Supported Scenarios:",
        f"- {scenario_a}",
        f"- {scenario_b}",
        "Non Goals:",
        "- Do not perform change-analysis in this stage.",
        "- Do not generate implementation-plan artifacts in this stage.",
    ]
    return "\n".join(lines).strip() + "\n"


def _generate_pipelines(
    *,
    repo_facts: str,
    repo_understanding: str,
    domain_candidates: str,
    knowledge_confidence: str,
    review_summary: str,
) -> str:
    ru_pipelines = _extract_section(repo_understanding, ("Pipelines",))
    rs_pipelines = _extract_section(review_summary, ("Pipelines", "Main Pipelines"))
    domain_text = _extract_section(domain_candidates, ("Candidate Domains",))

    names = _unique(
        _find_key_values(ru_pipelines, "Pipeline Name")
        + _find_key_values(rs_pipelines, "Pipeline Name")
        + _find_list_items(_find_key_values(domain_text, "Related Pipelines"))
    )
    if not names:
        names = ["Semantic Baseline Synthesis"]

    purpose_hint = _first_non_empty(
        _first_key_value(ru_pipelines, "Purpose"),
        _first_meaningful_line(rs_pipelines),
        "Transform FACT artifacts into stable IBS core baseline files.",
    )
    flow_hint = "Discovery FACT artifacts -> refine validation -> IBS Core baseline artifacts."
    concept_names = _collect_concept_names(repo_understanding, review_summary)
    concepts_hint = ", ".join(concept_names[:3]) if concept_names else "Repository semantics"
    confidence = _infer_confidence(knowledge_confidence)
    evidence_hint = _first_non_empty(
        _first_meaningful_line(_extract_section(repo_facts, ("Entrypoints",))),
        "repo-understanding / review-summary / repo-facts",
    )

    lines: list[str] = []
    for name in names[:3]:
        lines.extend([
            "Pipeline Name: " + name,
            "Purpose: " + purpose_hint,
            "Flow: " + flow_hint,
            "Inputs: repo-facts, repo-understanding, domain-candidates, knowledge-confidence, review-summary",
            "Outputs: purpose.md, domains.md, concepts.md, pipelines.md",
            "Concepts: " + concepts_hint,
            "Evidence: " + evidence_hint,
            "Confidence: " + confidence,
            "",
        ])
    return "\n".join(lines).strip() + "\n"


def _generate_domains(
    *,
    domain_candidates: str,
    repo_understanding: str,
    review_summary: str,
) -> str:
    dc = _extract_section(domain_candidates, ("Candidate Domains",))
    ru = _extract_section(repo_understanding, ("Candidate Domains",))
    rs = _extract_section(review_summary, ("Candidate Domains",))

    domain_names = _unique(
        _find_key_values(dc, "Domain Name")
        + _find_key_values(ru, "Domain Name")
        + _find_key_values(rs, "Domain Name")
    )
    if not domain_names:
        domain_names = ["Repository Semantics"]

    desc = _first_non_empty(
        _first_key_value(dc, "Description"),
        _first_key_value(ru, "Description"),
        _first_key_value(rs, "Description"),
        "Capability grouping inferred from FACT artifacts.",
    )
    related = _unique(
        _find_list_items(_find_key_values(dc, "Related Pipelines"))
        + _find_list_items(_find_key_values(ru, "Related Pipelines"))
    )
    if not related:
        related = ["Semantic Baseline Synthesis"]

    lines: list[str] = []
    for name in domain_names[:3]:
        lines.extend([
            "Domain Name: " + name,
            "Description: " + desc,
            "Related Pipelines:",
        ])
        lines.extend([f"- {p}" for p in related[:3]])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _generate_concepts(
    *,
    repo_facts: str,
    repo_understanding: str,
    knowledge_confidence: str,
    review_summary: str,
) -> str:
    ru_concepts = _extract_section(repo_understanding, ("Concepts",))
    rs_concepts = _extract_section(review_summary, ("Concepts", "Core Concepts"))
    rf_entities = _extract_section(repo_facts, ("Core Entities",))

    names = _collect_concept_names(repo_understanding, review_summary)
    if not names:
        names = _find_key_values(rf_entities, "Name")
    if not names:
        names = ["Semantic Artifact"]

    desc = _first_non_empty(
        _first_key_value(ru_concepts, "Description"),
        _first_meaningful_line(rs_concepts),
        "Core semantic unit used to explain repository behavior.",
    )
    role = _first_non_empty(
        _first_key_value(ru_concepts, "Role"),
        "Capture stable repository knowledge for downstream planning.",
    )
    used_by = _first_non_empty(
        _first_key_value(ru_concepts, "Used By"),
        "purpose.md / pipelines.md / domains.md",
    )
    evidence = _first_non_empty(
        _first_key_value(ru_concepts, "Evidence"),
        _first_meaningful_line(rf_entities),
        "repo-understanding / review-summary / repo-facts",
    )
    confidence = _infer_confidence(knowledge_confidence)

    lines: list[str] = []
    for name in names[:5]:
        lines.extend([
            "Concept Name: " + name,
            "Description: " + desc,
            "Role: " + role,
            "Used By: " + used_by,
            "Evidence: " + evidence,
            "Confidence: " + confidence,
            "",
        ])
    return "\n".join(lines).strip() + "\n"


def _extract_section(content: str, headings: tuple[str, ...]) -> str:
    if not content:
        return ""
    normalized = {h.lower() for h in headings}
    current_heading: str | None = None
    current_lines: list[str] = []
    sections: dict[str, str] = {}

    for raw in content.splitlines():
        line = raw.strip()
        match = re.match(r"^##\s+(.+?)\s*$", line)
        if match:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = match.group(1).strip().lower()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(raw)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()

    for key in normalized:
        if key in sections:
            return sections[key]
    return ""


def _first_key_value(content: str, key: str) -> str:
    values = _find_key_values(content, key)
    return values[0] if values else ""


def _find_key_values(content: str, key: str) -> list[str]:
    if not content:
        return []
    pattern = re.compile(rf"^\s*[-*]?\s*{re.escape(key)}\s*:\s*(.+?)\s*$", re.IGNORECASE)
    values: list[str] = []
    for raw in content.splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        value = match.group(1).strip()
        if value:
            values.append(value)
    return _unique(values)


def _find_list_items(values: list[str]) -> list[str]:
    items: list[str] = []
    for value in values:
        for part in value.split(","):
            item = part.strip()
            if item:
                items.append(item)
    return _unique(items)


def _first_meaningful_line(content: str) -> str:
    if not content:
        return ""
    for raw in content.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("-"):
            line = line.lstrip("-").strip()
        if line:
            return line
    return ""


def _first_non_empty(*values: str) -> str:
    for value in values:
        if value and value.strip():
            return value.strip()
    return ""


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


def _collect_concept_names(repo_understanding: str, review_summary: str) -> list[str]:
    ru_concepts = _extract_section(repo_understanding, ("Concepts",))
    rs_concepts = _extract_section(review_summary, ("Concepts", "Core Concepts"))
    names = _find_key_values(ru_concepts, "Concept Name") + _find_key_values(rs_concepts, "Concept Name")

    if names:
        return _unique(names)

    fallback: list[str] = []
    for text in (ru_concepts, rs_concepts):
        line = _first_meaningful_line(text)
        if line:
            fallback.append(line)
    return _unique(fallback)


def _infer_confidence(knowledge_confidence: str) -> str:
    lower = (knowledge_confidence or "").lower()
    if "confidence: high" in lower or "overall: high" in lower:
        return "high"
    if "confidence: low" in lower or "overall: low" in lower:
        return "low"
    return "medium"
