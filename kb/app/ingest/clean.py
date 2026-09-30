"""Residual text cleanup after extraction.

trafilatura/BeautifulSoup already strip most nav/header/footer markup, but
some boilerplate survives as plain text lines (e.g. "All rights reserved",
"Subscribe to our newsletter"). This module drops those known patterns and
collapses excess whitespace. Kept deliberately small and pure — no I/O.
"""

from __future__ import annotations

import re

_BOILERPLATE_LINE_PATTERNS = [
    r"^skip to (main )?content$",
    r"^all rights reserved.*$",
    r"^subscribe to our newsletter.*$",
    r"^\W*©.*$",
    r"^follow us on.*$",
    r"^cookie(s)? (policy|preference|banner).*$",
    r"^we use cookies.*$",
    r"^home\s*\|\s*about\s*\|\s*contact.*$",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _BOILERPLATE_LINE_PATTERNS]


def strip_boilerplate_lines(text: str) -> str:
    kept = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if any(p.match(stripped) for p in _COMPILED):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def collapse_whitespace(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    return collapse_whitespace(strip_boilerplate_lines(text))
