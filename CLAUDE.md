# CLAUDE.md — Ringback

> Standing rules. Read this + ARCHITECTURE.md + DECISIONS.md + ROADMAP.md every session.
> Reuses the SaaS shell + UI kit from Deflekt (P1). **Build TEXT-FIRST; add voice only when the
> text core passes its regression evals.** Voice minutes cost real money — respect spend caps.

## Product
**Ringback** — an inbound voice agent for a vertical (clinics / home-services scheduling). Answers
calls 24/7, books/reschedules/answers FAQ/qualifies leads in natural conversation, writes to
calendar/CRM, hands off to a human when needed. Full PRD: `docs/05-prd-voice-inbound-agent.md`.

## Stack
- **Agent core:** Python (reuse LangGraph patterns from Consensus/P3).
- **Telephony:** Twilio/Vonage inbound. **Voice:** low-latency STT/TTS provider (ElevenLabs/Deepgram/
  Vapi-style). **Orchestration:** FastAPI. **UI:** Next.js. **DB:** Postgres. **Cache:** Redis.
- **VERIFY provider pricing/features live before committing** — this space moves fast. Isolate the
  provider behind an interface so it's swappable.
- **Auth/UI kit:** reused from Deflekt.

## How to work (enforce)
1. **Text-first.** Build/prove intents, tools, guardrails, confirmation, escalation in TEXT mode.
   Voice is added only after the text regression set is green.
2. **Plan before code**; vertical slices; small commits; update DECISIONS.md + ROADMAP.md.
3. **Latency is the architecture** for the voice layer — every component choice is a latency choice.

## Conventions
- Structure: `agent/` (core, text+voice share it), `orchestrator/` (FastAPI), `voice/` (telephony+STT/TTS bridge), `web/`, `packages/ui/`, `docs/`.
- Calendar/CRM behind an **interface** (mockable in text mode / tests).
- Every call logged: transcript, intent, actions, outcome, latency, cost.

## Hard rules — do NOT
- Do NOT fabricate availability — only offer slots the calendar tool actually returns. (Tested.)
- Do NOT take a state-changing action (book/cancel) without spoken confirmation.
- Do NOT answer off-domain — refuse/transfer; never improvise policy, hours, or prices (tools only).
- Do NOT add the voice layer before the text core passes regression evals.
- Do NOT store PII/recordings unencrypted — encrypt at rest, access-control, retention policy.
- Do NOT store secrets in code; do NOT add deps without asking.
- Do NOT deploy without a telephony spend cap/alarm.

## Escalation triggers
Low ASR confidence · repeated misunderstanding · detected frustration · out-of-scope · high-risk
request → warm transfer / scheduled callback WITH context.

## Commands
- Dev: `docker compose up` (agent + orchestrator + web + postgres + redis)
- Text playground: `npm run playground` (free — no voice spend)
- Test: `pytest` / `npm test` · Lint: `ruff check` / `npm run lint`
- Regression evals (text core): `python -m evals.run` (task success, intent accuracy, false-action
  rate, escalation appropriateness)
- Voice (only after text green): `python -m voice.serve`

## Definition of done for a slice
Runs locally, regression evals pass (text), no fabricated availability (test), docs updated, one commit.
