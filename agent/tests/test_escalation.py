"""Escalation triggers: high-risk request, frustration/human request, repeated misunderstanding."""
from helpers import make_agent, new_state


def test_high_risk_keyword_transfers():
    agent = make_agent()
    st = new_state()
    r = agent.handle_turn(st, "I think there's a gas leak in my kitchen")
    assert st.escalated
    assert st.escalation_mode == "transfer"
    assert st.outcome == "escalated"
    assert any(a["type"] == "escalation" for a in st.actions)
    assert "team member" in r.reply.lower() or "connect" in r.reply.lower()


def test_explicit_human_request_escalates():
    agent = make_agent()
    st = new_state()
    agent.handle_turn(st, "let me talk to a human please")
    assert st.escalated


def test_no_tool_write_happens_on_escalation():
    agent = make_agent()
    st = new_state()
    agent.handle_turn(st, "there is flooding and someone got hurt")
    assert st.escalated
    assert len(agent.calendar._bookings) == 0


def test_repeated_misunderstanding_escalates_to_callback():
    agent = make_agent()
    st = new_state()
    agent.handle_turn(st, "blorp florp")
    agent.handle_turn(st, "wibble wobble")
    r = agent.handle_turn(st, "zib zab zub")
    assert st.escalated
    assert st.escalation_mode == "callback"
    assert "call you back" in r.reply.lower()
