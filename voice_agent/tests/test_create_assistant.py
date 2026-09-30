from voice_agent.app.settings import Settings
from voice_agent.app.tools import TOOL_SCHEMAS
from voice_agent.scripts.create_assistant import build_assistant_payload, main


def test_build_assistant_payload_includes_every_tool_schema():
    payload = build_assistant_payload("https://example.ngrok.io")
    assert payload["model"]["tools"] == TOOL_SCHEMAS


def test_build_assistant_payload_points_tool_call_url_at_webhook():
    payload = build_assistant_payload("https://example.ngrok.io/")
    assert payload["model"]["toolCallUrl"] == "https://example.ngrok.io/webhook"


def test_build_assistant_payload_system_prompt_has_no_fact_markers():
    payload = build_assistant_payload("https://example.ngrok.io")
    prompt = payload["model"]["messages"][0]["content"]
    # The system prompt must never contain KB-owned facts like premium
    # figures or waiting-period numbers — those come from
    # search_knowledge_base at call time, never from the prompt itself.
    assert "24 months" not in prompt
    assert "search_knowledge_base" in prompt  # tool-usage rule IS expected


def test_main_fails_gracefully_without_vapi_api_key(monkeypatch, capsys):
    import voice_agent.scripts.create_assistant as script

    monkeypatch.setattr(script, "get_settings", lambda: Settings(vapi_api_key=None))
    exit_code = main()
    assert exit_code == 1
    assert "VAPI_API_KEY" in capsys.readouterr().err


def test_main_fails_gracefully_without_webhook_base_url(monkeypatch, capsys):
    import voice_agent.scripts.create_assistant as script

    monkeypatch.setattr(
        script, "get_settings", lambda: Settings(vapi_api_key="real_key_123", webhook_base_url=None)
    )
    exit_code = main()
    assert exit_code == 1
    assert "WEBHOOK_BASE_URL" in capsys.readouterr().err
