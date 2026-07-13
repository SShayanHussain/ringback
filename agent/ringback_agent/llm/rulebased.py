"""Deterministic rule-based NLU — the default. Key-free, reproducible, and honest.

This proves the CONTROL FLOW and GUARDRAILS (which are deterministic) without any API spend. NLU
*quality* is improved separately by swapping in an LLM backend behind the same interface; the
guardrails and confirmation logic are identical either way.
"""
from __future__ import annotations

import re

from ..state import ConversationState, Intent
from ..vertical import Vertical
from .base import IntentResult

_PHONE = re.compile(r"(?:\+?1[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
_NAME = re.compile(
    r"(?:my name is|this is|i am|i'm|it's|its|name'?s)\s+"
    r"([A-Za-z][\w'.\-]*(?:\s+[A-Za-z][\w'.\-]*){0,2})",
    re.I,
)
_ADDRESS_LEAD = re.compile(r"(?:address is|address'?s|located at|live at|it's at|i'm at|at)\s+(.+)$", re.I)
_TIME = re.compile(r"\b(\d{1,2})(?:\s*:\s*(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?\b", re.I)

_ORDINALS = {
    "first": 0, "1st": 0, "one": 0, "1": 0,
    "second": 1, "2nd": 1, "two": 1, "2": 1,
    "third": 2, "3rd": 2, "three": 2, "3": 2,
    "fourth": 3, "4th": 3, "four": 3, "4": 3,
}
_EARLIEST = ("earliest", "soonest", "first available", "as soon as", "asap", "any", "whatever", "doesn't matter", "does not matter")

_YES_PHRASES = ("sounds good", "go ahead", "book it", "do it", "that works", "yes please",
                "looks good", "that's right", "that is right", "let's do it", "lets do it",
                "please do", "for sure", "book that")
_NO_PHRASES = ("no thanks", "not right", "not correct", "that's wrong", "that is wrong",
               "do not", "don't", "different time", "another time", "change it", "not that")
_YES = {"yes", "yeah", "yep", "yup", "sure", "correct", "right", "confirm", "confirmed",
        "ok", "okay", "okey", "perfect", "great", "please", "affirmative", "yea"}
_NO = {"no", "nope", "nah", "wrong", "incorrect", "cancel", "change", "different", "stop", "nevermind"}

_FRUSTRATION = ("frustrat", "ridiculous", "useless", "terrible", "stupid", "hate this",
                "not helping", "talk to a human", "talk to a person", "speak to a human",
                "speak to someone", "real person", "representative", "human being",
                "this is stupid", "annoyed", "fed up", "waste of time", "forget it",
                "let me talk to", "get me a person", "operator")

_GREETINGS = ("hello", "hi ", "hi.", "hi!", "hey", "good morning", "good afternoon",
              "good evening", "howdy", "yo ")
_ACTION_BOOK = ("book", "schedule", "appointment", "come out", "send someone", "send somebody",
                "need someone", "need somebody", "set up", "make an appointment", "get someone",
                "come by", "come over", "come and", "visit", "have someone")
_RESCHEDULE = ("reschedule", "move my", "move the", "change my appointment", "change the appointment",
               "push back", "push my", "different day for my")
_CANCEL = ("cancel", "call off", "call it off")
_QUALIFY = ("quote", "estimate", "ballpark", "how much would it cost to", "give me a price for")


class RuleBasedNLU:
    def classify_intent(self, text: str, vertical: Vertical, state: ConversationState) -> IntentResult:
        t = f" {text.lower().strip()} "

        if any(k in t for k in _CANCEL) and "don't cancel" not in t and "do not cancel" not in t:
            return IntentResult(Intent.CANCEL.value, 0.85)
        if any(k in t for k in _RESCHEDULE):
            return IntentResult(Intent.RESCHEDULE.value, 0.85)
        if any(k in t for k in _QUALIFY):
            return IntentResult(Intent.QUALIFY.value, 0.8)
        if any(k in t for k in _ACTION_BOOK):
            return IntentResult(Intent.BOOK.value, 0.82)

        # FAQ = a configured fact matches (facts-from-config only).
        if vertical.faq_answer(text) is not None:
            return IntentResult(Intent.FAQ.value, 0.75)

        if vertical.is_out_of_scope(text):
            return IntentResult(Intent.OUT_OF_SCOPE.value, 0.9)

        # A described problem naming a service implies a booking ("my drain is clogged").
        if vertical.find_service(text) is not None:
            return IntentResult(Intent.BOOK.value, 0.6)

        # Bare greeting only if nothing else matched.
        if any(g in t for g in _GREETINGS) and len(text.split()) <= 4:
            return IntentResult(Intent.GREETING.value, 0.9)

        return IntentResult(Intent.UNKNOWN.value, 0.2)

    def extract_slots(self, text: str, expecting: str | None, vertical: Vertical) -> dict:
        out: dict = {}
        raw = text.strip()
        t = raw.lower()

        svc = vertical.find_service(text)
        if svc is not None:
            out["service_id"] = svc.id
            out["service"] = svc.name

        if any(w in t for w in ("emergency", "urgent", "asap", "right now", "right away", "today", "flooding")):
            out["urgency"] = "emergency"

        phone = _PHONE.search(raw)
        if phone:
            out["contact_phone"] = phone.group(0).strip()

        name_m = _NAME.search(raw)
        if name_m:
            out["contact_name"] = _clean_name(name_m.group(1))

        addr_m = _ADDRESS_LEAD.search(raw)
        if addr_m and expecting == "address":
            out["address"] = addr_m.group(1).strip().rstrip(".")

        # Fallback: a bare answer maps to the field we just asked for.
        if expecting == "contact_name" and "contact_name" not in out:
            cand = _clean_name(raw)
            if cand and not phone and 1 <= len(cand.split()) <= 4:
                out["contact_name"] = cand
        if expecting == "address" and "address" not in out:
            if any(ch.isdigit() for ch in raw) or _looks_like_street(t):
                out["address"] = raw.rstrip(".")
        if expecting == "contact_phone" and "contact_phone" not in out:
            digits = re.sub(r"\D", "", raw)
            if len(digits) >= 10:
                out["contact_phone"] = raw.strip()

        return out

    def interpret_yes_no(self, text: str) -> bool | None:
        t = text.lower()
        if any(p in t for p in _NO_PHRASES):
            return False
        if any(p in t for p in _YES_PHRASES):
            return True
        tokens = set(re.findall(r"[a-z']+", t))
        if tokens & _NO:
            return False
        if tokens & _YES:
            return True
        return None

    def detect_frustration(self, text: str) -> bool:
        t = text.lower()
        return any(cue in t for cue in _FRUSTRATION)

    def select_slot(self, text: str, offered: list[dict]) -> dict | None:
        if not offered:
            return None
        t = text.lower()

        if any(k in t for k in _EARLIEST):
            return offered[0]

        for word, idx in _ORDINALS.items():
            if re.search(rf"\b{re.escape(word)}\b", t):
                if idx < len(offered):
                    return offered[idx]

        m = re.search(r"\b(?:option|number|slot)\s*(\d)\b", t)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(offered):
                return offered[idx]

        # Match a spoken time to an offered slot's hour — but ONLY if that hour is actually offered.
        want = _parse_hour(t)
        if want is not None:
            from datetime import datetime
            for slot in offered:
                if datetime.fromisoformat(slot["start_iso"]).hour == want:
                    return slot
        return None


def _clean_name(s: str) -> str:
    s = re.sub(r"^(?:my name is|this is|i am|i'm|it's|its|name'?s)\s+", "", s.strip(), flags=re.I)
    s = s.strip(" .,!?")
    return " ".join(w.capitalize() for w in s.split())


def _looks_like_street(t: str) -> bool:
    return any(w in t for w in (" st", " street", " ave", " avenue", " rd", " road", " blvd",
                                " lane", " ln", " drive", " dr", " court", " ct", " way"))


def _parse_hour(t: str) -> int | None:
    m = _TIME.search(t)
    if not m:
        return None
    hour = int(m.group(1))
    ampm = (m.group(3) or "").replace(".", "")
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0
    if 0 <= hour <= 23:
        return hour
    return None
