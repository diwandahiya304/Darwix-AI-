import json
from pathlib import Path

from fastapi.testclient import TestClient

from multilingual.philippines.app.main import app

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
    assert response.json() == {"status": "ok", "market": "philippines"}


def test_webhook_dispatches_set_auto_debit_preference(tmp_path: Path, monkeypatch):
    import multilingual.philippines.app.main as main_module
    from multilingual.common.settings import Settings

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(crm_db_path=str(tmp_path / "crm.sqlite3")))
    payload = _tool_call_payload(
        "call_1", "set_auto_debit_preference", {"policy_number": "POL-001", "enroll": True, "payment_day": 15}
    )
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    result = json.loads(response.json()["results"][0]["result"])
    assert result["preference_id"].startswith("autodebit_")


def test_webhook_unknown_tool_returns_error_result_not_500():
    payload = _tool_call_payload("call_x", "not_a_real_tool", {})
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    result = json.loads(response.json()["results"][0]["result"])
    assert "error" in result
