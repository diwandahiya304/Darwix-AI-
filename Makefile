.PHONY: help setup test \
        test-kb test-voice-agent test-multilingual test-live-nudges \
        ingest-kb kb-index kb-search kb-eval \
        voice-agent-sim voice-agent-hallucination-check voice-agent-test-results \
        voice-agent-create-assistant voice-agent-pull-transcripts \
        multilingual-ingest-kb multilingual-sim-ph multilingual-sim-id \
        multilingual-comparison multilingual-asr-bench \
        multilingual-create-assistant-ph multilingual-create-assistant-id \
        q4-generate-audio q4-sim q4-report q4-quality q4-demo \
        run-kb run-voice-agent multilingual-run-ph multilingual-run-id run-live-nudges \
        clean

PYTHON ?= python

help:
	@echo "Targets:"
	@echo "  make setup               - install pinned dependencies (activate your venv first)"
	@echo "  make test                - run all component test suites"
	@echo "  make test-kb             - run kb/ tests"
	@echo "  make test-voice-agent    - run voice_agent/ tests"
	@echo "  make test-multilingual   - run multilingual/ tests"
	@echo "  make test-live-nudges    - run live_nudges/ tests"
	@echo "  make ingest-kb           - run the KB ingestion/cleaning pipeline (data/raw -> data/processed + docs/q2_kb)"
	@echo "  make kb-index            - (re)build the vector+BM25 retrieval index from kb_records.jsonl"
	@echo "  make kb-search q=\"...\"   - search the KB from the command line"
	@echo "  make kb-eval             - run the retrieval eval harness (kb/eval/queries.yaml -> docs/q2_kb/retrieval_test_results.md)"
	@echo "  make run-kb              - run kb/ retrieval API (uvicorn, port \$$KB_PORT)"
	@echo "  make voice-agent-sim              - run all 5 test scenarios (scripted, no API key needed)"
	@echo "  make voice-agent-hallucination-check - run the 8-question hallucination check"
	@echo "  make voice-agent-test-results     - compile docs/q1_voice_agent/test_results.md"
	@echo "  make voice-agent-create-assistant - create/update the Vapi assistant (needs VAPI_API_KEY)"
	@echo "  make voice-agent-pull-transcripts - pull real call transcripts from Vapi (needs VAPI_API_KEY)"
	@echo "  make run-voice-agent     - run voice_agent/ webhook server (uvicorn, port \$$VOICE_AGENT_PORT)"
	@echo "  make multilingual-ingest-kb        - ingest PH+ID KB seed content (language-tagged)"
	@echo "  make multilingual-sim-ph           - run all Philippines test scenarios (scripted, real KB)"
	@echo "  make multilingual-sim-id           - run all Indonesia test scenarios (scripted, real KB)"
	@echo "  make multilingual-comparison       - compile docs/q3_multilingual/comparison.md"
	@echo "  make multilingual-asr-bench        - run the ASR benchmark harness (illustrative, see caveat in report)"
	@echo "  make multilingual-create-assistant-ph - create/update the PH Vapi assistant (needs VAPI_API_KEY)"
	@echo "  make multilingual-create-assistant-id - create/update the ID Vapi assistant (needs VAPI_API_KEY)"
	@echo "  make multilingual-run-ph           - run the Philippines webhook server (uvicorn, port \$$PH_PORT)"
	@echo "  make multilingual-run-id           - run the Indonesia webhook server (uvicorn, port \$$ID_PORT)"
	@echo "  make q4-generate-audio   - render the 4 scenario WAVs + ground_truth.yaml (real TTS, only needed after editing scenarios.py)"
	@echo "  make q4-sim              - replay one scenario in real time via CLI: make q4-sim scenario=b_compliance_gap"
	@echo "  make q4-report           - run all 4 scenarios, write docs/q4_live_nudges/latency_report.{md,json,png}"
	@echo "  make q4-quality          - run each scenario 3x, write docs/q4_live_nudges/quality_report.md"
	@echo "  make q4-demo             - start the live_nudges dashboard server and open it in a browser"
	@echo "  make run-live-nudges     - run the live_nudges dashboard/WebSocket server (uvicorn, port \$$LIVE_NUDGES_PORT)"
	@echo "  make clean               - remove caches/build artifacts"

