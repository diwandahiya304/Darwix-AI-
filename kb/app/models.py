"""Shared pydantic models for the kb/ pipeline and retrieval layer.

Data flow: raw extraction (RawDocument, one per source file, one entry in
`pages` per PDF page / single entry for HTML) -> cleaned per-page text
(CleanedPage) rolled up into a CleanedDocument (used for whole-document
dedup) -> category-aware chunking -> versioned KBRecord (the unit the
retrieval API actually indexes and serves). See kb/README.md for the full
narrative.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class ExtractionFormat(str, Enum):
    """The raw file format extraction dealt with — distinct from
    KBSourceType below, which describes a KB record's content nature and
    is derived from this plus category/filename heuristics."""

    HTML = "html"
    PDF = "pdf"


class KBSourceType(str, Enum):
    """KBRecord.source_type — what kind of thing this record's content
    came from, for citation/filtering purposes."""

    WEBSITE = "website"
    PDF = "pdf"
    FORM = "form"
    FAQ = "faq"
    POLICY = "policy"


class Audience(str, Enum):
    CUSTOMER = "customer"
    AGENT = "agent"


class RecordStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class SourceIssue(BaseModel):
    """One flagged extraction failure or obvious source error.

    Written to data/processed/source_issues.json — never contains PII,
    only file/location/issue metadata.
    """

    file: str
    location: str
    issue_type: str
    description: str


class RawDocument(BaseModel):
    """Output of the extraction stage, before any cleaning.

    `pages` has one entry per PDF page (with that page's tables already
    inlined as markdown), or a single entry for HTML (a "page" there is
    the whole document/section) — this is what lets downstream chunks
    cite an accurate `source_ref` (`file#page=N` for PDF, bare `file` for
    HTML) instead of just "somewhere in this document."
    """

    source_id: str
    source_path: str
    source_type: ExtractionFormat
    title: str | None = None
    pages: list[str] = Field(default_factory=list)


class CleanedPage(BaseModel):
    page_number: int  # 1-indexed
    text: str
    pii: bool = False
    pii_types: list[str] = Field(default_factory=list)


class CleanedDocument(BaseModel):
    """Output of the cleaning/standardization/PII-masking stage, one per
    source document (pre-chunking). Dedup operates on the whole document
    (`joined_text()`); chunking operates per-page so citations stay
    accurate."""

    source_id: str
    source_path: str
    title: str
    category: str
    source_type: KBSourceType
    pages: list[CleanedPage]
    language: str = "en"
    pii: bool = False
    pii_types: list[str] = Field(default_factory=list)
    merged_source_ids: list[str] = Field(default_factory=list)

    def joined_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


class KBRecord(BaseModel):
    """The unit the retrieval API indexes and serves. Every field is
    traceable back to a source; see kb/README.md for the full schema
    rationale and kb/CHANGELOG.md for how `version`/`status` evolve."""

    record_id: str
    title: str
    content: str
    category: str
    subcategory: str | None = None
    source_type: KBSourceType
    source_ref: str  # e.g. "raw/pdfs/policy_terms.pdf#page=1" or "raw/web/faq.html"
    source_ids_merged: list[str] = Field(default_factory=list)
    version: str = "1.0.0"
    created_at: str
    updated_at: str
    pii: bool = False
    pii_types: list[str] = Field(default_factory=list)
    language: str = "en"
    audience: Audience = Audience.CUSTOMER
    keywords: list[str] = Field(default_factory=list)
    content_hash: str
    status: RecordStatus = RecordStatus.ACTIVE

    # Internal lineage fields beyond the requested minimum — not asked
    # for explicitly, but needed to reconstruct which source chunk this
    # is without re-deriving it from record_id string parsing.
    parent_source_id: str
    chunk_index: int


class PipelineCounts(BaseModel):
    docs_in: int = 0
    chunks_out: int = 0
    exact_duplicates_removed: int = 0
    near_duplicates_removed: int = 0
    extraction_failures: int = 0
    pii_records: int = 0
    records_versioned: int = 0  # records whose content changed vs. the prior run


class BeforeAfterExample(BaseModel):
    source_id: str
    before: str
    after: str
    note: str = ""


class PipelineReport(BaseModel):
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    counts: PipelineCounts
    pii_counts_by_type: dict[str, int] = Field(default_factory=dict)
    examples: list[BeforeAfterExample] = Field(default_factory=list)
