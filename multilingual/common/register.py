"""Register detection: a small, rule-based heuristic that classifies the
customer's last utterance as "formal" or "colloquial" so the bot can
mirror it — used to pick between formal/colloquial fallback message
variants (config/fallback_messages.yaml in each market) and, in the
system prompt's instructions, to guide overall tone for that turn.

This is NOT a robust NLU classifier — it's a keyword/marker heuristic,
genuinely useful for picking between two pre-written message variants,
but not sophisticated enough to drive free-form register-matched
generation on its own. Flagged explicitly as a known limitation (see
docs/q3_multilingual/gaps.md): a production system would want either a
small trained classifier or (more likely) let the underlying LLM infer
register directly from conversation context, using this heuristic only
as a fallback/tie-breaker signal.
"""

from __future__ import annotations

from enum import Enum


class Register(str, Enum):
    FORMAL = "formal"
    COLLOQUIAL = "colloquial"


# Markers are lowercase; matched as substrings against the lowercased
# utterance. Order doesn't matter — this is a simple marker-count vote,
# not a weighted model.
_FORMAL_MARKERS = {
    "fil": ["po", "opo", "ma'am", "sir", "ho"],
    "id": ["bapak", "ibu", "selamat pagi", "selamat siang", "selamat sore", "mohon", "bersedia"],
}

_COLLOQUIAL_MARKERS = {
    "fil": ["pre", "bro", "sis", "grabe", "ano ba"],
    "id": ["kak", "nih", "deh", "gue", "gitu", "yaudah", "udah", "gimana", "halo"],
}


def detect_register(utterance: str, language: str, default: Register = Register.FORMAL) -> Register:
    """`language` is "fil" or "id" — the marker lists are language-
    specific since formal/colloquial cues differ (po/opo for Filipino;
    Bapak/Ibu vs Kak/nih for Indonesian). Defaults to FORMAL when
    ambiguous or no markers match — the safer default for a financial
    services call (erring formal is a much smaller cultural misstep than
    erring colloquial with an older or more conservative customer)."""

    lowered = utterance.lower()
    formal_markers = _FORMAL_MARKERS.get(language, [])
    colloquial_markers = _COLLOQUIAL_MARKERS.get(language, [])

    formal_hits = sum(1 for marker in formal_markers if marker in lowered)
    colloquial_hits = sum(1 for marker in colloquial_markers if marker in lowered)

    if formal_hits == 0 and colloquial_hits == 0:
        return default
    return Register.COLLOQUIAL if colloquial_hits > formal_hits else Register.FORMAL
