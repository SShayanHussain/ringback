# DECISIONS.md — Ringback

> ADR log. Append after every choice. Context / Decision / Tradeoff / Revisit when.
---

## [seed] Text-first, voice-second
Context: voice minutes cost money; the logic (intents/tools/guardrails/confirmation/escalation) is
channel-independent.
Decision: build and prove the entire core in TEXT mode with a regression eval set; add STT/TTS/
telephony only once text is green.
Tradeoff: voice "wow" is delayed.
Revisit when: n/a — this sequencing is the point (and a good engineering-judgment story).

## [seed] Provider behind a swappable interface
Context: telephony + voice tooling and pricing change fast.
Decision: isolate the voice/telephony provider behind an interface.
Tradeoff: a small abstraction layer up front.
Revisit when: locked to one provider for a concrete reason (then simplify).

## [seed] Never fabricate availability
Context: the single most damaging failure is booking a slot that isn't real.
Decision: agent may only offer slots the calendar tool returns; hard guardrail + test.
Tradeoff: none worth taking the other way.
Revisit when: n/a — non-negotiable.

## [seed] Spoken confirmation as HITL-for-voice
Context: can't show an approval UI mid-call, but writes still need a gate.
Decision: explicit spoken confirmation before any state-changing action; human transfer for out-of-scope.
Tradeoff: an extra conversational turn.
Revisit when: n/a — this is the safety model for the channel.

## [seed] Single well-guardrailed agent, not multi-agent
Context: the task is bounded (scheduling/FAQ/qualify).
Decision: one agent with strong guardrails; no multi-agent orchestration here.
Tradeoff: less flexible than a crew.
Revisit when: scope genuinely expands beyond one agent's competence.

## [seed] Telephony spend cap + billing alarm before deploy
Context: per-minute costs are the real financial risk.
Decision: two alarms (general billing + telephony minutes) and a hard cap.
Tradeoff: none.
Revisit when: n/a — required.

## Automation-tool boundary: n8n for CRM/notification glue
Context: calendar/CRM integrations + staff notifications are business-process glue, not core agent logic.
Decision: agent core calls a webhook into n8n for CRM writes + escalation notifications; core logic
(intents, guardrails, confirmation) stays hand-coded.
Tradeoff: an extra hop + a second thing to deploy; but it's the correct tool for linear glue work,
and it demonstrably covers your AI-automation domain inside the capstone rather than skipping it.
Revisit when: the glue needs branching complexity or reliability n8n can't give — then port that
slice into worker/ as real code (same instinct as the automation guide's "prototype in n8n, rebuild
in code once it needs real reliability").

## Vertical = home-services (as a config abstraction)
Context: needed to pick clinics vs home-services. Clinics drag in HIPAA/health-info compliance that
slows a free-tier MVP without adding portfolio value; home-services keeps PII demonstrable but not
blocking, and the "missed call = lost job tonight" ROI story is blunt.
Decision: ship home-services as the active vertical, but make the vertical a data abstraction
(`agent/ringback_agent/verticals/*.json`) so switching to `clinic` is one env var, no code change.
Tradeoff: a small config layer instead of hard-coding one vertical.
Revisit when: a customer needs a vertical whose flow (not just facts) differs structurally.

## Deploy on the fully-free stack, not AWS
Context: user directive + PLAYBOOK §12 (Clause proved this stack in prod).
Decision: Vercel (web) · Render free (agent-core + orchestrator) · Supabase (Postgres, txn pooler
:6543 runtime / :5432 migrations) · Upstash (Redis, optional) · Groq/Gemini (LLM) · GitHub Actions →
platform git integrations. No SSH deploy. Full guide in docs/DEPLOYMENT-FREE-STACK.md.
Tradeoff: free-tier limits (Render idle spin-down, ~750 hrs) — mitigated with an uptime pinger.
Revisit when: real traffic exceeds free-tier limits.

## Provider verification result (voice, Phase 5) — à-la-carte, behind interfaces
Context: PRD requires verifying pricing/features live before committing.
Decision (verified July 2026, docs/PROVIDERS.md): Twilio telephony (Telnyx as cheaper swap),
Deepgram Nova-3 STT, ElevenLabs Flash TTS, Pipecat (OSS) orchestration keeping OUR core as the
brain, Groq LLM for turns. All behind the `voice/` interface. ~$0.07–0.12/min all-in vs Vapi's
bundled ~$0.30 — ~3x cheaper + full control.
Tradeoff: we assemble the pipeline instead of buying an all-in-one.
Revisit when: a provider's pricing/latency changes materially (it will — re-verify at signup).

## LLM/NLU seam with a deterministic rule-based default
Context: free LLM tiers 429 under multi-call flows (PLAYBOOK §12.2); CI/evals must be reproducible
and cost nothing; a missing key must never fake a confident answer (Golden Rule 1).
Decision: NLU behind an interface with `rulebased` (deterministic, key-free) as the default used by
tests/CI/evals; `groq`/`gemini` swap in behind the same interface. No-key/failed-LLM degrades to the
honest rule-based heuristics, never a fabricated confidence.
Tradeoff: rule-based NLU is simpler than an LLM — but it's enough to prove the control flow and
guardrails, which is the point of the text-first phase.
Revisit when: shipping to real callers — turn on Groq for better NLU; guardrails are unchanged.

## Agent core is its own /chat service (text and voice share it verbatim)
Context: "text and voice share this exact core" (ARCHITECTURE.md).
Decision: the brain is a standalone FastAPI service exposing POST /chat (stateless per turn). The
orchestrator's playground and (later) the voice bridge both call it — the wrapper differs, the brain
does not.
Tradeoff: one more service, but it makes the text-first→voice transition a no-op for the core.
Revisit when: never for the core; the voice bridge is additive.

## SaaS shell rebuilt as a clean equivalent (Deflekt repo absent)
Context: the brief said "copy the Deflekt (P1) shell," but that repo isn't in this workspace.
Decision: build a clean-equivalent Next.js shell + UI kit + JWT auth following the exact Deflekt /
PLAYBOOK conventions (Server Actions, httpOnly cookies, Server/Client boundary, defensive JSON).
Tradeoff: reimplementation instead of a literal copy.
Revisit when: the real Deflekt shell is available to diff/reuse.
