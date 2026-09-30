# (b) Objection — "premium too expensive" and "I don't trust insurance"

_Simulated via `sim/chat_sim.py --mode scripted` — **not a real Vapi call**. See README 'Vapi Setup Steps' for running real calls._

**Scenario:** One objection the KB directly addresses (premium vs competitors) and one it does not (general distrust of insurance) — deliberately mixed so this scenario also exercises the fallback path within an objection-handling context, not just the FAQ path.

## Transcript

**Assistant:** Could I ask a few quick questions about health insurance options?

**Customer:** Okay, but your premium seems a lot higher than what I've seen elsewhere.

> 🔧 **search_knowledge_base**(`{"query": "why is the premium higher than competitors"}`) → `{"grounded": true, "speakable_answer": "Objection Handling -- Health Insurance: Objection: Your premium is higher than what competitors quote for a similar sum assured. Response: Our sum assured includes cashless hospitalization across 10,000-plus network hospitals and a no-claim bonus that increases cover by 10 percent each claim-free year, which most competitor quotes at this price tier do not include. Policy Terms: SYNTHETIC TEST...", "citations": ["[kb_b2524b6a08de0226_000 | raw/web/objection_handling_health_insurance.html | 1.0.0]", "[kb_ffb60c939503aacd_000 | raw/pdfs/policy_terms.pdf | 1.0.0]"], "category": "objection_handling"}`

**Assistant:** Objection Handling -- Health Insurance: Objection: Your premium is higher than what competitors quote for a similar sum assured. Response: Our sum assured includes cashless hospitalization across 10,000-plus network hospitals and a no-claim bonus that increases cover by 10 percent each claim-free year, which most competitor quotes at this price tier do not include. Policy Terms: SYNTHETIC TEST...

**Assistant:** [relays the KB's grounded objection response — see transcript]

**Customer:** Hmm. Honestly, I just don't trust insurance companies in general.

> 🔧 **search_knowledge_base**(`{"query": "I don't trust insurance companies in general"}`) → `{"grounded": false, "speakable_answer": "I don't have that information right now. I can connect you to a specialist or arrange a callback.", "citations": [], "category": null}`

**Assistant:** I don't have that information right now. I can connect you to a specialist or arrange a callback.

**Assistant:** [relays the KB's answer if grounded, or the fallback message if not — see transcript]
