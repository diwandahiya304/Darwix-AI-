"""Pulls call records/transcripts from the Vapi API into
/recordings/voice_agent/vapi_calls/ — the raw material for a real
docs/q1_test_results.md once real calls exist.

Requires VAPI_API_KEY and VAPI_ASSISTANT_ID (from
scripts/create_assistant.py). If either is missing, exits with a clear
message rather than crashing.

**Honesty check**: no live Vapi account is available in this development
environment — the "fails gracefully without credentials" path is
verified for real, but the actual GET against Vapi's API is not verified
against real call data. The test evidence for this submission
(recordings/voice_agent/, docs/q1_test_results.md) was instead generated
via sim/chat_sim.py's scripted mode, which exercises the real webhook and
tools end-to-end — clearly labeled as simulated, not real Vapi calls. Run
this script for real once real Vapi calls exist.
"""

from __future__ import annotations

import json
import sys

import httpx

from voice_agent.app.settings import REPO_ROOT, get_settings

VAPI_BASE_URL = "https://api.vapi.ai"
OUTPUT_DIR = REPO_ROOT / "recordings" / "voice_agent" / "vapi_calls"


def main() -> int:
    settings = get_settings()
    if not settings.has_vapi_credentials():
        print("VAPI_API_KEY is not configured — see README 'Vapi Setup Steps'.", file=sys.stderr)
        return 1
    if not settings.vapi_assistant_id:
        print(
            "VAPI_ASSISTANT_ID is not configured — run scripts/create_assistant.py first.",
            file=sys.stderr,
        )
        return 1

    with httpx.Client(base_url=VAPI_BASE_URL, timeout=15.0) as client:
        response = client.get(
            "/call",
            headers={"Authorization": f"Bearer {settings.vapi_api_key}"},
            params={"assistantId": settings.vapi_assistant_id},
        )
    if response.status_code >= 400:
        print(f"Vapi API returned {response.status_code}: {response.text}", file=sys.stderr)
        return 1

    calls = response.json()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for call in calls:
        call_id = call.get("id", "unknown")
        (OUTPUT_DIR / f"{call_id}.json").write_text(json.dumps(call, indent=2), encoding="utf-8")
    print(f"Pulled {len(calls)} call(s) into {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
