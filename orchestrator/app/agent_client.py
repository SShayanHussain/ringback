"""Thin client to the agent core's /chat. This is the seam voice will reuse verbatim."""
from __future__ import annotations

import httpx

from .config import get_settings


def chat(message: str, session_id: str, workspace_id: str, vertical: str, state: dict | None) -> dict:
    url = get_settings().agent_core_url.rstrip("/") + "/chat"
    try:
        resp = httpx.post(
            url,
            json={"message": message, "session_id": session_id, "workspace_id": workspace_id,
                  "vertical": vertical, "state": state},
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(f"agent core unavailable: {e}") from e
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", "agent core error"))
    return data
