"""Indonesia test scenarios: cooperative customer, sector-specific
objection, mixed English/finance terms, colloquial speech, human
escalation, Indonesian regional accent. Reuses voice_agent.sim.scenarios'
generic Turn/Scenario dataclasses. Executed via
multilingual/common/chat_sim.py's scripted runner against this market's
real tool registry (multilingual.indonesia.app.tools.dispatch).

The regional-accent scenario is a TEXT-level proxy only: it uses actual
Javanese-influenced particles/vocabulary a customer might use in
transcribed speech (nggih, mboten, sampun, wis, ora). It does NOT test
real ASR pronunciation/accent recognition — that needs real audio and a
live ASR provider, neither available in this environment. See
docs/q3_multilingual/asr_report.md and gaps.md.
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
        description="Customer confirms the installment reminder and commits to a payment date.",
        turns=[
            _a("Selamat siang, Bapak/Ibu. Saya menelepon dari perusahaan pembiayaan Bapak/Ibu — apakah ada waktu sebentar?"),
            _c("Ya, ada apa ya?"),
            _a("Baik, panggilan ini direkam untuk keperluan kualitas. Saya ingin mengingatkan soal angsuran Bapak/Ibu."),
            _tool("search_knowledge_base", query="kapan jatuh tempo cicilan saya", customer_utterance="Kapan jatuh tempo cicilan saya ya?"),
            _c("Kapan ya jatuh temponya?"),
            _a("[relays the KB's grounded answer about the due date — see transcript]"),
            _c("Oh baik, saya akan bayar tanggal 25 nanti."),
            _tool("record_promise_to_pay", loan_id="LOAN-ID-001", promise_date="2025-10-25", amount=1250000),
            _a("Baik, sudah saya catat janji bayarnya untuk tanggal 25. Terima kasih Bapak/Ibu."),
        ],
    ),
    Scenario(
        scenario_id="b_objection",
        title="(b) Sector-specific objection",
        description="Customer raises 'Gajian belum masuk' and 'Dendanya kok besar?' — both KB-grounded, handled per OJK-conduct guardrails.",
        turns=[
            _a("Saya menelepon terkait angsuran Bapak/Ibu yang sudah jatuh tempo."),
            _c("Waduh, gajian belum masuk nih."),
            _tool("search_knowledge_base", query="Gajian belum masuk", customer_utterance="Gajian belum masuk nih."),
            _a("[relays the KB's grounded response asking for an estimated payday — see transcript]"),
            _c("Terus kenapa dendanya kok besar banget?"),
            _tool("search_knowledge_base", query="Dendanya kok besar", customer_utterance="Dendanya kok besar banget sih?"),
            _a("[relays the KB's grounded explanation of penalty calculation — see transcript]"),
        ],
    ),
    Scenario(
        scenario_id="c_mixed_terms",
        title="(c) Mixed English/finance terms (natural loanwords)",
        description="Customer and assistant naturally use finance English loanwords (DP, tenor, limit, top-up, auto-debit) mid-sentence — expected vocabulary, not a fallback trigger.",
        turns=[
            _a("Bapak/Ibu, cicilannya sudah jatuh tempo — apakah mau saya bantu aktifkan auto-debit supaya tidak perlu diingatkan terus?"),
            _c("Boleh, tapi tenornya bisa diperpanjang nggak kalau saya mau top-up?"),
            _tool("search_knowledge_base", query="Bisa nggak tenornya diperpanjang untuk top-up", customer_utterance="Tenornya bisa diperpanjang nggak kalau mau top-up?"),
            _a("[relays the KB's grounded answer about tenor extension and top-up eligibility — see transcript]"),
            _c("Ok, terus DP untuk pembiayaan baru minimal berapa persen?"),
            _tool("search_knowledge_base", query="Berapa DP minimal untuk pembiayaan kendaraan", customer_utterance="DP minimal berapa persen ya?"),
            _a("[relays the KB's grounded answer about minimum DP — see transcript]"),
        ],
    ),
    Scenario(
        scenario_id="d_colloquial",
        title="(d) Colloquial speech (Kak/nih register)",
        description="Customer speaks casually — assistant should detect the colloquial register and may mirror it while staying professional.",
        turns=[
            _a("Halo, ini Budi dari perusahaan pembiayaan Kakak. Ada waktu sebentar nggak?"),
            _c("Halo Kak, ada apa nih?"),
            _tool("search_knowledge_base", query="kapan jatuh tempo cicilan", customer_utterance="Cicilannya udah jatuh tempo nih Kak?"),
            _a("[relays the KB's grounded answer, matching the customer's casual tone — see transcript]"),
            _c("Oh gitu, boleh nggak aku ditelepon lagi besok aja?"),
            _tool("schedule_callback", phone="081234567890", requested_datetime="2025-10-06T10:00:00+07:00", notes="Customer asked for a casual follow-up tomorrow."),
            _a("Boleh banget Kak, aku telepon lagi besok ya!"),
        ],
    ),
    Scenario(
        scenario_id="e_human_escalation",
        title="(e) Human-assistance request",
        description="Customer explicitly asks for a human agent after a complaint about being contacted too often.",
        turns=[
            _a("Saya menelepon terkait angsuran Bapak/Ibu."),
            _c("Kok saya ditelepon terus sih, saya mau bicara sama orangnya langsung deh, bukan robot."),
            _tool("escalate_to_human", reason="explicit_request", context="Customer complained about repeated contact and explicitly asked for a human agent."),
            _a("Baik, mohon maaf atas ketidaknyamanannya. Saya akan sambungkan langsung ke tim kami."),
        ],
    ),
    Scenario(
        scenario_id="f_regional_accent",
        title="(f) Indonesian regional accent (Javanese-influenced, text proxy)",
        description=(
            "Customer's speech (as transcribed) uses Javanese-influenced "
            "particles/vocabulary (nggih=yes/polite, mboten=no/not, "
            "sampun=already, wis=already/colloquial, ora=not). This tests "
            "text-level handling of regional vocabulary only — NOT real "
            "ASR accent/pronunciation recognition, which needs real audio "
            "and a live provider (not available here). See "
            "docs/q3_multilingual/asr_report.md."
        ),
        turns=[
            _a("Selamat siang, Bapak/Ibu. Saya menelepon terkait angsuran yang sudah jatuh tempo."),
            _c("Nggih Pak, angsurane sampun kulo bayar kok, mboten enten tunggakan."),
            _tool(
                "search_knowledge_base",
                query="Saya sudah bayar angsuran, tidak ada tunggakan",
                customer_utterance="Angsurane sampun kulo bayar kok, mboten enten tunggakan.",
            ),
            _a("[relays the KB's grounded answer asking for payment proof/reference number — see transcript]"),
            _c("Enggeh, engkas kulo kirim buktine nggih, wis tak foto."),
            _a("Baik Pak/Bu, ditunggu buktinya nggih, terima kasih."),
        ],
    ),
]
