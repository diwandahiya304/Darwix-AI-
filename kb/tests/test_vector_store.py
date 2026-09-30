"""Vector store contract tests — fake 3-dim embeddings, no model load, so
these stay fast. Covers both backends since VECTOR_STORE_BACKEND is meant
to be swappable; skips Qdrant gracefully if its local mode ever isn't
available in a given environment rather than failing the whole suite."""

from __future__ import annotations

import pytest

from kb.app.retrieval.vector_store import get_vector_store

_BACKENDS = ["chroma", "qdrant"]


@pytest.fixture(params=_BACKENDS)
def store(request, tmp_path):
    backend = request.param
    path = tmp_path / backend
    try:
        # vector_size=3 to match this test file's fake embeddings — Qdrant
        # validates dimensionality strictly at collection-create time.
        vector_store = get_vector_store(backend, path, vector_size=3)
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"{backend} unavailable in this environment: {exc}")
    return vector_store


def test_empty_store_has_zero_count_and_returns_no_hits(store):
    assert store.count() == 0
    assert store.query([0.1, 0.2, 0.3], top_k=5) == []


def test_upsert_and_query_returns_closest_match_first(store):
    store.upsert(
        ids=["a", "b"],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        metadatas=[{"category": "faq"}, {"category": "policy"}],
        documents=["doc a", "doc b"],
    )
    assert store.count() == 2
    hits = store.query([1.0, 0.0, 0.0], top_k=2)
    assert hits[0].id == "a"
    assert hits[0].document == "doc a"
    assert hits[0].metadata["category"] == "faq"


def test_where_filter_restricts_results_to_matching_metadata(store):
    store.upsert(
        ids=["a", "b"],
        embeddings=[[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]],
        metadatas=[{"category": "faq"}, {"category": "policy"}],
        documents=["doc a", "doc b"],
    )
    hits = store.query([1.0, 0.0, 0.0], top_k=2, where={"category": "policy"})
    assert [h.id for h in hits] == ["b"]


def test_reset_clears_all_vectors(store):
    store.upsert(
        ids=["a"], embeddings=[[1.0, 0.0, 0.0]], metadatas=[{"category": "faq"}], documents=["doc a"]
    )
    assert store.count() == 1
    store.reset()
    assert store.count() == 0
