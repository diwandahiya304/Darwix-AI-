"""Generates a small, clearly-labeled SYNTHETIC messy dataset into
data/raw/ so the ingestion pipeline has something realistic to run
against out of the box, without requiring real business documents.

Everything here is fabricated: names, phone numbers, PAN/Aadhaar numbers,
and emails are invented specifically to exercise the PII-masking step —
none of it is real customer data. Filenames are chosen so
kb.app.ingest.standardize.canonicalize_category() lands each source in a
distinct taxonomy category (kb/config/taxonomy.yaml), so every
category-aware chunker in kb/app/ingest/chunk.py gets exercised: FAQ
(faq_health_insurance.html), objection handling
(objection_handling_health_insurance.html), eligibility rules
(eligibility_qualification_rules.html and eligibility_form.pdf), the
generic heading-aware chunker (product_partnership_benefits.html,
process_claim_filing.html), and a compliance/disclosure page. It also
includes: navigation/footer/cookie-banner boilerplate (extraction
cleanup), a near-duplicate HTML page (dedupe), inconsistent terminology
and date/currency formats, a PDF with a table, and a second PDF page with
no extractable text (extraction-failure path).

Run standalone: `python -m kb.app.ingest.synthetic_data`.
"""

from __future__ import annotations

import sys
from pathlib import Path

from fpdf import FPDF

_SYNTHETIC_NOTICE = (
    "<!-- SYNTHETIC TEST DATA -- fabricated for the KB ingestion pipeline. "
    "No real customer information. -->"
)

_PRODUCT_HTML = f"""<!DOCTYPE html>
<html><head><title>Branch Partnership Benefits</title></head>
<body>
{_SYNTHETIC_NOTICE}
<nav>Home | Products | Policies | Contact</nav>
<header>Site Header -- Acme Insurance</header>
<div class="cookie-banner">We use cookies. Accept all cookies.</div>
<main>
<h1>Branch Partnership Benefits</h1>
<p>Operational, marketing, and technology support is provided to branch
partners. Branch partners receive a dedicated relationship manager and
quarterly performance reviews.</p>
<p>The sum assured for group health products offered through branch
partners starts at Rs. 5,00,000 and can go up to Rs. 50,00,000 depending on
the qualification rules effective from 01/04/2023.</p>
<p>For support, contact our partnership desk. Sample contact on file:
Ramesh Kumar, ramesh.kumar@example.com, +91 9876543210.</p>
</main>
<footer>(c) 2024 Acme Insurance. All rights reserved. Follow us on social
media.</footer>
</body></html>
"""

# Near-duplicate of the page above: same core paragraphs, one synonym
# swapped ("sum assured" -> "cover amount") and the contact paragraph
# dropped -- close enough that near-dup detection should merge it, not
# different enough to look like distinct content.
_PRODUCT_DUP_HTML = f"""<!DOCTYPE html>
<html><head><title>Partner Benefits -- Branch Network</title></head>
<body>
{_SYNTHETIC_NOTICE}
<nav>Home | Products | Policies | Contact</nav>
<main>
<h1>Branch Partnership Benefits</h1>
<p>Operational, marketing, and technology support is provided to branch
partners. Branch partners receive a dedicated relationship manager and
quarterly performance reviews.</p>
<p>The cover amount for group health products offered through branch
partners starts at Rs. 5,00,000 and can go up to Rs. 50,00,000 depending on
the qualification rules effective from 01/04/2023.</p>
</main>
<footer>(c) 2024 Acme Insurance. All rights reserved.</footer>
</body></html>
"""

_FAQ_HTML = f"""<!DOCTYPE html>
<html><head><title>Health Insurance FAQ</title></head>
<body>
{_SYNTHETIC_NOTICE}
<header>Site Header -- Acme Insurance</header>
<main>
<h1>FAQ Health Insurance</h1>
<p>Q: What is the waiting period for pre-existing disease cover?</p>
<p>A: The cooling period for pre existing condition claims is 24 months
from the policy start date of 01/04/2023.</p>
<p>Q: I already have a claim rejected elsewhere, will you still cover me?</p>
<p>A: Coverage eligibility depends on full disclosure of pre-existing
disease history at the time of proposal.</p>
<p>Q: Can I add my spouse and children to the same policy?</p>
<p>A: Yes, spouse and dependent children up to 25 years old can be added
as family members on the same floater policy.</p>
<p>Customer testimonial: "Excellent service" -- Priya Sharma, PAN
ABCDE1234F, Aadhaar 1234 5678 9012, reachable at priya.sharma@example.com.
</p>
</main>
<footer>Subscribe to our newsletter for updates.</footer>
</body></html>
"""

