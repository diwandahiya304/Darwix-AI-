# Q4 Live Nudges: Real ASR Accuracy (faster-whisper, tiny.en)

**This is a genuinely measured WER/CER**, not the illustrative-only numbers in `docs/q3_multilingual/asr_report.md` — Q4's ASR is a real local model (faster-whisper) and the TTS script text is an exact reference transcript, so WER/CER against it is a real, reproducible measurement of this pipeline.

**Caveat**: measured against synthetic (pyttsx3) TTS voice audio, not real human speech — real speakers' prosody/disfluencies/recording conditions would likely produce different (plausibly worse) numbers. This is real, not illustrative, but it is not a claim about real-call ASR accuracy.

**Mean WER: 44.9%, mean CER: 22.9%** across 8 (scenario, speaker) transcript pairs.

| Scenario | Speaker | WER | CER |
|---|---|---|---|
| a_missed_cross_sell | agent | 46.8% | 27.2% |
| a_missed_cross_sell | customer | 47.1% | 19.4% |
| b_compliance_gap | agent | 36.6% | 26.3% |
| b_compliance_gap | customer | 70.0% | 31.4% |
| c_rising_frustration | agent | 39.3% | 16.0% |
| c_rising_frustration | customer | 29.4% | 13.7% |
| d_noisy_ambiguous | agent | 41.7% | 25.2% |
| d_noisy_ambiguous | customer | 48.4% | 24.0% |

Full reference/hypothesis text pairs: `docs/q4_live_nudges/asr_accuracy.json`.

## Why the WER is this high (checked against the actual transcripts, not assumed)

Inspecting the reference/hypothesis pairs directly surfaces three distinct,
real causes — this is not a scoring bug:

1. **Number formatting mismatch.** The reference script writes numbers as
   words ("twelve thousand rupees"), and faster-whisper transcribes
   numbers as digits ("12,000 rupees"). `jiwer`'s word-level WER counts
   every one of these as a full substitution error even when the
   transcription is semantically correct. This alone inflates every
   premium-amount line's error count substantially and was not
   normalized away — doing so honestly would require a
   number-normalization pass before scoring, which this report does not
   apply (a real methodological limitation, not a hidden fix).
2. **Stereo-channel bleed causing hallucinated filler.** The hypothesis
   text repeatedly contains a bare "You" interjected between real
   sentences on the *agent* channel specifically — e.g. "Hi, this is
   Asha calling a your health insurance renewal. You You Good." This is
   faster-whisper hallucinating on near-silent/bleed-through audio
   during the other channel's speaking turns, not a genuine word the
   agent said. This is a real, previously-undocumented ASR artifact
   found while building this report.
3. **Genuine transcription errors** on the small (`tiny.en`) model with
   robotic TTS-voice audio: "guaranteed returns" → "guaranteed return.",
   "full approval today" → "full of proof. available today.", and the
   already-documented mid-word cut ("proceed" → "prop-", see
   `docs/DECISIONS.md`).

**Takeaway**: a production deployment would need (a) number
normalization before WER scoring or before signal-matching, (b) a larger
whisper model (`base`/`small` instead of `tiny.en`) or VAD-based silence
gating to suppress the hallucinated-filler artifact, and (c) real human
speech to know whether error rates this high are specific to robotic TTS
audio or would persist on real calls. All three are listed in
`docs/q4_live_nudges/limitations.md`'s production-readiness list.