# Create/activate a Python 3.11 virtualenv yourself first, e.g.:
#   python -m venv .venv && source .venv/bin/activate   (macOS/Linux/Git Bash)
#   python -m venv .venv && .venv\Scripts\activate       (Windows PowerShell)
setup:
	@if command -v uv >/dev/null 2>&1; then \
		echo "Installing with uv..."; \
		uv pip install -r requirements.txt; \
	else \
		echo "Installing with pip..."; \
		$(PYTHON) -m pip install -r requirements.txt; \
	fi

test: test-kb test-voice-agent test-multilingual test-live-nudges

test-kb:
	$(PYTHON) -m pytest kb/tests -v

test-voice-agent:
	$(PYTHON) -m pytest voice_agent/tests -v

test-multilingual:
	$(PYTHON) -m pytest multilingual/tests -v

test-live-nudges:
	$(PYTHON) -m pytest live_nudges/tests -v

# Extract -> clean -> standardize -> mask PII -> dedupe -> chunk. Generates
# a synthetic dataset into data/raw/ first if it's empty. Writes
# data/processed/{kb_records.jsonl,source_issues.json} and
# docs/q2_kb/{kb_cleaning_report,pii_report}.{md,json}.
ingest-kb:
	$(PYTHON) -m kb.app.ingest.pipeline

# Embeds every active KB record and (re)builds the vector store + BM25
# index. `make run-kb`/`make kb-search` do this automatically on first
# use if the vector store is empty, but this target lets you force a
# rebuild (e.g. after `make ingest-kb` changes record content/versions).
kb-index:
	$(PYTHON) -m kb.app.retrieval.index_builder

# Usage: make kb-search q="what is the waiting period for pre-existing disease cover"
kb-search:
	$(PYTHON) -m kb.app.retrieval.cli --query "$(q)"

# Runs kb/eval/queries.yaml against the live retrieval index and writes
# docs/q2_kb/retrieval_test_results.{md,json} (hit@1, hit@3, out-of-scope
# rejection rate, per-query verdicts).
kb-eval:
	$(PYTHON) -m kb.eval.run_eval

run-kb:
	$(PYTHON) -m uvicorn kb.app.main:app --reload --port $${KB_PORT:-8001}

# Runs all 5 required scenarios (cooperative, objection, incomplete/
# conflicting, out-of-scope, human-escalation) via sim/chat_sim.py's
# scripted mode — real tool calls against the real KB, no API key needed.
# Writes recordings/voice_agent/*.md.
voice-agent-sim:
	$(PYTHON) -m voice_agent.sim.chat_sim

# 8 questions deliberately not in the KB — the bot must refuse to invent
# an answer for every one. Writes docs/q1_voice_agent/hallucination_check.{md,json}.
voice-agent-hallucination-check:
	$(PYTHON) -m voice_agent.sim.hallucination_check

# Runs both of the above plus per-scenario pass/fail evaluation and
# writes docs/q1_voice_agent/test_results.md.
voice-agent-test-results:
	$(PYTHON) -m voice_agent.scripts.compile_test_results

# Requires VAPI_API_KEY + WEBHOOK_BASE_URL in .env — see
# voice_agent/README.md "Vapi Setup Steps". Not run in this environment
# (no live Vapi account); fails gracefully with a clear message if unset.
voice-agent-create-assistant:
	$(PYTHON) -m voice_agent.scripts.create_assistant

# Requires VAPI_API_KEY + VAPI_ASSISTANT_ID in .env. Not run in this
# environment (no live Vapi account); fails gracefully if unset.
voice-agent-pull-transcripts:
	$(PYTHON) -m voice_agent.scripts.pull_transcripts

run-voice-agent:
	$(PYTHON) -m uvicorn voice_agent.app.main:app --reload --port $${VOICE_AGENT_PORT:-8002}

# Ingests the Philippines + Indonesia KB seed content (language-tagged,
# via kb.app.ingest.pipeline's extra_raw_dirs) into the same
# data/processed/kb_records.jsonl the English KB uses. Run `make kb-index`
# afterwards to rebuild the retrieval index with the new records included.
multilingual-ingest-kb:
	$(PYTHON) -m multilingual.scripts.ingest_multilingual_kb

