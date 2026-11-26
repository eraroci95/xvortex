"""API tests for login, sessions, CSRF, admin-only user creation and rate limiting.
Needs the full dependency set (pip install -r requirements-dev.txt)."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("argon2")

from tests.helpers import PASSWORD, login, login_csrf  # noqa: E402


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


def _second_device():
    """A separate client (own cookie jar) on the same app and database."""
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_password_change_replaces_every_session_and_the_new_password_works(client):
    other = _second_device()
    login(other)  # the same account signed in elsewhere
    headers = login_csrf(client)
    new = "a brand new long password"
    body = {"current_password": PASSWORD, "new_password": new}

    assert client.post("/api/auth/password", json=body).status_code == 403  # needs the CSRF header
    wrong = {"current_password": "not the password", "new_password": new}
    assert client.post("/api/auth/password", json=wrong, headers=headers).status_code == 400

    ok = client.post("/api/auth/password", json=body, headers=headers)
    assert ok.status_code == 200 and ok.json()["csrf_token"] != headers["X-CSRF-Token"]
    assert client.get("/api/auth/me").status_code == 200  # this device continues on a fresh session
    assert other.get("/api/auth/me").status_code == 401  # the other device is signed out
    client.cookies.clear()
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password=new).status_code == 200


def test_password_change_validates_the_new_password(client):
    headers = login_csrf(client)
    short = {"current_password": PASSWORD, "new_password": "short"}
    assert client.post("/api/auth/password", json=short, headers=headers).status_code == 422
    same = {"current_password": PASSWORD, "new_password": PASSWORD}
    assert client.post("/api/auth/password", json=same, headers=headers).status_code == 400
    assert login(client).status_code == 200  # nothing changed


def test_password_change_is_rate_limited(client):
    headers = login_csrf(client)
    guess = {"current_password": "guessing the password", "new_password": "some other long password"}
    for _ in range(5):
        assert client.post("/api/auth/password", json=guess, headers=headers).status_code == 400
    blocked = client.post("/api/auth/password", json=guess, headers=headers)
    assert blocked.status_code == 429 and "retry-after" in blocked.headers


def test_admin_can_reset_a_password_and_that_user_is_signed_out(client):
    member = _second_device()
    login(member, "user@example.com")
    headers = login_csrf(client)  # the administrator
    users = client.get("/api/admin/users").json()
    member_id = next(u["id"] for u in users if u["email"] == "user@example.com")
    admin_id = next(u["id"] for u in users if u["email"] == "admin@example.com")
    new = "reset by the administrator"
    url = f"/api/admin/users/{member_id}/password"

    assert client.post(url, json={"new_password": new}).status_code == 403  # needs the CSRF header
    assert client.post(url, json={"new_password": "short"}, headers=headers).status_code == 422
    assert client.post(f"/api/admin/users/{admin_id}/password", json={"new_password": new}, headers=headers).status_code == 400
    assert client.post(url, json={"new_password": new}, headers=headers).status_code == 204

    assert member.get("/api/auth/me").status_code == 401
    member.cookies.clear()
    assert login(member, "user@example.com").status_code == 401  # the old password is gone
    signed_in = login(member, "user@example.com", new)
    assert signed_in.status_code == 200
    member_headers = {"X-CSRF-Token": signed_in.json()["csrf_token"]}
    assert member.post(f"/api/admin/users/{admin_id}/password", json={"new_password": new}, headers=member_headers).status_code == 403
