"""Renders a CallScenario's scripted lines into one real stereo WAV file
(agent on the left channel, customer on the right — the exact convention
app/audio_io.py's diarization-by-channel relies on), and returns the
per-utterance timing computed from the actual rendered audio, so
ground-truth timestamps (live_nudges/tests/ground_truth.yaml) are derived
facts, not guesses.

Scenario d's ``add_noise=True`` mixes in synthesized background noise
(band-limited white noise, roughly office-babble-like) at a fixed SNR —
real signal degradation the ASR stage actually has to contend with, not
just "harder" text."""

from __future__ import annotations

import numpy as np

from live_nudges.app.audio_io import resample_linear
from live_nudges.app.models import CallScenario, Speaker
from live_nudges.audio_gen.tts import synthesize_line

TARGET_SR = 16_000
GAP_MS = 350  # silence between consecutive lines, regardless of speaker
_AGENT_VOICE_INDEX = 0
_CUSTOMER_VOICE_INDEX = 1
_NOISE_SNR_DB = 12.0


def _add_band_limited_noise(signal: np.ndarray, sr: int, snr_db: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    noise = rng.normal(0, 1, size=len(signal)).astype("float32")
    # Crude band-limiting (low-pass via short moving average) so it reads
    # as dull background rumble/babble rather than harsh hiss.
    kernel = np.ones(8, dtype="float32") / 8
    noise = np.convolve(noise, kernel, mode="same")

    signal_power = np.mean(signal ** 2) + 1e-12
    noise_power = np.mean(noise ** 2) + 1e-12
    target_noise_power = signal_power / (10 ** (snr_db / 10))
    noise *= np.sqrt(target_noise_power / noise_power)
    return signal + noise


def build_scenario_audio(scenario: CallScenario) -> tuple[np.ndarray, int, list[dict]]:
    """Returns (stereo float32 array, sample_rate, timings) where timings
    is a list of {index, speaker, start_ms, end_ms} for each utterance, in
    the order given."""

    rendered: list[tuple[Speaker, np.ndarray]] = []
    for utterance in scenario.utterances:
        voice_index = _AGENT_VOICE_INDEX if utterance.speaker == Speaker.AGENT else _CUSTOMER_VOICE_INDEX
        samples, sr = synthesize_line(utterance.text, voice_index)
        samples = resample_linear(samples, sr, TARGET_SR)
        rendered.append((utterance.speaker, samples))

    gap_samples = int(TARGET_SR * GAP_MS / 1000)
    total_len = sum(len(s) for _, s in rendered) + gap_samples * len(rendered) + gap_samples
    left = np.zeros(total_len, dtype="float32")
    right = np.zeros(total_len, dtype="float32")

    timings: list[dict] = []
    cursor = gap_samples
    for i, (speaker, samples) in enumerate(rendered):
        start = cursor
        end = start + len(samples)
        channel = left if speaker == Speaker.AGENT else right
        channel[start:end] = samples
        timings.append({
            "index": i,
            "speaker": speaker.value,
            "start_ms": int(start / TARGET_SR * 1000),
            "end_ms": int(end / TARGET_SR * 1000),
        })
        cursor = end + gap_samples

    if scenario.add_noise:
        left = _add_band_limited_noise(left, TARGET_SR, _NOISE_SNR_DB, seed=1)
        right = _add_band_limited_noise(right, TARGET_SR, _NOISE_SNR_DB, seed=2)

    stereo = np.stack([left, right], axis=1)
    return stereo, TARGET_SR, timings
