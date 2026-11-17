"""Candidate filtering (Phase 9) — cheap CPU-only pre-filter before LLM calls.

Mandatory step (constraint C-5): keeps LLM usage under Groq's free-tier
ceiling. Never remove. Thresholds configurable via env/settings (Phase 9.3).

Never logs document text (R-3) — counts and signals only (Phase 9.5).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import dateparser
import spacy

from app.pipeline.parse import Chunk

# ── Keyword/phrase signals (Phase 9.1) ───────────────────────────────────────

OBLIGATION_KEYWORDS: tuple[str, ...] = (
    "renew", "renewal", "terminate", "termination", "notice", "shall", "must",
    "obligation", "comply", "certificate", "insurance", "payment", "due",
    "expiration", "expire",
)

_DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d+\s+days?(?:'|\u2019)?\s+(?:notice|prior|written)", re.IGNORECASE),
    re.compile(r"\b(?:sixty|ninety|thirty|six|nine|three)\s+\(\d+\)\s+days", re.IGNORECASE),
    re.compile(r"\b\d+\s+days\b", re.IGNORECASE),
    re.compile(r"\b(?:annual|quarterly|monthly|yearly|weekly|bi-?annual)\b", re.IGNORECASE),
    re.compile(r"\$\s?\d[\d,]*(?:\.\d{2})?", re.NOFLAG),
)

_NOTICE_PERIOD = re.compile(
    r"\b(\d+|sixty|ninety|thirty|six|nine|three)\s*\(?(\d+)?\)?\s*days?(?:'|\u2019)?\s*(?:prior\s+)?(?:written\s+)?notice",
    re.IGNORECASE,
)

_NUMBER_WORDS = {"sixty": 60, "ninety": 90, "thirty": 30, "six": 6, "nine": 9, "three": 3}

_NLP = None


def _nlp() -> spacy.Language:
    """Lazy spaCy model load (startup cost avoided in unit tests that skip)."""
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm")
    return _NLP


@dataclass(slots=True)
class FilterSignals:
    """What the cheap filter found in one chunk (Phase 9.1 output)."""

    is_candidate: bool
    matched_signals: list[str]
    extracted_dates: list[str]  # raw strings; normalized in extract/score later
    notice_period_days: int | None


@dataclass(slots=True)
class FilteredChunk:
    """A chunk annotated with its filter results."""

    chunk: Chunk
    signals: FilterSignals


@dataclass(slots=True)
class FilterStats:
    """Observability without document text (Phase 9.5)."""

    total_chunks: int = 0
    candidates: int = 0
    signals_histogram: dict[str, int] = field(default_factory=dict)


def extract_dates(text: str) -> list[str]:
    """Raw date-like strings via regex + dateparser validation (§9.1)."""
    found: list[str] = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0)
            if snippet not in found:
                found.append(snippet)
    return found


def _parse_notice_days(text: str) -> int | None:
    match = _NOTICE_PERIOD.search(text)
    if match is None:
        return None
    number = match.group(1)
    if number.isdigit():
        return int(number)
    return _NUMBER_WORDS.get(number.lower())


def is_candidate_chunk(text: str, *, min_signals: int | None = None) -> FilterSignals:
    """Decide candidate status via keyword + regex + DATE-NER signals (§9.1)."""
    if min_signals is None:
        from app.core.config import get_settings

        min_signals = get_settings().filter_min_signals
    lowered = text.lower()
    matched: list[str] = []

    keyword_hits = [kw for kw in OBLIGATION_KEYWORDS if kw in lowered]
    matched.extend(f"keyword:{kw}" for kw in keyword_hits)

    dates = extract_dates(text)
    matched.extend(f"date:{d}" for d in dates)

    notice_days = _parse_notice_days(text)
    if notice_days is not None:
        matched.append(f"notice_period:{notice_days}")

    # spaCy NER: DATE entities boost candidacy when keywords exist too.
    doc = _nlp()(text)
    ner_dates = [e.text for e in doc.ents if e.label_ == "DATE"]
    matched.extend(f"ner_date:{d}" for d in ner_dates if d not in [x.split(":", 1)[1] for x in matched])

    is_candidate = len(matched) >= min_signals and (
        bool(keyword_hits) or bool(dates) or bool(ner_dates)
    )
    return FilterSignals(
        is_candidate=is_candidate,
        matched_signals=matched,
        extracted_dates=dates,
        notice_period_days=notice_days,
    )


def filter_chunks(
    chunks: list[Chunk],
    *,
    min_signals: int | None = None,
) -> tuple[list[FilteredChunk], FilterStats]:
    """Annotate every chunk (Phase 9.2 keeps non-candidates in the output list
    for the optional 'full scan' mode; only candidates reach the LLM).

    `min_signals` defaults to `FILTER_MIN_SIGNALS` from env (Phase 9.3)."""
    if min_signals is None:
        from app.core.config import get_settings

        min_signals = get_settings().filter_min_signals
    stats = FilterStats(total_chunks=len(chunks))
    results: list[FilteredChunk] = []
    for chunk in chunks:
        signals = is_candidate_chunk(chunk.text, min_signals=min_signals)
        results.append(FilteredChunk(chunk=chunk, signals=signals))
        if signals.is_candidate:
            stats.candidates += 1
        for signal in signals.matched_signals:
            key = signal.split(":", 1)[0]
            stats.signals_histogram[key] = stats.signals_histogram.get(key, 0) + 1
    return results, stats


def candidate_chunks(chunks: list[Chunk], *, min_signals: int | None = None) -> list[FilteredChunk]:
    """Convenience: only the chunks that will be sent to the LLM."""
    results, _ = filter_chunks(chunks, min_signals=min_signals)
    return [fc for fc in results if fc.signals.is_candidate]


def normalize_date(raw: str) -> str | None:
    """Best-effort dateparser normalization of a raw date string (§9.1).

    Returns ISO 'YYYY-MM-DD' or None when unparseable — normalization is
    refined again at extraction time (Phase 10/11), never a hard failure.
    """
    parsed = dateparser.parse(raw, settings={"RETURN_AS_TIMEZONE_AWARE": False})
    if parsed is None:
        return None
    return parsed.date().isoformat()
