"""Renders exactly one line of text to one WAV file via pyttsx3 (local
SAPI5 on Windows — fully offline, no TTS provider credentials, same
no-live-credentials constraint documented for multilingual/'s ASR/TTS).

Run as a **separate subprocess per line** (see tts.py's ``synthesize_line``)
rather than importing pyttsx3 directly in the calling process: pyttsx3's
SAPI5 driver reliably hangs when a second ``pyttsx3.init()`` /
``runAndWait()`` pair is created in the same process — a real bug found
while building this, not a hypothetical one. One line per process
sidesteps it entirely and costs a fraction of a second per subprocess
spawn, negligible against the alternative of a hung process.
"""

from __future__ import annotations

import sys

import pyttsx3


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: tts_worker.py <text> <voice_index> <out_wav_path>", file=sys.stderr)
        return 1
    text, voice_index_str, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    voice_index = int(voice_index_str)

    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    if not voices:
        print("no TTS voices available on this system", file=sys.stderr)
        return 1
    engine.setProperty("voice", voices[voice_index % len(voices)].id)
    engine.setProperty("rate", 175)
    engine.save_to_file(text, out_path)
    engine.runAndWait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
