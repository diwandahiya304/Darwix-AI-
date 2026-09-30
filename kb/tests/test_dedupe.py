from kb.app.ingest.dedupe import content_hash, dedupe_documents


class _Doc:
    def __init__(self, doc_id: str, text: str):
        self.id = doc_id
        self.text = text


def test_content_hash_ignores_whitespace_and_case():
    assert content_hash("Hello   World") == content_hash("hello world")


def test_content_hash_differs_for_different_content():
    assert content_hash("Hello World") != content_hash("Goodbye World")


def test_exact_duplicates_are_removed():
    docs = [_Doc("a", "Same content here."), _Doc("b", "Same content here.")]
    result = dedupe_documents(docs, get_id=lambda d: d.id, get_text=lambda d: d.text)
    assert len(result.kept) == 1
    assert result.exact_duplicates_removed == 1


def test_near_duplicates_are_merged_keeping_longest():
    short = _Doc(
        "short",
        "Operational, marketing, and technology support is provided to "
        "branch partners. Branch partners receive a dedicated relationship "
        "manager and quarterly performance reviews.",
    )
    long_ = _Doc(
        "long",
        "Operational, marketing, and technology support is provided to "
        "branch partners. Branch partners receive a dedicated relationship "
        "manager and quarterly performance reviews. They also get priority "
        "access to the partnership desk for escalations.",
    )
    result = dedupe_documents([short, long_], get_id=lambda d: d.id, get_text=lambda d: d.text)
    assert len(result.kept) == 1
    assert result.kept[0].id == "long"
    assert result.near_duplicates_removed == 1
    assert result.merged_source_ids["long"] == ["short"]


def test_distinct_documents_are_both_kept():
    docs = [
        _Doc("a", "Health insurance covers hospitalization expenses for the insured."),
        _Doc("b", "Business loans require collateral and a minimum credit score."),
    ]
    result = dedupe_documents(docs, get_id=lambda d: d.id, get_text=lambda d: d.text)
    assert len(result.kept) == 2
    assert result.near_duplicates_removed == 0
