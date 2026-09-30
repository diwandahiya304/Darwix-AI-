"""Deduplication.

Exact duplicates: sha256 hash of whitespace/case-normalized content.

Near-duplicates: exact Jaccard similarity over 5-word shingle sets,
compared pairwise (O(n^2)). We deliberately do NOT use MinHash/LSH
approximation here: `datasketch` eagerly imports `scipy` at package-import
time, and scipy's numpy floor (>=2.0) directly conflicts with the numpy
ceiling spaCy/thinc require (<2.0) for the PII stack in this same venv
(see docs/DECISIONS.md for the exact conflict). A KB built in a 48-hour
assessment has, at most, a few hundred source documents — exact pairwise
Jaccard is fast enough at that scale and removes an entire dependency
(and its transitive numpy/scipy conflict) for no accuracy loss. Revisit
with real MinHash/LSH only if the corpus grows into the
thousands-of-documents range where O(n^2) stops being cheap.

NEAR_DUP_THRESHOLD is 0.5, not the assignment brief's ">0.92" — that
figure is calibrated for embedding cosine similarity, a metric with very
different dynamics from shingle-level Jaccard. Jaccard is length-
sensitive: a document that is another one plus a couple of extra sentences
tops out well under 0.92 even when every shared sentence is byte-identical,
because each added/changed word invalidates up to k=5 overlapping
shingles and the union grows with the longer document. A 0.92 Jaccard
threshold would only ever catch near-byte-identical documents; 0.5 was
calibrated against this module's own test fixtures
(kb/tests/test_dedupe.py) to catch real paraphrase-level near-duplicates
while leaving unrelated documents (Jaccard near 0) a wide safety margin.
See docs/DECISIONS.md.

When two documents are judged near-duplicates, the longer (more complete)
one is kept and the shorter one's id is recorded under
`merged_source_ids[kept_id]` so the merge is traceable.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Callable, TypeVar

NEAR_DUP_THRESHOLD = 0.5
_SHINGLE_SIZE = 5

T = TypeVar("T")


def content_hash(text: str) -> str:
    normalized = " ".join(text.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _shingles(text: str, k: int = _SHINGLE_SIZE) -> set[str]:
    tokens = text.lower().split()
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class DedupeResult:
    kept: list
    exact_duplicates_removed: int = 0
    near_duplicates_removed: int = 0
    merged_source_ids: dict[str, list[str]] = field(default_factory=dict)


def dedupe_documents(
    documents: list[T],
    get_id: Callable[[T], str],
    get_text: Callable[[T], str],
) -> DedupeResult:
    """documents: arbitrary objects; get_id/get_text extract what's needed
    without this module knowing the concrete document type."""

    seen_hashes: set[str] = set()
    exact_removed = 0
    unique_docs: list[T] = []
    for doc in documents:
        h = content_hash(get_text(doc))
        if h in seen_hashes:
            exact_removed += 1
            continue
        seen_hashes.add(h)
        unique_docs.append(doc)

    kept: list[T] = []
    kept_shingles: dict[str, set[str]] = {}
    merged: dict[str, list[str]] = {}
    near_removed = 0

    # Longest-first so the kept representative is the most complete version.
    for doc in sorted(unique_docs, key=lambda d: len(get_text(d)), reverse=True):
        doc_id = get_id(doc)
        shingles = _shingles(get_text(doc))
        if not shingles:
            kept.append(doc)
            continue

        match_id = next(
            (
                kid
                for kid, kshingles in kept_shingles.items()
                if jaccard_similarity(shingles, kshingles) >= NEAR_DUP_THRESHOLD
            ),
            None,
        )
        if match_id is not None:
            merged.setdefault(match_id, []).append(doc_id)
            near_removed += 1
            continue

        kept_shingles[doc_id] = shingles
        kept.append(doc)

    return DedupeResult(
        kept=kept,
        exact_duplicates_removed=exact_removed,
        near_duplicates_removed=near_removed,
        merged_source_ids=merged,
    )
