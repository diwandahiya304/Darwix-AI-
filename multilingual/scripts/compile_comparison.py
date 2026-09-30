"""Runs both markets' scenarios for real and compiles
docs/q3_multilingual/comparison.md: ASR quality, TTS quality, fallback
behaviour, issues. ASR/TTS sections are marked NOT MEASURED (no live
credentials — see asr_report.md); fallback behaviour and issues are
compiled from real scripted simulator runs against the real KB.

Run: `make multilingual-comparison`.
"""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from kb.app.main import app as kb_app
from multilingual.common.chat_sim import run_scripted
from multilingual.common.settings import REPO_ROOT, get_settings
from multilingual.indonesia.app.tools import dispatch as id_dispatch
from multilingual.indonesia.sim.scenarios import SCENARIOS as ID_SCENARIOS
from multilingual.philippines.app.tools import dispatch as ph_dispatch
from multilingual.philippines.sim.scenarios import SCENARIOS as PH_SCENARIOS

RESULTS_PATH = REPO_ROOT / "docs" / "q3_multilingual" / "comparison.md"


def _market_stats(scenarios, dispatch, settings, kb_client) -> dict:
    total_kb_calls = 0
    grounded_calls = 0
    fallback_calls = 0
    errors = []
    for scenario in scenarios:
        transcript = run_scripted(scenario, settings, dispatch, kb_http_client=kb_client)
        for entry in transcript:
            if "tool" not in entry:
                continue
            if entry["tool"] == "search_knowledge_base":
                total_kb_calls += 1
                if entry["result"].get("grounded"):
                    grounded_calls += 1
                else:
                    fallback_calls += 1
            if "error" in entry["result"]:
                errors.append(f"{scenario.scenario_id}: {entry['tool']} -> {entry['result']['error']}")
    grounding_rate = grounded_calls / total_kb_calls if total_kb_calls else None
    return {
        "scenarios_run": len(scenarios),
        "kb_calls": total_kb_calls,
        "grounded": grounded_calls,
        "fallback": fallback_calls,
        "grounding_rate": grounding_rate,
        "errors": errors,
    }


def _rate_str(rate: float | None) -> str:
    return f"{rate:.0%}" if rate is not None else "n/a"


def main() -> int:
    settings = get_settings()
    with TestClient(kb_app, base_url="http://kb.local") as kb_client:
        ph_stats = _market_stats(PH_SCENARIOS, ph_dispatch, settings, kb_client)
        id_stats = _market_stats(ID_SCENARIOS, id_dispatch, settings, kb_client)

    lines = [
        "# Q3 Comparison: Philippines vs. Indonesia",
        "",
        "## ASR Quality",
        "",
        "**Not measured** — no live ASR provider credentials in this "
        "environment. See `docs/q3_multilingual/asr_report.md` for the "
        "benchmark harness design, candidate provider documentation, and "
        "the honesty caveat on every number in it.",
        "",
        "## TTS Quality",
        "",
        "**Not measured** — no live TTS provider credentials. Candidate "
        "voices (see `multilingual/README.md` 'ASR/TTS Setup'): "
        "Philippines `fil-PH-BlessicaNeural`/`AngeloNeural` (Azure) or "
        "ElevenLabs multilingual; Indonesia `id-ID-ArdiNeural`/"
        "`GadisNeural` (Azure) or ElevenLabs. **Known compromise, not "
        "verified against real audio**: neither Azure nor ElevenLabs, as "
        "far as documented, offers a voice specifically tuned for "
        "natural Taglish code-switching prosody or a Javanese-accented "
        "Indonesian voice — both would default to standard fil-PH/id-ID "
        "prosody, which may sound less natural for heavily code-switched "
        "or regionally-accented delivery than a native speaker would.",
        "",
        "## Fallback Behaviour (measured, real simulator runs against the real KB)",
        "",
        "| Market | Scenarios run | KB lookups | Grounded | Fallback | Grounding rate |",
        "|---|---|---|---|---|---|",
        f"| Philippines | {ph_stats['scenarios_run']} | {ph_stats['kb_calls']} | "
        f"{ph_stats['grounded']} | {ph_stats['fallback']} | {_rate_str(ph_stats['grounding_rate'])} |",
        f"| Indonesia | {id_stats['scenarios_run']} | {id_stats['kb_calls']} | "
        f"{id_stats['grounded']} | {id_stats['fallback']} | {_rate_str(id_stats['grounding_rate'])} |",
        "",
        "## Issues",
        "",
    ]
    all_errors = ph_stats["errors"] + id_stats["errors"]
    if all_errors:
        lines += [f"- {e}" for e in all_errors]
    else:
        lines.append("No tool-dispatch errors observed across either market's scripted scenario runs.")
    lines += [
        "",
        "- See `docs/q3_multilingual/gaps.md` for the full retrieval-threshold "
        "and regional-accent findings — both markets needed their own "
        "calibrated grounding threshold (thinner margins than English's, "
        "see `docs/DECISIONS.md`), and Indonesia's regional-accent "
        "scenario specifically surfaced a paraphrase-distance retrieval "
        "miss, independent of any ASR question.",
        "- Philippines' near-miss objection (\"Wala akong pera ngayon\", "
        "measured dense score 0.834) was fixed by per-language threshold "
        "calibration, not by rewording the query — see `docs/DECISIONS.md`.",
    ]

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Comparison written to {RESULTS_PATH}")
    print(f"PH grounding rate: {ph_stats['grounding_rate']}, ID grounding rate: {id_stats['grounding_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
