"""Standalone CLI streaming simulator:
``python -m live_nudges.replay --audio file.wav --speed 1.0``

Sends real audio chunks with real timing (app/audio_io.py), runs them
through the real ASR/signal/nudge pipeline (app/pipeline.py), and prints
the transcript and nudges to stdout/stderr as they're produced — this is
the CLI delivery channel, and also the same core call this module's
FastAPI server (app/main.py) runs in-process for the WebSocket dashboard.

Writes a per-call JSONL latency log to
data/processed/live_nudges_latency/<call_id>.jsonl (regenerable
intermediate data — `make q4-report` aggregates every call's log under
that directory into the checked-in P50/P95/max report).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from live_nudges.app.models import Nudge, TranscriptSegment
from live_nudges.app.pipeline import run_call
from live_nudges.app.semantic import embed_for_dedup
from live_nudges.app.settings import REPO_ROOT, get_settings

LATENCY_DIR = REPO_ROOT / "data" / "processed" / "live_nudges_latency"


def _print_segment(segment: TranscriptSegment) -> None:
    tag = "final" if segment.is_final else "partial"
    print(f"[{segment.window_end_ms:>6}ms] {segment.speaker.value:>8} ({tag}, "
          f"{segment.asr_latency_ms:.0f}ms): {segment.text}")


def _print_nudge(nudge: Nudge) -> None:
    print(f"           >>> NUDGE [{nudge.priority.value.upper()}] {nudge.message}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", required=True, help="path to a WAV file (stereo preferred; mono falls back to a single channel)")
    parser.add_argument("--speed", type=float, default=1.0, help="real-time speed multiplier (1.0 = real time)")
    parser.add_argument("--call-id", default=None, help="defaults to the audio file's stem")
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"No such file: {audio_path}", file=sys.stderr)
        return 1
    call_id = args.call_id or audio_path.stem

    settings = get_settings()
    print(f"=== {call_id} ({audio_path}) — speed x{args.speed} ===")
    result = run_call(
        audio_path, call_id=call_id, settings=settings, speed=args.speed,
        embed_fn=embed_for_dedup, latency_log_path=LATENCY_DIR / f"{call_id}.jsonl",
        on_segment=_print_segment, on_nudge=_print_nudge,
    )
    print(f"--- {len(result.nudges)} nudge(s), {len(result.suppressed)} suppressed, "
          f"LLM layer {'configured' if result.llm_configured else 'NOT configured (see .env LLM_API_KEY)'} ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
