from datetime import datetime

from ringback_agent.agent import Agent
from ringback_agent.config import Settings
from ringback_agent.llm.rulebased import RuleBasedNLU
from ringback_agent.state import ConversationState
from ringback_agent.tools import MockCalendar, MockCRM
from ringback_agent.vertical import load_vertical

# A fixed Monday 7:00 AM so business hours (Mon 08:00-18:00) yield deterministic availability.
FIXED_CLOCK = datetime(2026, 7, 13, 7, 0)


def make_agent(vertical_name="home-services", clock=FIXED_CLOCK, calendar=None):
    v = load_vertical(vertical_name)
    cal = calendar or MockCalendar(v.business_hours, clock=clock)
    return Agent(vertical=v, calendar=cal, crm=MockCRM(), nlu=RuleBasedNLU(), settings=Settings())


def new_state(vertical_name="home-services"):
    return ConversationState(vertical=vertical_name)
