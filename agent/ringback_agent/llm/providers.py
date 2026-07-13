"""Optional real LLM backends (Groq / Gemini) behind the NLU interface.

Constructed lazily; httpx imported inside methods (PLAYBOOK §11 rule 2 — never build heavy clients
at import). Any failure degrades to the rule-based fallback (honest heuristics), never a fabricated
confident answer. interpret_yes_no / detect_frustration / select_slot stay deterministic (fallback).
"""
from __future__ import annotations

import json
import logging
import re
import time

from ..config import Settings
from ..state import ConversationState, Intent
from ..vertical import Vertical
from .base import IntentResult
from .rulebased import RuleBasedNLU

log = logging.getLogger("ringback.llm")

_INTENTS = [i.value for i in Intent]


class _Throttle:
    def __init__(self, min_interval_ms: int):
        self._gap = min_interval_ms / 1000.0
        self._last = 0.0

    def wait(self) -> None:
        if self._gap <= 0:
            return
        delta = time.monotonic() - self._last
        if delta < self._gap:
            time.sleep(self._gap - delta)
        self._last = time.monotonic()


class GroqBackend:
    """OpenAI-compatible chat completions with JSON mode."""

    def __init__(self, settings: Settings):
        self.key = settings.groq_api_key
        self.model = settings.llm_model_turn or "llama-3.1-8b-instant"
        self.throttle = _Throttle(settings.llm_min_interval_ms)

    def complete_json(self, system: str, user: str, required: list[str]) -> dict:
        import httpx

        self.throttle.wait()
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _parse_required(content, required)


class GeminiBackend:
    def __init__(self, settings: Settings):
        self.key = settings.llm_api_key
        self.model = settings.llm_model_turn or "gemini-2.0-flash-lite"
        self.throttle = _Throttle(settings.llm_min_interval_ms)

    def complete_json(self, system: str, user: str, required: list[str]) -> dict:
        import httpx

        self.throttle.wait()
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}"
            f":generateContent?key={self.key}"
        )
        resp = httpx.post(
            url,
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_required(content, required)


class LLMNLU:
    """Uses an LLM backend for intent + slot extraction; deterministic fallback for the rest."""

    def __init__(self, backend, fallback: RuleBasedNLU | None = None):
        self.backend = backend
        self.fb = fallback or RuleBasedNLU()

    def classify_intent(self, text: str, vertical: Vertical, state: ConversationState) -> IntentResult:
        system = (
            "You are the intent classifier for an inbound scheduling phone agent. "
            f"Return JSON {{\"intent\": one of {_INTENTS}, \"confidence\": 0..1}}. "
            "Use 'out_of_scope' for anything not about scheduling or this business's FAQ."
        )
        try:
            data = self.backend.complete_json(system, text, ["intent", "confidence"])
            intent = str(data["intent"]).lower()
            if intent not in _INTENTS:
                raise ValueError(f"unknown intent {intent}")
            return IntentResult(intent, float(data["confidence"]))
        except Exception as e:  # noqa: BLE001 — degrade, don't crash
            log.warning("LLM classify failed (%s); using rule-based fallback.", e)
            return self.fb.classify_intent(text, vertical, state)

    def extract_slots(self, text: str, expecting: str | None, vertical: Vertical) -> dict:
        services = ", ".join(f"{s.id}={s.name}" for s in vertical.services)
        system = (
            "Extract booking fields from the caller message as JSON with any of these keys you can "
            "find: service_id, service, urgency, address, contact_name, contact_phone. "
            f"Known services: {services}. Only include keys you are confident about."
        )
        try:
            data = self.backend.complete_json(
                system, f"expecting={expecting}\nmessage={text}", []
            )
            allowed = {"service_id", "service", "urgency", "address", "contact_name", "contact_phone"}
            merged = {k: v for k, v in data.items() if k in allowed and v}
            # Union with deterministic extraction so we never lose a clean regex hit (phone, etc.).
            merged.update(self.fb.extract_slots(text, expecting, vertical))
            return merged
        except Exception as e:  # noqa: BLE001
            log.warning("LLM extract failed (%s); using rule-based fallback.", e)
            return self.fb.extract_slots(text, expecting, vertical)

    def interpret_yes_no(self, text: str) -> bool | None:
        return self.fb.interpret_yes_no(text)

    def detect_frustration(self, text: str) -> bool:
        return self.fb.detect_frustration(text)

    def select_slot(self, text: str, offered: list[dict]) -> dict | None:
        return self.fb.select_slot(text, offered)


def _parse_required(content: str, required: list[str]) -> dict:
    """Defensive JSON parse + required-key validation (PLAYBOOK §12.2 / Flowlet §5)."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.S)
        if not m:
            raise
        data = json.loads(m.group(0))
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"LLM JSON missing required keys: {missing}")
    return data
