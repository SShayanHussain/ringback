"""Auth: signup / login / refresh / me. JWT access + refresh (PRD §0b).

The web layer stores these tokens in its own httpOnly cookies (Server Actions), which avoids
cross-site cookie pain between the Vercel web domain and the Render API domain.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..config import get_settings
from ..deps import get_claims
from ..errors import AppError, ok
from ..repo import get_repo
from ..security import hash_password, sign_jwt, verify_jwt, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupIn(BaseModel):
    email: str
    password: str
    workspace_name: str | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


def _pub(user: dict) -> dict:
    return {"id": user["id"], "email": user["email"],
            "workspace_id": user["workspace_id"], "role": user["role"]}


def _issue(user: dict) -> dict:
    s = get_settings()
    access = sign_jwt(
        {"sub": user["id"], "workspace_id": user["workspace_id"],
         "role": user["role"], "email": user["email"]},
        s.jwt_access_secret, s.jwt_access_ttl,
    )
    refresh = sign_jwt(
        {"sub": user["id"], "workspace_id": user["workspace_id"]},
        s.jwt_refresh_secret, s.jwt_refresh_ttl,
    )
    return {"access_token": access, "refresh_token": refresh, "user": _pub(user)}


@router.post("/signup")
def signup(body: SignupIn):
    if len(body.password) < 8:
        raise AppError(422, "weak_password", "Password must be at least 8 characters.")
    repo = get_repo()
    if repo.get_user_by_email(body.email):
        raise AppError(409, "email_taken", "That email is already registered.")
    wid = repo.create_workspace(body.workspace_name or f"{body.email.split('@')[0]}'s workspace")
    user = repo.create_user(wid, body.email, hash_password(body.password), "owner")
    return ok(_issue(user))


@router.post("/login")
def login(body: LoginIn):
    user = get_repo().get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise AppError(401, "bad_credentials", "Invalid email or password.")
    return ok(_issue(user))


@router.post("/refresh")
def refresh(body: RefreshIn):
    claims = verify_jwt(body.refresh_token, get_settings().jwt_refresh_secret)
    if not claims:
        raise AppError(401, "invalid_refresh", "Refresh token is invalid or expired.")
    user = get_repo().get_user(claims["sub"])
    if not user:
        raise AppError(401, "invalid_refresh", "User no longer exists.")
    return ok(_issue(user))


@router.get("/me")
def me(claims: dict = Depends(get_claims)):
    return ok({"user": {"id": claims["sub"], "email": claims.get("email"),
                        "workspace_id": claims["workspace_id"], "role": claims.get("role")}})
