"""ASR quality metrics: WER/CER (via jiwer), a code-switching handling
check, and named-term accuracy — the three things the brief asks the
benchmark to report per provider/utterance.
"""

from __future__ import annotations

import jiwer
from pydantic import BaseModel


class WerCerResult(BaseModel):
    wer: float
    cer: float


def compute_wer_cer(reference: str, hypothesis: str) -> WerCerResult:
    return WerCerResult(wer=jiwer.wer(reference, hypothesis), cer=jiwer.cer(reference, hypothesis))


class NamedTermAccuracyResult(BaseModel):
    expected_terms: list[str]
    found_terms: list[str]
    missed_terms: list[str]
    accuracy: float | None  # None if no expected terms were given


def named_term_accuracy(hypothesis: str, expected_terms: list[str]) -> NamedTermAccuracyResult:
    """Checks whether domain-specific named terms (premium, cicilan,
    tenor, DP, ...) survive correctly in the hypothesis — these are
    exactly the terms a generic ASR model is most likely to mis-transcribe
    (out-of-vocabulary loanwords, code-mixed finance jargon)."""

    hyp_lower = hypothesis.lower()
    found = [t for t in expected_terms if t.lower() in hyp_lower]
    missed = [t for t in expected_terms if t.lower() not in hyp_lower]
    accuracy = len(found) / len(expected_terms) if expected_terms else None
    return NamedTermAccuracyResult(
        expected_terms=expected_terms, found_terms=found, missed_terms=missed, accuracy=accuracy
    )


class CodeSwitchResult(BaseModel):
    reference_has_code_switch: bool
    hypothesis_preserved_switch_terms: bool
    detail: str


def check_code_switching_handling(
    reference: str, hypothesis: str, code_switch_markers: list[str]
) -> CodeSwitchResult:
    """`code_switch_markers`: the specific English/loanword tokens this
    utterance deliberately code-switches with (e.g. ["premium",
    "auto-debit"] for Taglish, ["DP", "tenor", "top-up"] for Indonesian
    finance loanwords). Reports whether the reference actually contains
    them (sanity check on the test utterance itself) and whether the
    hypothesis preserved them — a common ASR failure mode is dropping or
    mangling exactly these out-of-base-language tokens."""

    ref_lower = reference.lower()
    hyp_lower = hypothesis.lower()
    ref_has = any(marker.lower() in ref_lower for marker in code_switch_markers)
    hyp_preserved = all(marker.lower() in hyp_lower for marker in code_switch_markers) if ref_has else True
    detail = (
        f"{sum(1 for m in code_switch_markers if m.lower() in hyp_lower)}/{len(code_switch_markers)} "
        f"code-switch markers preserved in hypothesis"
    )
    return CodeSwitchResult(
        reference_has_code_switch=ref_has, hypothesis_preserved_switch_terms=hyp_preserved, detail=detail
    )
