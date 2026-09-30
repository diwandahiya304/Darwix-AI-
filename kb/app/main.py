"""KB retrieval API — FastAPI service.

Endpoints:
  POST /search       {query, top_k?, filters?} -> SearchResponse
  GET  /record/{id}  -> KBRecord or 404
  GET  /health        -> basic liveness + how many active records are indexed

Run: `make run-kb` (uvicorn kb.app.main:app --port $KB_PORT).

The retrieval index (vector store + BM25 + loaded records) is built once
at startup, not per-request — see kb.app.retrieval.search.RetrievalIndex.
If the vector store is empty at startup (first run, or after deleting
data/processed/kb_index/), it's built automatically from
data/processed/kb_records.jsonl so `make run-kb` works right after
`make ingest-kb` without a separate manual indexing step.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from kb.app.models import KBRecord
from kb.app.retrieval.index_builder import build_index, load_active_records
from kb.app.retrieval.search import RetrievalIndex, SearchResponse, build_retrieval_index, hybrid_search
from kb.app.retrieval.vector_store import get_vector_store
from kb.app.settings import REPO_ROOT, get_settings

logger = logging.getLogger("kb.api")

_KB_RECORDS_PATH = REPO_ROOT / "data" / "processed" / "kb_records.jsonl"

_state: dict[str, RetrievalIndex] = {}


class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None
    filters: dict[str, str] | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    records = load_active_records(_KB_RECORDS_PATH)
    vector_store = get_vector_store(settings.vector_store_backend, settings.vector_store_path_abs())
    if vector_store.count() == 0 and records:
        logger.info("Vector store empty — building index from %d active records", len(records))
        build_index(records, vector_store, settings.embedding_model)
    _state["index"] = build_retrieval_index(records, vector_store)
    logger.info("kb API ready: %d active records indexed", len(records))
    yield
    _state.clear()


app = FastAPI(title="KB Retrieval API", lifespan=lifespan)


def _get_index() -> RetrievalIndex:
    index = _state.get("index")
    if index is None:
        raise HTTPException(status_code=503, detail="Retrieval index not ready yet")
    return index


@app.post("/search", response_model=SearchResponse)
def search(request: SearchRequest) -> SearchResponse:
    settings = get_settings()
    start = time.perf_counter()
    response = hybrid_search(
        request.query,
        index=_get_index(),
        settings=settings,
        top_k=request.top_k,
        filters=request.filters,
    )
    logger.info(
        "search query=%r top_k=%s grounded=%s latency_ms=%.1f",
        request.query,
        request.top_k or settings.kb_top_k,
        response.grounded,
        (time.perf_counter() - start) * 1000,
    )
    return response


@app.get("/record/{record_id}", response_model=KBRecord)
def get_record(record_id: str) -> KBRecord:
    index = _get_index()
    record = index.records.get(record_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No active record with id {record_id!r}")
    return record


@app.get("/health")
def health() -> dict:
    index = _state.get("index")
    return {
        "status": "ok" if index is not None else "starting",
        "records_indexed": len(index.records) if index is not None else 0,
    }
