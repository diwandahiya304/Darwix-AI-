"""Tests the real faster-whisper streaming ASR stage — genuine model
inference on genuine (locally synthesized) speech audio, not a mock.
Renders one short line once per test session (pyttsx3 subprocess, ~1s)
and reuses it, since the point here is testing StreamingASR's windowing/
latency-measurement logic, not re-synthesizing audio per test."""

from __future__ import annotations

import numpy as np
import pytest

from live_nudges.app.models import AudioChunk, Speaker
from live_nudges.app.streaming_asr import StreamingASR
from live_nudges.audio_gen.tts import synthesize_line
from live_nudges.app.audio_io import resample_linear


@pytest.fixture(scope="module")
def short_speech_samples():
    samples, sr = synthesize_line("Testing one two three.", voice_index=0)
    return resample_linear(samples, sr, 16000)


def _chunks_from_samples(samples: np.ndarray, chunk_ms: int, sample_rate: int):
    chunk_len = int(sample_rate * chunk_ms / 1000)
    chunks = []
    for i, start in enumerate(range(0, len(samples), chunk_len)):
        piece = samples[start:start + chunk_len]
        call_time_ms = int((start + len(piece)) / sample_rate * 1000)
        chunks.append(AudioChunk(
            chunk_id=i, speaker=Speaker.AGENT, samples=piece.tolist(),
            call_time_ms=call_time_ms, t_audio_sent=0.0,
        ))
    return chunks


def test_streaming_asr_emits_a_final_segment_with_positive_latency(short_speech_samples):
    asr = StreamingASR(sample_rate=16000, window_ms=2000, partial_ms=1000,
                        model_name="tiny.en", device="cpu", compute_type="int8")
    finals = []
    for chunk in _chunks_from_samples(short_speech_samples, chunk_ms=300, sample_rate=16000):
        for segment in asr.process_chunk(chunk):
            if segment.is_final:
                finals.append(segment)
    finals.extend(s for s in asr.flush() if s.is_final)
    assert len(finals) >= 1
    assert finals[0].asr_latency_ms > 0
    assert finals[0].speaker == Speaker.AGENT


def test_streaming_asr_emits_a_partial_before_the_final(short_speech_samples):
    asr = StreamingASR(sample_rate=16000, window_ms=2000, partial_ms=800,
                        model_name="tiny.en", device="cpu", compute_type="int8")
    seen_kinds = []
    for chunk in _chunks_from_samples(short_speech_samples, chunk_ms=300, sample_rate=16000):
        for segment in asr.process_chunk(chunk):
            seen_kinds.append(segment.is_final)
    seen_kinds.extend(True for _ in asr.flush())
    assert False in seen_kinds
    assert True in seen_kinds
    assert seen_kinds.index(False) < seen_kinds.index(True)


def test_transcribed_text_is_roughly_correct(short_speech_samples):
    asr = StreamingASR(sample_rate=16000, window_ms=3000, partial_ms=1500,
                        model_name="tiny.en", device="cpu", compute_type="int8")
    text = ""
    for chunk in _chunks_from_samples(short_speech_samples, chunk_ms=300, sample_rate=16000):
        for segment in asr.process_chunk(chunk):
            if segment.is_final:
                text = segment.text
    for segment in asr.flush():
        if segment.is_final:
            text = segment.text
    assert "test" in text.lower()


def test_flush_is_idempotent_once_the_buffer_is_drained(short_speech_samples):
    asr = StreamingASR(sample_rate=16000, window_ms=2000, partial_ms=1000,
                        model_name="tiny.en", device="cpu", compute_type="int8")
    for chunk in _chunks_from_samples(short_speech_samples, chunk_ms=300, sample_rate=16000):
        asr.process_chunk(chunk)
    first_flush = asr.flush()
    assert len(first_flush) == 1
    assert asr.flush() == []
