"""Tests --mode llm's orchestration logic (assistant/customer turn loop,
tool dispatch wiring through the REAL tool registry, end-of-call
detection via [END CALL], the turn-count safety cap) with a fake
Anthropic-shaped client — no live API key needed. The orchestration is
real and tested; the live API call itself isn't exercised in this
environment (no LLM_API_KEY is configured — see settings.py) — see
chat_sim.py's module docstring for why that's an honest, documented gap
rather than a claim this was verified end-to-end against a real model.
"""

from __future__ import annotations

from types import SimpleNamespace

from voice_agent.app.settings import Settings
from voice_agent.sim.chat_sim import MAX_LLM_TURNS, run_llm
from voice_agent.sim.scenarios import Scenario


def _text(text: str):
    return SimpleNamespace(type="text", text=text)


def _tool_use(name: str, input_: dict, id_: str = "tool_1"):
    return SimpleNamespace(type="tool_use", name=name, input=input_, id=id_)


class _FakeMessages:
    """Alternates: calls WITH `tools=` are the assistant role, calls
    without are the customer role — matching how run_llm invokes each."""

    def __init__(self, assistant_turns, customer_turns):
        self._assistant_turns = list(assistant_turns)
        self._customer_turns = list(customer_turns)

    def create(self, *, model, messages, system=None, tools=None, max_tokens=None):
        content = self._assistant_turns.pop(0) if tools else self._customer_turns.pop(0)
        return SimpleNamespace(content=content)


class _FakeClient:
    def __init__(self, assistant_turns, customer_turns):
        self.messages = _FakeMessages(assistant_turns, customer_turns)


def _scenario() -> Scenario:
    return Scenario(scenario_id="test", title="Test", description="A test scenario.", turns=[])


def test_run_llm_dispatches_a_real_tool_call_and_stops_on_end_call(tmp_path):
    assistant_turns = [
        [_text("Hi, could I get your age?")],  # seed turn
        [_tool_use("score_lead", {"age": 30, "intent": "interested"})],  # after 1st customer reply
        [_text("Thanks, you're a great fit!")],  # after the real tool result comes back
    ]
    customer_turns = [
        [_text("I'm 30 and interested.")],  # doesn't end the call yet
        [_text("Great, thanks. [END CALL]")],
    ]
    client = _FakeClient(assistant_turns, customer_turns)
    settings = Settings(crm_db_path=str(tmp_path / "crm.sqlite3"))

    transcript = run_llm(_scenario(), settings, client=client)

    # [assistant greeting, customer reply, assistant tool call, assistant
    # final text, customer end-call reply]
    speakers_and_kinds = [(t["speaker"], "tool" if "tool" in t else "text") for t in transcript]
    assert speakers_and_kinds == [
        ("assistant", "text"),
        ("customer", "text"),
        ("assistant", "tool"),
        ("assistant", "text"),
        ("customer", "text"),
    ]
    assert transcript[0]["text"] == "Hi, could I get your age?"
    assert transcript[2]["tool"] == "score_lead"
    assert transcript[2]["result"]["temperature"] == "hot"  # real dispatch_tool call, real scoring logic
    assert "great fit" in transcript[3]["text"]
    assert "END CALL" not in transcript[4]["text"]  # the literal token is stripped


def test_run_llm_respects_max_turns_safety_cap(tmp_path):
    # Customer never says [END CALL] — the loop must still terminate.
    assistant_turns = [[_text("Turn.")] for _ in range(MAX_LLM_TURNS + 1)]
    customer_turns = [[_text("Still talking.")] for _ in range(MAX_LLM_TURNS)]
    client = _FakeClient(assistant_turns, customer_turns)
    settings = Settings(crm_db_path=str(tmp_path / "crm.sqlite3"))

    transcript = run_llm(_scenario(), settings, max_turns=3, client=client)

    customer_turns_taken = [t for t in transcript if t["speaker"] == "customer"]
    assert len(customer_turns_taken) == 3


def test_run_llm_raises_clear_error_for_unimplemented_provider(tmp_path):
    settings = Settings(llm_provider="openai", crm_db_path=str(tmp_path / "crm.sqlite3"))
    try:
        run_llm(_scenario(), settings, client=None)
        assert False, "expected NotImplementedError"
    except NotImplementedError as exc:
        assert "openai" in str(exc)
