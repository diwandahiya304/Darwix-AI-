"""Integration test for the full hybrid search stack: real embeddings
model + a real (temporary) Chroma vector store + BM25 + RRF fusion, over
a small hand-built record set. Slower than a unit test (loads the real
embedding model once, module-scoped), but retrieval quality is exactly
the thing worth testing for real rather than mocking away.

Uses overridden kb_min_relevance_score thresholds (lenient/strict) rather
than the real KB's calibrated 0.84 default, since that value was
calibrated against the actual 18-record KB corpus — a different, tiny
2-record fixture would have its own different score distribution and
testing against a borrowed threshold would be meaningless.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kb.app.models import KBRecord, KBSourceType
from kb.app.retrieval.index_builder import build_index
from kb.app.retrieval.search import build_retrieval_index, hybrid_search
from kb.app.retrieval.vector_store import get_vector_store
from kb.app.settings import Settings


def _record(record_id: str, title: str, content: str, category: str) -> KBRecord:
    return KBRecord(
        record_id=record_id,
        title=title,
        content=content,
        category=category,
        source_type=KBSourceType.WEBSITE,
        source_ref=f"raw/web/{record_id}.html",
        created_at="2025-01-01T00:00:00+00:00",
        updated_at="2025-01-01T00:00:00+00:00",
        content_hash="x",
        parent_source_id=record_id,
        chunk_index=0,
    )


@pytest.fixture(scope="module")
def tiny_index(tmp_path_factory):
    records = {
        "waiting_period": _record(
            "waiting_period",
            "FAQ",
            "The waiting period for pre-existing disease claims is 24 months from the policy start date.",
            "faq",
        ),
        "loan_terms": _record(
            "loan_terms",
            "Loan Terms",
            "Business loans require collateral and a minimum credit score of 650.",
            "policy",
        ),
    }
    settings = Settings(
        vector_store_backend="chroma",
        vector_store_path=str(tmp_path_factory.mktemp("chroma")),
    )
    vector_store = get_vector_store(settings.vector_store_backend, settings.vector_store_path_abs())
    build_index(records, vector_store, settings.embedding_model)
    return build_retrieval_index(records, vector_store), settings


def test_relevant_query_returns_correct_top_result_and_is_grounded(tiny_index):
    index, settings = tiny_index
    lenient = settings.model_copy(update={"kb_min_relevance_score": 0.5})
    response = hybrid_search(
        "what is the waiting period for pre-existing disease cover",
        index=index,
        settings=lenient,
        top_k=2,
    )
    assert response.results[0].record_id == "waiting_period"
    assert response.grounded is True
    assert response.results[0].citation == "[waiting_period | raw/web/waiting_period.html | 1.0.0]"


def test_query_ranks_the_matching_record_first_over_an_unrelated_one(tiny_index):
    index, settings = tiny_index
    lenient = settings.model_copy(update={"kb_min_relevance_score": 0.5})
    response = hybrid_search(
        "business loan collateral requirements", index=index, settings=lenient, top_k=2
    )
    assert response.results[0].record_id == "loan_terms"


def test_strict_threshold_marks_query_as_not_grounded(tiny_index):
    index, settings = tiny_index
    strict = settings.model_copy(update={"kb_min_relevance_score": 0.999})
    response = hybrid_search(
        "what is the waiting period", index=index, settings=strict, top_k=2
    )
    assert response.grounded is False


def test_category_filter_excludes_non_matching_records(tiny_index):
    index, settings = tiny_index
    lenient = settings.model_copy(update={"kb_min_relevance_score": 0.0})
    response = hybrid_search(
        "waiting period", index=index, settings=lenient, top_k=2, filters={"category": "policy"}
    )
    assert all(hit.category == "policy" for hit in response.results)
    assert all(hit.record_id != "waiting_period" for hit in response.results)


def test_language_filter_uses_the_per_language_threshold_override(tmp_path: Path):
    """Real bug this guards against: a single global threshold silently
    rejected a genuinely-grounded Tagalog KB match (measured dense score
    0.834) because it was calibrated only against English query/content
    pairs. This builds a dedicated index with one English and one
    Tagalog-tagged record and verifies the SAME strict global default
    (0.999) is bypassed only when the search is explicitly scoped to
    "fil" with a lenient override — an unfiltered or English-filtered
    search still correctly uses the strict default. See docs/DECISIONS.md.
    (Uses pytest's tmp_path, not tempfile.TemporaryDirectory — Chroma
    keeps its index file handle open past the `with` block, which trips
    Windows' stricter file-locking during eager TemporaryDirectory
    cleanup; tmp_path's deferred cleanup doesn't hit this.)
    """

    records = {
        "en_record": _record("en_record", "EN", "The waiting period is 24 months.", "faq"),
        "fil_record": _record(
            "fil_record", "FIL",
            "Ang panahon ng paghihintay bago masakop ang sakit ay 24 buwan mula "
            "sa petsa ng pagsisimula ng polisiya.",
            "faq",
        ),
    }
    records["fil_record"] = records["fil_record"].model_copy(update={"language": "fil"})

    settings = Settings(
        vector_store_backend="chroma",
        vector_store_path=str(tmp_path / "chroma"),
        kb_min_relevance_score=0.999,
        kb_min_relevance_score_fil=0.5,
    )
    vector_store = get_vector_store(settings.vector_store_backend, settings.vector_store_path_abs())
    build_index(records, vector_store, settings.embedding_model)
    index = build_retrieval_index(records, vector_store)

    # Scoped to fil + lenient fil override -> grounded despite the
    # strict 0.999 global default.
    fil_response = hybrid_search(
        "Ano ang waiting period ng polisiya",
        index=index, settings=settings, top_k=1, filters={"language": "fil"},
    )
    assert fil_response.results[0].record_id == "fil_record"
    assert fil_response.grounded is True

    # Scoped to en (still the strict 0.999 default for English) -> not
    # grounded, even for a near word-for-word matching record.
    #
    # NOTE: deliberately does NOT assert anything about an *unfiltered*
    # query's top result. Measured directly: at 2-record scale,
    # multilingual-e5-small's cross-lingual proximity is close enough
    # that an unfiltered English query can rank the Tagalog paraphrase
    # (dense 0.8214) fractionally ABOVE the near-identical English
    # record (dense 0.8191) — it does not reliably prefer same-language
    # matches on its own. This is exactly why every real caller
    # (multilingual/common/kb_client.py) always passes an explicit
    # language filter rather than relying on unfiltered ranking to sort
    # languages apart — see docs/DECISIONS.md.
    en_response = hybrid_search(
        "What is the waiting period", index=index, settings=settings, top_k=1,
        filters={"language": "en"},
    )
    assert en_response.results[0].record_id == "en_record"
    assert en_response.grounded is False
