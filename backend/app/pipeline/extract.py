"""LLM extraction (Phase 10) — provider-agnostic interface, API-only.

`extract_clause(chunk_text, signals) -> ExtractionResult` behind a single
interface; provider selected via `LLM_PROVIDER` (groq | gemini). No local
LLM exists in this project (plan decision 2026-11-03).

Every call site gets: timeout (30s), typed failure (`ExtractionFailedError`),
retry with backoff on 429/5xx/timeout, and rate-limit awareness (C-5).
Prompts are versioned template files (rules Part B).
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import get_settings

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
_TIMEOUT_SECONDS = 30.0
_MAX_RETRIES = 3
_BACKOFF_BASE_SECONDS = 1.0
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class ExtractionFailedError(Exception):
    """Raised when the LLM call ultimately fails (after retries) or returns
    unparseable output. The document is marked failed, never crashed (TRD §6)."""


class ExtractionResult(BaseModel):
    """Structured extraction output (Phase 10.1)."""

    model_config = ConfigDict(extra="forbid")

    obligation_type: str  # validated against ObligationType values upstream
    plain_language_summary: str
    key_dates: list[dict[str, str | None]] = Field(default_factory=list)
    responsible_party: str | None = None
    llm_confidence: float = Field(ge=0.0, le=1.0)
    source_quote: str
    raw_llm_output: str = ""  # debugging only; NEVER logged in full (R-3)


class LLMProvider(Protocol):
    """Minimal provider contract used by `extract_clause`."""

    def complete_json(self, prompt: str, *, timeout: float) -> str:
        """Return the model's raw JSON string; raise RuntimeError on failure."""
        ...


# ── provider implementations ─────────────────────────────────────────────────

class GroqProvider:
    """Groq (Llama 3.3 70B) primary (Phase 10.3)."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.groq_api_key:
            msg = "GROQ_API_KEY not configured"
            raise ExtractionFailedError(msg)
        from groq import Groq

        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    def complete_json(self, prompt: str, *, timeout: float) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1024,
                response_format={"type": "json_object"},
                timeout=timeout,
            )
        except Exception as exc:  # SDK raises heterogeneous errors
            status_code = getattr(exc, "status_code", None)
            if status_code in _RETRYABLE_STATUS or status_code is None:
                raise _RetryableError(str(exc)) from exc
            raise ExtractionFailedError(str(exc)) from exc
        return response.choices[0].message.content or ""


class _RetryableError(Exception):
    """Internal marker for transient provider errors."""


class GeminiProvider:
    """Gemini Flash free tier fallback (Phase 10.4)."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            msg = "GEMINI_API_KEY not configured"
            raise ExtractionFailedError(msg)
        from google import genai

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    def complete_json(self, prompt: str, *, timeout: float) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
        except Exception as exc:
            raise _RetryableError(str(exc)) from exc
        return response.text or ""


class MockProvider:
    """Deterministic provider for unit tests (Phase 10.9) — never for prod."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.calls = 0

    def complete_json(self, prompt: str, *, timeout: float) -> str:
        self.calls += 1
        return self._response


# ── interface ────────────────────────────────────────────────────────────────

_PROVIDERS: dict[str, type] = {
    "groq": GroqProvider,
    "gemini": GeminiProvider,
}


def _get_provider(name: str | None = None, *, mock_response: str | None = None) -> Any:
    """Instantiate the configured provider; `mock_response` forces MockProvider."""
    if mock_response is not None:
        return MockProvider(mock_response)
    provider_name = (name or get_settings().llm_provider).lower()
    cls = _PROVIDERS.get(provider_name)
    if cls is None:
        msg = f"Unknown LLM_PROVIDER {provider_name!r} (supported: groq, gemini)"
        raise ExtractionFailedError(msg)
    return cls()


def _load_prompt_template() -> str:
    template = _PROMPTS_DIR / "extract_clause_v1.txt"
    return template.read_text(encoding="utf-8")


def _render_prompt(chunk_text: str, signals_text: str) -> str:
    return (
        _load_prompt_template()
        .replace("{{chunk_text}}", chunk_text)
        .replace("{{signals}}", signals_text or "(none)")
    )


def _strip_fences(raw: str) -> str:
    """Tolerate stray markdown fences some models add."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return match.group(0) if match else raw


def _call_with_retries(provider: Any, prompt: str) -> str:
    """Retry 429/5xx/timeout with exponential backoff (Phase 10.7).

    Rate-limit awareness (Phase 10.8): backoff starts at 1s and doubles;
    Groq free tier is ~30 req/min — callers also serialize per document.
    """
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES):
        try:
            return provider.complete_json(prompt, timeout=_TIMEOUT_SECONDS)
        except _RetryableError as exc:
            last_error = exc
            if attempt < _MAX_RETRIES - 1:
                time.sleep(_BACKOFF_BASE_SECONDS * (2**attempt))
        except ExtractionFailedError:
            raise
        except Exception as exc:  # unexpected → retryable in tests? no: fail fast
            msg = f"Unexpected provider error: {exc}"
            raise ExtractionFailedError(msg) from exc
    msg = f"LLM call failed after {_MAX_RETRIES} attempts: {last_error}"
    raise ExtractionFailedError(msg)


def extract_clause(
    chunk_text: str,
    signals_text: str = "",
    *,
    provider: Any = None,
) -> ExtractionResult:
    """Provider-agnostic interface (Phase 10.2). Raises ExtractionFailedError
    on persistent failure — callers mark the document failed, never crash."""
    prompt = _render_prompt(chunk_text, signals_text)
    chosen = provider if provider is not None else _get_provider()
    raw = _call_with_retries(chosen, prompt)

    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError as exc:
        msg = f"LLM returned unparseable JSON (len={len(raw)})"
        raise ExtractionFailedError(msg) from exc

    try:
        result = ExtractionResult.model_validate(data)
    except ValidationError as exc:
        msg = "LLM output missing required fields"
        raise ExtractionFailedError(msg) from exc
    result.raw_llm_output = raw
    return result

