"""Centralized config for live_nudges/, loaded from .env (see
.env.example). CLAUDE.md §1: pydantic for every settings object."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    live_nudges_port: int = 8005

    # --- Chunked real-time replay (app/audio_io.py) ---
    chunk_ms: int = 300              # 250-500ms PCM chunk size, paced at --speed
    asr_window_ms: int = 2000        # rolling window faster-whisper transcribes per hop
    asr_partial_ms: int = 1000       # emit a partial transcript after this much of the window

    # --- Streaming ASR (app/streaming_asr.py) ---
    # No live ASR provider (Deepgram/Azure) credentials in this
    # environment — faster-whisper is a real local model, not a mock, and
    # is the explicitly-allowed fallback path. See docs/DECISIONS.md.
    asr_model: str = "tiny.en"
    asr_device: str = "cpu"
    asr_compute_type: str = "int8"
    asr_sample_rate: int = 16_000

    # --- LLM signal layer (app/signals_llm.py) ---
    # Reuses the same Anthropic credentials as voice_agent/ (LLM_API_KEY/
    # LLM_MODEL in .env) — same account, no need for a second key.
    # "changeme"/unset means: skip this layer, log it as not configured
    # (same graceful-degrade pattern as every other unconfigured external
    # dependency in this repo), never crash or silently pretend to run it.
    llm_provider: str = "anthropic"
    llm_api_key: str | None = None
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_window_seconds: float = 30.0   # sliding window of transcript sent to the LLM layer
    llm_min_interval_seconds: float = 5.0  # don't call the LLM more than this often

    # --- Nudge engine (app/controller.py) ---
    nudge_confidence_threshold: float = 0.6
    nudge_cooldown_seconds: float = 30.0
    nudge_expiry_seconds: float = 60.0
    # Cosine-similarity threshold (via the same multilingual-e5-small
    # embedding model kb/ already uses) above which two same-signal-type
    # nudges are treated as duplicates even if their exact evidence text
    # differs — see docs/DECISIONS.md.
    nudge_semantic_dup_threshold: float = 0.90

    # --- Config-driven compliance content ---
    disclosures_config_path: str = "live_nudges/config/disclosures.yaml"
    approved_offers_config_path: str = "live_nudges/config/approved_offers.yaml"

    def has_llm_credentials(self) -> bool:
        return bool(self.llm_api_key) and self.llm_api_key != "changeme"

    def disclosures_config_path_abs(self) -> Path:
        path = Path(self.disclosures_config_path)
        return path if path.is_absolute() else REPO_ROOT / path

    def approved_offers_config_path_abs(self) -> Path:
        path = Path(self.approved_offers_config_path)
        return path if path.is_absolute() else REPO_ROOT / path


def get_settings() -> Settings:
    return Settings()
