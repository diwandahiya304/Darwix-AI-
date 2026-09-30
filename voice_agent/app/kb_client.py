"""Client for the Q2 KB retrieval API — the ONLY source of facts this
voice agent uses for product/policy/eligibility/objection questions.
Never hardcode facts here or in the system prompt; if the KB has no
grounded answer, this returns FALLBACK_MESSAGE verbatim so the assistant
just relays what the tool says rather than needing to remember an exact
phrase itself — the tool is the source of truth for the fallback wording,
the system prompt just says "when grounded is false, tell the customer
what the tool returned" (see config/system_prompt.md).
"""

from __future__ import annotations

import httpx

from voice_agent.app.models import SearchKBResult
from voice_agent.app.settings import Settings

FALLBACK_MESSAGE = (
    "I don't have that information right now. I can connect you to a "
    "specialist or arrange a callback."
)

_MAX_SPEAKABLE_RESULTS = 2
_MAX_SPEAKABLE_CHARS = 400
_TIMEOUT_SECONDS = 5.0


def _speakable(contents: list[str]) -> str:
    combined = " ".join(c.strip() for c in contents if c.strip())
    if len(combined) > _MAX_SPEAKABLE_CHARS:
        truncated = combined[:_MAX_SPEAKABLE_CHARS].rsplit(" ", 1)[0]
        combined = truncated + "..."
    return combined


def search_knowledge_base(
    query: str, settings: Settings, client: httpx.Client | None = None
) -> SearchKBResult:
    """Calls the Q2 KB's POST /search. Any failure to reach the KB
    (network error, non-2xx response, malformed body) degrades to the
    same ungrounded/fallback result a genuine "no answer" would — a KB
    outage must never be indistinguishable from the agent inventing an
    answer; it must always look exactly like "I don't know," which is
    always the safe behavior."""

    owns_client = client is None
    http_client = client or httpx.Client(base_url=settings.kb_api_base_url, timeout=_TIMEOUT_SECONDS)
    try:
        try:
            response = http_client.post(
                "/search",
                json={
                    "query": query,
                    "top_k": settings.kb_search_top_k,
                    # Q3 added Filipino/Bahasa Indonesia records to the same
                    # index (kb/app/ingest/pipeline.py's extra_raw_dirs).
                    # Without an explicit language filter, cross-lingual
                    # embedding similarity can outrank a correct "no match"
                    # for an English-only bot — see docs/DECISIONS.md
                    # ("cross-lingual ranking unreliable without explicit
                    # filter") and docs/q3_multilingual/gaps.md.
                    "filters": {"language": "en"},
                },
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return SearchKBResult(
                grounded=False, speakable_answer=FALLBACK_MESSAGE, citations=[], category=None
            )
    finally:
        if owns_client:
            http_client.close()

    if not data.get("grounded"):
        return SearchKBResult(
            grounded=False, speakable_answer=FALLBACK_MESSAGE, citations=[], category=None
        )

    results = data.get("results") or []
    if not results:
        return SearchKBResult(
            grounded=False, speakable_answer=FALLBACK_MESSAGE, citations=[], category=None
        )

    top_results = results[:_MAX_SPEAKABLE_RESULTS]
    return SearchKBResult(
        grounded=True,
        speakable_answer=_speakable([r["content"] for r in top_results]),
        citations=[r["citation"] for r in top_results],
        category=results[0].get("category"),
    )
