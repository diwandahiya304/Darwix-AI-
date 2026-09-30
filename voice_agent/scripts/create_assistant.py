"""Creates or updates the Vapi assistant configuration via Vapi's REST
API — the platform config is reproducible by running this script rather
than clicking through Vapi's dashboard, satisfying "config reproducible
via script" and "stored as JSON with secrets stripped."

Requires VAPI_API_KEY and WEBHOOK_BASE_URL (the public URL Vapi can reach
your local voice_agent/app/main.py through — see README "Vapi Setup
Steps" for exposing it via ngrok/cloudflared). If either is missing, this
exits with a clear message rather than crashing.

**Honesty check**: no live Vapi account is available in this development
environment. `build_assistant_payload()` (the request body construction)
is tested directly and the "fails gracefully without credentials" path
is verified for real — but the actual POST to Vapi's API, and the exact
shape Vapi expects, are NOT verified against a live response. Vapi's API
can change; if this script errors against a real account, check Vapi's
current `/assistant` create-endpoint docs and adjust
`build_assistant_payload` — the rest of this repo (webhook, tools,
scoring, CRM) doesn't depend on this script succeeding.

The response is written to voice_agent/config/vapi_assistant.json with
the API key itself never included — only Vapi's own returned
assistant id/config, which is safe to commit.
"""

from __future__ import annotations

import json
import sys

import httpx

from voice_agent.app.settings import REPO_ROOT, get_settings
from voice_agent.app.tools import TOOL_SCHEMAS

SYSTEM_PROMPT_PATH = REPO_ROOT / "voice_agent" / "config" / "system_prompt.md"
OUTPUT_PATH = REPO_ROOT / "voice_agent" / "config" / "vapi_assistant.json"
VAPI_BASE_URL = "https://api.vapi.ai"


def build_assistant_payload(webhook_base_url: str) -> dict:
    """Pure — no network. The request body sent to Vapi's assistant
    create endpoint. system_prompt.md contains ONLY persona/tone/call-
    flow/guardrails/tool-usage rules (see CLAUDE.md / the assignment
    brief's explicit "do not put facts in the system prompt" instruction)
    — every fact this assistant states comes from TOOL_SCHEMAS'
    search_knowledge_base at call time.
    """

    system_prompt = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    return {
        "name": "health-insurance-lead-qualification",
        "model": {
            # Swap provider/model for your preference — nothing else in
            # this repo depends on which LLM backs the live assistant.
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "messages": [{"role": "system", "content": system_prompt}],
            "tools": TOOL_SCHEMAS,
            "toolCallUrl": f"{webhook_base_url.rstrip('/')}/webhook",
        },
        "firstMessage": "Hi, this is Asha calling from Acme Insurance — do you have a moment?",
        # Pick a real voice id in the Vapi dashboard/docs before creating for real.
        "voice": {"provider": "11labs", "voiceId": "changeme"},
    }


def main() -> int:
    settings = get_settings()
    if not settings.has_vapi_credentials():
        print(
            "VAPI_API_KEY is not configured (or is still 'changeme'). "
            "Set it in .env — see README 'Vapi Setup Steps' — then re-run this script.",
            file=sys.stderr,
        )
        return 1
    if not settings.webhook_base_url:
        print(
            "WEBHOOK_BASE_URL is not configured. Expose voice_agent/app/main.py "
            "publicly (ngrok/cloudflared — see README 'Vapi Setup Steps') and set "
            "WEBHOOK_BASE_URL to that URL in .env, then re-run this script.",
            file=sys.stderr,
        )
        return 1

    payload = build_assistant_payload(settings.webhook_base_url)
    with httpx.Client(base_url=VAPI_BASE_URL, timeout=15.0) as client:
        response = client.post(
            "/assistant",
            headers={"Authorization": f"Bearer {settings.vapi_api_key}"},
            json=payload,
        )
    if response.status_code >= 400:
        print(f"Vapi API returned {response.status_code}: {response.text}", file=sys.stderr)
        return 1

    data = response.json()
    OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Assistant created/updated: id={data.get('id')}. Config written to {OUTPUT_PATH}")
    print(f"Set VAPI_ASSISTANT_ID={data.get('id')} in .env.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
