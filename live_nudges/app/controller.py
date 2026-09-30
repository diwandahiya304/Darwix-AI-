"""Nudge control: per-signal-type confidence thresholds, duplicate
suppression (topic+cooldown, plus a semantic-similarity check across
differently-worded evidence for the same signal type), cooldowns, topic
grouping, priority preemption, and expiry. Every suppression decision is
logged with its reason (`suppressed()`) — this module is what the
false-positive analysis in docs/q4_live_nudges/quality_report.md is
really evaluating, more than the signal-detection rules themselves.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from live_nudges.app.models import Nudge, NudgePriority, Signal, SignalType
from live_nudges.app.nudges import build_nudge
from live_nudges.app.settings import Settings

# Per-signal-type confidence floors. A global `settings.nudge_confidence_
# threshold` also applies as a baseline; whichever is higher wins for a
# given signal type. Compliance is intentionally the most permissive
# (better to over-flag a compliance risk than miss one); low-value/noisy
# signals like a bare topic shift are the strictest.
_CONFIDENCE_THRESHOLD_BY_TYPE: dict[SignalType, float] = {
    SignalType.COMPLIANCE_RISK: 0.5,
    SignalType.FRUSTRATION: 0.6,
    SignalType.PAYMENT_DIFFICULTY: 0.6,
    SignalType.CALLBACK_NEEDED: 0.6,
    SignalType.MISSED_OPPORTUNITY: 0.65,
    SignalType.BUYING_SIGNAL: 0.7,
    SignalType.INTENT_SHIFT: 0.75,
}

# Priority preemption ordering — CRITICAL nudges always sort first in the
# active queue (dashboard/CLI display), then HIGH, then NORMAL.
_PRIORITY_BY_TYPE: dict[SignalType, NudgePriority] = {
    SignalType.COMPLIANCE_RISK: NudgePriority.CRITICAL,
    SignalType.FRUSTRATION: NudgePriority.HIGH,
    SignalType.PAYMENT_DIFFICULTY: NudgePriority.HIGH,
    SignalType.MISSED_OPPORTUNITY: NudgePriority.NORMAL,
    SignalType.BUYING_SIGNAL: NudgePriority.NORMAL,
    SignalType.CALLBACK_NEEDED: NudgePriority.NORMAL,
    SignalType.INTENT_SHIFT: NudgePriority.NORMAL,
}

_PRIORITY_SORT_ORDER = {NudgePriority.CRITICAL: 0, NudgePriority.HIGH: 1, NudgePriority.NORMAL: 2}


@dataclass
class SuppressionEvent:
    signal: Signal
    reason: str  # below_confidence_threshold | cooldown_duplicate | semantic_duplicate


def _confidence_floor(settings: Settings, signal_type: SignalType) -> float:
    return max(settings.nudge_confidence_threshold, _CONFIDENCE_THRESHOLD_BY_TYPE[signal_type])


@dataclass
class NudgeController:
    settings: Settings
    embed_fn: object = None  # (text: str) -> list[float] | None; None disables semantic dedup (see _semantic_similarity)
    _last_emitted_at_ms: dict[str, float] = field(default_factory=dict)
    _last_embedding_by_type: dict[SignalType, tuple[list[float], str]] = field(default_factory=dict)
    _active: list[Nudge] = field(default_factory=list)
    _history: list[Nudge] = field(default_factory=list)
    _suppressed: list[SuppressionEvent] = field(default_factory=list)
    _counter: int = 0

    def evaluate(self, signal: Signal, now_ms: float) -> Nudge | None:
        self._expire(now_ms)

        if signal.confidence < _confidence_floor(self.settings, signal.signal_type):
            self._suppressed.append(SuppressionEvent(signal, "below_confidence_threshold"))
            return None

        last_emitted = self._last_emitted_at_ms.get(signal.topic)
        cooldown_ms = self.settings.nudge_cooldown_seconds * 1000
        if last_emitted is not None and (now_ms - last_emitted) < cooldown_ms:
            self._suppressed.append(SuppressionEvent(signal, "cooldown_duplicate"))
            return None

        if self._is_semantic_duplicate(signal, now_ms):
            self._suppressed.append(SuppressionEvent(signal, "semantic_duplicate"))
            return None

        self._counter += 1
        expiry_ms = self.settings.nudge_expiry_seconds * 1000
        nudge = build_nudge(
            signal, nudge_id=f"nudge_{self._counter:04d}",
            priority=_PRIORITY_BY_TYPE[signal.signal_type],
            created_at_ms=now_ms, expires_at_ms=now_ms + expiry_ms,
        )
        self._last_emitted_at_ms[signal.topic] = now_ms
        self._record_embedding(signal)
        self._active.append(nudge)
        self._history.append(nudge)
        return nudge

    def _is_semantic_duplicate(self, signal: Signal, now_ms: float) -> bool:
        """Catches a same-signal-type repeat worded differently enough to
        dodge the exact topic-key cooldown above (e.g. two frustration
        utterances that don't share a topic key but clearly mean the same
        thing). Only compared against the *last* nudge of the same
        signal_type, and only within its cooldown window — this is meant
        to close a gap in the topic-key check, not replace it."""

        if self.embed_fn is None:
            return False
        last = self._last_embedding_by_type.get(signal.signal_type)
        if last is None:
            return False
        last_embedding, last_topic = last
        last_emitted = self._last_emitted_at_ms.get(last_topic)
        # Uses the expiry window (not the per-topic cooldown) as the
        # recency bound: this check exists specifically to catch a
        # same-signal-type repeat under a *different* topic key, which by
        # definition wouldn't be caught by the cooldown (that's keyed on
        # topic). Using cooldown_seconds here would make this check a
        # no-op whenever cooldown is 0/short, even though semantic dedup
        # is meant to be an independent safety net — see docs/DECISIONS.md.
        if last_emitted is None or (now_ms - last_emitted) >= self.settings.nudge_expiry_seconds * 1000:
            return False
        new_embedding = self.embed_fn(signal.evidence_text)
        if new_embedding is None:
            return False
        similarity = sum(a * b for a, b in zip(new_embedding, last_embedding))
        return similarity >= self.settings.nudge_semantic_dup_threshold

    def _record_embedding(self, signal: Signal) -> None:
        if self.embed_fn is None:
            return
        embedding = self.embed_fn(signal.evidence_text)
        if embedding is not None:
            self._last_embedding_by_type[signal.signal_type] = (embedding, signal.topic)

    def _expire(self, now_ms: float) -> None:
        self._active = [n for n in self._active if n.expires_at_ms > now_ms]

    def active_nudges(self, now_ms: float | None = None) -> list[Nudge]:
        if now_ms is not None:
            self._expire(now_ms)
        return sorted(self._active, key=lambda n: (_PRIORITY_SORT_ORDER[n.priority], -n.created_at_ms))

    def history(self) -> list[Nudge]:
        return list(self._history)

    def suppressed(self) -> list[SuppressionEvent]:
        return list(self._suppressed)