# Runs all Philippines scenarios (scripted, real KB via in-process
# TestClient, no API key needed). Writes recordings/multilingual/philippines/*.md.
multilingual-sim-ph:
	$(PYTHON) -m multilingual.philippines.sim.chat_sim

# Runs all Indonesia scenarios (scripted, real KB via in-process
# TestClient, no API key needed). Writes recordings/multilingual/indonesia/*.md.
multilingual-sim-id:
	$(PYTHON) -m multilingual.indonesia.sim.chat_sim

# Runs both markets' scenarios for real and compiles
# docs/q3_multilingual/comparison.md (fallback behaviour, grounding rate).
multilingual-comparison:
	$(PYTHON) -m multilingual.scripts.compile_comparison

# Illustrative ASR benchmark harness (jiwer WER/CER, code-switching,
# named-term accuracy) — no live ASR credentials in this environment, see
# docs/q3_multilingual/asr_report.md's "Read this first" caveat.
multilingual-asr-bench:
	$(PYTHON) -m multilingual.asr_bench.run_benchmark

# Requires VAPI_API_KEY + PH_WEBHOOK_BASE_URL in .env — see
# multilingual/README.md "Vapi Setup Steps". Not run in this environment
# (no live Vapi account); fails gracefully with a clear message if unset.
multilingual-create-assistant-ph:
	$(PYTHON) -m multilingual.scripts.create_assistant --market philippines

# Requires VAPI_API_KEY + ID_WEBHOOK_BASE_URL in .env. Not run in this
# environment (no live Vapi account); fails gracefully if unset.
multilingual-create-assistant-id:
	$(PYTHON) -m multilingual.scripts.create_assistant --market indonesia

multilingual-run-ph:
	$(PYTHON) -m uvicorn multilingual.philippines.app.main:app --reload --port $${PH_PORT:-8003}

multilingual-run-id:
	$(PYTHON) -m uvicorn multilingual.indonesia.app.main:app --reload --port $${ID_PORT:-8004}

# Renders the 4 required scripted scenarios to real stereo WAVs
# (recordings/live_nudges/audio/*.wav, agent=left/customer=right channel)
# via local offline TTS (pyttsx3), and derives
# live_nudges/tests/ground_truth.yaml from the actual rendered timing.
# Only needs re-running after editing live_nudges/sim/scenarios.py — the
# WAVs and ground truth are checked into git like any other test fixture.
q4-generate-audio:
	$(PYTHON) -m live_nudges.scripts.generate_audio

# Replays one scenario's real audio in real time (1x speed) through the
# real streaming ASR -> signal extraction -> nudge pipeline, printing the
# transcript and each nudge to stdout/stderr as it's produced — the CLI
# delivery channel. Usage: make q4-sim scenario=b_compliance_gap
scenario ?= a_missed_cross_sell
q4-sim:
	$(PYTHON) -m live_nudges.replay --audio recordings/live_nudges/audio/$(scenario).wav --speed 1.0

# Runs all 4 scenarios (compressed speed — see the report's own caveat on
# why that doesn't affect the honesty of the numbers) and writes
# docs/q4_live_nudges/latency_report.{md,json} + latency_chart.png, plus
# a real (not illustrative) ASR WER/CER report (asr_accuracy.{md,json}).
q4-report:
	$(PYTHON) -m live_nudges.scripts.compile_latency_report
	$(PYTHON) -m live_nudges.scripts.compute_asr_accuracy

# Runs each of the 4 scenarios 3x against ground_truth.yaml and writes
# docs/q4_live_nudges/quality_report.md (precision/recall/false
# positives/suppression rate, with honest run-to-run variance).
q4-quality:
	$(PYTHON) -m live_nudges.scripts.compile_quality_report

# Starts the dashboard/WebSocket server and opens it in the default
# browser. Pick a scenario from the dropdown and click Start to watch
# transcript + nudges arrive live over the WebSocket.
q4-demo:
	$(PYTHON) -c "import webbrowser, time, threading; threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:$${LIVE_NUDGES_PORT:-8005}')).start()"
	$(PYTHON) -m uvicorn live_nudges.app.main:app --port $${LIVE_NUDGES_PORT:-8005}

run-live-nudges:
	$(PYTHON) -m uvicorn live_nudges.app.main:app --reload --port $${LIVE_NUDGES_PORT:-8005}

clean:
	find . -type d -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache */.pytest_cache
