"""Tool registry: the single source of truth for what each tool does,
used by both the real Vapi webhook (app/main.py) and the simulator
(sim/chat_sim.py) — so "what the simulator tested" and "what the real
webhook does" can never silently diverge into two implementations.

Every handler takes a plain dict of arguments (matching how Vapi delivers
tool-call arguments) and returns a plain dict (matching how Vapi expects
tool results back); the pydantic models in models.py validate at the
boundary inside each handler, so a malformed call fails with a clear
validation error rather than a confusing downstream crash.

TOOL_SCHEMAS is the JSON-schema tool definition list passed to Vapi by
scripts/create_assistant.py — kept in the same file as the dispatch table
so the schema and the implementation can't drift apart silently.
"""

from __future__ import annotations

from typing import Callable

from voice_agent.app import crm, escalation
from voice_agent.app.kb_client import search_knowledge_base
from voice_agent.app.models import (
    CreateLeadArgs,
    EscalateArgs,
    ScheduleCallbackArgs,
    ScoreLeadArgs,
    SearchKBArgs,
)
from voice_agent.app.scoring import score_lead
from voice_agent.app.settings import Settings


def _handle_search_knowledge_base(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = SearchKBArgs(**arguments)
    return search_knowledge_base(args.query, settings, client=kwargs.get("kb_http_client")).model_dump()


def _handle_score_lead(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = ScoreLeadArgs(**arguments)
    return score_lead(args).model_dump()


def _handle_escalate_to_human(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = EscalateArgs(**arguments)
    return escalation.escalate_to_human(args, settings).model_dump()


def _handle_create_lead(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = CreateLeadArgs(**arguments)
    return crm.create_lead(args, settings.crm_db_path_abs()).model_dump()


def _handle_schedule_callback(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = ScheduleCallbackArgs(**arguments)
    return crm.schedule_callback(args, settings.crm_db_path_abs()).model_dump()


TOOLS: dict[str, Callable[..., dict]] = {
    "search_knowledge_base": _handle_search_knowledge_base,
    "score_lead": _handle_score_lead,
    "escalate_to_human": _handle_escalate_to_human,
    "create_lead": _handle_create_lead,
    "schedule_callback": _handle_schedule_callback,
}


def dispatch_tool(name: str, arguments: dict, settings: Settings, **kwargs) -> dict:
    """Never raises — a malformed tool call or an internal error becomes
    an {"error": ...} result the caller (webhook or simulator) can report,
    rather than crashing the whole call/request. A crashed call is a
    worse failure mode than a visibly-erroring tool result.

    `kwargs` currently supports `kb_http_client` (an httpx.Client) — used
    by tests to point search_knowledge_base at the real kb/ FastAPI app
    in-process (via httpx.ASGITransport) instead of a real network call
    to a separately-running server. The real webhook (main.py) never
    passes this — production search_knowledge_base always makes a real
    HTTP call to KB_API_BASE_URL.
    """

    handler = TOOLS.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name!r}"}
    try:
        return handler(arguments, settings, **kwargs)
    except Exception as exc:
        return {"error": f"Tool {name!r} failed: {exc}"}


TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the knowledge base for grounded facts about products, "
                "policies, eligibility rules, or objection responses. ALWAYS call "
                "this before answering any product/policy/eligibility/objection "
                "question — never answer from memory or invent an answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The customer's question, in their own words.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_lead",
            "description": (
                "Score the lead's qualification (hot/warm/cold) from the details "
                "collected so far. Call this once age, budget, and intent have "
                "been collected (family size / conditions are optional)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer"},
                    "city": {"type": "string"},
                    "family_size": {"type": "integer"},
                    "conditions": {
                        "type": "string",
                        "description": "Free-text description of any disclosed pre-existing conditions.",
                    },
                    "budget": {"type": "integer", "description": "Stated monthly budget in INR."},
                    "intent": {
                        "type": "string",
                        "description": "e.g. interested, exploring, not_interested",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Escalate the call to a human agent. Call this on explicit "
                "request, after 2 failed fallback attempts in a row, on signs of "
                "distress, or on a complaint."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "e.g. explicit_request, repeated_confusion, distress, complaint",
                    },
                    "context": {"type": "string", "description": "Brief context for the human agent."},
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_lead",
            "description": (
                "Create a CRM lead record. Call this once, near the end of the "
                "call, after scoring the lead with score_lead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_name": {"type": "string"},
                    "phone": {"type": "string"},
                    "city": {"type": "string"},
                    "age": {"type": "integer"},
                    "family_size": {"type": "integer"},
                    "conditions": {"type": "string"},
                    "budget": {"type": "integer"},
                    "intent": {"type": "string"},
                    "qualification": {"type": "string", "enum": ["hot", "warm", "cold"]},
                    "qualification_reasons": {"type": "array", "items": {"type": "string"}},
                    "objections_raised": {"type": "array", "items": {"type": "string"}},
                    "call_summary": {"type": "string"},
                    "next_action": {"type": "string"},
                },
                "required": ["qualification", "call_summary", "next_action"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "schedule_callback",
            "description": "Schedule a callback at the customer's requested date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "requested_datetime": {"type": "string", "description": "ISO 8601 datetime."},
                    "notes": {"type": "string"},
                },
                "required": ["phone", "requested_datetime"],
            },
        },
    },
]
