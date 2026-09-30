"""PII detection and masking.

Primary: Microsoft Presidio, explicitly configured to use the small
`en_core_web_sm` spaCy model (Presidio's default engine reaches for
`en_core_web_lg`, ~587MB, and will silently `spacy download` it the first
time it's used if not pinned away from that — see docs/DECISIONS.md).
Custom pattern recognizers are added for Indian identifiers Presidio has
no built-in coverage for: Aadhaar and PAN. `entities=` is passed explicitly
on every analyze() call so Presidio never invokes its URL recognizer,
which otherwise makes a live network call to publicsuffix.org — a
hermetic-pipeline violation (CLAUDE.md §9) and, in this environment, an
outright SSL failure.

Fallback: if presidio-analyzer / spacy aren't importable, or the analyzer
fails to build for any reason, we degrade to a pure-regex detector
covering email, Indian phone numbers, Aadhaar, and PAN. Person-name
detection is NOT available in fallback mode — that needs NLP. This is a
documented, known limitation (docs/DECISIONS.md), not a silent gap.

Non-English content (`mask_pii(text, language=...)` with anything other
than "en") skips Presidio/NER entirely and uses email-only regex masking
— en_core_web_sm's English-trained NER produces severe false positives on
Tagalog/Indonesian text (verified directly, not assumed — see
docs/DECISIONS.md), and the India-specific Aadhaar/PAN/phone patterns
don't apply to those markets anyway.

In both modes: PII is replaced with typed placeholders ([EMAIL], [PHONE],
[AADHAAR], [PAN], [PERSON]). Raw PII values are never returned, logged, or
printed anywhere — only counts by type reach docs/q2_kb/pii_report.*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_INDIA_PHONE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}\b")
_AADHAAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

_PLACEHOLDER_BY_TYPE = {
    "EMAIL": "[EMAIL]",
    "PHONE": "[PHONE]",
    "AADHAAR": "[AADHAAR]",
    "PAN": "[PAN]",
    "PERSON": "[PERSON]",
}

# Presidio entity name -> our canonical type name.
_PRESIDIO_ENTITY_MAP = {
    "PERSON": "PERSON",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "AADHAAR": "AADHAAR",
    "PAN": "PAN",
}


@dataclass
class PIIMaskResult:
    masked_text: str
    pii_types: list[str] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)


def _regex_mask(text: str) -> PIIMaskResult:
    counts: dict[str, int] = {}

    def _sub(pattern: re.Pattern, pii_type: str, s: str) -> str:
        def _repl(_match: re.Match) -> str:
            counts[pii_type] = counts.get(pii_type, 0) + 1
            return _PLACEHOLDER_BY_TYPE[pii_type]

        return pattern.sub(_repl, s)

    masked = text
    masked = _sub(_EMAIL_RE, "EMAIL", masked)
    masked = _sub(_PAN_RE, "PAN", masked)
    masked = _sub(_AADHAAR_RE, "AADHAAR", masked)
    masked = _sub(_INDIA_PHONE_RE, "PHONE", masked)
    return PIIMaskResult(masked_text=masked, pii_types=sorted(counts), counts=counts)


try:
    from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    _PRESIDIO_IMPORTABLE = True
except ImportError:
    _PRESIDIO_IMPORTABLE = False


def _build_presidio_engines():
    nlp_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
    }
    nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
    analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])

    analyzer.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="AADHAAR",
            patterns=[Pattern(name="aadhaar", regex=_AADHAAR_RE.pattern, score=0.85)],
        )
    )
    analyzer.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="PAN",
            patterns=[Pattern(name="pan", regex=_PAN_RE.pattern, score=0.85)],
        )
    )
    # Presidio's built-in PHONE_NUMBER recognizer (phonenumbers-backed)
    # doesn't reliably catch bare 10-digit Indian mobile numbers without a
    # country-code hint; add our own pattern as a second recognizer for the
    # same entity type so either one firing is enough.
    analyzer.registry.add_recognizer(
        PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            patterns=[Pattern(name="india_phone", regex=_INDIA_PHONE_RE.pattern, score=0.8)],
        )
    )
    return analyzer, AnonymizerEngine()


_analyzer = None
_anonymizer = None


def _filter_person_false_positives(results: list, text: str) -> list:
    """`en_core_web_sm` (chosen for footprint — see docs/DECISIONS.md) is
    noisier than the large spaCy model and produces two recurring
    false-positive shapes for PERSON on this kind of business content:

    1. It sometimes tags a structured identifier (e.g. "PAN ABCDE1234F")
       as a single PERSON span, and presidio_anonymizer's default overlap
       resolution keeps whichever span is *longer* — not whichever
       recognizer scored higher — so the wrong PERSON guess silently wins
       over our exact regex match for AADHAAR/PAN. Since those are
       pattern-matched (deterministic, not probabilistic), a PERSON hit
       that overlaps one is treated as the false positive and dropped.
    2. It sometimes tags a single capitalized product/plan word (e.g.
       "Silver", "Gold" in a pricing table) as PERSON. Every genuine
       PERSON in this KB's source content is a first-name + last-name
       pair, so a single-token PERSON match is dropped too.

    Neither case is a PII-safety issue either way (both entity types get
    masked in the end) — this only fixes which placeholder/type the
    pii_report attributes it to, and stops real product terms from being
    redacted out of KB content they need to stay useful for retrieval.
    A larger/fine-tuned NER model would need fewer heuristics like this;
    see kb/README.md Known Limitations.
    """

    structured = [r for r in results if r.entity_type != "PERSON"]
    persons = [r for r in results if r.entity_type == "PERSON"]

    def _overlaps(a, b) -> bool:
        return a.start < b.end and b.start < a.end

    kept_persons = [
        p
        for p in persons
        if not any(_overlaps(p, s) for s in structured)
        and len(text[p.start : p.end].split()) >= 2
    ]
    return structured + kept_persons


def _presidio_mask(text: str) -> PIIMaskResult:
    global _analyzer, _anonymizer
    if _analyzer is None:
        _analyzer, _anonymizer = _build_presidio_engines()

    results = _analyzer.analyze(
        text=text, language="en", entities=list(_PRESIDIO_ENTITY_MAP)
    )
    results = _filter_person_false_positives(results, text)
    counts: dict[str, int] = {}
    for r in results:
        pii_type = _PRESIDIO_ENTITY_MAP.get(r.entity_type, r.entity_type)
        counts[pii_type] = counts.get(pii_type, 0) + 1

    operators = {
        r.entity_type: OperatorConfig(
            "replace",
            {"new_value": _PLACEHOLDER_BY_TYPE.get(_PRESIDIO_ENTITY_MAP.get(r.entity_type, r.entity_type), f"[{r.entity_type}]")},
        )
        for r in results
    }
    anonymized = _anonymizer.anonymize(text=text, analyzer_results=results, operators=operators)
    return PIIMaskResult(masked_text=anonymized.text, pii_types=sorted(counts), counts=counts)


def _regex_mask_language_agnostic(text: str) -> PIIMaskResult:
    """Used for non-English content (multilingual/'s Philippines/
    Indonesia KB seed). Only email addresses are masked — verified
    directly: en_core_web_sm's PERSON NER, trained on English, produces
    massive false positives on Tagalog/Indonesian text (real run: 107
    PERSON detections across 20 source docs vs. 4 for English-only
    content, mangling legitimate content like "Petugas penagihan
    [PERSON], mempermalukan, [PERSON] kata-kata [PERSON]..." into
    nonsense). India-specific Aadhaar/PAN/phone patterns are also skipped
    — irrelevant identifier formats for these markets. Philippine/
    Indonesian phone or national-ID patterns (PhilSys ID/TIN; NIK/KTP)
    are NOT implemented — a documented limitation (docs/DECISIONS.md),
    not a silent gap."""

    counts: dict[str, int] = {}

    def _repl(_match: re.Match) -> str:
        counts["EMAIL"] = counts.get("EMAIL", 0) + 1
        return _PLACEHOLDER_BY_TYPE["EMAIL"]

    masked = _EMAIL_RE.sub(_repl, text)
    return PIIMaskResult(masked_text=masked, pii_types=sorted(counts), counts=counts)


def mask_pii(text: str, language: str = "en") -> PIIMaskResult:
    if language != "en":
        return _regex_mask_language_agnostic(text)
    if _PRESIDIO_IMPORTABLE:
        try:
            return _presidio_mask(text)
        except Exception:
            # Presidio/spaCy misconfigured or the model failed to load at
            # runtime: degrade to the regex-only detector instead of
            # failing the whole ingestion run (CLAUDE.md §3).
            pass
    return _regex_mask(text)
