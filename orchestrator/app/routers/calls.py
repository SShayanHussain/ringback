"""Call log — every call: transcript, intent, actions, outcome (PRD §7). Always tenant-scoped."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import current_workspace
from ..errors import AppError, ok
from ..repo import get_repo

router = APIRouter(prefix="/calls", tags=["calls"])


@router.get("")
def list_calls(workspace: str = Depends(current_workspace), limit: int = 100):
    return ok(get_repo().list_calls(workspace, limit=limit))


@router.get("/{call_id}")
def get_call(call_id: str, workspace: str = Depends(current_workspace)):
    call = get_repo().get_call(workspace, call_id)
    if not call:
        raise AppError(404, "not_found", "Call not found.")
    return ok(call)
