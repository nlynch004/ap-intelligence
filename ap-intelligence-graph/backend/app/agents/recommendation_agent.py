from app.llm.factory import call_with_fallback
from app.llm.recommendation_schema import validate_raw_recommendation


def generate_recommendation(question: str, evidence_brief: str, structured_context: dict) -> tuple[dict, str]:
    result, provider_name = call_with_fallback(
        "recommend", question, evidence_brief, structured_context, validate=validate_raw_recommendation
    )
    return result, provider_name
