"""Generates docs/PROJECT_WALKTHROUGH.pdf — a written substitute for the
video walkthrough (docs/VIDEO_SCRIPT.md), for submission when there
isn't time to record a video. Covers the same ground the video script
does: system overview, architecture, key decisions, per-question
results (with real numbers), limitations, and production plan.

Run: `python -m docs.scripts.generate_walkthrough_pdf` from the repo
root, or just `python docs/scripts/generate_walkthrough_pdf.py`.
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "docs" / "PROJECT_WALKTHROUGH.pdf"
CHART_PATH = REPO_ROOT / "docs" / "q4_live_nudges" / "latency_chart.png"


class Walkthrough(FPDF):
    def header(self):
        pass

    def footer(self):
        self.set_y(-12)
        self.set_x(self.l_margin)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")


def h1(pdf: Walkthrough, text: str):
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 20, 20)
    pdf.ln(4)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 9, text)
    pdf.ln(1)


def h2(pdf: Walkthrough, text: str):
    pdf.set_font("Helvetica", "B", 12.5)
    pdf.set_text_color(30, 30, 30)
    pdf.ln(2)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 7, text)
    pdf.ln(1)


def body(pdf: Walkthrough, text: str):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 5.6, text)
    pdf.ln(1)


def bullet(pdf: Walkthrough, text: str):
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(40, 40, 40)
    pdf.set_x(pdf.l_margin + 4)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 5.6, f"-  {text}")


def bold_line(pdf: Walkthrough, text: str):
    pdf.set_font("Helvetica", "B", 10.5)
    pdf.set_text_color(10, 10, 10)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 5.6, text)


def hr(pdf: Walkthrough):
    pdf.ln(2)
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(4)


def main() -> None:
    pdf = Walkthrough(format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(15, 15, 15)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 12, "Knowledge-Grounded Voice AI Platform")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_text_color(90, 90, 90)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 7, "Written Project Walkthrough (submitted in place of a recorded video)")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 6, "Repository: https://github.com/diwandahiya304/Darwix-AI-")
    hr(pdf)

    h1(pdf, "1. System Overview")
    body(pdf,
         "This is a knowledge-grounded voice AI platform covering all four parts of the "
         "assessment. Everything shares one retrieval API built in Question 2 (kb/). The "
         "voice agent in Question 1 (voice_agent/) grounds every answer against it. The two "
         "multilingual bots in Question 3 (multilingual/, Philippines + Indonesia) reuse the "
         "same index with language-tagged records. Question 4 (live_nudges/) is a separate "
         "real-time pipeline that turns live call audio into in-call nudges.\n\n"
         "The single rule that runs through everything: the bot must say \"I don't know\" "
         "instead of inventing an answer -- checked by an automated test in every voice "
         "component, not just prompted for.")

    h1(pdf, "2. Architecture and Key Design Decisions")
    body(pdf, "High-level flow:")
    bullet(pdf, "kb/ (Q2): ingest -> clean -> mask PII -> dedupe -> chunk -> version -> hybrid dense+BM25 index -> FastAPI /search")
    bullet(pdf, "voice_agent/ (Q1) and multilingual/ (Q3) both call kb/'s /search directly, filtered by language -- never hardcoded facts in a prompt")
    bullet(pdf, "live_nudges/ (Q4): independent pipeline -- real synthesized call audio -> real streaming ASR -> signal extraction -> nudge controller -> WebSocket dashboard / CLI")
    pdf.ln(2)
    body(pdf, "Three decisions mattered more than the rest:")
    bold_line(pdf, "Hybrid retrieval (dense + BM25), not dense-only.")
    body(pdf, "Pure embedding search sometimes ranked a loose paraphrase above an exact keyword "
              "match (a policy number, a product name). BM25 catches what embeddings miss; fusing "
              "both with Reciprocal Rank Fusion covers more real phrasing than either alone.")
    bold_line(pdf, "Per-language grounding thresholds, not one global number.")
    body(pdf, "The same relevance threshold that worked for English was measurably too strict for "
              "Filipino and Indonesian content -- calibrated separately for each, against real "
              "measured score distributions, not guessed.")
    bold_line(pdf, "A real regression found and fixed: merging Q3's multilingual KB records into "
                   "the shared index silently broke Q1's English hallucination check (88% to 62% "
                   "pass rate), because searches were not language-filtered. Fixed with an explicit "
                   "language filter everywhere, locked in with a regression test.")

    h1(pdf, "3. Knowledge Base and Retrieval Design (Q2)")
    body(pdf, "Schema matches the brief's field example exactly: record_id, title, content, "
              "category, source_ref, version, pii -- every record traceable to a source. "
              "Chunking is category-aware: FAQ/objection content splits into Q/A pairs, "
              "eligibility rules split by bullet, everything else splits by heading then "
              "sentence-count. PII is identified and masked with Presidio plus custom Indian-ID "
              "recognizers.")
    bold_line(pdf, "Real measured results (docs/q2_kb/retrieval_test_results.json):")
    bullet(pdf, "hit@1 = 1.00, hit@3 = 1.00, out-of-scope rejection = 1.00 (13 queries)")
    bullet(pdf, "Retrieval latency: P50 = 74.1ms, P95 = 103.4ms -- well under a 300ms target")
    bullet(pdf, "Working connection to Q1 confirmed: real HTTP calls, not hardcoded FAQs")

    h1(pdf, "4. Voice Agent Flow (Q1)")
    body(pdf, "The system prompt contains zero facts -- verified by an automated test. Every "
              "fact comes from a search_knowledge_base tool call at answer time. Qualification "
              "scoring, escalation, and lead creation are deterministic code, not the LLM "
              "guessing -- important for auditability in an insurance context.")
    bold_line(pdf, "Real results:")
    bullet(pdf, "All 5 required scenarios pass: cooperative, objection, incomplete/conflicting "
                "details, out-of-scope, human escalation")
    bullet(pdf, "Hallucination refusal rate: 87.5% (7/8) -- one genuine, root-caused miss, "
                "reported honestly, not excluded")
    bold_line(pdf, "Honest gap: no live Vapi account exists in this environment, so there is no "
                   "callable number or web-calling interface right now. These are simulated calls "
                   "against real webhook/tool/KB code, not recorded phone calls.")

    h1(pdf, "5. Multilingual Handling (Q3)")
    body(pdf, "Two markets reuse the same KB and retrieval code with language-tagged records and "
              "their own calibrated grounding thresholds.")
    bullet(pdf, "Philippines: life insurance/bancassurance, English/Tagalog/Taglish, register-mirrored (formal po/opo vs. casual). 100% grounding rate across 5 scenarios.")
    bullet(pdf, "Indonesia: multifinance, formal + colloquial Bahasa + English loanwords, OJK-style compliance guardrails in the system prompt. 86% grounding rate across 6 scenarios (one genuine paraphrase-distance retrieval miss, root-caused not hidden).")
    bullet(pdf, "At least 3 localization (not translation) examples per market are documented.")
    bold_line(pdf, "Honest gaps: the Indonesian regional accent is text-level only (no audio was "
                   "synthesized for Q3 at all), and the ASR report for Q3 is explicitly "
                   "illustrative-only -- no Deepgram/Azure credentials, no real audio, no real "
                   "recorded calls for this market.")

    h1(pdf, "6. Live Nudges (Q4) -- the most real part of this submission")
    body(pdf, "This is a genuinely real pipeline, not simulated. A local text-to-speech engine "
              "synthesizes 4 scripted scenarios into real stereo call audio (agent on the left "
              "channel, customer on the right). That audio is replayed in real, paced 300ms "
              "chunks -- never analyzing a finished recording. A real local speech-to-text model "
              "(faster-whisper) runs genuine inference per rolling window as the audio plays. Two "
              "signal layers (fast keyword rules, plus an optional LLM layer that honestly "
              "reports itself as \"not configured\" rather than faking a result) feed a nudge "
              "controller with per-type confidence floors, cooldowns, a semantic-similarity "
              "duplicate check, expiry, and priority ordering (compliance beats frustration beats "
              "opportunity). Delivery is a WebSocket dashboard and a CLI.")
    bold_line(pdf, "Real measured results:")
    bullet(pdf, "Nudge quality (docs/q4_live_nudges/quality_report.md): 83% precision, 100% recall, 0 false negatives, across 4 scenarios x 3 runs each. The one recurring false positive is explained, not hidden: a casual 'sounds good' collides with the buying-signal keyword list.")
    bullet(pdf, "Latency (docs/q4_live_nudges/latency_report.md): ASR P50 = 834ms, P95 = 1651ms (real local model inference); signal extraction and the LLM layer both under 2ms P95.")
    bullet(pdf, "A real (not illustrative) ASR word-error-rate was measured: 44.9% mean WER against synthetic TTS voice audio -- traced to two specific, documented causes (number-format mismatches and a stereo-channel-bleed hallucination artifact), not just reported as a bare number.")
    body(pdf, "Building this surfaced and fixed several real bugs: a sentence split across a "
              "fixed ASR window boundary silently missed a compliance signal; trailing audio "
              "was being silently dropped when a call ended mid-window; and an early "
              "latency-measurement bug made the real ASR inference time vanish from the report. "
              "All are logged with how they were found and fixed.")

    if CHART_PATH.exists():
        pdf.ln(2)
        pdf.image(str(CHART_PATH), w=170)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(110, 110, 110)
        pdf.set_x(pdf.l_margin); pdf.multi_cell(0, 5, "Figure: Q4 per-component latency (P50 / P95 / max), from docs/q4_live_nudges/latency_chart.png")

    h1(pdf, "7. Error and Fallback Cases (across all components)")
    bullet(pdf, "Q1: out-of-scope questions get a polite decline and redirect, never a half-answer (recordings/voice_agent/d_out_of_scope.md)")
    bullet(pdf, "Q3: below the per-language grounding threshold, the bot states it doesn't have that information, in the customer's own language and register -- never switching to English unexpectedly")
    bullet(pdf, "Q4: the noisy/ambiguous scenario produces zero or one nudge, not a flood of false positives; a low-confidence signal is genuinely suppressed by the controller and logged with its reason")

    h1(pdf, "8. Known Limitations")
    bullet(pdf, "No live Vapi/Deepgram/Azure/Anthropic credentials anywhere in this environment by default -- Q1 has no callable number, Q3 has no synthesized audio at all, Q4's LLM layer and telephony side are unconfigured")
    bullet(pdf, "Q4 does not reuse Q1/Q3 recordings (allowed, not required, by the brief) -- it has its own independently-synthesized audio")
    bullet(pdf, "Cross-lingual retrieval margins are thin -- a real regression (found and fixed) shows how easily this class of bug reappears")
    bullet(pdf, "Q4's ASR uses fixed-timer windows, not voice-activity detection, and is measurably imperfect (44.9% WER) even against robotic TTS audio")
    bullet(pdf, "Q4's single-process ASR model and in-process WebSocket broadcaster don't scale to 10x concurrent calls without a real queue/pub-sub backbone")
    bullet(pdf, "No native-speaker or compliance/legal review of any Filipino/Bahasa Indonesia content, or of the OJK/IRDAI-style guardrails")

    h1(pdf, "9. Production Improvement Plan")
    bullet(pdf, "Wire in real providers (Vapi, Deepgram/Azure, Azure/ElevenLabs TTS) behind the existing interfaces -- no code shape change needed, only credentials plus a live smoke test")
    bullet(pdf, "Monitoring and observability: structured logging for every KB search, every tool call, every nudge fired/suppressed, plus latency/error dashboards")
    bullet(pdf, "A continuous eval pipeline in CI (retrieval hit@k, hallucination refusal rate, nudge precision/recall) with a required-to-pass threshold, instead of on-demand reports")
    bullet(pdf, "PII compliance hardening: multilingual NER validated for Filipino/Bahasa Indonesia, encryption at rest, an audit log, a data-retention policy")
    bullet(pdf, "Cost tracking: LLM tokens, ASR minutes, TTS characters, with a per-call cost ceiling and alerting")
    bullet(pdf, "Scaling: per-call-id state and a real pub/sub backbone (Redis/Kafka) for Q4, horizontal scaling for the KB API")
    bullet(pdf, "A human-in-the-loop review queue for hallucination-check failures, suppressed nudges, and retrieval misses -- closing the loop from \"found in testing\" to \"fixed in production\"")
    bullet(pdf, "A/B testing of prompts, fallback phrasing, and nudge confidence thresholds against real traffic before committing to one configuration")
    bullet(pdf, "Native-speaker and compliance/legal review of every Filipino/Bahasa Indonesia string and every compliance-guardrail claim before this reaches a real customer")

    h1(pdf, "10. Closing")
    body(pdf, "Everything described here is real, tested code -- 222 tests across four "
              "components, all passing, all runnable with `make test`. Every number in this "
              "walkthrough came from a report file under docs/, not eyeballed. Where something "
              "isn't real -- no live Vapi, no live ASR provider for Q3, illustrative-only numbers "
              "-- that is stated in the same breath as the result, because that was the standard "
              "this build was held to throughout.\n\n"
              "Full detail on every decision: docs/DECISIONS.md. Plain-language defense of the "
              "biggest choices plus 15 likely interview questions: docs/DEFENSE_NOTES.md. "
              "Line-by-line audit against the assessment brief, including what's genuinely not "
              "done yet: docs/SUBMISSION_CHECKLIST.md.")

    pdf.output(str(OUT_PATH))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
