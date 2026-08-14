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


def call_with_fallback(fn_name: str, *args, **kwargs):
    """Call `fn_name` on the live provider; on any runtime error (bad key,
    network, rate limit, malformed JSON), fall back to the deterministic
    provider so a mid-demo API hiccup never breaks the flow."""
    provider = get_provider()
    if provider is _mock:
        return getattr(_mock, fn_name)(*args, **kwargs), _mock.name
    try:
        return getattr(provider, fn_name)(*args, **kwargs), provider.name
    except Exception:
        logger.exception("Live provider call to %s failed, falling back to mock", fn_name)
        return getattr(_mock, fn_name)(*args, **kwargs), f"{_mock.name} (fallback)"
