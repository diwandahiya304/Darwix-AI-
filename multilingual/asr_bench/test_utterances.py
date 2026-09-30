"""Test utterance set for the ASR benchmark — covers the required test
coverage (cooperative, sector-specific objection, mixed English/finance
terms, colloquial speech, human escalation, and, for Indonesia, regional
accent). Drawn directly from the customer lines already written in
sim/scenarios.py for each market, so the same utterances back both the
conversational scenario tests and the ASR benchmark rather than
maintaining two separate example sets that could drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestUtterance:
    utterance_id: str
    market: str  # "philippines" | "indonesia"
    category: str
    text: str  # reference transcript ("ground truth")
    named_terms: list[str] = field(default_factory=list)
    code_switch_markers: list[str] = field(default_factory=list)


TEST_UTTERANCES: list[TestUtterance] = [
    TestUtterance(
        "ph_cooperative", "philippines", "cooperative",
        "Kailan po ba due yung premium ko?", named_terms=["premium"], code_switch_markers=["premium"],
    ),
    TestUtterance(
        "ph_objection", "philippines", "objection",
        "Wala akong pera ngayon.",
    ),
    TestUtterance(
        "ph_mixed_terms", "philippines", "mixed_terms",
        "Sige, pero what's my coverage amount ulit and sino yung beneficiary ko?",
        named_terms=["coverage", "beneficiary"], code_switch_markers=["coverage", "beneficiary"],
    ),
    TestUtterance(
        "ph_colloquial", "philippines", "colloquial",
        "Ah ok lang, pwede bang tawagan mo na lang ako next week?",
        code_switch_markers=["ok", "next week"],
    ),
    TestUtterance(
        "ph_escalation", "philippines", "escalation",
        "Sandali lang, scam ba talaga ito? Gusto ko makausap yung totoong tao.",
        code_switch_markers=["scam"],
    ),
    TestUtterance(
        "id_cooperative", "indonesia", "cooperative",
        "Kapan ya jatuh temponya?", named_terms=["jatuh tempo"],
    ),
    TestUtterance(
        "id_objection", "indonesia", "objection",
        "Waduh, gajian belum masuk nih.",
    ),
    TestUtterance(
        "id_mixed_terms", "indonesia", "mixed_terms",
        "Boleh, tapi tenornya bisa diperpanjang nggak kalau saya mau top-up?",
        named_terms=["tenor", "top-up"], code_switch_markers=["tenor", "top-up"],
    ),
    TestUtterance(
        "id_colloquial", "indonesia", "colloquial",
        "Halo Kak, ada apa nih?",
    ),
    TestUtterance(
        "id_escalation", "indonesia", "escalation",
        "Kok saya ditelepon terus sih, saya mau bicara sama orangnya langsung deh, bukan robot.",
    ),
    TestUtterance(
        "id_regional_accent", "indonesia", "regional_accent",
        "Nggih Pak, angsurane sampun kulo bayar kok, mboten enten tunggakan.",
        named_terms=["angsuran"], code_switch_markers=["nggih", "sampun", "mboten"],
    ),
]
