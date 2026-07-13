# PLAYBOOK.md — Production Deployment & Engineering Playbook

> **What this is:** Every hard-won lesson from building and deploying Deflekt (Next.js + FastAPI +
> Postgres/pgvector + Redis + Docker + GitHub Actions + EC2 + RDS + GHCR), distilled so the next
> project skips the trial-and-error.
>
> **How to use in a new project:** Copy this file into the new repo root. Then add this line near
> the top of `CLAUDE.md` (Claude Code) and `GEMINI.md` (Antigravity):
> `Read PLAYBOOK.md before writing any deployment, CI/CD, database, or AI-pipeline code. Its rules are mandatory.`

---

## 1. Golden rules (learned the hard way)

1. **Fail loudly — never fabricate fallback data.** A "mock answer" placeholder written into the
   vector DB when S3 creds were missing silently poisoned retrieval for days. If a pipeline can't
   fetch real input, mark the job `failed` with the error stored on the record. No dummy text, no
   fake success states, no `confidence: 0.9` from a stub.
2. **Read the actual production logs before theorizing.** Every prod bug in this project was
   solved by `docker compose logs <service> --tail 60`. The app-layer error ("500") is almost
   never the root cause — the upstream service's log is.
3. **Safety checks must be wired in, not just written.** The faithfulness/grounding gate existed
   as a function but was never called from the endpoint. After writing any guard, grep for its
   call site.
4. **Environment parity bites hardest at the managed-service boundary.** Everything that "worked
   locally" and broke in prod broke at: RDS (TLS, extensions, migrations), retired model APIs,
   secrets transport, and browser secure-context APIs. Test those boundaries first.
5. **Every fallback path needs an exit alarm.** If code falls back (local storage, dummy key,
   cache), it must log a loud WARNING with the reason, and the fallback result must be
   distinguishable from the real thing.

---

## 2. AWS / RDS lessons (the expensive ones)

### TLS to RDS — the #1 silent killer
- **Symptom:** `no pg_hba.conf entry for host "...", user "...", database "...", no encryption` → 500s on every DB route.
- **Cause:** RDS requires SSL. The Node `postgres` (porsager/postgres.js) driver does **NOT**
  enable SSL by default. Python `psycopg` defaults to `sslmode=prefer`, so the Python service
  works while the Node service fails — confusing as hell.
- **Fix (do this day one):**
  ```ts
  const isLocalDb = /@(localhost|127\.0\.0\.1|db|postgres)[:/]/.test(connectionString);
  const client = postgres(connectionString, isLocalDb ? {} : { ssl: { rejectUnauthorized: false } });
  ```
  (`rejectUnauthorized: false` = encrypted without pinning the RDS CA; fine inside a VPC. Pin the
  CA bundle if traffic leaves the VPC.)

