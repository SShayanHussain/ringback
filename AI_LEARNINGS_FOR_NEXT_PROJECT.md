# AI Context & Memory for Next Project

> **Agent Instructions:** 
> Read this file before initializing, planning, or writing deployment, CI/CD, AWS, database, or AI code in this new project. This document contains critical lessons learned through extensive trial and error on the previous MVP to ensure smooth development and deployment. 
> Follow these practices strictly to prevent repeating past mistakes.

---

## 1. AWS & RDS (Database) Deployments
- **RDS requires SSL/TLS by default:** Do NOT forget to configure SSL for database connections in production. The Node.js `postgres` driver does not enable SSL by default (unlike Python). 
  - **Rule:** Conditionally set `ssl: { rejectUnauthorized: false }` for any connection outside of `localhost`/`127.0.0.1`.
- **Database Extensions (`pgvector`):** `db/init.sql` mounted in Docker does NOT run against AWS RDS. Extensions like `pgvector` must be created explicitly via a migration script or a manual `rds-setup.sql` script that runs against the production RDS instance.
- **Migrating Production Data:** The lean Next.js standalone Docker image lacks migration tools. 
  - **Rule:** Create a dedicated `Dockerfile.migrate` (a one-shot migrator container). This container must be run in the CI/CD pipeline on the EC2 host *before* starting the main app containers (`docker compose run --rm migrate`). 
  - If the database was ever manually modified, migrations must "baseline" existing tables to prevent recreating them and crashing deployments.

## 2. CI/CD Pipeline Practices
- **Deployment Safety (`set -e`):** In the deployment script, ALWAYS use `set -e` so that if the database migration fails, the deployment aborts *before* restarting the app. The production environment should remain on the old stable version.
- **Handling Secrets on EC2:** When passing secrets to an EC2 instance via SSH actions (like `appleboy/ssh-action`), `export VAR=...` often gets dropped. 
  - **Rule:** Write a literal `.env` file on the server. Escape `$` signs as `$$` to prevent Docker Compose from incorrectly interpolating passwords or tokens.
  - Example: `echo "DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/\$/$$/g')" > .env`
- **SSH Timeouts:** Heavy Docker image pulls will kill the default SSH action timeout (which is typically ~30s). 
  - **Rule:** Set `timeout: 30m` and `command_timeout: 30m` for SSH deployment actions.
- **Docker Profiles:** If the migrator container is behind a `profile: ["migrate"]`, you MUST explicitly pull it (`docker compose --profile migrate pull`), otherwise the server will reuse a stale local image forever.
- **Image Tagging:** Tag Docker images with both `:latest` and the `GITHUB_SHA`. `:latest` alone makes rollbacks impossible.

