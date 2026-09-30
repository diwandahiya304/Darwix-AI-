"""Philippines tool registry: the common tools (search_knowledge_base
scoped to language="fil", escalate_to_human, schedule_callback) plus
set_auto_debit_preference — this market's one business action.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from multilingual.common.settings import Settings
from multilingual.common.tools import COMMON_TOOL_SCHEMAS, build_common_tools, dispatch_tool
from multilingual.philippines.app.auto_debit import SetAutoDebitArgs, set_auto_debit_preference

_FALLBACK_PATH = Path(__file__).resolve().parents[1] / "config" / "fallback_messages.yaml"


def _load_fallback_messages() -> dict[str, str]:
    with _FALLBACK_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _handle_set_auto_debit_preference(arguments: dict, settings: Settings, **kwargs) -> dict:
    args = SetAutoDebitArgs(**arguments)
    return set_auto_debit_preference(args, settings.crm_db_path_abs()).model_dump()


def build_tools() -> dict:
    tools = build_common_tools("fil", _load_fallback_messages())
    tools["set_auto_debit_preference"] = _handle_set_auto_debit_preference
    return tools


TOOLS = build_tools()

TOOL_SCHEMAS: list[dict] = COMMON_TOOL_SCHEMAS + [
    {
        "type": "function",
        "function": {
            "name": "set_auto_debit_preference",
            "description": "Record the customer's auto-debit enrollment preference for their premium.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_number": {"type": "string"},
                    "enroll": {"type": "boolean"},
                    "payment_day": {"type": "integer", "description": "Preferred day of month, 1-28."},
                },
                "required": ["policy_number", "enroll"],
            },
        },
    },
]


def dispatch(name: str, arguments: dict, settings: Settings, **kwargs) -> dict:
    return dispatch_tool(name, arguments, TOOLS, settings, **kwargs)
