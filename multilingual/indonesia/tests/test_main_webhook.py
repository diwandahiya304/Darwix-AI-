import json
from pathlib import Path

from fastapi.testclient import TestClient

from multilingual.indonesia.app.main import app

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
    assert response.json() == {"status": "ok", "market": "indonesia"}


def test_webhook_dispatches_record_promise_to_pay(tmp_path: Path, monkeypatch):
    import multilingual.indonesia.app.main as main_module
    from multilingual.common.settings import Settings

    monkeypatch.setattr(main_module, "get_settings", lambda: Settings(crm_db_path=str(tmp_path / "crm.sqlite3")))
    payload = _tool_call_payload(
        "call_1", "record_promise_to_pay", {"loan_id": "LOAN-001", "promise_date": "2025-10-10", "amount": 1250000}
    )
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    result = json.loads(response.json()["results"][0]["result"])
    assert result["promise_id"].startswith("promise_")


def test_webhook_unknown_tool_returns_error_result_not_500():
    payload = _tool_call_payload("call_x", "not_a_real_tool", {})
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    result = json.loads(response.json()["results"][0]["result"])
    assert "error" in result
