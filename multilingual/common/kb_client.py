"""Language-scoped KB client: wraps kb/'s /search API the same way
voice_agent/app/kb_client.py does, but always filters by `language`
(reusing the SAME retrieval index kb/ builds — see
kb/app/ingest/pipeline.py's `extra_raw_dirs` and
multilingual/scripts/ingest_multilingual_kb.py) and returns a fallback
message matching the customer's DETECTED REGISTER (formal vs colloquial)
instead of one fixed message — the bot must never switch to English
unexpectedly and must mirror the customer's register (Q3 general
requirement).
"""

from __future__ import annotations

import httpx

from multilingual.common.models import LocalizedSearchKBResult
from multilingual.common.register import detect_register
from multilingual.common.settings import Settings

_MAX_SPEAKABLE_RESULTS = 2
_MAX_SPEAKABLE_CHARS = 400
_TIMEOUT_SECONDS = 5.0


def _speakable(contents: list[str]) -> str:
    combined = " ".join(c.strip() for c in contents if c.strip())
    if len(combined) > _MAX_SPEAKABLE_CHARS:
        combined = combined[:_MAX_SPEAKABLE_CHARS].rsplit(" ", 1)[0] + "..."
    return combined


def search_localized_knowledge_base(
    query: str,
    language: str,
    fallback_messages: dict[str, str],
    settings: Settings,
    customer_utterance: str | None = None,
    client: httpx.Client | None = None,
) -> LocalizedSearchKBResult:
    """`fallback_messages`: {"formal": "...", "colloquial": "..."} in the
    target language/market — see each market's
    config/fallback_messages.yaml. `customer_utterance` (defaults to
    `query`) drives register detection to pick which variant to relay.
    Any failure to reach the KB (network error, non-2xx, malformed body)
    degrades to the same localized fallback a genuine "no answer" would —
    same reliability principle as voice_agent/app/kb_client.py."""

    register = detect_register(customer_utterance or query, language)
    fallback_text = fallback_messages.get(register.value) or fallback_messages.get("formal", "")

    def _fallback_result() -> LocalizedSearchKBResult:
        return LocalizedSearchKBResult(
            grounded=False, speakable_answer=fallback_text, citations=[], category=None,
            register_used=register.value,
        )

    owns_client = client is None
    http_client = client or httpx.Client(base_url=settings.kb_api_base_url, timeout=_TIMEOUT_SECONDS)
    try:
        try:
            response = http_client.post(
                "/search",
                json={
                    "query": query,
                    "top_k": settings.kb_search_top_k,
                    "filters": {"language": language},
                },
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError):
            return _fallback_result()
    finally:
        if owns_client:
            http_client.close()

    if not data.get("grounded"):
        return _fallback_result()

    results = data.get("results") or []
    if not results:
        return _fallback_result()

    top_results = results[:_MAX_SPEAKABLE_RESULTS]
    return LocalizedSearchKBResult(
        grounded=True,
        speakable_answer=_speakable([r["content"] for r in top_results]),
        citations=[r["citation"] for r in top_results],
        category=results[0].get("category"),
        register_used=register.value,
    )
