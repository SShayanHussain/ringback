"""Per-call log record (PRD §7). Every call logs: transcript, intent, actions, outcome, latency,
cost. In text mode latency/cost are ~0; the voice layer (Phase 5) fills in real turn latency and
per-minute cost. The orchestrator persists this to Postgres, tenant-scoped.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from .state import ConversationState


@dataclass
class CallLog:
    session_id: str
    vertical: str
    channel: str = "text"  # text | voice
    intent: str | None = None
    outcome: str = "in_progress"
    escalated: bool = False
    escalation_reason: str | None = None
    transcript: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    turn_latency_ms: list = field(default_factory=list)  # per-turn; voice fills these
    cost_usd: float = 0.0

    @classmethod
    def from_state(cls, state: ConversationState, channel: str = "text") -> "CallLog":
        return cls(
            session_id=state.session_id,
            vertical=state.vertical,
            channel=channel,
            intent=state.intent,
            outcome=state.outcome,
            escalated=state.escalated,
            escalation_reason=state.escalation_reason,
            transcript=list(state.history),
            actions=list(state.actions),
        )

    def to_dict(self) -> dict:
        return asdict(self)
