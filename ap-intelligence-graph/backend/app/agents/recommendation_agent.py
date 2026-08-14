"""Recommendation agent (spec Sec.20, Sec.21). Input: question + compact
retrieved context. Output: structured recommendation, uncertainty, confidence.
supporting_memory_ids are attached by the caller from the deterministic
retrieval result, not trusted from the model."""

from app.llm.factory import call_with_fallback


def generate_recommendation(question: str, evidence_brief: str, structured_context: dict) -> tuple[dict, str]:
    result, provider_name = call_with_fallback("recommend", question, evidence_brief, structured_context)
    return result, provider_name
