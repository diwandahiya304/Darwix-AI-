"""Computes a REAL ASR word-error-rate for the Q4 pipeline — unlike
multilingual/asr_bench/'s illustrative-only numbers (no live provider
credentials there), Q4's ASR is a real local model (faster-whisper)
running on real (if TTS-synthesized) audio, and the TTS script text
itself is an exact reference transcript, so a genuine WER/CER is
computable here without needing any external ground-truth labeling.

**Caveat, stated plainly**: this measures faster-whisper's accuracy on
synthetic, robotic TTS voice audio, not real human speech — a real
speaker's prosody, disfluencies, and recording conditions would likely
produce different (probably worse) numbers. It is still a genuine,
reproducible measurement of this specific pipeline, not an illustrative
stand-in.

Writes docs/q4_live_nudges/asr_accuracy.md + .json.
Run: `python -m live_nudges.scripts.compute_asr_accuracy` (also invoked
by `make q4-report`).
"""

from __future__ import annotations

import json
import sys

import jiwer

from live_nudges.app.models import Speaker
from live_nudges.app.pipeline import run_call
from live_nudges.app.semantic import embed_for_dedup
from live_nudges.app.settings import REPO_ROOT, get_settings
from live_nudges.sim.scenarios import SCENARIOS

AUDIO_DIR = REPO_ROOT / "recordings" / "live_nudges" / "audio"
DOCS_PATH_MD = REPO_ROOT / "docs" / "q4_live_nudges" / "asr_accuracy.md"
DOCS_PATH_JSON = REPO_ROOT / "docs" / "q4_live_nudges" / "asr_accuracy.json"
SPEED = 20.0


def _reference_text_by_speaker(scenario) -> dict[Speaker, str]:
    texts: dict[Speaker, list[str]] = {Speaker.AGENT: [], Speaker.CUSTOMER: []}
    for utterance in scenario.utterances:
        texts[utterance.speaker].append(utterance.text)
    return {speaker: " ".join(lines) for speaker, lines in texts.items()}


def _hypothesis_text_by_speaker(transcript) -> dict[Speaker, str]:
    texts: dict[Speaker, list[str]] = {Speaker.AGENT: [], Speaker.CUSTOMER: []}
    for segment in transcript:
        if segment.is_final and segment.text:
            texts[segment.speaker].append(segment.text)
    return {speaker: " ".join(lines) for speaker, lines in texts.items()}


def main() -> int:
    settings = get_settings()
    rows = []
    for scenario in SCENARIOS:
        audio_path = AUDIO_DIR / f"{scenario.scenario_id}.wav"
        if not audio_path.exists():
            print(f"Missing {audio_path} — run `make q4-generate-audio` first", file=sys.stderr)
            return 1
        result = run_call(audio_path, call_id=f"wer_{scenario.scenario_id}", settings=settings,
                           speed=SPEED, embed_fn=embed_for_dedup)
        reference = _reference_text_by_speaker(scenario)
        hypothesis = _hypothesis_text_by_speaker(result.transcript)
        for speaker in (Speaker.AGENT, Speaker.CUSTOMER):
            ref, hyp = reference[speaker].strip(), hypothesis[speaker].strip()
            if not ref:
                continue
            wer = jiwer.wer(ref, hyp) if hyp else 1.0
            cer = jiwer.cer(ref, hyp) if hyp else 1.0
            rows.append({
                "scenario_id": scenario.scenario_id, "speaker": speaker.value,
                "wer": round(wer, 3), "cer": round(cer, 3),
                "reference": ref, "hypothesis": hyp,
            })

    mean_wer = sum(r["wer"] for r in rows) / len(rows)
    mean_cer = sum(r["cer"] for r in rows) / len(rows)

    DOCS_PATH_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_PATH_JSON.write_text(json.dumps({"mean_wer": round(mean_wer, 3), "mean_cer": round(mean_cer, 3), "rows": rows}, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Q4 Live Nudges: Real ASR Accuracy (faster-whisper, tiny.en)",
        "",
        "**This is a genuinely measured WER/CER**, not the illustrative-only "
        "numbers in `docs/q3_multilingual/asr_report.md` — Q4's ASR is a real "
        "local model (faster-whisper) and the TTS script text is an exact "
        "reference transcript, so WER/CER against it is a real, reproducible "
        "measurement of this pipeline.",
        "",
        "**Caveat**: measured against synthetic (pyttsx3) TTS voice audio, not "
        "real human speech — real speakers' prosody/disfluencies/recording "
        "conditions would likely produce different (plausibly worse) numbers. "
        "This is real, not illustrative, but it is not a claim about "
        "real-call ASR accuracy.",
        "",
        f"**Mean WER: {mean_wer:.1%}, mean CER: {mean_cer:.1%}** across "
        f"{len(rows)} (scenario, speaker) transcript pairs.",
        "",
        "| Scenario | Speaker | WER | CER |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['scenario_id']} | {row['speaker']} | {row['wer']:.1%} | {row['cer']:.1%} |")
    lines += [
        "",
        "Full reference/hypothesis text pairs: `docs/q4_live_nudges/asr_accuracy.json`.",
    ]
    DOCS_PATH_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {DOCS_PATH_MD} — mean WER={mean_wer:.1%}, mean CER={mean_cer:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
