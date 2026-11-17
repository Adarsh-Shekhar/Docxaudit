"""Shared mock-LLM helpers (Phase 10.9/12 tests — never live calls)."""
from __future__ import annotations

import json

from app.pipeline.extract import MockProvider

DEFAULT_QUOTE = "renews automatically"


def valid_extraction_json(source_quote: str = DEFAULT_QUOTE) -> str:
    """A deterministic, schema-valid extraction response."""
    return json.dumps(
        {
            "obligation_type": "renewal",
            "plain_language_summary": "This clause appears to require sixty days' notice to prevent automatic renewal.",
            "key_dates": [
                {"date_str": "sixty (60) days", "normalized_date": None, "description": "notice period"}
            ],
            "responsible_party": "either party",
            "llm_confidence": 0.8,
            "source_quote": source_quote,
        }
    )


def mock_provider(source_quote: str = DEFAULT_QUOTE) -> MockProvider:
    return MockProvider(valid_extraction_json(source_quote))


def broken_provider() -> MockProvider:
    """Provider whose output never parses — exercises the failure path."""
    return MockProvider("this is not json at all")
