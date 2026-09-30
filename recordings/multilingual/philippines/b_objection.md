# (b) Sector-specific objection

_Simulated via `multilingual/philippines/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer raises 'Wala akong pera ngayon' and 'May insurance na ako sa work' — both KB-grounded.

## Transcript

**Assistant:** Tumatawag po ako tungkol sa inyong premium na malapit nang due.

**Customer:** Ay, wala akong pera ngayon eh.

> 🔧 **search_knowledge_base**(`{"query": "Wala akong pera ngayon", "customer_utterance": "Wala akong pera ngayon."}`) → `{"grounded": true, "speakable_answer": "Objection Handling Premium Reminder: Objection: Wala akong pera ngayon. Response: Naiintindihan po namin. Meron po kaming auto-debit facility na pwede ninyong i-set sa araw na may sahod kayo, para hindi na po kayo mag-alala sa due date. Gusto niyo po bang i-set up natin ito ngayon, o mas gugustuhin niyo po bang tawagan namin kayo sa ibang araw? Faq Life Insurance Premium: Q: Ano po ang mangyayari...", "citations": ["[kb_6934336ba879f884_000 | kb_seed/web/objection_handling_premium_reminder.html | 1.0.1]", "[kb_52c904d1a83715a6_001 | kb_seed/web/faq_life_insurance_premium.html | 1.0.1]"], "category": "objection_handling", "register_used": "formal"}`

**Assistant:** Objection Handling Premium Reminder: Objection: Wala akong pera ngayon. Response: Naiintindihan po namin. Meron po kaming auto-debit facility na pwede ninyong i-set sa araw na may sahod kayo, para hindi na po kayo mag-alala sa due date. Gusto niyo po bang i-set up natin ito ngayon, o mas gugustuhin niyo po bang tawagan namin kayo sa ibang araw? Faq Life Insurance Premium: Q: Ano po ang mangyayari...

**Assistant:** [relays the KB's grounded objection response about auto-debit on payday — see transcript]

**Customer:** Hmm, may insurance na naman ako sa work eh, kailangan pa ba ito?

> 🔧 **search_knowledge_base**(`{"query": "May insurance na ako sa work", "customer_utterance": "May insurance na ako sa work."}`) → `{"grounded": true, "speakable_answer": "Objection Handling Premium Reminder: Objection: May insurance na ako sa work. Response: Maganda po iyon! Karamihan po ng group insurance sa trabaho ay tumatagal lamang habang kayo ay empleyado roon. Ang inyong individual policy po ay nagpapatuloy nang independiyente kahit magpalit kayo ng trabaho. Gusto niyo po bang malaman kung paano ito nagko-complement sa inyong coverage sa work? Faq Life...", "citations": ["[kb_6934336ba879f884_003 | kb_seed/web/objection_handling_premium_reminder.html | 1.0.1]", "[kb_52c904d1a83715a6_003 | kb_seed/web/faq_life_insurance_premium.html | 1.0.1]"], "category": "objection_handling", "register_used": "formal"}`

**Assistant:** Objection Handling Premium Reminder: Objection: May insurance na ako sa work. Response: Maganda po iyon! Karamihan po ng group insurance sa trabaho ay tumatagal lamang habang kayo ay empleyado roon. Ang inyong individual policy po ay nagpapatuloy nang independiyente kahit magpalit kayo ng trabaho. Gusto niyo po bang malaman kung paano ito nagko-complement sa inyong coverage sa work? Faq Life...

**Assistant:** [relays the KB's grounded response about individual vs. group coverage — see transcript]
