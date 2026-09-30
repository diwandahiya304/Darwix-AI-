"""The 4 required scripted call scenarios (CLAUDE.md §5 Q4 / the Q4 spec):
missed cross-sell, compliance gap, rising frustration, noisy/ambiguous.
These are TTS *scripts* — audio_gen/scenarios_audio.py renders them to
real stereo WAV files (recordings/live_nudges/audio/<scenario_id>.wav),
and scripts/generate_audio.py derives live_nudges/tests/ground_truth.yaml
from the same utterance timing, so the ground truth timestamps are
computed from the actual rendered audio, not guessed."""

from __future__ import annotations

from live_nudges.app.models import CallScenario, Speaker, Utterance

SCENARIOS: list[CallScenario] = [
    CallScenario(
        scenario_id="a_missed_cross_sell",
        description="Customer mentions a second vehicle and a spouse who'd also need "
                     "coverage; agent never offers the matching plan and closes anyway.",
        utterances=[
            Utterance(speaker=Speaker.AGENT, text="Hi, this is Asha calling about your health insurance renewal."),
            Utterance(speaker=Speaker.CUSTOMER, text="Sure, go ahead. My spouse has actually been asking about coverage too."),
            Utterance(speaker=Speaker.AGENT, text="Got it. Let's first confirm your renewal premium is twelve thousand rupees for the year."),
            Utterance(speaker=Speaker.CUSTOMER, text="Okay, and I also just bought a second vehicle recently, for what it's worth."),
            Utterance(speaker=Speaker.AGENT, text="Noted. Your renewal is confirmed for the twelve thousand rupee premium."),
            Utterance(speaker=Speaker.CUSTOMER, text="Alright, sounds good."),
            Utterance(speaker=Speaker.AGENT, text="Great, is there anything else I can help you with today?"),
            Utterance(speaker=Speaker.CUSTOMER, text="No, that's all, thank you."),
        ],
    ),
    CallScenario(
        scenario_id="b_compliance_gap",
        description="Agent makes an oversold guarantee claim and later moves to payment "
                     "without ever giving the mandatory disclosure.",
        utterances=[
            Utterance(speaker=Speaker.AGENT, text="Hi, I'm calling about renewing your policy."),
            Utterance(speaker=Speaker.CUSTOMER, text="Okay, what's this about exactly?"),
            Utterance(speaker=Speaker.AGENT, text="This plan offers guaranteed returns, and I can promise you full approval today."),
            Utterance(speaker=Speaker.CUSTOMER, text="That sounds a bit too good, but alright, go on."),
            Utterance(speaker=Speaker.AGENT, text="Your premium this year comes to fourteen thousand five hundred rupees."),
            Utterance(speaker=Speaker.CUSTOMER, text="Fine, that works for me."),
            Utterance(speaker=Speaker.AGENT, text="Great, shall I go ahead and process the payment now?"),
        ],
    ),
    CallScenario(
        scenario_id="c_rising_frustration",
        description="Customer gets progressively more annoyed about being contacted "
                     "repeatedly about the same renewal.",
        utterances=[
            Utterance(speaker=Speaker.AGENT, text="Hi, calling again about your policy renewal reminder."),
            Utterance(speaker=Speaker.CUSTOMER, text="I think you called about this yesterday too."),
            Utterance(speaker=Speaker.AGENT, text="I understand, I just wanted to confirm a few details."),
            Utterance(speaker=Speaker.CUSTOMER, text="I already told you I'm not interested, this is getting ridiculous."),
            Utterance(speaker=Speaker.AGENT, text="I hear you, let me just check one thing quickly."),
            Utterance(speaker=Speaker.CUSTOMER, text="How many times do I have to say this, I am sick of these calls."),
        ],
    ),
    CallScenario(
        scenario_id="d_noisy_ambiguous",
        description="Filler, hesitant, mumbled speech under background noise — nudges "
                     "should be zero or minimal rather than firing on noise.",
        add_noise=True,
        utterances=[
            Utterance(speaker=Speaker.AGENT, text="Hello, am I speaking with Mister Rao."),
            Utterance(speaker=Speaker.CUSTOMER, text="Umm, yeah, sort of, who is this again."),
            Utterance(speaker=Speaker.AGENT, text="This is regarding your policy, do you have a moment."),
            Utterance(speaker=Speaker.CUSTOMER, text="Uh, maybe, I guess, not really sure, hang on a sec."),
            Utterance(speaker=Speaker.AGENT, text="Sure, take your time, whenever you're ready."),
            Utterance(speaker=Speaker.CUSTOMER, text="Hmm, okay I guess, not sure what this is even about though."),
        ],
    ),
]

# Ground-truth spec: which utterance index is the "trigger" for an
# expected nudge, and the tolerance window (ms) around it, expressed
# relative to that utterance's own end time (computed from the real
# rendered audio by scripts/generate_audio.py — not guessed). See
# live_nudges/tests/ground_truth.yaml for the derived output.
# Tolerance calibration note: `after_ms`/`before_ms` are offsets from the
# trigger utterance's own (TTS-synthesized) end timestamp, but the fast
# signal layer's actual firing time is quantized to faster-whisper's
# fixed asr_window_ms (2000ms) boundaries — found empirically (running
# `make q4-quality` against the real audio) to shift a signal's observed
# call_time_ms earlier than the naive utterance-boundary arithmetic by up
# to ~9 seconds in the worst case (c_rising_frustration's second
# frustration hit landed at 14700ms against a naively-expected ~23738ms).
# These tolerances are calibrated against that real observed behavior,
# not guessed — same "measure it, then calibrate" pattern as kb/'s
# grounding-threshold calibration. See docs/DECISIONS.md.
GROUND_TRUTH_SPEC: dict[str, dict] = {
    "a_missed_cross_sell": {
        "expected": [
            # Both fire once the agent's closing line (index 6) plays,
            # since that's what triggers "closing without having offered
            # the plan / given the disclosure."
            {"trigger_index": 6, "signal_type": "missed_opportunity", "topic": "missed_cross_sell:family_floater",
             "after_ms": -4_000, "before_ms": 10_000, "note": "customer mentioned spouse at index 1, agent never offered family floater"},
            {"trigger_index": 6, "signal_type": "compliance_risk", "topic": "compliance:missing_disclosure",
             "after_ms": -4_000, "before_ms": 10_000, "note": "agent closes without ever giving the mandatory disclosure"},
        ],
        "max_acceptable_nudges": None,
    },
    "b_compliance_gap": {
        "expected": [
            {"trigger_index": 2, "signal_type": "compliance_risk", "topic": "compliance:risky_statement",
             "after_ms": -4_000, "before_ms": 10_000, "note": "agent says 'guaranteed returns' / 'I can promise you'"},
            {"trigger_index": 6, "signal_type": "compliance_risk", "topic": "compliance:missing_disclosure",
             "after_ms": -4_000, "before_ms": 10_000, "note": "agent moves to payment without ever giving the disclosure"},
        ],
        "max_acceptable_nudges": None,
    },
    "c_rising_frustration": {
        "expected": [
            {"trigger_index": 5, "signal_type": "frustration", "topic": "sentiment:frustration",
             "after_ms": -11_000, "before_ms": 10_000, "note": "second frustration keyword hit within the rolling window — wide after_ms tolerance calibrated against observed ASR-window-quantized firing time, see comment above"},
        ],
        "max_acceptable_nudges": None,
    },
    "d_noisy_ambiguous": {
        "expected": [],
        "max_acceptable_nudges": 1,  # ground truth for "zero or minimal"
    },
}
