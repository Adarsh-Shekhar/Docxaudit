"""Composite confidence scoring (Phase 11.1, R-4).

Formula (documented here and in code comments — Phase 31 may retune weights):

    composite = clamp01(
        0.50 * llm_confidence                       # model's own (never sole) signal
      + 0.25 * min(1.0, filter_signals / 4)         # cheap-filter signal density
      + 0.25 * citation_signal                      # 1.0 verified, 0.4 unverified
    )

Low confidence changes DISPLAY (flag, sort-to-top), never visibility (R-4).
The pipeline never drops a candidate based on score (R-4) — dropping happens
only at citation verification (R-5), which is a different rule.
"""
from __future__ import annotations

CITATION_VERIFIED_SIGNAL = 1.0
CITATION_UNVERIFIED_SIGNAL = 0.4

WEIGHT_LLM = 0.50
WEIGHT_SIGNALS = 0.25
WEIGHT_CITATION = 0.25
MAX_SIGNALS_FOR_FULL_BONUS = 4.0


def compute_composite_confidence(
    *,
    llm_confidence: float,
    filter_signal_count: int,
    citation_verified: bool,
) -> float:
    """Blend LLM self-confidence with rule signals and citation verification."""
    llm_term = WEIGHT_LLM * max(0.0, min(1.0, llm_confidence))
    signal_term = WEIGHT_SIGNALS * min(1.0, max(0, filter_signal_count) / MAX_SIGNALS_FOR_FULL_BONUS)
    citation_term = WEIGHT_CITATION * (
        CITATION_VERIFIED_SIGNAL if citation_verified else CITATION_UNVERIFIED_SIGNAL
    )
    composite = llm_term + signal_term + citation_term
    return max(0.0, min(1.0, composite))
