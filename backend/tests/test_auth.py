"""Auth endpoint tests (Phase 4.7)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "owner@example.com") -> dict[str, object]:
    resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "S3cure-passphrase",
            "organization_name": "Acme Corp",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_register_returns_tokens(client: TestClient) -> None:
    body = _register(client)
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 30 * 60


def test_register_duplicate_email_conflict(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/auth/register",
        json={
            "email": "owner@example.com",
            "password": "S3cure-passphrase",
            "organization_name": "Other Org",
        },
    )
    assert resp.status_code == 409


def test_login_success_returns_user(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "S3cure-passphrase"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "owner@example.com"
    assert body["user"]["role"] == "admin"


def test_login_failure_invalid_credentials(client: TestClient) -> None:
    _register(client)
    resp = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401
    assert "credentials" in resp.json()["detail"]


def test_refresh_flow(client: TestClient) -> None:
    body = _register(client)
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_expired_or_bad_token_unauthorized(client: TestClient) -> None:
    resp = client.get(
        "/users",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401


def test_missing_token_unauthorized(client: TestClient) -> None:
    resp = client.get("/users")
    assert resp.status_code == 401


def test_access_token_is_not_a_refresh_token(client: TestClient) -> None:
    body = _register(client)
    # Using an access token where a refresh token is required must fail.
    resp = client.post(
        "/auth/refresh",
        json={"refresh_token": body["access_token"]},
    )
    assert resp.status_code == 401


def test_cross_registration_isolation(client: TestClient) -> None:
    """Two separate orgs exist; tokens are org-scoped (manual conformance start)."""
    _register(client)
    resp = client.post(
        "/auth/register",
        json={
            "email": f"other-{uuid.uuid4().hex[:8]}@example.com",
            "password": "S3cure-passphrase",
            "organization_name": "Differential Org",
        },
    )
    assert resp.status_code == 201
    # The /users listing uses the new admin's own token → only themselves.
    body2 = resp.json()
    me = client.get(
        "/users",
        headers={"Authorization": f"Bearer {body2['access_token']}"},
    )
    assert me.status_code == 200
    data = me.json()
    assert len(data) == 1
