"""Runs the ASR benchmark: for each test utterance, transcribes via each
provider and computes WER/CER, code-switching handling, and named-term
accuracy. Writes docs/q3_multilingual/asr_report.{md,json}.

**Honesty check, read before trusting any number in the generated
report**: no ASR provider credentials exist in this environment.
Deepgram and Azure Speech (`providers.py`) are real, correctly-
implemented REST clients — but every real-provider row in the generated
report reads "not run — no credentials configured," never a fabricated
number. Two `FakeASRProvider` instances, clearly labeled illustrative
(not real measurements), demonstrate the harness's WER/CER/code-
switching/named-term-accuracy computation actually works end-to-end —
their "errors" are hand-designed to represent well-documented real ASR
failure modes (dropping out-of-vocabulary loanwords; generic phonetic
noise), not measured from any real system.

Run: `make multilingual-asr-bench`.
"""

from __future__ import annotations

import json
import random
import sys

from multilingual.asr_bench.metrics import (
    check_code_switching_handling,
    compute_wer_cer,
    named_term_accuracy,
)
from multilingual.asr_bench.providers import FakeASRProvider
from multilingual.asr_bench.test_utterances import TEST_UTTERANCES
from multilingual.common.settings import REPO_ROOT, get_settings

RESULTS_MD_PATH = REPO_ROOT / "docs" / "q3_multilingual" / "asr_report.md"
RESULTS_JSON_PATH = REPO_ROOT / "docs" / "q3_multilingual" / "asr_report.json"

_LOANWORD_MANGLES = {
    "premium": "premyum",
    "auto-debit": "oto-debit",
    "coverage": "koveraj",
    "beneficiary": "benefisyari",
    "tenor": "tenar",
    "top-up": "topap",
    "jatuh tempo": "jato tempo",
    "scam": "sekam",
    "ok": "okey",
}


def _drop_loanwords(text: str) -> str:
    """Illustrative only — simulates an ASR model that struggles with
    out-of-vocabulary finance loanwords/code-switch terms, a well-
    documented real failure mode for generic ASR on code-switched
    speech. NOT a measurement of any real provider."""

    result = text
    for term, mangled in _LOANWORD_MANGLES.items():
        result = result.replace(term, mangled)
    return result


def _minor_phonetic_noise(text: str) -> str:
    """Illustrative only — simulates generic transcription noise (a few
    character-level slips). NOT a measurement of any real provider."""

    rng = random.Random(42)
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch.isalpha() and rng.random() < 0.04:
            chars[i] = ch.swapcase()
    return "".join(chars)


def run_benchmark() -> dict:
    settings = get_settings()
    fake_providers = [
        FakeASRProvider("illustrative-loanword-drop-pattern", _drop_loanwords),
        FakeASRProvider("illustrative-phonetic-noise-pattern", _minor_phonetic_noise),
    ]
    real_provider_status = {
        "deepgram-nova-3": (
            "configured but not executed in this run (no test audio available)"
            if settings.deepgram_api_key
            else "not run — DEEPGRAM_API_KEY not configured in this environment"
        ),
        "azure-speech": (
            "configured but not executed in this run (no test audio available)"
            if (settings.azure_speech_key and settings.azure_speech_region)
            else "not run — AZURE_SPEECH_KEY/AZURE_SPEECH_REGION not configured in this environment"
        ),
    }

    rows = []
    for utt in TEST_UTTERANCES:
        for provider in fake_providers:
            result = provider.transcribe_text(utt.text)
            wer_cer = compute_wer_cer(utt.text, result.text)
            code_switch = check_code_switching_handling(utt.text, result.text, utt.code_switch_markers)
            term_acc = named_term_accuracy(result.text, utt.named_terms)
            rows.append(
                {
                    "utterance_id": utt.utterance_id,
                    "market": utt.market,
                    "category": utt.category,
                    "provider": provider.name,
                    "reference": utt.text,
                    "hypothesis": result.text,
                    "wer": round(wer_cer.wer, 3),
                    "cer": round(wer_cer.cer, 3),
                    "code_switch_preserved": code_switch.hypothesis_preserved_switch_terms,
                    "named_term_accuracy": term_acc.accuracy,
                    "missed_terms": term_acc.missed_terms,
                }
            )

    return {"rows": rows, "real_provider_status": real_provider_status}


