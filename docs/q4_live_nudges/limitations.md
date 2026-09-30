# Q4 Live Nudges: Limitations at Scale and With Noisy Audio

> File location note: asked for at `docs/q4_limitations.md`; placed under
> `docs/q4_live_nudges/` per CLAUDE.md's own convention instead — see
> `architecture.md`'s note at the top for the same flagged conflict.

## What this implementation actually demonstrates

Every stage is real: real stereo WAV audio (synthesized locally via
pyttsx3 — no TTS provider), a real chunked/paced replay
(`app/audio_io.py`), real faster-whisper inference per rolling window
(`app/streaming_asr.py`), real deterministic signal rules plus a real
(if usually unconfigured, since no Anthropic key exists in this
environment) Claude Haiku layer, and a real nudge controller with
measured, logged suppression decisions. What follows is what was
actually found to break while building and testing this, and where the
honest gaps are.

## At 10x concurrent call volume

- **Concurrent ASR streams**: each call currently loads/uses its own
  `StreamingASR` instance, but faster-whisper's model is a process-wide
  singleton (`streaming_asr._load_model`) shared across calls — fine for
  1 call, but 10 concurrent calls would serialize on that one model's
  CPU inference, directly increasing `asr` latency for every call
  proportionally to the others running. **Mitigation**: run several
  worker processes (or a small pool) each holding one model instance,
  route calls to workers round-robin; or batch multiple calls'
  windows into one `model.transcribe()` call if the backend supports
  batched inference — not implemented here.
- **LLM rate limits/cost**: `llm_min_interval_seconds` (default 5s)
  already throttles one call's Haiku usage, but 10 concurrent calls each
  independently respecting their own 5s floor multiplies total request
  rate 10x with no shared budget — a real provider rate limit or cost
  cap would need a shared token-bucket across all active calls, not a
  per-call interval. **Mitigation**: a shared rate limiter (even an
  in-process semaphore/token bucket would help locally; Redis-backed for
  multiple processes), and/or a smaller/cheaper model for the common
  case with Haiku reserved for escalation.
- **WebSocket fan-out**: `app/broadcaster.py` is a single in-process
  pub/sub with an unbounded per-subscriber `queue.Queue` — correct for
  one server process and a handful of dashboard viewers, but does not
  fan out across multiple server processes/machines, and a slow/stuck
  WebSocket client's queue would grow unboundedly. **Mitigation**: a
  real pub/sub backbone (Redis Streams/Pub-Sub, or Kafka if durability/
  replay matters) between the pipeline and however many WebSocket
  server processes are running, with bounded queues and backpressure
  (drop-oldest or disconnect a client that can't keep up).
- **Queueing**: there is no queue at all right now — `POST /start` runs
  the call synchronously on a background thread and rejects a second
  concurrent start outright (see `app/main.py`'s 409 response). At scale
  this needs a real job queue (Celery/RQ/Kafka-consumer-per-call) so
  calls queue rather than get rejected, with worker autoscaling behind
  it.
- **Per-call state storage**: `NudgeController`/`SignalExtractor`/
  `LLMSignalExtractor` state lives only in that call's Python objects,
  in that process's memory — it doesn't survive a process restart, and
  isn't visible to any other process (so a second dashboard server
  couldn't see call state from the first). **Mitigation**: externalize
  per-call state (disclosure-given, open cross-sell topics, cooldown
  timestamps) to Redis or a small database keyed by call_id, so any
  worker/process can pick up or observe any call.

## With noisy/real audio

- **ASR errors are real and already observed, not hypothetical.**
  Building this surfaced two genuine ASR artifacts on real (if
  synthetic-voice) audio: (1) faster-whisper's fixed-length windows can
  split a sentence across two consecutive final segments (mitigated here
  with a short rolling text buffer for compliance-phrase matching — see
  `docs/DECISIONS.md`), and (2) a word split exactly at a window
  boundary can come out garbled ("proceed" -> "prop-") even with that
  buffer, because the *audio itself* was cut mid-word before ASR ever
  saw it, which no amount of text-level buffering fixes. **Mitigation**:
  voice-activity-detection (VAD) driven window boundaries (cut on
  silence, not a fixed clock) instead of a fixed `asr_window_ms` would
  avoid cutting mid-word far more often than a fixed timer does; this
  wasn't implemented here to keep the windowing logic simple and
  auditable within the time available.
- **Confidence gating already exists but is keyword-derived, not
  ASR-derived.** faster-whisper does expose a token-level confidence/
  log-probability that this repo doesn't currently read or thread
  through — a low-confidence ASR hypothesis is currently treated exactly
  like a high-confidence one for keyword matching. **Mitigation**: surface
  faster-whisper's segment `avg_logprob`/`no_speech_prob` and require a
  minimum before trusting a segment's text for compliance-critical
  checks specifically (where a false negative — missing a real risky
  statement — is worse than a false positive).
- **Diarization drift**: the stereo-channel-split diarization used here
  is exact by construction (two separately-synthesized channels) and
  cannot represent real-world diarization drift (a real ASR/diarization
  pipeline occasionally misattributing a turn, especially with
  crosstalk/overlap). The scenario d noise test (`d_noisy_ambiguous.wav`,
  band-limited synthesized background noise) demonstrates degraded
  *content* recognition under noise, but not diarization failure
  specifically. **Mitigation**: multi-utterance confirmation (only act on
  a signal once it's corroborated by 2+ segments attributed to the same
  speaker, not just 1) would reduce the blast radius of a single
  misattributed turn; not implemented as a general mechanism here beyond
  frustration's existing 2-hit rolling-window rule.
- **Background noise measurably degrades this pipeline** — that's the
  whole point of scenario d, and the quality report
  (`quality_report.md`) reports real precision/recall numbers on it, not
  assumed ones.

## What a real (measured) ASR accuracy number surfaced

`docs/q4_live_nudges/asr_accuracy.md` computes a genuine WER against the
exact TTS script text (not illustrative, unlike `multilingual/`'s ASR
report) — mean WER 44.9%, mean CER 22.9%. Inspecting *why* surfaced two
further, previously-undocumented real issues:

- **Number-format mismatch inflates WER on every amount mentioned**
  ("twelve thousand rupees" vs. faster-whisper's "12,000 rupees") — a
  real scoring-methodology gap (no number normalization applied before
  WER), not a transcription failure, but it means this WER number
  overstates *semantic* error relative to a normalized comparison.
- **Stereo-channel bleed hallucinates a filler "You"** on the agent
  channel during the customer's speaking turns — faster-whisper
  producing a word from near-silent/bleed-through audio rather than
  correctly emitting nothing. This is a genuine ASR failure mode that a
  larger model or VAD-based silence gating would likely reduce.

## What would need to change before this is production-grade

1. VAD-driven (not fixed-timer) ASR window boundaries.
2. A shared rate limiter and a real job queue in front of the LLM layer
   and the call-runner, respectively.
3. External (Redis/DB-backed) per-call state instead of in-process
   Python objects, and a real pub/sub backbone for WebSocket fan-out
   across multiple server processes.
4. ASR confidence signals (log-probability) threaded into the
   compliance-checking path specifically.
5. A real diarization/ASR provider (Deepgram, Azure) evaluated against
   real (not synthesized) call recordings — this repo's numbers are
   honest about what they measure (a specific local model on specific
   synthesized audio), not a claim about real-world ASR accuracy.