## 3. Code, Framework, & Multi-Tenancy Rules
- **Multi-Tenancy is Strict:** Every tenant-data table MUST carry a `tenant_id` (or `workspace_id`). Every single database query, cache key, and rate limit MUST be scoped by this ID.
- **Fail Loudly (No Mock Data):** If an external resource (like an S3 bucket or an API) fails, the system MUST throw an error or mark the job as failed. NEVER fabricate mock data, fallback text, or fake success states (e.g., dummy embeddings or confidence scores). Fake data silently poisons the database and destroys retrieval accuracy.
- **Strict Environment Validation:** Use a library like `zod` to validate all environment variables at startup. Let the app crash immediately with a clear missing-variable message rather than causing undefined behavior downstream.
- **React Server vs Client Components:** Passing `onClick` or other interactive handlers from a Server Component to a Client Component in Next.js will crash in production. Extract interactive elements into small `"use client"` wrapper components.
- **HTTPS & Secure Contexts:** Browser APIs like `navigator.clipboard` will silently fail over plain HTTP. Serve the application over HTTPS from day one (using Let's Encrypt/nginx or an AWS ALB).

## 4. Debugging & AI System Practices
- **Always Check Logs First:** If the app throws a 500 error, the root cause is almost always in the upstream service (e.g., the AI worker or the FastAPI service). Do not theorize; check the logs: `docker compose logs <service> --tail 60`.
- **Cache Invalidation:** If using a semantic cache (like Redis), it MUST be invalidated whenever the underlying data changes (e.g., during re-ingestion of documents). Stale caches cause "ghost bugs" where fixes appear to not work.
- **Model Dependencies:** Treat LLM/Embedding model APIs as ephemeral. Do not hardcode model IDs (e.g., `text-embedding-004`). Pass them via environment variables so model deprecations can be handled via config changes rather than code deployments.
- **Grounding Gate:** Never emit an ungrounded AI answer. Use a confidence threshold and an LLM judge. If the check fails, abstain and escalate to a human. Ensure this gate is explicitly invoked in the core `/chat` endpoint.

---
*Created automatically to preserve institutional knowledge from the Deflekt MVP.*

## 5. Flowlet AI Execution Learnings
- **Strict JSON Schema Enforcement (`ajv`):** When building AI output nodes that upstream logic branches on, a vague instruction is not enough. You must pass a strict JSON Schema to the LLM and validate the output structurally. Otherwise, unpredictable formats will break subsequent routing logic.
- **Exact Prompt Hashing (Semantic Caching):** For identical inputs flowing through an AI step, hash the complete expanded prompt and use it as a Redis cache key to avoid duplicate LLM calls, effectively reducing redundant token costs by 100%.
- **Isolated AI Execution Pools:** AI steps are inherently slow (often multi-second TTFT). If they run in the same worker pool as fast HTTP/Transform steps, they will cause head-of-line blocking. Dedicate a separate BullMQ queue/worker pool strictly for LLM processing to maintain overall system throughput.

## 6. Consensus Multi-Agent Systems & MCP Tool Learnings
- **Avoid Shell Tools for Bracketed File Path Manipulation:** Operating system shells (particularly Windows PowerShell) interpolate directories with square brackets `[workspaceId]` as wildcard vectors. Rather than using raw terminal execution scripts (like `mkdir` or `cp`) inside automated build or deploy pipelines, use language-native APIs (such as Python's `os.makedirs` or Node's `fs.mkdirSync`) which bypass the shell's regex parser entirely.
- **FastMCP SSE-based Server Integrations:** FastMCP's helper wrappers (like `create_fastapi_app`) are prone to versioning discrepancies and can throw `AttributeError` runtime exceptions. Instead, bind the MCP SSE application (`FastMCP.sse_app()`) to Starlette routes manually, providing clean endpoints for both tool calling and hosting ping tests.
- **Supabase IPv6 Gateway Resolution Blocks:** Direct database connections to Supabase will fail silently or throw `getaddrinfo ENOTFOUND` when triggered from IPv4-only cloud platforms (like Vercel serverless environments or Render web instances).
  - **Rule:** Mandate the use of the Supabase Transaction Pooler URL (`.pooler.supabase.com` on port `6543`) for all cloud environments.
- **Redis Gateway Startup Resiliency:** Gateways should not throw crash loops when Redis connections are offline in local development. Introduce fallback validation blocks verifying `REDIS_URL` at runtime, logging explicit warnings instead of failing with obscure errors.
- **LangGraph Checkpoint Serialization Safety:** Complex agent graphs store extensive message histories in their state. Heavy state serialization (checkpoints) to Postgres can cause thread blocking. In production, serialize only IDs or refs to heavy documents and keep raw text contents out of the state dictionary.

### 6a. The "stuck run" class — background workers + LLM SDKs (debugged the hard way in prod)
These four bugs all presented identically ("runs never finish") but at different layers. The deploy was Render free tier (one instance running gateway + MCP + an **RQ** worker) + Supabase Postgres + Gemini via LangGraph. Order of appearance:

- **gRPC LLM clients DEADLOCK inside a forked worker → run hangs forever at `running`.** RQ (and Celery with the fork/prefork model) run each job in a **forked** work-horse. `langchain-google-genai` (and other Google SDKs) default to a **gRPC** transport whose background threads/channels do not survive `fork()`, so the first `.ainvoke()` blocks forever — no error, no timeout, no log line after "calling LLM".
  - **Rule:** In any forked worker, force the LLM SDK onto HTTP: `ChatGoogleGenerativeAI(..., transport="rest", timeout=60, max_retries=2)`. This was THE fix that made runs complete. (Alternative: use a non-forking worker, e.g. RQ `SimpleWorker` / `--worker-class`, but REST is simpler and lighter.)
- **Unpinned observability deps silently jump a major version and crash the worker at *import* → runs stuck at `queued`.** `langfuse>=2.0.0` resolved to **v3** on a fresh build; v3 removed `langfuse.callback.CallbackHandler` and changed its constructor. The module-level import blew up when the RQ work-horse imported the job module, so the job died *before* the code set status to `running` — leaving the row at `queued` forever with the failure hidden in the worker log, not the DB.
  - **Rule:** Pin observability/tracing SDKs to a major (`langfuse>=2,<3`). **Tracing must never be able to fail a run** — build callbacks in a `try/except` that returns `[]` on any import/init error, and only enable it when real keys are present.
- **Constructing heavy clients at module top-level turns a missing env var into a silent stuck-`queued`.** `llm = ChatGoogleGenerativeAI(...)` and the Langfuse handler were created at import time; a missing `GOOGLE_API_KEY` (or a broken SDK) crashed the worker as it imported the job, so the row never left `queued` and no error was recorded on it.
  - **Rule:** Construct LLM/tracing/DB clients **lazily** (inside the node/function, e.g. a `get_llm()` singleton). Then the failure happens *inside* the run and is recorded as a `failed` row with a visible `error_message` — diagnosable instead of invisible.
- **Forked workers don't inherit the CWD on `sys.path`.** The `rq worker` console script does not add the project dir to `sys.path`, so `q.enqueue("app.worker.run_agent")` failed to import `app` in the work-horse. **Rule:** set `PYTHONPATH=.` (or `ENV PYTHONPATH=/app`) wherever the worker is launched.

### 6b. Make stuck states impossible to hide (observability rules that paid off)
- **Bound every external `await` with a timeout.** A run row can only get stuck at `running` if an `await` never returns or the process is killed. Wrap LLM calls and checkpoint setup in `asyncio.wait_for(...)`, and on `TimeoutError` raise a *descriptive* `RuntimeError` (note: `str(asyncio.TimeoutError())` is `""` — an empty `error_message` — so always re-raise with your own message).
- **Emit flushed stage markers around every external boundary.** Adding `print("... setting up checkpointer / invoking graph / calling LLM", flush=True)` turned an opaque hang into a one-glance diagnosis of *which* boundary blocked. Do this from day one in any multi-step worker; use `flush=True` because forked stdout is buffered.
- **A "queued forever" vs "running forever" symptom already localizes the bug:** stuck at `queued` ⇒ worker crashed *before* claiming the job (import error, bad PYTHONPATH, dep version); stuck at `running` ⇒ blocked *inside* the job (hung `await`) or the process was killed (OOM — check for `Work-horse terminated ... signal 9`).

### 6c. LangGraph HITL interrupts do NOT raise out of `.ainvoke()`
- **Symptom:** approvals were never created and runs were marked `completed` even though the graph paused at a human-approval `interrupt()`.
- **Cause:** in current LangGraph, `interrupt()` does **not** propagate `GraphInterrupt` out of `graph.ainvoke()` — the call **returns** with the interrupt recorded in the checkpoint. `except GraphInterrupt:` never fires.
- **Rule:** detect the pause by inspecting state after invoke — `snapshot = await graph.aget_state(config); if snapshot.next: <paused/awaiting-approval> else: <done>`. Keep the `except GraphInterrupt` only as a version-compat fallback.

### 6d. Supabase pooler ↔ async checkpointer caveat
- Existing rule (use the Supabase pooler on cloud/IPv4 hosts) still holds for the **sync** driver. But LangGraph's **`AsyncPostgresSaver` (async psycopg3) uses prepared statements**, which the **transaction** pooler (port `6543`) breaks. If checkpoint writes hang or throw `prepared statement "..." already exists`, use the **session** pooler (port `5432`) for the async checkpointer, or disable prepared statements. (In this deploy the sync psycopg2 writes — the `queued→running` update — worked, which is exactly why the failure looked like it was "past" the DB and in the LLM.)

---

## 7. Clause (Vertical RAG on the FULLY-FREE stack) — going-live learnings
> Stack: Vercel + Render(free) + Supabase + Upstash + Langfuse + **Gemini (embeddings) & Groq (generation)** + GitHub Actions. No paid AWS. The bugs below all showed up only when deploying for real.

- **Supabase pooler on serverless is the #1 blocker.** Serverless web (Vercel) MUST use the **TRANSACTION pooler (`:6543`)**, not the session pooler (`:5432`): session mode caps at ~15 clients and Vercel exhausts it → `EMAXCONNSESSION max clients reached in session mode` (surfaces as Next's opaque *"error in the Server Components render"*). The transaction pooler (pgbouncer) forbids prepared statements, so pair it with **postgres.js `{ max: 1, prepare: false, idle_timeout: 20 }`** and **psycopg `conn.prepare_threshold = None`** — moving to `:6543` without disabling prepared statements throws `prepared statement already exists`. Run **migrations** on the session/direct URL (`:5432`).
  - **Rule:** `:6543` = app runtime (prepared statements OFF); `:5432` = migrations + async checkpointer.
- **Free LLM tiers can't sustain an agentic (multi-call) flow.** One CRAG question = 5–10 LLM calls, so a 5-req/min free quota `429`s on a *single* question. Mitigate (all free): **split models** across `LLM_MODEL_ANSWER`/`LLM_MODEL_CHEAP` (per-model RPM budgets); prefer higher-RPM free models (`gemini-2.0-flash-lite` ~30 rpm); add a **min-interval throttle** (`LLM_MIN_INTERVAL_MS`); and make the provider an **env switch** — **Groq** free tier (~30 rpm + 14,400/day, OpenAI-compatible) is far more generous. Keep embeddings on Gemini. Build a provider-agnostic `generate` / `generate_json` seam (strict JSON via Gemini `responseSchema` OR OpenAI JSON mode + your own required-key validation) from day one.
- **A `@contextmanager` must `yield` exactly once.** A `yield` inside its `except` turns a body exception into `generator didn't stop after throw()`, MASKING the real error (our rate limit vanished behind it). Guard setup BEFORE the yield; run the body under a bare `try/finally`. Wrappers (tracing/metrics) must be exception-transparent.
- **API errors must be JSON; clients must parse defensively.** A thrown handler returns FastAPI's plain-text `Internal Server Error`, so the client's `res.json()` crashes with `Unexpected token 'I'`, hiding the cause. **Rule:** catch at the API boundary and return `{error:{message}}` with a real status (429 for rate limits, 502 otherwise); on the client `res.text()` then a guarded `JSON.parse`.
- **Name env vars by ROLE; mind multi-provider key slots.** `AWS_*` for Supabase Storage (S3-compatible) confused everyone → use `STORAGE_*`. With two LLM providers, `LLM_API_KEY` = Gemini (`AIza…`, embeddings ALWAYS) and `GROQ_API_KEY` = Groq (`gsk_…`, generation); a swapped key reads as `400 API key not valid`. Verify a Gemini key first: `curl ".../v1beta/models?key=<KEY>"`.
- **`/health` must answer GET *and* HEAD** — `@app.api_route("/health", methods=["GET","HEAD"])` (`@app.get` returns 405 on HEAD, which uptime monitors send). Keep it DB/LLM-free. Point an uptime monitor at `/health` every 5 min to keep a free Render service past the ~15-min idle spin-down.
- **Free-tier packing:** Render free = one web service, no worker → **fold ingestion into the API as an in-process background task** (return 200 fast; also avoids the gRPC-in-fork deadlock since there's no fork).
- **DX:** auto-load a repo-root `.env` (guarded `load_dotenv()` at the TOP of config — before the frozen settings dataclass, whose field defaults read `os.getenv` at import; plus `config({path:"../.env"})` in `drizzle.config.ts`); the root lockfile is authoritative in npm workspaces (CI installs at root, then `--workspace`); authed mutations via **Server Actions** (server-side session), reads via Server Components; **generate + commit** Drizzle migrations and apply them on the `:5432` URL.

