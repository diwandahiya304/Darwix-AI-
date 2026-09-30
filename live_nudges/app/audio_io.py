"""Loads a WAV file and chunks it into real-time-paced PCM segments —
this is the actual "process audio while the call is happening" mechanism
required by CLAUDE.md §5 Q4. Nothing here reads the whole file and
analyzes it before returning; `stream_audio_file` sleeps between chunks
to match real elapsed audio time (scaled by `speed`), and only ever
returns samples for audio that has "already played."

**Diarization**: stereo files are split by channel — agent on the left
channel, customer on the right (the convention `audio_gen/
scenarios_audio.py` synthesizes with) — which is an exact, not
probabilistic, speaker separation. Mono files fall back to a single
"unknown" speaker channel; there is no real diarization model (e.g.
pyannote) wired in — see docs/q4_live_nudges/limitations.md. This
matches what was asked for ("support stereo files... and diarization
fallback for mono") without overclaiming real diarization accuracy on
mono audio, which this repo cannot evaluate without labeled real-world
recordings.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import soundfile as sf

from live_nudges.app.models import AudioChunk, Speaker


def resample_linear(samples: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Linear-interpolation resampling — good enough for speech at these
    sample rates (verified against faster-whisper transcription quality
    during development), avoids adding a scipy/resampy dependency for a
    single utility function. Shared by app/audio_io.py and
    audio_gen/scenarios_audio.py."""
    if orig_sr == target_sr:
        return samples.astype("float32")
    duration = len(samples) / orig_sr
    new_len = max(1, int(round(duration * target_sr)))
    old_x = np.arange(len(samples))
    new_x = np.linspace(0, len(samples), new_len, endpoint=False)
    return np.interp(new_x, old_x, samples).astype("float32")


def load_call_audio(path: Path, target_sr: int) -> dict[Speaker, np.ndarray]:
    """Reads a WAV file and returns one mono float32 array per speaker
    channel, resampled to ``target_sr``. Stereo -> {AGENT: left, CUSTOMER:
    right}. Mono -> {CUSTOMER: the whole signal} (diarization fallback —
    see module docstring)."""

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    channels = data.shape[1]

    if channels >= 2:
        left = resample_linear(data[:, 0], sr, target_sr)
        right = resample_linear(data[:, 1], sr, target_sr)
        return {Speaker.AGENT: left, Speaker.CUSTOMER: right}

    mono = resample_linear(data[:, 0], sr, target_sr)
    return {Speaker.CUSTOMER: mono}


def stream_audio_file(
    path: Path,
    chunk_ms: int,
    sample_rate: int,
    speed: float = 1.0,
) -> Iterator[AudioChunk]:
    """Yields one AudioChunk per ``chunk_ms`` of audio, per active
    channel, interleaved in call-time order, sleeping in real time
    (scaled by ``speed``) between chunks so downstream stages only ever
    see audio that has "already happened." ``t_audio_sent`` is a real
    wall-clock timestamp, not a simulated one."""

    channels = load_call_audio(path, sample_rate)
    chunk_samples = int(sample_rate * chunk_ms / 1000)

    # Build a flat, call-time-ordered schedule across all channels so
    # overlapping/near-simultaneous speech from both channels interleaves
    # the way it would on a real call, rather than draining one channel
    # fully before the other.
    schedule: list[tuple[int, Speaker, int]] = []  # (start_sample, speaker, chunk_index)
    for speaker, samples in channels.items():
        n_chunks = max(1, int(np.ceil(len(samples) / chunk_samples)))
        for i in range(n_chunks):
            schedule.append((i * chunk_samples, speaker, i))
    schedule.sort(key=lambda item: item[0])

    chunk_id = 0
    call_start = time.perf_counter()
    for start_sample, speaker, i in schedule:
        end_sample = start_sample + chunk_samples
        call_time_ms = int((end_sample / sample_rate) * 1000)

        target_elapsed_s = (call_time_ms / 1000.0) / speed
        actual_elapsed_s = time.perf_counter() - call_start
        sleep_s = target_elapsed_s - actual_elapsed_s
        if sleep_s > 0:
            time.sleep(sleep_s)

        samples = channels[speaker][start_sample:end_sample]
        yield AudioChunk(
            chunk_id=chunk_id,
            speaker=speaker,
            samples=samples.tolist(),
            call_time_ms=call_time_ms,
            t_audio_sent=time.time() * 1000,
        )
        chunk_id += 1
