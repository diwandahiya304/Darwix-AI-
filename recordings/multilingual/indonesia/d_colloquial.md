# (d) Colloquial speech (Kak/nih register)

_Simulated via `multilingual/indonesia/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer speaks casually — assistant should detect the colloquial register and may mirror it while staying professional.

## Transcript

**Assistant:** Halo, ini Budi dari perusahaan pembiayaan Kakak. Ada waktu sebentar nggak?

**Customer:** Halo Kak, ada apa nih?

> 🔧 **search_knowledge_base**(`{"query": "kapan jatuh tempo cicilan", "customer_utterance": "Cicilannya udah jatuh tempo nih Kak?"}`) → `{"grounded": true, "speakable_answer": "Faq Multifinance Installment: Q: Kapan jatuh tempo cicilan saya? A: Cicilan Bapak/Ibu jatuh tempo setiap tanggal 25 setiap bulannya, sesuai dengan perjanjian pembiayaan yang telah disepakati. Pembayaran dapat dilakukan mulai H-3 sebelum tanggal jatuh tempo. Process Installment Payment Options — Jika Terjadi Tunggakan: Jika terjadi keterlambatan pembayaran melebihi jatuh tempo, akan dikenakan...", "citations": ["[kb_cfaf31d50571976c_000 | kb_seed/web/faq_multifinance_installment.html | 1.0.1]", "[kb_3d37805d0dd48738_002 | kb_seed/web/process_installment_payment_options.html | 1.0.0]"], "category": "faq", "register_used": "colloquial"}`

**Assistant:** Faq Multifinance Installment: Q: Kapan jatuh tempo cicilan saya? A: Cicilan Bapak/Ibu jatuh tempo setiap tanggal 25 setiap bulannya, sesuai dengan perjanjian pembiayaan yang telah disepakati. Pembayaran dapat dilakukan mulai H-3 sebelum tanggal jatuh tempo. Process Installment Payment Options — Jika Terjadi Tunggakan: Jika terjadi keterlambatan pembayaran melebihi jatuh tempo, akan dikenakan...

**Assistant:** [relays the KB's grounded answer, matching the customer's casual tone — see transcript]

**Customer:** Oh gitu, boleh nggak aku ditelepon lagi besok aja?

> 🔧 **schedule_callback**(`{"phone": "081234567890", "requested_datetime": "2025-10-06T10:00:00+07:00", "notes": "Customer asked for a casual follow-up tomorrow."}`) → `{"callback_id": "cb_f6ae6a58981f", "confirmed_datetime": "2025-10-06T10:00:00+07:00"}`

**Assistant:** Boleh banget Kak, aku telepon lagi besok ya!
