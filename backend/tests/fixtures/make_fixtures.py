"""Generate SYNTHETIC contract fixtures (Phase 8.5).

Never real contracts (C-8, R-3) — deterministic, public-domain-shaped
clauses with known content so tests can assert exact offsets/pages.
"""
from __future__ import annotations

import io
import textwrap
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument

SYNTHETIC_CLAUSES: list[str] = [
    "1. Term and Renewal. This Agreement begins on January 1, 2026 and renews automatically for successive one (1) year periods unless either party gives sixty (60) days' prior written notice of non-renewal.",
    "2. Termination for Convenience. Either party may terminate this Agreement for any reason upon ninety (90) days' notice.",
    "3. Payment. Client shall pay an invoice of $1,500.00 monthly within thirty (30) days of receipt. Late payments accrue interest.",
    "4. Insurance. Vendor shall maintain a certificate of insurance with coverage of not less than $2,000,000 per occurrence, renewed annually.",
    "5. Governing Law. This Agreement is governed by the laws of the State of Delaware.",
]

_WRAP_WIDTH = 95  # chars per rendered line
_LINE_HEIGHT = 14
_TOP_MARGIN = 72


def build_synthetic_pdf_bytes(clauses_per_page: int = 4) -> bytes:
    """Create a synthetic multi-page contract PDF with known page boundaries.

    Lines are placed with `insert_text` (not `insert_textbox`, which
    collapses blank lines and can silently truncate overflow), one clause
    paragraph at a time with a visible blank gap between clauses.
    """
    doc = pymupdf.open()
    for page_start in range(0, len(SYNTHETIC_CLAUSES), clauses_per_page):
        page = doc.new_page()  # letter-size default
        y = _TOP_MARGIN
        for clause in SYNTHETIC_CLAUSES[page_start : page_start + clauses_per_page]:
            for line in textwrap.wrap(clause, _WRAP_WIDTH):
                page.insert_text((72, y), line, fontsize=10, fontname="helv")
                y += _LINE_HEIGHT
            y += _LINE_HEIGHT * 2  # blank gap between clauses
    out = io.BytesIO()
    doc.save(out)
    doc.close()
    return out.getvalue()


def build_synthetic_docx_bytes() -> bytes:
    """Create a synthetic DOCX with one clause per paragraph (plus heading)."""
    doc = DocxDocument()
    doc.add_heading("Synthetic Services Agreement", level=1)
    for clause in SYNTHETIC_CLAUSES:
        doc.add_paragraph(clause)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def write_fixtures(directory: Path) -> dict[str, Path]:
    """Write both fixtures to `directory` and return their paths."""
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "contract.pdf": directory / "synthetic_contract.pdf",
        "contract.docx": directory / "synthetic_contract.docx",
    }
    paths["contract.pdf"].write_bytes(build_synthetic_pdf_bytes())
    paths["contract.docx"].write_bytes(build_synthetic_docx_bytes())
    return paths


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    for name, path in write_fixtures(root).items():
        print(f"wrote {name}: {path} ({path.stat().st_size} bytes)")
