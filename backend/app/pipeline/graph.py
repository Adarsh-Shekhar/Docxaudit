"""LangGraph orchestration of the extraction pipeline (Phase 12.1).

parse → filter → extract → score(cite) → persist, as a stateful graph.

Design:
- Nodes are pure functions over `PipelineState` — only `persist_node`
  touches the DB, via a session factory injected at build time, so the
  graph stays testable with any factory (tests use the SQLite fixtures).
- Extraction rows are written ONLY at `persist_node`, transactionally
  (Phase 12.6): all clauses commit or the run fails with nothing partial.
- `run_extraction` is the background entrypoint (Phase 12.2): it owns
  status updates on `Document` (short-lived sessions per update) and
  always leaves the document in a terminal state (completed | failed).
  Documented limitation (C-3): in-process jobs die if the process
  restarts — acceptable at capstone scale.
"""
from __future__ import annotations

import uuid
from typing import Any, TypedDict

from langgraph.graph import StateGraph
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from app.pipeline.cite import attach_citation, verify_quote
from app.pipeline.extract import ExtractionFailedError, ExtractionResult, extract_clause
from app.pipeline.filter import FilteredChunk, candidate_chunks
from app.pipeline.parse import Chunk, parse_docx, parse_pdf
from app.pipeline.score import compute_composite_confidence

ACTIVE_EXTRACTION_STATUSES = frozenset(
    {"queued", "parsing", "filtering", "extracting", "scoring", "persisting"}
)
# Statuses that mean a graph run is IN PROGRESS. `queued` is excluded: it is
# set by the endpoint immediately before invoking this very run.
RUN_IN_PROGRESS_STATUSES = ACTIVE_EXTRACTION_STATUSES - {"queued"}


class ExtractionRecord(TypedDict):
    """One candidate's in-flight extraction payload between nodes."""

    chunk: Chunk
    result: ExtractionResult
    signal_count: int
    composite: float
    citation: dict[str, Any] | None  # set in score_node; None → dropped (R-5)


class PipelineState(TypedDict, total=False):
    document_id: str
    storage_path: str
    mime_type: str
    status: str
    error: str | None
    chunks: list[Chunk]
    candidates: list[FilteredChunk]
    extractions: list[ExtractionRecord]
    progress_done: int
    progress_total: int


def _resolve_provider(explicit: Any = None) -> Any:
    """Provider selection hook — monkeypatch target for tests."""
    if explicit is not None:
        return explicit
    from app.core.config import get_settings
    from app.pipeline.extract import _get_provider

    return _get_provider(get_settings().llm_provider)


def build_graph(
    provider: Any,
    session_factory: sessionmaker[Session],
) -> Any:
    """Build the pipeline graph bound to `provider` and `session_factory`."""

    def parse_node(state: PipelineState) -> dict[str, Any]:
        from app.core.storage import get_storage

        data = get_storage().read(state["storage_path"])
        mime = state["mime_type"]
        if mime.endswith("pdf"):
            chunks = parse_pdf(data)
        elif "wordprocessingml" in mime:
            chunks = parse_docx(data)
        else:
            msg = f"Unsupported mime type: {mime}"
            raise ExtractionFailedError(msg)
        for chunk in chunks:
            chunk.document_id = state["document_id"]
        return {"chunks": chunks, "status": "filtering"}

    def filter_node(state: PipelineState) -> dict[str, Any]:
        candidates = candidate_chunks(state["chunks"])
        return {
            "candidates": candidates,
            "progress_total": len(candidates),
            "status": "extracting",
        }

    def extract_node(state: PipelineState) -> dict[str, Any]:
        extractions: list[ExtractionRecord] = []
        for fc in state["candidates"]:
            signals_text = "; ".join(fc.signals.matched_signals[:8])
            try:
                result = extract_clause(fc.chunk.text, signals_text, provider=provider)
            except ExtractionFailedError as exc:
                return {"error": str(exc), "status": "failed"}
            composite = compute_composite_confidence(
                llm_confidence=result.llm_confidence,
                filter_signal_count=len(fc.signals.matched_signals),
                citation_verified=False,  # finalized in score_node
            )
            extractions.append(
                ExtractionRecord(
                    chunk=fc.chunk,
                    result=result,
                    signal_count=len(fc.signals.matched_signals),
                    composite=composite,
                    citation=None,
                )
            )
        return {
            "extractions": extractions,
            "progress_done": len(extractions),
            "status": "scoring",
        }

    def score_node(state: PipelineState) -> dict[str, Any]:
        """Citation verification + final composite (Phase 11 wired into graph).

        R-5: a clause with no usable citation is blocked — `citation=None`
        marks it for dropping at persist. DOCX `page_number=None` remains
        legitimate (paragraph locators exist, so attach_citation passes).
        """
        kept: list[ExtractionRecord] = []
        for record in state["extractions"]:
            match = verify_quote(record["chunk"], record["result"].source_quote)
            try:
                citation = attach_citation(record["chunk"], match)
            except ValueError:
                continue  # R-5: block this clause; never persist citation-less
            record["citation"] = citation
            record["composite"] = compute_composite_confidence(
                llm_confidence=record["result"].llm_confidence,
                filter_signal_count=record["signal_count"],
                citation_verified=match.verified,
            )
            kept.append(record)
        return {"extractions": kept, "status": "persisting"}

    def persist_node(state: PipelineState) -> dict[str, Any]:
        """Transactional persist (Phase 12.6): own session, all-or-nothing."""
        from app.models.extracted_clause import ClauseStatus, ExtractedClause, ObligationType

        clauses = 0
        with session_factory() as db:
            try:
                for record in state["extractions"]:
                    citation = record["citation"]
                    assert citation is not None  # score_node guarantees
                    db.add(
                        ExtractedClause(
                            document_id=uuid.UUID(state["document_id"]),
                            obligation_type=ObligationType(record["result"].obligation_type),
                            plain_language_text=record["result"].plain_language_summary,
                            raw_source_text=record["chunk"].text,
                            page_number=citation["page_number"],
                            char_start=int(citation["char_start"]),
                            char_end=int(citation["char_end"]),
                            confidence_score=float(record["composite"]),
                            status=ClauseStatus.PENDING,
                        )
                    )
                    clauses += 1
                db.commit()
            except Exception:
                db.rollback()
                raise
        return {"status": "completed", "progress_done": clauses}

    def error_node(state: PipelineState) -> dict[str, Any]:
        return {"status": "failed"}

    graph = StateGraph(PipelineState)
    graph.add_node("parse", parse_node)
    graph.add_node("filter", filter_node)
    graph.add_node("extract", extract_node)
    graph.add_node("score", score_node)
    graph.add_node("persist", persist_node)
    graph.add_node("error", error_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "filter")
    graph.add_edge("filter", "extract")
    graph.add_conditional_edges(
        "extract",
        lambda state: "error" if state.get("error") else "score",
    )
    graph.add_edge("score", "persist")
    graph.add_edge("error", "__end__")
    return graph.compile()


