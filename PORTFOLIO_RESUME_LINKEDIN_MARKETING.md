# Ringback — Portfolio, Resume & LinkedIn Marketing Suite

This document contains production metrics, LaTeX resume code, portfolio presentation copy, and a 4-part LinkedIn marketing campaign designed to position **Ringback** as a highly rigorous, production-grade AI voice agent system. The messaging highlights the **text-first methodology**, behavioral guardrails, eval-gated CI, and no-code automation integration for the home-services industry.

---

## SECTION 1: Production Benchmarks & Eval Metrics

| Metric Category | Metric Name | Value / Result | Engineering Significance |
| :--- | :--- | :--- | :--- |
| **Trust / Safety** | Task Success Rate | **100% (14/14)** | Every eval scenario (book, reschedule, cancel, FAQ, qualify, escalate) completes correctly. |
| **Safety** | False-Action Rate | **0%** | No state-changing action (book/cancel) ever fires without explicit spoken confirmation. |
| **Integrity** | Fabricated Availability | **0 incidents** | Agent only offers slots the calendar tool actually returned — hard guardrail + test. |
| **Architecture** | Channel Independence | **Text ≡ Voice** | Conversation core is channel-agnostic; voice wraps STT/TTS around the identical logic. |
| **Development** | CI Eval Gate | **Regression Enforced** | No code ships without `python -m evals.run --ci` passing (task success ≥ threshold, false-action = 0%). |
| **Automation** | Webhook → Calendar + Email | **3 event types routed** | Make.com processes `booking.created`, `call.escalated`, `lead.qualified` in real-time. |

---

## SECTION 2: Portfolio Web Page & Card Breakdown

### A. Card View (Overview Card)
- **Title:** Ringback — Text-First AI Voice Agent for Home Services
- **Tagline:** An eval-gated inbound voice agent that books, reschedules, cancels, answers FAQ, qualifies leads, and escalates to humans — built text-first with behavioral guardrails and no-code automation integration.
- **Tech Badges:** `Python` `FastAPI` `Next.js 14` `PostgreSQL` `Supabase` `Make.com` `Groq` `Docker`
- **Video Loop Scenario:**
  1. Customer calls: "Hi, I need to book a drain cleaning."
  2. Agent checks availability via the calendar tool and offers real slots.
  3. Customer picks Thursday at 9 AM; agent asks for name, phone, address.
  4. Agent reads back the booking and asks for confirmation: "Should I go ahead?"
  5. Customer confirms → booking created → Google Calendar event appears instantly.
  6. Business owner receives a formatted confirmation email via Make.com.

---

### B. Detailed Modal View (Expanded Showcase)

#### 1. Executive Summary & Problem Solved
Home-services businesses (plumbing, HVAC, electrical, cleaning) lose revenue every time a call goes to voicemail — a missed call tonight is a lost job tonight. Generic chatbot builders fail because they hallucinate availability, book phantom slots, and can't enforce the confirmation protocols real businesses need. **Ringback** solves this with a *text-first* AI agent that proves its conversation logic (intents, tools, guardrails, confirmation, escalation) in text mode with a regression eval set, then adds voice as a thin STT/TTS wrapper around the identical core.

#### 2. Architecture & Tech Stack Choices
- **Conversation Core:** Python (FastAPI), deterministic rule-based NLU with Groq/Gemini swap-in, tool-calling against a calendar/CRM interface.
- **Orchestrator:** FastAPI — JWT auth, tenant/workspace scoping, call logging, webhook-out to Make.com.
- **Web Dashboard:** Next.js 14 (App Router), React — playground, call logs, calendar, configuration, integrations.
- **Database:** Supabase PostgreSQL (transaction pooler `:6543` at runtime, session `:5432` for migrations).
- **Automation:** Make.com scenario with Router-based event splitting → Google Calendar + Gmail notifications.
- **Deployment:** Vercel (web) + Render free (agent-core + orchestrator) + UptimeRobot (keep-warm).

#### 3. Core Technical Features
- **Text-First Methodology:** Entire conversation core built and proven in text before voice, using a regression eval set. Voice = STT (audio→text) → same core → TTS (text→audio). Proving it in text costs nothing and de-risks the paid voice pipeline.
- **Behavioral Guardrails (Wired + Tested):** `assert_confirmed()` blocks writes without spoken confirmation; `assert_slot_offered()` prevents fabricated availability. Both have dedicated tests — not just defined, but called in the execution path and verified in CI.
- **Vertical as Config:** Services, durations, business hours, FAQ, escalation rules live in YAML config files. Switch from home-services to clinics by changing one env var — no code change.
- **No-Code Automation Seam:** Agent core fires HMAC-signed webhooks. Make.com routes by event type: `booking.created` → Calendar + Email, `call.escalated` → urgent staff alert, `lead.qualified` → follow-up notification.

