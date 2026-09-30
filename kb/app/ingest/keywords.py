"""Keyword extraction: lightweight, dependency-free heuristic for
KBRecord.keywords — supplementary retrieval-filter/debugging metadata,
NOT part of ranking itself (that's the hybrid dense+BM25 search in
kb/app/retrieval/, which ranks on the full chunk text, not this list).

Two sources, deduplicated and capped at a small count:
1. Canonical terminology terms (kb/config/terminology.yaml) found
   verbatim in the chunk — known-important domain terms by construction.
2. A stopword-filtered word-frequency fallback, so a chunk with no
   terminology-map hits still gets some keywords.
"""

from __future__ import annotations

import re
from collections import Counter

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "this", "that", "these", "those", "and", "or", "but", "if", "then",
    "for", "to", "of", "in", "on", "at", "by", "with", "from", "as",
    "it", "its", "you", "your", "we", "our", "they", "their", "has",
    "have", "had", "will", "would", "can", "could", "should", "must",
    "not", "no", "yes", "than", "into", "up", "out", "about", "over",
    "which", "who", "what", "when", "where", "how", "will",
}  # fmt: skip

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]{3,}")
_MAX_KEYWORDS = 6


def extract_keywords(content: str, terminology_map: dict[str, str] | None = None) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()

    if terminology_map:
        # Check both the canonical term and its synonym: content may
        # already have synonyms substituted (the real pipeline runs
        # apply_terminology() before this) or may not — this function
        # shouldn't assume its caller's exact order.
        lowered = content.lower()
        for synonym, canonical in terminology_map.items():
            canonical_lower = canonical.lower()
            if canonical_lower in seen:
                continue
            if canonical_lower in lowered or synonym.lower() in lowered:
                found.append(canonical_lower)
                seen.add(canonical_lower)

    if len(found) < _MAX_KEYWORDS:
        words = [w.lower() for w in _WORD_RE.findall(content) if w.lower() not in _STOPWORDS]
        for word, _count in Counter(words).most_common():
            if word in seen:
                continue
            found.append(word)
            seen.add(word)
            if len(found) >= _MAX_KEYWORDS:
                break

    return found[:_MAX_KEYWORDS]
