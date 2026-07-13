"""Settings + a tiny stdlib .env loader (no python-dotenv dependency).

PLAYBOOK §12.8: auto-load a repo-root .env for host-run scripts BEFORE reading settings, because
defaults read os.environ at import time. This is a no-op inside containers (env already set).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Populate os.environ from the nearest .env (repo root) without clobbering real env vars."""
    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            try:
                for raw in candidate.read_text(encoding="utf-8").splitlines():
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
            except OSError:
                pass
            return


_load_dotenv()


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    vertical: str = field(default_factory=lambda: _env("VERTICAL", "home-services"))
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "rulebased"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY"))
    groq_api_key: str = field(default_factory=lambda: _env("GROQ_API_KEY"))
    llm_model_turn: str = field(default_factory=lambda: _env("LLM_MODEL_TURN", "llama-3.1-8b-instant"))
    llm_model_heavy: str = field(
        default_factory=lambda: _env("LLM_MODEL_HEAVY", "llama-3.3-70b-versatile")
    )
    llm_min_interval_ms: int = field(default_factory=lambda: int(_env("LLM_MIN_INTERVAL_MS", "0")))
    # NLU confidence below this escalates to a human (PRD escalation trigger).
    min_confidence: float = field(default_factory=lambda: float(_env("MIN_NLU_CONFIDENCE", "0.35")))
    max_misunderstandings: int = field(
        default_factory=lambda: int(_env("MAX_MISUNDERSTANDINGS", "2"))
    )


def get_settings() -> Settings:
    return Settings()
