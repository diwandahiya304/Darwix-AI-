# (e) Human-assistance request

_Simulated via `multilingual/philippines/sim` — scripted mode, real tool calls against the real KB and market-specific tools, **not a real Vapi call**. See docs/q3_multilingual/gaps.md and multilingual/README.md for what would need to happen for a real one._

**Scenario:** Customer explicitly asks for a human agent after expressing suspicion the call is a scam.

## Transcript

**Assistant:** Tumatawag po ako tungkol sa inyong premium reminder.

**Customer:** Sandali lang, scam ba talaga ito? Gusto ko makausap yung totoong tao.

> 🔧 **escalate_to_human**(`{"reason": "explicit_request", "context": "Customer suspects scam and explicitly asked for a human agent."}`) → `{"escalated": true, "method": "logged_only", "logged_at": "2026-09-30T11:16:22.294352+00:00"}`

**Assistant:** Naiintindihan po namin, ikokonekta ko na po kayo agad sa isang specialist.
