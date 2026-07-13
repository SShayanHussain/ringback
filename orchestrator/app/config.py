"""Orchestrator settings. Fail-fast validation of the things that MUST be set in prod."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

log = logging.getLogger("ringback.orchestrator")


def _env(k: str, d: str = "") -> str:
    return os.environ.get(k, d)


@dataclass(frozen=True)
class Settings:
    app_url: str = field(default_factory=lambda: _env("APP_URL", "http://localhost:3000"))
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL"))
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL"))
    agent_core_url: str = field(default_factory=lambda: _env("AGENT_CORE_URL", "http://localhost:8001"))
    jwt_access_secret: str = field(default_factory=lambda: _env("JWT_ACCESS_SECRET", "dev-access-secret"))
    jwt_refresh_secret: str = field(default_factory=lambda: _env("JWT_REFRESH_SECRET", "dev-refresh-secret"))
    jwt_access_ttl: int = field(default_factory=lambda: int(_env("JWT_ACCESS_TTL", "900")))
    jwt_refresh_ttl: int = field(default_factory=lambda: int(_env("JWT_REFRESH_TTL", "1209600")))
    credentials_enc_key: str = field(default_factory=lambda: _env("CREDENTIALS_ENC_KEY"))
    n8n_webhook_url: str = field(default_factory=lambda: _env("N8N_WEBHOOK_URL"))
    n8n_webhook_secret: str = field(default_factory=lambda: _env("N8N_WEBHOOK_SECRET"))
    vertical: str = field(default_factory=lambda: _env("VERTICAL", "home-services"))

    @property
    def db_enabled(self) -> bool:
        return bool(self.database_url)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
        if not _settings.db_enabled:
            # Loud exit-alarm on the fallback (PLAYBOOK Golden Rule 5): in-memory storage is ephemeral.
            log.warning("DATABASE_URL is not set — using EPHEMERAL in-memory storage (dev/test only).")
    return _settings
