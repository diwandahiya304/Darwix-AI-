"""Pydantic models for the Q4 live-nudges pipeline. CLAUDE.md §1: pydantic
for every data model that crosses a function or API boundary — no bare
dicts between the audio, ASR, signal-extraction, and nudge-generation
stages."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Speaker(str, Enum):
    AGENT = "agent"
    CUSTOMER = "customer"


class Utterance(BaseModel):
    """One scripted line used to synthesize a scenario's test audio (see
    audio_gen/scenarios_audio.py). This is the TTS *script*, not what the
    pipeline sees at runtime — the pipeline only ever sees real audio
    samples and the transcript faster-whisper produces from them."""

    speaker: Speaker
    text: str


class CallScenario(BaseModel):
    scenario_id: str
    description: str
    utterances: list[Utterance]
    # Scenario d mixes in background noise at generation time — see
    # audio_gen/scenarios_audio.py.
    add_noise: bool = False


class AudioChunk(BaseModel):
    """One paced real-time chunk from app/audio_io.py's chunker. Carries
    raw samples as a list (not a numpy array) only at the pydantic
    boundary — app/streaming_asr.py converts back to ndarray immediately,
    since pydantic/JSON have no native ndarray type."""

    chunk_id: int
    speaker: Speaker
    samples: list[float]  # mono float32 PCM, already resampled to asr_sample_rate
    call_time_ms: int      # position in the call this chunk ends at
    t_audio_sent: float    # wall-clock epoch ms when this chunk became "available"


class TranscriptSegment(BaseModel):
    """Output of the streaming ASR stage — either a partial (interim) or
    final transcript for a rolling window of one speaker's channel."""

    segment_id: int
    speaker: Speaker
    text: str
    is_final: bool
    window_start_ms: int
    window_end_ms: int
    asr_latency_ms: float  # real measured wall-clock faster-whisper inference time


class ComplianceRisk(BaseModel):
    type: str
    evidence: str


class MissedOpportunity(BaseModel):
    type: str
    evidence: str


class LLMSignalResult(BaseModel):
    """Strict JSON schema the LLM layer (app/signals_llm.py) must return.
    Anything that fails to validate against this is treated as "LLM layer
    unavailable for this window" (same never-invent posture as
    voice_agent's KB grounding) rather than a best-effort partial parse."""

    intent: str | None = None
    topic_shift: bool = False
    compliance_risk: ComplianceRisk | None = None
    frustration_score: float = Field(default=0.0, ge=0.0, le=1.0)
    buying_signal: bool = False
    missed_opportunity: MissedOpportunity | None = None
    callback_needed: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class SignalType(str, Enum):
    INTENT_SHIFT = "intent_shift"
    COMPLIANCE_RISK = "compliance_risk"
    FRUSTRATION = "frustration"
    BUYING_SIGNAL = "buying_signal"
    MISSED_OPPORTUNITY = "missed_opportunity"
    CALLBACK_NEEDED = "callback_needed"
    PAYMENT_DIFFICULTY = "payment_difficulty"


class SignalLayer(str, Enum):
    FAST = "fast"   # app/signals_fast.py — keyword/regex/rule, <50ms
    LLM = "llm"     # app/signals_llm.py — Claude Haiku, sliding window


class Signal(BaseModel):
    """A raw detection from either signal-extraction layer. Not every
    signal becomes a nudge — app/controller.py applies thresholds/
    cooldowns/dedup/priority-preemption before that."""

    signal_type: SignalType
    topic: str  # coarse grouping key for duplicate-suppression/cooldowns
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_text: str
    layer: SignalLayer
    segment_id: int
    call_time_ms: int


class NudgePriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"


class Nudge(BaseModel):
    """A short (<=~15 words), actionable prompt surfaced to the agent
    while the call is still in progress."""

    nudge_id: str
    signal_type: SignalType
    topic: str
    priority: NudgePriority
    message: str
    confidence: float
    evidence_text: str
    layer: SignalLayer
    call_time_ms: int
    created_at_ms: float   # wall-clock epoch ms
    expires_at_ms: float


class LatencyEvent(BaseModel):
    """One timestamped hop, appended to a per-call JSONL log as the call
    runs (app/pipeline.py). `make q4-report` reconstructs per-component
    durations from consecutive hops sharing a segment_id."""

    call_id: str
    segment_id: int
    hop: str  # audio_received | asr_done | signals_done | llm_done | nudge_created | delivered
    t_wall_ms: float


class GroundTruthNudge(BaseModel):
    """One expected nudge for a test scenario, hand-labeled with an
    approximate timestamp — see live_nudges/tests/ground_truth.yaml."""

    signal_type: SignalType
    topic: str
    expected_after_ms: int
    expected_before_ms: int
    note: str = ""


class ScenarioGroundTruth(BaseModel):
    scenario_id: str
    expected_nudges: list[GroundTruthNudge]
    max_acceptable_nudges: int  # ground truth for "zero or minimal" scenarios
