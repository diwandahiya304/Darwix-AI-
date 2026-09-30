"""PDF extraction: per-page text and tables via pdfplumber.

Returns one entry per page in `RawDocument.pages` (tables converted to
markdown and inlined into that page's text) — not one flat concatenated
string — so downstream chunks can cite an accurate `source_ref`
(`file#page=N`) instead of just "somewhere in this PDF."

A page that yields neither text nor tables is flagged `extraction_failed`;
if pytesseract and a working Tesseract install are available, we retry
that page through OCR (rasterized via PyMuPDF) before giving up on it.
OCR is a soft dependency: if it's not importable or the Tesseract binary
isn't on PATH, we log the page as failed and move on rather than crashing
the whole pipeline (CLAUDE.md §3 — reliable core first).
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pdfplumber

from kb.app.models import ExtractionFormat, RawDocument, SourceIssue


def _table_to_markdown(table: list[list[str | None]]) -> str:
    rows = [[cell or "" for cell in row] for row in table]
    if not rows:
        return ""
    header, *body = rows
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines)


def _ocr_page(pdf_path: str, page_index: int) -> str | None:
    try:
        import pymupdf
        import pytesseract
        from PIL import Image
    except ImportError:
        return None
    try:
        pdf_doc = pymupdf.open(pdf_path)
        page = pdf_doc[page_index]
        pixmap = page.get_pixmap(dpi=200)
        image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        text = pytesseract.image_to_string(image).strip()
        return text or None
    except Exception:
        # Covers both "Tesseract binary not on PATH" and any PyMuPDF
        # rasterization failure — OCR is best-effort, never fatal.
        return None


def extract_pdf(
    pdf_path: str, display_path: str | None = None
) -> tuple[RawDocument, list[SourceIssue]]:
    """`pdf_path` is the real filesystem path used to open the file.
    `display_path` (defaults to `pdf_path`) is what ends up in the
    RawDocument/SourceIssue records — pass a repo-relative path so
    source_issues.json and derived record_ids don't bake in a
    machine-specific absolute path.
    """

    label = display_path or pdf_path
    issues: list[SourceIssue] = []
    pages: list[str] = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = (page.extract_text() or "").strip()
            page_tables = page.extract_tables() or []
            tables_md = [_table_to_markdown(t) for t in page_tables]

            if not page_text and not page_tables:
                ocr_text = _ocr_page(pdf_path, i)
                if ocr_text:
                    pages.append(ocr_text)
                    issues.append(
                        SourceIssue(
                            file=label,
                            location=f"page_{i + 1}",
                            issue_type="extraction_recovered_via_ocr",
                            description=(
                                "No embedded text/tables; recovered via OCR fallback."
                            ),
                        )
                    )
                else:
                    pages.append("")
                    issues.append(
                        SourceIssue(
                            file=label,
                            location=f"page_{i + 1}",
                            issue_type="extraction_failed",
                            description=(
                                "No embedded text/tables, and OCR was unavailable "
                                "or produced nothing."
                            ),
                        )
                    )
            else:
                combined = page_text
                if tables_md:
                    combined = (combined + "\n\n" + "\n\n".join(tables_md)).strip()
                pages.append(combined)

    source_id = hashlib.sha256(label.encode("utf-8")).hexdigest()[:16]
    doc = RawDocument(
        source_id=source_id,
        source_path=label,
        source_type=ExtractionFormat.PDF,
        title=Path(pdf_path).stem.replace("_", " ").title(),
        pages=pages,
    )
    return doc, issues
