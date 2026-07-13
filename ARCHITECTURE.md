# ARCHITECTURE.md — Ringback

## System overview

```
   Caller ─▶ Telephony (Twilio/Vonage inbound number)
                        │  audio stream
                ┌───────▼─────────┐     ┌──────────────┐
                │ Streaming STT   │────▶│ Agent core   │  (LangGraph-style,
                │ (low latency)   │     │ intent+tools │   reused from P3)
                └─────────────────┘     └──┬────┬──────┘
                        ▲                  │    │ tool calls
                ┌───────┴─────────┐        │    ▼
                │ Streaming TTS   │◀───────┘  ┌──────────────────────┐
                │ (barge-in ok)   │           │ Calendar / CRM APIs  │
                └─────────────────┘           │ (availability, book) │
                                              └──────────────────────┘
   Confirmation before any write ● ; escalation → warm transfer / callback
                        │
                ┌───────▼─────────┐        ┌──────────────┐
                │ FastAPI orchestr│───────▶│ Postgres     │
                │ + call logging  │        │ calls·txns·  │
                └─────────────────┘        │ transcripts  │
                                           └──────────────┘
```

## Services
- **agent/** — the conversation core (intents: book/reschedule/cancel/FAQ/qualify), tool use,
  guardrails, confirmation, escalation. **Text and voice share this exact core** — voice just wraps it.
- **orchestrator/** — FastAPI: auth (P1), configuration, call logging, integration management.
- **voice/** — telephony bridge + streaming STT/TTS. Added last. Provider behind a swappable interface.
- **web/** — Next.js: dashboard, call log/transcript view, calendar of agent bookings, **text playground**
  (test free), configuration, integrations.

## Text-first principle
Intents, tools, guardrails, confirmation, escalation are channel-independent and built/proven in TEXT.
Voice = STT (audio→text) → same core → TTS (text→audio). Proving the core in chat costs nothing and
de-risks the paid part.

## Latency is the architecture (voice layer)
Streaming STT + TTS; barge-in (caller can interrupt); fast model for turns, heavier only when needed;
cache FAQ answers + availability lookups. p95 turn latency is the number that makes/breaks UX.

## Guardrails
Scope lock (refuse/transfer off-domain) · spoken confirmation before writes · no fabricated
availability (slots only from the calendar tool) · escalation triggers · facts (hours/prices/
availability) from tools only, never model memory.

## Deployment
Docker (agent, orchestrator, voice, web). AWS: ECS/EC2, RDS, Redis (session/availability cache),
Secrets Manager (provider + CRM creds). CI/CD runs the text-core regression evals (staging can run
text-only, free). **Two alarms: general billing + telephony spend cap.** PII: encrypt at rest,
access-control, retention policy (extra care for clinics/health info).
