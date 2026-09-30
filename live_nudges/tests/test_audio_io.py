import numpy as np
import soundfile as sf

from live_nudges.app.audio_io import load_call_audio, resample_linear, stream_audio_file
from live_nudges.app.models import Speaker


def _write_stereo_wav(path, duration_s: float = 1.0, sr: int = 8000):
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    left = np.sin(2 * np.pi * 220 * t).astype("float32")
    right = np.sin(2 * np.pi * 440 * t).astype("float32")
    sf.write(str(path), np.stack([left, right], axis=1), sr)


def _write_mono_wav(path, duration_s: float = 1.0, sr: int = 8000):
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    sf.write(str(path), np.sin(2 * np.pi * 220 * t).astype("float32"), sr)


def test_resample_linear_changes_length_proportionally():
    samples = np.zeros(1000, dtype="float32")
    resampled = resample_linear(samples, orig_sr=8000, target_sr=16000)
    assert len(resampled) == 2000


def test_resample_linear_is_a_no_op_at_same_rate():
    samples = np.arange(10, dtype="float32")
    resampled = resample_linear(samples, orig_sr=8000, target_sr=8000)
    assert np.allclose(resampled, samples)


def test_stereo_file_splits_into_agent_left_customer_right(tmp_path):
    path = tmp_path / "stereo.wav"
    _write_stereo_wav(path)
    channels = load_call_audio(path, target_sr=16000)
    assert Speaker.AGENT in channels
    assert Speaker.CUSTOMER in channels
    assert len(channels[Speaker.AGENT]) == len(channels[Speaker.CUSTOMER])


def test_mono_file_falls_back_to_customer_only(tmp_path):
    path = tmp_path / "mono.wav"
    _write_mono_wav(path)
    channels = load_call_audio(path, target_sr=16000)
    assert set(channels.keys()) == {Speaker.CUSTOMER}


def test_stream_audio_file_yields_chunks_with_increasing_call_time(tmp_path):
    path = tmp_path / "stereo.wav"
    _write_stereo_wav(path, duration_s=1.0, sr=8000)
    chunks = list(stream_audio_file(path, chunk_ms=250, sample_rate=8000, speed=1000.0))
    assert len(chunks) > 0
    call_times = [c.call_time_ms for c in chunks if c.speaker == Speaker.AGENT]
    assert call_times == sorted(call_times)
    assert all(c.t_audio_sent > 0 for c in chunks)


def test_stream_audio_file_chunk_sample_count_matches_chunk_ms(tmp_path):
    path = tmp_path / "stereo.wav"
    _write_stereo_wav(path, duration_s=1.0, sr=8000)
    chunks = list(stream_audio_file(path, chunk_ms=250, sample_rate=8000, speed=1000.0))
    expected_samples = int(8000 * 250 / 1000)
    assert chunks[0].samples.__len__() == expected_samples
