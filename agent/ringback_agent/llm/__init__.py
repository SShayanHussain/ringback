"""LLM/NLU seam. Provider-agnostic from day one (PLAYBOOK §12.2).

Default is the deterministic, key-free RuleBasedNLU so tests, CI, and evals are reproducible and
cost nothing. Set LLM_PROVIDER=groq|gemini (+ a key) to swap in a real model behind the SAME NLU
interface — the agent code does not change.

No-key / failure behavior degrades to honest heuristics (RuleBasedNLU), never to a fabricated
confident answer (PLAYBOOK Golden Rule 1 / §5).
"""
from __future__ import annotations

import logging

from ..config import Settings, get_settings
from .base import NLU, IntentResult
from .rulebased import RuleBasedNLU

log = logging.getLogger("ringback.llm")


def build_nlu(settings: Settings | None = None) -> NLU:
    settings = settings or get_settings()
    provider = (settings.llm_provider or "rulebased").lower()

    if provider in ("rulebased", "rule", "mock", ""):
        return RuleBasedNLU()

    # Real providers are constructed lazily and wrap RuleBasedNLU as a fail-safe fallback.
    from .providers import GeminiBackend, GroqBackend, LLMNLU

    if provider == "groq":
        if not settings.groq_api_key:
            log.warning("LLM_PROVIDER=groq but GROQ_API_KEY is empty — falling back to rulebased NLU.")
            return RuleBasedNLU()
        return LLMNLU(GroqBackend(settings), fallback=RuleBasedNLU())

    if provider == "gemini":
        if not settings.llm_api_key:
            log.warning("LLM_PROVIDER=gemini but LLM_API_KEY is empty — falling back to rulebased NLU.")
            return RuleBasedNLU()
        return LLMNLU(GeminiBackend(settings), fallback=RuleBasedNLU())

    log.warning("Unknown LLM_PROVIDER=%s — falling back to rulebased NLU.", provider)
    return RuleBasedNLU()


__all__ = ["NLU", "IntentResult", "RuleBasedNLU", "build_nlu"]
