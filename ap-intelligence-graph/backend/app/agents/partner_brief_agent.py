from app.llm.factory import call_with_fallback
from app.llm.partner_brief_schema import validate_raw_partner_brief


def generate_partner_brief(evidence: dict) -> tuple[dict, str]:
    result, provider_name = call_with_fallback("generate_partner_brief", evidence, validate=validate_raw_partner_brief)
    return result, provider_name
