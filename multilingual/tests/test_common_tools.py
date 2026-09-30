from pathlib import Path

import httpx

from multilingual.common.settings import Settings
from multilingual.common.tools import COMMON_TOOL_SCHEMAS, build_common_tools, dispatch_tool


def test_common_tool_schemas_have_matching_handlers():
    tools = build_common_tools("id", {"formal": "f", "colloquial": "c"})
    schema_names = {s["function"]["name"] for s in COMMON_TOOL_SCHEMAS}
    assert schema_names == set(tools.keys())


def test_dispatch_unknown_tool_returns_error_not_a_crash():
    tools = build_common_tools("id", {"formal": "f", "colloquial": "c"})
    result = dispatch_tool("not_real", {}, tools, Settings())
    assert "error" in result


def test_dispatch_search_knowledge_base_is_language_scoped_and_localized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"grounded": False, "results": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    tools = build_common_tools("id", {"formal": "Mohon maaf.", "colloquial": "Maaf ya Kak."})
    result = dispatch_tool(
        "search_knowledge_base",
        {"query": "cicilan", "customer_utterance": "Halo Kak, cicilannya gimana?"},
        tools,
        Settings(),
        kb_http_client=client,
    )
    assert result["grounded"] is False
    assert result["speakable_answer"] == "Maaf ya Kak."


def test_dispatch_schedule_callback_reuses_voice_agent_crm(tmp_path: Path):
    tools = build_common_tools("fil", {"formal": "f", "colloquial": "c"})
    settings = Settings(crm_db_path=str(tmp_path / "crm.sqlite3"))
    result = dispatch_tool(
        "schedule_callback",
        {"phone": "09171234567", "requested_datetime": "2025-10-05T15:00:00+08:00"},
        tools,
        settings,
    )
    assert result["callback_id"].startswith("cb_")


def test_dispatch_escalate_to_human_reuses_voice_agent_escalation(tmp_path: Path, monkeypatch):
    import voice_agent.app.escalation as escalation_module

    monkeypatch.setattr(escalation_module, "_DEFAULT_LOG_PATH", tmp_path / "escalations.jsonl")
    tools = build_common_tools("fil", {"formal": "f", "colloquial": "c"})
    result = dispatch_tool("escalate_to_human", {"reason": "explicit_request"}, tools, Settings())
    assert result["escalated"] is True
