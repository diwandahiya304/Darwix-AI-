# Q4 Live Nudges: Quality Report (Precision / Recall / False Positives)

Each of the 4 required scenarios run 3x against the real pipeline (real TTS-generated audio -> real faster-whisper ASR -> real signal/nudge logic), scored against hand-labeled, timestamp-bounded expected nudges in `live_nudges/tests/ground_truth.yaml`.

| Scenario | Run | TP | FP | FN | Precision | Recall | Suppressed | Within tolerance |
|---|---|---|---|---|---|---|---|---|
| a_missed_cross_sell | 1 | 2 | 1 | 0 | 67% | 100% | 4 | yes |
| a_missed_cross_sell | 2 | 2 | 1 | 0 | 67% | 100% | 4 | yes |
| a_missed_cross_sell | 3 | 2 | 1 | 0 | 67% | 100% | 4 | yes |
| b_compliance_gap | 1 | 2 | 0 | 0 | 100% | 100% | 8 | yes |
| b_compliance_gap | 2 | 2 | 0 | 0 | 100% | 100% | 8 | yes |
| b_compliance_gap | 3 | 2 | 0 | 0 | 100% | 100% | 8 | yes |
| c_rising_frustration | 1 | 1 | 0 | 0 | 100% | 100% | 1 | yes |
| c_rising_frustration | 2 | 1 | 0 | 0 | 100% | 100% | 1 | yes |
| c_rising_frustration | 3 | 1 | 0 | 0 | 100% | 100% | 1 | yes |
| d_noisy_ambiguous | 1 | 0 | 0 | 0 | 100% | 100% | 0 | yes |
| d_noisy_ambiguous | 2 | 0 | 0 | 0 | 100% | 100% | 0 | yes |
| d_noisy_ambiguous | 3 | 0 | 0 | 0 | 100% | 100% | 0 | yes |

**Totals across all 4 scenarios x 3 runs:** 15 true positive, 3 false positive, 0 false negative. Precision: 83%, Recall: 100%.

## The recurring false positive, explained

The 1 false positive in every `a_missed_cross_sell` run is the same
one each time: the customer's line "Alright, sounds good" (a casual
acknowledgement of the confirmed premium amount) contains the substring
"sounds good", which `app/signals_fast.py`'s `_BUYING_SIGNAL_KEYWORDS`
list matches unconditionally — firing a `buying_signal:ready_to_close`
nudge that doesn't reflect a real buying moment. This is a genuine
keyword-collision limitation of the fast rule layer (a short phrase
list has no way to distinguish "sounds good [I accept the price]" from
"sounds good [as a genuine close-ready signal]"), reported honestly
rather than tuned away by special-casing this one sentence. A semantic
or LLM-based layer (see `docs/q4_live_nudges/limitations.md`) would be
the real fix, not a longer keyword blocklist.

## Run-to-run variance

- `a_missed_cross_sell`: identical (TP=2, FP=1, FN=0) across all 3 runs
- `b_compliance_gap`: identical (TP=2, FP=0, FN=0) across all 3 runs
- `c_rising_frustration`: identical (TP=1, FP=0, FN=0) across all 3 runs
- `d_noisy_ambiguous`: identical (TP=0, FP=0, FN=0) across all 3 runs

**No variance observed.** faster-whisper's decoding is deterministic for identical input audio on CPU (greedy decoding, no sampling), and the fast/LLM signal layers are deterministic given identical transcript text — so identical audio reliably produces identical nudges here. This is a real property of this specific pipeline (scripted audio, local deterministic ASR), not evidence that a production system with live audio and a live ASR provider would behave this predictably — see docs/q4_live_nudges/limitations.md.
