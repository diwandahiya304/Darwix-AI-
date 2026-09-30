"""Real model integration test (not mocked) — slower than the rest of the
suite, but the whole point of choosing an embedding model is that it
actually separates relevant from irrelevant text, which a mock can't
verify. Runs fully offline once the model is cached locally
(HF_HUB_OFFLINE=1, set by kb.app.retrieval.embeddings on import)."""

from kb.app.retrieval.embeddings import embed_passages, embed_query

_MODEL = "intfloat/multilingual-e5-small"


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def test_query_scores_higher_against_relevant_passage_than_irrelevant():
    query = embed_query("what is the waiting period for pre-existing disease cover", _MODEL)
    relevant, irrelevant = embed_passages(
        [
            "The waiting period for pre existing disease claims is 24 months from the policy start date.",
            "Business loans require collateral and a minimum credit score.",
        ],
        _MODEL,
    )
    assert _dot(query, relevant) > _dot(query, irrelevant)


def test_embeddings_are_l2_normalized():
    (vec,) = embed_passages(["Sample passage text."], _MODEL)
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-4
