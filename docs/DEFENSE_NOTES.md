# Defense Notes

Plain-language explanations of the biggest decisions in this project —
what was chosen, why, what else was considered, the trade-off accepted,
and what would change in production. Full detail with dates and file
references is in [`docs/DECISIONS.md`](DECISIONS.md); this file is the
short, spoken-language version for a video walkthrough or an interview.

---

## 1. Chunking strategy (kb/)

**What I chose**: category-aware chunking. FAQ and objection content
gets split into question/answer pairs. Eligibility rules get split by
bullet point. Everything else gets split by heading, then by
sentence-count (80-200 words per chunk).

**Why**: a single fixed chunk size (say, "every 200 words") cuts an FAQ
answer in half half the time, which makes retrieval return a question
with no answer. Splitting by the content's own structure keeps each
chunk a complete, useful unit.

**Alternatives considered**: fixed-size sliding-window chunking (simple,
but breaks FAQ/Q&A pairs); one chunk per whole document (simple, but a
long policy document would dilute the embedding and retrieval would get
worse at finding the specific paragraph a user asked about).

**Trade-off**: category-aware chunking needs a human (or heuristic) to
correctly classify each source document's category first — get that
wrong and the wrong splitting rule applies. It also means more code to
maintain than one universal splitter.

**What I'd change in production**: validate the category classification
itself with a small eval set, since a chunking strategy is only as good
as knowing which rule to apply.

---

## 2. Hybrid retrieval (dense + BM25) instead of dense-only or BM25-only

**What I chose**: combine dense embedding search (finds paraphrases,
"waiting period" ≈ "how long before I'm covered") with BM25 keyword
search (finds exact terms, like a specific policy number or product
name), merged with Reciprocal Rank Fusion.

**Why**: dense-only search sometimes ranks a loosely-related paraphrase
above an exact keyword match. BM25-only search misses a customer who
phrases their question differently than the KB does. Combining both
covers more real customer phrasing than either alone.

**Alternatives considered**: dense-only (simpler, but measurably worse on
exact-term queries in early testing); a re-ranker model on top of dense
results (more accurate potentially, but adds a second model to load and
maintain for a 48-hour build).

**Trade-off**: fusion adds a tuning knob (the RRF constant, k=60 here —
a standard default, not specially tuned) and makes debugging "why did
this result rank #1" slightly harder than a single-method system.

**What I'd change in production**: log both the dense score and the
BM25 score separately per result, not just the fused score, so a
retrieval-quality regression can be traced to which method drifted.

---

## 3. The `grounded=false` threshold (never invent an answer)

**What I chose**: a per-language minimum relevance score
(`KB_MIN_RELEVANCE_SCORE`, calibrated separately for English, Filipino,
Indonesian). Below that score, the system returns "I don't know" instead
of the KB's top result.

**Why**: this is the single most important rule in the whole brief — a
bot that invents an answer is worse than one that says "let me connect
you with someone." The threshold has to be calibrated against real
measured score distributions (what does a genuinely relevant match score
vs. a genuinely irrelevant one), not guessed.

**Alternatives considered**: one global threshold for every language —
tried first, and found empirically too strict for non-English content
(a real Filipino objection scored below the English-calibrated
threshold despite being a correct match). A fixed top-K cutoff instead
of a score threshold (simpler, but doesn't distinguish "1 great match"
from "3 mediocre matches" the way a score does).

**Trade-off**: the calibrated margin is thin (about 0.02 for English,
even thinner for the other two languages) — a slightly different query
phrasing could tip a real match below threshold, or a slightly
off-target result above it. This is called out explicitly as the
retrieval design's biggest open risk, not hidden.

**What I'd change in production**: calibrate against a much larger,
real (not hand-written) query sample, and re-check the threshold
whenever the embedding model or the KB content changes meaningfully.

---

## 4. ASR provider choice (faster-whisper over Deepgram/Azure)

