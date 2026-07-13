# ROADMAP.md — Ringback

> **Text-first.** Voice is added only after Phase 3 regression evals are green. **They are green**
> (`cd agent && python -m evals.run --ci` → 14/14, 100% task success, 0% false-action). Voice
> (Phase 5) is still deliberately deferred until spend caps + alarms are live.

## Phase 0 — Foundation ✅
- [x] Repo structure (`agent/`, `orchestrator/`, `voice/`, `web/`, `packages/ui/`, `docs/`)
- [x] Docs committed (CLAUDE, ARCHITECTURE, DECISIONS, ROADMAP, .env.example, PRD, PROVIDERS, deploy, automation)
- [x] SaaS shell + UI kit + auth — clean-equivalent to Deflekt (repo absent; see DECISIONS.md)
- [x] Pick vertical (home-services) + make it a config abstraction; noted in README
- [x] docker-compose (postgres + redis + agent-core + orchestrator + web); CI stub (lint + tests + eval gate)

## Phase 1 — Text agent core ✅
- [x] Conversation state + intents: book, reschedule, cancel, FAQ, qualify (+ greeting/out-of-scope/unknown)
- [x] Tool interface: calendar (availability, create/modify/cancel), CRM write — MOCKED, deterministic
- [x] Confirmation step before any write (wired guardrail `assert_confirmed`)
- [x] Escalation triggers → transfer/callback with context
- [x] Facts (hours/prices/availability/FAQ) come from the vertical config via tools only

## Phase 2 — Real integrations 🟡 (interfaces + seam in place; real providers deferred)
- [ ] Calendar integration (Google/Outlook) behind the interface  ← replaces MockCalendar
- [ ] CRM integration behind the interface                        ← replaces MockCRM
- [x] CRM write + escalation notification via webhook (n8n seam) — orchestrator fires signed events
- [x] Credentials encrypted at rest (Fernet; `orchestrator/app/crypto.py`)

## Phase 3 — Regression evals (GATE before voice) ✅
- [x] Eval set: task success, intent accuracy, false-action rate, escalation appropriateness
- [x] **Test: never fabricates availability** (behavioral + write-boundary guardrail)
- [x] **Test: no write without confirmation** (behavioral + guardrail unit)
- [x] CI runs the text-core regression set (`python -m evals.run --ci`, fails below threshold)

## Phase 4 — Product surfaces (text) ✅
- [x] Text playground (free; posts through a server route so the token stays server-side)
- [x] Configuration (services, hours, escalation — read from the vertical; edit-in-place pending)
- [x] Integrations page (connection status; encrypted storage ready)
- [x] Calls log (transcript, intent, action, outcome, cost) — text runs first
- [x] Calendar view of agent bookings
- [x] Dashboard (calls, bookings, answered, escalations)

## Phase 5 — Voice layer 🔒 (NOT started — deferred by design; see voice/README.md)
- [ ] Telephony inbound (Twilio default / Telnyx swap) behind provider interface
- [ ] Streaming STT (Deepgram Nova-3) → agent core /chat → streaming TTS (ElevenLabs Flash); barge-in
- [ ] Latency tuning (fast turn model; cache FAQ/availability); measure p95 turn latency
- [ ] Add low-ASR-confidence as an escalation trigger
- [ ] End-to-end call: book/answer/escalate

## Phase 6 — Ship 🟡 (guide written; not yet deployed)
- [x] Free-stack deploy guide (Vercel + Render + Supabase + Upstash) — docs/DEPLOYMENT-FREE-STACK.md
- [ ] **Billing alarm + telephony spend cap** (REQUIRED before any voice deploy)
- [ ] CI/CD to platforms (staging text-only/free); plan-gating (minutes + numbers + integrations)
- [x] PII posture: encryption at rest, tenant scoping, retention note (90-day prune in supabase-setup.sql)
- [x] README: architecture, DECISIONS narrative, provider verification, eval artifacts
