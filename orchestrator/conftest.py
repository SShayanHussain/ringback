"""Test bootstrap: force ephemeral in-memory storage and a fresh repo per test."""
import os
import pathlib
import sys

# Must be set BEFORE app modules read settings.
os.environ.pop("DATABASE_URL", None)
os.environ.setdefault("JWT_ACCESS_SECRET", "test-access-secret")
os.environ.setdefault("JWT_REFRESH_SECRET", "test-refresh-secret")

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pytest  # noqa: E402

from app.repo import InMemoryRepo, reset_repo_for_tests  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_repo():
    reset_repo_for_tests(InMemoryRepo())
    yield
