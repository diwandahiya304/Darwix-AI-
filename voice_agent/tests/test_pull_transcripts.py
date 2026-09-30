from voice_agent.app.settings import Settings
from voice_agent.scripts.pull_transcripts import main


def test_main_fails_gracefully_without_vapi_api_key(monkeypatch, capsys):
    import voice_agent.scripts.pull_transcripts as script

    monkeypatch.setattr(script, "get_settings", lambda: Settings(vapi_api_key=None))
    exit_code = main()
    assert exit_code == 1
    assert "VAPI_API_KEY" in capsys.readouterr().err


def test_main_fails_gracefully_without_assistant_id(monkeypatch, capsys):
    import voice_agent.scripts.pull_transcripts as script

    monkeypatch.setattr(
        script, "get_settings", lambda: Settings(vapi_api_key="real_key_123", vapi_assistant_id=None)
    )
    exit_code = main()
    assert exit_code == 1
    assert "VAPI_ASSISTANT_ID" in capsys.readouterr().err
