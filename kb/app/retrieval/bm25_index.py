"""BM25 lexical search over the active KB record set.

Rebuilds a rank_bm25.BM25Okapi index at query time over the (possibly
metadata-filtered) candidate subset rather than maintaining one
persistent index — deliberately simple, appropriate at this corpus's
scale (a few dozen records for a 48-hour assessment): rebuild cost is
sub-millisecond here. Revisit if the corpus grows into the range where
that stops being true (CLAUDE.md §3 — no unnecessary complexity before
it's needed).
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


class BM25Index:
    def __init__(self, doc_ids: list[str], documents: list[str]):
        self.doc_ids = doc_ids
        self._bm25 = BM25Okapi([tokenize(d) for d in documents]) if documents else None

    def query(self, query_text: str, top_k: int) -> list[tuple[str, float]]:
        """Returns [(doc_id, bm25_score), ...] sorted best-first, length
        <= top_k. Scores are unbounded BM25 scores, not comparable across
        different candidate subsets — only used for within-query ranking
        and as an RRF input."""

        if self._bm25 is None or not self.doc_ids:
            return []
        scores = self._bm25.get_scores(tokenize(query_text))
        ranked = sorted(zip(self.doc_ids, scores), key=lambda pair: pair[1], reverse=True)
        return [(doc_id, score) for doc_id, score in ranked[:top_k] if score > 0]


def build_bm25_index(doc_ids: list[str], documents: list[str]) -> BM25Index:
    return BM25Index(doc_ids, documents)
