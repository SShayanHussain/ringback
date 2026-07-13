"""Data access. EVERY tenant-scoped read/write takes a workspace_id and filters by it (PLAYBOOK §4).

Two backends: PgRepo (Postgres/Supabase) and InMemoryRepo (dev/tests, ephemeral, loudly flagged).
The tenant-isolation test exercises the same scoping contract both backends implement.
"""
from __future__ import annotations

import json
import uuid
from typing import Protocol

from .config import get_settings
from .db import connection


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class Repo(Protocol):
    def create_workspace(self, name: str) -> str: ...
    def create_user(self, workspace_id: str, email: str, password_hash: str, role: str) -> dict: ...
    def get_user_by_email(self, email: str) -> dict | None: ...
    def get_user(self, user_id: str) -> dict | None: ...
    def insert_call(self, workspace_id: str, call: dict) -> str: ...
    def list_calls(self, workspace_id: str, limit: int = 100) -> list[dict]: ...
    def get_call(self, workspace_id: str, call_id: str) -> dict | None: ...
    def get_config(self, workspace_id: str) -> dict: ...
    def set_config(self, workspace_id: str, config: dict) -> None: ...
    def save_integration(self, workspace_id: str, provider: str, enc_blob: str) -> None: ...
    def list_integrations(self, workspace_id: str) -> list[dict]: ...


class InMemoryRepo:
    def __init__(self):
        self.workspaces: dict[str, dict] = {}
        self.users: dict[str, dict] = {}
        self.calls: dict[str, dict] = {}
        self.configs: dict[str, dict] = {}
        self.integrations: list[dict] = []

    def create_workspace(self, name: str) -> str:
        wid = _uid("ws")
        self.workspaces[wid] = {"id": wid, "name": name}
        return wid

    def create_user(self, workspace_id, email, password_hash, role) -> dict:
        uid = _uid("usr")
        user = {"id": uid, "workspace_id": workspace_id, "email": email.lower(),
                "password_hash": password_hash, "role": role}
        self.users[uid] = user
        return user

    def get_user_by_email(self, email) -> dict | None:
        return next((u for u in self.users.values() if u["email"] == email.lower()), None)

    def get_user(self, user_id) -> dict | None:
        return self.users.get(user_id)

    def insert_call(self, workspace_id, call) -> str:
        cid = _uid("call")
        self.calls[cid] = {"id": cid, "workspace_id": workspace_id, **call}
        return cid

    def list_calls(self, workspace_id, limit=100) -> list[dict]:
        rows = [c for c in self.calls.values() if c["workspace_id"] == workspace_id]
        return rows[-limit:][::-1]

    def get_call(self, workspace_id, call_id) -> dict | None:
        c = self.calls.get(call_id)
        return c if c and c["workspace_id"] == workspace_id else None  # tenant scope

    def get_config(self, workspace_id) -> dict:
        return self.configs.get(workspace_id, {})

    def set_config(self, workspace_id, config) -> None:
        self.configs[workspace_id] = config

    def save_integration(self, workspace_id, provider, enc_blob) -> None:
        self.integrations = [i for i in self.integrations
                             if not (i["workspace_id"] == workspace_id and i["provider"] == provider)]
        self.integrations.append({"workspace_id": workspace_id, "provider": provider, "enc_blob": enc_blob})

    def list_integrations(self, workspace_id) -> list[dict]:
        return [{"provider": i["provider"], "connected": True}
                for i in self.integrations if i["workspace_id"] == workspace_id]


class PgRepo:
    def create_workspace(self, name: str) -> str:
        wid = _uid("ws")
        with connection() as c:
            c.execute("INSERT INTO workspaces (id, name) VALUES (%s, %s)", (wid, name))
        return wid

    def create_user(self, workspace_id, email, password_hash, role) -> dict:
        uid = _uid("usr")
        with connection() as c:
            c.execute(
                "INSERT INTO users (id, workspace_id, email, password_hash, role) VALUES (%s,%s,%s,%s,%s)",
                (uid, workspace_id, email.lower(), password_hash, role),
            )
        return {"id": uid, "workspace_id": workspace_id, "email": email.lower(),
                "password_hash": password_hash, "role": role}

    def get_user_by_email(self, email) -> dict | None:
        with connection() as c:
            row = c.execute(
                "SELECT id, workspace_id, email, password_hash, role FROM users WHERE email=%s",
                (email.lower(),),
            ).fetchone()
        return _user_row(row)

    def get_user(self, user_id) -> dict | None:
        with connection() as c:
            row = c.execute(
                "SELECT id, workspace_id, email, password_hash, role FROM users WHERE id=%s",
                (user_id,),
            ).fetchone()
        return _user_row(row)

    def insert_call(self, workspace_id, call) -> str:
        cid = _uid("call")
        with connection() as c:
            c.execute(
                "INSERT INTO calls (id, workspace_id, channel, intent, outcome, escalated, payload) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (cid, workspace_id, call.get("channel", "text"), call.get("intent"),
                 call.get("outcome"), call.get("escalated", False), json.dumps(call)),
            )
        return cid

    def list_calls(self, workspace_id, limit=100) -> list[dict]:
        with connection() as c:
            rows = c.execute(
                "SELECT payload FROM calls WHERE workspace_id=%s ORDER BY created_at DESC LIMIT %s",
                (workspace_id, limit),
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

    def get_call(self, workspace_id, call_id) -> dict | None:
        with connection() as c:
            row = c.execute(
                "SELECT payload FROM calls WHERE id=%s AND workspace_id=%s",  # tenant scope
                (call_id, workspace_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def get_config(self, workspace_id) -> dict:
        with connection() as c:
            row = c.execute("SELECT data FROM configs WHERE workspace_id=%s", (workspace_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def set_config(self, workspace_id, config) -> None:
        with connection() as c:
            c.execute(
                "INSERT INTO configs (workspace_id, data) VALUES (%s,%s) "
                "ON CONFLICT (workspace_id) DO UPDATE SET data=EXCLUDED.data, updated_at=now()",
                (workspace_id, json.dumps(config)),
            )

    def save_integration(self, workspace_id, provider, enc_blob) -> None:
        with connection() as c:
            c.execute(
                "INSERT INTO integrations (workspace_id, provider, enc_blob) VALUES (%s,%s,%s) "
                "ON CONFLICT (workspace_id, provider) DO UPDATE SET enc_blob=EXCLUDED.enc_blob",
                (workspace_id, provider, enc_blob),
            )

    def list_integrations(self, workspace_id) -> list[dict]:
        with connection() as c:
            rows = c.execute(
                "SELECT provider FROM integrations WHERE workspace_id=%s", (workspace_id,)
            ).fetchall()
        return [{"provider": r[0], "connected": True} for r in rows]


def _user_row(row) -> dict | None:
    if not row:
        return None
    return {"id": row[0], "workspace_id": row[1], "email": row[2], "password_hash": row[3], "role": row[4]}


_repo: Repo | None = None


def get_repo() -> Repo:
    global _repo
    if _repo is None:
        _repo = PgRepo() if get_settings().db_enabled else InMemoryRepo()
    return _repo


def reset_repo_for_tests(repo: Repo) -> None:
    global _repo
    _repo = repo
