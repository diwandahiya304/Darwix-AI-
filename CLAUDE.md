# CLAUDE.md — Project Constitution

This file governs how Claude Code works in this repository, for the whole 48-hour
assessment. Every session, on every component, follows these rules without
being reminded. If a request conflicts with this file, follow this file and
flag the conflict to the user.

## 0. What this repo is

A 48-hour AI Engineer take-home assessment (see `ai_assignment.pdf` at repo
root for the original brief) with four connected parts:

| Folder          | Question | Objective                                                              | Depends on |
|------------------|----------|-------------------------------------------------------------------------|------------|
| `voice_agent/`  | Q1       | Knowledge-grounded voice agent for one qualification/reminder use case | `kb/` (Q2) |
| `kb/`           | Q2       | Production-ready knowledge base: ingest, clean, chunk, index, retrieve | —          |
| `multilingual/` | Q3       | Native-language voice bots for Philippines (Taglish) + Indonesia (Bahasa) | `kb/` (optional reuse) |
| `live_nudges/`  | Q4       | Real-time call insights and nudges during a live call                 | may reuse recordings from Q1/Q3 |

Build order matters: **`kb/` (Q2) first**, because Q1 must retrieve from it
rather than hardcode FAQs/policies in a system prompt. `multilingual/` and
`live_nudges/` can start once `kb/` and `voice_agent/` have a working core
loop. Do not parallelize into all four folders before Q2's retrieval API is
callable — Q1 grading explicitly penalizes a "disconnected knowledge base and
voice bot."

## 1. Stack and environment

- **Python 3.11** everywhere. No other language runtimes.
- **FastAPI** for every HTTP surface (KB retrieval API, voice agent webhook
  handlers, nudge delivery endpoint). **pydantic** (v2) for every data model
  and settings object — no bare dicts for anything that crosses a function or
  API boundary.
- **pytest** for all tests. No other test runner.
- Dependency management: a single pinned root `requirements.txt`. Use `uv pip
  install -r requirements.txt` if `uv` is available, else plain `pip`. When a
  component needs a new dependency (an ASR SDK, a vector store client, an LLM
  SDK), add it to the root `requirements.txt` pinned to an exact version, and
  record *why that library* in `docs/DECISIONS.md` (alternatives considered).
  Do not leave dependencies unpinned (no bare `fastapi`, always
  `fastapi==x.y.z`).
- Package layout per component: `app/` (importable code) + `tests/`
  (pytest). Component READMEs describe the run command; the Makefile is the
  single source of truth for *how* to run it.

## 2. Secrets and data safety

- **Never commit secrets, API keys, tokens, or real customer data.** All
  configuration comes from environment variables loaded via `.env` (never
  committed). `.env.example` is the living template — every time a new env
  var is introduced anywhere in the repo, add it to `.env.example` in the
  same change, with a placeholder value and a one-line comment on what it's
  for.
- `data/raw/` and `recordings/` are gitignored by default because they are
  the most likely place real customer data or real call audio ends up. If a
  file in either directory is confirmed synthetic/sample data with no PII,
  it may be force-added deliberately — never by a wildcard `git add`.
- `data/processed/` is tracked, but nothing goes in it until it has been
  through the PII scrub step described in `kb/README.md`. When in doubt,
  treat content as containing PII and keep it out of git.
- Before any commit, review `git status` output for anything that looks like
  a credential, key, or recording, even if the filename looks innocuous.

## 3. Priority: reliable core over polish

- Ship the smallest working end-to-end path for each question before adding
  anything optional (business actions in Q1, extra nudge channels in Q4,
  extra accents in Q3, etc.). A working, ungrounded-answer-safe, measured
  core beats a feature-rich but flaky one.
- Do not add infrastructure (queues, extra services, extra databases,
  frontend frameworks) unless a requirement in the assignment brief cannot be
  met without it. If tempted to add something not asked for, write a one-line
  note in `docs/DECISIONS.md` explaining why it was skipped instead of just
  skipping it silently.
- Optional items (Q1's business action, Q3's extra polish) only get built
  after the required core evidence for that question is already working and
  measured.

## 4. Definition of Done (every component, every feature)

A change is not done until all four of these exist in the same commit/PR:

