"""Real streaming ASR via faster-whisper (local, offline — see
docs/DECISIONS.md for why this is the "fallback: faster-whisper chunked
streaming" path rather than Deepgram/Azure, which have no credentials in
this environment). This is genuine model inference on genuine audio
samples, not a scripted/modeled latency number — ``asr_latency_ms`` below
is measured wall-clock time around the actual ``model.transcribe()``
call.

Not true low-latency streaming ASR (which revises partial hypotheses
token-by-token as audio arrives) — faster-whisper doesn't expose that.
Instead, per speaker channel, this accumulates audio into a rolling
window and runs one whisper pass at ``asr_partial_ms`` (a "partial") and
another at ``asr_window_ms`` (a "final"), which still satisfies "process
audio while the call is happening": each pass only ever sees audio that
already played, and its latency is measured from when that audio became
available.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from live_nudges.app.models import AudioChunk, Speaker, TranscriptSegment

_model = None
_model_key: tuple[str, str, str] | None = None


def _load_model(model_name: str, device: str, compute_type: str):
    global _model, _model_key
    key = (model_name, device, compute_type)
    if _model is not None and _model_key == key:
        return _model
    from faster_whisper import WhisperModel

    _model = WhisperModel(model_name, device=device, compute_type=compute_type)
    _model_key = key
    return _model


def transcribe_array(samples: np.ndarray, sample_rate: int, model_name: str, device: str, compute_type: str) -> str:
    """Runs one real faster-whisper pass over ``samples`` (mono float32 at
    ``sample_rate``). Passing a numpy array (not a file path) sidesteps a
    PyAV/faster-whisper version mismatch in this environment that breaks
    file-path decoding — see docs/DECISIONS.md — and is the natural input
    shape for streaming chunks anyway."""

    if len(samples) == 0:
        return ""
    model = _load_model(model_name, device, compute_type)
    segments, _info = model.transcribe(samples, language="en", vad_filter=False)
    return " ".join(seg.text.strip() for seg in segments).strip()


@dataclass
class _ChannelState:
    buffer: list[float] = field(default_factory=list)
    window_start_ms: int = 0
    partial_emitted: bool = False
    last_call_time_ms: int = 0


class StreamingASR:
    """Stateful, per-speaker-channel accumulator that turns a stream of
    AudioChunks into a stream of partial/final TranscriptSegments,
    running real faster-whisper inference on each window."""

    def __init__(self, sample_rate: int, window_ms: int, partial_ms: int,
                 model_name: str, device: str, compute_type: str) -> None:
        self.sample_rate = sample_rate
        self.window_ms = window_ms
        self.partial_ms = partial_ms
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._channels: dict[Speaker, _ChannelState] = {}
        self._next_segment_id = 0

    def _state_for(self, speaker: Speaker) -> _ChannelState:
        if speaker not in self._channels:
            self._channels[speaker] = _ChannelState()
        return self._channels[speaker]

    def process_chunk(self, chunk: AudioChunk) -> list[TranscriptSegment]:
        state = self._state_for(chunk.speaker)
        state.buffer.extend(chunk.samples)
        state.last_call_time_ms = chunk.call_time_ms
        window_elapsed_ms = chunk.call_time_ms - state.window_start_ms

        segments: list[TranscriptSegment] = []

        if not state.partial_emitted and window_elapsed_ms >= self.partial_ms:
            segments.append(self._run(chunk, state, is_final=False))
            state.partial_emitted = True

        if window_elapsed_ms >= self.window_ms:
            segments.append(self._run(chunk, state, is_final=True))
            state.buffer = []
            state.window_start_ms = chunk.call_time_ms
            state.partial_emitted = False

        return segments

    def _run(self, chunk: AudioChunk, state: _ChannelState, is_final: bool) -> TranscriptSegment:
        return self._run_on_buffer(state.buffer, chunk.speaker, state.window_start_ms, chunk.call_time_ms, is_final)

    def _run_on_buffer(self, buffer: list[float], speaker: Speaker, window_start_ms: int,
                        window_end_ms: int, is_final: bool) -> TranscriptSegment:
        t0 = time.perf_counter()
        samples = np.array(buffer, dtype="float32")
        text = transcribe_array(samples, self.sample_rate, self.model_name, self.device, self.compute_type)
        latency_ms = (time.perf_counter() - t0) * 1000

        segment = TranscriptSegment(
            segment_id=self._next_segment_id,
            speaker=speaker,
            text=text,
            is_final=is_final,
            window_start_ms=window_start_ms,
            window_end_ms=window_end_ms,
            asr_latency_ms=latency_ms,
        )
        self._next_segment_id += 1
        return segment

    def flush(self) -> list[TranscriptSegment]:
        """Emits a final segment for any channel with buffered audio that
        never reached a full window — call this once after the audio
        stream ends. Without it, a call shorter than one window (or the
        last few seconds of any call) would have its trailing audio
        silently never transcribed at all, which is a real correctness
        bug, not just a test artifact — found while testing this module
        against short scripted audio. See docs/DECISIONS.md."""

        segments: list[TranscriptSegment] = []
        for speaker, state in self._channels.items():
            if state.buffer:
                segments.append(self._run_on_buffer(
                    state.buffer, speaker, state.window_start_ms, state.last_call_time_ms, is_final=True,
                ))
                state.buffer = []
                state.window_start_ms = state.last_call_time_ms
                state.partial_emitted = False
        return segments
