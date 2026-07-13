"""Ringback orchestrator — FastAPI app wiring."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import errors
from .config import get_settings
from .routers import auth, calls, config, health, integrations, playground

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Ringback Orchestrator", version="0.1.0")
_settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

errors.install(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(playground.router)
app.include_router(calls.router)
app.include_router(config.router)
app.include_router(integrations.router)


@app.get("/")
def root():
    return {"service": "ringback-orchestrator", "docs": "/docs"}
