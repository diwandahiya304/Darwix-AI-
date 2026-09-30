# (e) Human-assistance request

_Simulated via `multilingual/indonesia/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer explicitly asks for a human agent after a complaint about being contacted too often.

## Transcript

**Assistant:** Saya menelepon terkait angsuran Bapak/Ibu.

**Customer:** Kok saya ditelepon terus sih, saya mau bicara sama orangnya langsung deh, bukan robot.

> 🔧 **escalate_to_human**(`{"reason": "explicit_request", "context": "Customer complained about repeated contact and explicitly asked for a human agent."}`) → `{"escalated": true, "method": "logged_only", "logged_at": "2026-09-30T11:16:57.278984+00:00"}`

**Assistant:** Baik, mohon maaf atas ketidaknyamanannya. Saya akan sambungkan langsung ke tim kami.
