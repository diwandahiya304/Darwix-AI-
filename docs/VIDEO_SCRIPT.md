# Video Walkthrough Script (10-12 minutes)

Timed for a screen-recorded walkthrough. Each section names the exact
command to run or file to show on screen, plus the talking points. Total
target: ~11 minutes — pad the demo sections if things run fast, trim
the limitations section if running long (it's the most compressible).

---

## 0:00-0:45 — System Overview

**Say:** "This is a knowledge-grounded voice AI platform covering all
four parts of the assessment. Everything shares one retrieval API built
in Question 2 — the voice agent in Question 1 grounds every answer
against it, and the two multilingual bots in Question 3 reuse the same
index with language-tagged records. Question 4 is a separate real-time
pipeline that turns live call audio into in-call nudges. The single
rule that runs through everything: the bot has to say 'I don't know'
instead of inventing an answer, and that's checked by an automated test
in every component, not just prompted for."

**Show:** the root `README.md`'s top table (the 4 folders) and the
mermaid architecture diagram.

---

## 0:45-2:00 — Architecture and Key Design Decisions

**Say:** "A few decisions mattered more than the others. First: the
knowledge base uses hybrid retrieval — dense embeddings plus BM25,
fused with reciprocal rank fusion — because pure dense search missed
exact-terminology matches like policy numbers, and pure BM25 missed
paraphrases. Second: the grounding threshold isn't one global number —
English, Filipino, and Indonesian each have their own calibrated
threshold, because I found empirically that the same threshold that
worked for English was too strict for non-English content. Third, and
this one I found the hard way: once I merged the multilingual KB
records into the same index as English, Question 1's hallucination
check regressed from 88% to 62% pass rate, because it was searching
across all languages unfiltered. The fix was an explicit language
filter on every call — that's now enforced everywhere, and it's
logged in the decisions file as a real regression I found and fixed,
not a hypothetical risk."

**Show:** `docs/DECISIONS.md` scrolled to the "cross-lingual ranking
unreliable" and "voice_agent KB client now explicitly filters" entries.

---

## 2:00-3:30 — KB and Retrieval Design (live demo)

**Say:** "Let me show retrieval actually working." Run:
```bash
make kb-search q="what is the waiting period for pre-existing disease cover"
```
**Say:** "That's a real query against the real index — hybrid dense +
BM25, and you can see the citation: which source file, which version.
Every record is traceable back to where it came from — that's the
`record_id`/`source_ref`/`version` schema the brief asked for." Then:
```bash
make kb-eval
```
**Say:** "This runs 13 queries against the live index and reports hit at
1, hit at 3, and out-of-scope rejection rate — all 1.00 right now,
latency P50 74ms, P95 103ms, both well under budget."

**Show:** `docs/q2_kb/retrieval_test_results.md`'s table.

---

## 3:30-5:00 — Voice Agent Flow (Q1)

**Say:** "The voice agent's system prompt has zero facts in it — I have
a test that asserts that directly. Every fact comes from a
`search_knowledge_base` tool call at answer time. Qualification scoring,
escalation, and lead creation are deterministic code, not the LLM
guessing — that's important for auditability in an insurance context."
Run:
```bash
make voice-agent-sim
```
**Say:** "This runs all 5 required scenarios — cooperative, objection,
incomplete and conflicting details, out-of-scope, human escalation —
against the real webhook and the real KB, no mocking. Let's look at the
objection transcript."

**Show:** `recordings/voice_agent/b_objection.md` — point out one
grounded answer (with citation) and one fallback (KB has no answer, bot
says so).

**Say honestly:** "There's no live Vapi account in this environment, so
these are simulated calls against real code, not phone calls — that's
stated plainly in the README, not hidden."

---

## 5:00-6:30 — Multilingual Handling (Q3)

**Say:** "Two markets reuse the same KB and retrieval code, with
language-tagged records and their own calibrated grounding thresholds.
Philippines is Taglish — English, Tagalog, and natural code-switching,
register-mirrored so a formal 'po/opo' customer gets a formal reply and
a casual customer gets a casual one. Indonesia is Bahasa Indonesia with
OJK-style compliance guardrails baked into the system prompt — no
threats, no third-party disclosure, restricted calling hours." Run:
```bash
make multilingual-sim-ph
```
**Show:** one PH transcript, pointing at a Taglish line and its grounded
answer. Then:

**Say:** "Localization, not translation, matters here — three examples
per market are in `docs/q3_multilingual/localization_examples.md`
showing adapted phrasing, not literal translation." **Show:** one
example from that file.

**Say honestly:** "The ASR section for Q3 is illustrative only — no
Deepgram or Azure credentials, and no real audio was synthesized for
these two markets, so there's no WER number here I can call real. That's
stated clearly at the top of the ASR report, not glossed over."

---

## 6:30-9:00 — Live Nudges (Q4, live demo)

**Say:** "This is the one I want to spend the most time on, because it's
genuinely real, not simulated. I generate real stereo call audio locally
with a TTS engine, replay it in real, paced chunks — never analyzing a
finished recording — and run real local speech-to-text inference on it
per rolling window as the audio plays." Run:
```bash
make q4-sim scenario=b_compliance_gap
```
**Say, while it plays:** "Watch the transcript print in real time on the
left, and nudges fire on the right as they're detected — that's the
agent saying an oversold guarantee phrase, and a moment later a missing
mandatory disclosure at the point the agent tries to close." **Show:**
the compliance nudge lines printing to stderr.

**Say:** "Every nudge decision — fired or suppressed — is logged with a
reason. Confidence thresholds are per signal type, there's a per-topic
cooldown, and a semantic-similarity check that catches a repeat worded
differently. Priority ordering is compliance first, then frustration,
then opportunity." **Show (optional, if time):**
```bash
make q4-demo
```
opened in a browser — the live dashboard with the transcript, the
frustration meter, and the active-nudge queue with expiry countdowns.

**Say:** "Quality: 3 runs per scenario against timestamp-bounded ground
truth — 100% recall, 83% precision, and the one recurring false positive
is explained in the report, not buried: a casual 'sounds good'
collides with the buying-signal keyword list."

**Show:** `docs/q4_live_nudges/quality_report.md`'s table and the
"recurring false positive, explained" section.

---

## 9:00-10:00 — Error / Fallback Cases

**Say:** "Every component has a real fallback path, tested, not just
prompted for." Rapid-fire, showing each:
- Q1: `recordings/voice_agent/d_out_of_scope.md` — polite decline, never
  half-answers.
- Q3: the per-language grounding threshold — below it, the bot states it
  doesn't have that information, in the customer's own register, never
  switching to English unexpectedly.
- Q4: `d_noisy_ambiguous` scenario — filler, hesitant speech produces
  zero or one nudge, not a flood of false positives; a low-confidence
  intent-shift signal is genuinely suppressed by the controller, visible
  in the suppressed-log toggle.

---

## 10:00-11:00 — Limitations and Production Improvements

**Say plainly:** "The honest gaps: no live Vapi account, so Q1/Q3 have
no callable number and no real recorded calls. Q3 has no synthesized
audio at all, so its ASR numbers are illustrative only. Q4's ASR is
real, but I measured a real 45% word-error-rate against synthetic voice
audio, and traced it to two specific causes — number formatting and a
stereo-bleed hallucination artifact — both documented with actual
transcript evidence, not hand-waved. Q4 also doesn't scale to 10x
concurrent calls without a real queue and pub-sub backbone — that's
detailed in the limitations doc, not glossed over."

**Say:** "Production plan: wire in real Vapi/Deepgram/Azure credentials
behind the existing interfaces — no code shape change needed. Add a
continuous eval pipeline in CI instead of an on-demand report. Cost and
PII-compliance hardening before any of this touches a real customer.
And critically, native-speaker and compliance review of every Filipino
and Bahasa Indonesia string — none of that has happened yet, and I say
so directly rather than implying it has."

**Show:** the README's Production Improvement Plan list.

---

## 11:00-11:30 — Close

**Say:** "Everything shown here is real, tested code — 222+ tests across
four components, all passing, all runnable with `make test`. Every
number in this walkthrough came from a report file under `docs/`, not
eyeballed. Where something isn't real — no live Vapi, no live ASR
provider, illustrative-only numbers — I've said so in the same breath as
the result, because that's the standard I held this whole build to."
