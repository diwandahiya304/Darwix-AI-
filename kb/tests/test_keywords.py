from kb.app.ingest.keywords import extract_keywords


def test_terminology_terms_are_preferred_when_present():
    terminology_map = {"cover amount": "sum assured", "sum insured": "sum assured"}
    content = "The cover amount for this plan is generous and well explained."
    keywords = extract_keywords(content, terminology_map)
    assert "sum assured" in keywords


def test_falls_back_to_word_frequency_when_no_terminology_hit():
    content = "Hospitals process claims quickly when documents are complete and claims are accurate."
    keywords = extract_keywords(content, terminology_map={})
    assert keywords
    assert "claims" in keywords


def test_stopwords_are_excluded():
    content = "This is the plan that we have for you and your family."
    keywords = extract_keywords(content)
    assert "this" not in keywords
    assert "that" not in keywords
    assert "your" not in keywords


def test_keyword_count_is_capped():
    content = " ".join(f"uniqueword{i}" for i in range(20))
    keywords = extract_keywords(content)
    assert len(keywords) <= 6