def run_extraction(document_id: uuid.UUID, *, provider: Any = None) -> None:
    """Background entrypoint (Phase 12.2/12.4/12.5).

    - Concurrency guard: refuses to run while another run is active.
    - Re-run resets: deletes previous clauses before starting.
    - Never crashes: any exception leaves the document `failed`.
    """
    from app.core.db import get_session_factory
    from app.models.document import Document
    from app.models.extracted_clause import ExtractedClause

    factory = get_session_factory()

    # ── setup: guard + reset (own session) ────────────────────────────────
    with factory() as setup:
        doc = setup.get(Document, document_id)
        if doc is None:
            return
        if doc.extraction_status in RUN_IN_PROGRESS_STATUSES:
            return  # Phase 12.5: no duplicate runs
        setup.execute(delete(ExtractedClause).where(ExtractedClause.document_id == document_id))
        doc.extraction_status = "parsing"
        doc.extraction_error = None
        doc.extraction_progress_done = 0
        doc.extraction_progress_total = 0
        setup.commit()
        storage_path = doc.storage_path
        mime_type = doc.mime_type

    def _set_status(status: str, *, done: int = 0, total: int = 0, error: str | None = None) -> None:
        """Short-lived session per status update (Phase 12.3)."""
        with factory() as session:
            fresh = session.get(Document, document_id)
            if fresh is None:
                return
            fresh.extraction_status = status
            fresh.extraction_progress_done = done
            fresh.extraction_progress_total = total
            fresh.extraction_error = error
            session.commit()

    try:
        chosen = _resolve_provider(provider)
        initial: PipelineState = {
            "document_id": str(document_id),
            "storage_path": storage_path,
            "mime_type": mime_type,
            "status": "parsing",
            "error": None,
            "chunks": [],
            "candidates": [],
            "extractions": [],
            "progress_done": 0,
            "progress_total": 0,
        }
        app = build_graph(chosen, factory)

        final: dict[str, Any] = dict(initial)
        for event in app.stream(initial, stream_mode="updates"):
            for _node, update in event.items():
                final.update(update)
                _set_status(
                    str(final.get("status", "parsing")),
                    done=int(final.get("progress_done", 0)),
                    total=int(final.get("progress_total", 0)),
                )

        if final.get("status") == "failed":
            _set_status("failed", error=str(final.get("error") or "extraction failed")[:1023])
        else:
            _set_status(
                "completed",
                done=int(final.get("progress_done", 0)),
                total=int(final.get("progress_total", 0)),
            )
    except Exception as exc:  # noqa: BLE001 — background job must never crash the app
        _set_status("failed", error=str(exc)[:1023])
