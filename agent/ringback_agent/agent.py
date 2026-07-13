"""The conversation core - a small deterministic state machine (LangGraph *patterns*, no heavy dep).

handle_turn(state, user_text) -> TurnResult. Text and voice both call this exact function. Every
state-changing action passes through guardrails (confirmation + slot-was-offered) before any tool
write. Facts come only from the vertical config via tools.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from . import escalation, guardrails
from .config import Settings, get_settings
from .llm import build_nlu
from .state import ConversationState, EscalationMode, Intent, Outcome
from .tools import CalendarProvider, CRMProvider, MockCalendar, MockCRM
from .vertical import Vertical, load_vertical

_FIELD_PROMPTS = {
    "address": "What's the service address?",
    "contact_name": "And your name?",
    "contact_phone": "What's the best phone number to reach you?",
}


@dataclass
class TurnResult:
    reply: str
    state: ConversationState
    intent: str | None = None
    confidence: float = 1.0
    escalated: bool = False
    outcome: str = Outcome.IN_PROGRESS.value
    actions: list = field(default_factory=list)


class Agent:
    def __init__(
        self,
        vertical: Vertical | None = None,
        calendar: CalendarProvider | None = None,
        crm: CRMProvider | None = None,
        nlu=None,
        settings: Settings | None = None,
    ):
        self.settings = settings or get_settings()
        self.vertical = vertical or load_vertical(self.settings.vertical)
        self.calendar = calendar or MockCalendar(self.vertical.business_hours)
        self.crm = crm or MockCRM()
        self.nlu = nlu or build_nlu(self.settings)

    # ------------------------------------------------------------------ public
    def handle_turn(self, state: ConversationState, user_text: str) -> TurnResult:
        state.record_user(user_text)
        n_actions = len(state.actions)

        # 1) Escalation short-circuits everything (high-risk / frustration / repeated misunderstanding).
        esc = escalation.evaluate(
            user_text, self.vertical, state, self.nlu, self.settings.max_misunderstandings
        )
        if esc.should:
            return self._finish(state, self._do_escalate(state, esc), n_actions,
                                 intent=state.intent, escalated=True)

        # 2) Awaiting a spoken confirmation for a pending write.
        if state.awaiting_confirmation:
            return self._handle_confirmation(state, user_text, n_actions)

        # 3) Continue an in-flight flow.
        if state.intent in (Intent.BOOK.value, Intent.RESCHEDULE.value,
                            Intent.CANCEL.value, Intent.QUALIFY.value) and not state.finished:
            return self._continue_flow(state, user_text, n_actions)

        # 4) Fresh classification.
        ir = self.nlu.classify_intent(user_text, self.vertical, state)
        if ir.intent == Intent.GREETING.value:
            return self._finish(state, self.vertical.greeting(), n_actions, intent=ir.intent,
                                confidence=ir.confidence)
        if ir.intent == Intent.FAQ.value:
            return self._do_faq(state, user_text, n_actions, ir.confidence)
        if ir.intent == Intent.OUT_OF_SCOPE.value:
            return self._do_out_of_scope(state, n_actions, ir.confidence)
        if ir.intent in (Intent.BOOK.value, Intent.RESCHEDULE.value,
                        Intent.CANCEL.value, Intent.QUALIFY.value):
            state.intent = ir.intent
            state.finished = False
            return self._continue_flow(state, user_text, n_actions, confidence=ir.confidence)

        # UNKNOWN → clarify once; the misunderstanding counter drives eventual escalation.
        state.misunderstanding_count += 1
        reply = ("I can help you book, reschedule or cancel a visit, or answer a question about our "
                 "services. What would you like to do?")
        return self._finish(state, reply, n_actions, intent=Intent.UNKNOWN.value,
                            confidence=ir.confidence)

    # ------------------------------------------------------------- confirmation
    def _handle_confirmation(self, state: ConversationState, user_text: str, n_actions: int) -> TurnResult:
        ans = self.nlu.interpret_yes_no(user_text)
        if ans is True:
            return self._execute_pending(state, n_actions)
        if ans is False:
            state.awaiting_confirmation = False
            state.pending_action = None
            state.slots.pop("chosen_slot_iso", None)
            state.slots.pop("chosen_slot_label", None)
            reply = "No problem, I won't do that. Would you like a different time, or anything else?"
            return self._finish(state, reply, n_actions, intent=state.intent)
        state.misunderstanding_count += 1
        reply = "Sorry, I didn't catch that. Should I go ahead? Please say yes or no."
        return self._finish(state, reply, n_actions, intent=state.intent)

    def _execute_pending(self, state: ConversationState, n_actions: int) -> TurnResult:
        guardrails.assert_confirmed(state)  # wired-in safety check (no write without confirmation)
        action = state.pending_action or {}
        atype = action.get("type")

        if atype == "create_booking":
            guardrails.assert_slot_offered(action["start_iso"], state.offered_slots)
            b = self.calendar.create_booking(
                action["service_id"], action["start_iso"], action["contact_name"],
                action["contact_phone"], action.get("address", ""),
            )
            state.record_action({"type": "booking_created", "booking_id": b.id,
                                 "service_id": b.service_id, "start_iso": b.start_iso})
            self._crm_log(action["contact_name"], action["contact_phone"],
                          action.get("address", ""), f"Booked {action['service']}", "booked")
            outcome = Outcome.BOOKED.value
            reply = (f"Done - you're booked for {action['service']} on {action['slot_label']}. "
                     f"We'll see you then. Anything else?")
        elif atype == "modify_booking":
            guardrails.assert_slot_offered(action["start_iso"], state.offered_slots)
            self.calendar.modify_booking(action["booking_id"], action["start_iso"])
            state.record_action({"type": "booking_modified", "booking_id": action["booking_id"],
                                 "start_iso": action["start_iso"]})
            outcome = Outcome.RESCHEDULED.value
            reply = f"All set - your {action['service']} is moved to {action['slot_label']}. Anything else?"
        elif atype == "cancel_booking":
            self.calendar.cancel_booking(action["booking_id"])
            state.record_action({"type": "booking_cancelled", "booking_id": action["booking_id"]})
            outcome = Outcome.CANCELLED.value
            reply = f"Your {action['service']} on {action['slot_label']} is cancelled. Anything else?"
        else:
            raise guardrails.GuardrailViolation(f"Unknown pending action type: {atype!r}")

        state.awaiting_confirmation = False
        state.pending_action = None
        state.outcome = outcome
        state.finished = True
        return self._finish(state, reply, n_actions, intent=state.intent, outcome=outcome)

    # -------------------------------------------------------------------- flows
    def _continue_flow(self, state, user_text, n_actions, confidence: float = 1.0) -> TurnResult:
        if state.intent == Intent.BOOK.value:
            return self._book(state, user_text, n_actions, confidence)
        if state.intent == Intent.QUALIFY.value:
            return self._qualify(state, user_text, n_actions, confidence)
        if state.intent in (Intent.RESCHEDULE.value, Intent.CANCEL.value):
            return self._reschedule_or_cancel(state, user_text, n_actions, confidence)
        raise ValueError(f"no flow for intent {state.intent}")

    def _book(self, state, user_text, n_actions, confidence) -> TurnResult:
        expecting = state.slots.pop("_expecting", None)
        state.slots.update(self.nlu.extract_slots(user_text, expecting, self.vertical))

        # a) collect required fields one at a time
        missing = [f for f in self.vertical.booking_fields if not self._has_field(state, f)]
        if missing:
            fld = missing[0]
            if fld == "service":
                return self._ask_service(state, n_actions, confidence)
            state.slots["_expecting"] = fld
            return self._finish(state, _FIELD_PROMPTS[fld], n_actions,
                                intent=state.intent, confidence=confidence)

        # b) offer real availability (only what the calendar returns)
        if not state.offered_slots:
            return self._offer_slots(state, state.slots["service_id"], n_actions, confidence)

        # c) interpret the caller's slot selection
        chosen = self.nlu.select_slot(user_text, state.offered_slots)
        if not chosen:
            state.misunderstanding_count += 1
            reply = ("That time isn't one of the openings. Here are the options again: "
                     + self._present_slots(state.offered_slots))
            return self._finish(state, reply, n_actions, intent=state.intent)

        # d) stage the write + ask for spoken confirmation
        svc = self.vertical.service_by_id(state.slots["service_id"])
        state.pending_action = {
            "type": "create_booking",
            "service_id": svc.id,
            "service": svc.name,
            "start_iso": chosen["start_iso"],
            "slot_label": chosen["label"],
            "contact_name": state.slots.get("contact_name", ""),
            "contact_phone": state.slots.get("contact_phone", ""),
            "address": state.slots.get("address", ""),
        }
        state.awaiting_confirmation = True
        return self._finish(state, self._confirm_text(svc.name, chosen["label"], state.slots),
                            n_actions, intent=state.intent)

    def _reschedule_or_cancel(self, state, user_text, n_actions, confidence) -> TurnResult:
        # look up the existing booking by phone
        if not state.slots.get("booking_id"):
            expecting = state.slots.pop("_expecting", None)
            state.slots.update(self.nlu.extract_slots(user_text, expecting, self.vertical))
            phone = state.slots.get("contact_phone")
            if not phone:
                state.slots["_expecting"] = "contact_phone"
                return self._finish(state, "Sure - what's the phone number on the appointment?",
                                    n_actions, intent=state.intent, confidence=confidence)
            bookings = self.calendar.find_bookings(contact_phone=phone)
            if not bookings:
                state.reset_flow()
                reply = ("I don't see an appointment under that number. I can book a new visit, or "
                         "connect you with someone - which would you prefer?")
                return self._finish(state, reply, n_actions, intent=None)
            b = bookings[0]
            svc = self.vertical.service_by_id(b.service_id)
            state.slots["booking_id"] = b.id
            state.slots["service_id"] = b.service_id
            state.slots["service"] = svc.name if svc else b.service_id
            state.slots["existing_start"] = b.start_iso

        svc_name = state.slots.get("service", "appointment")

        if state.intent == Intent.CANCEL.value:
            state.pending_action = {
                "type": "cancel_booking",
                "booking_id": state.slots["booking_id"],
                "service": svc_name,
                "slot_label": _pretty(state.slots["existing_start"]),
            }
            state.awaiting_confirmation = True
            reply = f"Just to confirm, cancel your {svc_name} on {_pretty(state.slots['existing_start'])}?"
            return self._finish(state, reply, n_actions, intent=state.intent)

        # reschedule: offer new slots, then select, then confirm
        if not state.offered_slots:
            return self._offer_slots(state, state.slots["service_id"], n_actions, confidence,
                                     lead="Here's what's open: ")
        chosen = self.nlu.select_slot(user_text, state.offered_slots)
        if not chosen:
            state.misunderstanding_count += 1
            return self._finish(state, "Which of these works? " + self._present_slots(state.offered_slots),
                                n_actions, intent=state.intent)
        state.pending_action = {
            "type": "modify_booking",
            "booking_id": state.slots["booking_id"],
            "service": svc_name,
            "start_iso": chosen["start_iso"],
            "slot_label": chosen["label"],
        }
        state.awaiting_confirmation = True
        reply = f"Just to confirm, move your {svc_name} to {chosen['label']}?"
        return self._finish(state, reply, n_actions, intent=state.intent)

    def _qualify(self, state, user_text, n_actions, confidence) -> TurnResult:
        expecting = state.slots.pop("_expecting", None)
        state.slots.update(self.nlu.extract_slots(user_text, expecting, self.vertical))
        for fld in ("service", "contact_name", "contact_phone"):
            if not self._has_field(state, fld):
                if fld == "service":
                    return self._ask_service(state, n_actions, confidence)
                state.slots["_expecting"] = fld
                return self._finish(state, _FIELD_PROMPTS[fld], n_actions,
                                    intent=state.intent, confidence=confidence)
        svc = self.vertical.service_by_id(state.slots["service_id"])
        self._crm_log(state.slots.get("contact_name", ""), state.slots["contact_phone"],
                      state.slots.get("address", ""), f"Quote request: {svc.name}", "qualified")
        state.outcome = Outcome.QUALIFIED.value
        state.finished = True
        price = f" Pricing for {svc.name} is {svc.price}." if svc.price else ""
        reply = (f"Thanks! I've noted your interest in {svc.name} and a team member can follow up."
                 f"{price} Would you like me to book a visit now?")
        return self._finish(state, reply, n_actions, intent=state.intent, outcome=state.outcome)

    # ----------------------------------------------------------------- helpers
    def _ask_service(self, state, n_actions, confidence) -> TurnResult:
        examples = ", ".join(s.name for s in self.vertical.services[:3])
        state.slots["_expecting"] = "service"
        return self._finish(state, f"What do you need help with - for example {examples}?",
                            n_actions, intent=state.intent, confidence=confidence)

    def _offer_slots(self, state, service_id, n_actions, confidence, lead="") -> TurnResult:
        svc = self.vertical.service_by_id(service_id)
        slots = self.calendar.get_availability(service_id, svc.duration_min if svc else 60, count=3)
        if not slots:
            # Never fabricate. No availability => offer a callback (context preserved).
            state.escalated = True
            state.escalation_reason = "no availability"
            state.escalation_mode = EscalationMode.CALLBACK.value
            state.outcome = Outcome.ESCALATED.value
            state.finished = True
            reply = ("I don't have any openings coming up for that. Let me have someone call you back "
                     "to find a time - what's the best number?")
            return self._finish(state, reply, n_actions, intent=state.intent,
                                escalated=True, outcome=Outcome.ESCALATED.value)
        state.offered_slots = [s.as_dict() for s in slots]
        reply = (lead or "Here's what's available: ") + self._present_slots(state.offered_slots) + " Which works best?"
        return self._finish(state, reply, n_actions, intent=state.intent, confidence=confidence)

    def _do_faq(self, state, user_text, n_actions, confidence) -> TurnResult:
        answer = self.vertical.faq_answer(user_text)  # facts from config ONLY
        if answer is None:
            return self._do_out_of_scope(state, n_actions, confidence)
        state.record_action({"type": "faq_answered"})
        state.outcome = Outcome.ANSWERED.value
        return self._finish(state, answer + " Anything else I can help with?", n_actions,
                            intent=Intent.FAQ.value, outcome=Outcome.ANSWERED.value, confidence=confidence)

    def _do_out_of_scope(self, state, n_actions, confidence) -> TurnResult:
        reply = ("That's outside what I can help with here - I handle booking, rescheduling, and "
                 "questions about our services. I can connect you with a team member if you'd like. "
                 "Otherwise, how can I help with an appointment?")
        return self._finish(state, reply, n_actions, intent=Intent.OUT_OF_SCOPE.value,
                            confidence=confidence)

    def _do_escalate(self, state, esc: escalation.EscalationDecision) -> str:
        state.escalated = True
        state.escalation_reason = esc.reason
        state.escalation_mode = esc.mode
        state.outcome = Outcome.ESCALATED.value
        state.finished = True
        state.record_action({"type": "escalation", "reason": esc.reason, "mode": esc.mode})
        if esc.mode == EscalationMode.TRANSFER.value:
            num = self.vertical.transfer_number()
            tail = f" (transferring you now{f' to {num}' if num else ''})" if num else ""
            return ("I want to make sure this is handled properly, so I'm connecting you with a "
                    f"team member{tail}. Please hold.")
        return ("I'll have a team member call you back with all of this context. What's the best "
                "number and time to reach you?")

    def _confirm_text(self, service: str, slot_label: str, slots: dict) -> str:
        sd = defaultdict(str, {
            "service": service,
            "slot": slot_label,
            "address": slots.get("address", ""),
            "contact_name": slots.get("contact_name", ""),
        })
        try:
            return self.vertical.confirmation_script.format_map(sd)
        except (KeyError, IndexError):
            return f"Just to confirm: {service} on {slot_label}. Shall I book that?"

    def _present_slots(self, offered: list[dict]) -> str:
        return "  ".join(f"{i + 1}) {s['label']}" for i, s in enumerate(offered)) + "."

    def _has_field(self, state, field: str) -> bool:
        if field == "service":
            return bool(state.slots.get("service_id"))
        return bool(state.slots.get(field))

    def _crm_log(self, name, phone, address, summary, outcome) -> None:
        try:
            cid = self.crm.upsert_contact(name=name, phone=phone, address=address)
            self.crm.log_interaction(cid, summary, outcome)
        except Exception:  # noqa: BLE001 - CRM is glue; never fail the call on it (fires via n8n in prod)
            pass

    def _finish(self, state, reply, n_actions, *, intent=None, confidence=1.0,
                escalated=False, outcome=None) -> TurnResult:
        state.record_agent(reply)
        return TurnResult(
            reply=reply,
            state=state,
            intent=intent if intent is not None else state.intent,
            confidence=confidence,
            escalated=escalated or state.escalated,
            outcome=outcome or state.outcome,
            actions=state.actions[n_actions:],
        )


def _pretty(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    hour12 = dt.hour % 12 or 12
    ampm = "AM" if dt.hour < 12 else "PM"
    return f"{dt.strftime('%a %b %d')} {hour12}:{dt.minute:02d} {ampm}"