**What I chose**: `faster-whisper` (a local, open-source speech-to-text
model) for Question 4's real-time pipeline, instead of a cloud provider
like Deepgram or Azure Speech.

**Why**: no live API credentials for Deepgram or Azure exist in this
environment, and the brief explicitly names faster-whisper-style local
inference as an acceptable fallback. It also means zero per-minute cost
and no network dependency for the demo.

**Alternatives considered**: Deepgram/Azure (better real-world accuracy
almost certainly, better diarization, but not usable here without a
paid account); doing nothing and treating Q4's ASR as "illustrative
only" like Q3's — rejected once local ASR was confirmed to actually
work, since real local inference is strictly better evidence than a
simulated number.

**Trade-off**: measured a genuine 44.9% word-error-rate against
synthetic TTS voice audio (see `docs/q4_live_nudges/asr_accuracy.md`) —
worse than a production cloud provider would likely give on the same
audio, and definitely not validated against real human speech at all. A
smaller local model (`tiny.en`) also transcribes less accurately than a
larger one, which was a deliberate speed/accuracy trade for a 48-hour
build.

**What I'd change in production**: use a real cloud ASR provider (or at
minimum a larger local model) and validate against real recorded human
speech, not just synthetic TTS audio.

---

## 5. Nudge suppression design (controller.py)

**What I chose**: five layered controls — a confidence floor per signal
type (compliance's is the most permissive; a rare/noisy signal type like
"topic shift" is the strictest), a cooldown per topic, a
semantic-similarity check for a same-type repeat worded differently, an
expiry window, and priority ordering (compliance beats frustration beats
opportunity).

**Why**: a naive "fire every time a keyword matches" nudge system would
flood an agent with repeats and low-value noise — the brief explicitly
lists "excessive low-value alerts" as a rejection condition. Each control
targets a different way a naive system over-fires: the confidence floor
stops weak signals, the cooldown stops the same topic repeating, the
semantic check catches a *different-worded* repeat the cooldown alone
would miss, and priority ordering makes sure a compliance risk is never
buried under three frustration nudges.

**Alternatives considered**: a single global confidence threshold for
every signal type (simpler, but treats "customer might be a little
annoyed" the same as "agent just broke a compliance rule," which is the
wrong trade-off — better to over-flag compliance and under-flag mild
frustration than the reverse).

**Trade-off**: five separate controls is more to tune and reason about
than one. It also means a genuinely important-but-late repeat (a
compliance issue mentioned again 20 seconds after the first mention,
still within cooldown) gets suppressed — the cooldown window is a
judgment call, not a provably-correct number.

**What I'd change in production**: measure real agent feedback (did they
find the nudge useful, did they ignore it) and tune the thresholds
against that signal instead of my own judgment call.

---

## 6. LLM choice (Claude Haiku, Anthropic-only)

**What I chose**: Claude Haiku for both the voice-agent's optional
LLM-mode simulator and Q4's LLM signal layer, via the `anthropic` SDK
only — no OpenAI/other provider implemented in code.

