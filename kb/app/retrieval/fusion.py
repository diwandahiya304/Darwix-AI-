"""Reciprocal Rank Fusion (RRF): combines multiple ranked-id lists
(dense vector search, BM25) into one fused ranking without needing their
scores to be on comparable scales — RRF only looks at rank position.

score(doc) = sum over each ranking r of 1 / (k + rank_r(doc))

k=60 is the constant from Cormack, Clarke & Buettcher (2009), "Reciprocal
Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods" —
the standard default used across IR literature, not a value tuned for
this corpus. A document absent from a given ranking simply contributes
nothing from that ranking (not a penalty, not a zero-rank bonus).
"""

from __future__ import annotations

DEFAULT_RRF_K = 60


def reciprocal_rank_fusion(
    rankings: list[list[str]], k: int = DEFAULT_RRF_K
) -> dict[str, float]:
    """`rankings`: one ordered-best-first list of doc ids per ranking
    method. Returns {doc_id: fused_score} for every doc id that appeared
    in at least one ranking — sort by score descending for the final
    order."""

    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores
