"""Semantic mapping from issue text to demand card semantic fields."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_DOMAIN_MAP_PATH = "docs/semantic-foundation/semantic/domain-map.yaml"
_CONCEPT_MAP_PATH = "docs/semantic-foundation/semantic/concept-map.yaml"
_RULE_MAP_PATH = "docs/semantic-foundation/semantic/rule-map.yaml"
_DEMAND_MODEL_MAP_PATH = "docs/semantic-foundation/semantic/demand-model-map.yaml"

_INVARIANT_MARKERS = ("must", "always", "never", "required", "cannot", "should not")
_ALIAS_CATALOG: dict[str, dict[str, tuple[str, ...]]] = {
    "domains": {
        "redis discovery": (
            "service registry backend",
            "backend registry",
            "service registry layer",
        ),
        "fs dsl": (
            "filesystem dsl",
            "file system dsl",
            "dsl layer",
        ),
    },
    "concepts": {
        "hash to context operator": (
            "context hashing op",
            "context hash operator",
            "hash context op",
        ),
        "service discovery": (
            "service registry",
            "service lookup",
        ),
    },
    "rules": {
        "api stability": (
            "avoid breaking existing interfaces",
            "interface compatibility",
            "no breaking api changes",
        ),
        "parser compatibility": (
            "old syntax compatibility",
            "legacy syntax compatibility",
        ),
    },
    "invariants": {
        "legacy syntax must remain parseable": (
            "old syntax should continue to work",
            "legacy syntax should remain valid",
        ),
    },
}


def _normalize_list(values: list[Any] | None) -> list[str]:
    if not isinstance(values, list):
        return []

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        candidate = str(value).strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        result.append(candidate)
    return result


def _extract_name(item: Any, fallback_keys: tuple[str, ...]) -> str:
    if isinstance(item, str):
        return item.strip()

    if isinstance(item, dict):
        for key in fallback_keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def _extract_from_asset_group(raw: Any, nested_key: str, fallback_keys: tuple[str, ...]) -> list[str]:
    if isinstance(raw, dict):
        entries = raw.get(nested_key, [])
    else:
        entries = raw

    if not isinstance(entries, list):
        return []

    output: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        name = _extract_name(entry, fallback_keys)
        if name and name not in seen:
            seen.add(name)
            output.append(name)
    return output


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", text.lower()))


def _normalize_phrase(text: str) -> str:
    collapsed = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", collapsed).strip()


def _contains_phrase(haystack: str, needle: str) -> bool:
    if not needle:
        return False
    padded_haystack = f" {haystack} "
    padded_needle = f" {needle} "
    return padded_needle in padded_haystack


def _alias_terms(family: str, candidate: str) -> list[str]:
    terms: list[str] = [candidate, candidate.replace("_", " ")]
    family_aliases = _ALIAS_CATALOG.get(family, {})
    alias_values = family_aliases.get(_normalize_phrase(candidate), ())
    terms.extend(alias_values)
    return _normalize_list(terms)


def _rank_matches(issue_text: str, candidates: list[str], *, family: str) -> list[str]:
    issue_text_lower = issue_text.lower()
    issue_phrase = _normalize_phrase(issue_text)
    issue_tokens = _tokenize(issue_text)

    scored: list[tuple[int, int, str]] = []
    for index, candidate in enumerate(candidates):
        candidate_lower = candidate.lower()
        candidate_tokens = _tokenize(candidate)
        candidate_phrase = _normalize_phrase(candidate)

        score = 0
        if candidate_lower in issue_text_lower or _contains_phrase(issue_phrase, candidate_phrase):
            score += 100

        alias_hit = False
        for alias in _alias_terms(family, candidate):
            alias_phrase = _normalize_phrase(alias)
            # Keep alias matching bounded: require phrase-like aliases (>= 2 tokens).
            if len(alias_phrase.split()) < 2:
                continue
            if _contains_phrase(issue_phrase, alias_phrase):
                alias_hit = True
                break
        if alias_hit:
            score += 60

        overlap = issue_tokens.intersection(candidate_tokens)
        score += len(overlap)

        if score > 0:
            scored.append((score, index, candidate))

    scored.sort(key=lambda item: (-item[0], item[1], item[2].lower()))
    return [item[2] for item in scored]


def _extract_invariants(semantic_assets: dict[str, Any], rules: list[str]) -> list[str]:
    direct_invariants = _extract_from_asset_group(
        semantic_assets.get("invariants"),
        nested_key="invariants",
        fallback_keys=("name", "statement", "summary", "id"),
    )
    if direct_invariants:
        return direct_invariants

    demand_models = semantic_assets.get("demand_models")
    if demand_models is None and isinstance(semantic_assets.get("demand_model_map"), dict):
        demand_models = semantic_assets["demand_model_map"].get("demand_models", [])

    extracted: list[str] = []
    seen: set[str] = set()

    if isinstance(demand_models, list):
        for model in demand_models:
            if not isinstance(model, dict):
                continue
            for key in ("invariants", "constraints"):
                invariants = model.get(key)
                for invariant in _normalize_list(invariants if isinstance(invariants, list) else []):
                    if invariant not in seen:
                        seen.add(invariant)
                        extracted.append(invariant)

    if extracted:
        return extracted

    # Fallback: treat strongly normative rules as invariants.
    for rule in rules:
        lowered = rule.lower()
        if any(marker in lowered for marker in _INVARIANT_MARKERS):
            if rule not in seen:
                seen.add(rule)
                extracted.append(rule)

    return extracted


def load_semantic_foundation_assets(root: str | Path) -> dict[str, Any]:
    """Load semantic foundation maps when available."""
    repo_root = Path(root)
    files = {
        "domain_map": repo_root / _DOMAIN_MAP_PATH,
        "concept_map": repo_root / _CONCEPT_MAP_PATH,
        "rule_map": repo_root / _RULE_MAP_PATH,
        "demand_model_map": repo_root / _DEMAND_MODEL_MAP_PATH,
    }

    loaded: dict[str, Any] = {}
    for key, path in files.items():
        if not path.exists():
            loaded[key] = {}
            continue
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        loaded[key] = data if isinstance(data, dict) else {}

    return loaded


def map_semantics(
    *,
    issue_text: str,
    semantic_assets: dict[str, Any] | None = None,
) -> dict[str, list[str]]:
    """Map issue text onto semantic assets for demand card fields."""
    assets = semantic_assets or {}

    domain_candidates = _extract_from_asset_group(
        assets.get("domains", assets.get("domain_map", {})),
        nested_key="domains",
        fallback_keys=("name", "id", "summary"),
    )
    concept_candidates = _extract_from_asset_group(
        assets.get("concepts", assets.get("concept_map", {})),
        nested_key="concepts",
        fallback_keys=("name", "id", "summary"),
    )
    rule_candidates = _extract_from_asset_group(
        assets.get("rules", assets.get("rule_map", {})),
        nested_key="rules",
        fallback_keys=("name", "statement", "id"),
    )

    domains = _rank_matches(issue_text, domain_candidates, family="domains")
    concepts = _rank_matches(issue_text, concept_candidates, family="concepts")
    rules = _rank_matches(issue_text, rule_candidates, family="rules")

    invariant_candidates = _extract_invariants(assets, rules=rule_candidates)
    invariants = (
        _rank_matches(issue_text, invariant_candidates, family="invariants")
        if invariant_candidates
        else []
    )
    if not invariants and invariant_candidates and (domains or concepts or rules):
        invariants = invariant_candidates

    return {
        "domains": _normalize_list(domains),
        "concepts": _normalize_list(concepts),
        "rules": _normalize_list(rules),
        "invariants": _normalize_list(invariants),
    }
