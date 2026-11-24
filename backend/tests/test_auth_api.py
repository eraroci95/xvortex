"""API tests for login, sessions, CSRF, admin-only user creation and rate limiting.
Needs the full dependency set (pip install -r requirements-dev.txt)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")

from tests.helpers import login, login_csrf  # noqa: E402


def test_login_sets_httponly_cookie_and_returns_csrf(client):
    r = login(client)
    assert r.status_code == 200 and r.json()["csrf_token"]
    assert "httponly" in r.headers["set-cookie"].lower()
    assert client.get("/api/auth/me").json()["user"]["email"] == "admin@example.com"


def test_wrong_password_and_unknown_email_give_same_error(client):
    a = login(client, password="wrong password!!")
    b = login(client, email="nobody@example.com")
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_private_endpoints_require_login(client):
    for path in ("/api/auth/me", "/api/admin/users", "/api/dashboard/summary",
                 "/api/settings/dashboard-layout", "/api/notifications"):
        assert client.get(path).status_code == 401, path


def test_logout_requires_csrf_and_ends_session(client):
    csrf = login(client).json()["csrf_token"]
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_only_admin_can_create_users(client):
    headers = login_csrf(client)
    body = {"email": "new@example.com", "display_name": "New", "password": "another long password"}
    assert client.post("/api/admin/users", json=body).status_code == 403  # no CSRF header
    assert client.post("/api/admin/users", json=body, headers=headers).status_code == 201
    assert client.post("/api/admin/users", json=body, headers=headers).status_code == 409
    client.cookies.clear()
    login(client, "user@example.com")
    assert client.get("/api/admin/users").status_code == 403


def test_short_password_rejected(client):
    headers = login_csrf(client)
    body = {"email": "x@example.com", "display_name": "X", "password": "short"}
    assert client.post("/api/admin/users", json=body, headers=headers).status_code == 422


def test_account_locks_after_repeated_failures(client):
    for _ in range(5):
        assert login(client, password="wrong password!!").status_code == 401
    r = login(client)  # even the right password is refused while locked
    assert r.status_code == 429 and "retry-after" in r.headers
