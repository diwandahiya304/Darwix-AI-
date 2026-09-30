"""Centralized config for multilingual/ (both markets), loaded from .env.
Reuses voice_agent.app.escalation/crm directly (generic, not English-
specific) rather than duplicating them — this Settings object supplies
the paths/URLs those functions need."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    kb_api_base_url: str = "http://localhost:8001"
    kb_search_top_k: int = 3

    vapi_api_key: str | None = None

    ph_vapi_assistant_id: str | None = None
    ph_webhook_base_url: str | None = None
    ph_port: int = 8003

    id_vapi_assistant_id: str | None = None
    id_webhook_base_url: str | None = None
    id_port: int = 8004

    escalation_webhook_url: str | None = None
    escalation_transfer_number: str | None = None

    # ASR benchmark (multilingual/asr_bench/) — no keys configured in
    # this environment; used only to report configuration status
    # honestly, never to fabricate a "not configured" API call.
    deepgram_api_key: str | None = None
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None

    crm_db_path: str = "./data/processed/mock_crm_multilingual.sqlite3"

    def crm_db_path_abs(self) -> Path:
        path = Path(self.crm_db_path)
        return path if path.is_absolute() else REPO_ROOT / path

    def has_vapi_credentials(self) -> bool:
        return bool(self.vapi_api_key) and self.vapi_api_key != "changeme"


def get_settings() -> Settings:
    return Settings()
