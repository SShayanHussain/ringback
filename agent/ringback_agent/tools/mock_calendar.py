"""Deterministic mock calendar. Availability is generated from business hours + a seeded busy set.

CRITICAL: this is the single source of truth for what slots exist. The agent may only ever offer
what get_availability() returns, and the guardrail (guardrails.assert_slot_offered) enforces it at
the booking boundary. There is no path that fabricates a slot.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta

from .base import Booking, Slot

_WD = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_hm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


class MockCalendar:
    def __init__(
        self,
        business_hours: dict[str, list[str]],
        busy: set[tuple[str, int]] | None = None,
        clock: datetime | None = None,
    ):
        self.business_hours = business_hours
        # busy = set of (date_iso, hour) that are already booked/blocked.
        self._busy: set[tuple[str, int]] = set(busy or set())
        self._clock = clock
        self._bookings: dict[str, Booking] = {}
        self._counter = 0

    def _now(self) -> datetime:
        return self._clock or datetime.now()

    def get_availability(
        self, service_id: str, duration_min: int, count: int = 3, now=None
    ) -> list[Slot]:
        now = now or self._now()
        cursor = now.replace(minute=0, second=0, microsecond=0)
        if now.minute or now.second or now.microsecond:
            cursor += timedelta(hours=1)
        limit = now + timedelta(days=14)
        slots: list[Slot] = []
        while cursor < limit and len(slots) < count:
            hrs = self.business_hours.get(_WD[cursor.weekday()], [])
            if hrs:
                open_dt = datetime.combine(cursor.date(), _parse_hm(hrs[0]))
                close_dt = datetime.combine(cursor.date(), _parse_hm(hrs[1]))
                slot_end = cursor + timedelta(minutes=duration_min)
                key = (cursor.date().isoformat(), cursor.hour)
                if cursor >= now and open_dt <= cursor and slot_end <= close_dt and key not in self._busy:
                    slots.append(Slot(cursor.isoformat(timespec="minutes"), _fmt_label(cursor, now)))
            cursor += timedelta(hours=1)
        return slots

    def create_booking(
        self, service_id: str, start_iso: str, contact_name: str, contact_phone: str, address: str = ""
    ) -> Booking:
        self._counter += 1
        bid = f"bk_{self._counter:04d}"
        booking = Booking(
            id=bid,
            service_id=service_id,
            start_iso=start_iso,
            contact_name=contact_name,
            contact_phone=contact_phone,
            address=address,
        )
        self._bookings[bid] = booking
        # Mark the hour busy so it isn't offered again.
        dt = datetime.fromisoformat(start_iso)
        self._busy.add((dt.date().isoformat(), dt.hour))
        return booking

    def modify_booking(self, booking_id: str, new_start_iso: str) -> Booking:
        booking = self._bookings[booking_id]
        old = datetime.fromisoformat(booking.start_iso)
        self._busy.discard((old.date().isoformat(), old.hour))
        booking.start_iso = new_start_iso
        nd = datetime.fromisoformat(new_start_iso)
        self._busy.add((nd.date().isoformat(), nd.hour))
        return booking

    def cancel_booking(self, booking_id: str) -> bool:
        booking = self._bookings.get(booking_id)
        if not booking:
            return False
        booking.status = "cancelled"
        dt = datetime.fromisoformat(booking.start_iso)
        self._busy.discard((dt.date().isoformat(), dt.hour))
        return True

    def find_bookings(
        self, contact_phone: str | None = None, contact_name: str | None = None
    ) -> list[Booking]:
        out = []
        for b in self._bookings.values():
            if b.status != "confirmed":
                continue
            if contact_phone and _digits(contact_phone) == _digits(b.contact_phone):
                out.append(b)
            elif contact_name and contact_name.lower() == b.contact_name.lower():
                out.append(b)
        return out


def _fmt_label(dt: datetime, now: datetime) -> str:
    days = (dt.date() - now.date()).days
    if days == 0:
        day = "Today"
    elif days == 1:
        day = "Tomorrow"
    else:
        day = dt.strftime("%A")
    # %-I is not portable to Windows; format 12-hour manually.
    hour12 = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{day} {hour12}:{dt.minute:02d} {ampm}"


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())
