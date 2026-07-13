"""Health — GET + HEAD, no DB/LLM, so uptime pingers keep the free service warm (PLAYBOOK §12.6)."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}
