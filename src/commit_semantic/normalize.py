"""
Text normalization utilities for deduplication and pattern extraction.

Provides lightweight normalization for:
- Whitespace and punctuation
- ASCII lowercasing
- Conservative synonym mapping
- Optional number placeholder
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_WS_RE = re.compile(r"\s+")
_NUM_RE = re.compile(r"\b\d+(\.\d+)?\b")

# Conservative synonym mapping - don't do too much
_SYNONYM_MAP = {
    "修正": "修复",
    "调整": "优化",
    "接入": "新增",
    "引入": "新增",
}


def normalize_text(
    text: str,
    *,
    lowercase_ascii: bool = True,
    normalize_numbers: bool = False,
    synonym_normalize: bool = True,
) -> str:
    """
    Lightweight normalization for short text, used by dedup/patterning.

    Args:
        text: Input text to normalize
        lowercase_ascii: Convert ASCII letters to lowercase
        normalize_numbers: Replace numbers with <NUM> placeholder
        synonym_normalize: Apply conservative synonym mapping

    Returns:
        Normalized text
    """
    if not text:
        return ""

    s = unicodedata.normalize("NFKC", text).strip()
    s = _WS_RE.sub(" ", s)

    if lowercase_ascii:
        s = _lower_ascii_only(s)

    s = _normalize_punctuation(s)

    if synonym_normalize:
        for src, dst in _SYNONYM_MAP.items():
            s = s.replace(src, dst)

    if normalize_numbers:
        s = _NUM_RE.sub("<NUM>", s)

    return s.strip()


def normalize_phrase_set(items: Iterable[str]) -> tuple[str, ...]:
    """
    Normalize rules/invariants and sort to form stable signature.

    Args:
        items: Collection of phrases (rules or invariants)

    Returns:
        Sorted tuple of normalized phrases
    """
    normalized = [normalize_text(x, normalize_numbers=True) for x in items if x]
    normalized = sorted(set(x for x in normalized if x))
    return tuple(normalized)


def build_constraint_signature(rules: list[str], invariants: list[str]) -> str:
    """
    Compress rules + invariants into lightweight signature.

    Args:
        rules: List of rule strings
        invariants: List of invariant strings

    Returns:
        Signature string with normalized and sorted constraints
    """
    parts = list(normalize_phrase_set(rules)) + list(normalize_phrase_set(invariants))
    return " | ".join(parts)


def _lower_ascii_only(text: str) -> str:
    """Convert only ASCII letters to lowercase, preserve other characters."""
    chars: list[str] = []
    for ch in text:
        if "A" <= ch <= "Z":
            chars.append(ch.lower())
        else:
            chars.append(ch)
    return "".join(chars)


def _normalize_punctuation(text: str) -> str:
    """
    Conservative punctuation normalization.
    Avoid over-processing Chinese sentences.
    """
    return (
        text.replace("，", ", ")
        .replace("。", ". ")
        .replace("：", ": ")
        .replace("；", "; ")
        .replace("（", "(")
        .replace("）", ")")
    )
