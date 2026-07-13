"""Hard rule: no state-changing action (book/cancel/reschedule) without an explicit confirmation."""
import pytest

from helpers import make_agent, new_state
from ringback_agent import guardrails
from ringback_agent.state import ConversationState


def test_no_booking_is_written_before_confirmation():
    agent = make_agent()
    st = new_state()
    agent.handle_turn(st, "book a drain cleaning")
    agent.handle_turn(st, "123 Main Street")
    agent.handle_turn(st, "John Smith")
    agent.handle_turn(st, "555-123-4567")
    agent.handle_turn(st, "the first one")

    # Staged, but NOT executed.
    assert st.awaiting_confirmation
    assert not any(a["type"] == "booking_created" for a in st.actions)
    assert len(agent.calendar._bookings) == 0


def test_declining_confirmation_writes_nothing():
    agent = make_agent()
    st = new_state()
    agent.handle_turn(st, "book a drain cleaning")
    agent.handle_turn(st, "123 Main Street")
    agent.handle_turn(st, "John Smith")
    agent.handle_turn(st, "555-123-4567")
    agent.handle_turn(st, "the first one")
    agent.handle_turn(st, "actually, no")

    assert not st.awaiting_confirmation
    assert st.pending_action is None
    assert not any(a["type"] == "booking_created" for a in st.actions)
    assert len(agent.calendar._bookings) == 0


def test_execute_without_confirmation_raises():
    # Defense in depth: the guardrail refuses even if called out of band.
    st = ConversationState()
    st.awaiting_confirmation = False
    st.pending_action = None
    with pytest.raises(guardrails.GuardrailViolation):
        guardrails.assert_confirmed(st)
