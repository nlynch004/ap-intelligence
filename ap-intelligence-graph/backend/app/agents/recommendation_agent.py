"""Recommendation agent (spec Sec.20, Sec.21). Input: question + compact
retrieved context. Output: structured recommendation, uncertainty, confidence.
supporting_memory_ids are attached by the caller from the deterministic
retrieval result, not trusted from the model."""

from app.llm.factory import call_with_fallback
from app.llm.recommendation_schema import validate_raw_recommendation


def generate_recommendation(question: str, evidence_brief: str, structured_context: dict) -> tuple[dict, str]:
    """Returns a dict guaranteed to match RawRecommendationOut's shape - the
    raw LLM result is validated by `validate_raw_recommendation` before it
    is trusted; a malformed/incomplete live response falls back to the
    (always-valid) mock provider rather than reaching the routers as
    unvalidated data (see llm/factory.py::call_with_fallback)."""
    result, provider_name = call_with_fallback(
        "recommend", question, evidence_brief, structured_context, validate=validate_raw_recommendation
    )
    return result, provider_name
