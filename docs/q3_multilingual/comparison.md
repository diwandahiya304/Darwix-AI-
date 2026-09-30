# Q3 Comparison: Philippines vs. Indonesia

## ASR Quality

**Not measured** — no live ASR provider credentials in this environment. See `docs/q3_multilingual/asr_report.md` for the benchmark harness design, candidate provider documentation, and the honesty caveat on every number in it.

## TTS Quality

**Not measured** — no live TTS provider credentials. Candidate voices (see `multilingual/README.md` 'ASR/TTS Setup'): Philippines `fil-PH-BlessicaNeural`/`AngeloNeural` (Azure) or ElevenLabs multilingual; Indonesia `id-ID-ArdiNeural`/`GadisNeural` (Azure) or ElevenLabs. **Known compromise, not verified against real audio**: neither Azure nor ElevenLabs, as far as documented, offers a voice specifically tuned for natural Taglish code-switching prosody or a Javanese-accented Indonesian voice — both would default to standard fil-PH/id-ID prosody, which may sound less natural for heavily code-switched or regionally-accented delivery than a native speaker would.

## Fallback Behaviour (measured, real simulator runs against the real KB)

| Market | Scenarios run | KB lookups | Grounded | Fallback | Grounding rate |
|---|---|---|---|---|---|
| Philippines | 5 | 6 | 6 | 0 | 100% |
| Indonesia | 6 | 7 | 6 | 1 | 86% |

## Issues

No tool-dispatch errors observed across either market's scripted scenario runs.

- See `docs/q3_multilingual/gaps.md` for the full retrieval-threshold and regional-accent findings — both markets needed their own calibrated grounding threshold (thinner margins than English's, see `docs/DECISIONS.md`), and Indonesia's regional-accent scenario specifically surfaced a paraphrase-distance retrieval miss, independent of any ASR question.
- Philippines' near-miss objection ("Wala akong pera ngayon", measured dense score 0.834) was fixed by per-language threshold calibration, not by rewording the query — see `docs/DECISIONS.md`.
