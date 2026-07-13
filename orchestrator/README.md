# orchestrator/ — Ringback API

FastAPI. Auth (JWT access+refresh), strict tenant scoping, call logging, the text playground proxy,
and the n8n automation seam. Talks to the agent core over `AGENT_CORE_URL/chat`.

## Run

```bash
pip install -e .
pytest -q                                  # health · auth · tenant isolation
uvicorn app.main:app --port 8000           # needs agent-core on AGENT_CORE_URL for /playground
```

Without `DATABASE_URL` it runs on **ephemeral in-memory storage** (dev/test) and logs a loud warning.
Set `DATABASE_URL` (Supabase transaction pooler `:6543` at runtime) for real persistence.

## Routes

| Route | Purpose |
|---|---|
| `GET/HEAD /health` | Uptime-pinger friendly; no DB/LLM. |
| `POST /auth/{signup,login,refresh}` · `GET /auth/me` | JWT access + refresh. |
| `POST /playground/chat` | Proxies the agent core; persists call log; fires n8n events. |
| `GET /calls` · `GET /calls/{id}` | Tenant-scoped call log. |
| `GET/PUT /config` | Vertical defaults (from agent core) + tenant overrides. |
| `GET/POST /integrations` | Calendar/CRM creds, **encrypted at rest** (Fernet). |

Responses: `{ "data": ... }` on success, `{ "error": { "code", "message" } }` on failure.
