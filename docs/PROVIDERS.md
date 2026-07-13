# Providers — verified pricing & the decision (Phase 5 / voice)

> **Verified live via official + market sources, July 2026.** Prices move fast and are per-account —
> re-verify at signup before committing. Nothing is committed in code: every provider sits behind a
> swappable interface (`voice/`), so a change is config, not a rewrite (DECISIONS.md).

## The decision (à-la-carte, not all-in-one)

We assemble the voice stack from best-of-breed pieces instead of an all-in-one platform, so **our
agent core stays the brain** and the per-minute cost is ~3x lower.

| Layer | Chosen | Verified rate | Alt / swap |
|---|---|---|---|
| Telephony | **Twilio** (Media Streams) | inbound local **$0.0085/min**; toll-free $0.022/min | **Telnyx ~$0.002/min** (≈4x cheaper at scale) |
| STT | **Deepgram Nova-3** streaming | **~$0.0077/min**, billed per second | — |
| TTS | **ElevenLabs Flash** | **$0.05 / 1k chars** (~$0.045/min) | Deepgram Aura (budget) |
| Orchestration | **Pipecat** (OSS, self-host) | infra only | LiveKit Agents |
| LLM (turns) | **Groq** (free tier) → paid | ~30 rpm + 14.4k/day free | Gemini (`LLM_PROVIDER` switch) |

**All-in cost ≈ $0.07–0.12/min** vs **Vapi's bundled ~$0.30–0.33/min**. That margin is what makes the
`TELEPHONY_MONTHLY_MINUTE_CAP=2000` / `$50` alarm sane (~$140–240/mo worst case).

### Why not Vapi / an all-in-one?
Convenient, but it hides the agent logic we've built and tested, costs ~3x more per minute, and
couples us to one vendor. Pipecat keeps the pipeline (STT → **our /chat** → TTS) under our control
and lets us benchmark provider combos for latency — and "latency is the architecture" for voice.

### Why Twilio default, Telnyx as the swap?
Twilio has the most mature Media Streams docs/ecosystem → fastest to a working call. Telnyx is ~4x
cheaper per minute; once volume justifies it, switch the `TELEPHONY_PROVIDER` env — the interface is
identical.

## Cost model (per 3-minute booking call, à-la-carte)
| Component | Rate | 3 min |
|---|---|---|
| Telephony (Twilio local) | $0.0085/min | $0.026 |
| STT (Deepgram Nova-3) | $0.0077/min | $0.023 |
| TTS (ElevenLabs Flash, ~900 chars/min) | $0.05/1k | ~$0.135 |
| LLM (Groq, cheap turn model) | ~$0.01–0.03/min | ~$0.06 |
| **Total** | | **~$0.24 / call** (~$0.08/min) |

TTS dominates → cache FAQ/confirmation phrasings and keep replies tight (also better UX).

## Sources (verified July 2026)
- Twilio Programmable Voice pricing (US): https://www.twilio.com/en-us/voice/pricing/us
- Telnyx vs Twilio voice pricing: https://telnyx.com/resources/telnyx-vs-twilio-which-voice-api-is-better
- Deepgram pricing (Nova-3 streaming): https://deepgram.com/pricing
- ElevenLabs pricing (Flash TTS + agents): https://elevenlabs.io/pricing
- Vapi pricing (all-in bundle): https://vapi.ai/pricing
- Pipecat vs LiveKit orchestration: https://www.assemblyai.com/blog/orchestration-tools-ai-voice-agents
