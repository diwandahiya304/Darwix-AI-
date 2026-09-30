# (d) Colloquial speech (relaxed Taglish, po/opo dropped)

_Simulated via `multilingual/philippines/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer speaks casually without po/opo — assistant should detect the relaxed register and may mirror it slightly while staying respectful.

## Transcript

**Assistant:** Hi! Si Grace 'to from your insurance provider, may minute ka ba?

**Customer:** Oo bes, ano nangyari?

> 🔧 **search_knowledge_base**(`{"query": "kailan due ang premium", "customer_utterance": "Ano ba, kailan due yung premium ko ulit?"}`) → `{"grounded": true, "speakable_answer": "Faq Life Insurance Premium: Q: Kailan po ang due date ng aking premium? A: Ang premium po ay dapat bayaran nang buo bago ang due date na nakalagay sa inyong policy schedule, halimbawa ika-15 ng Marso. May 31 araw pong grace period pagkatapos ng due date bago mag-lapse ang coverage. Process Premium Payment Options — Pag-set Up ng Auto-Debit: Ang auto-debit po ay awtomatikong magbabawas ng premium...", "citations": ["[kb_52c904d1a83715a6_000 | kb_seed/web/faq_life_insurance_premium.html | 1.0.1]", "[kb_c6c55d3345f7c170_001 | kb_seed/web/process_premium_payment_options.html | 1.0.1]"], "category": "faq", "register_used": "colloquial"}`

**Assistant:** Faq Life Insurance Premium: Q: Kailan po ang due date ng aking premium? A: Ang premium po ay dapat bayaran nang buo bago ang due date na nakalagay sa inyong policy schedule, halimbawa ika-15 ng Marso. May 31 araw pong grace period pagkatapos ng due date bago mag-lapse ang coverage. Process Premium Payment Options — Pag-set Up ng Auto-Debit: Ang auto-debit po ay awtomatikong magbabawas ng premium...

**Assistant:** [relays the KB's grounded answer, matching the customer's relaxed tone — see transcript]

**Customer:** Ah ok lang, pwede bang tawagan mo na lang ako next week?

> 🔧 **schedule_callback**(`{"phone": "09171234567", "requested_datetime": "2025-10-07T14:00:00+08:00", "notes": "Customer asked for a casual follow-up next week."}`) → `{"callback_id": "cb_53bcb09c3a9c", "confirmed_datetime": "2025-10-07T14:00:00+08:00"}`

**Assistant:** Sige bes, tatawagan kita next week! Ingat ka.
