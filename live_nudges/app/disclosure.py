"""Loads config-driven compliance content (required disclosures, risky
phrases, approved cross-sell offers) from live_nudges/config/*.yaml —
never hardcoded in app/signals_fast.py's Python, matching the same
never-invent posture CLAUDE.md §11 requires for KB content in a voice
agent's system prompt. A nudge suggesting a cross-sell offer or flagging
a compliance gap can only ever reference something in this config."""

from __future__ import annotations

from pathlib import Path

import yaml

_disclosures_cache: dict[Path, dict] = {}
_offers_cache: dict[Path, dict] = {}


def load_disclosures_config(path: Path) -> dict:
    if path not in _disclosures_cache:
        with path.open(encoding="utf-8") as f:
            _disclosures_cache[path] = yaml.safe_load(f)
    return _disclosures_cache[path]


def load_approved_offers_config(path: Path) -> dict:
    if path not in _offers_cache:
        with path.open(encoding="utf-8") as f:
            _offers_cache[path] = yaml.safe_load(f)
    return _offers_cache[path]
