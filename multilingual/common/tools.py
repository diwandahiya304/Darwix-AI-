"""Builds a market-specific tool registry: a language-scoped, register-
aware search_knowledge_base, plus escalate_to_human and
schedule_callback reused DIRECTLY from voice_agent/app/ (generic, not
English-specific — Python's duck typing means voice_agent's functions
work fine against this module's Settings object since it exposes the
same attribute names they read, escalation_webhook_url etc.). Each
market's app/tools.py adds its own one extra tool on top of what
`build_common_tools` returns.

Mirrors voice_agent/app/tools.py's dispatch_tool pattern exactly, so the
same webhook/simulator code shape applies to every market — see
docs/DECISIONS.md.
"""

from __future__ import annotations

from typing import Callable

from voice_agent.app import crm, escalation
from voice_agent.app.models import EscalateArgs, ScheduleCallbackArgs

from multilingual.common.kb_client import search_localized_knowledge_base
from multilingual.common.settings import Settings


def build_common_tools(language: str, fallback_messages: dict[str, str]) -> dict[str, Callable]:
    def _handle_search_knowledge_base(arguments: dict, settings: Settings, **kwargs) -> dict:
        query = arguments["query"]
        customer_utterance = arguments.get("customer_utterance", query)
        result = search_localized_knowledge_base(
            query,
            language,
            fallback_messages,
            settings,
            customer_utterance=customer_utterance,
            client=kwargs.get("kb_http_client"),
        )
        return result.model_dump()

    def _handle_escalate_to_human(arguments: dict, settings: Settings, **kwargs) -> dict:
        args = EscalateArgs(**arguments)
        return escalation.escalate_to_human(args, settings).model_dump()

    def _handle_schedule_callback(arguments: dict, settings: Settings, **kwargs) -> dict:
        args = ScheduleCallbackArgs(**arguments)
        return crm.schedule_callback(args, settings.crm_db_path_abs()).model_dump()

    return {
        "search_knowledge_base": _handle_search_knowledge_base,
        "escalate_to_human": _handle_escalate_to_human,
        "schedule_callback": _handle_schedule_callback,
    }


COMMON_TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search this market's knowledge base for grounded facts. ALWAYS "
                "call this before answering any product/policy/eligibility/"
                "objection question — never answer from memory or invent an "
                "answer. Pass the customer's most recent utterance as "
                "customer_utterance so the fallback (if needed) matches their "
                "register."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The customer's question, in their own words."},
                    "customer_utterance": {
                        "type": "string",
                        "description": "The customer's most recent message verbatim (for register detection).",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Escalate the call to a human agent. Call on explicit request, "
                "after 2 fallback responses in a row, on distress, or on a "
                "complaint."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["reason"],
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


def dispatch_tool(name: str, arguments: dict, tools: dict[str, Callable], settings: Settings, **kwargs) -> dict:
    """Never raises — same reliability principle as
    voice_agent/app/tools.py::dispatch_tool."""

    handler = tools.get(name)
    if handler is None:
        return {"error": f"Unknown tool: {name!r}"}
    try:
        return handler(arguments, settings, **kwargs)
    except Exception as exc:
        return {"error": f"Tool {name!r} failed: {exc}"}