**Why**: Haiku is fast and cheap enough to call frequently (every ~5
seconds in Q4's sliding-window layer) without becoming a latency or cost
problem, while still being capable enough for structured JSON output
with a defined schema. Implementing one provider well within a 48-hour
window was judged better than implementing two shallowly.

**Alternatives considered**: OpenAI (equally viable technically, not
implemented — a scope decision, not a technical rejection); a
larger/more capable model (Sonnet/Opus) for the LLM layer — rejected as
unnecessary cost/latency for a structured-JSON classification task this
narrow.

**Trade-off**: single-provider means no fallback if Anthropic has an
outage, and no side-by-side comparison of which model produces better
signal-extraction judgments.

**What I'd change in production**: add a second provider as a fallback
(not necessarily OpenAI specifically — whichever the org already has a
relationship with), and A/B test model choice against a real accuracy
metric before committing to one for the compliance-critical signal
path specifically.

---

## 15 Likely Interview Questions

**1. Why hybrid retrieval instead of just embeddings?**
Because pure embedding search sometimes ranks a paraphrase above an
exact keyword/product-name match. BM25 catches what embeddings miss, and
fusing them covers more real phrasing than either alone.

**2. How do you know your grounding threshold is right?**
I calibrated it against real measured score distributions from actual
KB queries, not a guessed number — and I say plainly that the margin is
thin (~0.02) and would need a bigger calibration sample in production.

**3. What happens if the KB has no answer?**
The system returns `grounded=false` and a fallback message instead of
the top (irrelevant) result — verified by an automated test in every
voice component, not just a prompt instruction.

**4. Why didn't you use a real phone number for Q1?**
No live Vapi account exists in this environment. The webhook, tools,
scoring, and escalation are all real code, tested end-to-end via a
simulator — but I say directly in the README that there's no callable
number right now, rather than implying there is one.

**5. What's the biggest bug you found while building this?**
Merging Q3's multilingual KB records into the shared index silently
broke Q1's English hallucination check (88% → 62% pass rate) because
searches weren't language-filtered. Fixed with an explicit language
filter everywhere, and I have a regression test locking it in.

**6. Why faster-whisper instead of a cloud ASR provider?**
No live Deepgram/Azure credentials exist here, and the brief names local
inference as an acceptable fallback. It's real model inference on real
audio, with a real measured (if imperfect — 44.9% WER) accuracy number,
not a simulated one.

**7. Is your 44.9% ASR word-error-rate concerning?**
It's real, but I traced *why* it's that high: number-format mismatches
(spelled-out numbers vs. digits) and a stereo-channel-bleed
hallucination artifact both inflate it, and I documented both with
actual transcript evidence rather than just reporting a number.

**8. How do you stop the nudge system from spamming the agent?**
Five layered controls: a per-signal-type confidence floor, a per-topic
cooldown, a semantic-similarity duplicate check, an expiry window, and
priority ordering. The "noisy/ambiguous call" test scenario specifically
verifies a low-confidence signal gets suppressed, not just absent.

**9. How is Q4 actually "real-time" and not analyzing a recording after
the fact?**
Audio is chunked and replayed at real (or sped-up-for-testing) pace;
each chunk only becomes visible to the ASR/signal/nudge pipeline once
it's "played" — the pipeline never sees audio from later in the call
before that point in time.

**10. Why does compliance have the lowest confidence threshold?**
Because a false negative (missing a real compliance risk) is worse than
a false positive (flagging something that turns out fine) in that
specific domain — better to over-flag and let a human dismiss it.

**11. What's your biggest known limitation?**
No native-speaker or compliance/legal review of any Filipino or Bahasa
Indonesia content — everything was AI-drafted and needs that review
before touching a real customer. I say this directly rather than
implying the localization is production-ready.

**12. How would this scale to 10x call volume?**
Right now it wouldn't cleanly — one process holds one ASR model
instance and one in-process WebSocket broadcaster. Production would need
a worker pool behind a real job queue, and per-call state in
Redis/similar instead of in-process Python objects. This is written up
in detail, not glossed over.

**13. Why did you rebuild Q4 mid-assessment instead of keeping the
simpler version?**
The first version was a text-only simulation with a modeled ASR latency
number. Once I confirmed local TTS and local ASR both actually work here
with zero live credentials, a real audio pipeline was strictly better
evidence for the same amount of remaining time, so I rebuilt it.

**14. How do you know your test coverage is real and not just
"assert True"?**
Every component's tests exercise real code paths — real KB retrieval,
real tool dispatch, real signal-extraction rules, real (if small) ASR
model inference — not mocked-out logic standing in for the thing being
tested. Placeholder tests were replaced as soon as real logic existed,
per the project's own rule.

**15. What would you do differently if you had another week?**
Wire in one real telephony/ASR/TTS provider end-to-end for at least one
component to validate the whole stack against real audio and a real
call, get native-speaker review on the Filipino/Bahasa content, and
build the continuous-eval-in-CI pipeline described in the production
plan instead of running these evals by hand.
