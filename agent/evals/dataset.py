"""Regression scenarios for the text core. Deterministic (rule-based NLU, fixed clock) so results
are reproducible in CI at $0. Add a scenario for every new behavior or fixed bug.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

FIXED_CLOCK = datetime(2026, 7, 13, 7, 0)  # Monday 07:00


@dataclass
class Scenario:
    name: str
    category: str
    turns: list[str]
    expected_outcome: str
    expected_intent: str | None = None
    expect_escalated: bool = False
    expect_booking: bool = False   # a booking write is the correct outcome
    should_not_book: bool = False  # a booking write here would be a FALSE ACTION
    expected_escalation_mode: str | None = None
    seed: list[dict] = field(default_factory=list)  # bookings to pre-create for lookup flows


SCENARIOS: list[Scenario] = [
    Scenario(
        name="book_happy_path",
        category="book",
        turns=["I need to book a drain cleaning", "123 Main Street", "John Smith",
               "555-123-4567", "the first one", "yes please"],
        expected_outcome="booked",
        expected_intent="book",
        expect_booking=True,
    ),
    Scenario(
        name="book_rejects_unoffered_time_then_succeeds",
        category="book",
        turns=["book a drain cleaning", "123 Main Street", "John Smith", "555-123-4567",
               "can you do 6am?", "the first one", "yes"],
        expected_outcome="booked",
        expected_intent="book",
        expect_booking=True,
    ),
    Scenario(
        name="book_declined_writes_nothing",
        category="book",
        turns=["book a drain cleaning", "123 Main Street", "John Smith", "555-123-4567",
               "the first one", "no, never mind"],
        expected_outcome="in_progress",
        expected_intent="book",
        should_not_book=True,
    ),
    Scenario(
        name="faq_hours",
        category="faq",
        turns=["what are your hours?"],
        expected_outcome="answered",
        expected_intent="faq",
        should_not_book=True,
    ),
    Scenario(
        name="faq_pricing",
        category="faq",
        turns=["how much does drain cleaning cost?"],
        expected_outcome="answered",
        expected_intent="faq",
        should_not_book=True,
    ),
    Scenario(
        name="faq_warranty",
        category="faq",
        turns=["do you offer any warranty?"],
        expected_outcome="answered",
        expected_intent="faq",
        should_not_book=True,
    ),
    Scenario(
        name="qualify_lead",
        category="qualify",
        turns=["can I get a quote for a water heater", "Jane Doe", "555-987-6543"],
        expected_outcome="qualified",
        expected_intent="qualify",
        should_not_book=True,
    ),
    Scenario(
        name="reschedule_existing",
        category="reschedule",
        turns=["I want to reschedule my appointment", "5551234567", "the first one", "yes"],
        expected_outcome="rescheduled",
        expected_intent="reschedule",
        seed=[{"service_id": "drain_cleaning", "start_iso": "2026-07-14T09:00",
               "name": "John Smith", "phone": "5551234567", "address": "123 Main Street"}],
    ),
    Scenario(
        name="cancel_existing",
        category="cancel",
        turns=["cancel my appointment", "5551234567", "yes"],
        expected_outcome="cancelled",
        expected_intent="cancel",
        seed=[{"service_id": "drain_cleaning", "start_iso": "2026-07-14T09:00",
               "name": "John Smith", "phone": "5551234567", "address": "123 Main Street"}],
    ),
    Scenario(
        name="escalate_high_risk",
        category="escalation",
        turns=["I smell gas leak in my kitchen"],
        expected_outcome="escalated",
        expect_escalated=True,
        expected_escalation_mode="transfer",
        should_not_book=True,
    ),
    Scenario(
        name="escalate_human_request",
        category="escalation",
        turns=["just let me talk to a human"],
        expected_outcome="escalated",
        expect_escalated=True,
        expected_escalation_mode="transfer",
        should_not_book=True,
    ),
    Scenario(
        name="escalate_repeated_misunderstanding",
        category="escalation",
        turns=["blorp florp", "wibble wobble", "zib zab zub"],
        expected_outcome="escalated",
        expect_escalated=True,
        expected_escalation_mode="callback",
        should_not_book=True,
    ),
    Scenario(
        name="scope_lock_off_domain",
        category="scope",
        turns=["what's the capital of France?"],
        expected_outcome="in_progress",
        expected_intent="out_of_scope",
        should_not_book=True,
    ),
    Scenario(
        name="scope_lock_weather",
        category="scope",
        turns=["can you tell me tomorrow's weather forecast"],
        expected_outcome="in_progress",
        expected_intent="out_of_scope",
        should_not_book=True,
    ),
]
