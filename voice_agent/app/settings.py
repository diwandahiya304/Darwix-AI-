"""Centralized config for voice_agent/, loaded from .env (see
.env.example). CLAUDE.md §1: pydantic for every settings object."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # kb/ retrieval API this agent grounds every answer against.
    kb_api_base_url: str = "http://localhost:8001"
    kb_search_top_k: int = 3

    # Vapi (voice platform) — all optional: the webhook server, scoring,
    # escalation, and CRM logic all work and are fully tested without
    # these set. Only scripts/create_assistant.py and
    # scripts/pull_transcripts.py need a real vapi_api_key.
    vapi_api_key: str | None = None
    vapi_assistant_id: str | None = None
    vapi_phone_number_id: str | None = None
    # Public URL (ngrok/cloudflared) Vapi calls for tool-call webhooks —
    # see README "Vapi Setup Steps".
    webhook_base_url: str | None = None

    # escalate_to_human: posts to a webhook if configured; otherwise (the
    # default, for local dev/demo) logs a "would transfer to <number>"
    # entry — see app/escalation.py.
    escalation_webhook_url: str | None = None
    escalation_transfer_number: str | None = None

    crm_db_path: str = "./data/processed/mock_crm.sqlite3"

    voice_agent_port: int = 8002

    # sim/chat_sim.py's --mode llm (optional; --mode scripted needs none
    # of this). "changeme"/empty means: fall back to scripted mode.
    llm_provider: str = "anthropic"
    llm_api_key: str | None = None
    llm_model: str = "claude-haiku-4-5-20251001"

    def crm_db_path_abs(self) -> Path:
        path = Path(self.crm_db_path)
        return path if path.is_absolute() else REPO_ROOT / path

    def has_vapi_credentials(self) -> bool:
        return bool(self.vapi_api_key) and self.vapi_api_key != "changeme"

    def has_llm_credentials(self) -> bool:
        return bool(self.llm_api_key) and self.llm_api_key != "changeme"


def get_settings() -> Settings:
    return Settings()
