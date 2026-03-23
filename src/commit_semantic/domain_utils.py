"""Domain utilities for commit-semantic pipeline.

Pure functions for domain discovery and assignment.
LLM orchestration stays in run.py; this module is fully testable without mocks.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

NOISE_DOMAIN_NAMES = {
    "misc",
    "other",
    "others",
    "general",
    "generic",
    "unknown",
    "uncategorized",
}


def _normalize_name(value: str) -> str:
    return (value or "").strip().lower()


def _singular_plural_forms(name: str) -> set[str]:
    normalized = _normalize_name(name)
    forms = {normalized}
    if normalized.endswith("s") and len(normalized) > 1:
        forms.add(normalized[:-1])
    elif normalized:
        forms.add(f"{normalized}s")
    return forms


def _unique_sorted_strings(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _is_noise_domain(domain: dict) -> bool:
    return _normalize_name(domain.get("domain", "")) in NOISE_DOMAIN_NAMES


def choose_domain_winner(left: dict, right: dict) -> dict:
    """Choose the stronger canonical domain between two merge candidates."""
    left_name = _normalize_name(left.get("domain", ""))
    right_name = _normalize_name(right.get("domain", ""))

    if left_name != right_name and left_name in _singular_plural_forms(right_name):
        if right_name.endswith("s") and not left_name.endswith("s"):
            return right
        if left_name.endswith("s") and not right_name.endswith("s"):
            return left

    left_score = (
        len(_unique_sorted_strings(left.get("paths", []))),
        len(_unique_sorted_strings(left.get("keywords", []))),
        len((left.get("description", "") or "").strip()),
    )
    right_score = (
        len(_unique_sorted_strings(right.get("paths", []))),
        len(_unique_sorted_strings(right.get("keywords", []))),
        len((right.get("description", "") or "").strip()),
    )
    return right if right_score > left_score else left


def should_merge_domains(left: dict, right: dict) -> bool:
    """Return True when two discovered domains represent the same cluster."""
    left_name = _normalize_name(left.get("domain", ""))
    right_name = _normalize_name(right.get("domain", ""))
    if not left_name or not right_name:
        return False
    if left_name == right_name:
        return True
    if left_name in _singular_plural_forms(right_name):
        return True

    left_keywords = {_normalize_name(value) for value in left.get("keywords", []) if _normalize_name(value)}
    right_keywords = {_normalize_name(value) for value in right.get("keywords", []) if _normalize_name(value)}
    if len(left_keywords & right_keywords) >= 2 and _overlap_ratio(left_keywords, right_keywords) >= 0.5:
        return True

    left_paths = {value for value in left.get("paths", []) if value}
    right_paths = {value for value in right.get("paths", []) if value}
    if left_paths and right_paths and _overlap_ratio(left_paths, right_paths) >= 0.6:
        return True

    return False


def _merge_domain_pair(left: dict, right: dict) -> dict:
    winner = choose_domain_winner(left, right)
    loser = right if winner is left else left
    return {
        "domain": winner.get("domain", ""),
        "description": winner.get("description", "") or loser.get("description", ""),
        "paths": _unique_sorted_strings(list(winner.get("paths", [])) + list(loser.get("paths", []))),
        "keywords": _unique_sorted_strings(list(winner.get("keywords", [])) + list(loser.get("keywords", []))),
    }


def normalize_domains(domains: list[dict]) -> list[dict]:
    """Filter noise and merge overlapping discovered domains into canonical entries."""
    normalized: list[dict] = []
    for domain in domains:
        candidate = {
            "domain": domain.get("domain", ""),
            "description": domain.get("description", ""),
            "paths": _unique_sorted_strings(list(domain.get("paths", []))),
            "keywords": _unique_sorted_strings(list(domain.get("keywords", []))),
        }
        if not candidate["domain"] or _is_noise_domain(candidate):
            continue

        merged = False
        for index, existing in enumerate(normalized):
            if should_merge_domains(existing, candidate):
                normalized[index] = _merge_domain_pair(existing, candidate)
                merged = True
                break
        if not merged:
            normalized.append(candidate)

    return normalized


def build_sha_file_map(repo_path: str, shas: list[str]) -> tuple[dict[str, list[str]], bool]:
    """Batch-fetch SHA → file_paths mapping. Single git call.

    Returns (sha_map, success). If git fails, returns empty lists for all SHAs
    and success=False so caller can record degradation in summary.

    Critical: --no-walk prevents git from walking full history per SHA.
    """
    if not shas:
        return {}, True

    result = subprocess.run(
        ["git", "log", "--name-only", "--format=%H", "--stdin", "--no-walk"],
        input="\n".join(shas),
        capture_output=True, text=True, cwd=repo_path,
    )
    if result.returncode != 0:
        logger.warning("git log failed (rc=%d): %s", result.returncode, result.stderr[:200])
        return {sha: [] for sha in shas}, False

    sha_map: dict[str, list[str]] = {}
    current_sha = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if len(line) == 40 and all(c in "0123456789abcdef" for c in line):
            current_sha = line
            sha_map[current_sha] = []
        elif current_sha:
            sha_map[current_sha].append(line)
    return sha_map, True


def assign_domain_by_path(file_paths: list[str], domains: list[dict]) -> str | None:
    """Path-prefix matching at commit level. Longest prefix wins.

    Returns domain name if ALL file_paths resolve to the same domain (single-domain commit).
    Returns None if paths span multiple domains or no match (needs LLM classification).
    """
    if not file_paths or not domains:
        return None

    matched_domains: set[str] = set()
    for fp in file_paths:
        best_domain = None
        best_prefix_len = 0
        for domain in domains:
            for path_prefix in domain.get("paths", []):
                if fp.startswith(path_prefix) and len(path_prefix) > best_prefix_len:
                    best_prefix_len = len(path_prefix)
                    best_domain = domain["domain"]
        if best_domain:
            matched_domains.add(best_domain)

    if len(matched_domains) == 1:
        return matched_domains.pop()
    return None


def parse_llm_domains(raw: str) -> list[dict]:
    """Parse LLM output for domain discovery. Expects JSON array.

    Returns parsed domains list, or empty list on parse failure.
    Each domain must have at least 'domain' and 'description' keys.
    """
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM domains output as JSON")
        return []

    if not isinstance(data, list):
        logger.warning("LLM domains output is not a list")
        return []

    valid = []
    for item in data:
        if isinstance(item, dict) and "domain" in item:
            valid.append({
                "domain": item["domain"],
                "description": item.get("description", ""),
                "paths": item.get("paths", []),
                "keywords": item.get("keywords", []),
            })
    return valid


def parse_llm_classifications(raw: str) -> dict[str, str]:
    """Parse LLM output for unit classification. Expects JSON array of {id, domain}.

    Returns {unit_id: domain} mapping. Unparseable entries are skipped.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        raw = "\n".join(lines).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM classification output as JSON")
        return {}

    if not isinstance(data, list):
        return {}

    result: dict[str, str] = {}
    for item in data:
        if isinstance(item, dict) and "id" in item and "domain" in item:
            result[str(item["id"])] = item["domain"]
    return result


