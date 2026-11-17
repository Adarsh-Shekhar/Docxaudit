"""Clauses API tests (Phase 13.4) — the ONLY path that creates Obligations (R-2)."""
from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.extracted_clause import ExtractedClause
from app.models.obligation import Obligation
from tests.fixtures.make_fixtures import build_synthetic_pdf_bytes
from tests.mock_llm import mock_provider

ADMIN_EMAIL = "admin@example.com"
MEMBER_EMAIL = "member@example.com"


@pytest.fixture(name="db_session")
def db_session_fixture(db_engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture(name="review_setup")
def review_setup_fixture(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> dict[str, object]:
    """Admin + member + a completed synthetic-PDF extraction with clauses."""
    monkeypatch.setattr("app.pipeline.graph._resolve_provider", lambda explicit=None: mock_provider())

    reg = client.post(
        "/auth/register",
        json={"email": ADMIN_EMAIL, "password": "S3cure-passphrase", "organization_name": "Acme"},
    )
    assert reg.status_code == 201
    admin = reg.json()["access_token"]

    member_signup = client.post(
        "/users",
        headers={"Authorization": f"Bearer {admin}"},
        json={"email": MEMBER_EMAIL, "password": "TempPass123"},
    )
    assert member_signup.status_code in (200, 201)
    member = client.post(
        "/auth/login", json={"email": MEMBER_EMAIL, "password": "TempPass123"}
    ).json()["access_token"]

    up = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {admin}"},
        files={"file": ("contract.pdf", build_synthetic_pdf_bytes(), "application/pdf")},
    )
    assert up.status_code == 201
    doc = up.json()

    trig = client.post(f"/documents/{doc['id']}/extract", headers={"Authorization": f"Bearer {admin}"})
    assert trig.status_code == 202
    st = client.get(f"/documents/{doc['id']}/status", headers={"Authorization": f"Bearer {admin}"})
    assert st.json()["status"] == "completed", st.json()

    listed = client.get(f"/documents/{doc['id']}/clauses", headers={"Authorization": f"Bearer {admin}"})
    assert listed.status_code == 200
    payload = listed.json()
    assert len(payload["clauses"]) >= 1

    return {
        "admin": admin,
        "member": member,
        "doc_id": doc["id"],
        "clauses": payload["clauses"],
    }


def _auth(token: object) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ── listing (read-only; any org member) ──────────────────────────────────────

def test_list_clauses_includes_citation_confidence_progress(review_setup: dict[str, object], client: TestClient) -> None:
    member = review_setup["member"]
    doc_id = review_setup["doc_id"]
    resp = client.get(f"/documents/{doc_id}/clauses", headers=_auth(member))
    assert resp.status_code == 200  # members may read (FR-5.1)
    payload = resp.json()

    assert payload["progress"] == {"reviewed": 0, "total": len(payload["clauses"])}
    for clause in payload["clauses"]:
        assert set(clause) >= {
            "id", "document_id", "obligation_type", "plain_language_text",
            "page_number", "char_start", "char_end", "confidence_score", "status",
        }
        assert clause["status"] == "pending"
        assert clause["page_number"] is not None  # PDF: citation must have a page (R-5)
        assert clause["char_start"] <= clause["char_end"]
        assert 0.0 <= clause["confidence_score"] <= 1.0


def test_list_clauses_cross_org_is_404(review_setup: dict[str, object], client: TestClient) -> None:
    other = client.post(
        "/auth/register",
        json={"email": "rival@example.com", "password": "S3cure-passphrase", "organization_name": "Rival"},
    ).json()["access_token"]
    resp = client.get(f"/documents/{review_setup['doc_id']}/clauses", headers=_auth(other))
    assert resp.status_code == 404


# ── accept (R-2: creates exactly one Obligation) ─────────────────────────────

def test_accept_creates_exactly_one_obligation(
    review_setup: dict[str, object], client: TestClient, db_session: Session
) -> None:
    admin = review_setup["admin"]
    doc_id = review_setup["doc_id"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    resp = client.patch(
        f"/clauses/{clause['id']}",
        headers=_auth(admin),
        json={"action": "accept"},
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["status"] == "accepted"

    obligations = db_session.scalars(select(Obligation)).all()
    assert len(obligations) == 1
    ob = obligations[0]
    # Citation copied from the clause (R-5 traceability).
    assert ob.document_id == uuid.UUID(str(doc_id))
    assert ob.extracted_clause_id == uuid.UUID(clause["id"])
    assert ob.citation_page == clause["page_number"]
    assert ob.citation_offset_start == clause["char_start"]
    assert ob.citation_offset_end == clause["char_end"]
    assert ob.description == clause["plain_language_text"]

    # Audit logged.
    audit = client.get("/orgs/me/audit", headers=_auth(admin)).json()
    assert "clause.accepted" in [e["action"] for e in audit]

    # Progress advanced.
    progress = client.get(f"/documents/{doc_id}/clauses", headers=_auth(admin)).json()["progress"]
    assert progress == {"reviewed": 1, "total": progress["total"]}


def test_edit_creates_obligation_with_edited_values(
    review_setup: dict[str, object], client: TestClient, db_session: Session
) -> None:
    admin = review_setup["admin"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    resp = client.patch(
        f"/clauses/{clause['id']}",
        headers=_auth(admin),
        json={
            "action": "edit",
            "plain_language_text": "Edited: appears to require renewal notice.",
            "obligation_type": "termination_notice",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "edited"
    assert resp.json()["plain_language_text"].startswith("Edited:")

    obligations = db_session.scalars(select(Obligation)).all()
    assert len(obligations) == 1
    assert obligations[0].description == "Edited: appears to require renewal notice."
    assert obligations[0].obligation_type.value == "termination_notice"


def test_reject_creates_no_obligation(
    review_setup: dict[str, object], client: TestClient, db_session: Session
) -> None:
    admin = review_setup["admin"]
    doc_id = review_setup["doc_id"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    resp = client.patch(f"/clauses/{clause['id']}", headers=_auth(admin), json={"action": "reject"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    assert db_session.scalars(select(Obligation)).all() == []
    assert db_session.get(ExtractedClause, uuid.UUID(clause["id"])).status.value == "rejected"  # type: ignore[union-attr]

    audit = client.get("/orgs/me/audit", headers=_auth(admin)).json()
    assert "clause.rejected" in [e["action"] for e in audit]

    progress = client.get(f"/documents/{doc_id}/clauses", headers=_auth(admin)).json()["progress"]
    assert progress == {"reviewed": 1, "total": progress["total"]}


# ── guards ───────────────────────────────────────────────────────────────────

def test_member_cannot_decide_but_can_read(review_setup: dict[str, object], client: TestClient) -> None:
    member = review_setup["member"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    resp = client.patch(f"/clauses/{clause['id']}", headers=_auth(member), json={"action": "accept"})
    assert resp.status_code == 403

    # Read still allowed.
    assert client.get(f"/documents/{review_setup['doc_id']}/clauses", headers=_auth(member)).status_code == 200


def test_redeciding_returns_409(review_setup: dict[str, object], client: TestClient) -> None:
    admin = review_setup["admin"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    first = client.patch(f"/clauses/{clause['id']}", headers=_auth(admin), json={"action": "accept"})
    assert first.status_code == 200

    again = client.patch(f"/clauses/{clause['id']}", headers=_auth(admin), json={"action": "accept"})
    assert again.status_code == 409
    assert again.json()["detail"]["current_status"] == "accepted"


def test_cross_org_decision_is_404(review_setup: dict[str, object], client: TestClient) -> None:
    other = client.post(
        "/auth/register",
        json={"email": "other-admin@example.com", "password": "S3cure-passphrase", "organization_name": "Other"},
    ).json()["access_token"]
    clause = review_setup["clauses"][0]  # type: ignore[index]
    resp = client.patch(f"/clauses/{clause['id']}", headers=_auth(other), json={"action": "accept"})
    assert resp.status_code == 404


# ── validation ───────────────────────────────────────────────────────────────

def test_invalid_action_and_type_rejected(review_setup: dict[str, object], client: TestClient) -> None:
    admin = review_setup["admin"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    bad_type = client.patch(
        f"/clauses/{clause['id']}",
        headers=_auth(admin),
        json={"action": "edit", "obligation_type": "not_a_type"},
    )
    assert bad_type.status_code == 422

    empty_edit = client.patch(f"/clauses/{clause['id']}", headers=_auth(admin), json={"action": "edit"})
    assert empty_edit.status_code == 422

    payload_on_accept = client.patch(
        f"/clauses/{clause['id']}",
        headers=_auth(admin),
        json={"action": "accept", "plain_language_text": "x"},
    )
    assert payload_on_accept.status_code == 422

    # The clause is still untouched by the failed attempts.
    still = client.get(f"/documents/{review_setup['doc_id']}/clauses", headers=_auth(admin)).json()
    assert still["progress"]["reviewed"] == 0


def test_accept_then_rerun_extraction_resets_decisions(
    review_setup: dict[str, object], client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Phase 12.4 × 13 interaction: re-extraction resets clause decisions."""
    admin = review_setup["admin"]
    doc_id = review_setup["doc_id"]
    clause = review_setup["clauses"][0]  # type: ignore[index]

    assert client.patch(f"/clauses/{clause['id']}", headers=_auth(admin), json={"action": "accept"}).status_code == 200
    assert db_session.scalars(select(Obligation)).all() != []

    rerun = client.post(f"/documents/{doc_id}/extract", headers=_auth(admin))
    assert rerun.status_code == 202

    obligations = db_session.scalars(select(Obligation)).all()
    # Re-run deleted clause rows (CASCADE → SET NULL obligations), then created fresh pending clauses.
    fresh = client.get(f"/documents/{doc_id}/clauses", headers=_auth(admin)).json()
    assert fresh["progress"]["reviewed"] == 0
    assert len(fresh["clauses"]) >= 1
    # Old obligations lost their clause link (SET NULL) but were not silently duplicated.
    for ob in obligations:
        assert ob.extracted_clause_id not in {c["id"] for c in fresh["clauses"]}
