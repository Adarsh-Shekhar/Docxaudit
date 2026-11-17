"""Scoring + citation verification tests (Phase 11.5)."""
from __future__ import annotations

import pytest

from app.pipeline.cite import attach_citation, verify_quote
from app.pipeline.parse import Chunk
from app.pipeline.score import compute_composite_confidence


def _chunk(text: str, page: int | None = 1, base: int = 0) -> Chunk:
    return Chunk(text=text, page_number=page, char_start=base, char_end=base + len(text))


# ── citation verification ────────────────────────────────────────────────────

def test_exact_quote_is_verified_with_exact_offsets() -> None:
    chunk = _chunk("The client shall pay within thirty (30) days of receipt.")
    match = verify_quote(chunk, "shall pay within thirty (30) days")
    assert match.verified
    assert chunk.char_start + 11 == match.char_start  # "The client " = 11 chars
    assert match.char_end - match.char_start == len("shall pay within thirty (30) days")


def test_paraphrased_quote_still_matches_fuzzily() -> None:
    chunk = _chunk("Vendor shall maintain a certificate of insurance with coverage of not less than $2,000,000.")
    quote = "maintain a certificate of insurance coverage of not less than $2,000,000"
    match = verify_quote(chunk, quote)
    assert match.verified
    assert chunk.char_start <= match.char_start < match.char_end <= chunk.char_end


def test_garbage_quote_falls_back_to_whole_chunk_unverified() -> None:
    chunk = _chunk("Some totally unrelated clause text.")
    match = verify_quote(chunk, "zzz nothing alike here")
    assert not match.verified
    assert match.char_start == chunk.char_start
    assert match.char_end == chunk.char_end


def test_offsets_are_absolute() -> None:
    # chunk starts at 100 in the document; match offsets must be absolute.
    chunk = _chunk("Renewal notice due January 1, 2026.", base=100)
    match = verify_quote(chunk, "January 1, 2026")
    assert match.verified
    assert match.char_start >= 100


def test_attach_citation_rejects_invalid_chunk() -> None:
    bad = Chunk(text="", page_number=None, char_start=5, char_end=2)
    match = verify_quote(bad, "anything")
    with pytest.raises(ValueError, match="R-5"):
        attach_citation(bad, match)


def test_attach_citation_allows_docx_page_none() -> None:
    chunk = _chunk("DOCX paragraph.", page=None)
    match = verify_quote(chunk, "DOCX paragraph")
    payload = attach_citation(chunk, match)
    assert payload["page_number"] is None
    assert payload["citation_verified"] is True


# ── composite scoring ────────────────────────────────────────────────────────

def test_composite_within_bounds() -> None:
    for llm in (0.0, 0.33, 0.5, 0.9, 1.0):
        for sigs in (0, 2, 4, 9):
            for cit in (True, False):
                score = compute_composite_confidence(
                    llm_confidence=llm, filter_signal_count=sigs, citation_verified=cit
                )
                assert 0.0 <= score <= 1.0


def test_perfect_inputs_score_high() -> None:
    score = compute_composite_confidence(llm_confidence=1.0, filter_signal_count=4, citation_verified=True)
    assert score == 1.0


def test_unverified_citation_lowers_score() -> None:
    verified = compute_composite_confidence(llm_confidence=0.8, filter_signal_count=3, citation_verified=True)
    unverified = compute_composite_confidence(llm_confidence=0.8, filter_signal_count=3, citation_verified=False)
    assert unverified < verified


def test_llm_confidence_is_never_the_sole_signal_r4() -> None:
    """R-4: even llm_confidence=1.0 with no signals + no citation can't max out."""
    score = compute_composite_confidence(llm_confidence=1.0, filter_signal_count=0, citation_verified=False)
    assert score < 1.0


def test_formula_documented_matches_implementation() -> None:
    # 0.5*0.8 + 0.25*(3/4) + 0.25*1.0 = 0.4 + 0.1875 + 0.25 = 0.8375
    score = compute_composite_confidence(llm_confidence=0.8, filter_signal_count=3, citation_verified=True)
    assert score == pytest.approx(0.8375)
