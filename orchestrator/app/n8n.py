"""Outbound automation seam. The orchestrator POSTs business events (booking / escalation / lead)
to an n8n/Zapier/Make webhook the user builds. Signed with an HMAC so the flow can verify origin.

Fire-and-forget: a webhook hiccup must NEVER fail the call (it's glue, per DECISIONS.md).
See docs/AUTOMATION-GUIDE.md for the exact payloads.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
import uuid

import httpx

from .config import get_settings

log = logging.getLogger("ringback.n8n")


def notify(event: str, data: dict) -> dict:
    s = get_settings()
    if not s.n8n_webhook_url:
        log.info("n8n webhook not configured; skipping event=%s", event)
        return {"skipped": True}
    # event_id lets the receiving flow dedupe under webhook storms (PLAYBOOK §9).
    envelope = {"event": event, "event_id": uuid.uuid4().hex, "ts": int(time.time()), "data": data}
    body = json.dumps(envelope, separators=(",", ":"))
    sig = hmac.new(s.n8n_webhook_secret.encode(), body.encode(), hashlib.sha256).hexdigest() \
        if s.n8n_webhook_secret else ""
    try:
        httpx.post(
            s.n8n_webhook_url,
            content=body,
            headers={"Content-Type": "application/json", "X-Ringback-Signature": sig},
            timeout=10,
        )
        return {"sent": True}
    except httpx.HTTPError as e:
        log.warning("n8n webhook failed (event=%s): %s", event, e)
        return {"error": str(e)}
