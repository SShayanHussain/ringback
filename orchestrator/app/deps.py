"""Auth dependencies. current_workspace() is the tenant boundary every data route depends on."""
from __future__ import annotations

from fastapi import Depends, Header

from .config import get_settings
from .errors import AppError
from .security import verify_jwt


def get_claims(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError(401, "unauthorized", "Missing bearer token.")
    claims = verify_jwt(authorization[7:], get_settings().jwt_access_secret)
    if not claims or "workspace_id" not in claims:
        raise AppError(401, "unauthorized", "Invalid or expired token.")
    return claims


def current_workspace(claims: dict = Depends(get_claims)) -> str:
    return claims["workspace_id"]


def require_owner(claims: dict = Depends(get_claims)) -> dict:
    if claims.get("role") != "owner":
        raise AppError(403, "forbidden", "Owner role required.")
    return claims
