"""Dependency-free auth: HS256 JWT (access + refresh) and PBKDF2 password hashing (stdlib only)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

_PBKDF2_ROUNDS = 200_000


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ---- JWT (HS256) ----

def sign_jwt(claims: dict, secret: str, ttl_seconds: int) -> str:
    now = int(time.time())
    payload = {**claims, "iat": now, "exp": now + ttl_seconds}
    header = {"alg": "HS256", "typ": "JWT"}
    segs = [_b64e(json.dumps(header, separators=(",", ":")).encode()),
            _b64e(json.dumps(payload, separators=(",", ":")).encode())]
    signing_input = ".".join(segs).encode()
    sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    return ".".join(segs + [_b64e(sig)])


def verify_jwt(token: str, secret: str) -> dict | None:
    try:
        h, p, s = token.split(".")
        signing_input = f"{h}.{p}".encode()
        expected = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(s)):
            return None
        payload = json.loads(_b64d(p))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        return payload
    except Exception:  # noqa: BLE001
        return None


# ---- Passwords (PBKDF2-HMAC-SHA256) ----

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return f"pbkdf2${_b64e(salt)}${_b64e(dk)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_b64, dk_b64 = stored.split("$")
        if scheme != "pbkdf2":
            return False
        salt = _b64d(salt_b64)
        expected = _b64d(dk_b64)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
        return hmac.compare_digest(dk, expected)
    except Exception:  # noqa: BLE001
        return False
