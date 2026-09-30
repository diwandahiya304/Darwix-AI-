"""Creates or updates a Vapi assistant for one market — `--market
philippines` or `--market indonesia`. Mirrors voice_agent/scripts/
create_assistant.py's pattern exactly (same honesty caveats apply: no
live Vapi account exists in this environment, so the request payload
construction is tested directly but the actual POST to Vapi's API is
not verified against a live response — see multilingual/README.md 'Vapi
Setup Steps').

Requires VAPI_API_KEY and this market's *_WEBHOOK_BASE_URL
(PH_WEBHOOK_BASE_URL / ID_WEBHOOK_BASE_URL). Writes the response to
multilingual/<market>/config/vapi_assistant.json — no API key included,
safe to commit.

Run: `make multilingual-create-assistant-ph` /
`make multilingual-create-assistant-id`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

from multilingual.common.settings import REPO_ROOT, Settings, get_settings

VAPI_BASE_URL = "https://api.vapi.ai"

_MARKETS = {
    "philippines": {
        "assistant_name": "philippines-premium-reminder",
        "tools_module": "multilingual.philippines.app.tools",
        "config_dir": REPO_ROOT / "multilingual" / "philippines" / "config",
        "first_message": "Magandang araw po! Ito po si Grace, tumatawag mula sa inyong bangko partner.",
        "voice": {"provider": "azure", "voiceId": "fil-PH-BlessicaNeural"},
        "webhook_url_attr": "ph_webhook_base_url",
    },
    "indonesia": {
        "assistant_name": "indonesia-installment-reminder",
        "tools_module": "multilingual.indonesia.app.tools",
        "config_dir": REPO_ROOT / "multilingual" / "indonesia" / "config",
        "first_message": "Selamat siang, Bapak/Ibu. Saya Budi dari perusahaan pembiayaan Anda.",
        "voice": {"provider": "azure", "voiceId": "id-ID-ArdiNeural"},
        "webhook_url_attr": "id_webhook_base_url",
    },
}


def build_assistant_payload(market: str, webhook_base_url: str) -> dict:
    """Pure — no network. system_prompt.md contains ONLY persona/tone/
    call-flow/guardrails/tool-usage rules — every fact comes from
    TOOL_SCHEMAS' search_knowledge_base at call time."""

    import importlib

    config = _MARKETS[market]
    system_prompt = (config["config_dir"] / "system_prompt.md").read_text(encoding="utf-8")
    tools_module = importlib.import_module(config["tools_module"])

    return {
        "name": config["assistant_name"],
        "model": {
            "provider": "anthropic",
            "model": "claude-haiku-4-5-20251001",
            "messages": [{"role": "system", "content": system_prompt}],
            "tools": tools_module.TOOL_SCHEMAS,
            "toolCallUrl": f"{webhook_base_url.rstrip('/')}/webhook",
        },
        "firstMessage": config["first_message"],
        "voice": config["voice"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create/update a Vapi assistant for one market.")
    parser.add_argument("--market", choices=list(_MARKETS), required=True)
    args = parser.parse_args(argv)

    settings = get_settings()
    if not settings.has_vapi_credentials():
        print(
            "VAPI_API_KEY is not configured (or is still 'changeme'). "
            "Set it in .env — see multilingual/README.md 'Vapi Setup Steps'.",
            file=sys.stderr,
        )
        return 1

    webhook_base_url = getattr(settings, _MARKETS[args.market]["webhook_url_attr"])
    if not webhook_base_url:
        print(
            f"{_MARKETS[args.market]['webhook_url_attr'].upper()} is not configured. "
            f"Expose multilingual/{args.market}/app/main.py publicly (ngrok/cloudflared) "
            f"and set it in .env, then re-run this script.",
            file=sys.stderr,
        )
        return 1

    payload = build_assistant_payload(args.market, webhook_base_url)
    with httpx.Client(base_url=VAPI_BASE_URL, timeout=15.0) as client:
        response = client.post(
            "/assistant", headers={"Authorization": f"Bearer {settings.vapi_api_key}"}, json=payload
        )
    if response.status_code >= 400:
        print(f"Vapi API returned {response.status_code}: {response.text}", file=sys.stderr)
        return 1

    data = response.json()
    output_path = _MARKETS[args.market]["config_dir"] / "vapi_assistant.json"
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Assistant created/updated: id={data.get('id')}. Config written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
