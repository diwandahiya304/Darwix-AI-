"""LLM signal-extraction layer: Claude Haiku called on final utterances,
no more often than `llm_min_interval_seconds`, over a sliding window of
the last `llm_window_seconds` of transcript — returns STRICT JSON
matching `LLMSignalResult`. Anything that fails schema validation is
treated as "this layer produced nothing for this window," exactly like
voice_agent's KB client degrading a KB outage to "ungrounded" rather than
ever inventing an answer (CLAUDE.md §6's grounding rule, applied here to
signal detection instead of factual answers).

No live Anthropic credentials are required to exercise this module's
code — `client=None` (the default) constructs a real `anthropic.Anthropic`
client lazily only if `settings.has_llm_credentials()`; otherwise
`maybe_process` returns `[]` and the caller logs the layer as not
configured, the same graceful-degrade pattern used for every other
unconfigured external dependency in this repo (Vapi, Deepgram, Azure
Speech). Tests inject a fake client exposing the same
`.messages.create(...)` shape voice_agent/sim/chat_sim.py's `run_llm`
already established, so the JSON-parsing/validation/signal-mapping code
is fully tested without a live API key.
"""

from __future__ import annotations

import json

from live_nudges.app.models import (
    LLMSignalResult, Signal, SignalLayer, SignalType, Speaker, TranscriptSegment,
)
from live_nudges.app.settings import Settings

_SYSTEM_PROMPT = (
    "You analyze a short window of a live customer service call transcript "
    "(insurance/finance sector). Return ONLY a single JSON object, no prose, "
    "matching exactly this shape:\n"
    '{"intent": string|null, "topic_shift": bool, '
    '"compliance_risk": {"type": string, "evidence": string}|null, '
    '"frustration_score": number (0-1), "buying_signal": bool, '
    '"missed_opportunity": {"type": string, "evidence": string}|null, '
    '"callback_needed": bool, "confidence": number (0-1)}\n'
    "Only report compliance_risk or missed_opportunity if the transcript "
    "window actually contains clear evidence for it — never invent one."
)


def _build_prompt(window: list[tuple[Speaker, str, int]]) -> str:
    lines = [f"{speaker.value}: {text}" for speaker, text, _ in window]
    return "Transcript window (oldest first):\n" + "\n".join(lines)


class LLMSignalExtractor:
    def __init__(self, settings: Settings, client=None) -> None:
        self.settings = settings
        self._client = client
        self._window: list[tuple[Speaker, str, int]] = []
        self._last_call_time_ms: float | None = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.settings.has_llm_credentials():
            return None
        if self.settings.llm_provider != "anthropic":
            return None
        import anthropic

        self._client = anthropic.Anthropic(api_key=self.settings.llm_api_key)
        return self._client

    def _update_window(self, segment: TranscriptSegment) -> None:
        if segment.is_final and segment.text:
            self._window.append((segment.speaker, segment.text, segment.window_end_ms))
        cutoff = segment.window_end_ms - self.settings.llm_window_seconds * 1000
        self._window = [w for w in self._window if w[2] >= cutoff]

    def is_configured(self) -> bool:
        return self._get_client() is not None

    def maybe_process(self, segment: TranscriptSegment) -> list[Signal]:
        self._update_window(segment)

        if not segment.is_final or not segment.text:
            return []

        now_ms = segment.window_end_ms
        min_interval_ms = self.settings.llm_min_interval_seconds * 1000
        if self._last_call_time_ms is not None and (now_ms - self._last_call_time_ms) < min_interval_ms:
            return []

        client = self._get_client()
        if client is None:
            return []

        self._last_call_time_ms = now_ms
        result = self._call_llm(client)
        if result is None:
            return []
        return self._to_signals(result, segment)

    def _call_llm(self, client) -> LLMSignalResult | None:
        try:
            response = client.messages.create(
                model=self.settings.llm_model,
                max_tokens=300,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": _build_prompt(self._window)}],
            )
            raw_text = response.content[0].text
            data = json.loads(raw_text)
            return LLMSignalResult.model_validate(data)
        except Exception:
            return None

    def _to_signals(self, result: LLMSignalResult, segment: TranscriptSegment) -> list[Signal]:
        if result.confidence <= 0:
            return []
        signals: list[Signal] = []
        call_time_ms = segment.window_end_ms

        if result.compliance_risk is not None:
            signals.append(Signal(
                signal_type=SignalType.COMPLIANCE_RISK,
                topic=f"compliance:{result.compliance_risk.type}",
                confidence=result.confidence, evidence_text=result.compliance_risk.evidence,
                layer=SignalLayer.LLM, segment_id=segment.segment_id, call_time_ms=call_time_ms,
            ))
        if result.missed_opportunity is not None:
            signals.append(Signal(
                signal_type=SignalType.MISSED_OPPORTUNITY,
                topic=f"missed_{result.missed_opportunity.type}",
                confidence=result.confidence, evidence_text=result.missed_opportunity.evidence,
                layer=SignalLayer.LLM, segment_id=segment.segment_id, call_time_ms=call_time_ms,
            ))
        if result.frustration_score >= 0.6:
            signals.append(Signal(
                signal_type=SignalType.FRUSTRATION, topic="sentiment:frustration",
                confidence=result.frustration_score, evidence_text=segment.text,
                layer=SignalLayer.LLM, segment_id=segment.segment_id, call_time_ms=call_time_ms,
            ))
        if result.buying_signal:
            signals.append(Signal(
                signal_type=SignalType.BUYING_SIGNAL, topic="buying_signal:ready_to_close",
                confidence=result.confidence, evidence_text=segment.text,
                layer=SignalLayer.LLM, segment_id=segment.segment_id, call_time_ms=call_time_ms,
            ))
        if result.callback_needed:
            signals.append(Signal(
                signal_type=SignalType.CALLBACK_NEEDED, topic="callback:requested",
                confidence=result.confidence, evidence_text=segment.text,
                layer=SignalLayer.LLM, segment_id=segment.segment_id, call_time_ms=call_time_ms,
            ))
        if result.topic_shift and result.intent:
            signals.append(Signal(
                signal_type=SignalType.INTENT_SHIFT, topic=f"intent_shift:llm:{result.intent}",
                confidence=result.confidence, evidence_text=segment.text,
                layer=SignalLayer.LLM, segment_id=segment.segment_id, call_time_ms=call_time_ms,
            ))
        return signals
