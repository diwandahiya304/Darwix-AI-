from pathlib import Path

from voice_agent.app.settings import Settings
from voice_agent.app.tools import TOOL_SCHEMAS, TOOLS, dispatch_tool


def test_every_tool_schema_has_a_matching_dispatch_handler():
    schema_names = {schema["function"]["name"] for schema in TOOL_SCHEMAS}
    assert schema_names == set(TOOLS.keys())


def test_dispatch_unknown_tool_returns_error_not_a_crash():
    result = dispatch_tool("not_a_real_tool", {}, Settings())
    assert "error" in result


def test_dispatch_score_lead():
    result = dispatch_tool(
        "score_lead", {"age": 30, "budget": 2000, "intent": "interested"}, Settings()
    )
    assert result["temperature"] == "hot"


def test_dispatch_malformed_arguments_returns_error_not_a_crash():
    # age must be an int — this should fail pydantic validation inside the
    # handler and come back as a reported error, not raise out of dispatch_tool.
    result = dispatch_tool("score_lead", {"age": "not-a-number"}, Settings())
    assert "error" in result


def test_dispatch_create_lead_and_schedule_callback(tmp_path: Path):
    settings = Settings(crm_db_path=str(tmp_path / "crm.sqlite3"))
    lead_result = dispatch_tool(
        "create_lead",
        {"qualification": "warm", "call_summary": "test", "next_action": "callback"},
        settings,
    )
    assert lead_result["lead_id"].startswith("lead_")

    callback_result = dispatch_tool(
        "schedule_callback",
        {"phone": "9000000000", "requested_datetime": "2025-10-05T15:00:00+05:30"},
        settings,
    )
    assert callback_result["callback_id"].startswith("cb_")


def test_dispatch_escalate_to_human(tmp_path: Path, monkeypatch):
    import voice_agent.app.escalation as escalation_module

    monkeypatch.setattr(escalation_module, "_DEFAULT_LOG_PATH", tmp_path / "escalations.jsonl")
    result = dispatch_tool("escalate_to_human", {"reason": "explicit_request"}, Settings())
    assert result["escalated"] is True
