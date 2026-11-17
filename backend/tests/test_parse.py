"""Parsing tests (Phase 8.4) — synthetic fixtures only (C-8, R-3)."""
from __future__ import annotations

import pymupdf
import pytest

from app.pipeline.parse import (
    Chunk,
    NoTextLayerError,
    _split_paragraphs,
    parse_docx,
    parse_pdf,
)
from tests.fixtures.make_fixtures import (
    SYNTHETIC_CLAUSES,
    build_synthetic_docx_bytes,
    build_synthetic_pdf_bytes,
)

# ── helpers ──────────────────────────────────────────────────────────────────

def _pdf_page_texts(file_bytes: bytes) -> list[str]:
    """The exact per-page text PyMuPDF extracts — ground truth for offsets."""
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    try:
        return [page.get_text("text") for page in doc]
    finally:
        doc.close()


# ── PDF ──────────────────────────────────────────────────────────────────────

def test_pdf_offset_reconstruction_is_exact() -> None:
    pdf = build_synthetic_pdf_bytes()
    chunks = parse_pdf(pdf)
    ground_truth = "".join(_pdf_page_texts(pdf))

    # Chunks now cover every character (separators absorbed) — exact rebuild.
    assert "".join(c.text for c in chunks) == ground_truth


def test_pdf_offsets_are_contiguous_and_non_overlapping() -> None:
    pdf = build_synthetic_pdf_bytes()
    chunks = parse_pdf(pdf)
    page_texts = _pdf_page_texts(pdf)

    # Within each page, chunk ranges must sit inside that page's global span.
    span_start = 0
    for page_index, page_text in enumerate(page_texts, start=1):
        span_end = span_start + len(page_text)
        page_chunks = [c for c in chunks if c.page_number == page_index]
        for c in page_chunks:
            assert span_start <= c.char_start
            assert c.char_end <= span_end
        span_start = span_end


def test_pdf_page_numbers_correct() -> None:
    # 5 clauses, 2 per page → 3 pages (2, 2, 1)
    chunks = parse_pdf(build_synthetic_pdf_bytes(clauses_per_page=2))
    pages = {c.page_number for c in chunks if c.text.strip()}
    assert pages == {1, 2, 3}

    content_per_page = {
        p: sum(1 for c in chunks if c.page_number == p and c.text.strip())
        for p in pages
    }
    assert all(n <= 2 for n in content_per_page.values())
    assert sum(n for n in content_per_page.values()) >= len(SYNTHETIC_CLAUSES)


def test_pdf_global_offsets_are_monotonic() -> None:
    chunks = parse_pdf(build_synthetic_pdf_bytes())
    starts = [c.char_start for c in chunks if c.text.strip()]
    ends = [c.char_end for c in chunks if c.text.strip()]
    assert starts == sorted(starts)
    assert all(s < e for s, e in zip(starts, ends, strict=True))


def test_scanned_pdf_raises_no_text_layer() -> None:
    # Build a genuinely image-only PDF (no text inserted).
    doc = pymupdf.open()
    page = doc.new_page()
    page.draw_rect(pymupdf.Rect(50, 50, 400, 200))  # shapes, no text
    import io

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()

    with pytest.raises(NoTextLayerError):
        parse_pdf(buf.getvalue())


# ── DOCX ─────────────────────────────────────────────────────────────────────

def test_docx_paragraph_chunks_with_locators() -> None:
    chunks = parse_docx(build_synthetic_docx_bytes())
    clause_chunks = [c for c in chunks if c.text.startswith(("1.", "2.", "3.", "4.", "5."))]
    assert len(clause_chunks) == len(SYNTHETIC_CLAUSES)
    for chunk in clause_chunks:
        assert chunk.page_number is None
        assert "paragraph_index" in chunk.extra


def test_docx_offsets_reconstruct_clauses() -> None:
    chunks = parse_docx(build_synthetic_docx_bytes())
    clause_chunks = [c for c in chunks if c.text.startswith(("1.", "2.", "3.", "4.", "5."))]
    for chunk, expected in zip(clause_chunks, SYNTHETIC_CLAUSES, strict=True):
        assert chunk.text.rstrip("\n") == expected
        assert chunk.char_end - chunk.char_start == len(chunk.text)


# ── splitting helper ─────────────────────────────────────────────────────────

def test_split_paragraphs_preserves_every_character() -> None:
    # No trailing newline: parts must rebuild the text exactly.
    page = "Para one.\n\nPara two.\n\nsecond line"
    assert "".join(_split_paragraphs(page)) == page

    # With trailing newline(s): also exact.
    page2 = "Para one.\n\nPara two.\n\n"
    assert "".join(_split_paragraphs(page2)) == page2


def test_chunk_is_immutable_shape() -> None:
    c = Chunk(text="x", page_number=1, char_start=0, char_end=1)
    assert c.document_id == ""
    assert isinstance(c.extra, dict)
