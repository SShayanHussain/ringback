"""At-rest encryption for integration credentials (hard rule: PII/creds encrypted at rest).

Uses Fernet (AES-128-CBC + HMAC) keyed from CREDENTIALS_ENC_KEY. Imported lazily so the rest of the
service runs in unit tests without the cryptography wheel. Refuses to "pretend-encrypt": if the key
is missing it raises, rather than storing plaintext (PLAYBOOK Golden Rule 1).
"""
from __future__ import annotations

import base64
import hashlib

from .config import get_settings


def _fernet():
    from cryptography.fernet import Fernet

    key_material = get_settings().credentials_enc_key
    if not key_material:
        raise RuntimeError("CREDENTIALS_ENC_KEY is not set — cannot encrypt integration credentials.")
    try:
        raw = bytes.fromhex(key_material)
    except ValueError:
        raw = hashlib.sha256(key_material.encode()).digest()
    fkey = base64.urlsafe_b64encode(raw[:32].ljust(32, b"0"))
    return Fernet(fkey)


def encrypt(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
