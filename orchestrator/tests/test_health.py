from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_get():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_health_head():
    # Uptime monitors send HEAD; must not 405.
    r = client.head("/health")
    assert r.status_code == 200
