"""Fast signal-extraction layer: deterministic keyword/regex rules,
config-driven (live_nudges/config/disclosures.yaml,
approved_offers.yaml — never hardcoded lists of compliance/offer
content, per app/disclosure.py's docstring). Runs in well under 50ms
per segment (verified in tests) — this is the layer that must never add
meaningful latency, so app/signals_llm.py's Haiku layer runs
independently on a slower cadence instead of gating this one.

Stateful across the call via `SignalExtractor` (disclosure-given state,
open cross-sell opportunities, a rolling frustration-hit window, and the
last customer topic bucket for intent-shift detection)."""

from __future__ import annotations

from live_nudges.app.disclosure import load_approved_offers_config, load_disclosures_config
from live_nudges.app.models import Signal, SignalLayer, SignalType, Speaker, TranscriptSegment
from live_nudges.app.settings import Settings

_FRUSTRATION_KEYWORDS = [
    "frustrated", "annoyed", "already told you", "again and again",
    "waste of time", "ridiculous", "this is unacceptable", "angry",
    "sick of", "how many times",
]
_FRUSTRATION_WINDOW_SEGMENTS = 6
_FRUSTRATION_HITS_FOR_SIGNAL = 2

_BUYING_SIGNAL_KEYWORDS = [
    "sounds good", "sign me up", "how do i proceed", "i want to buy",
    "let's do it", "i'm interested", "go ahead and set it up",
]

_CALLBACK_KEYWORDS = [
    "call me later", "not a good time", "call back", "busy right now",
    "can you call tomorrow", "in a meeting",
]

_PAYMENT_DIFFICULTY_KEYWORDS = [
    "can't afford", "cannot afford", "lost my job", "financial difficulty",
    "struggling to pay", "tough time paying", "don't have the money",
]

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "pricing": ["premium", "price", "cost", "how much"],
    "eligibility": ["eligible", "waiting period", "pre-existing", "age limit"],
    "complaint": ["complaint", "unhappy", "not satisfied", "issue with"],
    "cancellation": ["cancel", "refund", "discontinue"],
}


def _contains_any(text_lower: str, phrases: list[str]) -> str | None:
    for phrase in phrases:
        if phrase in text_lower:
            return phrase
    return None


def _topic_for(text_lower: str) -> str | None:
    for topic, keywords in _TOPIC_KEYWORDS.items():
        if _contains_any(text_lower, keywords):
            return topic
    return None


