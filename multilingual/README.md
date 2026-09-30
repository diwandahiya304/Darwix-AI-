# multilingual/ — Native-Language Voice Bots (Q3)

> Status: **fully implemented and tested against a simulated call
> pipeline**, same honesty caveats as `voice_agent/`: no live Vapi
> account, no live ASR/TTS provider credentials exist in this
> environment. **Every Tagalog/Filipino and Bahasa Indonesia string in
> this submission was AI-drafted, not native-speaker-reviewed** — see
> [`docs/q3_multilingual/gaps.md`](../docs/q3_multilingual/gaps.md)
> before treating any of it as production-ready.

## Overview

Two markets, reusing the Q2 KB architecture with language-tagged records
(one retrieval index, filtered by `language` — see
`kb/app/ingest/pipeline.py`'s `extra_raw_dirs` and
`multilingual/scripts/ingest_multilingual_kb.py`), and reusing
`voice_agent/`'s escalation/CRM modules directly rather than duplicating
them.

## Philippines Bot

- Sector: life insurance / bancassurance.
- Flow built: **premium/renewal reminder** (bancassurance cross-sell is
  mentioned in the system prompt's product content but not built as a
  separate flow — a scope decision, see `docs/DECISIONS.md`).
- Languages: English, Filipino/Tagalog, natural Taglish — register-
  mirrored (po/opo formal vs. relaxed colloquial), never switches to
  English unexpectedly.
- Domain terms used naturally: premium, policy, beneficiary, rider,
  lapse, coverage, bank referral (see `multilingual/philippines/kb_seed/`).
- One business action: `set_auto_debit_preference` (avoiding a lapsed
  policy is the whole point of this call).

## Indonesia Bot

- Sector: multifinance / consumer finance.
- Flow built: installment (angsuran/cicilan) reminder + collections
  support, with explicit **OJK-style conduct guardrails** baked into the
  system prompt (no threats, no third-party disclosure, restricted
  calling hours, mandatory identification) — see
  `multilingual/indonesia/kb_seed/web/compliance_disclosure_ojk_conduct.html`.
