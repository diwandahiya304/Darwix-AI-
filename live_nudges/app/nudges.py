"""Turns a raw Signal into the short (<=~15 words), actionable Nudge text
an agent would actually see. Message templates only — the *decision* of
whether a signal becomes a visible nudge, and at what priority, lives in
app/controller.py."""

from __future__ import annotations

from live_nudges.app.models import Nudge, NudgePriority, Signal

_MESSAGE_BY_TOPIC_PREFIX: list[tuple[str, str]] = [
    ("compliance:risky_statement", "Compliance: that oversells the product — avoid guarantees, restate accurately."),
    ("compliance:missing_disclosure", "Compliance: give the mandatory disclosure before proceeding to close."),
    ("compliance:", "Compliance risk detected — review before proceeding."),
    ("sentiment:frustration", "Customer sounds frustrated — acknowledge their concern before continuing."),
    ("payment_difficulty:", "Customer mentioned payment difficulty — offer a payment-support or callback path."),
    ("buying_signal:", "Buying signal detected — a good moment to move toward closing."),
    ("callback:", "Customer indicated this isn't a good time — offer to schedule a callback."),
    ("missed_cross_sell:", "Missed cross-sell: consider offering the relevant plan before ending the call."),
    ("missed_", "Possible missed opportunity — review before ending the call."),
    ("intent_shift:", "Customer shifted topic — confirm their earlier question was fully addressed."),
]


def render_message(signal: Signal) -> str:
    for prefix, message in _MESSAGE_BY_TOPIC_PREFIX:
        if signal.topic.startswith(prefix):
            return message
    return f"{signal.signal_type.value}: {signal.evidence_text}"[:80]


def build_nudge(
    signal: Signal, nudge_id: str, priority: NudgePriority,
    created_at_ms: float, expires_at_ms: float,
) -> Nudge:
    return Nudge(
        nudge_id=nudge_id,
        signal_type=signal.signal_type,
        topic=signal.topic,
        priority=priority,
        message=render_message(signal),
        confidence=signal.confidence,
        evidence_text=signal.evidence_text,
        layer=signal.layer,
        call_time_ms=signal.call_time_ms,
        created_at_ms=created_at_ms,
        expires_at_ms=expires_at_ms,
    )
