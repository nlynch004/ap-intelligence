from app.llm.campaign_review_schema import validate_raw_campaign_review
from app.llm.factory import call_with_fallback


def generate_campaign_review(evidence: dict) -> tuple[dict, str]:
    result, provider_name = call_with_fallback("review_campaign", evidence, validate=validate_raw_campaign_review)
    return result, provider_name
