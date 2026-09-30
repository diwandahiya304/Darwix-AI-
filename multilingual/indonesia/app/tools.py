"""Indonesia tool registry: the common tools (search_knowledge_base
scoped to language="id", escalate_to_human, schedule_callback) plus
record_promise_to_pay — this market's one business action.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from multilingual.common.settings import Settings
from multilingual.common.tools import COMMON_TOOL_SCHEMAS, build_common_tools, dispatch_tool
from multilingual.indonesia.app.promise_to_pay import RecordPromiseToPayArgs, record_promise_to_pay

_FALLBACK_PATH = Path(__file__).resolve().parents[1] / "config" / "fallback_messages.yaml"


def _load_fallback_messages() -> dict[str, str]:
    with _FALLBACK_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _handle_record_promise_to_pay(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = RecordPromiseToPayArgs(**arguments)
    return record_promise_to_pay(args, settings.crm_db_path_abs()).model_dump()


def build_tools() -> dict:
    tools = build_common_tools("id", _load_fallback_messages())
    tools["record_promise_to_pay"] = _handle_record_promise_to_pay
    return tools


TOOLS = build_tools()

TOOL_SCHEMAS: list[dict] = COMMON_TOOL_SCHEMAS + [
    {
        "type": "function",
        "function": {
            "name": "record_promise_to_pay",
            "description": "Record a customer's committed payment date/amount ('janji bayar').",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_id": {"type": "string"},
                    "promise_date": {"type": "string", "description": "ISO 8601 date."},
                    "amount": {"type": "integer", "description": "Amount in IDR."},
                },
                "required": ["loan_id", "promise_date"],
            },
        },
    },
]


def dispatch(name: str, arguments: dict, settings: Settings, **kwargs) -> dict:
    return dispatch_tool(name, arguments, TOOLS, settings, **kwargs)