TOKEN_PATTERN = re.compile(r"[a-z0-9_/-]+")
PATH_PREFIX_WEIGHT = 5
THEME_TOKEN_WEIGHT = 3
SUMMARY_TOKEN_WEIGHT = 2
SECTION_NAME_TOKEN_WEIGHT = 2
DOMAIN_KEYWORD_WEIGHT = 1
MIN_ASSIGNMENT_SCORE = 4
AMBIGUITY_DELTA = 2


def _tokenize_signal(value: str) -> set[str]:
    normalized = (value or "").lower().replace("-", " ").replace("_", " ").replace("/", " ")
    return {token for token in TOKEN_PATTERN.findall(normalized) if token}


def _split_keywords(values: list[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        tokens.update(_tokenize_signal(value))
    return tokens


def _domain_tokens(domain: dict) -> set[str]:
    domain_name = str(domain.get("domain", "") or "").replace("-", " ").replace("_", " ")
    return _tokenize_signal(domain_name)


def score_unit_for_domain(unit: dict, domain: dict, *, allow_path_scoring: bool = True) -> int:
    """Deterministically score one unit against one domain."""
    score = 0

    unit_paths = [path for path in unit.get("file_paths", []) if path]
    if allow_path_scoring and unit_paths:
        if any(
            path.startswith(path_prefix)
            for path_prefix in domain.get("paths", [])
            if path_prefix
            for path in unit_paths
        ):
            score += PATH_PREFIX_WEIGHT

    domain_tokens = _domain_tokens(domain)
    keyword_tokens = _split_keywords(list(domain.get("keywords", [])))
    signal_tokens = domain_tokens | keyword_tokens

    theme_tokens = _tokenize_signal(unit.get("theme", ""))
    if signal_tokens & theme_tokens:
        score += THEME_TOKEN_WEIGHT

    summary_tokens = _tokenize_signal(unit.get("summary", ""))
    if signal_tokens & summary_tokens:
        score += SUMMARY_TOKEN_WEIGHT

    section_tokens = _tokenize_signal(unit.get("section_name", ""))
    if signal_tokens & section_tokens:
        score += SECTION_NAME_TOKEN_WEIGHT

    if keyword_tokens & (theme_tokens | summary_tokens | section_tokens):
        score += DOMAIN_KEYWORD_WEIGHT

    return score


def classify_unit_locally(unit: dict, domains: list[dict], *, allow_path_scoring: bool = True) -> str | None:
    """Return a deterministic domain only when evidence is strong and unambiguous."""
    scored: list[tuple[int, str]] = []
    for domain in domains:
        score = score_unit_for_domain(unit, domain, allow_path_scoring=allow_path_scoring)
        scored.append((score, domain.get("domain", "")))

    if not scored:
        return None

    scored.sort(key=lambda item: (-item[0], item[1]))
    top_score, top_domain = scored[0]
    if top_score < MIN_ASSIGNMENT_SCORE:
        return None

    second_score = scored[1][0] if len(scored) > 1 else 0
    if top_score - second_score < AMBIGUITY_DELTA:
        return None

    return top_domain or None


def compute_fingerprint(units_file: Path, arch_file: Path | None = None) -> dict:
    """Compute content fingerprint for cache invalidation.

    Returns dict with units_hash, arch_hash (or null), for embedding in domains.json.
    """
    units_hash = ""
    if units_file.exists():
        h = hashlib.sha256()
        with open(units_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        units_hash = h.hexdigest()[:16]

    arch_hash = None
    if arch_file and arch_file.exists():
        h = hashlib.sha256()
        with open(arch_file, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        arch_hash = h.hexdigest()[:16]

    return {"units_hash": units_hash, "arch_hash": arch_hash}


def fingerprint_matches(domains_data: dict, current_fp: dict) -> bool:
    """Check if cached domains.json fingerprint matches current inputs."""
    cached_fp = domains_data.get("_fingerprint", {})
    return (
        cached_fp.get("units_hash") == current_fp.get("units_hash")
        and cached_fp.get("arch_hash") == current_fp.get("arch_hash")
    )


def build_units_summary(units: list[dict], max_themes: int = 30, max_summaries: int = 5) -> str:
    """Build a compact summary of units for the discover LLM prompt.

    Includes theme distribution, op distribution, and representative summaries.
    """
    from collections import Counter

    theme_counts = Counter(u.get("theme", "unknown") for u in units)
    op_counts = Counter(u.get("op", "other") for u in units)

    top_themes = theme_counts.most_common(max_themes)
    summaries = []
    seen_themes: set[str] = set()
    for u in units:
        theme = u.get("theme", "")
        summary = u.get("summary", "")
        if summary and theme not in seen_themes and len(summaries) < max_summaries:
            summaries.append(f"[{theme}] {summary}")
            seen_themes.add(theme)

    lines = [
        f"Total units: {len(units)}",
        f"Distinct themes: {len(theme_counts)}",
        "",
        "Theme distribution (top {}):" .format(min(max_themes, len(top_themes))),
    ]
    for theme, count in top_themes:
        lines.append(f"  {theme}: {count}")

    lines.append("")
    lines.append("Op distribution:")
    for op, count in op_counts.most_common():
        lines.append(f"  {op}: {count}")

    if summaries:
        lines.append("")
        lines.append("Representative summaries:")
        for s in summaries:
            lines.append(f"  - {s}")

    return "\n".join(lines)
