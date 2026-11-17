"""Candidate filter tests (Phase 9.4)."""
from __future__ import annotations

from app.pipeline.filter import (
    candidate_chunks,
    extract_dates,
    filter_chunks,
    is_candidate_chunk,
    normalize_date,
)
from app.pipeline.parse import Chunk


def _chunk(text: str) -> Chunk:
    return Chunk(text=text, page_number=1, char_start=0, char_end=len(text))


# ── known obligation sentences → candidate (DoD: no false negatives) ────────

OBLIGATION_SENTENCES = [
    "This Agreement renews automatically unless either party gives sixty (60) days' notice.",
    "Client shall pay an invoice of $1,500.00 within thirty days of receipt.",
    "Vendor shall maintain a certificate of insurance renewed annually.",
    "Either party may terminate this Agreement upon ninety (90) days' notice.",
    "The policy expires on January 1, 2026.",
]

BOILERPLATE_SENTENCES = [
    "This Agreement is governed by the laws of the State of Delaware.",
    "The parties acknowledge that electronic signatures are acceptable.",
    "No amendment is valid unless made in writing and signed by both parties.",
    "Headings are for convenience only and do not affect interpretation.",
]


def test_obligation_sentences_are_candidates() -> None:
    for sentence in OBLIGATION_SENTENCES:
        signals = is_candidate_chunk(sentence)
        assert signals.is_candidate, f"false negative on: {sentence!r} → {signals.matched_signals}"


def test_boilerplate_is_not_candidate() -> None:
    for sentence in BOILERPLATE_SENTENCES:
        signals = is_candidate_chunk(sentence)
        assert not signals.is_candidate, f"false positive on: {sentence!r} → {signals.matched_signals}"


def test_notice_period_extraction() -> None:
    assert is_candidate_chunk("ninety (90) days' notice.").notice_period_days == 90
    assert is_candidate_chunk("30 days notice required").notice_period_days == 30
    assert is_candidate_chunk("sixty (60) days' prior written notice").notice_period_days == 60
    assert is_candidate_chunk("no notice here").notice_period_days is None


def test_extract_dates_finds_various_forms() -> None:
    text = "Due January 1, 2026; invoice $1,500.00 within 30 days; renewal annually."
    dates = extract_dates(text)
    assert any("January 1, 2026" in d for d in dates)
    assert any("$" in d for d in dates)
    assert any("30 days" in d for d in dates)


def test_normalize_date() -> None:
    assert normalize_date("January 1, 2026") == "2026-01-01"
    assert normalize_date("2026-01-01") == "2026-01-01"
    assert normalize_date("not a date") is None


# ── pipeline-level filter behavior (DoD: ≥50% reduction, zero false negs) ────

def test_filter_reduces_candidate_set() -> None:
    all_chunks = [_chunk(s) for s in OBLIGATION_SENTENCES + BOILERPLATE_SENTENCES * 3]
    results, stats = filter_chunks(all_chunks)
    assert stats.total_chunks == len(all_chunks)
    assert stats.candidates == len(OBLIGATION_SENTENCES)
    candidates = candidate_chunks(all_chunks)
    # 5 candidates out of 17 chunks → well over 50% reduction
    assert len(candidates) <= len(all_chunks) * 0.5


def test_filter_keeps_non_candidates_available() -> None:
    """Full-scan escape hatch (Phase 9.2): non-candidates stay in results."""
    results, _ = filter_chunks([_chunk(s) for s in BOILERPLATE_SENTENCES])
    assert len(results) == len(BOILERPLATE_SENTENCES)
    assert all(not r.signals.is_candidate for r in results)


def test_signals_histogram_has_no_document_text() -> None:
    """R-3: observability must not leak text (Phase 9.5)."""
    _, stats = filter_chunks([_chunk("Vendor shall renew the certificate by 2026-01-01")])
    for key in stats.signals_histogram:
        assert key in {"keyword", "date", "notice_period", "ner_date"}
    assert all(isinstance(v, int) for v in stats.signals_histogram.values())


def test_min_signals_threshold_is_configurable() -> None:
    text = "The certificate renews annually."  # keyword + recurring term
    assert is_candidate_chunk(text, min_signals=1).is_candidate
    assert not is_candidate_chunk(text, min_signals=10).is_candidate
