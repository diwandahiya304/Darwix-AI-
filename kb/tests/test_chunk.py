from kb.app.ingest.chunk import chunk_document


def test_faq_category_splits_one_chunk_per_qa_pair():
    text = (
        "Q: What is the waiting period for pre existing disease cover?\n"
        "A: The waiting period is 24 months from the policy start date.\n"
        "Q: Can I cover my spouse?\n"
        "A: Yes, spouses can be added as dependents at proposal stage.\n"
    )
    chunks = chunk_document(text, category="faq", title="FAQ Health Insurance")
    assert len(chunks) == 2
    assert "waiting period" in chunks[0].lower()
    assert "Q:" in chunks[0] and "A:" in chunks[0]
    assert "spouse" in chunks[1].lower()


def test_faq_category_falls_back_to_generic_when_no_qa_pattern():
    text = "This page has no Q/A markers at all, just a plain paragraph of text."
    chunks = chunk_document(text, category="faq", title="FAQ Health Insurance")
    assert len(chunks) == 1
    assert "plain paragraph" in chunks[0]


def test_objection_handling_splits_one_chunk_per_pair():
    text = (
        "Objection: Your premium is higher than competitors.\n"
        "Response: Our sum assured includes cashless hospitalization across "
        "10,000+ network hospitals.\n"
        "Objection: I already have coverage through my employer.\n"
        "Response: Employer cover often ends with employment; this policy "
        "continues independently.\n"
    )
    chunks = chunk_document(text, category="objection_handling", title="Objection Handling")
    assert len(chunks) == 2
    assert "Objection:" in chunks[0] and "Response:" in chunks[0]
    assert "competitors" in chunks[0]
    assert "employer" in chunks[1].lower()


def test_eligibility_qualification_splits_one_chunk_per_rule():
    text = (
        "Eligibility Rules\n"
        "- Applicant must be between 18 and 65 years old.\n"
        "- No declined claims in the last 3 years.\n"
        "- Sum assured requested must not exceed INR 5,000,000 without "
        "additional medical tests.\n"
    )
    chunks = chunk_document(text, category="eligibility_qualification", title="Eligibility Rules")
    assert len(chunks) == 3
    assert "18 and 65" in chunks[0]
    assert "declined claims" in chunks[1]
    assert "medical tests" in chunks[2]


def test_generic_category_splits_by_heading_then_wordcount():
    text = (
        "## Silver Plan\n"
        + " ".join(f"Silver plan detail sentence number {i}." for i in range(1, 30))
        + "\n## Gold Plan\n"
        + " ".join(f"Gold plan detail sentence number {i}." for i in range(1, 30))
    )
    chunks = chunk_document(text, category="product", title="Health Insurance Plans")
    assert len(chunks) >= 2
    assert any("Silver Plan" in c and "Silver plan detail" in c for c in chunks)
    assert any("Gold Plan" in c and "Gold plan detail" in c for c in chunks)
    for chunk in chunks:
        # self-contained: every chunk carries the document title
        assert "Health Insurance Plans" in chunk


def test_chunks_never_split_mid_sentence():
    text = " ".join(f"This is sentence number {i} in a long paragraph." for i in range(1, 30))
    chunks = chunk_document(text, category="product", title="Process Overview")
    for chunk in chunks:
        assert chunk.strip().endswith(".")


def test_short_content_becomes_a_single_self_contained_chunk():
    text = "This is a short, self-contained answer about the waiting period."
    chunks = chunk_document(text, category="policy", title="Policy Terms")
    assert len(chunks) == 1
    assert chunks[0] == f"Policy Terms: {text}"
