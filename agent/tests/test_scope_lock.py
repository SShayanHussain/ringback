"""Scope lock: off-domain requests are refused/transferred, never improvised — and never touch tools."""
from helpers import make_agent, new_state


def test_off_domain_request_is_refused_and_calls_no_tools():
    agent = make_agent()
    st = new_state()
    r = agent.handle_turn(st, "what's the weather forecast for tomorrow?")
    assert st.outcome != "booked"
    assert len(agent.calendar._bookings) == 0
    assert not any(a.get("type") == "booking_created" for a in st.actions)
    assert "outside what i can help with" in r.reply.lower()


def test_reschedule_then_cancel_via_lookup():
    agent = make_agent()
    # Seed an existing booking to look up.
    agent.calendar.create_booking(
        "drain_cleaning", "2026-07-14T09:00", "John Smith", "5551234567", "123 Main Street"
    )
    st = new_state()
    agent.handle_turn(st, "I need to cancel my appointment")
    agent.handle_turn(st, "5551234567")           # look up by phone
    assert st.awaiting_confirmation
    agent.handle_turn(st, "yes")
    assert st.outcome == "cancelled"
    assert agent.calendar.find_bookings(contact_phone="5551234567") == []
