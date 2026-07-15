"""Text playground — the free way to exercise the agent. Proxies to the agent core /chat, persists
the call log (tenant-scoped) at terminal states, and fires the n8n automation seam.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import agent_client, n8n
from ..config import get_settings
from ..deps import current_workspace
from ..errors import ok
from ..repo import get_repo

router = APIRouter(prefix="/playground", tags=["playground"])


class ChatIn(BaseModel):
    message: str
    session_id: str = "web"
    state: dict | None = None


@router.post("/chat")
def chat(body: ChatIn, workspace: str = Depends(current_workspace)):
    s = get_settings()
    data = agent_client.chat(body.message, body.session_id, workspace, s.vertical, body.state)
    meta = data.get("meta", {})
    call_log = data.get("call_log", {})

    if meta.get("finished") or meta.get("escalated"):
        get_repo().insert_call(workspace, call_log)
        _notify(workspace, meta, call_log)

    return ok({"reply": data.get("reply", ""), "meta": meta, "state": data.get("state")})


def _notify(workspace: str, meta: dict, call_log: dict) -> None:
    repo = get_repo()
    # Where booking/escalation notifications should land: the owner-configured address if set,
    # else the workspace owner's signup email. Make maps this to the Gmail "To" field.
    cfg = repo.get_config(workspace)
    notify_email = cfg.get("notify_email") or repo.get_workspace_owner_email(workspace)
    base = {"workspace_id": workspace, "notify_email": notify_email,
            "session_id": call_log.get("session_id"),
            "intent": meta.get("intent"), "outcome": meta.get("outcome")}
    for action in meta.get("actions", []):
        t = action.get("type")
        if t == "booking_created":
            n8n.notify("booking.created", {**base, "booking": action, "transcript": call_log.get("transcript")})
        elif t == "booking_cancelled":
            n8n.notify("booking.cancelled", {**base, "booking": action})
        elif t == "booking_modified":
            n8n.notify("booking.rescheduled", {**base, "booking": action})
        elif t == "escalation":
            n8n.notify("call.escalated", {**base, "escalation": action, "transcript": call_log.get("transcript")})
    if meta.get("outcome") == "qualified":
        n8n.notify("lead.qualified", {**base, "transcript": call_log.get("transcript")})
