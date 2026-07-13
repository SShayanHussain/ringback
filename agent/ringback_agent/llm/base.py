"""NLU interface shared by the rule-based and LLM-backed implementations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..state import ConversationState
from ..vertical import Vertical


@dataclass
class IntentResult:
    intent: str          # one of state.Intent values
    confidence: float    # 0..1; below settings.min_confidence => escalate


@runtime_checkable
class NLU(Protocol):
    def classify_intent(self, text: str, vertical: Vertical, state: ConversationState) -> IntentResult: ...

    def extract_slots(
        self, text: str, expecting: str | None, vertical: Vertical
    ) -> dict: ...

    def interpret_yes_no(self, text: str) -> bool | None: ...

    def detect_frustration(self, text: str) -> bool: ...

    def select_slot(self, text: str, offered: list[dict]) -> dict | None: ...
