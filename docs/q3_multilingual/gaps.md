# Known Gaps: Native-Speaker Review, Compliance Review, and Technical Limitations (Q3)

This document exists because the assignment brief explicitly asked for
honesty over false confidence: **every piece of Tagalog/Filipino and
Bahasa Indonesia content in this submission was drafted by an AI system,
not a certified native speaker, and none of it has been reviewed by a
native speaker or a compliance/legal team.** Treat everything linguistic
or regulatory in `multilingual/` as a first draft requiring professional
review before any real customer contact — not as production-ready.

## Native-speaker review needed (linguistic)

Every file under `multilingual/philippines/kb_seed/`,
`multilingual/indonesia/kb_seed/`, both markets' `config/system_prompt.md`
and `config/fallback_messages.yaml` carries an inline
`LINGUISTIC REVIEW NEEDED` notice. Specific points flagged as uncertain,
not just generically caveated:

- **Philippines**: whether "i-reinstate" (policy reinstatement) is the
  verb form a real call center agent would use vs. a different English-
  loanword or Tagalog alternative; natural phrasing for "verify this
  call" in a scam-concern context; whether the register-mirroring rules
  in the system prompt describe real agent behavior or an AI-plausible
  approximation of it.
- **Indonesia**: whether "restrukturisasi" is the term a real
  multifinance call center would use directly with customers, or a more
  colloquial equivalent reserved for internal/formal documentation; the
  formal/colloquial marker lists in `multilingual/common/register.py`
  are a plausible-but-unverified guess at what actually signals register
  in spoken Indonesian, not a validated linguistic classification.
- **Indonesia regional accent**: the Javanese-influenced test utterance
  (nggih/mboten/sampun) was written by an AI system with general
  knowledge of Javanese-influenced Indonesian, not a Javanese speaker.
  Whether this is a realistic representation of how a Javanese-accented
  customer would actually phrase this in a phone call is unverified.

**Recommendation**: have a native Tagalog/Filipino speaker and a native
Indonesian speaker (ideally with call-center or financial-services
experience) review every KB seed file, system prompt, and fallback
message before any real deployment — not just spot-check a sample.

## Compliance/legal review needed

- **Philippines Data Privacy Act reference**
  (`multilingual/philippines/kb_seed/web/compliance_disclosure_requirements.html`):
  based on general knowledge that the Philippines has a Data Privacy Act
  (RA 10173) restricting disclosure of personal/financial information —
  **not a verified legal citation**. A compliance team must confirm the
  exact regulatory basis and required disclosure wording.
- **Indonesia OJK-style collections conduct**
  (`multilingual/indonesia/kb_seed/web/compliance_disclosure_ojk_conduct.html`):
  based on general public knowledge of OJK (Otoritas Jasa Keuangan) debt
  collection conduct expectations (no threats, no third-party
  disclosure, restricted calling hours, mandatory identification) —
  **not a verified citation of a specific OJK regulation number or exact
  required wording**. The substance is directionally correct (these are
  well-known, widely-cited conduct norms in Indonesian collections), but
  a compliance team must confirm the precise regulatory basis before
  this is used in a real collections call.
- Neither market's guardrails have been checked against actual insurance/
  multifinance industry regulations beyond the general conduct principles
  above (e.g. specific cooling-off/free-look period lengths, specific
  mandatory disclosure timing requirements) — the numbers used
  (15-day free-look, 08:00-20:00 calling window) are reasonable
  illustrative defaults, not verified against a specific regulator's
  actual requirement.

## Technical limitations (measured directly, not assumed)

- **Per-language grounding thresholds are calibrated on a very thin
  sample** (~8 exploratory queries per language) and have **thinner
  margins than English's already-thin one**: fil ~0.006, id ~0.003 vs.
  en's ~0.02 (see `kb/app/settings.py`, `docs/DECISIONS.md`). These are
  real, measured numbers, not estimates — and they mean a differently-
  phrased genuine customer question is *more* likely to land on the
  wrong side of the threshold in Tagalog/Indonesian than in English.
- **A single global threshold silently rejected a genuinely-grounded
  Tagalog match** before this was caught (dense score 0.834 against an
  English-calibrated 0.84 cutoff) — fixed with per-language overrides,
  but this is exactly the kind of failure mode that could recur with any
  future language added without its own calibration pass.
- **Cross-lingual ranking is not reliable without an explicit language
  filter**: measured directly that an unfiltered English query can rank
  a topically-similar Tagalog record fractionally above a near-identical
  English one (0.8214 vs 0.8191). Every real caller in this codebase
  (`multilingual/common/kb_client.py`) always passes an explicit
  language filter for exactly this reason — this is a structural
  requirement, not an optional optimization.
- **Retrieval is sensitive to paraphrase distance from the KB's own
  wording, and this bit the regional-accent scenario specifically**: a
  standard-Indonesian paraphrase of the Javanese-influenced test
  utterance ("Saya sudah bayar angsuran, tidak ada tunggakan") failed to
  retrieve the KB's actual objection-handling record ("Saya udah bayar
  kemarin"), while the KB's own exact phrasing scored 0.8282 — just
  barely above threshold. This suggests regional/dialect-influenced
  speech, once transcribed and possibly normalized toward standard
  Indonesian, may need either KB content authored closer to how people
  actually phrase things, or retrieval-side robustness work — this is
  not specific to accent/pronunciation, it showed up at the text level
  before ASR is even in the picture.
- **No real ASR/TTS provider was exercised** — see
  `docs/q3_multilingual/asr_report.md`'s "Read this first" section. The
  Indonesian regional-accent requirement in particular is only tested at
  the text level here; real accent/pronunciation performance is
  completely unverified.
- **No real Vapi account** — the same caveat as `voice_agent/README.md`
  applies to both markets' `scripts/create_assistant.py`.
- **PII masking for non-English content is email-only** (see
  `kb/app/ingest/pii.py` — NER-based detection was disabled for non-
  English text after it was found mangling real words as false-positive
  PERSON entities; see `docs/DECISIONS.md`). Philippine/Indonesian phone
  numbers and national ID formats (PhilSys ID/TIN; NIK/KTP) have no
  dedicated recognizer — a real production deployment ingesting real
  customer data in these markets would need one built before go-live.

## What would need to happen before real deployment

1. Native-speaker linguistic review of every file flagged above, with
   corrections applied and re-verified against the system prompt tests
   (`test_build_assistant_payload_system_prompt_has_no_fact_markers` and
   equivalents).
2. Compliance/legal review of both markets' regulatory claims, with
   exact citations and required wording confirmed.
3. Real ASR/TTS provider credentials, real test audio from native
   speakers (including the Indonesian regional accent requirement), and
   a genuine benchmark run — not the illustrative one in this
   submission.
4. Re-calibration of per-language grounding thresholds against a much
   larger, native-speaker-reviewed query set once real content volume
   grows past this assessment's small seed set.
5. A real Vapi account, with `scripts/create_assistant.py`'s payload
   shape verified against a live response and corrected if Vapi's actual
   API contract differs from what's implemented here.
