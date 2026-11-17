"""Citation verification and attachment (Phase 11.2/11.3, R-5).

The LLM is asked (prompt v1, rule 4) to quote the shortest source span
supporting its summary. We fuzzy-match that quote back to the original
chunk text to confirm it exists; the matched offset range is what gets
stored. A clause with no valid citation is BLOCKED from persisting —
never surfaced (R-5).
"""
from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz

from app.pipeline.parse import Chunk

# Fuzzy threshold (plan §11 Risks/Notes: tune against Phase 31 test set;
# 0.55 balances LLM paraphrase slips against false positives).
DEFAULT_MATCH_THRESHOLD = 0.55


@dataclass(slots=True)
class QuoteMatch:
    """Result of locating the LLM's quote inside the source chunk."""

    verified: bool
    char_start: int  # absolute offsets (chunk offsets + local match position)
    char_end: int
    match_score: float


def verify_quote(
    chunk: Chunk,
    quote: str,
    *,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> QuoteMatch:
    """Fuzzy-locate `quote` within `chunk.text` (Phase 11.2).

    - Exact substring → trivially verified.
    - Otherwise sliding-window fuzzy comparison (rapidfuzz `partial_ratio`
      alignment via `fuzz.partial_ratio_alignment`).
    - Fallback (plan §11.2: "if the chunk has only one plausible span, use
      it"): when nothing matches above threshold, the whole chunk is the
      span — verified=False so scoring lowers confidence, but the clause
      still carries the chunk's citation rather than being dropped.
    """
    quote = (quote or "").strip()
    if not quote:
        return QuoteMatch(verified=False, char_start=chunk.char_start, char_end=chunk.char_end, match_score=0.0)

    text = chunk.text
    local_start = text.find(quote)
    if local_start >= 0:
        return QuoteMatch(
            verified=True,
            char_start=chunk.char_start + local_start,
            char_end=chunk.char_start + local_start + len(quote),
            match_score=100.0,
        )

    alignment = fuzz.partial_ratio_alignment(quote, text)
    if alignment is not None and alignment.score / 100.0 >= threshold:
        return QuoteMatch(
            verified=True,
            char_start=chunk.char_start + alignment.dest_start,
            char_end=chunk.char_start + alignment.dest_end,
            match_score=alignment.score,
        )

    # Fallback: whole chunk is the only plausible span (verified=False).
    return QuoteMatch(
        verified=False,
        char_start=chunk.char_start,
        char_end=chunk.char_end,
        match_score=0.0,
    )


def attach_citation(chunk: Chunk, quote_match: QuoteMatch) -> dict[str, int | None | float | bool]:
    """Build the citation payload for an ExtractedClause (Phase 11.3).

    Raises ValueError if the chunk has no usable offset data — the caller
    must block the clause from persisting (R-5), never store a citation-less
    clause. DOCX chunks legitimately have page_number=None (documented).
    """
    if chunk.char_end < chunk.char_start or not chunk.text:
        msg = "Chunk has invalid offsets; refusing to attach citation (R-5)"
        raise ValueError(msg)

    page = chunk.page_number
    return {
        "page_number": page,
        "char_start": quote_match.char_start,
        "char_end": quote_match.char_end,
        "citation_verified": quote_match.verified,
        "match_score": quote_match.match_score,
    }