1. **README section** — the component's `README.md` documents what was
   built, how to configure it, and how to run it.
2. **Makefile target** — a runnable `make <target>` command exists at the
   repo root (e.g. `make test-kb`, `make run-kb`). No feature is "done" if
   the only way to exercise it is a command typed from memory.
3. **At least one test** — a `pytest` test under that component's `tests/`
   directory. Placeholder tests (`test_placeholder.py`) get replaced by real
   tests as soon as real logic exists; a placeholder must never be the only
   test left once a component has real behavior.
4. **Measurement** — anything measurable (retrieval accuracy, latency
   P50/P95, false-positive rate, ASR quality) is captured as JSON and/or
   Markdown under `docs/q{N}_*/`, not just eyeballed and left in a terminal
   scrollback.

## 5. Per-question required evidence (from the assignment brief)

Treat these as acceptance criteria, not suggestions — grading explicitly
rejects submissions missing them.

**Q2 — `kb/`**
- Document schema with `record_id, title, content, category, source,
  version, PII` (see the brief's field example) — every record traceable to
  a source.
- Chunking strategy, metadata structure, taxonomy, versioning, embedding/
  indexing approach, retrieval/ranking logic, and citation method documented
  in `kb/README.md`.
- PII identified and protected (never left in `data/processed/` or in KB
  records marked `PII: false`).
- At least **5 retrieval test queries** in `docs/q2_kb/retrieval_tests.md`
  (or `.json`), each with: user question, retrieved chunk/record, source
  reference, relevance explanation, verdict (correct / partially correct /
  incorrect).
- A working connection from this KB to the Q1 voice bot (or, at minimum, a
  simple retrieval interface) — "disconnected KB and voice bot" is an
  explicit rejection condition.

**Q1 — `voice_agent/`**
- Voice platform configured with the provided script/business rules for
  **one** use case (health-insurance lead qualification, business-loan
  qualification, candidate screening, insurance renewal, or loan pre-due
  reminder).
- Retrieves from `kb/` at answer time — FAQs/objections/policies are **not**
  hardcoded into the system prompt.
- Conversation flow covers: qualification logic, grounded objection
  handling, unsupported-question fallback, human escalation.
- Callable number or web calling interface.
- **≥3 recorded test calls** with transcripts + results in
  `recordings/voice_agent/` and `docs/q1_voice_agent/`, covering: cooperative
  customer, objection, incomplete/conflicting details, out-of-scope
  question, human-assistance request (five scenario types — three calls
  minimum can combine scenarios, but all five must be evidenced somewhere).
- The bot states when information is unavailable — it must never invent an
  answer. This is the single most important behavioral rule in the whole
  repo (see §6).

**Q3 — `multilingual/`**
- Philippines bot: life insurance or bancassurance sector; English +
  Filipino/Tagalog + natural Taglish; correct domain terms (premium, policy,
  beneficiary, rider, lapse, coverage, bank referral).
- Indonesia bot: multifinance/consumer finance sector; formal + colloquial
  Bahasa Indonesia + finance English loanwords + **at least one regional
  accent** outside standard Jakarta speech; correct domain terms (cicilan,
  tenor, denda, DP, jatuh tempo, angsuran, pembiayaan).
- Localization, not translation: ≥3 examples per market in
  `docs/q3_multilingual/localization_examples.md` showing adapted (not
  literally translated) phrasing.
- ASR report per market: provider/model, languages tested, code-switching
  behavior, approximate quality, observed errors, regional-accent
  performance (Indonesia).
- Native TTS voices where possible; compromises documented.
- **2 recorded calls per market** in `recordings/multilingual/{philippines,
  indonesia}/`, covering: cooperative customer, sector objection, mixed
  English/finance terms, colloquial speech, human escalation, and (Indonesia)
  regional accent.
- Fallback stays in the customer's language/register — no unexpected
  English switching.

**Q4 — `live_nudges/`**
- Input is streamed live audio or a recording replayed at real-time speed in
  chunks — **analyzing a completed recording after upload does not qualify.**
- Streaming ASR with per-chunk transcription latency reported, agent/
  customer separation where possible.
- Signal extraction: intent/topic shifts, compliance/risk, sentiment/
  frustration, buying signals, missed opportunities, callback needs.
- Nudges are short and actionable, delivered via dashboard, WebSocket,
  webhook, polling API, or CLI.
- **End-to-end latency measured and reported** (audio received →
  transcription → signal detection → nudge generation → display), with
  **P50/P95** plus per-component latency (ASR, signal extraction, LLM,
  delivery), saved to `docs/q4_live_nudges/latency_report.md`/`.json`.
- Nudge control implemented: confidence thresholds, duplicate suppression,
  cooldowns, topic grouping, priorities, expiry, or repetition rules — plus
  an approximate false-positive analysis in `docs/q4_live_nudges/`.
- Required test coverage: missed cross-sell, skipped disclosure/risky
  statement, rising frustration, noisy/ambiguous call with unnecessary
  nudges suppressed. At least one compliance example and one
  missed-opportunity example.
- Explain limitations at 10x scale and with noisy audio in
  `docs/q4_live_nudges/` (feeds the root README's Known Limitations /
  Production Improvement Plan too).

## 6. Grounding rule (applies everywhere, not just Q1)

If the knowledge base has no record that answers a question, the bot says so
explicitly (e.g. "I don't have that information — let me connect you with a
human agent" style fallback) instead of generating a plausible-sounding
answer. This is checked by tests, not just prompted for: every voice-agent
and multilingual component must have at least one test asserting the
unsupported-question fallback fires when retrieval returns nothing above
the relevance threshold. A hallucinated answer anywhere is treated as a
correctness bug, not a tuning issue.

## 7. Measurement conventions

- Every measurable result lives under `docs/q{N}_*/` as JSON (for
  machine-readable numbers) and/or Markdown (for the human-readable
  narrative + table). Don't leave results only in a notebook, a terminal, or
  a chat transcript.
- Latency is always reported as **P50 and P95**, never average-only.
- Retrieval and nudge quality are always reported with explicit
  correct/partially-correct/incorrect (retrieval) or true/false-positive
  (nudges) verdicts — not a vague "works well."
- File naming: `docs/q{N}_*/<topic>.md` for narrative, `<topic>.json` for
  raw numbers when both are useful (e.g. `latency_report.md` +
  `latency_report.json`).

## 8. Decisions log

Every non-trivial design choice (KB chunking strategy, embedding model,
voice platform, ASR/TTS providers, vector store, nudge suppression rules,
use-case selection for Q1, sector selection for Q3) gets an entry in
`docs/DECISIONS.md` with: date, decision, reason, alternatives considered.
The user must be able to defend every choice in a video walkthrough from
this file alone — write entries assuming that's the test.

## 9. Testing conventions

- One `tests/` directory per component, run individually via its Makefile
  target and collectively via `make test`.
- Tests should be fast and hermetic — mock external APIs (LLM calls, ASR/TTS,
  telephony webhooks) rather than making live network calls in CI/local test
  runs. Live-integration smoke tests (if any) are opt-in via a separate
  Makefile target, never part of `make test`.
- Replace `test_placeholder.py` in a component as soon as that component has
  real logic — a placeholder assertion (`assert True`) must not coexist with
  real, untested behavior.

## 10. Workflow checklist for every change

Before considering any feature complete, confirm:
- [ ] README section updated (component + root results section if relevant)
- [ ] Makefile target exists and runs
- [ ] Test added/updated and passing
- [ ] Measurement captured in `docs/q{N}_*/`
- [ ] `.env.example` updated if new env vars were introduced
- [ ] No secrets/PII in the diff (`git status` reviewed)
- [ ] `docs/DECISIONS.md` updated if a non-trivial choice was made
- [ ] Grounding/fallback behavior still covered by a test, if touched

## 11. What NOT to do

- Don't hardcode KB content into a voice agent's system prompt — that's an
  explicit rejection condition for Q1.
- Don't translate literally for Q3 — localize tone, terminology, and
  fallback per market.
- Don't compute nudges after the call ends — Q4 requires in-call latency,
  measured.
- Don't add unpinned dependencies, don't add frameworks/services beyond
  FastAPI+pydantic+pytest without a documented reason, don't commit anything
  under `data/raw/` or `recordings/` without confirming it's PII-free.
