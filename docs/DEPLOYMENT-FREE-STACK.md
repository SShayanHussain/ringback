# Deployment — the fully-free stack (no AWS)

Drop-in replacement for the AWS design (PLAYBOOK §12.9). Every service has a free tier.

| Need | Service | Notes |
|---|---|---|
| Web (Next.js) | **Vercel** | Git integration deploy; set `ORCHESTRATOR_URL`, `NEXT_PUBLIC_APP_URL`. |
| Agent core (FastAPI) | **Render** free web service | `uvicorn ringback_agent.service:app`. Keep warm (below). |
| Orchestrator (FastAPI) | **Render** free web service | `uvicorn app.main:app`. Keep warm. |
| Postgres | **Supabase** | Transaction pooler `:6543` at runtime; session `:5432` for migrations. |
| Redis (optional) | **Upstash** | No-op if `REDIS_URL` unset. |
| LLM | **Groq** (+ Gemini) | `LLM_PROVIDER` switch. Text core runs key-free (rulebased). |
| CI/CD | **GitHub Actions** → platform git integrations | No SSH. |

> Free Render = ~750 instance-hours/month total. Two always-on free services ≈ 1460 hrs → over budget.
> For a demo, keep the **orchestrator** always-on and let **agent-core** cold-start, or upgrade one.

## 0. Prerequisites
- Push this repo to GitHub. CI (`.github/workflows/ci.yml`) runs lint + tests + the eval gate on every PR.
- The text core needs **no** API key. Voice keys stay unset until Phase 5.

## 1. Supabase (Postgres)
1. Create a project. Grab two connection strings from **Project Settings → Database**:
   - **Transaction pooler** (`...pooler.supabase.com:6543`) → app runtime.
   - **Session/direct** (`...:5432`) → migrations only.
2. Apply the schema on the **session** URL (a mounted init.sql does NOT run on managed PG — PLAYBOOK §2):
   ```bash
   psql "postgresql://postgres:...@db.<ref>.supabase.co:5432/postgres" -f db/schema.sql
   ```
3. Runtime `DATABASE_URL` = the **:6543** pooler string. The orchestrator sets
   `conn.prepare_threshold = None` and `sslmode=require` for non-local hosts automatically
   (`orchestrator/app/db.py`). Migrations use `DATABASE_MIGRATE_URL` = the **:5432** string.

## 2. Render — agent core
- New Web Service → root `agent/` → it builds the Dockerfile.
- Env: `VERTICAL=home-services`, `LLM_PROVIDER=groq`, `GROQ_API_KEY=gsk_...` (or leave `rulebased`).
- Health check path: `/health` (answers GET **and** HEAD).

## 3. Render — orchestrator
- New Web Service → root `orchestrator/`.
- Env: `DATABASE_URL` (:6543 pooler), `AGENT_CORE_URL` (the agent-core Render URL),
  `JWT_ACCESS_SECRET`, `JWT_REFRESH_SECRET`, `CREDENTIALS_ENC_KEY` (32-byte hex),
  `APP_URL` (the Vercel URL, for CORS), `N8N_WEBHOOK_URL` + `N8N_WEBHOOK_SECRET` (once built).
- Health check path: `/health`.

## 4. Vercel — web
- Import the repo, set **root directory = `web`** (monorepo). Build `npm run build`, output standalone.
- Env: `ORCHESTRATOR_URL` (the orchestrator Render URL), `NEXT_PUBLIC_APP_URL` (the Vercel URL),
  `NODE_ENV=production`.

## 5. Keep free services warm (PLAYBOOK §12.6)
Render free services spin down after ~15 min idle. Point **UptimeRobot** at each `/health` every
5 min. `/health` is DB/LLM-free and answers HEAD, so pinging is free and won't 405.

## 6. Env var hygiene (PLAYBOOK §12.5)
Name by **role**. `LLM_API_KEY` = Gemini (`AIza…`); `GROQ_API_KEY` = Groq (`gsk_…`). A swapped key
reads as `400 API key not valid`. Verify a Gemini key before deploy:
`curl "https://generativelanguage.googleapis.com/v1beta/models?key=<KEY>"`.

## 7. Spend caps — REQUIRED before any voice deploy
Voice is not deployed until:
- Text eval gate green: `cd agent && python -m evals.run --ci`.
- `TELEPHONY_MONTHLY_MINUTE_CAP` + `TELEPHONY_SPEND_ALARM_USD` enforced, with an alarm at the
  telephony provider (Twilio/Telnyx usage triggers) **and** a billing alarm.
- Provider spend limits set in the Twilio/Telnyx console (hard cap, not just an alert).

## 8. Prod gotchas already handled in code
- **Supabase pooler exhaustion** (§12.1): `:6543` + prepared statements off.
- **API errors are JSON** (§12.4): `{error:{code,message}}`, never a plain-text 500.
- **`/health` GET+HEAD** (§12.6).
- **No forked worker** (§12.7): agent core is in-process → no gRPC-in-fork deadlock class.
- **Next standalone build** needs placeholder envs (handled in `web/Dockerfile` + CI).

## 9. Rollback
Vercel and Render both keep previous deploys — roll back in their dashboards. Migrations are
idempotent (`IF NOT EXISTS`); never hand-edit the DB (PLAYBOOK §4).
