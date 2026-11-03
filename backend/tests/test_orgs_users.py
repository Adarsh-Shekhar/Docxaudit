"""Org/user management tests (Phase 5.5)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_two_orgs(
    client: TestClient,
) -> tuple[str, str, list[float]]:
    """Register org A admin (admin@acme...), org B admin; return both tokens."""
    admin_a = client.post(
        "/auth/register",
        json={
            "email": f"admin-{uuid.uuid4().hex[:8]}@acme.example.com",
            "password": "S3cure-passphrase",
            "organization_name": "Acme",
        },
    )
    admin_b = client.post(
        "/auth/register",
        json={
            "email": f"admin-{uuid.uuid4().hex[:8]}@beta.example.com",
            "password": "S3cure-passphrase",
            "organization_name": "Beta",
        },
    )
    assert admin_a.status_code == 201 and admin_b.status_code == 201
    return (
        admin_a.json()["access_token"],  # type: ignore[union-attr]
        admin_b.json()["access_token"],  # type: ignore[union-attr]
        [],
    )


def test_invite_member_scoped_and_listed(client: TestClient) -> None:
    token_a, token_b, _ = _setup_two_orgs(client)
    resp = client.post(
        "/users",
        headers=_auth_header(token_a),
        json={"email": f"teammate-{uuid.uuid4().hex[:8]}@acme.example.com", "password": "TempPass123"},
    )
    assert resp.status_code == 201, resp.json()

    members_a = client.get("/users", headers=_auth_header(token_a))
    assert [u["role"] for u in members_a.json()] == ["admin", "member"]
    assert len(members_a.json()) == 2

    members_b = client.get("/users", headers=_auth_header(token_b))
    assert len(members_b.json()) == 1  # org B sees its own admin only


def test_member_cannot_invite(client: TestClient) -> None:
    token_a, _, _ = _setup_two_orgs(client)
    created = client.post(
        "/users",
        headers=_auth_header(token_a),
        json={"email": f"mate-{uuid.uuid4().hex[:8]}@acme.example.com", "password": "TempPass123"},
    )
    member_token = client.post(
        "/auth/login",
        json={
            "email": created.json()["email"],
            "password": "TempPass123",
        },
    ).json()["access_token"]

    blocked = client.post(
        "/users",
        headers=_auth_header(member_token),
        json={"email": f"other-{uuid.uuid4().hex[:8]}@acme.example.com", "password": "TempPass123"},
    )
    assert blocked.status_code == 403


def test_role_change_by_admin_succeeds_and_audits(client: TestClient) -> None:
    token_a, _, _ = _setup_two_orgs(client)
    created = client.post(
        "/users",
        headers=_auth_header(token_a),
        json={"email": f"mate-{uuid.uuid4().hex[:8]}@acme.example.com", "password": "TempPass123"},
    )
    member_id = created.json()["id"]

    promoted = client.patch(
        f"/users/{member_id}/role",
        headers=_auth_header(token_a),
        json={"role": "admin"},
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"

    audit = client.get("/orgs/me/audit", headers=_auth_header(token_a))
    actions = [e["action"] for e in audit.json()]
    assert "user.created" in actions
    assert "user.role_changed" in actions


def test_role_change_by_member_forbidden(client: TestClient) -> None:
    token_a, _, _ = _setup_two_orgs(client)
    created = client.post(
        "/users",
        headers=_auth_header(token_a),
        json={"email": f"mate-{uuid.uuid4().hex[:8]}@acme.example.com", "password": "TempPass123"},
    )
    member_id = created.json()["id"]
    member_token = client.post(
        "/auth/login",
        json={
            "email": created.json()["email"],
            "password": "TempPass123",
        },
    ).json()["access_token"]

    blocked = client.patch(
        f"/users/{member_id}/role",
        headers=_auth_header(member_token),
        json={"role": "admin"},
    )
    assert blocked.status_code == 403


def test_cannot_demote_last_admin(client: TestClient) -> None:
    token_a, _, _ = _setup_two_orgs(client)
    admin_id = client.get("/users", headers=_auth_header(token_a)).json()[0]["id"]

    demote_self = client.patch(
        f"/users/{admin_id}/role",
        headers=_auth_header(token_a),
        json={"role": "member"},
    )
    assert demote_self.status_code == 409
    assert "last admin" in demote_self.json()["detail"]


def test_cross_org_role_change_not_found(client: TestClient) -> None:
    token_a, token_b, _ = _setup_two_orgs(client)
    beta_user_id = client.get("/users", headers=_auth_header(token_b)).json()[0]["id"]

    cross = client.patch(
        f"/users/{beta_user_id}/role",
        headers=_auth_header(token_a),
        json={"role": "member"},
    )
    # 404 — never leak existence across orgs (Phase 4 DoD).
    assert cross.status_code == 404
