"""Voice agent chat simulator — runs the same system prompt + tools
against either a deterministic scripted customer (--mode scripted, no API
key needed) or a real LLM playing both roles (--mode llm, needs
LLM_API_KEY), so scenarios can be iterated on fast before real Vapi
calls.

**Scripted mode** executes voice_agent/sim/scenarios.py's fixed turn
scripts against the REAL tool registry (voice_agent/app/tools.py) —
every tool call in the transcript is real (hits the real KB retrieval
API, real scoring logic, real CRM writes), not fabricated. It's a
deterministic reference implementation of "what a correctly-behaving
assistant does" per the system prompt's rules — useful both as
executable test evidence (this submission's docs/q1_test_results.md and
recordings/voice_agent/ were generated this way) and as a regression
check if a live LLM-driven Vapi assistant deviates from it.

**LLM mode** drives both roles with a real model: one Claude call plays
the assistant (system_prompt.md + TOOL_SCHEMAS, with real tool-calling
dispatched through the same registry scripted mode uses), a second plays
the customer (given a short persona derived from the scenario
description). **Not exercised in this environment** — no LLM_API_KEY is
configured (see settings.py). Its orchestration logic (turn loop, tool
dispatch wiring, end-of-call detection, the turn-count safety cap) is
tested with a mocked Anthropic client in
voice_agent/tests/test_chat_sim_llm_mode.py — implemented and unit-tested
for real, just not exercised against a live API call. Only Anthropic is
implemented; see docs/DECISIONS.md for why OpenAI support was scoped out.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from voice_agent.app.settings import REPO_ROOT, Settings, get_settings
from voice_agent.app.tools import TOOL_SCHEMAS, dispatch_tool
from voice_agent.sim.scenarios import SCENARIOS, Scenario

SYSTEM_PROMPT_PATH = REPO_ROOT / "voice_agent" / "config" / "system_prompt.md"
TRANSCRIPTS_DIR = REPO_ROOT / "recordings" / "voice_agent"
MAX_LLM_TURNS = 12


# --- scripted mode -----------------------------------------------------------


def run_scripted(scenario: Scenario, settings: Settings, **kwargs) -> list[dict]:
    """Executes one scenario's fixed script against the real tool
    registry. Returns a transcript: {"speaker", "text"} for spoken turns,
    {"speaker": "assistant", "tool", "args", "result"} for tool calls.

    `kwargs` (e.g. `kb_http_client`) is forwarded to dispatch_tool — see
    its docstring."""

    transcript: list[dict] = []
    for turn in scenario.turns:
        if turn.tool_call is not None:
            tool_name, args = turn.tool_call
            result = dispatch_tool(tool_name, args, settings, **kwargs)
            transcript.append({"speaker": "assistant", "tool": tool_name, "args": args, "result": result})
            if tool_name == "search_knowledge_base":
                # The system prompt's rule: relay what the tool says,
                # verbatim-ish, whether grounded or not.
                transcript.append({"speaker": "assistant", "text": result.get("speakable_answer", "")})
        else:
            transcript.append({"speaker": turn.speaker, "text": turn.text})
    return transcript


# --- LLM mode (implemented, not live-exercised here) -----------------------


def _to_anthropic_tools(tool_schemas: list[dict]) -> list[dict]:
    return [
        {
            "name": schema["function"]["name"],
            "description": schema["function"]["description"],
            "input_schema": schema["function"]["parameters"],
        }
        for schema in tool_schemas
    ]


def _run_assistant_turn(
    client, model: str, system_prompt: str, anthropic_tools: list[dict], messages: list[dict],
    settings: Settings, transcript: list[dict],
) -> tuple[str, list[dict]]:
    """Sends `messages` to the assistant model; dispatches any requested
    tool calls through the real registry (appending each to `transcript`,
    same shape as scripted mode's tool entries, so llm-mode transcripts
    are equally inspectable) and loops until the model produces a final
    text response (no more tool_use blocks)."""

    while True:
        response = client.messages.create(
            model=model, system=system_prompt, tools=anthropic_tools, messages=messages, max_tokens=1024,
        )
        messages = messages + [{"role": "assistant", "content": response.content}]
        tool_use_blocks = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
        if not tool_use_blocks:
            text = "\n".join(b.text for b in response.content if getattr(b, "type", None) == "text")
            return text, messages
        tool_results = []
        for block in tool_use_blocks:
            result = dispatch_tool(block.name, block.input, settings)
            transcript.append({"speaker": "assistant", "tool": block.name, "args": block.input, "result": result})
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result)}
            )
        messages = messages + [{"role": "user", "content": tool_results}]


def _run_customer_turn(client, model: str, persona_prompt: str, customer_messages: list[dict]) -> str:
    response = client.messages.create(
        model=model, system=persona_prompt, messages=customer_messages, max_tokens=256
    )
    return "\n".join(b.text for b in response.content if getattr(b, "type", None) == "text")


def run_llm(scenario: Scenario, settings: Settings, max_turns: int = MAX_LLM_TURNS, client=None) -> list[dict]:
    """`client` is dependency-injected (same pattern as kb_client.py/
    escalation.py elsewhere in this repo) so tests can pass a fake
    Anthropic-shaped client without monkeypatching the `anthropic` import
    — see test_chat_sim_llm_mode.py."""

    if client is None:
        import anthropic

        if settings.llm_provider != "anthropic":
            raise NotImplementedError(
                f"--mode llm only implements the anthropic provider (LLM_PROVIDER="
                f"{settings.llm_provider!r} configured) — see docs/DECISIONS.md."
            )
        client = anthropic.Anthropic(api_key=settings.llm_api_key)
    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    anthropic_tools = _to_anthropic_tools(TOOL_SCHEMAS)
    persona_prompt = (
        "You are roleplaying a customer receiving an outbound cold call about "
        f"health insurance. Scenario: {scenario.description}\n"
        "Respond naturally, 1-2 sentences per turn, matching this scenario's "
        "intent. When the call feels complete, end your message with the "
        "literal token [END CALL]."
    )

    transcript: list[dict] = []
    assistant_text, assistant_messages = _run_assistant_turn(
        client, settings.llm_model, system_prompt, anthropic_tools,
        [{"role": "user", "content": "[Begin the call.]"}], settings, transcript,
    )
    transcript.append({"speaker": "assistant", "text": assistant_text})

    customer_messages: list[dict] = []
    for _ in range(max_turns):
        customer_messages.append({"role": "user", "content": assistant_text})
        customer_reply = _run_customer_turn(client, settings.llm_model, persona_prompt, customer_messages)
        customer_messages.append({"role": "assistant", "content": customer_reply})
        ended = "[END CALL]" in customer_reply
        clean_reply = customer_reply.replace("[END CALL]", "").strip()
        transcript.append({"speaker": "customer", "text": clean_reply})
        if ended:
            break
        assistant_messages.append({"role": "user", "content": clean_reply})
        assistant_text, assistant_messages = _run_assistant_turn(
            client, settings.llm_model, system_prompt, anthropic_tools, assistant_messages, settings, transcript,
        )
        transcript.append({"speaker": "assistant", "text": assistant_text})

    return transcript


# --- shared: transcript writing + CLI ---------------------------------------


def write_transcript(scenario: Scenario, transcript: list[dict], mode: str) -> Path:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPTS_DIR / f"{scenario.scenario_id}.md"
    lines = [
        f"# {scenario.title}",
        "",
        f"_Simulated via `sim/chat_sim.py --mode {mode}` — **not a real Vapi call**. "
        "See README 'Vapi Setup Steps' for running real calls._",
        "",
        f"**Scenario:** {scenario.description}",
        "",
        "## Transcript",
        "",
    ]
    for entry in transcript:
        if "tool" in entry:
            lines.append(
                f"> 🔧 **{entry['tool']}**(`{json.dumps(entry['args'])}`) "
                f"→ `{json.dumps(entry['result'])}`"
            )
        else:
            speaker = "Assistant" if entry["speaker"] == "assistant" else "Customer"
            lines.append(f"**{speaker}:** {entry['text']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_all_scripted(settings: Settings | None = None, **kwargs) -> dict[str, list[dict]]:
    settings = settings or get_settings()
    transcripts = {}
    for scenario in SCENARIOS:
        transcript = run_scripted(scenario, settings, **kwargs)
        write_transcript(scenario, transcript, mode="scripted")
        transcripts[scenario.scenario_id] = transcript
    return transcripts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Voice agent chat simulator.")
    parser.add_argument("--mode", choices=["scripted", "llm"], default="scripted")
    parser.add_argument("--scenario", default=None, help="Run only this scenario id.")
    parser.add_argument(
        "--kb-mode",
        choices=["inprocess", "http"],
        default="inprocess",
        help=(
            "inprocess (default): run kb.app.main in-process, no separate KB "
            "server needed — avoids silently degrading every KB lookup to "
            "'ungrounded' if you forgot to `make run-kb` first. http: make a "
            "real network call to KB_API_BASE_URL (use this to also exercise "
            "real network latency/config against a separately-running server)."
        ),
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    if args.mode == "llm" and not settings.has_llm_credentials():
        print(
            "LLM_API_KEY is not configured — falling back to --mode scripted. "
            "Set LLM_PROVIDER=anthropic and LLM_API_KEY in .env to use --mode llm.",
            file=sys.stderr,
        )
        args.mode = "scripted"

    scenarios = [s for s in SCENARIOS if args.scenario in (None, s.scenario_id)]
    if not scenarios:
        print(f"No scenario with id {args.scenario!r}.", file=sys.stderr)
        return 1

    def _run(kb_kwargs: dict) -> int:
        for scenario in scenarios:
            transcript = (
                run_llm(scenario, settings)
                if args.mode == "llm"
                else run_scripted(scenario, settings, **kb_kwargs)
            )
            path = write_transcript(scenario, transcript, mode=args.mode)
            print(f"{scenario.scenario_id}: transcript written to {path}")
        return 0

    if args.mode == "llm" or args.kb_mode == "http":
        return _run({})

    from fastapi.testclient import TestClient
    from kb.app.main import app as kb_app

    with TestClient(kb_app, base_url="http://kb.local") as kb_client:
        return _run({"kb_http_client": kb_client})


if __name__ == "__main__":
    sys.exit(main())
