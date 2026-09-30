from live_nudges.app.controller import NudgeController
from live_nudges.app.models import NudgePriority, Signal, SignalLayer, SignalType
from live_nudges.app.settings import Settings


def _signal(signal_type: SignalType, confidence: float, topic: str = "sentiment:frustration",
            call_time_ms: int = 0, evidence_text: str = "evidence") -> Signal:
    return Signal(
        signal_type=signal_type, topic=topic, confidence=confidence,
        evidence_text=evidence_text, layer=SignalLayer.FAST, segment_id=0, call_time_ms=call_time_ms,
    )


def test_below_per_type_confidence_threshold_is_suppressed():
    # FRUSTRATION's floor is 0.6 even though the global default is also 0.6
    controller = NudgeController(Settings())
    nudge = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.5), now_ms=0)
    assert nudge is None
    assert controller.suppressed()[0].reason == "below_confidence_threshold"


def test_compliance_has_a_lower_confidence_floor_than_intent_shift():
    controller = NudgeController(Settings(nudge_confidence_threshold=0.0))
    compliance_nudge = controller.evaluate(
        _signal(SignalType.COMPLIANCE_RISK, 0.55, topic="compliance:risky_statement"), now_ms=0,
    )
    intent_nudge = controller.evaluate(
        _signal(SignalType.INTENT_SHIFT, 0.55, topic="intent_shift:a->b"), now_ms=1000,
    )
    assert compliance_nudge is not None  # 0.55 clears compliance's 0.5 floor
    assert intent_nudge is None          # 0.55 does not clear intent_shift's 0.75 floor


def test_above_threshold_emits_a_nudge_with_correct_priority():
    controller = NudgeController(Settings())
    nudge = controller.evaluate(_signal(SignalType.COMPLIANCE_RISK, 0.9, topic="compliance:risky_statement"), now_ms=0)
    assert nudge is not None
    assert nudge.priority == NudgePriority.CRITICAL


def test_duplicate_within_cooldown_is_suppressed():
    controller = NudgeController(Settings(nudge_cooldown_seconds=30))
    first = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8), now_ms=0)
    second = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8), now_ms=5_000)
    assert first is not None
    assert second is None
    assert controller.suppressed()[0].reason == "cooldown_duplicate"


def test_same_topic_fires_again_after_cooldown_elapses():
    controller = NudgeController(Settings(nudge_cooldown_seconds=30))
    controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8), now_ms=0)
    second = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8), now_ms=31_000)
    assert second is not None


def test_different_topics_do_not_share_a_cooldown():
    controller = NudgeController(Settings(nudge_cooldown_seconds=30))
    controller.evaluate(_signal(SignalType.CALLBACK_NEEDED, 0.8, topic="topic_a"), now_ms=0)
    second = controller.evaluate(_signal(SignalType.CALLBACK_NEEDED, 0.8, topic="topic_b"), now_ms=1_000)
    assert second is not None


def test_active_nudges_expire_after_expiry_window():
    controller = NudgeController(Settings(nudge_expiry_seconds=10))
    controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8), now_ms=0)
    assert len(controller.active_nudges(now_ms=5_000)) == 1
    assert len(controller.active_nudges(now_ms=11_000)) == 0


def test_history_keeps_expired_nudges():
    controller = NudgeController(Settings(nudge_expiry_seconds=10))
    controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8), now_ms=0)
    controller.active_nudges(now_ms=11_000)
    assert len(controller.history()) == 1


def test_active_nudges_sorted_by_priority_critical_first():
    controller = NudgeController(Settings(nudge_cooldown_seconds=0))
    controller.evaluate(_signal(SignalType.CALLBACK_NEEDED, 0.8, topic="t1"), now_ms=0)
    controller.evaluate(_signal(SignalType.COMPLIANCE_RISK, 0.9, topic="t2"), now_ms=1)
    controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8, topic="t3"), now_ms=2)
    active = controller.active_nudges(now_ms=3)
    assert [n.priority for n in active] == [NudgePriority.CRITICAL, NudgePriority.HIGH, NudgePriority.NORMAL]


def test_semantic_duplicate_suppressed_when_embed_fn_reports_high_similarity():
    def fake_embed(text: str):
        return [1.0, 0.0]  # identical vector for every input -> always "similar"

    controller = NudgeController(Settings(nudge_cooldown_seconds=0), embed_fn=fake_embed)
    first = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8, topic="topic_a", evidence_text="I'm upset"), now_ms=0)
    second = controller.evaluate(
        _signal(SignalType.FRUSTRATION, 0.8, topic="topic_b", evidence_text="this is annoying"), now_ms=1_000,
    )
    assert first is not None
    assert second is None
    assert controller.suppressed()[0].reason == "semantic_duplicate"


def test_semantic_dedup_disabled_when_embed_fn_is_none():
    controller = NudgeController(Settings(nudge_cooldown_seconds=0), embed_fn=None)
    first = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8, topic="topic_a"), now_ms=0)
    second = controller.evaluate(_signal(SignalType.FRUSTRATION, 0.8, topic="topic_b"), now_ms=1_000)
    assert first is not None
    assert second is not None
