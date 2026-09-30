# (b) Sector-specific objection

_Simulated via `multilingual/indonesia/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer raises 'Gajian belum masuk' and 'Dendanya kok besar?' — both KB-grounded, handled per OJK-conduct guardrails.

## Transcript

**Assistant:** Saya menelepon terkait angsuran Bapak/Ibu yang sudah jatuh tempo.

**Customer:** Waduh, gajian belum masuk nih.

> 🔧 **search_knowledge_base**(`{"query": "Gajian belum masuk", "customer_utterance": "Gajian belum masuk nih."}`) → `{"grounded": true, "speakable_answer": "Objection Handling Collections: Objection: Gajian belum masuk. Response: Baik Pak/Bu, kami mengerti. Boleh kami tahu perkiraan tanggal gajian Bapak/Ibu supaya kami bisa catat janji bayarnya, dan kami akan hubungi kembali sesuai tanggal tersebut? Eligibility Qualification Pembiayaan: Nasabah dengan tunggakan lebih dari 90 hari tidak dapat mengajukan pembiayaan atau top-up baru sampai tunggakan...", "citations": ["[kb_d2968beec617c4ab_000 | kb_seed/web/objection_handling_collections.html | 1.0.1]", "[kb_3dec1f8f682e2238_003 | kb_seed/web/eligibility_qualification_pembiayaan.html | 1.0.1]"], "category": "objection_handling", "register_used": "colloquial"}`

**Assistant:** Objection Handling Collections: Objection: Gajian belum masuk. Response: Baik Pak/Bu, kami mengerti. Boleh kami tahu perkiraan tanggal gajian Bapak/Ibu supaya kami bisa catat janji bayarnya, dan kami akan hubungi kembali sesuai tanggal tersebut? Eligibility Qualification Pembiayaan: Nasabah dengan tunggakan lebih dari 90 hari tidak dapat mengajukan pembiayaan atau top-up baru sampai tunggakan...

**Assistant:** [relays the KB's grounded response asking for an estimated payday — see transcript]

**Customer:** Terus kenapa dendanya kok besar banget?

> 🔧 **search_knowledge_base**(`{"query": "Dendanya kok besar", "customer_utterance": "Dendanya kok besar banget sih?"}`) → `{"grounded": true, "speakable_answer": "Objection Handling Collections: Objection: Dendanya kok besar? Response: Kami mengerti kekhawatiran Bapak/Ibu. Denda dihitung sesuai perjanjian pembiayaan di awal, dan kami bisa bantu jelaskan rinciannya atau bantu ajukan keringanan denda jika Bapak/Ibu memenuhi syarat. Faq Multifinance Installment: Q: Berapa denda kalau telat bayar angsuran? A: Denda keterlambatan adalah 0,5% per hari dari...", "citations": ["[kb_d2968beec617c4ab_001 | kb_seed/web/objection_handling_collections.html | 1.0.1]", "[kb_cfaf31d50571976c_001 | kb_seed/web/faq_multifinance_installment.html | 1.0.1]"], "category": "objection_handling", "register_used": "formal"}`

**Assistant:** Objection Handling Collections: Objection: Dendanya kok besar? Response: Kami mengerti kekhawatiran Bapak/Ibu. Denda dihitung sesuai perjanjian pembiayaan di awal, dan kami bisa bantu jelaskan rinciannya atau bantu ajukan keringanan denda jika Bapak/Ibu memenuhi syarat. Faq Multifinance Installment: Q: Berapa denda kalau telat bayar angsuran? A: Denda keterlambatan adalah 0,5% per hari dari...

**Assistant:** [relays the KB's grounded explanation of penalty calculation — see transcript]