---

## SECTION 3: Resume LaTeX Code (STAR Method)

### LaTeX Resume Snippet (Insert in your PROJECTS section)

```latex
%-------------------------------------------
% RINGBACK - PROJECT RESUME ENTRY (LaTeX)
%-------------------------------------------
\textbf{Ringback — Text-First AI Voice Agent for Home Services} \hfill \textit{2026} \\
\textit{Python, FastAPI, Next.js 14, PostgreSQL, Supabase, Make.com, Docker} $|$ \href{https://github.com/SShayanHussain/ringback}{GitHub}
\begin{itemize}[leftmargin=0.25in, itemsep=2pt]
    \item Architected a text-first inbound voice agent using FastAPI and a channel-agnostic conversation core, achieving 100\% task success across 14 eval scenarios with 0\% false-action rate via wired behavioral guardrails.
    \item Engineered a deterministic rule-based NLU provider for reproducible CI/CD testing, with a hot-swappable Groq/Gemini interface enabling real NLU behind a single environment variable change.
    \item Built a no-code automation pipeline using Make.com with HMAC-signed webhooks, routing \texttt{booking.created}, \texttt{call.escalated}, and \texttt{lead.qualified} events to Google Calendar and Gmail notifications in real-time.
    \item Deployed a fully-free production stack (Vercel + Render + Supabase) with tenant-scoped Postgres, JWT auth, encrypted credential storage, and UptimeRobot keep-warm pinging for zero-downtime demo availability.
\end{itemize}
```

---

## SECTION 4: 4-Part LinkedIn Content Strategy

### Post 1: The "Text-First" Philosophy (Hook + Methodology)

**Headline:** 🎯 Stop building voice agents voice-first. You're burning money on bugs you could catch for free.

**Body:**
Here's an expensive mistake I see devs making: jumping straight into Twilio + STT + TTS before their conversation logic even works.

For **Ringback** (an AI voice agent for home-services scheduling), I did the opposite. I built the entire conversation core — intents, tool calls, guardrails, confirmation protocol, escalation — in **text mode first**.

Why?
📌 Text testing is free. Voice minutes cost money.
📌 A bug in conversation logic shows up identically in text and voice. Fix it once, fix it everywhere.
📌 Voice is just: STT (audio→text) → same core → TTS (text→audio). The wrapper changes, the brain doesn't.

💡 **The Result:** 14/14 eval scenarios passing with 100% task success and 0% false-action rate — all proven in text, before touching any voice API.

Build the brain first. Add the ears and mouth later.

#AI #VoiceAI #SoftwareEngineering #Python #FastAPI #SystemDesign

---

### Post 2: Guardrails That Actually Work (Wired, Not Written)

**Headline:** 🛡️ Your AI guardrail is useless if it's not called in the execution path.

**Body:**
I've seen this pattern too many times: a team writes a safety check function, puts it in `utils.py`, and never calls it from the actual endpoint.

In **Ringback**, the two critical guardrails are:

1️⃣ `assert_confirmed()` — No booking, cancellation, or reschedule fires without an explicit "yes" from the caller. Period.
2️⃣ `assert_slot_offered()` — The agent can ONLY book slots the calendar tool actually returned. No fabricated availability. Ever.

Both are called at the top of the execution path. Both have dedicated tests. CI fails if either is violated.

**The Rule:** After writing any guardrail, `grep` for its call site. No call site = no guardrail.

In production AI, the most important feature isn't the model. It's the cage around it.

#AI #SafeAI #SoftwareArchitecture #Testing #Python #BackendEngineering

---

### Post 3: The No-Code Automation Boundary

**Headline:** ⚡ I wired an AI agent to Google Calendar and Gmail without writing a single line of integration code.

**Body:**
Here's the architecture decision that saved me days of development on **Ringback**:

The AI agent handles the hard stuff — intent detection, slot negotiation, confirmation protocol, escalation triggers. All hand-coded, all tested.

But what happens AFTER a booking is confirmed? Calendar event creation, confirmation emails, staff alerts, lead notifications — that's **linear business-process glue**. It belongs in a no-code tool.

