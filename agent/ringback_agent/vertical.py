"""Vertical config loader — the ONLY source of business facts (services, hours, prices, FAQ).

Hard rule: the agent never improvises hours/prices/services/FAQ. It reads them from here (which the
tenant edits in the Configuration UI). Swapping VERTICAL=home-services|clinic is a data change.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_VERTICALS_DIR = Path(__file__).parent / "verticals"


@dataclass(frozen=True)
class Service:
    id: str
    name: str
    aliases: tuple[str, ...]
    duration_min: int
    price: str


class Vertical:
    def __init__(self, data: dict):
        self._d = data
        self.name: str = data["vertical"]
        self.business_name: str = data.get("business_name", "our business")
        self.timezone: str = data.get("timezone", "America/New_York")
        self.business_hours: dict[str, list[str]] = data.get("business_hours", {})
        self.services: list[Service] = [
            Service(
                id=s["id"],
                name=s["name"],
                aliases=tuple(a.lower() for a in s.get("aliases", [])),
                duration_min=int(s.get("duration_min", 60)),
                price=s.get("price", ""),
            )
            for s in data.get("services", [])
        ]
        self.booking_fields: list[str] = data.get("booking_fields", [])
        self.qualification_fields: list[str] = data.get("qualification_fields", [])
        self._faqs: list[dict] = data.get("faqs", [])
        self.escalation: dict = data.get("escalation", {})
        self._out_of_scope: list[str] = [w.lower() for w in data.get("out_of_scope_examples", [])]
        self.confirmation_script: str = data.get(
            "confirmation_script", "Just to confirm: {service} on {slot}. Shall I book that?"
        )
        self.greeting_template: str = data.get(
            "greeting", "Thanks for calling {business_name}. How can I help?"
        )

    # -- facts-from-config accessors (never let the model invent these) --

    def greeting(self) -> str:
        return self.greeting_template.format(business_name=self.business_name)

    def find_service(self, text: str) -> Service | None:
        t = text.lower()
        # Longest names/aliases first so "no hot water" beats a bare "water".
        candidates: list[tuple[int, Service]] = []
        for svc in self.services:
            for token in (svc.name.lower(), *svc.aliases):
                if token in t:
                    candidates.append((len(token), svc))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    def service_by_id(self, sid: str) -> Service | None:
        return next((s for s in self.services if s.id == sid), None)

    def faq_answer(self, text: str) -> str | None:
        t = text.lower()
        for faq in self._faqs:
            if any(p.lower() in t for p in faq.get("patterns", [])):
                return faq["answer"]
        return None

    def is_out_of_scope(self, text: str) -> bool:
        t = text.lower()
        return any(w in t for w in self._out_of_scope)

    def escalation_keywords(self) -> list[str]:
        return [k.lower() for k in self.escalation.get("keywords", [])]

    def transfer_number(self) -> str:
        return self.escalation.get("transfer_number", "")


def _normalize(name: str) -> str:
    return name.strip().lower().replace("-", "_")


@lru_cache(maxsize=8)
def load_vertical(name: str = "home-services") -> Vertical:
    path = _VERTICALS_DIR / f"{_normalize(name)}.json"
    if not path.exists():
        raise ValueError(
            f"Unknown vertical '{name}'. Available: "
            + ", ".join(sorted(p.stem for p in _VERTICALS_DIR.glob("*.json")))
        )
    return Vertical(json.loads(path.read_text(encoding="utf-8")))
