"""Cross-tenant reads must return nothing (PLAYBOOK §4). Tested at the repo AND the API layer."""
from fastapi.testclient import TestClient

from app.main import app
from app.repo import InMemoryRepo, get_repo

client = TestClient(app)


def test_repo_scopes_calls_by_workspace():
    repo = InMemoryRepo()
    ws_a = repo.create_workspace("A")
    ws_b = repo.create_workspace("B")
    cid = repo.insert_call(ws_a, {"session_id": "s1", "outcome": "booked"})

    assert repo.get_call(ws_a, cid) is not None
    assert repo.get_call(ws_b, cid) is None            # other tenant cannot read it
    assert repo.list_calls(ws_b) == []


def test_api_call_log_is_tenant_isolated():
    a = client.post("/auth/signup", json={"email": "a@example.com", "password": "supersecret"}).json()["data"]
    b = client.post("/auth/signup", json={"email": "b@example.com", "password": "supersecret"}).json()["data"]

    # Insert a call directly under A's workspace through the shared repo.
    get_repo().insert_call(a["user"]["workspace_id"], {"session_id": "s", "outcome": "booked"})

    ra = client.get("/calls", headers={"Authorization": f"Bearer {a['access_token']}"})
    rb = client.get("/calls", headers={"Authorization": f"Bearer {b['access_token']}"})
    assert len(ra.json()["data"]) == 1
    assert rb.json()["data"] == []   # B sees nothing of A's
