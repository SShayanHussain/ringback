"""Conversation state — serializable so text AND voice can round-trip it turn by turn.

The core is a small state machine (LangGraph *patterns*, no heavy dependency): each turn reads the
state + the user utterance and returns a reply + the next state. Voice sends the exact same payload.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum


class Intent(str, Enum):
    GREETING = "greeting"
    BOOK = "book"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"
    FAQ = "faq"
    QUALIFY = "qualify"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


class Outcome(str, Enum):
    IN_PROGRESS = "in_progress"
    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"
    ANSWERED = "answered"
    QUALIFIED = "qualified"
    ESCALATED = "escalated"


class EscalationMode(str, Enum):
    TRANSFER = "transfer"
    CALLBACK = "callback"


@dataclass
class ConversationState:
    session_id: str = "sess"
    vertical: str = "home-services"
    intent: str | None = None
    slots: dict = field(default_factory=dict)
    # The ONLY slots the agent may book. Populated exclusively from the calendar tool.
    offered_slots: list = field(default_factory=list)
    awaiting_confirmation: bool = False
    pending_action: dict | None = None
    misunderstanding_count: int = 0
    escalated: bool = False
    escalation_reason: str | None = None
    escalation_mode: str | None = None
    outcome: str = Outcome.IN_PROGRESS.value
    actions: list = field(default_factory=list)
    history: list = field(default_factory=list)
    finished: bool = False

    def record_user(self, text: str) -> None:
        self.history.append({"role": "user", "text": text})

    def record_agent(self, text: str) -> None:
        self.history.append({"role": "agent", "text": text})

    def record_action(self, action: dict) -> None:
        self.actions.append(action)

    def reset_flow(self) -> None:
        """Clear an in-flight booking flow (keep identity fields the caller re-supplies)."""
        self.intent = None
        self.offered_slots = []
        self.awaiting_confirmation = False
        self.pending_action = None
        for k in ("service", "service_id", "chosen_slot_iso", "chosen_slot_label", "booking_id"):
            self.slots.pop(k, None)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict | None) -> "ConversationState":
        if not d:
            return cls()
        known = {f: d[f] for f in cls().__dict__ if f in d}
        return cls(**known)
