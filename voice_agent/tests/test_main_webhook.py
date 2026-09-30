import json
from pathlib import Path

from fastapi.testclient import TestClient

from voice_agent.app.main import app

client = TestClient(app)


def _tool_call_payload(tool_id: str, name: str, arguments: dict) -> dict:
    return {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {"id": tool_id, "type": "function", "function": {"name": name, "arguments": arguments}}
            ],
        }
    }


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_webhook_dispatches_score_lead_tool_call():
    payload = _tool_call_payload(
        "call_1", "score_lead", {"age": 30, "budget": 2000, "intent": "interested"}
    )
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["toolCallId"] == "call_1"
    result = json.loads(body["results"][0]["result"])
    assert result["temperature"] == "hot"


def test_webhook_handles_multiple_tool_calls_in_one_message(tmp_path: Path, monkeypatch):
    import voice_agent.app.main as main_module
    from voice_agent.app.settings import Settings

    monkeypatch.setattr(
        main_module, "get_settings", lambda: Settings(crm_db_path=str(tmp_path / "crm.sqlite3"))
    )
    payload = {
        "message": {
            "type": "tool-calls",
            "toolCallList": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {"name": "score_lead", "arguments": {"age": 30, "intent": "interested"}},
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {
                        "name": "create_lead",
                        "arguments": {"qualification": "warm", "call_summary": "s", "next_action": "n"},
                    },
                },
            ],
        }
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["toolCallId"] == "call_a"
    assert body["results"][1]["toolCallId"] == "call_b"


def test_webhook_unknown_tool_returns_error_result_not_500():
    payload = _tool_call_payload("call_x", "not_a_real_tool", {})
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    result = json.loads(response.json()["results"][0]["result"])
    assert "error" in result
