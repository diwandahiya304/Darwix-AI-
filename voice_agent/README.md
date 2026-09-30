# voice_agent/ — Knowledge-Grounded Voice Agent (Q1)

> Status: **fully implemented and tested against a simulated call
> pipeline.** No live Vapi account is available in this development
> environment — see "Vapi Setup Steps" below for connecting a real one.
> Everything up to the voice platform itself (webhook, tools, scoring,
> escalation, CRM, conversation design, simulator, hallucination check)
> is real, executed, and tested.

## Overview

Use case: **health-insurance lead qualification**, outbound call. The
assistant ("Asha") follows a system prompt containing **only** persona,
tone, call flow, guardrails, and tool-usage rules — see
[`config/system_prompt.md`](config/system_prompt.md) — and never a
single fact. Every fact (products, policies, eligibility, objections)
comes from the Q2 KB via `search_knowledge_base`, called through a
FastAPI webhook (`app/main.py`) that Vapi's custom-LLM/tool-calling setup
invokes at runtime.

## Architecture

```
Vapi (LLM + voice) --tool call--> app/main.py (/webhook)
                                       |
                                       v
                                  app/tools.py (dispatch registry)
                                    /    |      \       \        \
                    kb_client.py  scoring.py  escalation.py  crm.py
                    (Q2 /search)  (rules from   (webhook/log)  (SQLite)
                                   config/qualification_rules.yaml)
```

The same `tools.py` registry is used by the real webhook **and** by
`sim/chat_sim.py` — the simulator and the production path can never
silently diverge into two implementations.

## Vapi Setup Steps

No live Vapi account exists in this development environment, so these
steps are written for **you** to follow, not something already run here.
Every script below fails with a clear message (verified) if a required
env var is missing, rather than crashing.

1. **Create a Vapi account** at [vapi.ai](https://vapi.ai) and sign in to
   the dashboard.
2. **Get an API key**: Dashboard → Settings → API Keys → create a
   private key. Copy it.
3. **Configure `.env`**:
   ```bash
   cp .env.example .env
   # set:
   VAPI_API_KEY=<your key>
   ```
4. **Expose the webhook publicly** (Vapi needs to reach your local
   machine). Pick one:
   - **ngrok**: `ngrok http 8002` → copy the `https://...ngrok-free.app`
     URL it prints.
   - **cloudflared**: `cloudflared tunnel --url http://localhost:8002` →
     copy the `https://...trycloudflare.com` URL it prints.
   Set `WEBHOOK_BASE_URL=<that URL>` in `.env` (no trailing slash).
5. **Start the KB retrieval API** (separate terminal, from repo root):
   ```bash
   make ingest-kb     # if not already run
   make run-kb        # port 8001 by default
   ```
6. **Start the voice agent webhook** (another terminal):
   ```bash
   make run-voice-agent   # port 8002 by default
   ```
7. **Create the Vapi assistant**:
   ```bash
   make voice-agent-create-assistant
   ```
   This POSTs to Vapi's `/assistant` API with `config/system_prompt.md` +
   every tool schema from `app/tools.py::TOOL_SCHEMAS`, writes the
   response to `config/vapi_assistant.json` (safe to commit — no API key
   in it), and prints the new assistant id. Set
   `VAPI_ASSISTANT_ID=<that id>` in `.env`.

   **Honesty note**: `build_assistant_payload()`'s request shape (in
   `scripts/create_assistant.py`) is a best-effort model of Vapi's
   documented contract, built from training knowledge — not verified
   against a live response. If Vapi's API has changed or expects a
   slightly different shape, check their current `/assistant` docs and
   adjust that one function; nothing else in this repo depends on it.
8. **Pick a real voice**: `config/vapi_assistant.json`'s `voice.voiceId`
   is a placeholder (`"changeme"`) — pick a real one from the Vapi
   dashboard's voice library and either edit the assistant in the
   dashboard directly, or re-run step 7 after editing
   `scripts/create_assistant.py`'s `voiceId`.
9. **Get a phone number** (Dashboard → Phone Numbers) if you want a
   callable number, or use Vapi's **web calling widget** for browser-based
   testing without a phone number at all.
10. **Make a test call** — via the phone number, or Vapi's dashboard
    "Talk to Assistant" web-calling test feature.
11. **Pull the call transcript**:
    ```bash
    make voice-agent-pull-transcripts
    ```
    Writes each call's JSON into `recordings/voice_agent/vapi_calls/`. Then
    re-run `make voice-agent-test-results` (or write a real-call version
    of it) to compile results from genuine Vapi calls instead of the
    simulator.

## Running Locally Without Vapi (what was actually run for this submission)

No Vapi account, and no LLM API key, is configured here. Every deliverable
below was produced by **actually executing** the real webhook, real
tools, and real Q2 KB retrieval API — just through a text simulator
instead of a phone/web call:

```bash
make voice-agent-sim                    # all 5 required scenarios, scripted mode
make voice-agent-hallucination-check    # 8 questions not in the KB
make voice-agent-test-results           # compiles both into docs/q1_voice_agent/test_results.md
```

