from app.llm.factory import call_with_fallback
from app.llm.memory_history_schema import validate_raw_historical_summary


def generate_historical_summary(evidence: dict) -> tuple[dict, str]:
    result, provider_name = call_with_fallback("summarize_history", evidence, validate=validate_raw_historical_summary)
    return result, provider_name
