"""Indonesia webhook server — what Vapi's custom-LLM/tool-calling setup
calls at runtime for the installment-reminder/collections-support
assistant. Mirrors voice_agent/app/main.py's structure exactly.

Run: `make multilingual-run-id` (uvicorn, port $ID_PORT).
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI

from voice_agent.app.models import VapiToolResultItem, VapiWebhookRequest, VapiWebhookResponse

from multilingual.common.settings import get_settings
from multilingual.indonesia.app.tools import dispatch

logger = logging.getLogger("multilingual.indonesia.webhook")

app = FastAPI(title="Indonesia Voice Bot Webhook")


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
    return {"status": "ok", "market": "indonesia"}
