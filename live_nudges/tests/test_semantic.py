from live_nudges.app.semantic import embed_for_dedup


def test_embed_for_dedup_returns_a_vector_for_normal_text():
    vector = embed_for_dedup("I am frustrated with these calls")
    assert vector is not None
    assert len(vector) > 0


def test_embed_for_dedup_returns_none_for_empty_text():
    assert embed_for_dedup("") is None
    assert embed_for_dedup("   ") is None


def test_similar_sentences_have_higher_cosine_similarity_than_dissimilar_ones():
    a = embed_for_dedup("I already told you I'm not interested, this is ridiculous")
    b = embed_for_dedup("How many times do I have to say this, I am sick of these calls")
    c = embed_for_dedup("Your premium this year is fourteen thousand five hundred rupees")

    sim_ab = sum(x * y for x, y in zip(a, b))
    sim_ac = sum(x * y for x, y in zip(a, c))
    assert sim_ab > sim_ac
