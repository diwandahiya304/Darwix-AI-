from kb.app.ingest.pii import mask_pii


def test_email_is_masked():
    result = mask_pii("Contact ramesh.kumar@example.com for details.")
    assert "[EMAIL]" in result.masked_text
    assert "ramesh.kumar@example.com" not in result.masked_text
    assert "EMAIL" in result.pii_types


def test_india_phone_is_masked():
    result = mask_pii("Call +91 9876543210 for support.")
    assert "9876543210" not in result.masked_text
    assert "PHONE" in result.pii_types


def test_pan_is_masked():
    result = mask_pii("PAN Number: ABCDE1234F")
    assert "ABCDE1234F" not in result.masked_text
    assert "PAN" in result.pii_types


def test_aadhaar_is_masked():
    result = mask_pii("Aadhaar Number: 1234 5678 9012")
    assert "1234 5678 9012" not in result.masked_text
    assert "AADHAAR" in result.pii_types


def test_text_without_pii_is_unchanged():
    text = "This document has no personal information at all."
    result = mask_pii(text)
    assert result.pii_types == []
    assert result.masked_text == text


def test_non_english_text_skips_ner_and_only_masks_email():
    """Regression test: en_core_web_sm's English-trained NER produces
    severe false positives on Tagalog/Indonesian text (verified directly
    against real KB seed content — see docs/DECISIONS.md). Non-English
    content must skip NER-based PERSON detection entirely."""
    text = (
        "Petugas penagihan dilarang mengancam, mempermalukan, atau "
        "menggunakan kata-kata kasar kepada nasabah. Hubungi kami di "
        "cs@example.com untuk info lebih lanjut."
    )
    result = mask_pii(text, language="id")
    assert "PERSON" not in result.pii_types
    assert "dilarang" in result.masked_text  # real words preserved, not mangled
    assert "mempermalukan" in result.masked_text
    assert "[EMAIL]" in result.masked_text
    assert "cs@example.com" not in result.masked_text


def test_pan_is_not_misclassified_as_person_when_adjacent_to_a_name():
    """Regression test: spaCy's small-model NER sometimes tags "PAN
    ABCDE1234F" as a single PERSON span, which used to make
    presidio_anonymizer's longest-span-wins conflict resolution swallow our
    exact PAN regex match. The value must still end up masked either way,
    but it must be attributed to PAN, not PERSON."""
    result = mask_pii("Priya Sharma, PAN ABCDE1234F, reachable at priya.sharma@example.com.")
    assert "ABCDE1234F" not in result.masked_text
    assert "PAN" in result.pii_types
    assert "[PAN]" in result.masked_text


def test_single_capitalized_product_word_is_not_masked_as_person():
    """Regression test: en_core_web_sm sometimes tags a single capitalized
    plan/product word (e.g. a pricing table's "Silver" tier) as PERSON.
    Every real PERSON in this KB's content is a two-word name, so a
    single-token PERSON match should be treated as a false positive and
    left alone."""
    result = mask_pii("Silver INR 500,000 INR 8,500")
    assert "Silver" in result.masked_text
    assert "PERSON" not in result.pii_types


def test_no_raw_pii_values_leak_into_counts_only_report():
    """The PII report only ever sees counts, never raw text — this test
    exists to make explicit that PIIMaskResult.counts is type->int only."""
    result = mask_pii("Email: a@b.com, Email: c@d.com")
    assert result.counts == {"EMAIL": 2}
