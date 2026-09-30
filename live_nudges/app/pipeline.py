"""Orchestrates the full audio -> transcript -> signal -> nudge ->
delivery chain for one call, over a real WAV file, with a real
faster-whisper ASR stage — see app/audio_io.py and app/streaming_asr.py's
docstrings for why this is genuinely "processing audio while the call
happens," not a post-hoc analysis.

Every hop (audio_received, asr_done, signals_done, llm_done,
nudge_created, delivered) is timestamped and appended to a per-call JSONL
log in real time (LatencyLogger) — `make q4-report` reconstructs
per-component P50/P95/max durations from these logs.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from live_nudges.app.audio_io import stream_audio_file
from live_nudges.app.controller import NudgeController, SuppressionEvent
from live_nudges.app.models import LatencyEvent, Nudge, TranscriptSegment
from live_nudges.app.settings import Settings
from live_nudges.app.signals_fast import SignalExtractor
from live_nudges.app.signals_llm import LLMSignalExtractor
from live_nudges.app.streaming_asr import StreamingASR


class LatencyLogger:
    """Appends one JSON line per hop as the call runs — a real-time log,
    not something written after the call ends."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._events: list[LatencyEvent] = []
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("", encoding="utf-8")

    def log(self, call_id: str, segment_id: int, hop: str, t_wall_ms: float | None = None) -> None:
        event = LatencyEvent(call_id=call_id, segment_id=segment_id, hop=hop,
                              t_wall_ms=t_wall_ms if t_wall_ms is not None else time.time() * 1000)
        self._events.append(event)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(event.model_dump_json() + "\n")

    def events(self) -> list[LatencyEvent]:
        return list(self._events)


@dataclass
class CallRunResult:
    call_id: str
    transcript: list[TranscriptSegment] = field(default_factory=list)
    nudges: list[Nudge] = field(default_factory=list)
    suppressed: list[SuppressionEvent] = field(default_factory=list)
    latency_events: list[LatencyEvent] = field(default_factory=list)
    llm_configured: bool = False


def run_call(
    audio_path: Path,
    call_id: str,
    settings: Settings,
    speed: float = 1.0,
    embed_fn: Callable[[str], list[float] | None] | None = None,
    llm_client=None,
    latency_log_path: Path | None = None,
    on_segment: Callable[[TranscriptSegment], None] | None = None,
    on_nudge: Callable[[Nudge], None] | None = None,
    on_suppressed: Callable[[SuppressionEvent], None] | None = None,
) -> CallRunResult:
    asr = StreamingASR(
        sample_rate=settings.asr_sample_rate, window_ms=settings.asr_window_ms,
        partial_ms=settings.asr_partial_ms, model_name=settings.asr_model,
        device=settings.asr_device, compute_type=settings.asr_compute_type,
    )
    fast_extractor = SignalExtractor(settings)
    llm_extractor = LLMSignalExtractor(settings, client=llm_client)
    controller = NudgeController(settings, embed_fn=embed_fn)
    logger = LatencyLogger(latency_log_path)

    result = CallRunResult(call_id=call_id, llm_configured=llm_extractor.is_configured())

    def _process_segment(segment: TranscriptSegment, audio_received_t_ms: float) -> None:
        # audio_received uses the real wall-clock instant the audio that
        # closed this window became available (AudioChunk.t_audio_sent,
        # captured *before* asr.process_chunk ran) — logging it only
        # after process_chunk returns (as an earlier version of this
        # function did) would place it right next to asr_done and make
        # the real faster-whisper inference time vanish from the
        # asr_done - audio_received delta. See docs/DECISIONS.md.
        logger.log(call_id, segment.segment_id, "audio_received", t_wall_ms=audio_received_t_ms)
        result.transcript.append(segment)
        if on_segment:
            on_segment(segment)
        logger.log(call_id, segment.segment_id, "asr_done")

        fast_signals = fast_extractor.process(segment)
        logger.log(call_id, segment.segment_id, "signals_done")

        llm_signals = llm_extractor.maybe_process(segment)
        logger.log(call_id, segment.segment_id, "llm_done")

        for signal in fast_signals + llm_signals:
            suppressed_before = len(controller.suppressed())
            nudge = controller.evaluate(signal, now_ms=segment.window_end_ms)
            if nudge is not None:
                logger.log(call_id, segment.segment_id, "nudge_created")
                if on_nudge:
                    on_nudge(nudge)
                logger.log(call_id, segment.segment_id, "delivered")
                result.nudges.append(nudge)
            elif on_suppressed and len(controller.suppressed()) > suppressed_before:
                on_suppressed(controller.suppressed()[-1])

    for chunk in stream_audio_file(audio_path, chunk_ms=settings.chunk_ms, sample_rate=settings.asr_sample_rate, speed=speed):
        audio_received_t_ms = chunk.t_audio_sent
        for segment in asr.process_chunk(chunk):
            _process_segment(segment, audio_received_t_ms)

    # Flush any trailing audio that never reached a full window — see
    # StreamingASR.flush()'s docstring for why this matters. There is no
    # further chunk to time against, so the flush call's own start time
    # is the best available "audio received" instant for this trailing
    # content (it already arrived earlier; this slightly understates its
    # true audio_received time but does not corrupt the asr_done delta,
    # since that's still measured from immediately before the flush's
    # own whisper call).
    flush_t_ms = time.time() * 1000
    for segment in asr.flush():
        _process_segment(segment, flush_t_ms)

    result.suppressed = controller.suppressed()
    result.latency_events = logger.events()
    return result


def load_latency_events(path: Path) -> list[LatencyEvent]:
    events = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(LatencyEvent.model_validate(json.loads(line)))
    return events
