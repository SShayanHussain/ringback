"""Happy path: a full booking end to end, driven by the deterministic rule-based NLU."""
from helpers import make_agent, new_state


def test_book_happy_path_creates_a_booking():
    agent = make_agent()
    st = new_state()

    agent.handle_turn(st, "I need to book a drain cleaning")
    assert st.slots.get("service_id") == "drain_cleaning"

    agent.handle_turn(st, "123 Main Street")
    assert st.slots.get("address")

    agent.handle_turn(st, "John Smith")
    assert st.slots.get("contact_name") == "John Smith"

    agent.handle_turn(st, "555-123-4567")
    assert st.slots.get("contact_phone")

    # All fields collected → real availability offered.
    assert st.offered_slots, "the calendar tool should have offered real slots"

    r = agent.handle_turn(st, "the first one")
    assert st.awaiting_confirmation, "must ask for confirmation before writing"
    assert "confirm" in r.reply.lower() or "shall i book" in r.reply.lower()

    r = agent.handle_turn(st, "yes please")
    assert st.outcome == "booked"
    assert any(a["type"] == "booking_created" for a in st.actions)
    assert not st.awaiting_confirmation


def test_faq_answer_comes_from_config_not_the_model():
    agent = make_agent()
    st = new_state()
    r = agent.handle_turn(st, "what are your hours?")
    # The exact fact must come from the vertical config (facts-from-tools rule).
    assert "8am" in r.reply and "6pm" in r.reply
    assert st.outcome == "answered"


def test_clinic_vertical_switches_by_config():
    agent = make_agent(vertical_name="clinic")
    st = new_state("clinic")
    agent.handle_turn(st, "I'd like to book a follow-up")
    assert st.slots.get("service_id") == "follow_up"
    # Clinic booking_fields have no address; next question is the name.
    r = agent.handle_turn(st, "Jane Doe")
    assert st.slots.get("contact_name") == "Jane Doe"
    assert "address" not in r.reply.lower()
