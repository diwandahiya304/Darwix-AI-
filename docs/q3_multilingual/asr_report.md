# ASR Report (Q3)

## Read this first

**No ASR provider credentials (Deepgram, Azure Speech, Google STT, OpenAI gpt-4o-transcribe) exist in this development environment, and no real audio recordings of native speakers exist either.** Every number below from `illustrative-loanword-drop-pattern` / `illustrative-phonetic-noise-pattern` is a **synthetic, hand-designed stand-in** for a plausible ASR failure mode — dropping out-of-vocabulary finance loanwords, and generic phonetic noise — used to prove the benchmark harness itself (WER/CER via `jiwer`, code-switching handling, named-term accuracy) computes correctly. **They are not measurements of Deepgram, Azure, or any real provider**, and must not be read as such.

## Real provider configuration status

| Provider | Status |
|---|---|
| deepgram-nova-3 | not run — DEEPGRAM_API_KEY not configured in this environment |
| azure-speech | not run — AZURE_SPEECH_KEY/AZURE_SPEECH_REGION not configured in this environment |

## Candidate providers (from public documentation, not measured here)

- **Deepgram nova-3**: supports `language=multi` for automatic code-switch detection, or explicit language codes. The brief lists "tl" for Tagalog — note this repo's KB/pipeline uses "fil" (Filipino, matching Azure's locale code) as the language tag; these are close but not identical, and this discrepancy is flagged, not resolved, pending native-speaker/provider-docs review.
- **Azure Speech**: locales `fil-PH` (Filipino), `id-ID` (Indonesian), `en-PH` (Philippine English) per the brief. Azure also supports custom speech models for domain vocabulary, which would help with finance loanwords/named terms — not configured here.
- **Google STT / OpenAI gpt-4o-transcribe**: not implemented in `providers.py` at all (scope decision, same reasoning as voice_agent's single-provider LLM-mode choice) — see docs/DECISIONS.md.

## Benchmark results (illustrative providers only — see warning above)

| Utterance | Market | Category | Provider | WER | CER | Code-switch preserved | Named-term accuracy | Missed terms |
|---|---|---|---|---|---|---|---|---|
| ph_cooperative | philippines | cooperative | illustrative-loanword-drop-pattern | 0.143 | 0.03 | False | 0.00 | premium |
| ph_cooperative | philippines | cooperative | illustrative-phonetic-noise-pattern | 0.571 | 0.121 | True | 1.00 | — |
| ph_objection | philippines | objection | illustrative-loanword-drop-pattern | 0.0 | 0.0 | True | n/a | — |
| ph_objection | philippines | objection | illustrative-phonetic-noise-pattern | 0.5 | 0.13 | True | n/a | — |
| ph_mixed_terms | philippines | mixed_terms | illustrative-loanword-drop-pattern | 0.167 | 0.085 | False | 0.00 | coverage, beneficiary |
| ph_mixed_terms | philippines | mixed_terms | illustrative-phonetic-noise-pattern | 0.25 | 0.056 | True | 1.00 | — |
| ph_colloquial | philippines | colloquial | illustrative-loanword-drop-pattern | 0.083 | 0.036 | True | n/a | — |
| ph_colloquial | philippines | colloquial | illustrative-phonetic-noise-pattern | 0.25 | 0.071 | True | n/a | — |
| ph_escalation | philippines | escalation | illustrative-loanword-drop-pattern | 0.083 | 0.029 | False | n/a | — |
| ph_escalation | philippines | escalation | illustrative-phonetic-noise-pattern | 0.333 | 0.058 | True | n/a | — |
| id_cooperative | indonesia | cooperative | illustrative-loanword-drop-pattern | 0.25 | 0.083 | True | 0.00 | jatuh tempo |
| id_cooperative | indonesia | cooperative | illustrative-phonetic-noise-pattern | 0.75 | 0.167 | True | 1.00 | — |
| id_objection | indonesia | objection | illustrative-loanword-drop-pattern | 0.0 | 0.0 | True | n/a | — |
| id_objection | indonesia | objection | illustrative-phonetic-noise-pattern | 0.8 | 0.133 | True | n/a | — |
| id_mixed_terms | indonesia | mixed_terms | illustrative-loanword-drop-pattern | 0.2 | 0.045 | False | 0.00 | tenor, top-up |
| id_mixed_terms | indonesia | mixed_terms | illustrative-phonetic-noise-pattern | 0.3 | 0.06 | True | 1.00 | — |
| id_colloquial | indonesia | colloquial | illustrative-loanword-drop-pattern | 0.0 | 0.0 | True | n/a | — |
| id_colloquial | indonesia | colloquial | illustrative-phonetic-noise-pattern | 0.6 | 0.136 | True | n/a | — |
| id_escalation | indonesia | escalation | illustrative-loanword-drop-pattern | 0.071 | 0.023 | True | n/a | — |
| id_escalation | indonesia | escalation | illustrative-phonetic-noise-pattern | 0.286 | 0.058 | True | n/a | — |
| id_regional_accent | indonesia | regional_accent | illustrative-loanword-drop-pattern | 0.1 | 0.03 | True | 1.00 | — |
| id_regional_accent | indonesia | regional_accent | illustrative-phonetic-noise-pattern | 0.3 | 0.06 | True | 1.00 | — |

## Indonesian regional-accent performance

The `id_regional_accent` test utterance uses Javanese-influenced particles/vocabulary (nggih, sampun, mboten). **This benchmark tests text-level handling only** — whether these tokens survive a transcription/perturbation pass — **not real ASR pronunciation/accent recognition**, which needs real audio from an actual Javanese-accented speaker and a live provider, neither available here. A separate, real finding from the conversational simulator (not this benchmark): even a *standard-Indonesian paraphrase* of this utterance failed to retrieve the matching KB objection record (see docs/q3_multilingual/gaps.md) — suggesting regional phrasing may need either KB content written to match dialect variation more closely, or retrieval-side paraphrase robustness improvements, independent of any ASR accuracy question.

- `illustrative-loanword-drop-pattern`: code-switch preserved = True, WER = 0.1
- `illustrative-phonetic-noise-pattern`: code-switch preserved = True, WER = 0.3
