"""Hybrid retrieval: dense vector search (cosine similarity) + BM25
lexical search, merged via Reciprocal Rank Fusion (fusion.py).

Grounding decision (whether the caller should treat this as "no grounded
answer available") is based on the top result's RAW dense cosine
similarity, not the fused RRF score — RRF scores aren't on an
interpretable 0..1 scale (they're small numbers whose magnitude depends
on k and how many rankers contributed to them), so comparing one against
a human-configured threshold would be meaningless. RRF decides ranking
*order*; dense cosine similarity decides the grounding *cutoff*. See
docs/DECISIONS.md for how KB_MIN_RELEVANCE_SCORE was calibrated.
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from kb.app.models import KBRecord
from kb.app.retrieval.bm25_index import BM25Index, build_bm25_index
from kb.app.retrieval.embeddings import embed_query
from kb.app.retrieval.fusion import reciprocal_rank_fusion
from kb.app.retrieval.vector_store import VectorStore
from kb.app.settings import Settings


class SearchHit(BaseModel):
    record_id: str
    title: str
    content: str
    category: str
    source_ref: str
    version: str
    dense_score: float
    bm25_score: float
    fused_score: float
    citation: str

    @classmethod
    def build(
        cls, record: KBRecord, dense_score: float, bm25_score: float, fused_score: float
    ) -> "SearchHit":
        return cls(
            record_id=record.record_id,
            title=record.title,
            content=record.content,
            category=record.category,
            source_ref=record.source_ref,
            version=record.version,
            dense_score=dense_score,
            bm25_score=bm25_score,
            fused_score=fused_score,
            citation=f"[{record.record_id} | {record.source_ref} | {record.version}]",
        )


class SearchResponse(BaseModel):
    query: str
    grounded: bool
    results: list[SearchHit]
    latency_ms: float


class RetrievalIndex:
    """Holds the loaded records + vector store + BM25 index for one
    process's lifetime. Rebuilding this per-request would reload the
    embedding model and re-embed every record on every single search —
    built once at API/CLI startup instead (see main.py, cli.py)."""

    def __init__(self, records: dict[str, KBRecord], vector_store: VectorStore, bm25: BM25Index):
        self.records = records  # record_id -> KBRecord
        self.vector_store = vector_store
        self.bm25 = bm25


def build_retrieval_index(
    records: dict[str, KBRecord], vector_store: VectorStore
) -> RetrievalIndex:
    bm25 = build_bm25_index(
        doc_ids=list(records.keys()), documents=[r.content for r in records.values()]
    )
    return RetrievalIndex(records=records, vector_store=vector_store, bm25=bm25)


def _record_matches_filters(record: KBRecord, filters: dict) -> bool:
    for key, expected in filters.items():
        actual = getattr(record, key, None)
        actual = actual.value if hasattr(actual, "value") else actual
        if actual != expected:
            return False
    return True


def hybrid_search(
    query: str,
    index: RetrievalIndex,
    settings: Settings,
    top_k: int | None = None,
    filters: dict | None = None,
) -> SearchResponse:
    start = time.perf_counter()
    top_k = top_k or settings.kb_top_k
    overfetch = max(top_k * 4, 10)

    query_embedding = embed_query(query, settings.embedding_model)
    dense_hits = index.vector_store.query(query_embedding, top_k=overfetch, where=filters)
    dense_by_id = {h.id: h.score for h in dense_hits}
    dense_ranking = [h.id for h in dense_hits]

    if filters:
        candidates = {
            rid: r for rid, r in index.records.items() if _record_matches_filters(r, filters)
        }
        bm25_hits = build_bm25_index(
            doc_ids=list(candidates.keys()), documents=[r.content for r in candidates.values()]
        ).query(query, top_k=overfetch)
    else:
        bm25_hits = index.bm25.query(query, top_k=overfetch)
    bm25_by_id = dict(bm25_hits)
    bm25_ranking = [doc_id for doc_id, _ in bm25_hits]

    fused_scores = reciprocal_rank_fusion([dense_ranking, bm25_ranking])
    ordered_ids = sorted(fused_scores, key=lambda doc_id: fused_scores[doc_id], reverse=True)

    results = [
        SearchHit.build(
            record=index.records[doc_id],
            dense_score=dense_by_id.get(doc_id, 0.0),
            bm25_score=bm25_by_id.get(doc_id, 0.0),
            fused_score=fused_scores[doc_id],
        )
        for doc_id in ordered_ids
        if doc_id in index.records
    ][:top_k]

    if results:
        # Prefer the explicit language filter the caller scoped this
        # search to (multilingual/'s bots always pass one); fall back to
        # the top result's own record language for an unfiltered search
        # spanning multiple markets. Per-language thresholds exist
        # because a single global one silently rejected genuinely-
        # grounded non-English matches — see docs/DECISIONS.md.
        language_for_threshold = (filters or {}).get("language")
        if language_for_threshold is None:
            language_for_threshold = index.records[results[0].record_id].language
        grounded = results[0].dense_score >= settings.min_relevance_score_for(language_for_threshold)
    else:
        grounded = False
    latency_ms = (time.perf_counter() - start) * 1000

    return SearchResponse(query=query, grounded=grounded, results=results, latency_ms=latency_ms)
