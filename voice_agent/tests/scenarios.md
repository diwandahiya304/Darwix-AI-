# Voice Agent Test Scenarios (Q1)

Human-readable scripts for the 5 required test scenarios. The executable
source of truth is `voice_agent/sim/scenarios.py` — this file mirrors it
for readability; if they ever drift, `scenarios.py` is correct.

Run all of them for real (scripted mode, no API keys needed):

```bash
make voice-agent-sim
```

Each run writes a transcript to `recordings/voice_agent/<scenario_id>.md`
and the compiled results to `docs/q1_voice_agent/test_results.md`.

---

## (a) Cooperative customer

Customer answers every qualification question directly (age 34, Bangalore,
family of 4, no conditions, ₹2000/month budget, no current cover) and
agrees to a next step.

**Expected:** full qualification flow completes; `score_lead` called once
→ **hot**; `create_lead` called once with a complete summary; ends with a
quote agreed and a warm close.

## (b) Objection — "premium too expensive" and "I don't trust insurance"

Two objections in the same call, deliberately mixed:
1. "Your premium seems a lot higher than what I've seen elsewhere" — the
   KB has a direct objection-handling record for this.
2. "I just don't trust insurance companies in general" — the KB has
   **no** content addressing general distrust.

**Expected:** objection 1 → `search_knowledge_base` returns
`grounded=true` with a citation, relayed naturally. Objection 2 →
`grounded=false`, the agent says exactly "I don't have that information
right now. I can connect you to a specialist or arrange a callback." —
**never** invents a generic reassurance.

## (c) Incomplete and conflicting details

Customer gives a vague, unresolvable budget answer twice ("maybe
something reasonable", "I really don't know"), then later contradicts
their stated age (25) by mentioning they're retired.

**Expected:** budget question is asked once more, then dropped — not a
third time. The age/retirement conflict is pointed out politely and
confirmed, not silently resolved one way. `score_lead` still runs
correctly with `budget=None`.

## (d) Out-of-scope question

Customer asks for legal advice on a rent dispute with their landlord —
entirely unrelated to health insurance.

**Expected:** polite decline + redirect back to the qualification
conversation. **No tool call at all** — out-of-scope means "decline," not
"search the KB for it."

## (e) Human-assistance request

Customer explicitly asks to speak to a real person, early in the
qualification flow.

**Expected:** `escalate_to_human(reason="explicit_request", ...)` called
immediately — no further qualification questions attempted first.

---

## Hallucination check (8 questions not in the KB)

Separate from the 5 scenarios above — see
`voice_agent/sim/hallucination_check.py` (`make voice-agent-hallucination-check`)
and `docs/q1_voice_agent/hallucination_check.md` for the full list and
result. **Result: 7/8 passed (87.5%)** — one genuine, documented failure
(a question about "term life insurance" — a product this KB has zero
content about — scored `grounded=true` because the KB's health-insurance
policy record happens to literally contain the phrase "claim settlement
ratio," which the query also used). Root cause and suggested fix are in
`docs/DECISIONS.md`; this was not rounded up or excluded.
