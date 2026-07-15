# Automation guide — the flows YOU build (n8n / Zapier / Make)

Ringback keeps the **agent logic** (intents, guardrails, confirmation, escalation) hand-coded and
tested. The **business glue** — writing to a calendar/CRM, texting a confirmation, pinging staff on
an escalation — is exactly what a no-code automation tool is for (DECISIONS.md). You build these
flows; Ringback calls them via one outbound webhook. Later we can point the calendar/CRM interfaces
at these same flows.

> Rule of thumb (from the automation playbook): **prototype the glue in n8n; rebuild a slice in code
> only when it needs branching/reliability n8n can't give.** Start here.

---

## 1. The webhook contract

When a call reaches a business-meaningful outcome, the orchestrator POSTs JSON to
`N8N_WEBHOOK_URL` (set it in the orchestrator env). Configure it once, build a flow per event.

- **Method:** `POST` · **Content-Type:** `application/json`
- **Header `X-Ringback-Signature`:** `HMAC-SHA256(body, N8N_WEBHOOK_SECRET)` (hex). Verify it.
- **Envelope:**
  ```json
  {
    "event": "booking.created",
    "event_id": "3f9c...",          // unique per delivery — DEDUPE on this
    "ts": 1752459200,
    "data": { ... }                  // event-specific (below)
  }
  ```

### Verify the signature (n8n Function node / Make / Zapier Code)
```js
const crypto = require("crypto");
const raw = $input.first().json.__raw ?? JSON.stringify($json); // use the raw body
const expected = crypto.createHmac("sha256", $env.RINGBACK_SECRET).update(raw).digest("hex");
if (expected !== $headers["x-ringback-signature"]) throw new Error("bad signature");
```

### Dedupe (webhook storms — PLAYBOOK §9)
Keep a short-lived store (n8n static data / a Redis/Sheet row) of seen `event_id`s and drop repeats
before doing any side effect. Make every downstream write idempotent (e.g., upsert by phone).

---

## 2. Events & payloads

Every `data` block carries these top-level fields: `workspace_id`, **`notify_email`** (the owner's
configured/ signup address — map this to the Gmail "To"), `session_id`, `intent`, `outcome`.

### `booking.created`
```json
{ "workspace_id": "ws_...", "notify_email": "owner@business.com", "session_id": "web",
  "intent": "book", "outcome": "booked",
  "booking": { "type": "booking_created", "booking_id": "bk_0001",
               "service_id": "drain_cleaning", "service": "Drain cleaning",
               "start_iso": "2026-07-16T09:00", "start_label": "Thursday 9:00 AM",
               "contact_name": "John Smith", "contact_phone": "5551234567",
               "address": "12 Oak Street" },
  "transcript": [ { "role": "user", "text": "..." }, { "role": "agent", "text": "..." } ] }
```
Use `booking.contact_*` / `booking.address` for the calendar event details; `notify_email` is the
BUSINESS OWNER (who wants to know a booking landed). To also email the CALLER you'd capture their
email as a slot — today we capture name + phone only (phone → SMS is the caller channel).

### `booking.rescheduled` · `booking.cancelled`
Same shape; `booking.type` = `booking_modified` / `booking_cancelled` (both carry `service` +
`start_label`; rescheduled also carries the new `start_iso`).
### `call.escalated`
```json
{ "workspace_id": "ws_...", "notify_email": "owner@business.com", "session_id": "web",
  "intent": "book", "outcome": "escalated",
  "escalation": { "type": "escalation", "reason": "high-risk request (matched 'gas leak')",
                  "mode": "transfer" },
  "transcript": [ ... ] }
```
### `lead.qualified`
```json
{ "workspace_id": "ws_...", "notify_email": "owner@business.com", "session_id": "web",
  "intent": "qualify", "outcome": "qualified", "transcript": [ ... ] }
```

---

## 3. Flows to build (recommended)

**A. `booking.created` → put it on the calendar + confirm to the caller**
1. Webhook trigger → verify signature → dedupe on `event_id`.
2. **Google Calendar: Create Event** — start = `data.booking.start_iso`, title = the service, add
   the caller's name/phone from the transcript (or from a later CRM lookup).
3. **Twilio/Email: Send confirmation** — "You're booked for {service} on {when}."
4. **CRM: upsert contact** + log "booked".

**B. `call.escalated` → get a human on it fast**
1. Verify + dedupe.
2. **Slack/SMS to on-call staff** with `data.escalation.reason` + a link/summary of the transcript.
3. **Create a callback task** (n8n → your ticketing/CRM) when `mode = "callback"`.
4. Optional: **SLA timer** — if no human responds in N minutes, escalate again.

**C. `lead.qualified` → nurture**
1. Verify + dedupe.
2. **CRM: create/append lead** with the transcript summary.
3. **Email/SMS**: send pricing + a booking link.

**D. `booking.cancelled` / `booking.rescheduled` → keep systems in sync**
1. Verify + dedupe. 2. Update the calendar event. 3. Notify staff / update CRM.

---

## 4. The reverse direction (Phase 2, optional)

Today the calendar/CRM tools are mocked behind interfaces (`agent/ringback_agent/tools/`). Two ways
to make them real:
- **In code:** implement `CalendarProvider` / `CRMProvider` against Google/Outlook/your CRM.
- **Via n8n:** implement a thin provider that calls an n8n webhook which does the actual API work.
  Good for speed; move hot paths (availability lookups) into code if latency matters — voice is
  latency-sensitive, so real-time availability should be a direct API call, not a webhook hop.

---

## 5. Test your flow before going live
- In n8n, use the webhook's **Test URL**, then trigger a booking in the Ringback **Playground**
  (it fires real events at terminal turns).
- Confirm: signature verifies, `event_id` dedupes on a retry, and the side effect is idempotent.
- Only then set `N8N_WEBHOOK_URL` to the **production** webhook URL in the orchestrator env.
