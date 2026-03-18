"""
Strict deduplication logic for semantic cases.

Identifies exact duplicates based on:
- module
- development_type
- normalized issue_text
- optional constraint signature

Note: commit_log is NOT included in dedup key per P2/P3/P4 spec.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable

from .normalize import build_constraint_signature, normalize_text


@dataclass
class DedupInput:
    """Input case for deduplication."""
    case_id: str
    module: str
    development_type: str
    issue_text: str
    rules: list[str]
    invariants: list[str]
    semantic_value: str = "medium"


@dataclass
class DedupGroup:
    """Group of duplicate cases with canonical selection."""
    dedup_key: str
    canonical_case_id: str
    duplicate_case_ids: list[str] = field(default_factory=list)


def build_dedup_key(case: DedupInput, *, use_constraint_signature: bool = False) -> str:
    """
    Build strict deduplication key.

    Key components:
    - module + development_type + normalized_issue_text (always)
    - constraint_signature (optional)

    Note: commit_log is NOT part of the key - same pattern applied to
    different objects/paths naturally has different commit_log.

    Args:
        case: Input case to generate key for
        use_constraint_signature: Include constraint signature in key

    Returns:
        SHA1 hash of normalized key components
    """
    parts = [
        normalize_text(case.module),
        normalize_text(case.development_type),
        normalize_text(case.issue_text, normalize_numbers=True),
    ]

    if use_constraint_signature:
        parts.append(build_constraint_signature(case.rules, case.invariants))

    raw = "||".join(parts)
    return _sha1(raw)


def group_strict_duplicates(
    cases: Iterable[DedupInput],
    *,
    use_constraint_signature: bool = False,
) -> list[DedupGroup]:
    """
    Group cases by strict deduplication key.

    Only returns groups with 2+ cases (actual duplicates).
    Single cases are not included in output.

    Args:
        cases: Input cases to deduplicate
        use_constraint_signature: Include constraint signature in dedup key

    Returns:
        List of duplicate groups with canonical case selected
    """
    buckets: dict[str, list[DedupInput]] = {}

    for case in cases:
        key = build_dedup_key(case, use_constraint_signature=use_constraint_signature)
        buckets.setdefault(key, []).append(case)

    groups: list[DedupGroup] = []
    for key, bucket in buckets.items():
        if len(bucket) <= 1:
            continue
        canonical = select_canonical_duplicate(bucket)
        duplicate_ids = [c.case_id for c in bucket if c.case_id != canonical.case_id]
        groups.append(
            DedupGroup(
                dedup_key=key,
                canonical_case_id=canonical.case_id,
                duplicate_case_ids=duplicate_ids,
            )
        )

    return groups


def select_canonical_duplicate(cases: list[DedupInput]) -> DedupInput:
    """
    Select canonical case from duplicate group.

    Selection criteria (in order):
    1. Higher semantic_value (high > medium > low)
    2. Clearer issue_text (moderate length preferred, ~18 chars)
    3. Stable case_id (for deterministic results)

    Args:
        cases: List of duplicate cases

    Returns:
        Selected canonical case
    """
    def score(case: DedupInput) -> tuple[int, int, str]:
        semantic_rank = {"high": 0, "medium": 1, "low": 2}.get(case.semantic_value, 1)
        length_penalty = abs(len(case.issue_text) - 18)  # Prefer moderate length
        return (semantic_rank, length_penalty, case.case_id)

    return sorted(cases, key=score)[0]


def _sha1(text: str) -> str:
    """Generate SHA1 hash of text."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()
