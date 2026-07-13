"""Configuration — business hours, services, FAQ, escalation rules, confirmation scripts.

Defaults come from the vertical config (served by the agent core); tenant edits are stored as
overrides. Facts the agent speaks always resolve from here, never model memory.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config import get_settings
from ..deps import current_workspace, require_owner
from ..errors import ok
from ..repo import get_repo

router = APIRouter(prefix="/config", tags=["config"])


class ConfigIn(BaseModel):
    overrides: dict


@router.get("")
def get_config(workspace: str = Depends(current_workspace)):
    s = get_settings()
    defaults = {}
    try:
        r = httpx.get(f"{s.agent_core_url.rstrip('/')}/vertical", params={"name": s.vertical}, timeout=10)
        r.raise_for_status()
        defaults = r.json()
    except httpx.HTTPError:
        defaults = {"vertical": s.vertical, "note": "agent core unavailable; showing overrides only"}
    return ok({"defaults": defaults, "overrides": get_repo().get_config(workspace)})


@router.put("")
def put_config(body: ConfigIn, _: dict = Depends(require_owner),
               workspace: str = Depends(current_workspace)):
    get_repo().set_config(workspace, body.overrides)
    return ok({"saved": True})
