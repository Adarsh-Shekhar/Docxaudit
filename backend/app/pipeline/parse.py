"""Parse PDF/DOCX into offset-preserving chunks (Phase 8).

Every chunk carries `page_number` + global `char_start`/`char_end` so every
downstream step (and every surfaced clause) can cite exactly (R-5).

DOCX limitation (documented, plan §3.2): DOCX has no native page numbers
without rendering; `page_number` is None and citation locators fall back to
paragraph indices.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import pymupdf  # PyMuPDF 2.x canonical import name
from docx import Document as DocxDocument


class NoTextLayerError(Exception):
    """Raised for scanned/image PDFs with no extractable text (C-7: OCR out of scope)."""


@dataclass(slots=True)
class Chunk:
    """One paragraph/section of the document with exact citations."""

    text: str
    page_number: int | None
    char_start: int
    char_end: int  # exclusive
    document_id: str = ""
    extra: dict[str, object] = field(default_factory=dict)
    """PDF bounding box of the chunk text in PDF points (x0, y0, x1, y1).

    Phase 17.2 decision: computed ONCE here at parse time via PyMuPDF
    (reliable word coordinates) and stored through to ExtractedClause —
    computing on the frontend via a pdf.js text layer is less reliable.
    None for DOCX chunks and whenever the box cannot be located (the
    frontend then falls back to the text view).
    """
    bbox: tuple[float, float, float, float] | None = None


def parse_pdf(file_bytes: bytes) -> list[Chunk]:
    """Extract paragraph-level chunks with page numbers and global offsets.

    Offsets are *global* across the document and contiguous: adjacent chunks
    cover every character of the extracted text exactly once, with the
    inter-chunk separators (newlines) belonging to neither chunk.
    """
    chunks: list[Chunk] = []
    doc = pymupdf.open(stream=file_bytes, filetype="pdf")
    try:
        if doc.page_count == 0:
            raise NoTextLayerError("PDF has no pages")

        offset = 0
        for page_number in range(1, doc.page_count + 1):
            page = doc[page_number - 1]
            text = page.get_text("text")
            if text.strip():
                for paragraph in _split_paragraphs(text):
                    chunks.append(
                        Chunk(
                            text=paragraph,
                            page_number=page_number,
                            char_start=offset,
                            char_end=offset + len(paragraph),
                            bbox=_locate_bbox(page, paragraph),
                        )
                    )
                    offset += len(paragraph)
            # Pages whose text ends without a newline contribute nothing extra;
            # separator handling lives inside _split_paragraphs now.

        if not any(c.text.strip() for c in chunks):
            raise NoTextLayerError("No extractable text layer (scanned/image PDF?)")
        return chunks
    finally:
        doc.close()


def parse_docx(file_bytes: bytes) -> list[Chunk]:
    """Extract paragraph chunks; page_number=None with paragraph locators."""
    stream = io.BytesIO(file_bytes)
    try:
        doc = DocxDocument(stream)
    except Exception as exc:  # malformed docx
        msg = "Invalid DOCX file"
        raise ValueError(msg) from exc

    chunks: list[Chunk] = []
    offset = 0
    paragraph_texts = [p.text for p in doc.paragraphs]
    for paragraph_index, text in enumerate(paragraph_texts):
        if text.strip():
            # Each chunk absorbs its paragraph separator so that
            # "".join(chunks) == paragraphs joined with "\n" (offsets exact).
            chunk_text = text + ("\n" if paragraph_index < len(paragraph_texts) - 1 else "")
            chunks.append(
                Chunk(
                    text=chunk_text,
                    page_number=None,  # DOCX has no native page numbers (§8.1)
                    char_start=offset,
                    char_end=offset + len(chunk_text),
                    extra={"paragraph_index": paragraph_index},
                )
            )
            offset += len(chunk_text)
    return chunks


def _locate_bbox(page: pymupdf.Page, paragraph: str) -> tuple[float, float, float, float] | None:
    """Locate a paragraph's bounding box on `page` (Phase 17.2).

    PyMuPDF `search_for` normalizes whitespace, so multi-line chunks still
    match. Strategy: normalized whole-chunk search first; per-line fallback
    for chunks spanning layout oddities. Returns None when nothing matches
    (the clause then simply has no visual highlight).
    """
    body = paragraph.strip()
    if not body:
        return None
    try:
        rects = page.search_for(body)
        if not rects:
            lines = [line.strip() for line in body.split("\n") if line.strip()]
            found: list[pymupdf.Rect] = []
            for line in lines:
                found.extend(page.search_for(line))
            rects = found
        if not rects:
            return None
        union = rects[0]
        for rect in rects[1:]:
            union |= rect
        return (union.x0, union.y0, union.x1, union.y1)
    except Exception:  # noqa: BLE001 — bbox is best-effort; never fail parsing
        return None


def extract_full_text(chunks: list[Chunk]) -> str:
    """The canonical full text the citation offsets point into.

    Chunks absorb their separators by construction, so this is exactly
    `"".join(chunks)` for both PDF (matches raw page texts) and DOCX
    (skipped empty paragraphs contribute no offset — see parse_docx).
    Used by the text-view endpoint (Phase 17.4) and verification tests.
    """
    return "".join(chunk.text for chunk in chunks)


def reconstruct_text(chunks: list[Chunk], separators: dict[int, str] | None = None) -> str:
    """Rebuild original text from chunks for offset verification (tests/§11).

    `separators` maps `page_number -> separator text` used between chunks on
    that page; defaults to the paragraph separator used by the parsers.
    """
    sep_map: dict[int, str] = separators or {}
    pieces: list[str] = []
    prev_page: int | None = None
    for chunk in chunks:
        if prev_page is not None:
            page_key = chunk.page_number if chunk.page_number is not None else prev_page
            pieces.append(sep_map.get(page_key, "\n"))
        pieces.append(chunk.text)
        prev_page = chunk.page_number
    return "".join(pieces)


_CLAUSE_START = re.compile(r"^\s*\d+\.\s")


def _split_paragraphs(page_text: str) -> list[str]:
    """Split a page's text into paragraph chunks.

    Boundaries: blank lines, or a line starting a numbered clause
    ("1. Term...", "2. Pay...") — common in real contracts even when the
    rendering collapses blank lines.

    Invariant: `"".join(chunks) == page_text`. Each chunk absorbs the
    line breaks that follow it (including blank-line separators), so no
    character is ever dropped between chunks.
    """
    lines = page_text.split("\n")
    paragraphs: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        j = i + 1
        while j < n and lines[j].strip() != "" and not _CLAUSE_START.match(lines[j]):
            j += 1
        region = "\n".join(lines[i:j])
        if j < n:
            region += "\n"  # include the trailing line break of this region
        if region:
            paragraphs.append(region)
        i = j
    return paragraphs
