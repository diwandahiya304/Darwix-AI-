"""`make q4-report`: runs all 4 scripted scenarios (recordings/live_nudges/
audio/*.wav — generate first with `make q4-generate-audio`) through the
real pipeline, writes each call's per-hop JSONL latency log to
data/processed/live_nudges_latency/, then aggregates every logged hop
into P50/P95/max per component and an end-to-end figure, written to
docs/q4_live_nudges/latency_report.{md,json} plus a bar chart
(latency_chart.png).

`speed` here is fast (not 1.0) purely so this regenerates quickly — the
ASR component's measured latency is real faster-whisper inference time
regardless of `speed` (only the audio *pacing* between chunks is sped
up, not the model's own compute), so the numbers are honest wall-clock
code-path latency, same reasoning as multilingual/'s and the original
live_nudges evidence script's honesty notes.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from live_nudges.app.models import LatencyEvent
from live_nudges.app.pipeline import run_call
from live_nudges.app.semantic import embed_for_dedup
from live_nudges.app.settings import REPO_ROOT, get_settings
from live_nudges.sim.scenarios import SCENARIOS

AUDIO_DIR = REPO_ROOT / "recordings" / "live_nudges" / "audio"
LATENCY_DIR = REPO_ROOT / "data" / "processed" / "live_nudges_latency"
DOCS_DIR = REPO_ROOT / "docs" / "q4_live_nudges"
REPORT_SPEED = 20.0
COMPONENTS = ["asr", "signal_extraction", "llm", "delivery", "end_to_end"]


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, round(pct * (len(ordered) - 1)))
    return ordered[idx]


def _run_all_scenarios() -> None:
    settings = get_settings()
    for scenario in SCENARIOS:
        audio_path = AUDIO_DIR / f"{scenario.scenario_id}.wav"
        if not audio_path.exists():
            print(f"Missing {audio_path} — run `make q4-generate-audio` first", file=sys.stderr)
            sys.exit(1)
        print(f"Running {scenario.scenario_id} at speed x{REPORT_SPEED}...")
        run_call(
            audio_path, call_id=scenario.scenario_id, settings=settings, speed=REPORT_SPEED,
            embed_fn=embed_for_dedup, latency_log_path=LATENCY_DIR / f"{scenario.scenario_id}.jsonl",
        )


def _load_all_events() -> list[LatencyEvent]:
    events = []
    for path in sorted(LATENCY_DIR.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(LatencyEvent.model_validate(json.loads(line)))
    return events


def _compute_durations(events: list[LatencyEvent]) -> dict[str, list[float]]:
    singular: dict[tuple, dict[str, float]] = defaultdict(dict)
    pending_nudge_created: dict[tuple, deque] = defaultdict(deque)
    durations: dict[str, list[float]] = defaultdict(list)

    for event in sorted(events, key=lambda e: e.t_wall_ms):
        key = (event.call_id, event.segment_id)
        if event.hop in ("audio_received", "asr_done", "signals_done", "llm_done"):
            singular[key][event.hop] = event.t_wall_ms
        elif event.hop == "nudge_created":
            pending_nudge_created[key].append(event.t_wall_ms)
        elif event.hop == "delivered":
            if pending_nudge_created[key]:
                created_t = pending_nudge_created[key].popleft()
                durations["delivery"].append(event.t_wall_ms - created_t)
                if "audio_received" in singular[key]:
                    durations["end_to_end"].append(event.t_wall_ms - singular[key]["audio_received"])

    for hops in singular.values():
        if "audio_received" in hops and "asr_done" in hops:
            durations["asr"].append(hops["asr_done"] - hops["audio_received"])
        if "asr_done" in hops and "signals_done" in hops:
            durations["signal_extraction"].append(hops["signals_done"] - hops["asr_done"])
        if "signals_done" in hops and "llm_done" in hops:
            durations["llm"].append(hops["llm_done"] - hops["signals_done"])

    return durations


def _write_chart(summary: dict) -> None:
    components = [c for c in COMPONENTS if summary.get(c, {}).get("count", 0) > 0]
    p50s = [summary[c]["p50_ms"] for c in components]
    p95s = [summary[c]["p95_ms"] for c in components]
    maxs = [summary[c]["max_ms"] for c in components]

    x = range(len(components))
    width = 0.25
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - width for i in x], p50s, width, label="P50")
    ax.bar(list(x), p95s, width, label="P95")
    ax.bar([i + width for i in x], maxs, width, label="Max")
    ax.set_xticks(list(x))
    ax.set_xticklabels(components, rotation=20, ha="right")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Q4 live_nudges: per-component latency (P50/P95/max)")
    ax.legend()
    fig.tight_layout()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(DOCS_DIR / "latency_chart.png", dpi=120)
    plt.close(fig)


def main() -> int:
    LATENCY_DIR.mkdir(parents=True, exist_ok=True)
    _run_all_scenarios()

    events = _load_all_events()
    durations = _compute_durations(events)
    summary = {
        component: {
            "count": len(values),
            "p50_ms": round(_percentile(values, 0.5), 2),
            "p95_ms": round(_percentile(values, 0.95), 2),
            "max_ms": round(max(values), 2) if values else 0.0,
        }
        for component, values in durations.items()
    }

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "latency_report.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    _write_chart(summary)

    lines = [
        "# Q4 Live Nudges: Latency Report",
        "",
        f"Measured across all 4 scripted scenarios in `live_nudges/sim/scenarios.py`, "
        f"replayed at speed x{REPORT_SPEED} via `make q4-report` "
        f"(`live_nudges/scripts/compile_latency_report.py`). Speed only compresses "
        f"the audio *pacing* between chunks — `asr` is real faster-whisper "
        f"inference wall-clock time regardless of speed; `signal_extraction`, "
        f"`llm`, and `delivery` are real measured durations of this repo's actual "
        f"code paths.",
        "",
        "| Component | Count | P50 (ms) | P95 (ms) | Max (ms) |",
        "|---|---|---|---|---|",
    ]
    for component in COMPONENTS:
        s = summary.get(component, {"count": 0, "p50_ms": 0.0, "p95_ms": 0.0, "max_ms": 0.0})
        lines.append(f"| {component} | {s['count']} | {s['p50_ms']} | {s['p95_ms']} | {s['max_ms']} |")
    lines += [
        "",
        "![latency chart](latency_chart.png)",
        "",
        "`end_to_end` = audio_received (a segment's window closes) -> asr_done -> "
        "signals_done -> (llm_done, if the LLM layer ran for this segment) -> "
        "nudge_created -> delivered, summed only for segments that actually "
        "produced a nudge (a segment producing zero nudges has nothing to "
        "display, so it has no end-to-end entry).",
        "",
        "**`llm` count of 0 means the LLM layer was not configured** (no "
        "`LLM_API_KEY` in `.env` for this run) — every window was correctly "
        "skipped rather than silently faked. Set a real Anthropic key to "
        "populate this row. `asr` numbers are real local faster-whisper "
        "(`tiny.en`, CPU) inference; no Deepgram/Azure credentials exist in "
        "this environment, matching the same caveat already documented in "
        "`multilingual/README.md`'s ASR section — this repo's use of "
        "faster-whisper is the explicitly-allowed local fallback, not a "
        "workaround.",
    ]
    (DOCS_DIR / "latency_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {DOCS_DIR / 'latency_report.md'}, latency_report.json, latency_chart.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
