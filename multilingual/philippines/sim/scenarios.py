"""Philippines test scenarios: cooperative customer, sector-specific
objection, mixed English/finance terms, colloquial speech, human
escalation. Reuses voice_agent.sim.scenarios' generic Turn/Scenario
dataclasses. Executed via multilingual/common/chat_sim.py's scripted
runner against this market's real tool registry
(multilingual.philippines.app.tools.dispatch).
"""

from __future__ import annotations

from voice_agent.sim.scenarios import Scenario, Turn


def _c(text: str) -> Turn:
    return Turn(speaker="customer", text=text)


def _a(text: str) -> Turn:
    return Turn(speaker="assistant", text=text)


def _tool(tool: str, **args) -> Turn:
    return Turn(speaker="assistant", tool_call=(tool, args))


SCENARIOS: list[Scenario] = [
    Scenario(
        scenario_id="a_cooperative",
        title="(a) Cooperative customer",
        description="Customer confirms the reminder and agrees to auto-debit enrollment.",
        turns=[
            _a("Magandang araw po! Ito po si Grace, tumatawag mula sa inyong bangko partner. May sandali po ba kayo?"),
            _c("Opo, ano po iyon?"),
            _a("Salamat po. Ito po ay rine-record para sa quality assurance. Tumatawag po ako tungkol sa inyong premium reminder."),
            _tool("search_knowledge_base", query="kailan po ang due date ng aking premium", customer_utterance="Kailan po due yung premium ko?"),
            _c("Kailan po ba due yung premium ko?"),
            _a("[relays the KB's grounded answer about the due date — see transcript]"),
            _c("Ah okay po, gusto ko na lang po i-set up yung auto-debit para hindi na po ako mag-alala."),
            _tool("set_auto_debit_preference", policy_number="POL-PH-001", enroll=True, payment_day=15),
            _a("Salamat po! Na-set up na po namin ang auto-debit ninyo tuwing ika-15 ng buwan. Maganda pong araw po sa inyo!"),
        ],
    ),
    Scenario(
        scenario_id="b_objection",
        title="(b) Sector-specific objection",
        description="Customer raises 'Wala akong pera ngayon' and 'May insurance na ako sa work' — both KB-grounded.",
        turns=[
            _a("Tumatawag po ako tungkol sa inyong premium na malapit nang due."),
            _c("Ay, wala akong pera ngayon eh."),
            _tool("search_knowledge_base", query="Wala akong pera ngayon", customer_utterance="Wala akong pera ngayon."),
            _a("[relays the KB's grounded objection response about auto-debit on payday — see transcript]"),
            _c("Hmm, may insurance na naman ako sa work eh, kailangan pa ba ito?"),
            _tool("search_knowledge_base", query="May insurance na ako sa work", customer_utterance="May insurance na ako sa work."),
            _a("[relays the KB's grounded response about individual vs. group coverage — see transcript]"),
        ],
    ),
    Scenario(
        scenario_id="c_mixed_terms",
        title="(c) Mixed English/finance terms (natural Taglish)",
        description="Customer and assistant naturally code-switch finance terms (premium, coverage, rider, beneficiary) mid-sentence — this is expected Taglish, not a fallback trigger.",
        turns=[
            _a("Ma'am, may premium po kayong due sa 15th — gusto niyo po bang i-auto-debit para hindi ma-lapse ang policy?"),
            _c("Sige, pero what's my coverage amount ulit and sino yung beneficiary ko?"),
            _tool("search_knowledge_base", query="Ano ang coverage amount at beneficiary ng aking policy", customer_utterance="What's my coverage amount and sino beneficiary ko?"),
            _a("[relays the KB's grounded answer about coverage amount and beneficiary — see transcript]"),
            _c("Okay, pwede ko bang i-add yung rider for accidental death?"),
            _tool("search_knowledge_base", query="Paano magdagdag ng accidental death rider", customer_utterance="Pwede ba i-add yung rider for accidental death?"),
            _a("[relays the KB's grounded answer about riders — see transcript]"),
        ],
    ),
    Scenario(
        scenario_id="d_colloquial",
        title="(d) Colloquial speech (relaxed Taglish, po/opo dropped)",
        description="Customer speaks casually without po/opo — assistant should detect the relaxed register and may mirror it slightly while staying respectful.",
        turns=[
            _a("Hi! Si Grace 'to from your insurance provider, may minute ka ba?"),
            _c("Oo bes, ano nangyari?"),
            _tool("search_knowledge_base", query="kailan due ang premium", customer_utterance="Ano ba, kailan due yung premium ko ulit?"),
            _a("[relays the KB's grounded answer, matching the customer's relaxed tone — see transcript]"),
            _c("Ah ok lang, pwede bang tawagan mo na lang ako next week?"),
            _tool("schedule_callback", phone="09171234567", requested_datetime="2025-10-07T14:00:00+08:00", notes="Customer asked for a casual follow-up next week."),
            _a("Sige bes, tatawagan kita next week! Ingat ka."),
        ],
    ),
    Scenario(
        scenario_id="e_human_escalation",
        title="(e) Human-assistance request",
        description="Customer explicitly asks for a human agent after expressing suspicion the call is a scam.",
        turns=[
            _a("Tumatawag po ako tungkol sa inyong premium reminder."),
            _c("Sandali lang, scam ba talaga ito? Gusto ko makausap yung totoong tao."),
            _tool("escalate_to_human", reason="explicit_request", context="Customer suspects scam and explicitly asked for a human agent."),
            _a("Naiintindihan po namin, ikokonekta ko na po kayo agad sa isang specialist."),
        ],
    ),
]
