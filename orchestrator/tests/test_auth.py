from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _signup(email="owner@example.com", pw="supersecret"):
    return client.post("/auth/signup", json={"email": email, "password": pw})


def test_signup_issues_tokens_and_me_works():
    r = _signup()
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["access_token"] and data["refresh_token"]
    assert data["user"]["role"] == "owner"

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["user"]["email"] == "owner@example.com"


def test_login_wrong_password_returns_json_error_envelope():
    _signup()
    r = client.post("/auth/login", json={"email": "owner@example.com", "password": "wrong"})
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["code"] == "bad_credentials"  # {error:{code,message}} envelope


def test_refresh_issues_new_access():
    d = _signup(email="r@example.com").json()["data"]
    r = client.post("/auth/refresh", json={"refresh_token": d["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["data"]["access_token"]


def test_protected_route_requires_token():
    r = client.get("/calls")
    assert r.status_code == 401
