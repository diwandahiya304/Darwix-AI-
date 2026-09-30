"""HTML extraction: pull the main content out of a raw web page, stripping
navigation, headers, footers, cookie banners, and sidebars.

Primary extractor: trafilatura, using its markdown output format (not
plain text) so internal headings survive as `#`/`##` lines and lists
survive as `- ` lines — kb.app.ingest.chunk relies on both for
section-aware chunking. Fallback: a BeautifulSoup heuristic (largest
<main>/<article>/<body> text block, headings manually prefixed with `#`)
used when trafilatura returns nothing.

HTML has no natural pagination, so extract_html always returns a single-
entry `pages` list — the "page" is the whole document/section. This keeps
the same `RawDocument.pages` shape as extract_pdf's real per-page list.
"""

from __future__ import annotations

import hashlib

import trafilatura
from bs4 import BeautifulSoup

from kb.app.models import ExtractionFormat, RawDocument, SourceIssue

_BOILERPLATE_TAGS = ("nav", "header", "footer", "aside", "script", "style", "form")
_BOILERPLATE_CLASS_HINTS = (
    "cookie",
    "sidebar",
    "breadcrumb",
    "site-header",
    "site-footer",
    "nav-",
    "menu",
)
_HEADING_TAGS = {"h1": "#", "h2": "##", "h3": "###", "h4": "####"}


def _strip_boilerplate(soup: BeautifulSoup) -> BeautifulSoup:
    for tag in soup.find_all(_BOILERPLATE_TAGS):
        tag.decompose()
    for tag in soup.find_all(True):
        classes = " ".join(tag.get("class", [])).lower()
        tag_id = (tag.get("id") or "").lower()
        if any(hint in classes or hint in tag_id for hint in _BOILERPLATE_CLASS_HINTS):
            tag.decompose()
    return soup


def _fallback_extract(html: str) -> str:
    """BeautifulSoup fallback, used only when trafilatura returns nothing.
    Walks the largest content block's direct text, manually prefixing
    heading tags with markdown `#` markers and <li> items with `- ` so the
    output shape matches trafilatura's markdown mode."""

    soup = BeautifulSoup(html, "lxml")
    soup = _strip_boilerplate(soup)
    candidates = soup.find_all(["main", "article"])
    if not candidates:
        candidates = [soup.body] if soup.body else [soup]
    best = max(candidates, key=lambda c: len(c.get_text(strip=True)), default=None)
    if best is None:
        return ""

    lines: list[str] = []
    for el in best.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = el.get_text(" ", strip=True)
        if not text:
            continue
        if el.name in _HEADING_TAGS:
            lines.append(f"{_HEADING_TAGS[el.name]} {text}")
        elif el.name == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)
    return "\n".join(lines)


def _extract_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return None


def extract_html(html: str, source_path: str) -> tuple[RawDocument, list[SourceIssue]]:
    """Extract main content from a raw HTML string.

    `source_path` is used only as an identifier/label (a repo-relative
    path or a URL) — this function does not fetch anything itself, so it
    works the same whether the HTML came from disk or an HTTP client.
    """

    issues: list[SourceIssue] = []
    text = (
        trafilatura.extract(
            html, output_format="markdown", include_tables=True, favor_recall=True
        )
        or ""
    )
    if not text.strip():
        text = _fallback_extract(html)
        if not text.strip():
            issues.append(
                SourceIssue(
                    file=source_path,
                    location="document",
                    issue_type="extraction_failed",
                    description=(
                        "Neither trafilatura nor the BeautifulSoup fallback "
                        "produced any content."
                    ),
                )
            )

    source_id = hashlib.sha256(source_path.encode("utf-8")).hexdigest()[:16]
    doc = RawDocument(
        source_id=source_id,
        source_path=source_path,
        source_type=ExtractionFormat.HTML,
        title=_extract_title(html),
        pages=[text],
    )
    return doc, issues
