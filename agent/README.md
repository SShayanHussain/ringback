# agent/ — Ringback conversation core (the brain)

Channel-independent. Text and voice both call `POST /chat`. The core LOGIC (agent, rule-based NLU,
mock tools, guardrails) is **pure stdlib** — tests and evals need no API key and cost nothing.

## Run

```bash
pip install -e .            # or: pip install -e ./agent from repo root
pytest -q                   # unit tests (hard rules)
python -m evals.run         # regression report
python -m evals.run --ci    # the Phase 3 GATE (non-zero exit if below threshold)
python -m ringback_agent.playground   # free text REPL
uvicorn ringback_agent.service:app --port 8001   # the /chat service
```

## Layout

| File | Role |
|---|---|
| `agent.py` | The turn state machine (LangGraph *patterns*, no heavy dep). |
| `state.py` | Serializable `ConversationState` (round-trips per turn). |
| `vertical.py` + `verticals/*.json` | The ONLY source of business facts. Swap `VERTICAL` to switch. |
| `llm/` | NLU seam: `rulebased` (default, key-free) or `groq`/`gemini` behind the same interface. |
| `tools/` | `CalendarProvider`/`CRMProvider` interfaces + deterministic mocks. |
| `guardrails.py` | No-fabrication + no-write-without-confirmation, wired into the write path. |
| `escalation.py` | High-risk / frustration / repeated-misunderstanding triggers. |
| `service.py` | FastAPI `/chat` + `/health` (GET+HEAD). |

## Hard rules (enforced + tested)

- **Never fabricate availability** — `guardrails.assert_slot_offered` gates every booking write.
- **No write without confirmation** — `guardrails.assert_confirmed` gates every state change.
- **Facts from tools only** — hours/prices/FAQ come from `verticals/*.json`, never the model.
- **No-key mode is honest** — degrades to deterministic heuristics, never a fabricated confident answer.
