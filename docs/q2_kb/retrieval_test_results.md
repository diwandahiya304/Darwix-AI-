# KB Retrieval Test Results

_Generated: 2026-09-30T11:15:37Z_

## Summary

- hit@1: 1.00
- hit@3: 1.00
- Out-of-scope rejection rate: 1.00
- Latency P50: 74.1ms, P95: 103.4ms
- KB_MIN_RELEVANCE_SCORE: 0.84 (embedding: `intfloat/multilingual-e5-small`, vector store: chroma)

## Per-query results

| # | Query | Category | Retrieved chunk (top-1) | Source reference | Relevance explanation | Verdict |
|---|---|---|---|---|---|---|
| 1 | what is the waiting period for pre-existing disease cover | faq | Health Insurance Faq: Q: What is the waiting period for pre existing disease cover? A: The waiting period for pre existing disease claims is 24 months | raw/web/faq_health_insurance.html | Expected content found in the #1 result. | **correct** |
| 2 | can I add my spouse to the policy | faq | Health Insurance Faq: Q: Can I add my spouse and children to the same policy? A: Yes, spouse and dependent children up to 25 years old can be added as | raw/web/faq_health_insurance.html | Expected content found in the #1 result. | **correct** |
| 3 | I already had a claim rejected by another insurer, will you cover me | faq | Health Insurance Faq: Q: I already have a claim rejected elsewhere, will you still cover me? A: Coverage eligibility depends on full disclosure of pre | raw/web/faq_health_insurance.html | Expected content found in the #1 result. | **correct** |
| 4 | what support do branch partners get | product | Branch Partnership Benefits: Operational, marketing, and technology support is provided to branch partners. Branch partners receive a dedicated relati | raw/web/product_partnership_benefits.html | Expected content found in the #1 result. | **correct** |
| 5 | what is the sum assured for the gold plan | policy | Policy Terms: SYNTHETIC TEST DATA -- fabricated policy terms, no real customer data. Policy Terms and Conditions This policy provides sum assured up t | raw/pdfs/policy_terms.pdf | Expected content found in the #1 result. | **correct** |
| 6 | am I eligible if I am 70 years old | eligibility_qualification | Eligibility and Qualification Rules: Applicant must be between 18 and 65 years old at the time of proposal. | raw/web/eligibility_qualification_rules.html | Expected content found in the #1 result. | **correct** |
| 7 | do I need a medical checkup for a large sum assured | eligibility_qualification | Eligibility and Qualification Rules: Sum assured requested above INR 2,000,000 requires a pre-policy medical checkup. | raw/web/eligibility_qualification_rules.html | Expected content found in the #1 result. | **correct** |
| 8 | why is the premium higher than competitors | objection_handling | Objection Handling -- Health Insurance: Objection: Your premium is higher than what competitors quote for a similar sum assured. Response: Our sum ass | raw/web/objection_handling_health_insurance.html | Expected content found in the #1 result. | **correct** |
| 9 | I already have coverage through my employer, why buy this policy | objection_handling | Objection Handling -- Health Insurance: Objection: I already have health coverage through my employer, so I do not need my own policy. Response: Emplo | raw/web/objection_handling_health_insurance.html | Expected content found in the #1 result. | **correct** |
| 10 | how long does claim settlement take | process | Claim Filing Process — Step 3: Settlement: Cashless claims at network hospitals are typically settled directly with the hospital within 2 to 4 hours o | raw/web/process_claim_filing.html | Expected content found in the #1 result. | **correct** |
| 11 | what disclosures must the agent make before selling the policy | compliance_disclosure | Compliance Disclosure Requirements: Agents must state the free-look period of 15 days before the customer confirms purchase, during which the policy c | raw/web/compliance_disclosure_requirements.html | Expected content found in the #1 result. | **correct** |
| 12 | what is the weather like in Mumbai today | out_of_scope | Eligibility Form: SYNTHETIC TEST DATA -- fabricated eligibility form, no real customer data. Health Insurance Eligibility Form Applicant Name: [PERSON | raw/pdfs/eligibility_form.pdf#page=1 | Correctly rejected as out-of-scope (no grounded answer returned). | **correct** |
| 13 | can you help me file my income tax return | out_of_scope | Health Insurance Faq: Q: Can I add my spouse and children to the same policy? A: Yes, spouse and dependent children up to 25 years old can be added as | raw/web/faq_health_insurance.html | Correctly rejected as out-of-scope (no grounded answer returned). | **correct** |