`sim/chat_sim.py` also implements a real **`--mode llm`** (Anthropic,
dual-role: one call plays the assistant with real tool-calling, one plays
a customer persona) for fast iteration once you add `LLM_API_KEY` — its
orchestration logic is unit-tested with a mocked client
(`tests/test_chat_sim_llm_mode.py`), but not exercised against a live
model here. See `sim/chat_sim.py`'s module docstring and
`docs/DECISIONS.md` for why only Anthropic is implemented.

## Tools

| Tool | Purpose | Implementation |
|---|---|---|
| `search_knowledge_base(query)` | The **only** source of facts. Returns `grounded` + a speakable summary + citations. | `app/kb_client.py` → Q2's `POST /search` |
| `score_lead(age, city, family_size, conditions, budget, intent)` | Deterministic hot/warm/cold + reasons — never LLM reasoning. | `app/scoring.py`, rules in `config/qualification_rules.yaml` |
| `escalate_to_human(reason, context)` | Logs the escalation; posts to a webhook if configured, else logs a "would transfer" entry (no real telephony transfer without live Vapi). | `app/escalation.py` |
| `create_lead(...)` | Mock CRM write (SQLite). | `app/crm.py` |
| `schedule_callback(phone, requested_datetime, notes)` | Mock CRM write (SQLite). | `app/crm.py` |

## Conversation Flow

See [`docs/voice_flow.md`](../docs/voice_flow.md) for the full state
diagram (Mermaid) and narrative — greeting/consent/disclosure → purpose →
qualification → objection handling → next step → close, plus
interruption/incomplete-info/conflicting-info/out-of-scope/escalation
handling.

## Test Scenarios

See [`tests/scenarios.md`](tests/scenarios.md) for the 5 required
scenarios (cooperative, objection, incomplete+conflicting, out-of-scope,
human-escalation), executed for real via `make voice-agent-sim` —
transcripts in `recordings/voice_agent/*.md`, compiled results in
`docs/q1_voice_agent/test_results.md`.

**Latest run: all 5 scenarios PASS.** Notably, scenario (b)'s two
objections demonstrate both sides of grounding in one call: "premium too
expensive" is genuinely grounded (KB has direct content, dense score
0.89+); "I don't trust insurance" correctly falls back (`grounded=false`,
dense score 0.81 — below the 0.84 threshold) rather than inventing a
generic reassurance.

## Hallucination Check

8 questions deliberately outside the KB's content —
[`sim/hallucination_check.py`](sim/hallucination_check.py)
(`make voice-agent-hallucination-check`), results in
`docs/q1_voice_agent/hallucination_check.md`.

**Result: 7/8 (87.5%)** — one genuine, documented failure: "What is the
claim settlement ratio for your term life insurance product?" came back
`grounded=true` because the KB's health-insurance policy record literally
contains the phrase "claim settlement ratio," even though the question
was about an entirely different, unlisted product line (term life
insurance). Root cause and suggested production fix are in
`docs/DECISIONS.md` — **not excluded or rounded away.**

## Setup

```bash
make setup            # from repo root
cp .env.example .env  # then fill in VAPI_* if connecting a real account
```

## Run

```bash
make run-voice-agent   # webhook server, port $VOICE_AGENT_PORT
```

## Test

```bash
make test-voice-agent
```

50 tests: scoring (hard-disqualifier logic), KB client (mocked HTTP,
including graceful degradation on KB-unreachable), escalation (webhook +
fallback logging), mock CRM (SQLite round-trips), tool dispatch registry,
webhook wiring (FastAPI TestClient), the Vapi scripts' graceful-failure
paths, the 5 scenarios executed for real against the real KB (in-process,
no separate server process needed), and the LLM-mode orchestration logic
(mocked Anthropic client).

## Known Limitations

- **No live Vapi account** — the webhook payload contract
  (`app/models.py`'s `VapiWebhookRequest`/`Response`) and
  `scripts/create_assistant.py`'s request shape are best-effort models of
  Vapi's documented API, not verified against a real response. Verify and
  adjust once connected to a real account (see Vapi Setup Steps).
- **`sim/chat_sim.py --mode llm` is implemented but not live-exercised** —
  no `LLM_API_KEY` is configured here. Its orchestration is unit-tested
  with a mocked client; the actual model call isn't.
- **Only Anthropic is implemented for `--mode llm`** — OpenAI support was
  scoped out given no live key to verify either against; see
  `docs/DECISIONS.md`.
- **The hallucination check is 7/8, not 8/8** — a real, analyzed
  limitation (product-line ambiguity in a single-product KB), not a bug
  in the check. See `docs/DECISIONS.md`.
- **The KB's grounding-threshold margin is thin** (~0.02, see
  `kb/README.md`/`docs/DECISIONS.md`) — inherited from Q2, directly
  responsible for the hallucination-check failure above.
- **Mock CRM/escalation logging use plain fields, not PII-masked ones** —
  fine for this assessment (synthetic test data only), but a production
  deployment writing real customer data through these tools would need
  the same PII-handling discipline `kb/`'s ingestion pipeline applies.
- **No real telephony transfer capability** — `escalate_to_human` logs a
  "would transfer to `<number>`" entry when no webhook is configured,
  since actually transferring a call requires a live Vapi call in
  progress.
