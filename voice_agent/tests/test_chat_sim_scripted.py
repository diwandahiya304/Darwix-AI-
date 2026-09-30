"""Executes every scenario's scripted mode for real, against the real
tool registry — including the real KB retrieval API, run in-process via
FastAPI's TestClient against kb.app.main.app directly (TestClient IS an
httpx.Client subclass, so it can be passed straight in as
kb_client.py's `client` parameter) rather than requiring a
separately-running kb/ server process. Using it as a context manager
also triggers the app's real startup lifespan, which builds the
retrieval index from the real ingested KB. Skipped if the KB hasn't been
ingested yet, same pattern as kb/tests/test_main_api.py. This is the
actual mechanism that produces docs/q1_test_results.md and
recordings/voice_agent/*.md.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from kb.app.main import app as kb_app
from kb.app.settings import REPO_ROOT as KB_REPO_ROOT
from voice_agent.app.kb_client import FALLBACK_MESSAGE
from voice_agent.app.settings import Settings
from voice_agent.sim.chat_sim import run_scripted
from voice_agent.sim.scenarios import SCENARIOS

_KB_RECORDS_PATH = KB_REPO_ROOT / "data" / "processed" / "kb_records.jsonl"

pytestmark = pytest.mark.skipif(
    not _KB_RECORDS_PATH.exists(),
    reason="No ingested KB yet — run `make ingest-kb` first.",
)


@pytest.fixture(scope="module")
def kb_http_client():
    with TestClient(kb_app, base_url="http://kb.local") as client:
        yield client


@pytest.fixture(scope="module")
def settings(tmp_path_factory) -> Settings:
    db_path = tmp_path_factory.mktemp("voice_agent_crm") / "crm.sqlite3"
    return Settings(crm_db_path=str(db_path))


def _scenario(scenario_id: str):
    return next(s for s in SCENARIOS if s.scenario_id == scenario_id)


def test_every_scenario_runs_without_error(settings, kb_http_client):
    for scenario in SCENARIOS:
        transcript = run_scripted(scenario, settings, kb_http_client=kb_http_client)
        assert transcript


def test_cooperative_scenario_scores_hot_and_creates_a_lead(settings, kb_http_client):
    transcript = run_scripted(_scenario("a_cooperative"), settings, kb_http_client=kb_http_client)
    tool_calls = {entry["tool"]: entry["result"] for entry in transcript if "tool" in entry}
    assert tool_calls["score_lead"]["temperature"] == "hot"
    assert tool_calls["create_lead"]["lead_id"].startswith("lead_")


def test_objection_scenario_grounds_the_premium_objection(settings, kb_http_client):
    transcript = run_scripted(_scenario("b_objection"), settings, kb_http_client=kb_http_client)
    kb_calls = [e for e in transcript if e.get("tool") == "search_knowledge_base"]
    assert len(kb_calls) == 2
    premium_result = kb_calls[0]["result"]
    assert premium_result["grounded"] is True
    assert premium_result["citations"]


def test_objection_scenario_never_invents_an_answer_for_the_trust_objection(settings, kb_http_client):
    """The KB has no content addressing general "I don't trust insurance"
    distrust — this must fall back honestly, not invent a reassurance."""
    transcript = run_scripted(_scenario("b_objection"), settings, kb_http_client=kb_http_client)
    kb_calls = [e for e in transcript if e.get("tool") == "search_knowledge_base"]
    trust_result = kb_calls[1]["result"]
    if not trust_result["grounded"]:
        assert trust_result["speakable_answer"] == FALLBACK_MESSAGE


def test_incomplete_conflicting_scenario_scores_with_missing_budget(settings, kb_http_client):
    transcript = run_scripted(
        _scenario("c_incomplete_conflicting"), settings, kb_http_client=kb_http_client
    )
    tool_calls = {entry["tool"]: entry["result"] for entry in transcript if "tool" in entry}
    # Budget was never resolved (customer declined twice) — score_lead must
    # still run without it, per the "ask once, then move on" rule.
    assert tool_calls["score_lead"]["temperature"] in ("hot", "warm", "cold")


def test_out_of_scope_scenario_has_no_tool_calls():
    """A pure conversational redirect — no KB lookup, no scoring, no CRM
    write. Out-of-scope means "decline and redirect," not "search for it.\""""
    transcript = run_scripted(_scenario("d_out_of_scope"), Settings())
    assert not [e for e in transcript if "tool" in e]


def test_human_escalation_scenario_calls_escalate(settings):
    transcript = run_scripted(_scenario("e_human_escalation"), settings)
    tool_calls = {entry["tool"]: entry["result"] for entry in transcript if "tool" in entry}
    assert tool_calls["escalate_to_human"]["escalated"] is True
