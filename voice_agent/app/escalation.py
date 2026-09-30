"""escalate_to_human: triggered on explicit request, repeated confusion
(2 fallbacks), distress, or complaint — the conversation-flow layer
decides WHEN to call this (see docs/voice_flow.md); this module only
implements WHAT happens once it's called.

Logs every escalation to data/processed/escalations.jsonl (append-only,
auditable, never contains raw customer PII beyond what the call itself
already carries in `context` — same caveat as crm.py). If
ESCALATION_WEBHOOK_URL is configured, also POSTs the event there (e.g. a
real alerting/CRM webhook). There is no real telephony transfer
capability without a live Vapi account: when ESCALATION_TRANSFER_NUMBER
is configured but no webhook is, this logs a "would transfer to <number>"
entry for demo purposes rather than pretending a transfer happened.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

from voice_agent.app.models import EscalateArgs, EscalateResult
from voice_agent.app.settings import REPO_ROOT, Settings

_DEFAULT_LOG_PATH = REPO_ROOT / "data" / "processed" / "escalations.jsonl"


def escalate_to_human(
    args: EscalateArgs,
    settings: Settings,
    client: httpx.Client | None = None,
    log_path: Path | None = None,
) -> EscalateResult:
    log_path = log_path or _DEFAULT_LOG_PATH
    now = datetime.now(timezone.utc).isoformat()

    method = "logged_only"
    if settings.escalation_webhook_url:
        owns_client = client is None
        http_client = client or httpx.Client(timeout=5.0)
        try:
            try:
                http_client.post(
                    settings.escalation_webhook_url,
                    json={
                        "reason": args.reason,
                        "call_id": args.call_id,
                        "context": args.context,
                        "logged_at": now,
                    },
                )
                method = "webhook"
            except httpx.HTTPError:
                # Webhook delivery failing must never crash the call or
                # silently drop the escalation — it's still logged locally.
                method = "logged_only"
        finally:
            if owns_client:
                http_client.close()
    elif settings.escalation_transfer_number:
        method = "transfer_logged"

    entry = {
        "logged_at": now,
        "reason": args.reason,
        "call_id": args.call_id,
        "context": args.context,
        "method": method,
        "transfer_number": settings.escalation_transfer_number if method == "transfer_logged" else None,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return EscalateResult(escalated=True, method=method, logged_at=now)