def write_report(summary: dict) -> None:
    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# ASR Report (Q3)",
        "",
        "## Read this first",
        "",
        "**No ASR provider credentials (Deepgram, Azure Speech, Google STT, "
        "OpenAI gpt-4o-transcribe) exist in this development environment, and "
        "no real audio recordings of native speakers exist either.** Every "
        "number below from `illustrative-loanword-drop-pattern` / "
        "`illustrative-phonetic-noise-pattern` is a **synthetic, hand-designed "
        "stand-in** for a plausible ASR failure mode — dropping out-of-"
        "vocabulary finance loanwords, and generic phonetic noise — used to "
        "prove the benchmark harness itself (WER/CER via `jiwer`, code-"
        "switching handling, named-term accuracy) computes correctly. **They "
        "are not measurements of Deepgram, Azure, or any real provider**, and "
        "must not be read as such.",
        "",
        "## Real provider configuration status",
        "",
        "| Provider | Status |",
        "|---|---|",
    ]
    for provider, status in summary["real_provider_status"].items():
        lines.append(f"| {provider} | {status} |")

    lines += [
        "",
        "## Candidate providers (from public documentation, not measured here)",
        "",
        "- **Deepgram nova-3**: supports `language=multi` for automatic "
        "code-switch detection, or explicit language codes. The brief lists "
        "\"tl\" for Tagalog — note this repo's KB/pipeline uses \"fil\" "
        "(Filipino, matching Azure's locale code) as the language tag; "
        "these are close but not identical, and this discrepancy is "
        "flagged, not resolved, pending native-speaker/provider-docs review.",
        "- **Azure Speech**: locales `fil-PH` (Filipino), `id-ID` "
        "(Indonesian), `en-PH` (Philippine English) per the brief. Azure "
        "also supports custom speech models for domain vocabulary, which "
        "would help with finance loanwords/named terms — not configured here.",
        "- **Google STT / OpenAI gpt-4o-transcribe**: not implemented in "
        "`providers.py` at all (scope decision, same reasoning as "
        "voice_agent's single-provider LLM-mode choice) — see docs/DECISIONS.md.",
        "",
        "## Benchmark results (illustrative providers only — see warning above)",
        "",
        "| Utterance | Market | Category | Provider | WER | CER | Code-switch preserved | Named-term accuracy | Missed terms |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in summary["rows"]:
        term_acc = f"{row['named_term_accuracy']:.2f}" if row["named_term_accuracy"] is not None else "n/a"
        missed = ", ".join(row["missed_terms"]) or "—"
        lines.append(
            f"| {row['utterance_id']} | {row['market']} | {row['category']} | {row['provider']} | "
            f"{row['wer']} | {row['cer']} | {row['code_switch_preserved']} | {term_acc} | {missed} |"
        )

    regional_rows = [r for r in summary["rows"] if r["category"] == "regional_accent"]
    lines += [
        "",
        "## Indonesian regional-accent performance",
        "",
        "The `id_regional_accent` test utterance uses Javanese-influenced "
        "particles/vocabulary (nggih, sampun, mboten). **This benchmark tests "
        "text-level handling only** — whether these tokens survive a "
        "transcription/perturbation pass — **not real ASR pronunciation/"
        "accent recognition**, which needs real audio from an actual "
        "Javanese-accented speaker and a live provider, neither available "
        "here. A separate, real finding from the conversational simulator "
        "(not this benchmark): even a *standard-Indonesian paraphrase* of "
        "this utterance failed to retrieve the matching KB objection "
        "record (see docs/q3_multilingual/gaps.md) — suggesting regional "
        "phrasing may need either KB content written to match dialect "
        "variation more closely, or retrieval-side paraphrase robustness "
        "improvements, independent of any ASR accuracy question.",
        "",
    ]
    for row in regional_rows:
        lines.append(f"- `{row['provider']}`: code-switch preserved = {row['code_switch_preserved']}, WER = {row['wer']}")

    RESULTS_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    summary = run_benchmark()
    write_report(summary)
    print(f"ASR benchmark report written to {RESULTS_MD_PATH}")
    print("Real provider status:", summary["real_provider_status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
