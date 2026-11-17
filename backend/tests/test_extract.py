"""Extraction tests (Phase 10.9) — MockProvider only; no live LLM calls."""
from __future__ import annotations

import json

import pytest

from app.pipeline.extract import (
    ExtractionFailedError,
    ExtractionResult,
    MockProvider,
    _strip_fences,
    extract_clause,
)

_VALID_JSON = {
    "obligation_type": "renewal",
    "plain_language_summary": "This clause appears to require 60 days' notice to prevent automatic renewal.",
    "key_dates": [{"date_str": "sixty (60) days", "normalized_date": None, "description": "notice period"}],
    "responsible_party": "either party",
    "llm_confidence": 0.82,
    "source_quote": "renews automatically for successive one (1) year periods unless either party gives sixty (60) days' prior written notice",
}


def test_extract_clause_returns_valid_result() -> None:
    result = extract_clause(
        "This Agreement renews automatically... sixty (60) days' notice.",
        signals_text="keyword:renew; notice_period:60",
        provider=MockProvider(json.dumps(_VALID_JSON)),
    )
    assert isinstance(result, ExtractionResult)
    assert result.obligation_type == "renewal"
    assert result.llm_confidence == 0.82
    assert result.source_quote.startswith("renews automatically")
    # raw output retained for debugging but summary is the surface text
    assert "appears to require" in result.plain_language_summary


def test_unparseable_json_raises_typed_failure() -> None:
    with pytest.raises(ExtractionFailedError, match="unparseable"):
        extract_clause("text", provider=MockProvider("this is not json"))


def test_missing_fields_raise_typed_failure() -> None:
    bad = {"obligation_type": "renewal"}  # everything else missing
    with pytest.raises(ExtractionFailedError, match="missing required fields"):
        extract_clause("text", provider=MockProvider(json.dumps(bad)))


def test_confidence_out_of_range_rejected() -> None:
    bad = {**_VALID_JSON, "llm_confidence": 1.7}
    with pytest.raises(ExtractionFailedError, match="missing required fields"):
        extract_clause("text", provider=MockProvider(json.dumps(bad)))


def test_markdown_fences_tolerated() -> None:
    fenced = f"Sure! Here is the JSON:\n```json\n{json.dumps(_VALID_JSON)}\n```"
    result = extract_clause("text", provider=MockProvider(fenced))
    assert result.obligation_type == "renewal"


def test_persistent_provider_failure_raises_after_retries() -> None:
    class AlwaysFail:
        calls = 0

        def complete_json(self, prompt: str, *, timeout: float) -> str:  # noqa: ARG002
            self.calls += 1
            from app.pipeline.extract import _RetryableError

            raise _RetryableError("429 rate limited")  # transient → retried

    provider = AlwaysFail()
    with pytest.raises(ExtractionFailedError):
        # monkeypatch sleep to keep the test fast
        import app.pipeline.extract as ex

        original_sleep = ex.time.sleep
        ex.time.sleep = lambda *_: None
        try:
            extract_clause("text", provider=provider)
        finally:
            ex.time.sleep = original_sleep
    assert provider.calls == ex._MAX_RETRIES


def test_non_retryable_failure_fails_fast() -> None:
    class AuthFail:
        calls = 0

        def complete_json(self, prompt: str, *, timeout: float) -> str:  # noqa: ARG002
            self.calls += 1
            from app.pipeline.extract import ExtractionFailedError

            raise ExtractionFailedError("401 unauthorized")

    provider = AuthFail()
    with pytest.raises(ExtractionFailedError):
        extract_clause("text", provider=provider)
    assert provider.calls == 1


def test_prompt_is_rendered_from_versioned_template() -> None:
    captured: dict[str, str] = {}

    class Capture:
        def complete_json(self, prompt: str, *, timeout: float) -> str:  # noqa: ARG002
            captured["prompt"] = prompt
            return json.dumps(_VALID_JSON)

    extract_clause("THE CLAUSE BODY", signals_text="keyword:renew", provider=Capture())
    prompt = captured["prompt"]
    assert "THE CLAUSE BODY" in prompt
    assert "keyword:renew" in prompt
    assert "appears to require" in prompt  # R-1 instruction present in template
    assert "{{chunk_text}}" not in prompt  # placeholders rendered


def test_strip_fences() -> None:
    assert _strip_fences('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _strip_fences('{"a": 1}') == '{"a": 1}'

