"""Shared pydantic models for the voice_agent/ webhook server, tools, and
simulator. CLAUDE.md §1: pydantic for every data model crossing a
function/API boundary.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class LeadTemperature(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


# --- search_knowledge_base ------------------------------------------------


class SearchKBArgs(BaseModel):
    query: str


class SearchKBResult(BaseModel):
    grounded: bool
    speakable_answer: str
    citations: list[str] = Field(default_factory=list)
    category: str | None = None


# --- score_lead -------------------------------------------------------------


class ScoreLeadArgs(BaseModel):
    age: int | None = None
    city: str | None = None
    family_size: int | None = None
    conditions: str | None = None  # free text, e.g. "diabetes, controlled"
    budget: int | None = None  # monthly budget in INR
    intent: str | None = None  # e.g. "interested" | "exploring" | "not_interested"


class ScoreLeadResult(BaseModel):
    temperature: LeadTemperature
    points: int
    reasons: list[str]


# --- escalate_to_human --------------------------------------------------


class EscalateArgs(BaseModel):
    reason: str
    call_id: str | None = None
    context: str | None = None


class EscalateResult(BaseModel):
    escalated: bool
    method: str  # "webhook" | "transfer_logged" | "logged_only"
    logged_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# --- create_lead (mock CRM) ----------------------------------------------


class CreateLeadArgs(BaseModel):
    call_id: str | None = None
    customer_name: str | None = None
    phone: str | None = None
    city: str | None = None
    age: int | None = None
    family_size: int | None = None
    conditions: str | None = None
    budget: int | None = None
    intent: str | None = None
    qualification: LeadTemperature
    qualification_reasons: list[str] = Field(default_factory=list)
    objections_raised: list[str] = Field(default_factory=list)
    call_summary: str
    next_action: str


class CreateLeadResult(BaseModel):
    lead_id: str
    created_at: str


# --- schedule_callback -----------------------------------------------------


class ScheduleCallbackArgs(BaseModel):
    phone: str
    requested_datetime: str  # ISO 8601
    call_id: str | None = None
    notes: str | None = None


class ScheduleCallbackResult(BaseModel):
    callback_id: str
    confirmed_datetime: str


# --- Vapi webhook envelope --------------------------------------------------
# Best-effort model of Vapi's server-tool-call webhook contract, built from
# documentation/training knowledge, NOT verified against a live account
# (none is available in this environment — see README "Vapi Setup"). Treat
# this shape as a starting point to confirm/adjust against Vapi's current
# docs and a real webhook payload once connected to a live assistant.


class VapiFunctionCall(BaseModel):
    name: str
    arguments: dict


class VapiToolCall(BaseModel):
    id: str
    type: str = "function"
    function: VapiFunctionCall


class VapiMessage(BaseModel):
    type: str = "tool-calls"
    toolCallList: list[VapiToolCall] = Field(default_factory=list)
    call: dict | None = None


class VapiWebhookRequest(BaseModel):
    message: VapiMessage


class VapiToolResultItem(BaseModel):
    toolCallId: str
    result: str


class VapiWebhookResponse(BaseModel):
    results: list[VapiToolResultItem]
