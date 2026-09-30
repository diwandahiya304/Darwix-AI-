"""Shared scripted-mode simulator runner for both markets — mirrors
voice_agent/sim/chat_sim.py's run_scripted/write_transcript logic
exactly, parameterized by a market-specific `dispatch` function instead
of importing one hardcoded tool registry, so philippines/ and
indonesia/ don't duplicate this machinery. Reuses voice_agent's Turn/
Scenario dataclasses directly (fully generic — speaker/text/tool_call;
scenario_id/title/description/turns — nothing English-specific about
them) rather than redefining them.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from voice_agent.sim.scenarios import Scenario, Turn  # noqa: F401  (Turn re-exported for callers)

from multilingual.common.settings import Settings


def run_scripted(
    scenario: Scenario, settings: Settings, dispatch: Callable, **kwargs
) -> list[dict]:
    """Executes one scenario's fixed script against a market's real tool
    registry (via `dispatch`, e.g. multilingual.philippines.app.tools.dispatch).
    Returns a transcript: {"speaker", "text"} for spoken turns,
    {"speaker": "assistant", "tool", "args", "result"} for tool calls."""

    transcript: list[dict] = []
    for turn in scenario.turns:
        if turn.tool_call is not None:
            tool_name, args = turn.tool_call
            result = dispatch(tool_name, args, settings, **kwargs)
            transcript.append({"speaker": "assistant", "tool": tool_name, "args": args, "result": result})
            if tool_name == "search_knowledge_base":
                transcript.append({"speaker": "assistant", "text": result.get("speakable_answer", "")})
        else:
            transcript.append({"speaker": turn.speaker, "text": turn.text})
    return transcript


def write_transcript(scenario: Scenario, transcript: list[dict], market: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{scenario.scenario_id}.md"
    lines = [
        f"# {scenario.title}",
        "",
        f"_Simulated via `multilingual/{market}/sim` — scripted mode, real tool "
        f"calls against the real KB and market-specific tools, **not a real "
        f"Vapi call**. See docs/q3_multilingual/gaps.md and "
        f"multilingual/README.md for what would need to happen for a real one._",
        "",
        f"**Scenario:** {scenario.description}",
        "",
        "## Transcript",
        "",
    ]
    for entry in transcript:
        if "tool" in entry:
            lines.append(
                f"> 🔧 **{entry['tool']}**"
                f"(`{json.dumps(entry['args'], ensure_ascii=False)}`) → "
                f"`{json.dumps(entry['result'], ensure_ascii=False)}`"
            )
        else:
            speaker = "Assistant" if entry["speaker"] == "assistant" else "Customer"
            lines.append(f"**{speaker}:** {entry['text']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_all_scripted(
    scenarios: list[Scenario], settings: Settings, dispatch: Callable, market: str, output_dir: Path, **kwargs
) -> dict[str, list[dict]]:
    transcripts = {}
    for scenario in scenarios:
        transcript = run_scripted(scenario, settings, dispatch, **kwargs)
        write_transcript(scenario, transcript, market, output_dir)
        transcripts[scenario.scenario_id] = transcript
    return transcripts
