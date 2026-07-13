"""Agent-core HTTP service. POST /chat is the single seam text AND voice both call.

Stateless per request except for the mock tools, which persist in a per-process registry keyed by
workspace so a multi-turn text session (book -> reschedule) works in the playground. In Phase 2 the
calendar becomes a real external system and this registry goes away.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .agent import Agent
from .config import get_settings
from .logging_ import CallLog
from .state import ConversationState
from .tools import MockCalendar, MockCRM
from .vertical import load_vertical

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("ringback.agent")

app = FastAPI(title="Ringback Agent Core", version="0.1.0")
_settings = get_settings()
_TOOLS: dict[str, tuple[MockCalendar, MockCRM]] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str = "sess"
    workspace_id: str = "default"
    vertical: str | None = None
    state: dict | None = None


def _get_agent(vertical_name: str, workspace: str) -> Agent:
    vertical = load_vertical(vertical_name)
    key = f"{workspace}:{vertical_name}"
    if key not in _TOOLS:
        _TOOLS[key] = (MockCalendar(vertical.business_hours), MockCRM())
    cal, crm = _TOOLS[key]
    return Agent(vertical=vertical, calendar=cal, crm=crm, settings=_settings)


@app.api_route("/health", methods=["GET", "HEAD"])  # GET+HEAD for uptime pingers (PLAYBOOK §12.6)
def health():
    return {"status": "ok"}


@app.get("/vertical")
def vertical(name: str | None = None):
    v = load_vertical(name or _settings.vertical)
    return {
        "vertical": v.name,
        "business_name": v.business_name,
        "business_hours": v.business_hours,
        "services": [
            {"id": s.id, "name": s.name, "duration_min": s.duration_min, "price": s.price}
            for s in v.services
        ],
        "booking_fields": v.booking_fields,
        "transfer_number": v.transfer_number(),
    }


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        vertical_name = req.vertical or _settings.vertical
        agent = _get_agent(vertical_name, req.workspace_id)
        state = ConversationState.from_dict(req.state) if req.state else ConversationState(
            session_id=req.session_id, vertical=vertical_name
        )
        state.session_id = req.session_id
        result = agent.handle_turn(state, req.message)
        return {
            "reply": result.reply,
            "state": state.to_dict(),
            "meta": {
                "intent": result.intent,
                "confidence": result.confidence,
                "escalated": result.escalated,
                "escalation_reason": state.escalation_reason,
                "outcome": result.outcome,
                "actions": result.actions,
                "finished": state.finished,
            },
            "call_log": CallLog.from_state(state).to_dict(),
        }
    except Exception as e:  # noqa: BLE001 — always JSON, never a plain-text 500 (PLAYBOOK §12.4)
        log.exception("chat failed")
        return JSONResponse(status_code=502, content={"error": {"message": str(e)}})
