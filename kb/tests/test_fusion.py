from kb.app.retrieval.fusion import reciprocal_rank_fusion


def test_document_ranked_first_in_both_lists_wins():
    dense = ["a", "b", "c"]
    bm25 = ["a", "c", "b"]
    scores = reciprocal_rank_fusion([dense, bm25])
    assert max(scores, key=scores.get) == "a"


def test_document_only_in_one_ranking_still_scores():
    dense = ["a", "b"]
    bm25: list[str] = []  # BM25 found nothing
    scores = reciprocal_rank_fusion([dense, bm25])
    assert scores["a"] > scores["b"] > 0


def test_agreement_across_rankings_beats_a_single_first_place():
    # "b" is #2 in both rankings; "a" is #1 in one but absent from the other.
    dense = ["a", "b"]
    bm25 = ["b", "c"]
    scores = reciprocal_rank_fusion([dense, bm25])
    assert scores["b"] > scores["a"]


def test_empty_rankings_produce_empty_scores():
    assert reciprocal_rank_fusion([[], []]) == {}
