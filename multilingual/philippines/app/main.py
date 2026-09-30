"""Philippines webhook server — what Vapi's custom-LLM/tool-calling setup
calls at runtime for the premium/renewal-reminder assistant. Mirrors
voice_agent/app/main.py's structure exactly (same envelope model, reused
from voice_agent.app.models) — see docs/DECISIONS.md for why this
pattern is duplicated per market rather than shared.

Run: `make multilingual-run-ph` (uvicorn, port $PH_PORT).
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI

from voice_agent.app.models import VapiToolResultItem, VapiWebhookRequest, VapiWebhookResponse

from multilingual.common.settings import get_settings
from multilingual.philippines.app.tools import dispatch

logger = logging.getLogger("multilingual.philippines.webhook")

app = FastAPI(title="Philippines Voice Bot Webhook")


@app.post("/webhook", response_model=VapiWebhookResponse)
def webhook(request: VapiWebhookRequest) -> VapiWebhookResponse:
    settings = get_settings()
    results: list[VapiToolResultItem] = []
    for tool_call in request.message.toolCallList:
        result = dispatch(tool_call.function.name, tool_call.function.arguments, settings)
        logger.info(
            "tool=%s args=%s result=%s", tool_call.function.name, tool_call.function.arguments, result
        )
        results.append(VapiToolResultItem(toolCallId=tool_call.id, result=json.dumps(result)))
    return VapiWebhookResponse(results=results)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "market": "philippines"}
