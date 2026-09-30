"""ASR provider abstraction for the benchmark harness.

Real providers (Deepgram, Azure Speech — the two the assignment brief
names explicit voice/model IDs for) make real REST calls and are
**not exercised against a live API** in this environment — no ASR
provider credentials exist here. Each raises a clear, specific error if
its API key isn't configured, verified directly (not assumed).

`FakeASRProvider` is offline and deterministic — used to verify the
benchmark harness's WER/CER/code-switching/named-term-accuracy
computation is mechanically correct (metrics.py), NOT to represent real
ASR quality for any actual provider. Its output is a clearly-labeled
synthetic perturbation of the reference text, never presented as a real
measurement — see docs/q3_multilingual/asr_report.md.

Google STT and OpenAI gpt-4o-transcribe (the other two candidates the
brief lists) are not implemented here — same scope decision as
voice_agent's LLM-mode (one or two providers implemented correctly and
honestly labeled as unverified beats four implemented and none
verified). See docs/DECISIONS.md.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Protocol

from pydantic import BaseModel


class TranscriptionResult(BaseModel):
    text: str
    latency_ms: float
    provider: str


class ASRProvider(Protocol):
    name: str

    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...


class FakeASRProvider:
    """Offline, deterministic — no credentials, no network, no real
    audio needed. `perturbation` simulates what an imperfect ASR
    hypothesis might look like (a stand-in for a real error pattern,
    not a measurement of one)."""

    def __init__(self, name: str, perturbation: Callable[[str], str] | None = None):
        self.name = name
        self._perturbation = perturbation or (lambda t: t)

    def transcribe_text(self, reference_text: str) -> TranscriptionResult:
        """Takes reference TEXT directly (stand-in for audio) since no
        real audio or TTS-generated audio exists in this environment."""

        start = time.perf_counter()
        text = self._perturbation(reference_text)
        return TranscriptionResult(
            text=text, latency_ms=(time.perf_counter() - start) * 1000, provider=self.name
        )


class DeepgramProvider:
    """Deepgram nova-3, `language=multi` or explicit "tl"/"id" per the
    brief. NOT exercised against a live API here — see module docstring.
    """

    name = "deepgram-nova-3"

    def __init__(self, api_key: str | None, language: str):
        self.api_key = api_key
        self.language = language

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not self.api_key:
            raise RuntimeError(
                "DEEPGRAM_API_KEY not configured — see docs/q3_multilingual/asr_report.md "
                "and multilingual/README.md 'ASR/TTS Setup'."
            )
        import httpx

        start = time.perf_counter()
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        response = httpx.post(
            f"https://api.deepgram.com/v1/listen?model=nova-3&language={self.language}",
            headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/wav"},
            content=audio_bytes,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        text = data["results"]["channels"][0]["alternatives"][0]["transcript"]
        return TranscriptionResult(
            text=text, latency_ms=(time.perf_counter() - start) * 1000, provider=self.name
        )


class AzureSpeechProvider:
    """Azure Speech, locale `fil-PH` / `id-ID` / `en-PH` per the brief.
    NOT exercised against a live API here — see module docstring."""

    name = "azure-speech"

    def __init__(self, api_key: str | None, region: str | None, locale: str):
        self.api_key = api_key
        self.region = region
        self.locale = locale

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        if not self.api_key or not self.region:
            raise RuntimeError(
                "AZURE_SPEECH_KEY/AZURE_SPEECH_REGION not configured — see "
                "docs/q3_multilingual/asr_report.md and multilingual/README.md "
                "'ASR/TTS Setup'."
            )
        import httpx

        start = time.perf_counter()
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        url = (
            f"https://{self.region}.stt.speech.microsoft.com/speech/recognition/"
            f"conversation/cognitiveservices/v1?language={self.locale}"
        )
        response = httpx.post(
            url,
            headers={
                "Ocp-Apim-Subscription-Key": self.api_key,
                "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
            },
            content=audio_bytes,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("DisplayText", "")
        return TranscriptionResult(
            text=text, latency_ms=(time.perf_counter() - start) * 1000, provider=self.name
        )
