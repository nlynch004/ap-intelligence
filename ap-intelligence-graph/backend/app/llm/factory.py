"""Picks the LLM provider. One place to change to swap providers app-wide."""

import logging

from app.config import settings
from app.llm.mock_provider import MockProvider
from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)

_mock = MockProvider()
_openai_singleton: LLMProvider | None = None


def _get_openai() -> LLMProvider:
    global _openai_singleton
    if _openai_singleton is None:
        from app.llm.openai_provider import OpenAIProvider

        _openai_singleton = OpenAIProvider()
    return _openai_singleton


def get_provider() -> LLMProvider:
    if settings.has_openai_key:
        try:
            return _get_openai()
        except Exception:
            logger.exception("Failed to initialize OpenAIProvider, falling back to mock")
            return _mock
    return _mock


def call_with_fallback(fn_name: str, *args, validate=None, **kwargs):
    """Call `fn_name` on the live provider; on any runtime error (bad key,
    network, rate limit, malformed JSON) OR a structurally invalid result,
    fall back to the deterministic provider so a mid-demo API hiccup - or an
    LLM response that doesn't match the expected schema - never breaks the
    flow with an unhandled exception.

    `validate`, if given, is a callable(raw_result) -> result that raises on
    a structurally invalid result and otherwise returns the (possibly
    normalized) result. A validation failure is treated exactly like a call
    failure: it triggers the same mock fallback, not a propagated exception.
    """

    def _mock_result():
        result = getattr(_mock, fn_name)(*args, **kwargs)
        return validate(result) if validate else result

    provider = get_provider()
    if provider is _mock:
        return _mock_result(), _mock.name

    try:
        result = getattr(provider, fn_name)(*args, **kwargs)
        if validate:
            result = validate(result)
        return result, provider.name
    except Exception:
        logger.exception("Live provider call to %s failed or returned an invalid result, falling back to mock", fn_name)
        return _mock_result(), f"{_mock.name} (fallback)"
