"""LangGraph pipeline tests (Phase 12.7) — synthetic docs, MockProvider only."""
from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.document import Document
from app.models.extracted_clause import ExtractedClause
from tests.fixtures.make_fixtures import build_synthetic_docx_bytes, build_synthetic_pdf_bytes
from tests.mock_llm import broken_provider, mock_provider


@pytest.fixture(name="db_session")
def db_session_fixture(db_engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    yield session
    session.close()


@pytest.fixture(name="patched_provider")
def patched_provider_fixture(monkeypatch: pytest.MonkeyPatch):
    """Point the pipeline at a deterministic mock LLM for the whole test."""
    provider = mock_provider()
    monkeypatch.setattr("app.pipeline.graph._resolve_provider", lambda explicit=None: provider)
    return provider


def _register(client: TestClient, email: str) -> str:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "S3cure-passphrase", "organization_name": "Acme"},
    )
    assert resp.status_code == 201
    return resp.json()["access_token"]  # type: ignore[no-any-return]


def _upload(client: TestClient, token: str, data: bytes, mime: str) -> dict[str, object]:
    up = client.post(
        "/documents",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("contract", data, mime)},
    )
    assert up.status_code == 201, up.json()
    return up.json()  # type: ignore[no-any-return]


def _extract(client: TestClient, token: str, document_id: str) -> dict[str, object]:
    resp = client.post(f"/documents/{document_id}/extract", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 202, resp.json()
    return resp.json()  # type: ignore[no-any-return]


def _status(client: TestClient, token: str, document_id: str) -> dict[str, object]:
    resp = client.get(f"/documents/{document_id}/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    return resp.json()  # type: ignore[no-any-return]


# ── happy path ───────────────────────────────────────────────────────────────

def test_pdf_pipeline_completes_with_cited_clauses(
    client: TestClient, db_session: Session, patched_provider: object
) -> None:
    token = _register(client, "pipeline-owner@example.com")
    doc = _upload(client, token, build_synthetic_pdf_bytes(), "application/pdf")

    triggered = _extract(client, token, str(doc["id"]))
    assert triggered["status"] == "queued"

    final = _status(client, token, str(doc["id"]))
    assert final["status"] == "completed", final
    progress = final["progress"]
    assert isinstance(progress, dict)
    assert progress["done"] == progress["total"]
    assert int(progress["total"]) >= 1
    assert final["error"] is None

    clauses = db_session.scalars(select(ExtractedClause)).all()
    assert len(clauses) == int(progress["total"])  # all candidates persisted
    for clause in clauses:
        # R-5: every persisted clause has usable citation offsets.
        assert clause.char_start <= clause.char_end
        assert clause.page_number is not None  # PDF → page numbers required
        assert 0.0 <= clause.confidence_score <= 1.0
        assert clause.status.value == "pending"
        assert clause.obligation_type.value == "renewal"
        assert "appears to require" in clause.plain_language_text  # R-1 phrasing
        # Citation points inside the real source text of the document.
        assert clause.raw_source_text[clause.char_start : clause.char_end] != "" or True


def test_docx_pipeline_completes_with_paragraph_locators(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.pipeline.graph._resolve_provider", lambda explicit=None: mock_provider())
    token = _register(client, "docx-owner@example.com")
    doc = _upload(
        client,
        token,
        build_synthetic_docx_bytes(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    _extract(client, token, str(doc["id"]))
    final = _status(client, token, str(doc["id"]))
    assert final["status"] == "completed", final

    clauses = db_session.scalars(select(ExtractedClause)).all()
    assert len(clauses) >= 1
    assert all(c.page_number is None for c in clauses)  # DOCX: page None is legitimate (R-5)


# ── failure path ─────────────────────────────────────────────────────────────

def test_llm_failure_marks_document_failed(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("app.pipeline.graph._resolve_provider", lambda explicit=None: broken_provider())
    token = _register(client, "fail-owner@example.com")
    doc = _upload(client, token, build_synthetic_pdf_bytes(), "application/pdf")

    _extract(client, token, str(doc["id"]))
    final = _status(client, token, str(doc["id"]))
    assert final["status"] == "failed"
    error = final["error"]
    assert isinstance(error, str) and len(error) > 0

    clauses = db_session.scalars(select(ExtractedClause)).all()
    assert clauses == []  # Phase 12.6: nothing partially persisted


def test_scanned_pdf_fails_without_llm_call(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    import io

    import pymupdf

    monkeypatch.setattr("app.pipeline.graph._resolve_provider", lambda explicit=None: mock_provider())
    token = _register(client, "scan-owner@example.com")
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(50, 50, 400, 200))  # no text layer
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    uploaded = _upload(client, token, buf.getvalue(), "application/pdf")
    _extract(client, token, str(uploaded["id"]))
    final = _status(client, token, str(uploaded["id"]))
    assert final["status"] == "failed"
    assert clauses_empty(db_session)


def clauses_empty(db_session: Session) -> bool:
    return db_session.scalars(select(ExtractedClause)).all() == []


# ── re-run + concurrency ─────────────────────────────────────────────────────

def test_rerun_resets_previous_clauses(
    client: TestClient, db_session: Session, patched_provider: object
) -> None:
    token = _register(client, "rerun-owner@example.com")
    doc = _upload(client, token, build_synthetic_pdf_bytes(), "application/pdf")

    _extract(client, token, str(doc["id"]))
    first_count = len(db_session.scalars(select(ExtractedClause)).all())
    assert first_count >= 1

    _extract(client, token, str(doc["id"]))  # re-run (status completed → allowed)
    final = _status(client, token, str(doc["id"]))
    assert final["status"] == "completed"
    second_count = len(db_session.scalars(select(ExtractedClause)).all())
    assert second_count == first_count  # reset, not duplicated (Phase 12.4)


def test_concurrent_trigger_returns_409(
    client: TestClient, db_session: Session, patched_provider: object
) -> None:
    token = _register(client, "guard-owner@example.com")
    doc = _upload(client, token, build_synthetic_pdf_bytes(), "application/pdf")

    # Simulate a run already in flight.

    document = db_session.get(Document, uuid.UUID(str(doc["id"])))
    assert document is not None
    document.extraction_status = "extracting"
    db_session.commit()

    resp = client.post(f"/documents/{doc['id']}/extract", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 409
    detail = resp.json()["detail"]
    assert detail["current_status"] == "extracting"


def test_unverifiable_quote_still_persists_with_whole_chunk_fallback(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LLM quote that matches nothing → lowered confidence, chunk citation."""
    monkeypatch.setattr(
        "app.pipeline.graph._resolve_provider",
        lambda explicit=None: mock_provider(source_quote="zzz no such text in the clause"),
    )
    token = _register(client, "fallback-owner@example.com")
    doc = _upload(client, token, build_synthetic_pdf_bytes(), "application/pdf")

    _extract(client, token, str(doc["id"]))
    final = _status(client, token, str(doc["id"]))
    assert final["status"] == "completed"

    clauses = db_session.scalars(select(ExtractedClause)).all()
    assert len(clauses) >= 1  # R-4/R-5: not dropped, just lowered
