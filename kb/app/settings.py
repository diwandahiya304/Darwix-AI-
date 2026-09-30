"""Centralized config for the kb/ retrieval layer, loaded from .env (see
.env.example). CLAUDE.md §1: pydantic (v2) for every settings object —
no bare os.environ reads scattered through the codebase."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    embedding_model: str = "intfloat/multilingual-e5-small"
    vector_store_backend: str = "chroma"  # chroma | qdrant
    vector_store_path: str = "./data/processed/kb_index"

    kb_port: int = 8001
    kb_top_k: int = 3
    # Calibrated empirically against the English corpus + kb/eval/
    # queries.yaml (18 records, ~24 exploratory queries): in-scope top-1
    # dense cosine similarity ranged 0.849-0.937, out-of-scope ranged
    # 0.732-0.829 — a real but thin ~0.02 margin, not a comfortable gap.
    # See docs/DECISIONS.md for the full measurement and its limitation.
    kb_min_relevance_score: float = 0.84

    # Per-language overrides: verified directly that this same
    # multilingual embedding model produces a DIFFERENT (and, here, even
    # thinner) in-scope/out-of-scope score distribution per language —
    # 0.84 is wrong for Tagalog/Indonesian, not just "slightly off." A
    # single global threshold silently rejected a genuinely-grounded
    # Tagalog objection-handling match (0.834) that should have passed.
    # Calibrated against ~8 exploratory queries per language (thinner
    # sample than English's — flagged, not hidden, see docs/DECISIONS.md
    # and docs/q3_multilingual/gaps.md): fil in-scope 0.825-0.892,
    # out-of-scope 0.765-0.819 (~0.006 margin); id in-scope 0.830-0.921,
    # out-of-scope 0.760-0.827 (~0.003 margin) — both margins thinner
    # than English's, a real limitation, not just a calibration nuance.
    kb_min_relevance_score_fil: float = 0.822
    kb_min_relevance_score_id: float = 0.828

    def vector_store_path_abs(self) -> Path:
        path = Path(self.vector_store_path)
        return path if path.is_absolute() else REPO_ROOT / path

    def min_relevance_score_for(self, language: str | None) -> float:
        """Looks up the calibrated threshold for `language` ("fil"/"id"),
        falling back to the English-calibrated default for "en" or any
        unrecognized/absent language tag."""

        overrides = {"fil": self.kb_min_relevance_score_fil, "id": self.kb_min_relevance_score_id}
        return overrides.get(language, self.kb_min_relevance_score)


def get_settings() -> Settings:
    return Settings()
