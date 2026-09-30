from kb.app.retrieval.bm25_index import build_bm25_index, tokenize


def test_tokenize_lowercases_and_strips_punctuation():
    assert tokenize("Waiting Period! 24 months.") == ["waiting", "period", "24", "months"]


def test_query_ranks_matching_document_first():
    index = build_bm25_index(
        doc_ids=["a", "b", "c"],
        documents=[
            "The waiting period for pre existing disease claims is 24 months.",
            "Business loans require collateral and a minimum credit score.",
            "Claim settlement ratio for this product line was 96 percent.",
        ],
    )
    results = index.query("waiting period pre existing disease", top_k=3)
    assert results
    assert results[0][0] == "a"


def test_query_excludes_zero_score_documents():
    # 3 documents (not 2): with only 2 docs and every term split exactly
    # 1-of-2, BM25's classic IDF formula log((N-df+0.5)/(df+0.5))
    # degenerates to log(1)=0 for every term — a real edge case of tiny,
    # evenly-split corpora, not something to hit accidentally here.
    index = build_bm25_index(
        doc_ids=["a", "b", "c"],
        documents=[
            "Waiting period is 24 months.",
            "Completely unrelated content about loans.",
            "Sum assured for the gold plan is higher than silver.",
        ],
    )
    results = index.query("waiting period", top_k=3)
    assert [doc_id for doc_id, _ in results] == ["a"]


def test_empty_index_returns_no_results():
    index = build_bm25_index(doc_ids=[], documents=[])
    assert index.query("anything", top_k=3) == []
