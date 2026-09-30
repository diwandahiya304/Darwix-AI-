"""Chunking: turn a cleaned page's text into short, self-contained,
speakable KB record bodies.

Strategy depends on the record's category (`chunk_document`'s `category`
argument, already canonicalized against kb/config/taxonomy.yaml by the
time it reaches here):

- **faq** — one chunk per Q/A pair. The whole point of an FAQ record is
  that it answers exactly one question; splitting any other way (by
  word count, say) would separate a question from its answer.
- **objection_handling** — one chunk per objection + its approved
  response, same reasoning as FAQ.
- **eligibility_qualification** — one chunk per bulleted/numbered rule,
  each keeping its explicit condition intact and atomic (a voice agent
  citing "the applicant must be under 65" shouldn't also drag in three
  unrelated rules).
- **everything else** — split by heading first (trafilatura's markdown
  output, and the BeautifulSoup fallback, both preserve `#`/`##` heading
  markers — see extract_html.py), then by sentence boundaries within each
  section, targeting 80-200 words per chunk so each one is speakable in
  a single voice turn without either being cut short or running on.

If the category-specific parser finds nothing to split on (e.g. an FAQ
page that isn't actually formatted as Q:/A: lines), we fall back to the
generic heading+sentence chunker rather than silently producing zero
records for that source.

Every chunk is made self-contained by prepending the document title (and
section heading, if any): a chunk must make sense read completely on its
own, since the voice agent reads exactly one chunk aloud per turn, never
the surrounding document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")
_BULLET_RE = re.compile(r"^(?:[-*]|\d+[.)])\s+(\S.*)$")

_TARGET_MIN_WORDS = 80
_TARGET_MAX_WORDS = 200


@dataclass
class _Chunk:
    content: str
    heading: str | None = None  # section heading this chunk came from, if any


def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(paragraph) if s.strip()]


def _chunk_sentences_by_wordcount(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    buffer: list[str] = []

    def _word_count() -> int:
        return sum(len(s.split()) for s in buffer)

    def _flush() -> None:
        if buffer:
            chunks.append(" ".join(buffer))
            buffer.clear()

    for paragraph in paragraphs:
        for sentence in _split_sentences(paragraph):
            buffer.append(sentence)
            if _word_count() >= _TARGET_MAX_WORDS:
                _flush()
        if _word_count() >= _TARGET_MIN_WORDS:
            _flush()
    _flush()
    return chunks


def _split_by_headings(text: str) -> list[tuple[str | None, str]]:
    """[(heading_or_None, section_body), ...]. Text before the first
    heading (if any) is its own section with heading=None."""

    sections: list[tuple[str | None, list[str]]] = [(None, [])]
    for line in text.split("\n"):
        match = _HEADING_RE.match(line.strip())
        if match:
            sections.append((match.group(2).strip(), []))
        else:
            sections[-1][1].append(line)
    return [
        (heading, "\n".join(body_lines))
        for heading, body_lines in sections
        if any(line.strip() for line in body_lines)
    ]


def _chunk_generic(text: str) -> list[_Chunk]:
    return [
        _Chunk(content=body_chunk, heading=heading)
        for heading, body in _split_by_headings(text)
        for body_chunk in _chunk_sentences_by_wordcount(body)
    ]


def _strip_heading_marker(line: str) -> str:
    return _HEADING_RE.sub(r"\2", line).strip()


def _chunk_faq_pairs(text: str) -> list[_Chunk]:
    lines = [_strip_heading_marker(l) for l in text.split("\n") if l.strip()]
    chunks: list[_Chunk] = []
    pending_q: str | None = None
    for line in lines:
        if line.lower().startswith("q:"):
            pending_q = line
        elif line.lower().startswith("a:") and pending_q:
            chunks.append(_Chunk(content=f"{pending_q} {line}"))
            pending_q = None
    return chunks


def _chunk_objection_pairs(text: str) -> list[_Chunk]:
    lines = [_strip_heading_marker(l) for l in text.split("\n") if l.strip()]
    chunks: list[_Chunk] = []
    pending: str | None = None
    for line in lines:
        if line.lower().startswith("objection:"):
            pending = line
        elif line.lower().startswith("response:") and pending:
            chunks.append(_Chunk(content=f"{pending} {line}"))
            pending = None
    return chunks


def _chunk_eligibility_rules(text: str) -> list[_Chunk]:
    chunks: list[_Chunk] = []
    for line in text.split("\n"):
        match = _BULLET_RE.match(line.strip())
        if match:
            chunks.append(_Chunk(content=match.group(1).strip()))
    return chunks


_CATEGORY_CHUNKERS = {
    "faq": _chunk_faq_pairs,
    "objection_handling": _chunk_objection_pairs,
    "eligibility_qualification": _chunk_eligibility_rules,
}


def _make_self_contained(title: str, chunk: _Chunk) -> str:
    if chunk.content.lower().startswith(title.lower()):
        return chunk.content
    prefix = title
    if chunk.heading and chunk.heading.lower() != title.lower():
        prefix = f"{title} — {chunk.heading}"
    return f"{prefix}: {chunk.content}"


def chunk_document(text: str, category: str, title: str) -> list[str]:
    chunker = _CATEGORY_CHUNKERS.get(category)
    chunks = chunker(text) if chunker else []
    if not chunks:
        chunks = _chunk_generic(text)
    return [_make_self_contained(title, c) for c in chunks if c.content.strip()]
