"""Standardization: headings, dates, currency/amounts, terminology,
category taxonomy, and form-field naming.

Every function here is small and pure (text/string in, text/string out;
config loading is the only I/O, isolated to load_terminology_map() and
load_taxonomy()) so each rule is independently testable.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from dateutil import parser as date_parser

from kb.app.models import ExtractionFormat, KBSourceType

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

_SMALL_WORDS = {"a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with"}


def to_title_case(heading: str) -> str:
    words = heading.strip().split()
    out = []
    for i, word in enumerate(words):
        lower = word.lower()
        if i != 0 and lower in _SMALL_WORDS:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return " ".join(out)


_DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2}|"
    r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b"
)


def standardize_dates(text: str, dayfirst: bool = True) -> str:
    """Rewrite recognizable date strings to ISO 8601 (YYYY-MM-DD).

    dayfirst=True matches the Indian/Philippine/Indonesian date convention
    (DD/MM/YYYY) used across the source content this KB ingests. A date
    fragment that fails to parse is left untouched rather than raising —
    an unparsable date is a source-quality issue to flag, not a pipeline
    crash.
    """

    def _replace(match: re.Match) -> str:
        raw = match.group(0)
        try:
            parsed = date_parser.parse(raw, dayfirst=dayfirst, fuzzy=False)
        except (ValueError, OverflowError):
            return raw
        return parsed.date().isoformat()

    return _DATE_PATTERN.sub(_replace, text)


_CURRENCY_PATTERN = re.compile(r"(?:Rs\.?|INR|₹)\s?([\d,]+(?:\.\d+)?)", re.IGNORECASE)


def standardize_currency(text: str) -> str:
    """Rewrite Rs./INR/₹ amounts (including Indian digit grouping like
    5,00,000) to a canonical `INR <amount>` form."""

    def _replace(match: re.Match) -> str:
        amount = match.group(1).replace(",", "")
        try:
            value = float(amount)
        except ValueError:
            return match.group(0)
        if value == int(value):
            return f"INR {int(value):,}"
        return f"INR {value:,.2f}"

    return _CURRENCY_PATTERN.sub(_replace, text)


def to_snake_case(field_name: str) -> str:
    """Form field / column name -> snake_case. Handles spaces ("PAN
    Number"), camelCase ("sumAssured"), and acronym runs ("PANNumber")."""

    s = field_name.strip()
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)  # camelCase boundary
    s = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", "_", s)  # ABCWord -> ABC_Word
    s = re.sub(r"[^\w]+", "_", s)  # spaces/punctuation -> _
    s = re.sub(r"_+", "_", s)
    return s.strip("_").lower()


def _load_yaml(name: str) -> dict:
    path = _CONFIG_DIR / name
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_terminology_map() -> dict[str, str]:
    """{synonym_lowercase: canonical_term} built from kb/config/terminology.yaml."""

    raw = _load_yaml("terminology.yaml")
    mapping: dict[str, str] = {}
    for canonical, synonyms in raw.items():
        for synonym in synonyms:
            mapping[synonym.lower()] = canonical.replace("_", " ")
    return mapping


def apply_terminology(text: str, terminology_map: dict[str, str] | None = None) -> str:
    terminology_map = terminology_map if terminology_map is not None else load_terminology_map()
    # Longest synonyms first so multi-word terms match before a shorter
    # synonym that happens to be a substring of them.
    for synonym in sorted(terminology_map, key=len, reverse=True):
        canonical = terminology_map[synonym]
        pattern = re.compile(rf"\b{re.escape(synonym)}\b", re.IGNORECASE)

        def _replace(match: re.Match, canonical: str = canonical) -> str:
            # Case-preserving: a sentence-initial "Sum Insured" shouldn't
            # become a lowercase "sum assured" mid-sentence just because
            # the synonym match itself was case-insensitive.
            if match.group(0)[:1].isupper():
                return canonical[:1].upper() + canonical[1:]
            return canonical

        text = pattern.sub(_replace, text)
    return text


def load_taxonomy() -> list[str]:
    raw = _load_yaml("taxonomy.yaml")
    return raw.get("categories", [])


def canonicalize_category(raw_category: str, taxonomy: list[str] | None = None) -> str:
    """Maps a raw (usually filename-derived) category hint onto the fixed
    taxonomy. Three passes, most to least precise:

    1. Exact match after normalization.
    2. Underscore-token overlap (e.g. "eligibility_form" and
       "eligibility_qualification" share the token "eligibility") — needed
       once the taxonomy has compound category names; a plain substring
       check misses these (neither string literally contains the other).
    3. Plain substring containment, as a looser fallback for a
       single-word category matching part of a compound filename.

    Falls back to "uncategorized" rather than inventing a new category.
    """

    taxonomy = taxonomy if taxonomy is not None else load_taxonomy()
    normalized = raw_category.strip().lower().replace(" ", "_").replace("-", "_")
    if normalized in taxonomy:
        return normalized

    normalized_tokens = set(normalized.split("_"))
    best_category, best_overlap = None, 0
    for category in taxonomy:
        if category == "uncategorized":
            continue
        overlap = len(normalized_tokens & set(category.split("_")))
        if overlap > best_overlap:
            best_category, best_overlap = category, overlap
    if best_category:
        return best_category

    for category in taxonomy:
        if category in normalized or normalized in category:
            return category
    return "uncategorized"


def infer_source_type(
    source_path: str, extraction_format: ExtractionFormat, category: str
) -> KBSourceType:
    """Heuristic mapping onto KBRecord.source_type (website|pdf|form|faq|
    policy). Category wins where it directly names a KB source type (faq,
    policy); otherwise falls back to the underlying extraction format,
    with a filename hint distinguishing a fillable form from a plain PDF.
    This is a heuristic, not an exhaustive classifier — see kb/README.md
    Known Limitations."""

    stem = Path(source_path).stem.lower()
    if category == "faq":
        return KBSourceType.FAQ
    if category == "policy":
        return KBSourceType.POLICY
    if extraction_format == ExtractionFormat.PDF and "form" in stem:
        return KBSourceType.FORM
    if extraction_format == ExtractionFormat.PDF:
        return KBSourceType.PDF
    return KBSourceType.WEBSITE
