"""Tests app/signals_llm.py's JSON-schema parsing/validation and
signal-mapping using a fake Anthropic-shaped client (same
dependency-injection pattern as voice_agent/sim/chat_sim.py's
`run_llm(..., client=...)`) — no real API key needed to exercise this
code, matching CLAUDE.md §9's "mock external APIs" testing convention."""

from __future__ import annotations

import json

from live_nudges.app.models import Speaker, TranscriptSegment
from live_nudges.app.settings import Settings
from live_nudges.app.signals_llm import LLMSignalExtractor


class _FakeContentBlock:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.content = [_FakeContentBlock(json.dumps(payload))]


class _FakeMessages:
    def __init__(self, payload: dict) -> None:
        self._payload = payload
        self.calls = 0

    def create(self, **kwargs) -> _FakeResponse:
        self.calls += 1
        return _FakeResponse(self._payload)


class _FakeClient:
    def __init__(self, payload: dict) -> None:
        self.messages = _FakeMessages(payload)


def _segment(text: str, window_end_ms: int, is_final: bool = True, segment_id: int = 0) -> TranscriptSegment:
    return TranscriptSegment(
        segment_id=segment_id, speaker=Speaker.AGENT, text=text, is_final=is_final,
        window_start_ms=max(0, window_end_ms - 2000), window_end_ms=window_end_ms, asr_latency_ms=100.0,
    )


def test_without_credentials_and_no_injected_client_returns_no_signals():
    extractor = LLMSignalExtractor(Settings(llm_api_key=None), client=None)
    assert extractor.is_configured() is False
    signals = extractor.maybe_process(_segment("hello", 0))
    assert signals == []


def test_valid_compliance_risk_response_produces_a_signal():
    payload = {
        "intent": "renewal", "topic_shift": False,
        "compliance_risk": {"type": "risky_statement", "evidence": "guaranteed returns"},
        "frustration_score": 0.1, "buying_signal": False, "missed_opportunity": None,
        "callback_needed": False, "confidence": 0.9,
    }
    client = _FakeClient(payload)
    extractor = LLMSignalExtractor(Settings(), client=client)
    signals = extractor.maybe_process(_segment("This plan offers guaranteed returns.", 0))
    assert any(s.topic == "compliance:risky_statement" for s in signals)
    assert client.messages.calls == 1


def test_malformed_json_degrades_to_no_signals_not_a_crash():
    class _BrokenMessages:
        def create(self, **kwargs):
            return _FakeResponse({})  # will be replaced below

    client = _FakeClient({})
    client.messages.create = lambda **kwargs: type("R", (), {"content": [_FakeContentBlock("not json")]})()
    extractor = LLMSignalExtractor(Settings(), client=client)
    signals = extractor.maybe_process(_segment("hello", 0))
    assert signals == []


def test_schema_violation_degrades_to_no_signals():
    client = _FakeClient({"frustration_score": 5.0})  # out of [0,1] range -> validation error
    extractor = LLMSignalExtractor(Settings(), client=client)
    signals = extractor.maybe_process(_segment("hello", 0))
    assert signals == []


def test_min_interval_throttles_repeated_calls():
    payload = {"frustration_score": 0.0, "confidence": 0.0}
    client = _FakeClient(payload)
    extractor = LLMSignalExtractor(Settings(llm_min_interval_seconds=10.0), client=client)
    extractor.maybe_process(_segment("first", 0, segment_id=0))
    extractor.maybe_process(_segment("second", 2000, segment_id=1))  # within 10s -> throttled
    assert client.messages.calls == 1
    extractor.maybe_process(_segment("third", 15000, segment_id=2))  # past the interval
    assert client.messages.calls == 2


def test_partial_segments_still_update_window_but_do_not_call_llm():
    client = _FakeClient({"frustration_score": 0.0, "confidence": 0.0})
    extractor = LLMSignalExtractor(Settings(), client=client)
    signals = extractor.maybe_process(_segment("partial text", 0, is_final=False))
    assert signals == []
    assert client.messages.calls == 0


def test_zero_confidence_response_produces_no_signals_even_if_flags_are_true():
    payload = {
        "frustration_score": 0.9, "buying_signal": True, "callback_needed": True,
        "confidence": 0.0,
    }
    client = _FakeClient(payload)
    extractor = LLMSignalExtractor(Settings(), client=client)
    signals = extractor.maybe_process(_segment("hello", 0))
    assert signals == []
