# voice/ — Phase 5 ONLY (NOT built yet)

**Nothing here is wired.** Per the build order and the spend-cap rules, the voice layer is added
**only after the Phase 3 regression evals are green** (they are — but voice is still deferred until
you're ready to spend on minutes and have the telephony spend cap + alarm live).

Voice does **not** change the brain. It wraps the exact same agent core `/chat`:

```
Caller → Telephony (Twilio Media Streams / Telnyx) → Streaming STT (Deepgram Nova-3)
       → agent-core POST /chat  (the SAME core text uses)
       → Streaming TTS (ElevenLabs Flash / Deepgram Aura) → Caller
       barge-in enabled; p95 turn latency is the number that makes/breaks UX
```

## Provider decisions (verified July 2026; see docs/PROVIDERS.md)

All behind a swappable interface so a provider swap is config, not a rewrite:

- **Telephony:** Twilio (best Media Streams docs) default; Telnyx (~4x cheaper/min) drop-in swap.
- **STT:** Deepgram Nova-3 streaming (~$0.0077/min, billed per second).
- **TTS:** ElevenLabs Flash (~$0.05/1k chars) for quality; Deepgram Aura for budget.
- **Orchestration:** Pipecat (open source, self-host) — keeps our core as the brain; ~$0.07–0.12/min
  all-in vs Vapi's bundled ~$0.30/min.

## The interface to implement (Phase 5)

```python
class TelephonyProvider(Protocol):
    def answer(self, call): ...          # accept inbound, open a media stream
    def stream_audio_in(self, call): ...  # yield audio frames -> STT
    def play_audio(self, call, pcm): ...   # TTS frames -> caller
    def transfer(self, call, number): ...  # warm transfer on escalation
    def hangup(self, call): ...

class STTProvider(Protocol):
    def transcribe_stream(self, frames): ...  # -> partial/final text + confidence

class TTSProvider(Protocol):
    def synthesize_stream(self, text): ...    # -> audio frames (low latency)
```

## Hard gates before this ships (do NOT skip)

- [ ] Text regression evals green (`python -m evals.run --ci`) — **done**.
- [ ] `TELEPHONY_MONTHLY_MINUTE_CAP` + `TELEPHONY_SPEND_ALARM_USD` enforced and alarmed.
- [ ] Low-ASR-confidence added as an escalation trigger (voice-only signal).
- [ ] Per-turn latency + per-minute cost recorded on every CallLog.