- Languages: formal ("Selamat siang, Bapak/Ibu") + colloquial ("Halo Kak,
  ... nih") Bahasa Indonesia, register-mirrored via
  `multilingual/common/register.py`; finance English loanwords (DP,
  tenor, limit, top-up, auto-debit).
- Domain terms used naturally: cicilan, tenor, denda, DP, jatuh tempo,
  angsuran, pembiayaan.
- Regional accent: Javanese-influenced test coverage (nggih, mboten,
  sampun) — **text-level only**, see Known Limitations.
- One business action: `record_promise_to_pay` ("janji bayar").

## Architecture

```
Vapi --tool call--> multilingual/{market}/app/main.py (/webhook)
                              |
                              v
                    multilingual/{market}/app/tools.py
                       /            |            \
   common/kb_client.py    voice_agent escalation/crm   market-specific tool
   (language-filtered,      (reused directly, not       (set_auto_debit_
    register-aware            duplicated)                 preference /
    fallback)                                              record_promise_
                                                            to_pay)
```

## ASR Report

See [`docs/q3_multilingual/asr_report.md`](../docs/q3_multilingual/asr_report.md).
**Read its "Read this first" section before trusting any number in it**
— no live ASR provider exists in this environment; the harness
(`multilingual/asr_bench/`) is real and tested (jiwer-based WER/CER, a
code-switching handling check, named-term accuracy), but every number
comes from an illustrative offline provider, not Deepgram/Azure/Google/
OpenAI.

## Localization vs. Translation

At least 3 examples per market — see
[`docs/q3_multilingual/localization_examples.md`](../docs/q3_multilingual/localization_examples.md).

## Native TTS

**Not exercised** — no live TTS credentials. Candidate voices: Philippines
`fil-PH-BlessicaNeural`/`AngeloNeural` (Azure) or ElevenLabs multilingual;
Indonesia `id-ID-ArdiNeural`/`GadisNeural` (Azure) or ElevenLabs. See
`docs/q3_multilingual/comparison.md` for documented compromises (no voice
specifically tuned for Taglish code-switching prosody or a Javanese-
accented Indonesian voice, as far as documented — unverified against
real audio).

## Test Scenarios and Calls

5 scenarios (Philippines) / 6 scenarios (Indonesia, including the
regional-accent one) executed for real via `make multilingual-sim-ph` /
`make multilingual-sim-id` — transcripts in
`recordings/multilingual/{philippines,indonesia}/*.md`. **Simulated, not
real Vapi calls** — see Vapi Setup Steps below for running real ones.

**Result** (`docs/q3_multilingual/comparison.md`): Philippines 100%
grounding rate across scenarios; Indonesia 86% (one genuine miss — the
regional-accent scenario's KB lookup, root-caused in
`docs/q3_multilingual/gaps.md`, not hidden).

## ASR/TTS Setup Steps (for connecting real providers)

None of these are configured in this environment. To connect a real one:

1. **Deepgram**: create an account at [deepgram.com](https://deepgram.com),
   get an API key, set `DEEPGRAM_API_KEY` in `.env`.
2. **Azure Speech**: create a Speech resource in the Azure portal, set
   `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` in `.env`.
3. With real test audio (native-speaker recordings covering the required
   scenarios), update `multilingual/asr_bench/run_benchmark.py` to call
   `DeepgramProvider`/`AzureSpeechProvider` with real audio file paths
   instead of only reporting configuration status, then
   `make multilingual-asr-bench` and review the regenerated report
   carefully — the illustrative section should be replaced, not kept
   alongside real numbers.
4. For TTS, provision Azure Speech (same resource) or an ElevenLabs
   account, and wire the chosen voice ID into
   `multilingual/scripts/create_assistant.py`'s `voice` config per
   market.

## Vapi Setup Steps

Same pattern as `voice_agent/README.md` — see that file for the full
walkthrough (account, API key, ngrok/cloudflared). Market-specific
differences:

```bash
# .env
VAPI_API_KEY=<your key>
PH_WEBHOOK_BASE_URL=<ngrok/cloudflared URL for the PH webhook>
ID_WEBHOOK_BASE_URL=<ngrok/cloudflared URL for the ID webhook>

make run-kb                              # KB retrieval API, port 8001
make multilingual-run-ph                 # PH webhook, port $PH_PORT
make multilingual-run-id                 # ID webhook, port $ID_PORT
make multilingual-create-assistant-ph    # creates the Vapi assistant for PH
make multilingual-create-assistant-id    # creates the Vapi assistant for ID
```

Same honesty caveat as `voice_agent/scripts/create_assistant.py`: the
request payload is real and tested, the actual POST to Vapi's API is not
verified against a live response.

## Running Locally Without Live Credentials

```bash
make multilingual-ingest-kb       # ingest PH + ID KB seed content (language-tagged)
make kb-index                     # rebuild the retrieval index to include it
make multilingual-sim-ph          # run all PH scenarios (scripted, real KB)
make multilingual-sim-id          # run all ID scenarios (scripted, real KB)
make multilingual-comparison      # compile docs/q3_multilingual/comparison.md
make multilingual-asr-bench       # ASR benchmark harness (illustrative — see caveat above)
```

## Test

```bash
make test-multilingual
```

Tests: register detection, language-scoped KB client (mocked HTTP),
common tool registry (including reuse of `voice_agent`'s escalation/CRM),
both markets' webhook wiring (FastAPI TestClient), both markets' Vapi
script graceful-failure paths, ASR metrics (WER/CER, code-switching,
named-term accuracy) and benchmark orchestration, and the per-language
grounding-threshold fix (in `kb/tests/`).

## Metrics

`docs/q3_multilingual/asr_report.{md,json}`,
`docs/q3_multilingual/comparison.md`,
`docs/q3_multilingual/localization_examples.md`. See
[`docs/q3_multilingual/gaps.md`](../docs/q3_multilingual/gaps.md) for
everything flagged as needing native-speaker or compliance review, and
every technical limitation found and documented (per-language threshold
margins thinner than English's, a paraphrase-distance retrieval miss on
the regional-accent scenario, non-English PII masking's reduced scope).

## Known Limitations

See [`docs/q3_multilingual/gaps.md`](../docs/q3_multilingual/gaps.md) for
the full, honest list — summarized:

- No native-speaker or compliance/legal review of any linguistic or
  regulatory content.
- No live ASR/TTS/Vapi credentials — nothing audio-related is verified.
- Per-language grounding thresholds are calibrated on a thin sample with
  margins thinner than English's already-thin one.
- The Indonesian regional-accent scenario is tested at the text level
  only, and surfaced a real paraphrase-distance retrieval limitation
  independent of accent/pronunciation.
- Non-English PII masking only catches email addresses (NER disabled
  after it was found mangling real content — see `docs/DECISIONS.md`).