### Postgres extensions don't exist on RDS until you create them
- `db/init.sql` mounted into `/docker-entrypoint-initdb.d/` only runs on a **local container's
  first boot**. RDS never sees it. `CREATE EXTENSION IF NOT EXISTS vector;` must run against RDS
  explicitly — put it in the migration runner (idempotent, warn-don't-fail if unprivileged) and
  keep a manual `db/rds-setup.sql` escape hatch.

### Migrations must be a pipeline step, not a memory
- The lean Next.js standalone runtime image contains **no** drizzle-kit and **no** migration SQL.
  Nothing migrated RDS until we built a dedicated one-shot **migrator image**
  (`Dockerfile.migrate` + programmatic `migrate()` script) run on the EC2 host via
  `docker compose run --rm migrate` **before** `up -d`.
- If the DB was ever migrated by hand, the runner must **baseline** already-applied migrations
  into the tracking table (probe for existing tables/columns) or it will try to re-create tables
  and abort every deploy.
- `set -e` at the top of the deploy script so a failed migration **aborts before** the app
  restarts — prod stays on the old version.
- Docker Compose `pull` **skips profiled services**: if the migrator sits behind
  `profiles: ["migrate"]`, you must `docker compose --profile migrate pull` or `run` will reuse a
  stale local image forever after the first deploy.

### Secrets transport to EC2 (GitHub Actions → SSH)
- `export VAR=...` lines inside `appleboy/ssh-action` scripts get dropped (sudo wrapping /
  non-interactive shells). **Write a literal `.env` file on the server** right before
  `docker compose up`, from the action's `envs:` list.
- **Escape `$` as `$$`** when writing that `.env`: Docker Compose interpolates `$` in env files,
  so a password containing `$` gets truncated → auth failures that look like DB outages.
  ```bash
  echo "DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/\$/$$/g')" > .env
  ```
- Default `appleboy/ssh-action` timeout is ~30s — heavy image pulls die mid-deploy and the script
  silently aborts. Set `timeout: 30m` and `command_timeout: 30m`.

### Misc AWS/Docker
- GHCR image names must be **lowercase**: `${GITHUB_REPOSITORY,,}` in bash, and compute it once.
- No S3? A **shared named volume** (`uploads_data:/app/uploads`) mounted into every container
  that touches files, with a `local://` key prefix, is a fine MVP fallback — but the consumer
  must hard-fail when the file isn't found (see Golden Rule 1).
- Healthchecks on every service + `depends_on: condition: service_healthy` — nginx should depend
  on a *healthy* app, not a started one.
- `docker image prune -af` at the end of each deploy or the EC2 disk fills up.

---

## 3. CI/CD pipeline — the working shape

```
on push/PR:   lint + test (both services) + eval harness (AI gate)
on main only: build & push images to GHCR  →  ssh deploy:
              write .env (escaped) → pull (incl. migrate profile)
              → run migrate (one-shot, set -e) → up -d --remove-orphans → prune
```

Known gaps to fix on the NEXT project from day one (we accepted these for MVP):
- **Tag images with the git SHA** in addition to `:latest` — `:latest`-only means no rollback
  target. Rollback = redeploy previous SHA tag, never rebuild.
- **Staging stage:** auto-deploy `main` → staging stack (same compose, different ports/DB);
  production deploy behind a manual approval (`environment:` with required reviewers, or
  tag-push `v*` trigger). Don't wire `main` → prod directly again.
- **Branch protection** on `main`: PRs only, required status checks, short-lived feature branches
  (trunk-based development).
- **TLS on nginx** (Let's Encrypt/certbot or ALB+ACM) from day one — plain HTTP also breaks
  browser APIs (see §6).

---

## 4. Database & multi-tenancy rules

- Every schema change is a migration file. Never hand-edit the DB — hand-migration is what forced
  the baseline logic in §2.
- Every tenant-data table carries `tenant_id`/`workspace_id`; **every** query, cache key, and
  rate-limit key is tenant-scoped. Keep a test proving cross-tenant retrieval returns nothing.
- Store embeddings as `vector(N)` where **N is pinned in one place** and referenced by both the
  schema and the embedding calls (env: `EMBEDDING_DIM`). A dimension mismatch is a runtime error
  at insert/query time, not build time.
- API responses: `{ data }` on success, `{ error: { code, message } }` on failure. Never leak
  stack traces to clients; log them server-side.

---

## 5. AI / RAG pipeline rules

- **Model retirement is a production outage class.** `text-embedding-004` was retired and every
  chat call 404'd (`models/X is not found for API version v1beta`). Make model IDs env-configurable
  (`EMBEDDING_MODEL`, `LLM_MODEL_CHEAP`) with sane defaults so a retirement is a config change,
  not a code deploy. Current known-good: `gemini-embedding-001` with
  `output_dimensionality=768`, `gemini-2.5-flash` for generation.
- **Query and document embeddings must share model + dimension.** Changing the embedding model
  invalidates every stored vector — plan a re-ingest, don't mix spaces.
- `gemini-embedding-001` on the Gemini API does **not** accept batched `contents` — embed
  one-per-request in the background worker (loop is fine there).
- **Grounding gate:** generate → check confidence threshold → run faithfulness check (LLM judge)
  → escalate on failure. Never emit an ungrounded answer. And verify the gate is actually called
  (Golden Rule 3).
- **Cache invalidation is part of ingestion.** Cached answers (24h TTL) served stale/poisoned
  results long after the underlying bug was fixed — the "it's still broken" ghost. Invalidate the
  tenant's answer cache at the end of every successful ingest. When debugging "no change after
  fix," suspect the cache first and test with a *fresh* query.
- Re-ingest must be **idempotent**: delete the document's old chunks before inserting new ones.
- No-API-key/dummy mode must return `confidence 0.0` (escalate), never a confident fake.

---

## 6. Next.js / React production gotchas

- **Server → Client boundary:** passing `onClick` from a Server Component to a client component
  throws `Event handlers cannot be passed to Client Component props` in production renders.
  Extract interactive bits into small `"use client"` components (a `LogoutButton`-style wrapper).
- **Base UI (`@base-ui/react`):** triggers (`MenuPrimitive.Trigger`, etc.) already render a
  native `<button>`. Wrapping your `<Button>` inside them = nested buttons = invalid HTML and
  flaky clicks. Use the **`render` prop** to merge: `<Trigger render={<Button …>…</Button>} />`.
  (`asChild` is the Radix pattern and **breaks the Base UI build** — don't mix them up.)
- **`navigator.clipboard` requires a secure context** (HTTPS/localhost). Over plain HTTP it
  rejects silently. Ship a `document.execCommand("copy")` fallback + error toast — or better,
  serve HTTPS (§3).
- **Hydration mismatch (React #418)** in prod can be caused by browser extensions injecting DOM
  before hydration — `suppressHydrationWarning` on `<html>`/`<body>` is the accepted fix.
- **Standalone Docker builds need dummy env vars** at build time to pass env validation
  (`zod` schema): set placeholder `DATABASE_URL`, secrets, etc. in the builder stage.
- Runtime image = `.next/standalone` + `.next/static` + `public` only. Anything else you need at
  runtime (migrations!) needs its own image or explicit COPY.
- Env validation with zod at startup (`lib/env.ts`) is worth it — fails fast with a named list of
  missing vars instead of undefined-behavior downstream.

---

## 7. Day-one checklist for the next project

Copy-paste and check off before writing feature code:

- [ ] `PLAYBOOK.md` copied in; referenced from `CLAUDE.md` + `GEMINI.md`
- [ ] `docker-compose.yml` (local: pg+extensions image, redis, services, healthchecks)
- [ ] `docker-compose.prod.yml` with `${VAR}` env passthrough + shared volumes + migrate service behind a profile
- [ ] Node DB client: conditional `ssl: { rejectUnauthorized: false }` for non-local hosts
- [ ] Migrator image + baseline-aware migrate script; deploy runs it before `up -d` with `set -e`
- [ ] `db/rds-setup.sql` manual escape hatch (extensions, cleanups)
- [ ] CI: lint + test + eval gates → build/push (SHA **and** latest tags) → deploy
- [ ] Deploy script: literal `.env` written with `$`→`$$` escaping; 30m SSH timeouts
- [ ] Staging stack + manual prod approval (don't skip this time)
- [ ] TLS on nginx from day one
- [ ] Branch protection on `main`; feature branches + PRs
- [ ] Model IDs + embedding dims in env vars, not hardcoded
- [ ] Tenant isolation test green before the first feature ships
- [ ] `.env.example` kept in sync with what code actually reads (audit it — ours drifted)
- [ ] Billing alarm in CloudWatch

---

## 8. Debugging prod — the 5-minute triage that always worked

```bash
cd ~/deflekt   # or the new project dir on EC2
docker compose -f docker-compose.prod.yml ps                       # anything unhealthy/restarting?
docker compose -f docker-compose.prod.yml logs app --tail 60      # app-layer error + digest
docker compose -f docker-compose.prod.yml logs ai-service --tail 60   # usual root cause
docker compose -f docker-compose.prod.yml logs ai-worker --tail 60    # ingestion failures
docker compose -f docker-compose.prod.yml exec <svc> sh -c 'echo ${KEY:0:4}...'  # secret present?
```
Order of suspicion, based on history: upstream service logs → env/secret transport → TLS/managed
service boundary → retired/renamed model API → stale cache → actual code bug. It was almost never
the code you just wrote.

---

## 9. Flowlet Engine & UI Gotchas

- **Exactly-Once Execution (Webhook Storms):** Simply checking a database before processing a webhook isn't enough under high concurrency. Use 3-layer idempotency: Webhook Token Validation $\rightarrow$ Atomic `pending` $\rightarrow$ `queued` updates $\rightarrow$ Deduplication Ledger.
- **Base UI Click Handlers & Modals:** When using Base UI's `DropdownMenuItem` or similar components with blocking native actions like `window.confirm()`, always use `e.preventDefault()` inside `onClick`. Failing to do so allows the menu to close instantly, unmounting the component and silently swallowing the API request.
- **Decoupled Workers:** Keep the HTTP API ingestion loop $O(1)$ fast. Immediately enqueue tasks to BullMQ (or similar) and return HTTP 200. Let a separate background Node.js worker pool handle DAG traversal and slow external API/LLM calls.
- **Crash-Safe Fairness Leases:** To prevent one heavy tenant from starving a shared BullMQ queue, implement a concurrency limit using Redis leases (e.g. max 5 concurrent jobs per tenant). Crash-safe TTLs are crucial here to avoid deadlocks if a worker dies mid-job.

## 10. Consensus Multi-Agent & LangGraph Gotchas

- **PowerShell Wildcard Globbing in Path Operations:** In Windows PowerShell, square brackets `[]` are treated as wildcard glob matches (e.g., `[workspaceId]` will trigger search filters rather than matching the literal file system name). When creating or copying directories containing brackets, quote the path explicitly or use the direct Node/Python filesystem APIs (which avoid shell interpolation) to prevent silent failures.
- **FastMCP API Versioning and SSE Routing:** FastMCP's helper `create_fastapi_app` is unstable and can crash with `AttributeError` depending on installed versions. Prefer using `.sse_app()` natively with Starlette routing and manually inject FastAPI health routes (`/health`) to keep Render/Vercel host containers active.
- **CORS Configuration Naming Conventions:** Standardize between single origin `CORS_ORIGIN` and multiple origin arrays `CORS_ORIGINS`. Add robust validation at the Gateway layer to handle string splits on commas gracefully when checking allowed origins.
- **Supabase IPv6 Connection Pooler Resolution:** Vercel serverless layers and Render host containers run on IPv4-only configurations. Direct connection strings to newer Supabase instances default to IPv6 and throw fatal `getaddrinfo ENOTFOUND` errors. Always override connection parameters to target the transactional pooler URL (`.pooler.supabase.com` on port `6543`) which fully supports IPv4 fallback routing.
- **Redis Gateway Fail-Safe Bootstrapping:** In mixed local and cloud environments, a Redis cache might be optional or run dynamically. Hard dependencies on `REDIS_URL` without fallback logic will crash Gateway boots. Add runtime guards checking configuration strings to alert developers with a clean warning rather than generic stack-trace crashes.
- **LangGraph Checkpoint Serialization Latency:** When persisting graphs with state size > 1MB (e.g., storing raw PDF inputs or heavy LLM chat history), sync serialization slows down execution dramatically. Configure the checkpointer to write asynchronously or store large payloads separately in S3/Supabase Storage, saving only metadata IDs/refs in the LangGraph state.

---

## 11. Async agent workers — the "stuck run" class (LangGraph + RQ + Gemini on Render/Supabase)

Every one of these presented as "runs never finish" and was solved by reading the worker log,
not the app log (Golden Rule 2). The stack: Render free tier (one instance = gateway + MCP +
`rq worker`), Supabase Postgres, Gemini via LangGraph with a Postgres checkpointer.

### The single most important fix: gRPC LLM clients deadlock in a forked worker
- **Symptom:** run reaches the first LLM call (`researcher calling LLM`) and hangs **forever** at
  status `running` — no error, no timeout, no further log line.
- **Cause:** RQ executes each job in a **forked** work-horse. `langchain-google-genai` (and Google
  SDKs generally) default to a **gRPC** transport whose channels/threads don't survive `fork()`.
  The `await llm.ainvoke()` blocks indefinitely.
- **Fix:** force HTTP transport — `ChatGoogleGenerativeAI(..., transport="rest", timeout=60,
  max_retries=2)`. (Or run a non-forking worker class.) **This is the fix that made runs complete.**
- **Generalize:** any C-extension/gRPC/async client (gRPC, some HTTP/2 libs, connection pools)
  initialized before or across a `fork()` is suspect in RQ/Celery-prefork workers. Prefer REST, or
  create clients lazily *inside* the forked job.

### The "stuck at `queued`" vs "stuck at `running`" triage
The status the run is frozen at tells you which side of "claiming the job" broke:
- **Stuck at `queued`** ⇒ the work-horse died **before** running your code (so nothing set
  `running`). Causes seen: (a) a dependency silently jumped a major version and the module-level
  import threw — `langfuse>=2.0.0` pulled **v3**, which removed `langfuse.callback.CallbackHandler`
  and changed its constructor; (b) `rq worker` couldn't import the `app` package because the console
  script doesn't put CWD on `sys.path`; (c) any other import-time exception in the job module.
- **Stuck at `running`** ⇒ the job started, then a blocked `await` (see gRPC above) or the process
  was **OOM-killed** (free tier is 512 MB running 3–4 processes — look for
  `Work-horse terminated unexpectedly ... signal 9`). The `except` never runs, so the row is frozen.

### Rules to make these impossible to hide (all applied here)
1. **Pin observability/tracing SDKs to a major version** (`langfuse>=2,<3`), and **tracing must never
   fail a run** — build callbacks in `try/except → []`, enabled only when real keys exist. A trace
   backend hiccup should degrade to "no trace", never crash the worker.
2. **Construct LLM / tracing / heavy clients lazily**, not at module top-level. A missing
   `GOOGLE_API_KEY` built at import crashes the worker → silent stuck-`queued`; built lazily inside
   the node it becomes a `failed` row with a real `error_message`.
3. **Bound every external `await` with `asyncio.wait_for(...)`** (LLM calls, checkpoint setup). On
   timeout, **re-raise with your own message** — `str(asyncio.TimeoutError())` is `""`, so a raw
   timeout writes an empty `error_message`. A hang must become a visible `failed`, never `running`.
4. **Flushed stage markers at every boundary** (`print("... invoking graph", flush=True)`). This
   converted an opaque hang into a one-glance diagnosis. `flush=True` matters — forked stdout buffers.
5. **`PYTHONPATH=.`** wherever a bare `rq worker` (or similar) is launched, and `ENV PYTHONPATH=/app`
   in its Dockerfile.

### LangGraph HITL: `interrupt()` does not raise out of `.ainvoke()`
- Human-approval pauses were being lost — approvals never created, runs marked `completed`.
- In current LangGraph, `interrupt()` **returns** from `graph.ainvoke()` with the interrupt recorded
  in the checkpoint; it does **not** raise `GraphInterrupt` to the caller. `except GraphInterrupt`
  never fires.
- **Detect the pause via state:** `snap = await graph.aget_state(config); if snap.next: awaiting_approval
  else: completed`. Keep `except GraphInterrupt` only as a version-compat fallback.

### Supabase pooler ↔ async checkpointer
- The pooler rule (§10) is for the **sync** driver. LangGraph's **`AsyncPostgresSaver`** (async
  psycopg3) uses **prepared statements**, which the Supabase **transaction** pooler (`:6543`) breaks
  (hangs / `prepared statement already exists`). Use the **session** pooler (`:5432`) for the async
  checkpointer, or disable prepared statements. Tell-tale: sync writes (`queued→running`) succeed
  while the async checkpoint path is what's stuck.

### Free-tier packing
- Don't run gateway + MCP + a forked agent worker in one 512 MB instance and expect big LLM/graph
  jobs to survive — OOM kills the work-horse mid-run and freezes the row at `running`. Give the
  worker its own instance (or a bigger one) before load; watch for `signal 9` in logs.

---

## 12. Clause learnings — evals-first vertical RAG on the FULLY-FREE stack

> Stack: Vercel (web) · Render free (FastAPI, **one** web service) · Supabase (Postgres+pgvector+
> Storage) · Upstash Redis · Langfuse Cloud · **Gemini (embeddings) + Groq (generation)** · GitHub
> Actions. No paid AWS. These are the things that bit us specifically when going live for real.

### 12.1 Supabase pooler on serverless — connection exhaustion is the #1 prod blocker
- **Symptom:** login/dashboard/signup 500 with
  `(EMAXCONNSESSION) max clients reached in session mode - max clients are limited to pool_size: 15`.
  Every Server-Component DB read throws; in Next it surfaces as the opaque
  *"An error occurred in the Server Components render."*
- **Cause:** the serverless web tier (Vercel) pointed at the Supabase **SESSION** pooler (`:5432`).
  Session mode holds one server connection per client and caps ~15; Vercel spins up many function
  instances and exhausts it instantly.
- **Fix — runtime URL *and* driver config (both needed):**
  - **App runtime (Vercel web + Render api) → TRANSACTION pooler (`:6543`).** It multiplexes many
    serverless clients onto few server connections.
  - The transaction pooler (pgbouncer transaction mode) does **not** support server-side prepared
    statements, so disable them:
    ```ts
    // postgres.js (web), non-local hosts:
    postgres(url, { ssl: { rejectUnauthorized: false }, max: 1, prepare: false, idle_timeout: 20 })
    ```
    ```python
    # psycopg (api), right after connect:
    conn.prepare_threshold = None
    ```
  - **`max: 1`** on serverless — one connection per instance; the pooler fans out. Moving to `:6543`
    WITHOUT `prepare:false` throws `prepared statement "..." already exists`, so the two go together.
  - **Migrations run against the session/direct URL (`:5432`)** — DDL needs prepared statements.
- **Rule of thumb (reconciles §10 + §6d):** transaction pooler `:6543` = app runtime (prepared
  statements OFF); session/direct `:5432` = migrations + LangGraph async checkpointer.

### 12.2 Free LLM tiers can't sustain an agentic (multi-call) flow — design for it
- **Symptom:** one question returns `429 RESOURCE_EXHAUSTED ... limit: 5, model: gemini-2.5-flash`.
  A CRAG turn makes 5–10 LLM calls (classify → grade → decompose → generate → self-critic), so a
  *single* question blows a 5-req/min free quota.
- **Fixes, cheapest first (all free):**
  1. **Split models = split budgets.** Free limits are *per-model, per-minute*. Put the one answer
     call on `LLM_MODEL_ANSWER` and the many cheap calls on `LLM_MODEL_CHEAP` — each gets its own
     RPM. Use the highest-RPM free models (`gemini-2.0-flash-lite` ~30 rpm).
  2. **Throttle.** A global min-interval between calls (`LLM_MIN_INTERVAL_MS`) keeps bursts — incl.
     the parallel multi-hop sub-retrievals — under quota.
  3. **Switch provider (env flag).** `LLM_PROVIDER=gemini|groq`. **Groq's free tier is far more
     generous** (~30 rpm **and** 14,400/day, very fast) and is OpenAI-compatible → a drop-in HTTP
     backend. Keep **embeddings on Gemini** (no Groq embeddings). Enable paid billing only if you can.
- **Rule:** make the LLM layer provider-agnostic from day one — one `generate` / `generate_json`
  seam, strict JSON via Gemini `responseSchema` OR OpenAI-style JSON mode + your OWN required-key
  validation. Then swapping providers under a rate limit is one env var, not a refactor.

### 12.3 A `@contextmanager` must `yield` exactly once — a `yield` in `except` MASKS the real error
- **Symptom:** `RAG error: generator didn't stop after throw()` — and the *actual* error (the rate
  limit) has vanished.
- **Cause:** a tracing wrapper did `try: yield trace; except Exception: yield None`. When the `with`
  body raises, the exception is thrown *into* the generator at the `yield`; the `except` catches it
  and yields a SECOND time → contextlib raises "generator didn't stop after throw()", replacing the
  original exception and defeating downstream error handling (our `except RateLimitError`).
- **Fix:** guard setup BEFORE the yield; run the body under a bare `try/finally`:
  ```python
  @contextmanager
  def span(...):
      trace = _try_start()      # guarded, before the yield
      try:
          yield trace
      finally:
          _flush(trace)         # no `except` — body exceptions propagate untouched
  ```
- **Rule:** never `yield` inside an `except` (or a second branch) of a `@contextmanager`. Wrappers
  (tracing, timing, metrics) must be transparent to exceptions.

### 12.4 API errors must be JSON; clients must parse defensively
- **Symptom (browser):** `Unexpected token 'I', "Internal S"... is not valid JSON`.
- **Cause:** the API handler threw → FastAPI returned its plain-text `Internal Server Error`; the web
  action did `await res.json()` → a parse crash that *hides* the real error.
- **Fix (both ends):**
  - **API:** catch at the boundary and always return JSON with a real status — `429` for rate
    limits, `502` otherwise:
    `return JSONResponse(status_code=..., content={"error": {"message": str(e)}})`.
    Never let a handler exception become a plain-text 500.
  - **Client:** `const raw = await res.text(); try { data = JSON.parse(raw) } catch { data = { error:
    { message: raw } } }`. A non-JSON error body must surface *as* the message, never crash the parser.

### 12.5 Key hygiene: name env vars by ROLE, and mind multi-provider key slots
- **`AWS_*` for Supabase Storage confused everyone** ("why are we using AWS?"). "S3" is a *protocol*;
  Supabase Storage is S3-compatible. Name by **role** — `STORAGE_ENDPOINT / _ACCESS_KEY_ID /
  _SECRET_ACCESS_KEY / _BUCKET / _REGION` — not `AWS_*`. The SDK (`@aws-sdk`, boto3) speaks S3 to any
  compatible store regardless of var names.
- **Two providers = two key slots; a swapped key looks like an auth bug.** `LLM_API_KEY` = Gemini
  (`AIza…`, used by embeddings **always**); `GROQ_API_KEY` = Groq (`gsk_…`, generation). Putting the
  Groq key in `LLM_API_KEY` → Gemini `400 API key not valid`. Document which service each key feeds,
  note the **prefixes** so a mis-paste is obvious, and verify a Gemini key before deploy:
  `curl "https://generativelanguage.googleapis.com/v1beta/models?key=<KEY>"`.

### 12.6 `/health` must answer GET *and* HEAD; keep free tiers warm with an uptime pinger
- Uptime monitors (UptimeRobot) probe with **both GET and HEAD**; FastAPI's `@app.get` returns
  **405** on HEAD. Use `@app.api_route("/health", methods=["GET", "HEAD"])`. Keep it cheap — **no DB,
  no LLM** (a static `{"status": "ok"}`) — so pinging is free.
- Render free web services **spin down after ~15 min idle**. Point an uptime monitor at `…/health`
  every 5 min to keep it warm (this also removes the cold-start-vs-frontend-timeout race on the first
  request after idle). One always-on free service ≈ 730 hrs/month, within the ~750 free hours — don't
  run several always-on free services on one account.

### 12.7 Free-stack single-service packing (Render free = ONE web service)
- Free tier gives one web service and no separate worker. **Fold the ingestion/RAG worker into the
  API as an in-process background task** that returns 200 immediately. This *also* dodges the
  gRPC-in-fork deadlock class (§6a/§11) — there's no fork. Flushed stage markers still apply.
  (Contrast Deflekt's paid design of a dedicated worker; on free tier, in-process is the right call.)

### 12.8 DX that removed real friction
- **Auto-load a repo-root `.env`** for host-run scripts/evals: a guarded `load_dotenv()` at the TOP
  of the config module — **before** the settings dataclass, because frozen-dataclass field defaults
  read `os.getenv` at import, so dotenv must populate the env first — and `config({ path: "../.env" })`
  in `drizzle.config.ts` (drizzle-kit runs with CWD = the web workspace). No-op inside containers.
- **npm workspaces:** the **root** `package-lock.json` is authoritative — delete stray per-package
  lockfiles (they trigger Turbopack's dual-lockfile warning); CI `npm ci` at root, then
  `npm run <script> --workspace web`.
- **Authed mutations via Next.js Server Actions** (server-side `getSession()`); reads via Server
  Components — sidesteps client Bearer-token plumbing and respects the Server/Client boundary (§6).
- **Generate AND commit Drizzle migrations** (source of truth); apply them with the `:5432` URL (§12.1).

### 12.9 The fully-free service map (drop-in for the AWS design)
| Need | Paid (Deflekt) | Free (Clause) |
|---|---|---|
| Web host | EC2 + nginx | **Vercel** |
| API host | EC2 | **Render** free web service |
| Postgres + pgvector | RDS | **Supabase** (transaction pooler `:6543` at runtime) |
| Object storage | S3 | **Supabase Storage** (S3-compatible; name vars `STORAGE_*`) |
| Cache | self-hosted Redis | **Upstash** (optional; no-op if unset) |
| Tracing | — | **Langfuse Cloud** (pin `<3`; no-op without keys) |
| LLM | — | **Gemini** (embeddings) + **Groq** (generation, `LLM_PROVIDER` switch) |
| CI/CD | GH Actions → SSH | **GitHub Actions** → Vercel/Render git integrations |

