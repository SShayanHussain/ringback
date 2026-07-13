"""Integrations — calendar (Google/Outlook) + CRM. Credentials encrypted at rest (hard rule).

Phase 2 wires these to real providers behind the agent's CalendarProvider/CRMProvider interfaces
(or an n8n workflow). For now this stores encrypted credentials and lists connection status.
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import crypto
from ..deps import current_workspace, require_owner
from ..errors import AppError, ok
from ..repo import get_repo

router = APIRouter(prefix="/integrations", tags=["integrations"])

_ALLOWED = {"google_calendar", "outlook_calendar", "crm"}


class IntegrationIn(BaseModel):
    provider: str
    credentials: dict


@router.get("")
def list_integrations(workspace: str = Depends(current_workspace)):
    return ok(get_repo().list_integrations(workspace))


@router.post("")
def connect(body: IntegrationIn, _: dict = Depends(require_owner),
            workspace: str = Depends(current_workspace)):
    if body.provider not in _ALLOWED:
        raise AppError(422, "bad_provider", f"provider must be one of {sorted(_ALLOWED)}")
    try:
        enc = crypto.encrypt(json.dumps(body.credentials))
    except RuntimeError as e:
        # Refuse to store plaintext credentials (Golden Rule 1).
        raise AppError(500, "encryption_unavailable", str(e)) from e
    get_repo().save_integration(workspace, body.provider, enc)
    return ok({"provider": body.provider, "connected": True})
