import json

import httpx

from multilingual.common.kb_client import search_localized_knowledge_base
from multilingual.common.settings import Settings

_FALLBACKS = {
    "formal": "Mohon maaf, saya belum memiliki informasi tersebut.",
    "colloquial": "Maaf ya Kak, aku belum ada info soal itu.",
}


def _client_with_response(payload: dict) -> httpx.Client:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json=payload)

    client = httpx.Client(base_url="http://kb.test", transport=httpx.MockTransport(handler))
    client._captured = captured  # type: ignore[attr-defined]
    return client


def test_filters_by_language():
    client = _client_with_response({"grounded": False, "results": []})
    search_localized_knowledge_base(
        "kapan jatuh tempo", "id", _FALLBACKS, Settings(), client=client
    )
    assert client._captured["body"]["filters"] == {"language": "id"}


def test_grounded_response_returns_content_and_citations():
    payload = {
        "grounded": True,
        "results": [
            {
                "record_id": "kb_x",
                "content": "Cicilan jatuh tempo tanggal 25.",
                "category": "faq",
                "citation": "[kb_x | raw/x.html | 1.0.0]",
            }
        ],
    }
    client = _client_with_response(payload)
    result = search_localized_knowledge_base(
        "Selamat siang, Bapak, kapan jatuh tempo?", "id", _FALLBACKS, Settings(), client=client
    )
    assert result.grounded is True
    assert "tanggal 25" in result.speakable_answer
    assert result.register_used == "formal"


def test_ungrounded_response_uses_formal_fallback_for_formal_register():
    client = _client_with_response({"grounded": False, "results": []})
    result = search_localized_knowledge_base(
        "Selamat pagi Bapak, mohon informasinya", "id", _FALLBACKS, Settings(), client=client
    )
    assert result.grounded is False
    assert result.speakable_answer == _FALLBACKS["formal"]
    assert result.register_used == "formal"


def test_ungrounded_response_uses_colloquial_fallback_for_colloquial_register():
    client = _client_with_response({"grounded": False, "results": []})
    result = search_localized_knowledge_base(
        "Halo Kak, cicilannya gimana nih?", "id", _FALLBACKS, Settings(), client=client
    )
    assert result.grounded is False
    assert result.speakable_answer == _FALLBACKS["colloquial"]
    assert result.register_used == "colloquial"


def test_kb_unreachable_degrades_to_localized_fallback_not_a_crash():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(base_url="http://kb.test", transport=httpx.MockTransport(handler))
    result = search_localized_knowledge_base(
        "Halo Kak, gimana ini?", "id", _FALLBACKS, Settings(), client=client
    )
    assert result.grounded is False
    assert result.speakable_answer == _FALLBACKS["colloquial"]
