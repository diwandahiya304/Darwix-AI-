# (e) Human-assistance request

_Simulated via `sim/chat_sim.py --mode scripted` — **not a real Vapi call**. See README 'Vapi Setup Steps' for running real calls._

**Scenario:** Customer explicitly asks for a human agent. Expected: escalate_to_human called immediately, no further qualification attempted in the same turn.

## Transcript

**Assistant:** Could I ask your age to get started?

**Customer:** Actually, I'd like to speak to a real person please.

> 🔧 **escalate_to_human**(`{"reason": "explicit_request", "context": "Customer asked to speak to a human agent during the qualification questions."}`) → `{"escalated": true, "method": "logged_only", "logged_at": "2026-09-30T11:19:46.004000+00:00"}`

**Assistant:** Of course — I'll connect you with a specialist right away.
