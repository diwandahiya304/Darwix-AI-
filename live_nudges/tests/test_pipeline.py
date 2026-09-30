"""End-to-end tests against the real, checked-in scenario audio
(recordings/live_nudges/audio/*.wav) — real chunked replay, real
faster-whisper ASR, real signal/nudge logic. This is the strongest
evidence for CLAUDE.md §5 Q4's required coverage: missed cross-sell, a
compliance risky-statement + missing-disclosure example, rising
frustration, and a noisy/ambiguous call with nudges suppressed.

Runs at a high `speed` to keep the suite's wall-clock time reasonable —
the ASR component's own latency is real inference time regardless of
speed (see app/streaming_asr.py's docstring); only the audio pacing
between chunks is compressed."""

from __future__ import annotations

import pytest

from live_nudges.app.pipeline import run_call
from live_nudges.app.semantic import embed_for_dedup
from live_nudges.app.settings import REPO_ROOT, Settings

AUDIO_DIR = REPO_ROOT / "recordings" / "live_nudges" / "audio"
_SPEED = 30.0

pytestmark = pytest.mark.skipif(
    not AUDIO_DIR.exists() or not list(AUDIO_DIR.glob("*.wav")),
    reason="scenario audio not generated — run `make q4-generate-audio` first",
)


def _run(scenario_id: str):
    audio_path = AUDIO_DIR / f"{scenario_id}.wav"
    return run_call(audio_path, call_id=f"test_{scenario_id}", settings=Settings(), speed=_SPEED, embed_fn=embed_for_dedup)


def test_missed_cross_sell_scenario_emits_missed_opportunity_nudge():
    result = _run("a_missed_cross_sell")
    assert any(n.topic == "missed_cross_sell:family_floater" for n in result.nudges)


def test_compliance_gap_scenario_emits_risky_statement_and_missing_disclosure_nudges():
    result = _run("b_compliance_gap")
    topics = {n.topic for n in result.nudges}
    assert "compliance:risky_statement" in topics
    assert "compliance:missing_disclosure" in topics


def test_rising_frustration_scenario_emits_frustration_nudge():
    result = _run("c_rising_frustration")
    assert any(n.topic == "sentiment:frustration" for n in result.nudges)


def test_noisy_ambiguous_scenario_emits_zero_or_minimal_nudges():
    result = _run("d_noisy_ambiguous")
    assert len(result.nudges) <= 1


def test_latency_events_cover_the_expected_hops():
    result = _run("c_rising_frustration")
    hops = {e.hop for e in result.latency_events}
    assert {"audio_received", "asr_done", "signals_done", "llm_done"} <= hops


def test_llm_layer_reports_not_configured_without_credentials():
    result = _run("b_compliance_gap")
    assert result.llm_configured is False
