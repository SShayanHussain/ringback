"""Calendar / CRM behind interfaces so they are mockable in text mode and swappable in prod.

Phase 2 replaces MockCalendar/MockCRM with Google/Outlook + a real CRM (or an n8n webhook) without
touching the agent logic. The interface is the contract the guardrails rely on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Slot:
    start_iso: str  # ISO-8601 datetime (the machine value the guardrail checks)
    label: str      # human phrasing the agent speaks, e.g. "Tomorrow (Tue) 9:00 AM"

    def as_dict(self) -> dict:
        return {"start_iso": self.start_iso, "label": self.label}


@dataclass
class Booking:
    id: str
    service_id: str
    start_iso: str
    contact_name: str
    contact_phone: str
    address: str = ""
    status: str = "confirmed"
    extra: dict = field(default_factory=dict)


@runtime_checkable
class CalendarProvider(Protocol):
    def get_availability(
        self, service_id: str, duration_min: int, count: int = 3, now=None
    ) -> list[Slot]: ...

    def create_booking(
        self, service_id: str, start_iso: str, contact_name: str, contact_phone: str, address: str = ""
    ) -> Booking: ...

    def modify_booking(self, booking_id: str, new_start_iso: str) -> Booking: ...

    def cancel_booking(self, booking_id: str) -> bool: ...

    def find_bookings(
        self, contact_phone: str | None = None, contact_name: str | None = None
    ) -> list[Booking]: ...


@runtime_checkable
class CRMProvider(Protocol):
    def upsert_contact(
        self, name: str, phone: str, address: str = "", notes: str = ""
    ) -> str: ...

    def log_interaction(self, contact_id: str, summary: str, outcome: str) -> None: ...
