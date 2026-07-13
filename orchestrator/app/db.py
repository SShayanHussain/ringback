"""psycopg connection helper. Encodes the Supabase/free-stack rules from the PLAYBOOK:

- Non-local hosts get SSL (§2 / §12.1). psycopg respects sslmode in the URL; we also set it defensively.
- App runtime uses the TRANSACTION pooler (:6543) with prepared statements OFF
  (conn.prepare_threshold = None) — §12.1. Migrations use the SESSION/direct URL (:5432).
"""
from __future__ import annotations

import contextlib

from .config import get_settings

_LOCAL_HOSTS = ("localhost", "127.0.0.1", "postgres", "db")


def _is_local(url: str) -> bool:
    return any(f"@{h}" in url or f"@{h}:" in url for h in _LOCAL_HOSTS)


@contextlib.contextmanager
def connection():
    import psycopg  # lazy import so the module loads without psycopg in pure-unit tests

    url = get_settings().database_url
    kwargs = {}
    if not _is_local(url) and "sslmode=" not in url:
        kwargs["sslmode"] = "require"
    conn = psycopg.connect(url, autocommit=True, **kwargs)
    # Transaction pooler (pgbouncer) forbids server-side prepared statements.
    conn.prepare_threshold = None
    try:
        yield conn
    finally:
        conn.close()
