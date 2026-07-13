# Ringback

> **Never miss a call, never miss a booking.** An inbound voice agent for **home-services**
> scheduling — answers 24/7, books/reschedules/cancels, answers FAQ, qualifies leads, writes to
> calendar/CRM, and hands off to a human when it should.

**Build order is TEXT-FIRST.** The conversation core (intents, tools, guardrails, confirmation,
escalation) is channel-independent and proven in text with a regression eval set. Voice (STT/TTS +
telephony) is added only after the Phase 3 evals are green. Voice minutes cost real money — respect
the spend caps.

---

## Vertical: home-services (swappable)

The active vertical is **home-services** (plumbing / HVAC / electrical / cleaning — missed call =
lost job). It is a **config abstraction**: services, durations, business hours, FAQ, qualification
fields, and escalation rules all live in `agent/ringback_agent/verticals/*.yaml`. Switch to clinics
by setting `VERTICAL=clinic` — no code change. See [DECISIONS.md](DECISIONS.md).

## Monorepo layout

```
agent/          Python — the text-first conversation core (the "brain"). Its own FastAPI service
                exposing POST /chat. Text AND voice both call this exact core.
orchestrator/   FastAPI — auth (JWT), tenant/workspace scoping, config, call logging, the text
                playground endpoint, n8n webhook-out. Persists everything.
voice/          Phase 5 ONLY (not built). Telephony + streaming STT/TTS bridge behind a provider
                interface. Calls the same agent /chat.
web/            Next.js — SaaS shell: landing, pricing, auth, dashboard, calls, calendar,
                playground, configuration, integrations, settings.
packages/ui/    Shared UI kit (React).
evals/          Regression harness — `python -m evals.run`. The Phase 3 GATE before voice.
db/             Schema + migrations (every table tenant-scoped) + Supabase setup.
docs/           PRD, provider verification, free-stack deploy guide, automation (n8n) guide.
```

## Quickstart (local, free — no voice spend)

```bash
cp .env.example .env            # fill LLM_PROVIDER etc.; defaults run key-free (rule-based)
docker compose up               # postgres + redis + agent-core + orchestrator + web

# or run pieces directly:
make agent-test                 # pytest the conversation core
make evals                      # python -m evals.run  (the Phase 3 gate)
make playground                 # free text REPL against the agent core (no voice)
```

- Web: http://localhost:3000  ·  Orchestrator API: http://localhost:8000  ·  Agent core: http://localhost:8001
- The agent core runs **key-free by default** (deterministic rule-based LLM provider) so tests and
  evals are reproducible and cost nothing. Set `LLM_PROVIDER=groq|gemini` + a key for real NLU.

## Hard rules (enforced in code + tests)

1. **Never fabricate availability** — only slots the calendar tool actually returns. (`test_no_fabricated_availability.py`)
2. **No state-changing action without confirmation** — book/cancel require an explicit confirm turn. (`test_no_write_without_confirmation.py`)
3. **Facts from tools only** — hours/prices/services/FAQ come from the vertical config via tools, never model memory.
4. **Scope lock** — off-domain requests are refused/transferred, never improvised.
5. **Telephony spend cap + alarm before any voice deploy.**

## Deployment: free stack (not AWS)

Vercel (web) · Render (agent-core + orchestrator) · Supabase (Postgres, transaction pooler `:6543`
at runtime) · Upstash (Redis, optional) · Groq/Gemini (LLM). Full guide:
[docs/DEPLOYMENT-FREE-STACK.md](docs/DEPLOYMENT-FREE-STACK.md).

## Automation (you build this in n8n/Zapier/Make, then we integrate)

The agent core calls a single **webhook seam** for CRM writes + escalation notifications. Build the
flows in your no-code tool and point the webhook at them: [docs/AUTOMATION-GUIDE.md](docs/AUTOMATION-GUIDE.md).

## Docs to read every session

[CLAUDE.md](CLAUDE.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [DECISIONS.md](DECISIONS.md) ·
[ROADMAP.md](ROADMAP.md) · [PLAYBOOK.md](PLAYBOOK.md) · [docs/05-prd-voice-inbound-agent.md](docs/05-prd-voice-inbound-agent.md)
