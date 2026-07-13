"""Hard rule: NEVER fabricate availability. Only slots the calendar tool returns can be booked."""
import pytest

from helpers import FIXED_CLOCK, make_agent, new_state
from ringback_agent import guardrails
from ringback_agent.tools import MockCalendar


def _drive_to_selection(agent, st):
    agent.handle_turn(st, "I need to book a drain cleaning")
    agent.handle_turn(st, "123 Main Street")
    agent.handle_turn(st, "John Smith")
    agent.handle_turn(st, "555-123-4567")
    assert st.offered_slots


def test_asking_for_an_unoffered_time_does_not_book():
    agent = make_agent()
    st = new_state()
    _drive_to_selection(agent, st)

    offered_hours = {int(s["start_iso"][11:13]) for s in st.offered_slots}
    assert 6 not in offered_hours, "6am is before opening; it must never be offered"

    r = agent.handle_turn(st, "can you do 6am?")
    assert not st.awaiting_confirmation
    assert not any(a["type"] == "booking_created" for a in st.actions)
    assert "isn't one of the openings" in r.reply or "options again" in r.reply


def test_guardrail_blocks_a_fabricated_slot_at_the_write_boundary():
    agent = make_agent()
    st = new_state()
    _drive_to_selection(agent, st)

    # Simulate a bug/injection that stages a slot the tool never offered.
    st.awaiting_confirmation = True
    st.pending_action = {
        "type": "create_booking",
        "service_id": "drain_cleaning",
        "service": "drain cleaning",
        "start_iso": "2026-07-13T06:00",  # 6am — not in offered_slots
        "slot_label": "Today 6:00 AM",
        "contact_name": "John Smith",
        "contact_phone": "5551234567",
        "address": "123 Main Street",
    }
    with pytest.raises(guardrails.GuardrailViolation):
        agent.handle_turn(st, "yes")

    # No booking was written despite the confirmation.
    assert not any(a["type"] == "booking_created" for a in st.actions)


def test_no_availability_offers_callback_never_a_made_up_slot():
    # A calendar with no business hours returns zero slots (hermetic: no shared-state mutation).
    agent = make_agent(calendar=MockCalendar({}, clock=FIXED_CLOCK))
    st = new_state()
    agent.handle_turn(st, "book a drain cleaning")
    agent.handle_turn(st, "123 Main Street")
    agent.handle_turn(st, "John Smith")
    r = agent.handle_turn(st, "555-123-4567")
    assert st.offered_slots == []
    assert st.escalated and st.outcome == "escalated"
    assert "call you back" in r.reply.lower()
