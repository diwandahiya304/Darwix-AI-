"""voice_agent webhook server — what Vapi's custom-LLM/tool-calling setup
calls at runtime.

POST /webhook receives Vapi's tool-call message, dispatches each call
through app/tools.py's registry (the same registry sim/chat_sim.py uses),
and returns Vapi's expected response shape. GET /health is a plain
liveness check.

The exact request/response envelope (models.VapiWebhookRequest/Response)
is a best-effort model of Vapi's documented server-tool-call contract,
not verified against a live account (none is available in this
environment — see README "Vapi Setup Steps"). If Vapi's actual payload
shape differs once connected to a real assistant, adjust the parsing
here — tools.py's dispatch logic is independent of the exact envelope
shape and won't need to change.

Run: `make run-voice-agent` (uvicorn, port $VOICE_AGENT_PORT). Point
Vapi's assistant server-tool-call URL at
`<WEBHOOK_BASE_URL>/webhook` (see README for exposing this locally via
ngrok/cloudflared).
"""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI

from voice_agent.app.models import VapiToolResultItem, VapiWebhookRequest, VapiWebhookResponse
from voice_agent.app.settings import get_settings
from voice_agent.app.tools import dispatch_tool

logger = logging.getLogger("voice_agent.webhook")

app = FastAPI(title="Voice Agent Webhook")


@app.post("/webhook", response_model=VapiWebhookResponse)
def webhook(request: VapiWebhookRequest) -> VapiWebhookResponse:
    settings = get_settings()
    results: list[VapiToolResultItem] = []
    for tool_call in request.message.toolCallList:
        result = dispatch_tool(tool_call.function.name, tool_call.function.arguments, settings)
        logger.info(
            "tool=%s args=%s result=%s", tool_call.function.name, tool_call.function.arguments, result
        )
        results.append(VapiToolResultItem(toolCallId=tool_call.id, result=json.dumps(result)))
    return VapiWebhookResponse(results=results)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
