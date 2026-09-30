"""Thin subprocess wrapper around tts_worker.py — see that module's
docstring for why each line is rendered in its own process."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

_WORKER = Path(__file__).resolve().parent / "tts_worker.py"


def synthesize_line(text: str, voice_index: int) -> tuple[np.ndarray, int]:
    """Renders one line of text via pyttsx3 in a subprocess and returns
    (mono float32 samples, sample_rate)."""

    with tempfile.TemporaryDirectory() as tmp_dir:
        out_path = Path(tmp_dir) / "line.wav"
        result = subprocess.run(
            [sys.executable, str(_WORKER), text, str(voice_index), str(out_path)],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0 or not out_path.exists():
            raise RuntimeError(f"TTS worker failed for {text!r}: {result.stderr}")
        samples, sample_rate = sf.read(str(out_path), dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        return samples.astype("float32"), sample_rate
