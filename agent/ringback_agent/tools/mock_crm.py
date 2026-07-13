"""In-memory mock CRM. Phase 2 swaps this for a real CRM or (per DECISIONS.md) an n8n webhook that
does the CRM write + staff notification. The agent core only depends on the CRMProvider interface.
"""
from __future__ import annotations


class MockCRM:
    def __init__(self):
        self._contacts: dict[str, dict] = {}
        self._interactions: list[dict] = []
        self._counter = 0

    def upsert_contact(self, name: str, phone: str, address: str = "", notes: str = "") -> str:
        key = _digits(phone) or name.lower()
        existing = next((cid for cid, c in self._contacts.items() if c["key"] == key), None)
        if existing:
            self._contacts[existing].update(
                {"name": name or self._contacts[existing]["name"], "address": address or self._contacts[existing]["address"]}
            )
            return existing
        self._counter += 1
        cid = f"ct_{self._counter:04d}"
        self._contacts[cid] = {"key": key, "name": name, "phone": phone, "address": address, "notes": notes}
        return cid

    def log_interaction(self, contact_id: str, summary: str, outcome: str) -> None:
        self._interactions.append({"contact_id": contact_id, "summary": summary, "outcome": outcome})


def _digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())
