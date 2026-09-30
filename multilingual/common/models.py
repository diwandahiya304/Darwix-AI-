"""Shared pydantic models for multilingual/ (both markets)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LocalizedSearchKBResult(BaseModel):
    grounded: bool
    speakable_answer: str
    citations: list[str] = Field(default_factory=list)
    category: str | None = None
    register_used: str  # "formal" | "colloquial" — which fallback/tone variant was selected
