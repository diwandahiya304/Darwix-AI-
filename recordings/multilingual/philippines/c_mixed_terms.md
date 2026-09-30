# (c) Mixed English/finance terms (natural Taglish)

_Simulated via `multilingual/philippines/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer and assistant naturally code-switch finance terms (premium, coverage, rider, beneficiary) mid-sentence — this is expected Taglish, not a fallback trigger.

## Transcript

**Assistant:** Ma'am, may premium po kayong due sa 15th — gusto niyo po bang i-auto-debit para hindi ma-lapse ang policy?

**Customer:** Sige, pero what's my coverage amount ulit and sino yung beneficiary ko?

> 🔧 **search_knowledge_base**(`{"query": "Ano ang coverage amount at beneficiary ng aking policy", "customer_utterance": "What's my coverage amount and sino beneficiary ko?"}`) → `{"grounded": true, "speakable_answer": "Faq Life Insurance Premium: Q: Ano po ang rider na maidadagdag ko sa aking policy? A: Available po ang accidental death rider at critical illness rider na maidadagdag sa inyong base coverage, karaniwan po nang may karagdagang premium na nagsisimula sa ₱200 kada buwan depende sa edad at sum assured. Faq Life Insurance Premium: Q: Ano po ang mangyayari kung ma-late ako sa bayad? A: Kung lumampas po...", "citations": ["[kb_52c904d1a83715a6_003 | kb_seed/web/faq_life_insurance_premium.html | 1.0.1]", "[kb_52c904d1a83715a6_001 | kb_seed/web/faq_life_insurance_premium.html | 1.0.1]"], "category": "faq", "register_used": "formal"}`

**Assistant:** Faq Life Insurance Premium: Q: Ano po ang rider na maidadagdag ko sa aking policy? A: Available po ang accidental death rider at critical illness rider na maidadagdag sa inyong base coverage, karaniwan po nang may karagdagang premium na nagsisimula sa ₱200 kada buwan depende sa edad at sum assured. Faq Life Insurance Premium: Q: Ano po ang mangyayari kung ma-late ako sa bayad? A: Kung lumampas po...

**Assistant:** [relays the KB's grounded answer about coverage amount and beneficiary — see transcript]

**Customer:** Okay, pwede ko bang i-add yung rider for accidental death?

> 🔧 **search_knowledge_base**(`{"query": "Paano magdagdag ng accidental death rider", "customer_utterance": "Pwede ba i-add yung rider for accidental death?"}`) → `{"grounded": true, "speakable_answer": "Faq Life Insurance Premium: Q: Ano po ang rider na maidadagdag ko sa aking policy? A: Available po ang accidental death rider at critical illness rider na maidadagdag sa inyong base coverage, karaniwan po nang may karagdagang premium na nagsisimula sa ₱200 kada buwan depende sa edad at sum assured. Product Bank Referral Bancassurance: Ang aming bank referral program po ay nagbibigay-daan sa mga...", "citations": ["[kb_52c904d1a83715a6_003 | kb_seed/web/faq_life_insurance_premium.html | 1.0.1]", "[kb_916fda0d9abc8124_000 | kb_seed/web/product_bank_referral_bancassurance.html | 1.0.1]"], "category": "faq", "register_used": "formal"}`

**Assistant:** Faq Life Insurance Premium: Q: Ano po ang rider na maidadagdag ko sa aking policy? A: Available po ang accidental death rider at critical illness rider na maidadagdag sa inyong base coverage, karaniwan po nang may karagdagang premium na nagsisimula sa ₱200 kada buwan depende sa edad at sum assured. Product Bank Referral Bancassurance: Ang aming bank referral program po ay nagbibigay-daan sa mga...

**Assistant:** [relays the KB's grounded answer about riders — see transcript]
