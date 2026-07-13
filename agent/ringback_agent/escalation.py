"""Escalation triggers → warm transfer / scheduled callback WITH context.

Triggers (PRD §6): high-risk request · caller frustration / explicit human request · repeated
misunderstanding. (Out-of-scope is handled as a scope-lock refusal in routing; low ASR confidence
is a voice-layer signal added in Phase 5.)
"""
from __future__ import annotations

from dataclasses import dataclass

from .state import ConversationState
from .vertical import Vertical


@dataclass
class EscalationDecision:
    should: bool
    reason: str = ""
    mode: str = "transfer"  # transfer | callback


def evaluate(
    text: str,
    vertical: Vertical,
    state: ConversationState,
    nlu,
    max_misunderstandings: int,
) -> EscalationDecision:
    t = text.lower()

    for kw in vertical.escalation_keywords():
        if kw in t:
            return EscalationDecision(True, f"high-risk request (matched '{kw}')", "transfer")

    if nlu.detect_frustration(text):
        return EscalationDecision(True, "caller frustration / explicit request for a human", "transfer")

    if state.misunderstanding_count >= max_misunderstandings:
        return EscalationDecision(True, "repeated misunderstanding", "callback")

    return EscalationDecision(False)
