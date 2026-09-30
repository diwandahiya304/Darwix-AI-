import json
from pathlib import Path

import httpx

from voice_agent.app.escalation import escalate_to_human
from voice_agent.app.models import EscalateArgs
from voice_agent.app.settings import Settings


def test_logs_only_when_nothing_configured(tmp_path: Path):
    log_path = tmp_path / "escalations.jsonl"
    result = escalate_to_human(
        EscalateArgs(reason="explicit_request", call_id="call_1"),
        settings=Settings(),
        log_path=log_path,
    )
    assert result.escalated is True
    assert result.method == "logged_only"
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["reason"] == "explicit_request"


def test_transfer_number_configured_logs_transfer_logged(tmp_path: Path):
    log_path = tmp_path / "escalations.jsonl"
    settings = Settings(escalation_transfer_number="+911234567890")
    result = escalate_to_human(
        EscalateArgs(reason="distress"), settings=settings, log_path=log_path
    )
    assert result.method == "transfer_logged"
    entry = json.loads(log_path.read_text(encoding="utf-8").strip())
    assert entry["transfer_number"] == "+911234567890"


def test_webhook_configured_posts_and_logs_webhook_method(tmp_path: Path):
    log_path = tmp_path / "escalations.jsonl"
    received = []

    def handler(request: httpx.Request) -> httpx.Response:
        received.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(escalation_webhook_url="http://escalation.test/hook")
    result = escalate_to_human(
        EscalateArgs(reason="complaint", context="Customer says agent was rude."),
        settings=settings,
        client=client,
        log_path=log_path,
    )
    assert result.method == "webhook"
    assert received[0]["reason"] == "complaint"


def test_webhook_failure_falls_back_to_logged_only_not_a_crash(tmp_path: Path):
    log_path = tmp_path / "escalations.jsonl"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    settings = Settings(escalation_webhook_url="http://escalation.test/hook")
    result = escalate_to_human(
        EscalateArgs(reason="distress"), settings=settings, client=client, log_path=log_path
    )
    assert result.method == "logged_only"
    assert log_path.exists()


def test_multiple_escalations_append_not_overwrite(tmp_path: Path):
    log_path = tmp_path / "escalations.jsonl"
    settings = Settings()
    escalate_to_human(EscalateArgs(reason="a"), settings=settings, log_path=log_path)
    escalate_to_human(EscalateArgs(reason="b"), settings=settings, log_path=log_path)
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