_OBJECTION_HANDLING_HTML = f"""<!DOCTYPE html>
<html><head><title>Objection Handling -- Health Insurance</title></head>
<body>
{_SYNTHETIC_NOTICE}
<header>Site Header -- Acme Insurance</header>
<main>
<h1>Objection Handling Health Insurance</h1>
<p>Objection: Your premium is higher than what competitors quote for a
similar sum assured.</p>
<p>Response: Our sum assured includes cashless hospitalization across
10,000-plus network hospitals and a no-claim bonus that increases cover
by 10 percent each claim-free year, which most competitor quotes at this
price tier do not include.</p>
<p>Objection: I already have health coverage through my employer, so I
do not need my own policy.</p>
<p>Response: Employer-provided cover usually ends when employment ends;
an individual policy continues independently and is not affected by a
job change.</p>
<p>Objection: I am worried pre-existing conditions will not be covered
at all.</p>
<p>Response: Pre-existing conditions are covered after the waiting
period of 24 months from the policy start date, as long as they were
disclosed at proposal.</p>
</main>
<footer>(c) 2024 Acme Insurance. All rights reserved.</footer>
</body></html>
"""

_ELIGIBILITY_RULES_HTML = f"""<!DOCTYPE html>
<html><head><title>Eligibility and Qualification Rules</title></head>
<body>
{_SYNTHETIC_NOTICE}
<header>Site Header -- Acme Insurance</header>
<main>
<h1>Eligibility Qualification Rules</h1>
<ul>
<li>Applicant must be between 18 and 65 years old at the time of
proposal.</li>
<li>No declined or repudiated claims with any insurer in the last 3
years.</li>
<li>Sum assured requested above INR 2,000,000 requires a pre-policy
medical checkup.</li>
<li>Pre-existing disease history must be fully disclosed at proposal
stage; non-disclosure can void a claim.</li>
</ul>
</main>
<footer>(c) 2024 Acme Insurance. All rights reserved.</footer>
</body></html>
"""

_COMPLIANCE_DISCLOSURE_HTML = f"""<!DOCTYPE html>
<html><head><title>Compliance Disclosure Requirements</title></head>
<body>
{_SYNTHETIC_NOTICE}
<header>Site Header -- Acme Insurance</header>
<main>
<h1>Compliance Disclosure Requirements</h1>
<p>Agents must state the free-look period of 15 days before the customer
confirms purchase, during which the policy can be cancelled for a full
refund minus a small administrative charge.</p>
<p>Agents must disclose that this is an insurance product and not a
fixed deposit or guaranteed-return investment before discussing any
premium amount.</p>
<p>Agents must confirm the customer has read and understood the waiting
period and pre-existing disease exclusions before closing the sale.</p>
</main>
<footer>(c) 2024 Acme Insurance. All rights reserved.</footer>
</body></html>
"""

_PROCESS_CLAIM_FILING_HTML = f"""<!DOCTYPE html>
<html><head><title>Claim Filing Process</title></head>
<body>
{_SYNTHETIC_NOTICE}
<header>Site Header -- Acme Insurance</header>
<main>
<h1>Claim Filing Process</h1>
<h2>Step 1: Notify the Claims Desk</h2>
<p>Notify the claims desk within 48 hours of hospital admission for a
planned procedure, or within 24 hours of admission for an emergency, by
calling the claims helpline or submitting the online claim form.</p>
<h2>Step 2: Submit Documents</h2>
<p>Submit the hospital discharge summary, itemized final bill, and all
diagnostic reports within 15 days of discharge. Incomplete document sets
are the most common cause of claim delay.</p>
<h2>Step 3: Settlement</h2>
<p>Cashless claims at network hospitals are typically settled directly
with the hospital within 2 to 4 hours of document submission;
reimbursement claims at non-network hospitals are settled within 15
working days of receiving a complete document set.</p>
</main>
<footer>(c) 2024 Acme Insurance. All rights reserved.</footer>
</body></html>
"""


