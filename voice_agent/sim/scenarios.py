"""The 5 required test scenarios (assignment brief) as structured,
turn-by-turn scripts. sim/chat_sim.py's scripted mode executes these
against the REAL tool registry (voice_agent/app/tools.py) — customer
lines are fixed/scripted, but every tool call and its result is real
(hits the real KB retrieval API, real scoring logic, real CRM writes),
not fabricated. Human-readable versions of these same scripts live in
tests/scenarios.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Turn:
    speaker: str  # "customer" | "assistant"
    text: str = ""
    tool_call: tuple[str, dict] | None = None  # (tool_name, arguments)


@dataclass
class Scenario:
    scenario_id: str
    title: str
    description: str
    turns: list[Turn] = field(default_factory=list)


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
        description=(
            "Customer answers every qualification question directly and "
            "agrees to a next step. Expected: full qualification flow, "
            "score_lead called once, create_lead called once, next step "
            "agreed and closed warmly."
        ),
        turns=[
            _a("Hi, this is Asha calling from Acme Insurance — do you have a moment?"),
            _c("Sure, go ahead."),
            _a(
                "Great, thank you. This call is recorded for quality and training "
                "purposes. I'm calling about health insurance options — could I "
                "ask a few quick questions?"
            ),
            _c("Yes, that's fine."),
            _a("Could I start with your age?"),
            _c("I'm 34."),
            _a("And which city are you in?"),
            _c("Bangalore."),
            _a("How many people are in your family who'd need cover?"),
            _c("Four — myself, my spouse, and two kids."),
            _a("Do you or any family member have any pre-existing conditions you'd like to disclose?"),
            _c("No, we're all healthy."),
            _a("And roughly what monthly budget did you have in mind?"),
            _c("Around 2000 rupees a month."),
            _a("Do you have any current health insurance cover?"),
            _c("No, we don't have any right now."),
            _tool("score_lead", age=34, city="Bangalore", family_size=4, conditions=None, budget=2000, intent="interested"),
            _tool(
                "create_lead",
                customer_name="Cooperative Test Customer",
                phone="9000000001",
                city="Bangalore",
                age=34,
                family_size=4,
                conditions=None,
                budget=2000,
                intent="interested",
                qualification="hot",
                qualification_reasons=[],
                objections_raised=[],
                call_summary=(
                    "Cooperative customer, all qualification questions answered "
                    "directly, family of 4 with no current cover — good floater fit."
                ),
                next_action="send_quote",
            ),
            _a(
                "Thank you, that's really helpful. Based on what you've told me, "
                "I'd like to arrange a quote for a family floater plan — would that work?"
            ),
            _c("Yes, please."),
            _a("Wonderful, I'll have that sent over. Thanks so much for your time today!"),
        ],
    ),
    Scenario(
        scenario_id="b_objection",
        title="(b) Objection — \"premium too expensive\" and \"I don't trust insurance\"",
        description=(
            "One objection the KB directly addresses (premium vs competitors) "
            "and one it does not (general distrust of insurance) — deliberately "
            "mixed so this scenario also exercises the fallback path within an "
            "objection-handling context, not just the FAQ path."
        ),
        turns=[
            _a("Could I ask a few quick questions about health insurance options?"),
            _c("Okay, but your premium seems a lot higher than what I've seen elsewhere."),
            _tool("search_knowledge_base", query="why is the premium higher than competitors"),
            _a("[relays the KB's grounded objection response — see transcript]"),
            _c("Hmm. Honestly, I just don't trust insurance companies in general."),
            _tool("search_knowledge_base", query="I don't trust insurance companies in general"),
            _a("[relays the KB's answer if grounded, or the fallback message if not — see transcript]"),
        ],
    ),
    Scenario(
        scenario_id="c_incomplete_conflicting",
        title="(c) Incomplete and conflicting details",
        description=(
            "Customer gives a vague budget answer (ask once more, then move on "
            "per the hard rule) and later contradicts their stated age by "
            "mentioning they're retired — assistant must confirm, not silently "
            "pick one."
        ),
        turns=[
            _a("And roughly what monthly budget did you have in mind?"),
            _c("I'm not sure, maybe something reasonable?"),
            _a("No problem — even a rough monthly figure would help. Any ballpark?"),
            _c("I really don't know, sorry."),
            _a("That's alright, we can figure that out later. Could I ask your age?"),
            _c("I'm 25."),
            _a("Thanks. And do you have any current health cover?"),
            _c("Well, I'm retired now, so I get some cover through my pension."),
            _a(
                "I want to make sure I have this right — you mentioned you're 25, "
                "but also that you're retired. Could you confirm which applies?"
            ),
            _c("Sorry, I meant my mother's situation — I'm actually 58 and retired myself."),
            _tool("score_lead", age=58, city=None, family_size=None, conditions=None, budget=None, intent="exploring"),
        ],
    ),
    Scenario(
        scenario_id="d_out_of_scope",
        title="(d) Out-of-scope question",
        description=(
            "Customer asks for legal advice unrelated to this call. Expected: "
            "polite decline + redirect, never answered even partially."
        ),
        turns=[
            _a("Could I ask a few quick questions about health insurance options?"),
            _c("Actually, can you give me legal advice on a rent dispute with my landlord?"),
            _a(
                "I'm not able to help with legal matters, I'm afraid — that's outside "
                "what I can do on this call. I'd love to continue with the insurance "
                "questions if that's alright?"
            ),
            _c("Sure, go ahead."),
        ],
    ),
    Scenario(
        scenario_id="e_human_escalation",
        title="(e) Human-assistance request",
        description=(
            "Customer explicitly asks for a human agent. Expected: "
            "escalate_to_human called immediately, no further qualification "
            "attempted in the same turn."
        ),
        turns=[
            _a("Could I ask your age to get started?"),
            _c("Actually, I'd like to speak to a real person please."),
            _tool(
                "escalate_to_human",
                reason="explicit_request",
                context="Customer asked to speak to a human agent during the qualification questions.",
            ),
            _a("Of course — I'll connect you with a specialist right away."),
        ],
    ),
]
