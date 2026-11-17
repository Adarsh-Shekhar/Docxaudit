"""Document ingestion tests (Phase 7.7)."""
from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str, org: str) -> str:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "S3cure-passphrase", "organization_name": org},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]  # type: ignore[no-any-return]


_PDF_BYTES = b"%PDF-1.4\n% synthetic contract test fixture\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF"

_DOCX_BYTES = (
    b"PK\x03\x04" + b"\x00" * 8 + b"word/document.xml" + b"\x00" * 16
)  # minimal signature; content validity is Phase 8's concern


def test_upload_pdf_succeeds_and_download_roundtrips(client: TestClient) -> None:
    token = _register(client, "owner@example.com", "Acme")
    up = client.post(
        "/documents",
        headers=_auth(token),
        files={"file": ("contract.pdf", _PDF_BYTES, "application/pdf")},
    )
    assert up.status_code == 201, up.json()
    body = up.json()
    assert body["filename"] == "contract.pdf"
    assert body["version"] == 1

    dl = client.get(f"/documents/{body['id']}/content", headers=_auth(token))
    assert dl.status_code == 200
    assert base64.b64decode(dl.json()["content_base64"]) == _PDF_BYTES


def test_upload_unsupported_format_rejected(client: TestClient) -> None:
    token = _register(client, "owner@example.com", "Acme")
    up = client.post(
        "/documents",
        headers=_auth(token),
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert up.status_code == 415


def test_upload_size_limit(client: TestClient) -> None:
    token = _register(client, "owner@example.com", "Acme")
    up = client.post(
        "/documents",
        headers=_auth(token),
        files={
            "file": (
                "big.pdf",
                b"%PDF-1.4" + b"\x00" * (25 * 1024 * 1024 + 1),
                "application/pdf",
            )
        },
    )
    assert up.status_code == 413


def test_reupload_increments_version_and_links_parent(client: TestClient) -> None:
    token = _register(client, "owner@example.com", "Acme")
    first = client.post(
        "/documents",
        headers=_auth(token),
        files={"file": ("contract.pdf", _PDF_BYTES, "application/pdf")},
    ).json()
    second = client.post(
        "/documents",
        headers=_auth(token),
        params={"replaces_document_id": first["id"]},
        files={"file": ("contract_v2.pdf", _PDF_BYTES, "application/pdf")},
    )
    assert second.status_code == 201
    v2 = second.json()
    assert v2["version"] == 2
    assert v2["parent_document_id"] == first["id"]


def test_cross_org_access_returns_404(client: TestClient) -> None:
    token_a = _register(client, "a@example.com", "OrgA")
    token_b = _register(client, "b@example.com", "OrgB")
    doc = client.post(
        "/documents",
        headers=_auth(token_a),
        files={"file": ("contract.pdf", _PDF_BYTES, "application/pdf")},
    ).json()

    foreign = client.get(f"/documents/{doc['id']}", headers=_auth(token_b))
    assert foreign.status_code == 404

    foreign_delete = client.delete(f"/documents/{doc['id']}", headers=_auth(token_b))
    assert foreign_delete.status_code == 404


def test_member_cannot_delete_admin_can(client: TestClient) -> None:
    admin = _register(client, "admin@example.com", "Acme")
    client.post(
        "/users",
        headers=_auth(admin),
        json={"email": "mate@example.com", "password": "TempPass123"},
    )
    member_token = client.post(
        "/auth/login", json={"email": "mate@example.com", "password": "TempPass123"}
    ).json()["access_token"]

    doc = client.post(
        "/documents",
        headers=_auth(admin),
        files={"file": ("contract.pdf", _PDF_BYTES, "application/pdf")},
    ).json()

    member_try = client.delete(f"/documents/{doc['id']}", headers=_auth(member_token))
    assert member_try.status_code == 403

    admin_del = client.delete(f"/documents/{doc['id']}", headers=_auth(admin))
    assert admin_del.status_code == 204
    gone = client.get(f"/documents/{doc['id']}", headers=_auth(admin))
    assert gone.status_code == 404

    audit = client.get("/orgs/me/audit", headers=_auth(admin))
    assert "document.deleted" in [e["action"] for e in audit.json()]


def test_filename_sanitized_for_storage_path(client: TestClient) -> None:
    token = _register(client, "owner@example.com", "Acme")
    up = client.post(
        "/documents",
        headers=_auth(token),
        files={"file": ("../../evil name%.pdf", _PDF_BYTES, "application/pdf")},
    )
    assert up.status_code == 201
    assert up.json()["filename"] == "evil_name_.pdf"


def test_extraction_endpoints_report_live_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.mock_llm import mock_provider

    monkeypatch.setattr("app.pipeline.graph._resolve_provider", lambda explicit=None: mock_provider())
    token = _register(client, "owner@example.com", "Acme")
    doc = client.post(
        "/documents",
        headers=_auth(token),
        files={"file": ("contract.pdf", _PDF_BYTES, "application/pdf")},
    ).json()

    trig = client.post(f"/documents/{doc['id']}/extract", headers=_auth(token))
    assert trig.status_code == 202
    assert trig.json()["status"] == "queued"

    st = client.get(f"/documents/{doc['id']}/status", headers=_auth(token))
    assert st.status_code == 200
    body = st.json()
    # Background task completed synchronously in the test client; the fake
    # PDF has a text layer but the mock LLM handles whatever candidates exist.
    assert body["status"] in {"completed", "failed"}
    assert body["progress"] is None or set(body["progress"]) == {"done", "total"}


def test_upload_empty_file_rejected(client: TestClient) -> None:
    token = _register(client, "owner@example.com", "Acme")
    up = client.post(
        "/documents",
        headers=_auth(token),
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert up.status_code == 422


def test_list_only_own_org(client: TestClient) -> None:
    token_a = _register(client, "a@example.com", "OrgA")
    _register(client, "b@example.com", "OrgB")
    client.post(
        "/documents",
        headers=_auth(token_a),
        files={"file": ("a1.pdf", _PDF_BYTES, "application/pdf")},
    )
    client.post(
        "/documents",
        headers=_auth(token_a),
        files={"file": ("a2.pdf", _PDF_BYTES, "application/pdf")},
    )
    lst = client.get("/documents", headers=_auth(token_a))
    assert len(lst.json()) == 2
    assert {d["filename"] for d in lst.json()} == {"a1.pdf", "a2.pdf"}
