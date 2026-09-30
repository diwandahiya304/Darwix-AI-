import httpx

from voice_agent.app.kb_client import FALLBACK_MESSAGE, search_knowledge_base
from voice_agent.app.settings import Settings


def _client_with_response(payload: dict, status_code: int = 200) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.Client(base_url="http://kb.test", transport=httpx.MockTransport(handler))


def test_grounded_response_returns_speakable_summary_and_citations():
    payload = {
        "query": "waiting period",
        "grounded": True,
        "results": [
            {
                "record_id": "kb_abc_000",
                "title": "FAQ",
                "content": "The waiting period is 24 months.",
                "category": "faq",
                "source_ref": "raw/web/faq.html",
                "version": "1.0.0",
                "dense_score": 0.93,
                "bm25_score": 4.2,
                "fused_score": 0.03,
                "citation": "[kb_abc_000 | raw/web/faq.html | 1.0.0]",
            }
        ],
        "latency_ms": 42.0,
    }
    result = search_knowledge_base("waiting period", Settings(), client=_client_with_response(payload))
    assert result.grounded is True
    assert "24 months" in result.speakable_answer
    assert result.citations == ["[kb_abc_000 | raw/web/faq.html | 1.0.0]"]
    assert result.category == "faq"


def test_ungrounded_response_returns_fallback_message():
    payload = {"query": "weather today", "grounded": False, "results": [], "latency_ms": 10.0}
    result = search_knowledge_base("weather today", Settings(), client=_client_with_response(payload))
    assert result.grounded is False
    assert result.speakable_answer == FALLBACK_MESSAGE
    assert result.citations == []


def test_kb_unreachable_degrades_to_fallback_not_a_crash():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.Client(base_url="http://kb.test", transport=httpx.MockTransport(handler))
    result = search_knowledge_base("anything", Settings(), client=client)
    assert result.grounded is False
    assert result.speakable_answer == FALLBACK_MESSAGE


def test_non_200_response_degrades_to_fallback():
    client = _client_with_response({"detail": "server error"}, status_code=500)
    result = search_knowledge_base("anything", Settings(), client=client)
    assert result.grounded is False
    assert result.speakable_answer == FALLBACK_MESSAGE


def test_request_always_scopes_to_english_language_filter():
    """Q3 added Filipino/Bahasa Indonesia records to the same KB index.
    Without this filter, cross-lingual embedding similarity previously
    caused 3/8 out-of-KB English questions to falsely ground (measured
    hallucination pass rate dropped from 88% to 62%) — see
    docs/DECISIONS.md."""
    import json

    captured_request: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_request["body"] = json.loads(request.content)
        return httpx.Response(200, json={"grounded": False, "results": []})

    client = httpx.Client(base_url="http://kb.test", transport=httpx.MockTransport(handler))
    search_knowledge_base("anything", Settings(), client=client)
    assert captured_request["body"]["filters"] == {"language": "en"}


def test_long_content_is_truncated_for_speakability():
    long_content = "word " * 200
    payload = {
        "grounded": True,
        "results": [
            {
                "record_id": "kb_x",
                "title": "T",
                "content": long_content,
                "category": "policy",
                "source_ref": "raw/x.html",
                "version": "1.0.0",
                "citation": "[kb_x | raw/x.html | 1.0.0]",
            }
        ],
    }
    result = search_knowledge_base("query", Settings(), client=_client_with_response(payload))
    assert len(result.speakable_answer) <= 410
    assert result.speakable_answer.endswith("...")