def _write_policy_terms_pdf(path: Path) -> None:
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)

    pdf.add_page()
    pdf.multi_cell(0, 8, "SYNTHETIC TEST DATA -- fabricated policy terms, no real customer data.")
    pdf.ln(2)
    pdf.multi_cell(
        0,
        8,
        "Policy Terms and Conditions\n\n"
        "This policy provides coverage amount up to INR 10,00,000 subject "
        "to the waiting period defined below. The moratorium period for "
        "pre-existing disease claims is 24 months from the risk "
        "commencement date of 2023-04-01.\n\n"
        "Claim settlement rate for this product line was 96 percent for "
        "the period ending 15 March 2024.",
    )
    pdf.ln(4)
    pdf.multi_cell(0, 8, "Coverage Table:")
    pdf.set_font("Helvetica", size=10)
    rows = [
        ("Plan", "Sum Insured", "Annual Premium"),
        ("Silver", "Rs. 5,00,000", "Rs. 8,500"),
        ("Gold", "Rs. 10,00,000", "Rs. 14,200"),
        ("Platinum", "Rs. 20,00,000", "Rs. 22,900"),
    ]
    col_width = 60
    for row in rows:
        for cell in row:
            pdf.cell(col_width, 8, cell, border=1)
        pdf.ln(8)

    # Second page is intentionally left blank -- this exercises the
    # extraction_failed / OCR-fallback path in kb.app.ingest.extract_pdf.
    pdf.add_page()

    pdf.output(str(path))


def _write_eligibility_form_pdf(path: Path) -> None:
    pdf = FPDF()
    pdf.set_font("Helvetica", size=11)
    pdf.add_page()
    pdf.multi_cell(0, 8, "SYNTHETIC TEST DATA -- fabricated eligibility form, no real customer data.")
    pdf.ln(2)
    pdf.multi_cell(
        0,
        8,
        "Health Insurance Eligibility Form\n\n"
        "Applicant Name: Sunita Rao\n"
        "Contact Phone: 9123456780\n"
        "Email Address: sunita.rao@example.com\n"
        "PAN Number: BXPRA5678K\n"
        "Aadhaar Number: 9876-5432-1098\n"
        "Date Of Birth: 12-08-1990\n\n"
        "Qualification Rules: Applicant must be between 18 and 65 years "
        "old with no declined claims in the last 3 years.",
    )
    pdf.output(str(path))


def generate_synthetic_dataset(raw_dir: Path) -> None:
    web_dir = raw_dir / "web"
    pdf_dir = raw_dir / "pdfs"
    web_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    (web_dir / "product_partnership_benefits.html").write_text(_PRODUCT_HTML, encoding="utf-8")
    (web_dir / "product_partnership_benefits_duplicate.html").write_text(
        _PRODUCT_DUP_HTML, encoding="utf-8"
    )
    (web_dir / "faq_health_insurance.html").write_text(_FAQ_HTML, encoding="utf-8")
    (web_dir / "objection_handling_health_insurance.html").write_text(
        _OBJECTION_HANDLING_HTML, encoding="utf-8"
    )
    (web_dir / "eligibility_qualification_rules.html").write_text(
        _ELIGIBILITY_RULES_HTML, encoding="utf-8"
    )
    (web_dir / "compliance_disclosure_requirements.html").write_text(
        _COMPLIANCE_DISCLOSURE_HTML, encoding="utf-8"
    )
    (web_dir / "process_claim_filing.html").write_text(
        _PROCESS_CLAIM_FILING_HTML, encoding="utf-8"
    )

    _write_policy_terms_pdf(pdf_dir / "policy_terms.pdf")
    _write_eligibility_form_pdf(pdf_dir / "eligibility_form.pdf")

    (raw_dir / "SYNTHETIC_DATA_NOTICE.md").write_text(
        "# Synthetic Data Notice\n\n"
        "Everything under `data/raw/` was generated by "
        "`kb/app/ingest/synthetic_data.py` for pipeline testing. It is "
        "fabricated and contains no real customer information, even where "
        "it looks like PII (names, phone numbers, PAN/Aadhaar numbers, "
        "emails) -- those values are placeholders chosen to exercise the "
        "PII-masking step.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[3] / "data" / "raw"
    generate_synthetic_dataset(target)
    print(f"Synthetic dataset written to {target}")
