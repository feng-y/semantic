"""Text normalization utilities.

Provides lightweight normalization for:
- Whitespace and punctuation
- ASCII lowercasing
- Conservative synonym mapping
- Optional numeric placeholder
"""

from __future__ import annotations

import re
import unicodedata

_WS_RE = re.compile(r"\s+")
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

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
    Normalize text for deduplication and comparison.

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

    s = unicodedata.normalize("NFKC", text)
    s = _normalize_punctuation(s)
    s = _WS_RE.sub(" ", s)

    if lowercase_ascii:
        s = _lower_ascii_only(s)

    if synonym_normalize:
        for src, dst in _SYNONYM_MAP.items():
            s = s.replace(src, dst)

    if normalize_numbers:
        s = _NUM_RE.sub("<NUM>", s)

    return s.strip()


def _lower_ascii_only(text: str) -> str:
    """Convert only ASCII letters to lowercase, preserve other characters."""
    return text.translate(str.maketrans(
        {i: chr(i + 32) for i in range(65, 91)}
    ))


def _normalize_punctuation(text: str) -> str:
    """Normalize Chinese punctuation to ASCII equivalents."""
    return (
        text.replace("，", ",")
        .replace("。", ".")
        .replace("：", ":")
        .replace("；", ";")
        .replace("（", "(")
        .replace("）", ")")
    )
