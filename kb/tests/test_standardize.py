from kb.app.ingest.standardize import (
    apply_terminology,
    canonicalize_category,
    infer_source_type,
    standardize_currency,
    standardize_dates,
    to_snake_case,
    to_title_case,
)
from kb.app.models import ExtractionFormat, KBSourceType


def test_standardize_dates_handles_multiple_formats():
    text = "Policy started on 01/04/2023 and renewed on 15 March 2024."
    result = standardize_dates(text)
    assert "2023-04-01" in result
    assert "2024-03-15" in result


def test_standardize_dates_leaves_unparsable_fragments_untouched():
    text = "Reference code 99/99/9999 is not a date."
    result = standardize_dates(text)
    assert "99/99/9999" in result


def test_standardize_currency_normalizes_indian_amounts():
    text = "Sum assured is Rs. 5,00,000 and premium is INR 8500."
    result = standardize_currency(text)
    assert "INR 500,000" in result
    assert "INR 8,500" in result


def test_to_snake_case_converts_labels():
    assert to_snake_case("Applicant Name") == "applicant_name"
    assert to_snake_case("PAN Number") == "pan_number"
    assert to_snake_case("sumAssured") == "sum_assured"


def test_to_title_case_basic():
    assert to_title_case("branch partnership benefits") == "Branch Partnership Benefits"


def test_apply_terminology_canonicalizes_synonyms():
    mapping = {"cover amount": "sum assured", "sum insured": "sum assured"}
    text = "The cover amount is high and the Sum Insured is also high."
    result = apply_terminology(text, mapping)
    assert "sum assured" in result.lower()
    assert "cover amount" not in result.lower()


def test_apply_terminology_preserves_sentence_initial_capitalization():
    mapping = {"sum insured": "sum assured"}
    text = "Sum Insured requested above a threshold needs extra checks."
    result = apply_terminology(text, mapping)
    assert result.startswith("Sum assured")


def test_canonicalize_category_maps_known_and_unknown():
    taxonomy = ["faq", "policy_terms", "product"]
    assert canonicalize_category("FAQ", taxonomy) == "faq"
    assert canonicalize_category("something_random", taxonomy) == "uncategorized"


def test_canonicalize_category_matches_compound_categories_by_shared_token():
    # "eligibility_form" shares no substring with "eligibility_qualification"
    # in either direction, but does share the "eligibility" token.
    taxonomy = ["eligibility_qualification", "policy", "product", "uncategorized"]
    assert canonicalize_category("eligibility_form", taxonomy) == "eligibility_qualification"
    assert canonicalize_category("policy_terms", taxonomy) == "policy"


def test_infer_source_type_prefers_category_for_faq_and_policy():
    assert (
        infer_source_type("raw/web/faq_health_insurance.html", ExtractionFormat.HTML, "faq")
        == KBSourceType.FAQ
    )
    assert (
        infer_source_type("raw/pdfs/policy_terms.pdf", ExtractionFormat.PDF, "policy")
        == KBSourceType.POLICY
    )


def test_infer_source_type_detects_form_from_pdf_filename():
    assert (
        infer_source_type(
            "raw/pdfs/eligibility_form.pdf", ExtractionFormat.PDF, "eligibility_qualification"
        )
        == KBSourceType.FORM
    )


def test_infer_source_type_falls_back_to_extraction_format():
    assert (
        infer_source_type("raw/pdfs/coverage_table.pdf", ExtractionFormat.PDF, "product")
        == KBSourceType.PDF
    )
    assert (
        infer_source_type("raw/web/partnership.html", ExtractionFormat.HTML, "product")
        == KBSourceType.WEBSITE
    )
