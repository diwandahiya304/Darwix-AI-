from kb.app.settings import Settings


def test_min_relevance_score_for_known_languages_uses_overrides():
    settings = Settings(kb_min_relevance_score=0.84, kb_min_relevance_score_fil=0.822, kb_min_relevance_score_id=0.828)
    assert settings.min_relevance_score_for("fil") == 0.822
    assert settings.min_relevance_score_for("id") == 0.828


def test_min_relevance_score_for_english_or_unknown_uses_default():
    settings = Settings(kb_min_relevance_score=0.84)
    assert settings.min_relevance_score_for("en") == 0.84
    assert settings.min_relevance_score_for(None) == 0.84
    assert settings.min_relevance_score_for("es") == 0.84