class SignalExtractor:
    def __init__(self, settings: Settings) -> None:
        disclosures = load_disclosures_config(settings.disclosures_config_path_abs())
        offers = load_approved_offers_config(settings.approved_offers_config_path_abs())

        self._disclosure_phrases: list[str] = disclosures["disclosure_phrases"]
        self._stage_trigger_phrases: list[str] = disclosures["stage_trigger_phrases"]
        self._risky_phrases: list[str] = disclosures["risky_phrases"]

        self._cross_sell_triggers: dict[str, str] = {}   # trigger phrase -> topic
        self._offer_keywords: dict[str, list[str]] = {}  # topic -> agent offer phrases
        for offer in offers["offers"]:
            for phrase in offer["customer_trigger_phrases"]:
                self._cross_sell_triggers[phrase] = offer["topic"]
            self._offer_keywords[offer["topic"]] = offer["agent_offer_phrases"]

        self._disclosure_given = False
        self._open_cross_sell: dict[str, int] = {}  # topic -> segment_id first triggered
        self._handled_cross_sell: set[str] = set()
        self._frustration_hits: list[int] = []
        self._last_customer_topic: str | None = None
        # faster-whisper's fixed-length windows (app/streaming_asr.py) can
        # split one sentence across two consecutive final segments (found
        # in practice: "shall I go ahead and process the payment" landed
        # as "...and prop-" / "process the payment now." in two separate
        # segments — see docs/DECISIONS.md). Compliance phrase matching
        # (disclosure/risky/stage-trigger) uses this short rolling buffer
        # of recent agent text instead of a single segment's text, so a
        # phrase spanning a window boundary is still caught.
        self._agent_text_buffer = ""

    def process(self, segment: TranscriptSegment) -> list[Signal]:
        if not segment.is_final or not segment.text:
            return []
        text_lower = segment.text.lower()
        if segment.speaker == Speaker.CUSTOMER:
            return self._process_customer(segment, text_lower)
        return self._process_agent(segment, text_lower)

    def _signal(self, signal_type: SignalType, topic: str, confidence: float,
                evidence_text: str, segment_id: int, call_time_ms: int) -> Signal:
        return Signal(
            signal_type=signal_type, topic=topic, confidence=confidence,
            evidence_text=evidence_text, layer=SignalLayer.FAST,
            segment_id=segment_id, call_time_ms=call_time_ms,
        )

    def _process_customer(self, segment: TranscriptSegment, text_lower: str) -> list[Signal]:
        signals: list[Signal] = []
        call_time_ms = segment.window_end_ms

        trigger_phrase = _contains_any(text_lower, list(self._cross_sell_triggers.keys()))
        if trigger_phrase:
            topic = self._cross_sell_triggers[trigger_phrase]
            if topic not in self._handled_cross_sell:
                self._open_cross_sell.setdefault(topic, segment.segment_id)

        if _contains_any(text_lower, _BUYING_SIGNAL_KEYWORDS):
            signals.append(self._signal(SignalType.BUYING_SIGNAL, "buying_signal:ready_to_close",
                                         0.85, segment.text, segment.segment_id, call_time_ms))

        if _contains_any(text_lower, _CALLBACK_KEYWORDS):
            signals.append(self._signal(SignalType.CALLBACK_NEEDED, "callback:requested",
                                         0.8, segment.text, segment.segment_id, call_time_ms))

        if _contains_any(text_lower, _PAYMENT_DIFFICULTY_KEYWORDS):
            signals.append(self._signal(SignalType.PAYMENT_DIFFICULTY, "payment_difficulty:reported",
                                         0.8, segment.text, segment.segment_id, call_time_ms))

        if _contains_any(text_lower, _FRUSTRATION_KEYWORDS):
            self._frustration_hits.append(segment.segment_id)
        self._frustration_hits = [
            sid for sid in self._frustration_hits
            if segment.segment_id - sid < _FRUSTRATION_WINDOW_SEGMENTS * 2
        ]
        if len(self._frustration_hits) >= _FRUSTRATION_HITS_FOR_SIGNAL:
            confidence = min(0.95, 0.6 + 0.1 * len(self._frustration_hits))
            signals.append(self._signal(SignalType.FRUSTRATION, "sentiment:frustration",
                                         confidence, segment.text, segment.segment_id, call_time_ms))

        topic = _topic_for(text_lower)
        if topic and self._last_customer_topic and topic != self._last_customer_topic:
            signals.append(self._signal(
                SignalType.INTENT_SHIFT, f"intent_shift:{self._last_customer_topic}->{topic}",
                0.55, segment.text, segment.segment_id, call_time_ms,
            ))
        if topic:
            self._last_customer_topic = topic

        return signals

    def _process_agent(self, segment: TranscriptSegment, text_lower: str) -> list[Signal]:
        signals: list[Signal] = []
        call_time_ms = segment.window_end_ms

        self._agent_text_buffer = (self._agent_text_buffer + " " + segment.text).strip()[-300:]
        buffer_lower = self._agent_text_buffer.lower()

        if _contains_any(buffer_lower, self._disclosure_phrases):
            self._disclosure_given = True

        for topic, offer_keywords in self._offer_keywords.items():
            if topic in self._open_cross_sell and _contains_any(text_lower, offer_keywords):
                self._handled_cross_sell.add(topic)
                self._open_cross_sell.pop(topic, None)

        if _contains_any(buffer_lower, self._risky_phrases):
            signals.append(self._signal(SignalType.COMPLIANCE_RISK, "compliance:risky_statement",
                                         0.92, segment.text, segment.segment_id, call_time_ms))

        closing_phrase = _contains_any(buffer_lower, self._stage_trigger_phrases)
        if closing_phrase and not self._disclosure_given:
            signals.append(self._signal(SignalType.COMPLIANCE_RISK, "compliance:missing_disclosure",
                                         0.9, segment.text, segment.segment_id, call_time_ms))
        if closing_phrase and self._open_cross_sell:
            topic, first_segment_id = next(iter(self._open_cross_sell.items()))
            signals.append(self._signal(
                SignalType.MISSED_OPPORTUNITY, f"missed_{topic}",
                0.75, segment.text, first_segment_id, call_time_ms,
            ))

        return signals
