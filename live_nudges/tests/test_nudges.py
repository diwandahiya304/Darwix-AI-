from live_nudges.app.models import NudgePriority, Signal, SignalLayer, SignalType
from live_nudges.app.nudges import build_nudge, render_message


def _signal(topic: str, signal_type: SignalType = SignalType.COMPLIANCE_RISK) -> Signal:
    return Signal(
        signal_type=signal_type, topic=topic, confidence=0.9, evidence_text="evidence",
        layer=SignalLayer.FAST, segment_id=0, call_time_ms=0,
    )


def test_known_topic_prefixes_render_specific_messages():
    assert "guarantees" in render_message(_signal("compliance:risky_statement")).lower()
    assert "disclosure" in render_message(_signal("compliance:missing_disclosure")).lower()
    assert "frustrated" in render_message(_signal("sentiment:frustration", SignalType.FRUSTRATION)).lower()
    assert "cross-sell" in render_message(_signal("missed_cross_sell:family_floater", SignalType.MISSED_OPPORTUNITY)).lower()


def test_unknown_topic_falls_back_to_a_generic_message():
    message = render_message(_signal("something_unmapped:xyz", SignalType.INTENT_SHIFT))
    assert "intent_shift" in message


def test_message_stays_short():
    for topic in ["compliance:risky_statement", "sentiment:frustration", "missed_cross_sell:family_floater"]:
        message = render_message(_signal(topic))
        assert len(message.split()) <= 16


def test_build_nudge_carries_through_priority_and_signal_fields():
    signal = _signal("compliance:risky_statement")
    nudge = build_nudge(signal, nudge_id="nudge_0001", priority=NudgePriority.CRITICAL,
                         created_at_ms=100.0, expires_at_ms=60_100.0)
    assert nudge.priority == NudgePriority.CRITICAL
    assert nudge.signal_type == SignalType.COMPLIANCE_RISK
    assert nudge.confidence == 0.9
    assert nudge.expires_at_ms == 60_100.0
