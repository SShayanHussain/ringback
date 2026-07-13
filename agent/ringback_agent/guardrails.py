"""Hard guardrails, wired directly into the ONLY code path that performs a write (agent._execute_*).

PLAYBOOK Golden Rule 3: a safety check that is written but never called is worthless. These raise
on misuse (defense in depth) so any future code path that tries to write without satisfying them
fails loudly instead of silently booking the wrong thing.
"""
from __future__ import annotations

from .state import ConversationState

STATE_CHANGING = {"create_booking", "modify_booking", "cancel_booking"}


class GuardrailViolation(Exception):
    """Raised when a state-changing action is attempted without its precondition satisfied."""


def is_state_changing(action_type: str) -> bool:
    return action_type in STATE_CHANGING


def slot_is_offered(start_iso: str, offered: list[dict]) -> bool:
    return any(s.get("start_iso") == start_iso for s in offered)


def assert_slot_offered(start_iso: str, offered: list[dict]) -> None:
    """NEVER fabricate availability: a booking may only use a slot the calendar tool offered."""
    if not slot_is_offered(start_iso, offered):
        raise GuardrailViolation(
            f"Refusing to book {start_iso!r}: it was never offered by the calendar tool. "
            f"Offered={[s.get('start_iso') for s in offered]}"
        )


def assert_confirmed(state: ConversationState) -> None:
    """No state-changing write without an explicit confirmation turn (HITL-for-voice)."""
    if not state.awaiting_confirmation or not state.pending_action:
        raise GuardrailViolation(
            "Refusing a state-changing action without a pending, spoken confirmation."
        )
