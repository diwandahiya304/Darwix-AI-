# (c) Mixed English/finance terms (natural loanwords)

_Simulated via `multilingual/indonesia/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer and assistant naturally use finance English loanwords (DP, tenor, limit, top-up, auto-debit) mid-sentence — expected vocabulary, not a fallback trigger.

## Transcript

**Assistant:** Bapak/Ibu, cicilannya sudah jatuh tempo — apakah mau saya bantu aktifkan auto-debit supaya tidak perlu diingatkan terus?

**Customer:** Boleh, tapi tenornya bisa diperpanjang nggak kalau saya mau top-up?

> 🔧 **search_knowledge_base**(`{"query": "Bisa nggak tenornya diperpanjang untuk top-up", "customer_utterance": "Tenornya bisa diperpanjang nggak kalau mau top-up?"}`) → `{"grounded": true, "speakable_answer": "Faq Multifinance Installment: Q: Bisa nggak tenornya diperpanjang? A: Bisa Pak/Bu, perpanjangan tenor melalui restrukturisasi dapat diajukan dengan menghubungi cabang terdekat atau customer service, dan akan dievaluasi berdasarkan riwayat pembayaran Bapak/Ibu. Faq Multifinance Installment: Q: Apakah bisa top-up pembiayaan yang sedang berjalan? A: Bisa, top-up dapat diajukan setelah minimal 6...", "citations": ["[kb_cfaf31d50571976c_002 | kb_seed/web/faq_multifinance_installment.html | 1.0.1]", "[kb_cfaf31d50571976c_004 | kb_seed/web/faq_multifinance_installment.html | 1.0.1]"], "category": "faq", "register_used": "formal"}`

**Assistant:** Faq Multifinance Installment: Q: Bisa nggak tenornya diperpanjang? A: Bisa Pak/Bu, perpanjangan tenor melalui restrukturisasi dapat diajukan dengan menghubungi cabang terdekat atau customer service, dan akan dievaluasi berdasarkan riwayat pembayaran Bapak/Ibu. Faq Multifinance Installment: Q: Apakah bisa top-up pembiayaan yang sedang berjalan? A: Bisa, top-up dapat diajukan setelah minimal 6...

**Assistant:** [relays the KB's grounded answer about tenor extension and top-up eligibility — see transcript]

**Customer:** Ok, terus DP untuk pembiayaan baru minimal berapa persen?

> 🔧 **search_knowledge_base**(`{"query": "Berapa DP minimal untuk pembiayaan kendaraan", "customer_utterance": "DP minimal berapa persen ya?"}`) → `{"grounded": true, "speakable_answer": "Faq Multifinance Installment: Q: Berapa DP minimal untuk pembiayaan kendaraan? A: DP minimal umumnya 20 persen dari harga kendaraan untuk kendaraan baru, dan bisa berbeda untuk kendaraan bekas tergantung penilaian dan kebijakan pembiayaan. Faq Multifinance Installment: Q: Berapa denda kalau telat bayar angsuran? A: Denda keterlambatan adalah 0,5% per hari dari jumlah angsuran yang tertunggak,...", "citations": ["[kb_cfaf31d50571976c_003 | kb_seed/web/faq_multifinance_installment.html | 1.0.1]", "[kb_cfaf31d50571976c_001 | kb_seed/web/faq_multifinance_installment.html | 1.0.1]"], "category": "faq", "register_used": "formal"}`

**Assistant:** Faq Multifinance Installment: Q: Berapa DP minimal untuk pembiayaan kendaraan? A: DP minimal umumnya 20 persen dari harga kendaraan untuk kendaraan baru, dan bisa berbeda untuk kendaraan bekas tergantung penilaian dan kebijakan pembiayaan. Faq Multifinance Installment: Q: Berapa denda kalau telat bayar angsuran? A: Denda keterlambatan adalah 0,5% per hari dari jumlah angsuran yang tertunggak,...

**Assistant:** [relays the KB's grounded answer about minimum DP — see transcript]
