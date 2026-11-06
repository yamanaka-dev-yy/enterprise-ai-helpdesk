import time

import pytest
from helpdesk.auth import COOKIE, digest
from helpdesk.db import connect

from .conftest import login_demo, login_real


def test_requires_login(client):
    for path in ("/api/auth/me", "/api/documents", "/api/tickets", "/api/admin/overview"):
        assert client.get(path).status_code == 401
    assert client.post("/api/chat", json={"question": "VPNにつながらない"}).status_code == 401


@pytest.mark.parametrize("remember", [False, True])
def test_real_login_cookie_and_logout(client, remember):
    headers = login_real(client, remember=remember)
    assert client.get("/api/auth/me").json()["role"] == "admin"
    token = client.cookies.get(COOKIE)
    with connect(client.app.state.settings.database) as db:
        row = db.execute("SELECT * FROM sessions WHERE token_hash=?", (digest(token),)).fetchone()
        assert row
        assert row["expires"] - time.time() > (29 * 86400 if remember else 11 * 3600)
    response = client.post("/api/auth/logout", headers=headers)
    assert response.status_code == 200
    client.cookies.set(COOKIE, token)
    assert client.get("/api/auth/me").status_code == 401


def test_persistent_cookie_is_opt_in(client):
    for remember in (False, True):
        response = client.post("/api/auth/login", json={"email": "admin@example.test", "password": "Admin-Long-Password!", "remember": remember})
        cookie = response.headers["set-cookie"].lower()
        assert "httponly" in cookie and "samesite=lax" in cookie
        assert ("max-age=" in cookie) == remember


def test_password_spaces_are_significant(client):
    login_real(client, "employee")
    response = client.post("/api/auth/login", json={"email": "employee@example.test", "password": "Employee-Password!"})
    assert response.status_code == 401


def test_login_error_does_not_reveal_account_existence(client):
    responses = [client.post("/api/auth/login", json={"email": email, "password": "wrong"}) for email in ("admin@example.test", "nobody@example.test")]
    assert responses[0].json() == responses[1].json()


def test_session_rotation(client):
    login_demo(client)
    old = client.cookies.get(COOKIE)
    login_demo(client, "admin")
    assert client.cookies.get(COOKIE) != old
    client.cookies.clear()
    client.cookies.set(COOKIE, old)
    assert client.get("/api/auth/me").status_code == 401


def test_expired_session_is_denied(client, settings):
    login_demo(client)
    with connect(settings.database) as db:
        db.execute("UPDATE sessions SET expires=0")
    assert client.get("/api/auth/me").status_code == 401


def test_csrf_and_origin_are_checked(client):
    headers = login_demo(client)
    payload = {"question": "VPNにつながらない"}
    assert client.post("/api/chat", json=payload).status_code == 403
    assert client.post("/api/chat", json=payload, headers={**headers, "Origin": "https://evil.test"}).status_code == 403
    assert client.post("/api/auth/demo", json={"role": "admin"}, headers={"Origin": "null"}).status_code == 403
    assert client.post("/api/chat", json=payload, headers={**headers, "Origin": "http://testserver"}).status_code == 200


def test_role_cannot_be_injected_in_login_or_question(client):
    assert client.post("/api/auth/login", json={"email": "admin@example.test", "password": "Admin-Long-Password!", "role": "admin"}).status_code == 422
    headers = login_demo(client)
    assert client.post("/api/chat", json={"question": "VPNにつながらない", "role": "admin"}, headers=headers).status_code == 422
    assert client.get("/api/admin/overview").status_code == 403


def test_rate_limit_auth(client):
    for _ in range(30):
        assert client.post("/api/auth/demo", json={"role": "employee"}).status_code == 200
    response = client.post("/api/auth/demo", json={"role": "employee"})
    assert response.status_code == 429
    assert response.headers["retry-after"] == "300"


def test_metadata_has_no_secrets_and_api_is_not_cached(client):
    response = client.get("/api/config")
    assert response.headers["cache-control"] == "no-store"
    assert "password" not in response.text and "api_key" not in response.text
    assert response.headers["x-content-type-options"] == "nosniff"


def test_demo_cannot_request_remembered_cookie(client):
    assert client.post("/api/auth/demo", json={"role": "employee", "remember": True}).status_code == 422
    response = client.post("/api/auth/demo", json={"role": "employee"})
    assert "max-age=" not in response.headers["set-cookie"].lower()
