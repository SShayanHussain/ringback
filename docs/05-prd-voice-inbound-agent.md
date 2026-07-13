# PRD 05 — Voice / Inbound Agent (Capstone, Optional-Hard)

> **Role in portfolio:** The capstone and the frontier bet. Voice + customer-facing automation is
> the #1 traction category in 2026, and this fuses everything: real-time streaming, tool use,
> integrations, guardrails, HITL for risky actions, and the full deploy stack. Primary domains:
> **Real-time + Agentic + Integrations + everything-at-once.**
> **Why last & optional:** telephony costs real money per minute, so you only build this once the
> free-tier projects are done and you can budget a small amount. It's the most impressive interview
> piece; it's also the one you can *design fully* and build a text/chat version of first to prove the
> logic before spending on voice.
> **Suggested stack:** Python agent core (reuse P3's LangGraph patterns); a telephony/voice provider
> (Twilio/Vonage for the phone line; a low-latency STT/TTS + voice-agent layer such as an
> ElevenLabs/Deepgram/Vapi-style service); FastAPI orchestration; Postgres; a calendar/CRM
> integration. **Confirm current provider pricing/features before committing — this space moves fast.**

---

## 0. Product profile

- **Product name:** **Ringback** (alt: *Frontdesk*, *NeverMissed*, *Answerly*)
- **Tagline:** "Never miss a call, never miss a booking."
- **One-liner positioning:** Ringback answers your business phone 24/7, books and reschedules
  appointments in natural conversation, updates your calendar and CRM, and hands off to a human when
  it should.
- **Category:** AI voice / inbound-call agent SaaS (vertical: clinics or home-services scheduling).
- **Who pays:** clinics, salons, home-services, small B2B where a missed call is lost revenue and 24/7
  human staffing is impossible. Value = captured bookings, deflected routine calls, after-hours coverage.
- **Pricing concept:** Free/trial (limited minutes, test number) · Pro (a real number, monthly minute
  bundle, calendar+CRM) · Team (multiple numbers/locations). Gate minutes + numbers + integrations.
  (Note: minutes cost you real money — see spend caps.)
- **Visual theme:** warm, reassuring, small-business-friendly — the opposite of enterprise-cold.
  Approachable color, big clear numbers, plain language. The signature UI is the **call view**:
  live/played transcript, detected intent, the action it took (with the booking that landed), outcome,
  and per-call cost. A calendar view showing agent-made bookings is the "it actually works" screen.
  Think a friendly modern small-business dashboard, not a telecom console.

## 0b. SaaS surface / page map

**Public:** landing (let visitors hear a sample call) · pricing · login · signup · reset · verify.

**Onboarding (first-run):** create workspace → connect calendar/CRM → set business hours, services,
and FAQ → configure the number (or test in chat first) → run a test call/chat → see the booking land
in the calendar. First agent-made booking is the activation moment.

**Authenticated app (shell: top bar + left nav):**
- **Dashboard** — calls today, bookings made, deflected/answered, escalations, minutes used vs plan.
- **Calls** — log of every call: transcript, detected intent, action taken, outcome, latency, cost;
  filter by outcome (booked / answered / escalated).
- **Calendar** — bookings the agent created/modified; sync status with the connected calendar.
- **Playground** — test the agent in **text mode** (free) before/without spending on voice minutes.
- **Configuration** — business hours, services/durations, FAQ answers, escalation rules, confirmation
  scripts, the number(s).
- **Integrations** — calendar (Google/Outlook) + CRM connections; credentials encrypted.
- **Settings** — profile · workspace · team/members (owner/member) · plan/billing · minute/spend caps ·
  API keys · data-retention/PII settings.

**Auth:** JWT access + refresh (httpOnly), verification, reset, role-guarded routes, workspace-scoped
calls/calendar/config. Call recordings & transcripts contain PII → encrypt at rest, access-control,
retention policy (extra care if clinics/health info).

---

## 1. Problem & opportunity

For clinics, home services, salons, and small B2B, a **missed call is lost revenue**. They can't
staff phones 24/7, and after-hours or high-volume periods send callers to voicemail (who never call
back) or to a competitor. The 2026 market shows voice agents handling enormous call volumes in
exactly these categories — appointment scheduling, order/status, reminders, lead qualification —
because the ROI (captured bookings, deflected routine calls) is direct and measurable.

**The gap:** SMBs need an inbound agent that can **answer, understand, act** (book/reschedule/answer
FAQ/qualify a lead, and write the result to their calendar/CRM) with human handoff for anything it
shouldn't do alone — at a cost far below a 24/7 human. Most SMB solutions are either dumb IVR trees
or too enterprise/expensive.

**Anchor vertical:** e.g. **clinics or home-services scheduling** — "answer the call, understand the
request, check availability, book or reschedule, update the system, escalate edge cases to a human."

---

## 2. What it is (one sentence)

An inbound voice agent for a specific vertical that answers calls, handles scheduling/FAQ/lead-qual
through natural conversation, takes real actions (calendar/CRM writes) with guardrails and human
handoff for risky cases, and logs every call for review.

---

## 3. Users & core stories

- **Caller**: "I call, talk naturally, and get my appointment booked or my question answered — or
  smoothly transferred to a person."
- **Business owner**: "Calls get answered 24/7, bookings land in my calendar, and I see a log +
  transcript + outcome for every call."
- **Staff**: "I get handed the calls that actually need a human, with context, not from scratch."

---

## 4. Scope

### In scope (MVP — build the text/chat version FIRST, then add voice)
1. **Conversation core** (reuse P3 patterns): an agent that handles the target intents (book,
   reschedule, cancel, FAQ, qualify) with tools.
2. **Real actions via tools/MCP**: check calendar availability, create/modify booking, write to CRM.
   Consequential writes go through a confirmation step (voice equivalent of HITL: "You want Tuesday
   at 3pm, correct?") and risky/edge cases escalate to human transfer.
3. **Voice layer** (added after text works): telephony inbound → streaming STT → agent → streaming
   TTS, tuned for **low latency** (the whole UX depends on it — long pauses kill voice agents).
4. **Guardrails**: strict scope (won't answer off-domain), confirmation before any booking write,
   escalation triggers (angry caller, out-of-scope, low ASR confidence), and no fabricated
   availability (must reflect the real calendar).
5. **Call logging**: transcript, intent, actions taken, outcome, cost per call, for every call.
6. **Handoff**: warm transfer or callback-scheduling when the agent bows out, with context.

### Out of scope (MVP)
- Outbound calling (inbound only — simpler, and the higher-trust use case).
- Multi-language (stretch).
- Deep multi-agent orchestration — a single well-guardrailed agent is right here; don't over-engineer.

---

## 5. Architecture

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

**Key decisions:**

- **Build text-first, voice-second.** The logic (intents, tools, guardrails, confirmation, escalation)
  is identical; voice just wraps it in STT/TTS. Proving it in chat costs nothing and de-risks the
  expensive part. *This sequencing is itself a good engineering-judgment story.*
- **Latency is the architecture.** Voice UX lives or dies on response time: streaming STT and TTS,
  barge-in (caller can interrupt), a fast model for the conversational turns and a heavier one only
  when needed, aggressive caching of things like FAQ answers and availability lookups. Every
  component choice is a latency choice.
- **Confirmation = HITL for voice.** You can't show an approval UI mid-call, so the guardrail is a
  spoken confirmation before any state-changing action, plus human transfer for anything out of
  scope. Same principle as P3, adapted to the channel.
- **Never fabricate availability.** The single most damaging failure is booking a slot that isn't
  real. The agent must only offer slots the calendar tool returns — a hard guardrail, tested.
- **Provider choice is a live decision.** Telephony + voice-agent tooling changes fast and pricing
  matters at per-minute scale — verify current options and costs before committing, and isolate the
  provider behind an interface so you can swap it.

---

## 6. Guardrails & safety (voice raises the stakes)

- **Scope lock**: politely refuses/transfers off-domain requests; never improvises policy.
- **Write confirmation**: explicit spoken confirm before booking/cancelling.
- **Escalation triggers**: low ASR confidence, repeated misunderstanding, detected frustration,
  out-of-scope, or any high-risk request → warm human transfer / scheduled callback with context.
- **No hallucinated facts**: hours, prices, availability come from tools, never the model's memory.
- **Privacy**: call recordings/transcripts contain PII — encrypt at rest, access-control, retention
  policy. (Especially if you pick clinics — treat health info carefully; note compliance posture.)

---

## 7. Observability & evals

- **Per-call log**: transcript, detected intent, tools called, actions taken, outcome, latency
  per turn, cost. This is your LLMOps surface for voice.
- **Evals** (run the text core through these; voice adds ASR/latency metrics):
  - *Task success* — booking made correctly / question answered / correctly escalated.
  - *Intent accuracy* and *false-action rate* (did it ever book the wrong thing / fabricate a slot?).
  - *Escalation appropriateness* — escalated when it should, didn't when it shouldn't.
  - *Turn latency* (voice) — p95 response time; the number that makes or breaks UX.
- **Regression set** in CI on the text core so conversation logic changes are measured.

---

## 8. Deployment & CI/CD

- **Docker**: agent core, orchestrator, (voice bridge). **AWS**: ECS/EC2, RDS, Redis for
  session/availability cache, Secrets Manager for provider + CRM creds. Billing alarm on — and here
  also a **telephony spend alarm/cap**, since per-minute costs are the real risk.
- **CI/CD**: GitHub Actions → run text-core regression evals → build → deploy. Keep the voice
  provider behind config so staging can run text-only for free.

---

## 9. Definition of Done

- [ ] Text core handles all target intents with tools, confirmation before writes, and correct
      escalation — proven by the regression eval set.
- [ ] Never fabricates availability (explicit test); consequential writes always confirmed.
- [ ] Voice layer: inbound call → book/answer/escalate end-to-end with acceptable p95 turn latency.
- [ ] Every call logged (transcript, actions, outcome, cost); PII handled responsibly.
- [ ] Deployed on AWS with billing + telephony spend caps; DECISIONS.md covers text-first sequencing,
      latency architecture, provider isolation, and the no-fabricated-availability guardrail.
- [ ] **SaaS shell (reused from P1):** JWT auth, workspace/roles, landing/pricing/onboarding, navigable
      app (dashboard, calls, calendar, playground, configuration, integrations, settings), plan-gating
      with minute/spend caps. Net-new surfaces are the call log/transcript view, calendar of agent
      bookings, and the text-mode playground.

---

## 10. How to start with Claude Code

1. *"Spec attached. We build text-first. Design the conversation state, intents, tool interface
   (calendar/CRM behind an interface), and guardrails — no voice yet."*
2. Slice order: text agent + mock calendar tool + confirmation + escalation → real calendar/CRM
   integration → regression evals → **then** add streaming STT/TTS + telephony behind the same core
   → latency tuning → deploy.
3. Before spending on voice: *"Run the text core through the full regression set and show task
   success, false-action rate, and escalation appropriateness — I only add voice once this is green."*