⚙️ **The Setup:**
- Agent core fires an HMAC-signed webhook per event type
- Make.com receives it and routes via a Router module:
  - `booking.created` → Google Calendar event + confirmation email
  - `call.escalated` → 🚨 urgent staff alert
  - `lead.qualified` → 💡 follow-up notification

No API wrappers. No OAuth plumbing. No email templating code. Just a webhook and a no-code scenario.

**The Boundary:** Core agent logic = code. Business-process glue = no-code tool. Respect the boundary and ship faster.

#Automation #MakeHQ #AI #NoCode #SystemDesign #Webhooks

---

### Post 4: The Eval-Gated CI Pipeline

**Headline:** 🧪 No code ships unless the AI passes a regression test. Here's how I enforce that.

**Body:**
In traditional software, CI runs unit tests. In AI systems, that's not enough.

For **Ringback**, I built an eval harness that runs as a CI gate on every PR:

```
python -m evals.run --ci
```

⚙️ **What it checks:**
- ✅ Task success across 14 scenarios (book, reschedule, cancel, FAQ, qualify, escalate)
- ✅ False-action rate = 0% (no write without confirmation)
- ✅ No fabricated availability (only calendar-provided slots offered)
- ✅ Escalation fires when it should (out-of-scope, angry caller)

If any metric drops below threshold, the PR is blocked. No exceptions.

💡 **Why this matters:** The rule-based NLU provider makes evals **deterministic and free** — no API calls, no flaky LLM responses, no cost. When I swap to Groq for production NLU, the guardrails are unchanged. The eval harness proves the control flow, not the language model.

Ship with confidence. Gate with evals.

#MachineLearning #CI #Testing #AI #Python #DevOps

---

### Post 5: The Make.com Routing Flow

**Headline:** 🔀 Stop writing custom API glue code. Use a single webhook and a Router instead.

**Body:**
When building AI agents, connecting to external systems (Calendars, CRMs, Email) usually means writing a lot of brittle integration code. For **Ringback**, I took a different approach.

Instead of writing custom API wrappers, the agent fires a single **HMAC-signed webhook** to Make.com at the end of every call. The magic happens in the Make.com Router module:

Here is the exact flow:
1️⃣ Agent detects the intent (book, escalate, qualify) and emits an event.
2️⃣ Make.com receives the webhook and hits a **Router**.
3️⃣ Branch 1: `booking.created` ➡️ Creates a Google Calendar event & sends a confirmation Gmail.
4️⃣ Branch 2: `call.escalated` ➡️ Sends an urgent staff alert.
5️⃣ Branch 3: `lead.qualified` ➡️ Routes to a CRM follow-up queue.

**Why this matters:**
- 🧩 **Modular:** I can swap Gmail for Outlook or Google Calendar for Calendly in Make.com without touching a single line of Python code.
- 🚀 **Speed:** The business process glue is visual and instant.
- 🔒 **Secure:** The webhook is HMAC-signed so only authorized events are processed.

Stop hardcoding integrations. Build a robust webhook seam and let automation tools do the heavy lifting.

#NoCode #Automation #SystemArchitecture #Python #FastAPI #MakeHQ

---

### Post 6: End-to-End Problem Solving for Home Services

**Headline:** 📉 Did you know a missed call in the home services industry often means a lost job tonight? 

**Body:**
For plumbing, HVAC, and electrical businesses, availability is everything. If a customer calls with a burst pipe and goes to voicemail, they call the next business on Google. A missed call = lost revenue.

I built **Ringback** to solve this exact gap. It's a multi-tenant AI voice agent platform specifically designed for appointment-based businesses.

Here is how it works end-to-end:
📞 **The Call:** A customer calls at 2 AM. Ringback answers instantly.
📅 **The Booking:** The agent checks real-time availability via calendar integration and negotiates a time slot.
✅ **The Confirmation:** It safely asks for confirmation, capturing name, phone, and address. 
⚡ **The Sync:** A webhook fires to Make.com, instantly syncing the appointment to the business owner's Google Calendar and sending a confirmation email.

And because it's built as a **multi-tenant SaaS**:
- Every business gets isolated, tenant-scoped data (PostgreSQL + Supabase).
- Configuration (business hours, services, FAQ) is isolated per workspace.
- JWT authentication and encrypted credential storage ensure enterprise-grade security.

AI isn't just about chatbots anymore. It's about solving real revenue leaks with fully autonomous, end-to-end workflows.

#SaaS #VoiceAI #Entrepreneurship #SoftwareEngineering #NextJS #FullStack
