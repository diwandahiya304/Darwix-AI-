from multilingual.common.settings import Settings
from multilingual.philippines.app.tools import TOOL_SCHEMAS as PH_SCHEMAS
from multilingual.scripts.create_assistant import build_assistant_payload, main


def test_build_assistant_payload_ph_includes_tool_schemas_and_webhook_url():
    payload = build_assistant_payload("philippines", "https://example.ngrok.io")
    assert payload["model"]["tools"] == PH_SCHEMAS
    assert payload["model"]["toolCallUrl"] == "https://example.ngrok.io/webhook"


def test_build_assistant_payload_system_prompt_has_no_fact_markers():
    payload = build_assistant_payload("philippines", "https://example.ngrok.io")
    prompt = payload["model"]["messages"][0]["content"]
    assert "search_knowledge_base" in prompt  # tool-usage rule IS expected
    # no hardcoded fact like a specific premium figure from the KB
    assert "500,000" not in prompt


def test_main_fails_gracefully_without_vapi_api_key(monkeypatch, capsys):
    import multilingual.scripts.create_assistant as script

    monkeypatch.setattr(script, "get_settings", lambda: Settings(vapi_api_key=None))
    exit_code = main(["--market", "philippines"])
    assert exit_code == 1
    assert "VAPI_API_KEY" in capsys.readouterr().err


def test_main_fails_gracefully_without_webhook_base_url(monkeypatch, capsys):
    import multilingual.scripts.create_assistant as script

    monkeypatch.setattr(
        script, "get_settings", lambda: Settings(vapi_api_key="real_key", ph_webhook_base_url=None)
    )
    exit_code = main(["--market", "philippines"])
    assert exit_code == 1
    assert "PH_WEBHOOK_BASE_URL" in capsys.readouterr().err
